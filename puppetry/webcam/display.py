"""\
@file display.py
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

import cv2
import numpy as np
import time

import puppetry

# color = (blue, green, red)
BLUE = (255,0,0)
GREEN = (0,255,0)
RED = (0,0,255)
CYAN = (255,255,0)
MAGENTA = (255,0,255)
YELLOW = (0,255,255)
ORANGE = (120,160,255)

DARK_BLUE = (139,0,0)
DARK_GREEN = (0,139,0)
DARK_RED = (0,0,139)
DARK_CYAN = (100,100,0)
DARK_MAGENTA = (100,0, 100)
DARK_YELLOW = (0,100,100)
DARK_ORANGE = (60,80,128)

WHITE = (255,255,255)
LIGHT_GRAY = (186,186,186)
DARK_GRAY = (64,64,64)
BLACK = (0,0,0)

WINDOW_NAME = "Image"

class Display:
    '''
        Handles displaying the capture from the camera and
        any overlays we wish to apply.
    '''

    def __init__(self):
        self.display = True         #Master control
        self.dimensions = None #[ 640, 400 ] #Target window size. None is full
        self.display_video = True   #Display what the camera sees
        self.display_face_pts = True #Show points on the face.
        self.display_fps      = True #Show the estimated FPS of tracking
        self.mirror = False          #Flip display horizontally
        self.size = None            #The actual display size, set per frame
        self.image = None           #The image to display.
        self.aspect_ratio = None
        try:
            cv2.namedWindow(WINDOW_NAME)  # Create a window.   This is initially blank, but shows the user something is going on
        except cv2.error as excp:
            puppetry.log("cv2 exception creating window: %s" % str(excp))

    def prep_output(self, bgr_image):
        '''Prepare the next frame for display.'''

        if not self.display:    #Display disabled. Done
            return

        self.image = None

        self.size = [0,0]
        if self.dimensions is None:
            self.size[1], self.size[0], _ = bgr_image.shape
            self.aspect_ratio = self.size[0] / self.size[1]
        else:
            self.size = self.dimensions

        if self.display_video:  #Show the video image captured
            if self.dimensions is None:
                self.image = bgr_image
            else:
                dim = (self.size[0], self.size[1])
                try:
                    self.image = cv2.resize(bgr_image, dim, \
                                interpolation = cv2.INTER_NEAREST)
                except cv2.error as excp:
                    puppetry.log("cv2 exception resizing image: %s" % str(excp))

        else:
            color = BLACK
            self.image = np.full((self.size[1], self.size[0], 3), \
                    color, dtype=np.uint8)

    def label_point(self, id, location):
        '''Print point labels'''
        font = cv2.FONT_HERSHEY_SIMPLEX
        location = (50, 50)

        fontScale = 0.25 # fontScale
        color = GREEN
        thickness = 2 # Line thickness of 2 px

        # Using cv2.putText() method
        try:
            cv2.putText(self.image, str(id), location, font,
                               fontScale, color, thickness, cv2.LINE_AA)
        except cv2.error as excp:
            puppetry.log("cv2 exception drawing text: %s" % str(excp))

    def draw_landmarks(self, landmarks, color=MAGENTA):
        '''Display the landmark set.'''

        if not self.display:
            return 0

        if landmarks is None:
            return 0

        #Draw the points on the face
        i=0
        landmark = None
        location = None
        try:
            for landmark in landmarks.landmark:
                location = ( int(landmark.x * self.size[0]), \
                             int(landmark.y * self.size[1]) )

                cv2.circle(self.image, location, 2, color, -1)
                i += 1
        except OverflowError as excp:
            puppetry.log("OverflowError exception drawing landmark point: %d" % (str(excp), i))
            return 0
        except TypeError as excp:
            puppetry.log("TypeError %s drawing landmark point: %d location %r" % (str(excp), i, location))
            return 0
        except ValueError as excp:
            puppetry.log("ValueError exception %s drawing landmark point: %d" % (str(excp), i))
            return 0
        except cv2.error as excp:
            puppetry.log("cv2 exception %s drawing landmark point: %d location %r" % (str(excp), i, location))
            return 0
        # Successful
        return i

    def draw_all_points(self, points, orientation_landmarks=None, rect_landmarks=None):
        '''Display the points for this landmark set.'''

        if not self.display_face_pts or \
           not self.display:
            return 0

        #Draw the points on the face
        i=0
        point = None
        location = None
        try:
            for point in points:
                location = ( int(point[0] * self.size[0]), \
                             int(point[1] * self.size[1]) )

                #self.label_point( i, location)
                color = CYAN

                if orientation_landmarks is not None:
                    if i in orientation_landmarks:
                        color = YELLOW
                    elif i in rect_landmarks:
                        color = RED
                
                cv2.circle(self.image, location, 2, color, -1)
                i += 1
        except OverflowError as excp:
            puppetry.log("OverflowError exception drawing landmark points: %s" % (str(excp), point))
            return 0
        except TypeError as excp:
            puppetry.log("TypeError %s drawing landmark point: %r location %r size %r" % (str(excp), point, location))
            return 0
        except ValueError as excp:
            puppetry.log("ValueError exception %s drawing landmark point: %r" % (str(excp), point))
            return 0
        except cv2.error as excp:
            puppetry.log("cv2 exception %s drawing landmark point: %r location %r" % (str(excp), point, location))
            return 0
        # Successful
        return i


    def draw_perpendicular(self, point, rotation, position, camera):
        '''Draws a line perpendicular to a point'''

        if not self.display_face_pts or \
           not self.display:
            return

        # Project a 3D point (0, 0, 1000.0) onto the image plane.
        # We use this to draw a line sticking out of the nose
        try:
            pinocchio = 0.1 * self.size[0]
            (nose_end_point2D, _) = cv2.projectPoints( \
                                    np.array([(0.0, 0.0, pinocchio)]), \
                                    rotation, \
                                    position, \
                                    camera.matrix, \
                                    camera.dist_coeffs)

            point1 = ( int(point[0]), \
                       int(point[1]))
            point2 = ( int(nose_end_point2D[0][0][0]), \
                            int(nose_end_point2D[0][0][1]))

            color = RED
            cv2.line(self.image, point1, point2, color, 2)

        except cv2.error as excp:
            puppetry.log("cv2 exception in draw_perpendicular(): %s" % str(excp))

    def erase_image(self):
        ''' clear the display '''

        try:
            color = DARK_GRAY
            erase_size = (640,480)
            if self.size is not None:
                erase_size = (self.size[0], self.size[1])
            puppetry.log("erase rect %r %r" % erase_size)
            cv2.rectangle(self.image, (0,0), erase_size, color, -1)
        except cv2.error as excp:
            # just log it, doesn't have to be fatal
            puppetry.log("cv2 exception %s" % str(excp))

    def do_display(self, start_time):
        '''Display the frame'''
        if self.display:
            try:
                if self.mirror:
                    self.image = cv2.flip(self.image, 1)

                if self.display_fps:
                    # can get a div-by-zero error here if there's no image
                    display_duration = max(0.001, time.time() - start_time)
                    fps = 1 / display_duration
                    cv2.putText(self.image, f'FPS:{int(fps)}', (20, 70), \
                        cv2.FONT_HERSHEY_SIMPLEX, 1, GREEN, 2)

                x=0
                y=0
                if self.image is not None:
                    y,x, _ = self.image.shape

                if x>0 and y>0:
                    cv2.imshow(WINDOW_NAME, self.image)
            except cv2.error as excp:
                # to do - better error handling.   Window will come
                # up with a grey empty screen.   If we exit with the exception,
                # the viewer just has nothing happening - no feedback.
                #puppetry.log("cv2 exception %s" % str(excp))
                pass

