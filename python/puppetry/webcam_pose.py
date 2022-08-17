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
import time
import numpy as np
import cv2
import itertools
import mediapipe as mp
import eventlet
import puppetry
from camera import Camera
from display import Display
import sys
import traceback
import logging
import glm
from math import sin, cos, pi, sqrt
from pconsts import Vitruvian as V, Model as M
from putils import *
from pconsts import Vitruvian as V, Model as M, LandmarkIndicies as LI

# set up a logger sending to stderr, which gets routed to viewer logs
LOGGER_FORMAT = "%(filename)s:%(lineno)s %(funcName)s: %(message)s"
LOGGER_LEVEL = logging.INFO

logging.basicConfig( format=LOGGER_FORMAT, handlers=[logging.StreamHandler(sys.stderr)], level=LOGGER_LEVEL)
_logger = logging.getLogger(__name__)

UPDATE_PERIOD = 0.1     # time between puppetry updates

RAD_TO_DEG = 57.2958
DEG_TO_RAD  = 0.017453

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
                min_detection_confidence = 0.5,    \
                min_tracking_confidence  = 0.5)
        self.detected = None
        self.camera = Camera(camera_num = camera_num)
        self.display = Display()
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
                            flags=cv2.cv2.SOLVEPNP_ITERATIVE)

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

    def add_pose_effector(self, name, joint_id, output):
        scale = V.fv_scale
                
        joint = self.avg_pose_pts[joint_id].copy()

        joint[0] *= scale
        joint[1] *= (scale * -1.0)
        joint[2] *= (scale * -1.0)

        #Z aspect is kinda trash, do the best we can.
        #joint[2] = (joint[2] - self.pose_face_center[2]) * scale

        #joint[2] = 0.15     #Just make a static fake Z until we get X and Y.

        make_zxy_effector( name, joint, output )

    def rotate_head(self, output):
        '''Rotate the head and write it to the output stream'''

        packed_quaternion = puppetry.packedQuaternionFromEulerAngles( \
                                float(self.head_rot_ea[0] * DEG_TO_RAD * -1.0), \
                                float(self.head_rot_ea[1] * DEG_TO_RAD), \
                                float(self.head_rot_ea[2] * DEG_TO_RAD * -1.0) )

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

        a = self.avg_face_pts[LI.face_rect[2]]
        b = self.avg_face_pts[LI.face_rect[3]]

        #Animate the avatar
        self.rotate_head(output)

        #Draw on output image
        num_points = self.display.draw_all_points(self.avg_face_pts)
        if num_points > 0:
            self.display.draw_perpendicular( \
                            self.image_points[0], \
                            self.face_rot_vec, \
                            self.face_pos_vec, \
                            self.camera)
        else:
            return False
        return True

    def get_hand_rotation(self, label):
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
        euler = glm.vec3( -0.5 * pi, 0.0 * pi , 0.0 * pi )
        return glm.quat(euler) * glm.quat(rot)

    def handle_hand(self, label, output):
        '''Handles the finer points of the hand'''

        hname = 'rhand'
        shid = 12   #shoulder id
        elid = 14   #elbow id
        wrid = 16   #wrist id
        landmarks = self.detected.right_hand_landmarks
        if label == 'Left':
            hname = 'lhand'
            shid = 11
            elid = 13
            wrid = 15
            landmarks = self.detected.left_hand_landmarks

        if puppetry.part_active(hname) and \
           landmarks is not None:

            average_landmarks(landmarks, \
                              self.avg_hand_pts[label], \
                              NUM_HAND_POINTS, \
                              self.point_smoothing)

            self.display.draw_all_points(self.avg_hand_pts[label])

            self.avg_pose_pts[wrid][0] = self.avg_pose_pts[wrid][0] / self.display.aspect_ratio
            #self.avg_pose_pts[elid][0] = self.avg_pose_pts[elid][0] / self.display.aspect_ratio

            #This is because the chest doesn't move. 
            self.avg_pose_pts[elid][2] -= self.avg_pose_pts[shid][2]
            self.avg_pose_pts[wrid][2] -= self.avg_pose_pts[shid][2]

            #This is just magic number poking because Z doesn't make sense.
            self.avg_pose_pts[elid][2] -= ((self.avg_pose_pts[wrid][2] - self.avg_pose_pts[elid][2])/3.0)
            self.avg_pose_pts[elid][2] *= 1.5

            #Yes that's intended, the elbow is shoulder, the wrist is the elbow
            self.add_pose_effector('mShoulder'+label, elid, output)
            self.add_pose_effector('mElbow'+label, wrid, output)


    def main_loop(self):
        '''The main loop of expression processing'''

        self.camera.configure_camera()         # Start up camera device

        new_frame=True        #Set to true at end of frame
        frame_start_time=None       #Time for start of frame.
        frame_elapsed_time=None     #Total time spent in frame
        track_start_time=None       #Start time for this tracking iter

        show_erase = True

        data={}
        #while True:
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

                self.display.draw_landmarks(self.detected.pose_landmarks)

                #Get the pose's face center (exclude nose).
                self.pose_face_center = average_sequential_points(1,10, \
                                            self.avg_pose_pts)
                #Get the pose's pelvis center
                self.pose_pelvis_center = average_sequential_points(23,24, 
                                            self.avg_pose_pts)


                #Get the detected shoulder width
                self.shoulder_width = magnitude( \
                        get_direction( \
                                self.avg_pose_pts[11], \
                                self.avg_pose_pts[12] ) )


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
            if (UPDATE_PERIOD - frame_compute_time) < (track_compute_time * 1.5): 
                if success:
                    #Send the puppetry info to viewer first.
                    puppetry.sendPuppetryData(data)
                    # have an image from the camera, use it
                    self.display.do_display(track_start_time)
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
