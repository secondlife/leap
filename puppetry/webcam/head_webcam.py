"""
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
    type = "rot" | "pos" | "scale"
    type's value = array of three floats (e.g. [x,y,z])
Multiple joints can be combined into the same dictionary.

Notes about debugging at the command line:

When you test this script at the command line it will block
because the leap.py framework is waiting for the initial message
from the viewer.  To unblock the system paste the following
string into the script's stdin:

119:{'data':{'command':'18ce5015-b651-1d2e-2470-0de841fd3635','features':{}},'pump':'54481a53-c41f-4fc2-606e-516daed03636'}

Also, for more readable text with newlines between messages
uncomment the print("") line in the main loop below.
"""


import time
import numpy as np
import cv2
from PIL import Image, ImageDraw
import face_recognition
import eventlet

import puppetry

CAMERA_DIMENSIONS = [ 320, 240 ]
UPDATE_PERIOD = 0.1     # time between puppetry updates

MIRROR = True   #Make what is left right and what is right all that is left

DISPLAY_VIDEO = True    #Do we want to see what the agent is doing?
DISPLAY_FACE_TRACK = True    #Face tracking lines on the video?
class Expression:
    '''
    A class for using realtime data from the webcam to animate SecondLife Avatars
    '''

    def __init__(self):
        self.capture_device = None  #The handler to the webcam
        self.capture_id = 0         #Which camer we're using.
        self.face_rot_vec   = None  #The rotation of the face in the frame
        self.face_pos_vec   = None  #Translation of the face from center
        self.camera_matrix  = None
        self.dist_coeff     = None
        self.model_points = np.array([               # 3D model points.
                                (0.0, 0.0, 0.0),             # Nose tip
                                (0.0, -330.0, -65.0),        # Chin
                                (-225.0, 170.0, -135.0),     # Left eye left corner
                                (225.0, 170.0, -135.0),      # Right eye right corne
                                (-150.0, -150.0, -125.0),    # Left Mouth corner
                                (150.0, -150.0, -125.0)      # Right mouth corner
                            ])
        self.head_buf = []      #Buffer the head a few frames so it doesn't jerk as much


    def getFrame( self ):
        '''
            Gets a frame from the camera and scales it by scale_factor
            The scale factor is for tuning and optimization.  A smaller
            frame will find faces more quickly but with less accuracy
            Converts frame from BGR to RGB
            returns the scaled RGB frame
        '''

        # Grab a single frame of video
        ret_code, bgr_frame = self.capture_device.read()

        #TODO look at ret_code

        # Convert the image from BGR color (CV output) to RGB display and face track.
        # NOTE: BGR and inverting palette may improve tracking quality for dark skin tones

        if MIRROR:
            bgr_frame = cv2.flip(bgr_frame, 1)

        return bgr_frame


    def find_facial_landmarks( self, frame ):
        '''
            use face recognition to find key features on the face for animating
            expression
            Returns face_landmarks or None
        '''

        # Find all facial features in all the faces in the image
        face_landmarks_list = face_recognition.face_landmarks(frame)

        for face_landmarks in face_landmarks_list:
            #TODO this loop cycles through all the faces we found in the image.
            #typically this will only be one but weird things will happen if
            #a second person enters the image or there's a poster on the wall.
            #A few of different solutions are possible.
            # 1) use the nearest (largest/least occluded) centermost face
            # 2) use position to make a continuity.
            # 3) The user could take a snapshot of themselves stored only locally
            # and then we track only the face of the person in the photo.

            # NOTE: We'll face a similar and more difficult version of this challenge
            # on distinguishing the front of the left hand from the back of the right.

            return face_landmarks      #Hack!
        return None

    def displayDetected( self, frame, face_landmarks, image_points ):
        '''Display the video stream and mark the faces on it'''

        if not DISPLAY_VIDEO:
            return

        display_image = frame

        if DISPLAY_FACE_TRACK:
            # Create a PIL imagedraw object so we can draw on the picture
            pil_image = Image.fromarray(frame)
            d = ImageDraw.Draw(pil_image)

            # Project a 3D point (0, 0, 1000.0) onto the image plane.
            # We use this to draw a line sticking out of the nose

            (nose_end_point2D, jacobian) = cv2.projectPoints(np.array([(0.0, 0.0, 1000.0)]), \
                    self.face_rot_vec, self.face_pos_vec, self.camera_matrix, self.dist_coeffs)

            # Let's trace out each facial feature in the image with a line!
            for facial_feature in face_landmarks.keys():
                d.line(face_landmarks[facial_feature], width=3)

            display_image = np.array(pil_image)

            for p in image_points:
                cv2.circle(display_image, (int(p[0]), int(p[1])), 3, (0,0,255), -1)

            p1 = ( int(image_points[0][0]), int(image_points[0][1]))
            p2 = ( int(nose_end_point2D[0][0][0]), int(nose_end_point2D[0][0][1]))

            cv2.line(display_image, p1, p2, (255,0,0), 2)

        # Display the resulting image
        cv2.imshow('Video', display_image)

    def generate_expression( self, size ):
        '''
           Use the points we found in the image to establish the plain
           of the face then map the relative positions of the features
           against the neutral expression and output effector and
           rotational data for the viewer to consume.
        '''

        # TODO These values are a 'good enough' at the moment, we can probably improve
        #them a bit and adding more could give us better mapping.

        #print ("Camera Matrix :\n {0}".format(self.camera_matrix))

        #TODO:  Lenses have distortion. Could make this tuneable, have a few good
        #defaults.  When this gets a little more sophisticated, we'll be using the
        #distortion to help determine front-to-back depth in the scene

        #print ("Rotation Vector:\n {0}".format(self.face_rot_vec))
        #print ("Translation Vector:\n {0}".format(self.face_pos_vec))

        yaw = float(self.face_rot_vec[1][0] * 1.0) 
        pitch = float(self.face_rot_vec[0][0] + 3.2)
        roll = float(self.face_rot_vec[2][0] * -1.0)
        packed_quaternion = puppetry.packedQuaternionFromEulerAngles(yaw, pitch, roll)
        data = {"mHead": {"rot": packed_quaternion}}

        #TODO: scale translation into the model space and apply as the mHead effector target
        #Use the rest of the model points in relation to the plane of the face to
        #generate effector targets for eyelids and lips
        #TODO: Add model points for eyebrows.

        return data

    def main_loop( self ):
        '''
        Main loop
        '''
        print("Initializing")
        # Get a reference to webcam #0 (the default one)
        self.capture_device = cv2.VideoCapture( self.capture_id )
        self.capture_device.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_DIMENSIONS[0])
        self.capture_device.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_DIMENSIONS[1])

        time.sleep(1.0)

        while True:
            t0 = time.monotonic()
            bgr_frame =  self.getFrame( )
            rgb_frame = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)

            img_size = rgb_frame.shape

            face_landmarks = self.find_facial_landmarks( rgb_frame )
            if face_landmarks is None:
                continue

            image_points = np.array([ face_landmarks['nose_bridge'][-1],
                                         face_landmarks['chin'][8],
                                         face_landmarks['left_eye'][0],
                                         face_landmarks['right_eye'][3],
                                         face_landmarks['top_lip'][0],
                                         face_landmarks['top_lip'][6]
                                        ], dtype="double")
            # Camera internals
            focal_length = img_size[1]
            center = (img_size[1]/2, img_size[0]/2)
            self.camera_matrix = np.array(
                                     [[focal_length, 0, center[0]],
                                     [0, focal_length, center[1]],
                                     [0, 0, 1]], dtype = "double"
                                     )

            self.dist_coeffs = np.zeros((4,1)) # Assuming no lens distortion

            #Find the translation and rotation of the face.
            #translation becomes the effector position for the head.
            #rotation the rotation of the head.
            (success, self.face_rot_vec, self.face_pos_vec) = \
                        cv2.solvePnP(self.model_points, image_points, \
                        self.camera_matrix, self.dist_coeffs, \
                        flags=cv2.cv2.SOLVEPNP_ITERATIVE)

            data = self.generate_expression( img_size )
            puppetry.sendSet({"inverse_kinematics":data})
            #print("") # uncomment this line when debugging at CLI

            #Show the frame we captured and draw the detection onto it.
            self.displayDetected( bgr_frame, face_landmarks, image_points )

            # Hit 'q' on the keyboard to quit!
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            
            # sleep for eventlet coroutines
            t1 = time.monotonic()
            compute_time = t1 - t0
            nap_duration = max(0.0, UPDATE_PERIOD - compute_time)
            eventlet.sleep(nap_duration)

        # Release handle to the webcam
        self.capture_device.release()
        cv2.destroyAllWindows()


def main():
    puppetry.start()
    face = Expression()
    face.main_loop()
    puppetry.stop()

if __name__ == "__main__":
    main()
