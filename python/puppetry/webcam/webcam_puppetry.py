#!/usr/bin/env python3
"""\
@file webacam_puppetry.py
@brief

$LicenseInfo:firstyear=2022&license=viewerlgpl$
Second Life Viewer Source Code
Copyright (C) 2022, Linden Research, Inc.

This library is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation;
version 2.1 of the License only.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this library; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

Linden Research, Inc., 945 Battery Street, San Francisco, CA  94111  USA
$/LicenseInfo$
"""

'''
This script uses the LEAP framework for sending messages to the viewer.
Tell the viewer to launch it with the following option:
    --leap "python /path/to/this/script/this_script.py"
The viewer will start this script in a side process and will
read messages from its stdout.

The joint data is a dictionary with the following format:
    data={"joint_name":{"type":[1.23,4.56,7.89]}, ...}
Where:
    joint_name = string recognized by LLVOAvatar::getJoint(const std::string&),
        e.g. something like: "mWristLeft"
    type = "local_rot" | "rot" | "pos" | "scale"
    type's value = array of three floats (e.g. [x,y,z])
Multiple joints can be combined into the same dictionary.

Notes about debugging at the command line:

When you test this script at the command line it will block
because the leap.py framework is waiting for the initial message
from the viewer.  To unblock the system paste the following
string into the script's stdin:

119:{'data':{'command':'18ce5015-b651-1d2e-2470-0de841fd3635', \
     'features':{}},'pump':'54481a53-c41f-4fc2-606e-516daed03636'}
'''

import argparse
import cv2
import itertools
import glm
import logging
import mediapipe as mp
import numpy as np
import os
import sys
import time
import traceback

from camera import Camera
from display import Display
from plot import Plot
from math import sin, cos, pi, sqrt, degrees, radians
from putils import *
from pconsts import Model as M, LandmarkIndicies as LI

try:
    import puppetry
except ImportError as err:
    # modify sys.path so we can find puppetry module in parent directory
    currentdir = os.path.dirname(os.path.realpath(__file__))
    parentdir = os.path.dirname(currentdir)
    sys.path.append(parentdir)
    parentdir = os.path.dirname(parentdir)
    sys.path.append(parentdir)

# now we can really import puppetry
try:
    import puppetry
except ImportError as err:
    sys.exit("Can't find puppetry module")

DO_PLOT = False  #Set to True to display realtime 3D plot of data from mediapipe

# set up a logger sending to stderr, which gets routed to viewer logs
LOGGER_FORMAT = "%(filename)s:%(lineno)s %(funcName)s: %(message)s"
LOGGER_LEVEL = logging.INFO

logging.basicConfig( format=LOGGER_FORMAT, handlers=[logging.StreamHandler(sys.stderr)], level=LOGGER_LEVEL)
_logger = logging.getLogger(__name__)

UPDATE_PERIOD = 0.1     # time between puppetry updates

WINDOW_NAME = "Image"

NUM_FACE_POINTS = 468
NUM_HAND_POINTS =  21
NUM_POSE_POINTS =  32

class Expression:
    '''The Expression class manages mapping input from
        face tracking to the leap puppetry stream'''

    def __init__(self, camera_num = 0):
        self.mp_holistic = mp.solutions.holistic
        self.holistic = self.mp_holistic.Holistic( \
                static_image_mode = False,
                min_detection_confidence = 0.5,    \
                min_tracking_confidence  = 0.5)
        self.detected = None
        self.camera = Camera(camera_num = camera_num)
        self.display = Display()
        self.plot = None
        if DO_PLOT:
            self.plot = Plot()
        self.face_box = None
        self.pose_face_center    = [ 0.0, 0.0, 0.0 ]    #Center of face in pose
        self.pose_pelvis_center  = [ 0.0, 0.0, 0.0 ]    #Center of pelvis_center in pose
        self.face_rot_vec   = None  #The rotation of the face in the frame
        self.face_pos_vec   = None  #Translation of the face from center
        self.head_rot_ea   = [ 0.0, 0.0, 0.0 ] #Stored value for exp avg.
        self.face_transmat = None   #Face Transformation matrix.
        self.point_smoothing = 1.0  #Smoothing factor 0-1 lower is smoother
        self.smoothing = 0.4  #Smoothing factor 0-1 lower is smoother
        self.image_points = np.empty([6,2], dtype="double")
        self.avg_face_pts = np.zeros([NUM_FACE_POINTS,3], dtype="double")
        self.avg_pose_pts = np.zeros([NUM_POSE_POINTS,3], dtype="double")
        self.avg_hand_pts = { 'Left':  np.zeros([NUM_HAND_POINTS+1,3], dtype="double"),
                              'Right': np.zeros([NUM_HAND_POINTS+1,3], dtype="double") }
        self.hand_rot_ea = { 'Left':  [ 0.0, 0.0, 0.0 ],
                             'Right': [ 0.0, 0.0, 0.0 ] }
        self.arm_lengths = { 'Left' : 1.0, 'Right': 1.0 }

        self.expected_normalized_neck_height = 0.63
        self.neck_vertical_offset = 0.0

    def find_model_rotation(self, points, model_points, orientation_landmarks):
        '''Use a subset of the detected points to determine
           the rotation of the face relative the camera.'''

        #Extract orientation landmarks from points
        index=0
        for point in orientation_landmarks:
            self.image_points[index] = [ \
                    points[point][0] * self.camera.size[0], \
                    points[point][1] * self.camera.size[1]  \
            ]
            index += 1

        #Find the translation and rotation of the face.
        #translation becomes the effector position for the head.
        #rotation the rotation of the head.
        rot_vec = None
        pos_vec = None
        rot = None
        try:
            (success, rot_vec, pos_vec) = \
                        cv2.solvePnP(model_points, \
                            self.image_points, \
                            self.camera.matrix, \
                            self.camera.dist_coeffs, \
                            flags=cv2.SOLVEPNP_ITERATIVE)

            #Get a rotation matrix.
            rmat, jac = cv2.Rodrigues(rot_vec)
            #Get angles
            angles, mtxR, mtxQ, Qx, Qy, Qz = cv2.RQDecomp3x3(rmat)

            #Put things in the right frame for the viewer.
            rot = [ \
                    angles[2], \
                    angles[0] * -1.0, \
                    angles[1] \
                ]

            if abs(rot[1]) > 60:
                if rot[1] >= 0:
                    rot[1] = 180 - rot[1]
                else:
                    rot[1] = -180 - rot[1]
        except cv2.error as excp:
            puppetry.log("find_model_rotation() cv2 exception: %s" % str(excp))
            rot_vec = None
            pos_vec = None
            rot = None

        return rot_vec, pos_vec, rot

    def add_vector_pose_effector(self, name, joint, output):
        # The Puppetry feature expects the data to be "normalized" such that the span
        # between both arms is 2.0 units.
        normalization_factor = 2.0 / (self.arm_lengths['Left'] + self.arm_lengths['Right'])
        joint[0] *= normalization_factor
        joint[1] *= normalization_factor
        joint[2] *= normalization_factor

        ''' Before make_zyx_effector() the data is in the "webcam capture frame"
        but it gets transformed into the SL-avatar frame.
                        ___
                       /o o\ 
                       \___/
                         |
             R o--+--+-+ | +-+--+--o L
                         +
                         |
                         +              z     z
                         |             /      |
                       +-@-+          @--x    @--y
                       |   |          |      /
                       +   +          y     x
                       |   |
                       |   |      webcam    SL-avatar
                      /   /       capture   frame
                                  frame
        '''
        make_zxy_effector( name, joint, output )
        return joint

    def create_relative_effector(self, name, base, offset, output):
        '''Creates an effector offset from base by offset vector named name'''
        joint = base + offset

        # The Puppetry feature expects the data to be "normalized" such that the span
        # between both arms is 2.0 units.
        normalization_factor = 2.0 / (self.arm_lengths['Left'] + self.arm_lengths['Right'])
        joint[0] *= normalization_factor
        joint[1] *= normalization_factor
        joint[2] *= normalization_factor

        make_zxy_effector( name, joint, output)


    def rotate_head(self, output):
        '''Rotate the head and write it to the output stream'''

        deg_rot = [ float(self.head_rot_ea[0] * -1.0), \
                    float(self.head_rot_ea[1]) ,       \
                    float(self.head_rot_ea[2] * 1.0) ]

        packed_quaternion = puppetry.packedQuaternionFromEulerAngles( \
                    radians(deg_rot[0]), radians(deg_rot[1]), radians(deg_rot[2]) )

        if puppetry.part_active('head'):
            output["mHead"] =  {"rot": packed_quaternion}

        return self.head_rot_ea

    def handle_head(self, landmarks, output):
        '''handle stuff pertaining to the head'''

        average_landmarks(landmarks, self.avg_face_pts, NUM_FACE_POINTS, self.point_smoothing)
        self.face_rot_vec, self.face_pos_vec, rot = \
            self.find_model_rotation(self.avg_face_pts, M.face_points, LI.face_orientation)

        if rot is None:
            return False

        if abs(rot[0]) <= 60 and abs(rot[1]) <= 60 and abs(rot[2]) <= 60:
            self.head_rot_ea = get_weighted_average_vec( rot, self.head_rot_ea, self.smoothing )

        #Animate the avatar
        self.rotate_head(output)

        #Draw on output image
        num_points = self.display.draw_all_points(self.avg_face_pts, LI.face_orientation, LI.face_rect)
        if num_points > 0:
            self.display.draw_perpendicular( \
                            self.image_points[0], \
                            self.face_rot_vec, \
                            self.face_pos_vec, \
                            self.camera)
        else:
            return False
        return True

    def rotate_hand(self, label, output):
        '''Set the hand rotation in a similar way to the head rotation.
            We need 5 points that maintain a relatively stable relationship
            to one another.  The wrist and bases of the fingers make 4 but
            the thumb moves around a bit too much so we are simply going to 
            take the the distance and direction from the index base to 
            the pinky base and copy that to a new point relative the 
            wrist (the heel of the palm)'''

        #Get direction across the finger bases.
        palm_dir = get_direction(self.avg_hand_pts[label][5], \
                                 self.avg_hand_pts[label][17] )
        #Create a hand heel position from wrist and fingerbases direction.
        for idx in range(0,3):
            self.avg_hand_pts[label][NUM_HAND_POINTS][idx] = \
                self.avg_hand_pts[label][0][idx] + palm_dir[idx]

        #Find rotation of the hand.
        rot_vec, pos_vec, rot = \
            self.find_model_rotation(self.avg_hand_pts[label], M.hand_points[label], LI.hand_orientation)

        if abs(rot[0]) <= 90 and abs(rot[1]) <= 90 and abs(rot[2]) <= 90:
            self.hand_rot_ea[label] = get_weighted_average_vec( rot, self.hand_rot_ea[label], self.smoothing )

        #Fix the rotation for the viewer.  This should be fine since it is quat rotations.
        nrot = self.hand_rot_ea[label].copy()

        nrot[0] *= -1.0
        #nrot[1] *= 1.0
        nrot[2] *= -1.0

        packed_quaternion = puppetry.packedQuaternionFromEulerAngles( \
                                float(radians(nrot[0])), \
                                float(radians(nrot[1])), \
                                float(radians(nrot[2]))  \
                             )
        #puppetry.log("Hand Rot: %.3f %.3f %.3f" % ( self.hand_rot_ea[label][0] * -1.0, self.hand_rot_ea[label][1], self.hand_rot_ea[label][2] * 1.0 ) )

        joint_name = 'mWrist'+label
        if joint_name in output:
            output[joint_name]['rot'] = packed_quaternion
        else:
            output[joint_name] = { 'rot':packed_quaternion }

        return glm.quat(nrot)

    def handle_hand(self, label, output):
        '''Handles the finer points of the hand
        The webcam capture coordinate frame is:
                    ___
                   /o o\ 
                   \___/
                     |
         R o--+--+-+ | +-+--+--o L
                     +
                     |
                     +           z
                     |          /
                   +-@-+       @--x
                   |   |       |
                   +   +       y
                   |   |
                   |   |
                  /   /
        '''
        hname = 'rhand'
        shoulder_id = 12
        elbow_id = 14
        wrist_id = 16
        pinky_id = 18
        index_id = 20
        landmarks = self.detected.right_hand_landmarks
        if label == 'Left':
            hname = 'lhand'
            shoulder_id = 11
            elbow_id = 13
            wrist_id = 15
            pinky_id = 17
            index_id = 19

            landmarks = self.detected.left_hand_landmarks

        pose_wrist_v = None

        if puppetry.part_active(hname) and \
           landmarks is not None:

            average_landmarks(landmarks, \
                              self.avg_hand_pts[label], \
                              NUM_HAND_POINTS, \
                              self.point_smoothing)

            self.display.draw_all_points(self.avg_hand_pts[label])

            wrist_p = self.avg_pose_pts[wrist_id].copy()
            elbow_p = self.avg_pose_pts[elbow_id].copy()
            shoulder_p = self.avg_pose_pts[shoulder_id].copy()

            # HACK: I get more consistant length measurments when we DON'T
            # scale X-component by the aspect ratio.  Are we sure this is
            # what we want to do? - Leviathan
            scale_by_aspect_ratio = False
            if scale_by_aspect_ratio:
                wrist_p[0] = wrist_p[0] / self.display.aspect_ratio
                elbow_p[0] = elbow_p[0] / self.display.aspect_ratio
                shoulder_p[0] = shoulder_p[0] / self.display.aspect_ratio

            # measure arm length
            shoulder = shoulder_p - self.neck_pos
            upper_arm = elbow_p - shoulder_p
            lower_arm = wrist_p - elbow_p
            length = lambda v : sqrt(np.inner(v, v))
            arm_length = length(shoulder) + length(upper_arm) + length(lower_arm)

            # store a running average of the arm_length
            blend = 0.1
            self.arm_lengths[label] = (1.0 - blend) * self.arm_lengths[label] + blend * arm_length

            wrist_p[1] += self.neck_vertical_offset

            #Yes that's intended, the elbow is shoulder, the wrist is the elbow
            #self.add_vector_pose_effector('mShoulder'+label, elbow_p, output)
            pose_wrist_v = self.add_vector_pose_effector('mElbow'+label, wrist_p, output)

            #quat = self.rotate_hand(label, output)

            if self.plot is not None:
                elbow = self.avg_pose_pts[elbow_id].copy()
                wrist = self.avg_pose_pts[wrist_id].copy()
                index = self.avg_pose_pts[index_id].copy()
                self.plot.add_output_point(elbow)
                self.plot.add_output_point(wrist)

                #SPATTERS figure out post scaling merge
                #perp = rotate_point( wrist, index, quat )
                #self.plot.add_perp_point(perp)

        else:           #If we aren't rendering hands, don't render fingers.
            return

        return  #Forced finger disable
        if puppetry.part_active('fingers'):
            debug_wrist_v = output['mElbow'+label]['pos']

            hand_wrist_v =  self.avg_hand_pts[label][0]     #Position from hand

            #normal scale Index: 0.0977052 Mid: 0.104237 Ring: 0.0992813 Pinky: 0.0858058 Thumb: 0.0657669
            #norm = 1.70338


            #Create a scalar from observed hand to model hand scale.
            live_hand_width = distance_3d(
                    hand_wrist_v,
                    self.avg_hand_pts[label][LI.fingerbases['Index']] )
            live_hand_width += distance_3d(
                    hand_wrist_v,
                    self.avg_hand_pts[label][LI.fingerbases['Pinky']] )

            #hand_ratio = live_hand_width / M.hand_unit
            hand_ratio = M.hand_unit / live_hand_width

            hand_ratio *= 0.5       #Unclear why but our scale ended up wrong.  Just hack it for now.

            axial_correction = glm.quat( glm.vec3( 0.5 * pi, 0.0 * pi , 0.0 * pi ) )

            #avg_wrist_dir = get_direction( self.avg_pose_pts[wrist_id], \
            #                        ( self.avg_pose_pts[index_id] + self.avg_pose_pts[pinky_id] ) )
            #avg_wrist_v = np.array(axial_correction * avg_wrist_dir)
            #avg_wrist_v *= hand_ratio
            #self.create_relative_effector('mWrist'+label, pose_wrist_v, avg_wrist_v, output)

            #puppetry.log("Normies: mHandRight3Thumb: 0.066 mHandRight3Index: 0.098 mHandRight3Middle: 0.104 mHandRight3Ring: 0.099 mHandRight3Pinky: 0.086 ")
            #outstr = "Geners:  "
            for key in LI.fingertips:
                tip_v = self.avg_hand_pts[label][LI.fingertips[key]]    #This fingertip in the hand.
                tip_d = np.array( axial_correction * get_direction(hand_wrist_v, tip_v) )   #Direction from wrist to fingertip

                tip_d *= hand_ratio   #Scale the distance to the fingertip.
                joint_name = "mHand" + key + "3" + label
                self.create_relative_effector(joint_name, pose_wrist_v, tip_d, output)

                dist = magnitude ( distance_3d(debug_wrist_v, output[joint_name]['pos'] ) )
                #outstr = outstr + " %s: %.3f" % ( joint_name, dist)
            #puppetry.log(outstr)

    def get_initial_skeleton(self):
        '''On startup, mediapipe blocks heavily, temporarily disrupting leap communication
           So here we'll request/wait for skeleton data from the viewer before continuing.

           NOTE: After skeleton data is received, we continue on.  The first frame of 
           webcam capture may still be blocking, which means there is a small window of time
           where if the agent changes skeletons in the viewer, this information may not 
           be obtained by this plug-in module. 

           TODO:  Move mediapipe into a thread to get around blocking
        '''

        puppetry.sendPuppetryData(dict(command='send_skeleton'))    #Request skeleton
        retries = 3
        end_time = time.time() + 2.0

        while puppetry.isRunning() and retries > 0:
            if puppetry.get_skeleton_data('scale') is not None:
                return True           #We've got some data, can continue.

            eventlet.sleep(0.1) #Sleep 1/10th of a second

            cur_time = time.time()
            if cur_time > end_time:
                retries = retries - 1
                end_time = cur_time + 3.0
                if retries > 0:
                    puppetry.sendPuppetryData(dict(command='send_skeleton'))    #Re-request skeleton data.
        return False


    def main_loop(self):
        '''The main loop of expression processing'''

        frame_number = 0

        self.camera.configure_camera()         # Start up camera device

        new_frame=True        #Set to true at end of frame
        frame_start_time=None       #Time for start of frame.
        frame_elapsed_time=None     #Total time spent in frame
        track_start_time=None       #Start time for this tracking iter

        show_erase = True

        data={}
        while puppetry.isRunning():
            # Check to see if the camera device has changed
            if puppetry.camera_number is not None:
                self.display.erase_image()
                show_erase = True
                self.camera.device.release()
                self.camera = Camera(camera_num = puppetry.camera_number)
                puppetry.camera_number = None
                self.camera.configure_camera()         # Fire it up

            success = True
            track_start_time = time.time()
            if new_frame:
                frame_start_time = track_start_time
                new_frame = False

            face = None
            if self.camera.get_rgb_frame():
                self.detected = self.holistic.process(self.camera.rgb_image)
            else:
                success = False

            self.face_box = None

            if success and self.detected.face_landmarks is not None:
                data={} #At this point we know we have data so flush any subframe data.
                self.display.prep_output(self.camera.bgr_image)
                success = self.handle_head(self.detected.face_landmarks, data)
            else:
                success = False

            if success and self.detected.pose_world_landmarks is not None:
                #Found the face, let's proceed
                average_landmarks(self.detected.pose_world_landmarks, \
                                  self.avg_pose_pts, \
                                  NUM_POSE_POINTS, \
                                  self.point_smoothing)

                #Get the detected shoulder width
                self.shoulder_width = magnitude( \
                        get_landmark_direction( \
                                self.detected.pose_world_landmarks.landmark[11], \
                                self.detected.pose_world_landmarks.landmark[12] ) )

                #Note we draw pose_landmarks not pose_world_landmarks
                self.display.draw_landmarks(self.detected.pose_landmarks)

                if self.plot is not None:
                    self.plot.add_pose_landmarks(self.detected.pose_world_landmarks)

                #Get the pose's face center (exclude nose).
                self.pose_face_center = average_sequential_points(1,10, \
                                            self.avg_pose_pts)
                #Get the pose's pelvis center
                self.pose_pelvis_center = average_sequential_points(23,24, 
                                            self.avg_pose_pts)


                head_id = 9
                other_head_id = 10
                head_pos = average_sequential_points(head_id, other_head_id, self.avg_pose_pts)

                if self.plot is not None:
                    self.plot.add_output_point(head_pos)

                #Warning:  add_vector_pose_effector modifies passed in value
                if puppetry.part_active('head'):
                    # the "head" points are actually on the face and tend to be
                    # too far down and forward so we push head_pos up and back
                    DEFAULT_HEAD_VERTICAL_OFFSET = -0.08
                    DEFAULT_HEAD_FORWARD_OFFSET = 0.20
                    head_pos[1] += DEFAULT_HEAD_VERTICAL_OFFSET
                    head_pos[2] += DEFAULT_HEAD_FORWARD_OFFSET
                    #Warning:  add_vector_pose_effector modifies passed in value
                    self.add_vector_pose_effector('mHead', head_pos, data)

                # BUG: There can be a systematic vertical offset between neck and pelvis
                # as measured here vs the SL-avatar's model.
                # WORKAROUND: we compute an approximate neck_vertical_offset in the measurement-frame
                # and use it later to adjust measured-frame arm points before transforming to avatar's
                # root-frame and putting Puppetry data on the wire.
                shoulder_id = 11
                other_shoulder_id = 12
                self.neck_pos = average_sequential_points(shoulder_id, other_shoulder_id, self.avg_pose_pts)

                # Remember: measurement-frame has y-axis pointing DOWN so negate
                # self.expected_normalized_neck_height when computing the difference
                # between where we expect to find it, and where it actually is.
                normalization_factor = 2.0 / (self.arm_lengths['Left'] + self.arm_lengths['Right'])
                neck_vertical_offset = -self.expected_normalized_neck_height / normalization_factor - self.neck_pos[1]
                if self.neck_vertical_offset == 0.0:
                    self.neck_vertical_offset = neck_vertical_offset
                else:
                    blend = 0.1
                    self.neck_vertical_offset = (1.0 - blend) * self.neck_vertical_offset + blend * neck_vertical_offset

                self.handle_hand('Left', data)
                self.handle_hand('Right', data)

            cur_time = time.time()
            track_compute_time = cur_time - track_start_time
            frame_compute_time = cur_time - frame_start_time

            #Tracking time shouldn't vary much.  To get the smoothest data, 
            #Process as many tracking frames as we can within a leap frame
            #and average the data.  Tracking computation times shouldn't vary
            #much so we'll presume that if there's more than 1.5x the time it 
            #took to do this tracking, there's time to fetch another frame.
            #If not, send the data and prep for next frame.

            #if (UPDATE_PERIOD - frame_compute_time) < (track_compute_time * 1.5): 
            if True: 
                if success:
                    #Send the puppetry info to viewer first.
                    puppetry.sendPuppetryData(data)
                    # have an image from the camera, use it
                    self.display.do_display(track_start_time)

                    if self.plot is not None:
                        self.plot.draw()
                        frame_number += 1
                        self.plot.set_frame_number(frame_number)

                elif show_erase:
                    # if we just changed cameras and it failed, display
                    # the image we just erased so prevoius camera goes away
                    self.display.do_display(track_start_time)
                    show_erase = False

                cur_time = time.time()
                frame_compute_time = cur_time - frame_start_time
                nap_duration = max(0.0, UPDATE_PERIOD - frame_compute_time)
                eventlet.sleep(nap_duration)

                new_frame = True

            # Window has been closed or hit 'q' to quit
            try:
                key_press = cv2.waitKey(1) & 0xFF
                if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) == 0 or \
                    key_press == ord('q') or \
                    key_press == 27:
                    if self.plot is not None:
                        self.plot.stop()
                    puppetry.stop()   # will exit loop
            except cv2.error as excp:
                # Will throw exceptions before we get a window set up
                puppetry.log("quit check cv2 exception %s" % str(excp))
                pass

        try:
            # attempt to clean up
            self.camera.device.release()
            cv2.destroyAllWindows()
        except Exception as ex:
            pass


def main(camera_num = 0):
    '''pylint wants to docstring for the main function'''
    # _logger.setLevel(logging.DEBUG)
    puppetry.start()
    try:
        face = Expression(camera_num = camera_num)
    except Exception as exerr:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        puppetry.log("stacktrace: %r" % traceback.format_tb(exc_traceback))
        puppetry.log("Unable to create Expression for camera %r : %r" % (camera_num, str(exerr)))
        return

    #face.get_initial_skeleton()     #Get skeleton data from viewer.
    face.main_loop()
    puppetry.stop()

if __name__ == "__main__":
    """ Deal with command line arguments """

    parser = argparse.ArgumentParser(description='Second Life face motion capture',
        epilog="Pass in camera number to use")
    parser.add_argument('-c', '--camera', dest='camera_number',
        default=0, help='Camera device number to use')
    args = parser.parse_args()

    main(camera_num = int(args.camera_number))
