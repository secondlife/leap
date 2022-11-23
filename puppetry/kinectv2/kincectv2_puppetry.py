#!/usr/bin/env python3
"""\
@file kinectv2_puppetry.py

@brief experimental LEAP script to animate an avatar using a Kinect V2 sensor

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
Tell the viewer to launch it with the Advanced / Puppetry / Open Leap module command
The viewer will start this script in a side process and will
read messages from its stdout.

The joint data is a dictionary with the following format:
    data={"joint_name":{"type":[1.23,4.56,7.89]}, ...}
Where:
    joint_name = string recognized by viewer routine
    LLVOAvatar::getJoint(const std::string&),
        e.g. something like: "mWristLeft"
    type = "r" | "rotation", 'p' | 'position', or 's' 'scale'
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

'''

import copy
import ctypes
from enum import IntEnum
import eventlet
import glm
import math
import numpy as np
import quaternion
import os
from pykinect2 import PyKinectV2
from pykinect2.PyKinectV2 import *
from pykinect2 import PyKinectRuntime
import pygame
import sys
import _thread as thread
import time

import puppetry
from pygame_button import PYGButtonManager, PYGButton, PYGLogger

PYGLogger = puppetry.log

# To Do
# --------------------------------------------------
# Query and respond to messages for the sections of the skeleton to animate i.e. upper only, etc
#  - possibly make buttons for it in the Window
# Data smoothing
#




# Kinect camera coordinate frame:

#   0,0 .___________________.             turn(y)
#       |     Looking       |               |
#       | (*)    at     (x) |               @-nod(x)
#       |      Kinectv2     |              /
#       .___________________.           tilt(z)
#                          1080,1920

# The avatar's head coordinate frame:
#
#         ______       turn(z)
#        /o   o \       |
#       |   C    |      @-nod(Y)
#       |  ===   |     /
#        \______/   tilt(X)
#           |
#     R-+-+-+-+-+-L
#           |
#           |
#         +-@-+
#         |   |
#         +   +
#         |   |
#        /   /
#
#
#
#      z
#       (o)---y
#        |             -----+----+----+ mHandMiddle1,2,3Left
#        x             -----+----+----+ mHandRing1,2,3Left
#                      -----+----+----+ mHandPinky1,2,3Left
# mWristLeft -----+    -----+----+----+ mHandIndex1,2,3Left
#                      -----+----+----+ mHandThumb1,2,3Left

PI = math.pi            # yum
R2D = (180.0 / PI)      # radians to degree

PIO3 = PI/3             # Pi Over Three
MPIO3 = PI/-3           # Minus Pi Over Three

PIO4 = PI/4             # Pi Over Four
MPIO4 = PI/-4           # Minus Pi Over Four

Z_AXIS = glm.vec3(0.0, 0.0, 1.0)

FRAME_RATE = 10                         # updates per second
UPDATE_PERIOD = (1.0 / FRAME_RATE)      # interval sending updates to SL viewer


PYKINECT_2_SL_JOINTS = [
    'mPelvis',          # PyKinectV2.JointType_SpineBase = 0
    'mSpine2',          # PyKinectV2.JointType_SpineMid = 1
    'mNeck',            # PyKinectV2.JointType_Neck = 2
    'mHead',            # PyKinectV2.JointType_Head = 3
    'mShoulderLeft',    # PyKinectV2.JointType_ShoulderLeft = 4
    'mElbowLeft',       # PyKinectV2.JointType_ElbowLeft = 5
    'mWristLeft',       # PyKinectV2.JointType_WristLeft = 6
    'nobone',       # PyKinectV2.JointType_HandLeft = 7
    'mShoulderRight',   # PyKinectV2.JointType_ShoulderRight = 8
    'mElbowRight',      # PyKinectV2.JointType_ElbowRight = 9
    'mWristRight',      # PyKinectV2.JointType_WristRight = 10
    'nobone',       # PyKinectV2.JointType_HandRight = 11
    'mHipLeft',         # PyKinectV2.JointType_HipLeft = 12
    'mKneeLeft',        # PyKinectV2.JointType_KneeLeft = 13
    'mAnkleLeft',       # PyKinectV2.JointType_AnkleLeft = 14
    'mFootLeft',        # PyKinectV2.JointType_FootLeft = 15
    'mHipRight',        # PyKinectV2.JointType_HipRight = 16
    'mKneeRight',       # PyKinectV2.JointType_KneeRight = 17
    'mAnkleRight',      # PyKinectV2.JointType_AnkleRight = 18
    'mFootRight',       # PyKinectV2.JointType_FootRight = 19
    'collar',       # PyKinectV2.JointType_SpineShoulder = 20
    'nobone',       # PyKinectV2.JointType_HandTipLeft = 21
    'nobone',       # PyKinectV2.JointType_ThumbLeft = 22
    'nobone',       # PyKinectV2.JointType_HandTipRight = 23
    'nobone',       # PyKinectV2.JointType_ThumbRight = 24
]

# Used for logging
PYKINECT_2_NAME = [
    'SpineBase',     #  0
    'SpineMid',      #  1
    'Neck',          #  2
    'Head',          #  3
    'ShoulderLeft',  #  4
    'ElbowLeft',     #  5
    'WristLeft',     #  6
    'HandLeft',      #  7
    'ShoulderRight', #  8
    'ElbowRight',    #  9
    'WristRight',    # 10
    'HandRight',     # 11
    'HipLeft',       # 12
    'KneeLeft',      # 13
    'AnkleLeft',     # 14
    'FootLeft',      # 15
    'HipRight',      # 16
    'KneeRight',     # 17
    'AnkleRight',    # 18
    'FootRight',     # 19
    'SpineShoulder', # 20
    'HandTipLeft',   # 21
    'ThumbLeft',     # 22
    'HandTipRight',  # 23
    'ThumbRight',    # 24
]

# Application buttons
button_manager = None

# Main object for the application class
kinect_capture_app = None    #

# PyKinectV2.JointType_Count = 25


# -----------------------------------------------------------------------

# Cruft from example - needed?

# from avatar_skeleton.xml these are the "positions" of each joint in their parent-frame


# Not used currently
def getSLJointName(kinect_joint_index, side = 'right'):
    """ Given kinect joint, get the corresponding SL joint """
    sl_joint_name = PYKINECT_2_SL_JOINTS[kinect_joint_index]  # test was joint_index
    if sl_joint_name == 'nobone':
        sl_joint_name = None
    elif sl_joint_name == 'collar':
        if side == 'left':
            sl_joint_name = 'mCollarLeft'
        else:
            sl_joint_name = 'mCollarRight'

    return sl_joint_name


# -----------------------------------------------------------------------

def clamp(num, min_value, max_value):
    """ math """
    return max(min(num, max_value), min_value)

# -----------------------------------------------------------------------
# Main classes and code

# color for drawing the skeleton:
# also try "blue", "green", "orange", "purple", "yellow", "violet"
SKELETON_COLOR = pygame.color.THECOLORS["violet"]
HEAD_COLOR = pygame.color.THECOLORS["blue"]
HEAD_HEIGHT = 320
HEAD_WIDTH = 240

BONE_DRAW_WIDTH = 12
BONE_JOINT_DIAMETER = 16

BTN_X = 130
BTN_Y = 36
BTN_WIDTH = 240
BTN_HEIGHT = 50


TEXT_COLOR = pygame.color.THECOLORS["yellow"]
TEXT_COLOR_BG = pygame.color.THECOLORS["black"]
TEXT_FONT_SIZE = 28
TEXT_LINE_SPACE = TEXT_FONT_SIZE + 2
TEXTBOX_INDENT = 10
TEXTBOX_X = 10
TEXTBOX_Y = 142
TEXTBOX_W = 500

X_DEBUG_TEXT="xxxxxxxxx"

class MSG_LINE(IntEnum):
    TITLE = 0
    SHOULDER_L = 1
    SHOULDER_L_SL = 2
    ELBOW_L = 3
    ELBOW_L_SL = 4
    SHOULDER_R = 5
    SHOULDER_R_SL = 6
    ELBOW_R = 7
    ELBOW_R_SL = 8
    NECK = 9
    NECK_SL = 10
    NOISE = 11
    LINE_COUNT = 12

KINECT_COLOR_WIDTH = 1920
KINECT_COLOR_HEIGHT = 1080

# --------------------------------------------------

class KinectJointInfo(object):
    """ Simple container for Kinect joint info """
    def __init__(self, index):
        """ Empty constructor """
        self.index = index
        self.updateJoint(PyKinectV2.TrackingState_NotTracked, math.inf, math.inf)

    def updateJoint(self, state, x, y):
        """ figure out if we have valid data for this point """
        if math.isfinite(x) and math.isfinite(y) and state != PyKinectV2.TrackingState_NotTracked:
            self.valid = True       # Accept TrackingState_Inferred and TrackingState_Tracked if they have data
            self.x = float(x)
            self.y = float(y)
            self.y_flip = abs(KINECT_COLOR_HEIGHT - self.y)       # pre-calculate flipped Y so 0,0 is lower left
        else:
            self.valid = False
            self.x = None
            self.y = None
            self.y_flip = None

    def __str__(self):
        return '<KinectJointInfo x %r, y %r, y_flip %r, valid %r>' % (self.x, self.y, self.y_flip, self.valid)

    def __repr__(self):
        return self.__str__()

# --------------------------------------------------

# Button click callback functions
def toggle_setting(name):
    """ Button clicked to turn camera on and off """
    puppetry.log("Toggle %r button clicked" % name)
    if kinect_capture_app is not None:
        kinect_capture_app.toggle_setting(name)

# --------------------------------------------------


class SLPuppetRuntime(object):
    def __init__(self):
        pygame.init()

        # Used to manage how fast the screen updates
        self._clock = pygame.time.Clock()

        # Set the width and height of the screen [width, height]
        self._infoObject = pygame.display.Info()
        self._screen = pygame.display.set_mode((self._infoObject.current_w >> 1, self._infoObject.current_h >> 1),
                                               pygame.HWSURFACE|pygame.DOUBLEBUF|pygame.RESIZABLE, 32)
        self._mouse_scale_x = 0.5
        self._mouse_scale_y = 0.5
        self._camera_display = False
        self._debug_display = True
        self._log_joint_data = 0

        pygame.display.set_caption("Second Life Puppetry with Kinect v2")

        self._font = pygame.font.Font('freesansbold.ttf', TEXT_FONT_SIZE)

        # Loop until the user clicks the close button.
        self._done = False

        # Kinect runtime object, we want only color and body frames
        self._kinect = PyKinectRuntime.PyKinectRuntime(PyKinectV2.FrameSourceTypes_Color |
                                                        PyKinectV2.FrameSourceTypes_Depth |
                                                        PyKinectV2.FrameSourceTypes_Body)

        #self._kinect = PyKinectRuntime.PyKinectRuntime(PyKinectV2.FrameSourceTypes_Infrared | PyKinectV2.FrameSourceTypes_Body)

        # back buffer surface for getting Kinect color frames, 32bit color, width and height equal to the Kinect color frame size
        KINECT_COLOR_WIDTH = self._kinect.color_frame_desc.Width
        KINECT_COLOR_HEIGHT = self._kinect.color_frame_desc.Height
        self._frame_surface = pygame.Surface((KINECT_COLOR_WIDTH, KINECT_COLOR_HEIGHT), 0, 32)
        self._button_manager = PYGButtonManager(self._frame_surface)

        self._bodies = None          # skeleton data

        self._joints = []            # Extracted kinect data
        self._last_joints = []       # Previous data
        for i in range(PyKinectV2.JointType_Count):
            self._joints.append(KinectJointInfo(i))
            self._last_joints.append(KinectJointInfo(i))

        self._debug_lines = [X_DEBUG_TEXT for i in range(MSG_LINE.LINE_COUNT)]   # text status display in plug-in window
        self._noisy_data = 0

        self._last_ticks = pygame.time.get_ticks()

        self._button_manager.createButton('camera', 'Camera',
                    BTN_X, BTN_Y,              BTN_WIDTH, BTN_HEIGHT, toggle_setting)
        self._button_manager.createButton('debug', 'Info',
                    BTN_X, BTN_Y + BTN_HEIGHT, BTN_WIDTH, BTN_HEIGHT, toggle_setting)

    # --------------------------------------------------
    def toggle_setting(self, name):
        """ Button click callback: turn it on or off """
        if name == 'camera':
            self._camera_display = not self._camera_display
        elif name == 'debug':
            self._debug_display = not self._debug_display
        else:
            puppetry.log("*** Unexpected toggle_setting callback %r" % name)

    # --------------------------------------------------
    def draw_body_bone(self, color, start_joint_index, end_joint_index):
        """ Draw bone at start_joint_index to end_joint_index """
        start_joint = self._joints[start_joint_index]
        end_joint = self._joints[end_joint_index]

        if start_joint is None or end_joint is None:
            puppetry.log("None joints start %r end %r" % (start_joint is None, end_joint is None))

        # One of the joints is not valid - don't draw
        if start_joint.valid is False or end_joint.valid is False:
            #puppetry.log("Falsity! %r and %r" % (start_joint, end_joint))
            return

        # Draw line between joints
        try:
            # Have a start and end joint
            start_x = self._joints[start_joint_index].x
            start_y = self._joints[start_joint_index].y
            end_x = self._joints[end_joint_index].x
            end_y = self._joints[end_joint_index].y

            # Simple noise detection, looking for data jumps.  Need to
            # integrate this with dropping noisy sample in Puppetry, and
            # more investigation if data smoothing would help
            NOISE_LIMIT = 100
            last_joint = self._last_joints[start_joint_index]
            if last_joint is not None and last_joint.valid and \
                (abs(last_joint.x - start_x) > NOISE_LIMIT or \
                 abs(last_joint.y - start_y) > NOISE_LIMIT):
                self._noisy_data = self._noisy_data + 1   # count dropped data
                self._debug_lines[MSG_LINE.NOISE] = "Noise %r" % self._noisy_data
                #return

            # Save last position for this joint
            self._last_joints[start_joint_index] = self._joints[start_joint_index]

            pygame.draw.line(self._frame_surface, color, (start_x, start_y), (end_x, end_y), BONE_DRAW_WIDTH)
            pygame.draw.circle(self._frame_surface, color, (start_x, start_y), BONE_JOINT_DIAMETER)
        except Exception as ex: # need to catch here due to possible invalid positions (with inf)
            puppetry.log("Drawing exception %r: %r and %r" % (ex, start_joint, end_joint))
            pass


    # --------------------------------------------------
    def draw_head(self, color):
        """ Draw something vaguely head-like """

        # Must have valid data
        if not self._joints[PyKinectV2.JointType_Head].valid:
            return

        # Have a start and end joint
        center_x = self. _joints[PyKinectV2.JointType_Head].x
        center_y = self. _joints[PyKinectV2.JointType_Head].y

        try:        # Draw a shape
            head_rect = pygame.Rect(center_x - (HEAD_WIDTH/2), center_y - (HEAD_HEIGHT/2), HEAD_WIDTH, HEAD_HEIGHT)
            pygame.draw.ellipse(self._frame_surface, color, head_rect)
            #pygame.draw.circle(self._frame_surface, color, center, 100)
        except: # need to catch it due to possible invalid positions (with inf)
            pass

    # --------------------------------------------------
    def wipe_surface(self):
        """ Clear drawing surface (ugly yet simple way to hide video) """
        if not self._camera_display:
            self._frame_surface.fill((128,128,128))

    # --------------------------------------------------
    def draw_body(self):
        """ Draw stick figure """

        # Head
        self.draw_head(HEAD_COLOR)

        # Torso
        color = SKELETON_COLOR
        self.draw_body_bone(color, PyKinectV2.JointType_Head, PyKinectV2.JointType_Neck)
        self.draw_body_bone(color, PyKinectV2.JointType_Neck, PyKinectV2.JointType_SpineShoulder)
        self.draw_body_bone(color, PyKinectV2.JointType_SpineShoulder, PyKinectV2.JointType_SpineMid)
        self.draw_body_bone(color, PyKinectV2.JointType_SpineMid, PyKinectV2.JointType_SpineBase)
        self.draw_body_bone(color, PyKinectV2.JointType_SpineShoulder, PyKinectV2.JointType_ShoulderRight)
        self.draw_body_bone(color, PyKinectV2.JointType_SpineShoulder, PyKinectV2.JointType_ShoulderLeft)
        self.draw_body_bone(color, PyKinectV2.JointType_SpineBase, PyKinectV2.JointType_HipRight)
        self.draw_body_bone(color, PyKinectV2.JointType_SpineBase, PyKinectV2.JointType_HipLeft)

        # "blue", "green", "orange", "purple", "yellow", "violet"

        # Right Arm
        color = pygame.color.THECOLORS["green"]
        self.draw_body_bone(color, PyKinectV2.JointType_ShoulderRight, PyKinectV2.JointType_ElbowRight)
        self.draw_body_bone(color, PyKinectV2.JointType_ElbowRight, PyKinectV2.JointType_WristRight)
        self.draw_body_bone(color, PyKinectV2.JointType_WristRight, PyKinectV2.JointType_HandRight)
        self.draw_body_bone(color, PyKinectV2.JointType_HandRight, PyKinectV2.JointType_HandTipRight)
        self.draw_body_bone(color, PyKinectV2.JointType_WristRight, PyKinectV2.JointType_ThumbRight)

        # Left Arm
        color = pygame.color.THECOLORS["red"]
        self.draw_body_bone(color, PyKinectV2.JointType_ShoulderLeft, PyKinectV2.JointType_ElbowLeft)
        self.draw_body_bone(color, PyKinectV2.JointType_ElbowLeft, PyKinectV2.JointType_WristLeft)
        self.draw_body_bone(color, PyKinectV2.JointType_WristLeft, PyKinectV2.JointType_HandLeft)
        self.draw_body_bone(color, PyKinectV2.JointType_HandLeft, PyKinectV2.JointType_HandTipLeft)
        self.draw_body_bone(color, PyKinectV2.JointType_WristLeft, PyKinectV2.JointType_ThumbLeft)

        color = SKELETON_COLOR

        # Right Leg
        # self.draw_body_bone(color, PyKinectV2.JointType_HipRight, PyKinectV2.JointType_KneeRight)
        # self.draw_body_bone(color, PyKinectV2.JointType_KneeRight, PyKinectV2.JointType_AnkleRight)
        # self.draw_body_bone(color, PyKinectV2.JointType_AnkleRight, PyKinectV2.JointType_FootRight)

        # Left Leg
        # self.draw_body_bone(color, PyKinectV2.JointType_HipLeft, PyKinectV2.JointType_KneeLeft)
        # self.draw_body_bone(color, PyKinectV2.JointType_KneeLeft, PyKinectV2.JointType_AnkleLeft)
        # self.draw_body_bone(color, PyKinectV2.JointType_AnkleLeft, PyKinectV2.JointType_FootLeft)


    # --------------------------------------------------
    def draw_color_frame(self, frame, target_surface):
        target_surface.lock()
        address = self._kinect.surface_as_array(target_surface.get_buffer())
        ctypes.memmove(address, frame.ctypes.data, frame.size)
        del address
        target_surface.unlock()


    # --------------------------------------------------
    def draw_text_line(self, info_msg, indent, line_num):
        """ show a line of text """
        line_offset = TEXTBOX_Y + (TEXT_LINE_SPACE * line_num)    # extra +1 for label space
        indent = TEXTBOX_X + indent
        text = self._font.render(info_msg, True, TEXT_COLOR, TEXT_COLOR_BG)
        textRect = text.get_rect()    # create a rectangular object for the text surface object
        textRect.topleft = (indent, line_offset)  # set the center of the rectangular object.
        self._frame_surface.blit(text, textRect)


    # --------------------------------------------------
    def draw_debug_text(self):
        """ show some diagnostic info """
        if self._debug_display:
            line_num = 0
            indent = 0
            erase_rect = pygame.Rect(TEXTBOX_X, TEXTBOX_Y - 10, TEXTBOX_W,
                20 + (TEXT_LINE_SPACE * (1 + len(self._debug_lines))))
            pygame.draw.rect(self._frame_surface, TEXT_COLOR_BG, erase_rect)

            # Title line
            ticks =  pygame.time.get_ticks()
            self.draw_text_line("Puppetry - %4.0f ms frame" % (ticks - self._last_ticks), TEXTBOX_INDENT, MSG_LINE.TITLE)
            self._last_ticks = ticks

            for index, cur_line in enumerate(self._debug_lines):
                if cur_line != X_DEBUG_TEXT:
                    self.draw_text_line(cur_line, TEXTBOX_INDENT * 2, index)


    # --------------------------------------------------
    def getSafeJoint(self, joint_index, line_num):
        """ Extract and check data, return x and y (Y up) """
        cur_joint = self._joints[joint_index]
        if cur_joint is None or not cur_joint.valid:
            #puppetry.log("Missing joint data for pivot index %r" % pivot)
            self._debug_lines[line_num] = "No joint data %s" % PYKINECT_2_NAME[joint_index]
            return None, None

        return cur_joint.x, cur_joint.y_flip      # Y points up


    # --------------------------------------------------
    def findKinectJointAngle(self, root, pivot, far_end, line_num):
        """ Figure out angle between root, joint and far end points
            e.g.  an elbow pivot angle with shoulder and wrist position
            Currently using flattened 2d math to get 1 angle
        """
        angle = None

        root_x, root_y = self.getSafeJoint(root, line_num)
        if root_x is None:
            return None

        pivot_x, pivot_y = self.getSafeJoint(pivot, line_num)
        if pivot_x is None:
            return None

        far_end_x, far_end_y = self.getSafeJoint(far_end, line_num)
        if far_end_x is None:
            return None

        # Compute the angle at pivot in the triangle made by the 3 points
        p2r_x = pivot_x - root_x      # pivot to root
        p2r_y = pivot_y - root_y
        p2f_x = pivot_x - far_end_x   # pivot to far end
        p2f_y = pivot_y - far_end_y

        numer = (p2r_x * p2f_x) + (p2r_y * p2f_y)
        denom = math.sqrt( ((p2r_x * p2r_x) + (p2r_y * p2r_y)) * ((p2f_x * p2f_x) + (p2f_y * p2f_y)) )
        if denom < 0.001:
            angle = PI / 2
        else:
            angle = math.acos( numer/denom )

        # The above angle is the interior angle, but SL rotattion is the exterior
        slangle = PI - angle

        # Check for clockwise or counter-clockwise winding, and adjust the sign accordingly
        root_pivot_edge = (pivot_x - root_x) * (pivot_y + root_y)
        pivot_far_edge = (far_end_x - pivot_x) * (far_end_y + pivot_y)
        far_root_edge = (root_x - far_end_x) * (root_y + far_end_y)
        if (root_pivot_edge + pivot_far_edge + far_root_edge) < 0:
            slangle = slangle * -1.0

        if math.isfinite(slangle):
            self._debug_lines[line_num] = "%s angle %3.3f" % (PYKINECT_2_NAME[pivot], slangle)
        else:
            slangle = None
            root_joint = self._joints[root]
            pivot_joint = self._joints[pivot]
            far_end_joint = self._joints[far_end]
            self._debug_lines[line_num] = "%s angle NaN" % PYKINECT_2_NAME[pivot]
            puppetry.log("Unexpected NaN angle found for %r : %r %r %r" %
                (PYKINECT_2_NAME[pivot], root_joint, pivot_joint, far_end_joint))

        return slangle


    # --------------------------------------------------
    def extractJoints(self, body):
        """ Extract joint data that we care about.  Things just seem to work
            better doing this - pull the data at one point and process it """

        # Logs a snapshot of joint data once in a while
        do_logging = False
        self._log_joint_data = self._log_joint_data + 1
        if self._log_joint_data > (60 * 1/UPDATE_PERIOD):    # 60 second interval
            self._log_joint_data = 0
            do_logging = True

        # extract the data we care about for all joints
        kjoints = body.joints
        color_points = self._kinect.body_joints_to_color_space(kjoints)  # convert joint coordinates to color space
        for joint_index in range(PyKinectV2.JointType_Count):
            cur_kjoint = kjoints[joint_index]
            cur_color_point = color_points[joint_index]
            self._joints[joint_index].updateJoint(cur_kjoint.TrackingState,
                                       cur_color_point.x,
                                       cur_color_point.y)
            if do_logging:
                log_msg = "joint %r : %r" % (PYKINECT_2_NAME[joint_index], self._joints[joint_index])
                puppetry.log(log_msg)


    # --------------------------------------------------
    def calcLimbData2DLeft(self):
        """ Create data for a joint sequence along a limb """
        # Look for tracked bones, and gather data.  Use simple 2d projection,
        #  assuming human is facing the Kinect camera
        limb_data = {}

        # Force T pose, then try to manipulate the elbow
        limb_data['mCollarLeft'] = {'r': [0.0, 0.0, 0.0]}
        limb_data['mShoulderLeft'] = {'r': [0.0, 0.0, 0.0]}
        limb_data['mElbowLeft'] = {'r': [0.0, 0.0, 0.0]}
        limb_data['mWristLeft'] = {'r': [0.0, MPIO4, 0.0]}   # palm to camera

        slangle = self.findKinectJointAngle(PyKinectV2.JointType_SpineShoulder,
                                            PyKinectV2.JointType_ShoulderLeft,
                                            PyKinectV2.JointType_ElbowLeft, MSG_LINE.SHOULDER_L)
        if slangle is not None:     # set left shoulder rotation
            slangle = 0.5 * slangle                 # why does this make things right?
            slangle = clamp(slangle, MPIO3, PIO3)
            limb_data['mShoulderLeft'] = {'r' : [slangle, 0.0, 0.0]}
            self._debug_lines[MSG_LINE.SHOULDER_L_SL] = "mShoulderLeft  %1.2f" % slangle
        else:
            self._debug_lines[MSG_LINE.SHOULDER_L_SL] = "No mShoulderLeft"

        slangle = self.findKinectJointAngle(PyKinectV2.JointType_ShoulderLeft,
                                            PyKinectV2.JointType_ElbowLeft,
                                            PyKinectV2.JointType_WristLeft, MSG_LINE.ELBOW_L)
        if slangle is not None:   # set left elbow rotation
            slangle = 0.5 * slangle                 # why does this make things right?
            slangle = clamp(slangle, MPIO3, PIO3)
            limb_data['mElbowLeft'] = {'r' : [slangle, 0.0, 0.0]}
            self._debug_lines[MSG_LINE.ELBOW_L_SL] = "mElbowLeft  %1.2f" % (limb_data['mElbowLeft']['r'][0])
        else:
            self._debug_lines[MSG_LINE.ELBOW_L_SL] = "No mElbowLeft"

        #puppetry.log("left data %r" % (limb_data))
        return limb_data

    # --------------------------------------------------
    def calcLimbData2DRight(self):
        """ Create data for a joint sequence along a limb """
        # Look for tracked bones, and gather data.  Use simple 2d projection,
        #  assuing human is facing the Kinect camera
        limb_data = {}

        # Force T pose, then try to manipulate the elbow
        limb_data['mCollarRight'] = {'r': [0.0, 0.0, 0.0]}      # T pose
        limb_data['mShoulderRight'] = {'r': [0.0, 0.0, 0.0]}
        limb_data['mElbowRight'] = {'r': [0.0, 0.0, 0.0]}
        limb_data['mWristRight'] = {'r': [0.0, MPIO4, 0.0]}    # palm to camera

        # Get shoulder kinect angle
        slangle = self.findKinectJointAngle(PyKinectV2.JointType_SpineShoulder,
                                            PyKinectV2.JointType_ShoulderRight,
                                            PyKinectV2.JointType_ElbowRight, MSG_LINE.SHOULDER_R)
        if slangle is not None:   # set right shoulder rotation
            slangle = 0.5 * slangle                 # why does this make things right?
            slangle = clamp(slangle, MPIO3, PIO3)
            limb_data['mShoulderRight'] = {'r' : [slangle, 0.0, 0.0]}
            self._debug_lines[MSG_LINE.SHOULDER_R_SL] = "mShoulderRight %1.2f" % limb_data['mShoulderRight']['r'][0]
        else:
            self._debug_lines[MSG_LINE.SHOULDER_R_SL] = "No mShoulderRight"

        # Get elbow kinect angle
        slangle = self.findKinectJointAngle(PyKinectV2.JointType_ShoulderRight,
                                            PyKinectV2.JointType_ElbowRight,
                                            PyKinectV2.JointType_WristRight, MSG_LINE.ELBOW_R)
        if slangle is not None:   # set right elbow rotation
            slangle = 0.5 * slangle                 # why does this make things right?
            slangle = clamp(slangle, MPIO3, 0.0)
            limb_data['mElbowRight'] = {'r' : [slangle, 0.0, 0.0]}
            self._debug_lines[MSG_LINE.ELBOW_R_SL] = "mElbowRight %1.2f" % (limb_data['mElbowRight']['r'][0])
        else:
            self._debug_lines[MSG_LINE.ELBOW_R_SL] = "No mElbowRight"

        #puppetry.log("limb_data %r" % (limb_data))
        return limb_data

    # --------------------------------------------------
    def calcLimbData2DCenter(self):
        """ Create data for a joint sequence along a limb """
        # Look for tracked bones, and gather data.  Use simple 2d projection,
        #  assuing human is facing the Kinect camera
        limb_data = {}

        # Default pose
        limb_data['mNeck'] = {'r': [0.0, 0.0, 0.0]}
        limb_data['mHead'] = {'r': [0.0, 0.0, 0.0]}

        slangle = self.findKinectJointAngle(PyKinectV2.JointType_SpineShoulder,
                                           PyKinectV2.JointType_Neck,
                                           PyKinectV2.JointType_Head, MSG_LINE.NECK)

        if slangle is not None:   # add "rotation"
            slangle = clamp(slangle, -0.2, 0.2)
            limb_data['mNeck'] = {'r' : [slangle, 0.0, 0.0]}
            self._debug_lines[MSG_LINE.NECK_SL] = "mNeck  %1.2f" % (limb_data['mNeck']['r'][0])
        else:
            self._debug_lines[MSG_LINE.NECK_SL] = "No mNeck"

        #puppetry.log("limb_data %r" % (limb_data))
        return limb_data


    # --------------------------------------------------
    def computePuppetryData(self):
        """ Make SL puppetry data """
        puppet_data = {}
        sub_data = self.calcLimbData2DRight()
        puppet_data.update(sub_data)
        sub_data = self.calcLimbData2DLeft()
        puppet_data.update(sub_data)
        sub_data = self.calcLimbData2DCenter()
        puppet_data.update(sub_data)

        #puppetry.log("Created %r" % puppet_data)
        return puppet_data


    # --------------------------------------------------
    def run(self):
        """ Main Program Loop """
        update_time = time.monotonic() + UPDATE_PERIOD
        frame_time = UPDATE_PERIOD     # desired seconds per frame, match data rate for sending to SL
        while (not self._done) and puppetry.isRunning():
            # Main event loop
            start_time = time.monotonic()
            for event in pygame.event.get(): # User did something
                if event.type == pygame.QUIT: # If user clicked close
                    self._done = True # Flag that we are done so we exit this loop

                elif event.type == pygame.VIDEORESIZE: # window resized
                    new_size_x, new_size_y = event.dict['size']
                    self._screen = pygame.display.set_mode((new_size_x, new_size_y),
                                               pygame.HWSURFACE|pygame.DOUBLEBUF|pygame.RESIZABLE, 32)
                    self._mouse_scale_x = new_size_x / KINECT_COLOR_WIDTH
                    self._mouse_scale_y = new_size_y / KINECT_COLOR_WIDTH

            # Getting frames and drawing
            # Woohoo! We've got a color frame! Let's fill out back buffer surface with frame's data
            if self._kinect.has_new_color_frame():
                frame = self._kinect.get_last_color_frame()
                self.draw_color_frame(frame, self._frame_surface)
                frame = None

            # Have a body frame, so get skeletons
            if self._kinect.has_new_body_frame():
                self._bodies = self._kinect.get_last_body_frame()

            # draw skeletons to _frame_surface
            body_index = -1
            if self._bodies is not None:
                self.wipe_surface()
                for i in range(0, self._kinect.max_body_count):
                    body = self._bodies.bodies[i]
                    if not body.is_tracked:
                        continue

                    self.extractJoints(body)

                    self.draw_body()
                    body_index = i

                    break    # Only use the 1st body since we can only puppet one avatar

                # Do SL puppetry if enough time has passed
                now = time.monotonic()
                if body_index >= 0 and now > update_time:
                    update_time = now + UPDATE_PERIOD
                    data = self.computePuppetryData()
                    if data:
                        puppetry.sendSet({"j":data})  # "joint_state"
                        #puppetry.log("sent %r" % data)

            # Get the rodent and scale to image (not screen) size
            mouse_pos = list(pygame.mouse.get_pos())
            mouse_pos[0] = mouse_pos[0] / self._mouse_scale_x
            mouse_pos[1] = mouse_pos[1] / self._mouse_scale_y

            # Do the buttons
            self._button_manager.idle(mouse_pos)

            # Debug text drawing
            self.draw_debug_text()

            # copy back buffer surface pixels to the screen, resize it if needed and keep aspect ratio
            # (screen size may be different from Kinect's color frame size)
            h_to_w = float(self._frame_surface.get_height()) / self._frame_surface.get_width()
            target_height = int(h_to_w * self._screen.get_width())
            surface_to_draw = pygame.transform.scale(self._frame_surface, (self._screen.get_width(), target_height))
            self._screen.blit(surface_to_draw, (0,0))
            surface_to_draw = None
            pygame.display.update()

            # Go ahead and update the screen with what we've drawn.
            pygame.display.flip()

            duration = (time.monotonic() - start_time) / 1000.0
            sleepy_time = clamp(frame_time - duration, 0.05, frame_time)
            eventlet.sleep(sleepy_time)       # Let other eventlet coroutines have time

            self._clock.tick(20)      # Limit frames per second too

        # Close our Kinect sensor, close the window and quit.
        self._kinect.close()
        pygame.quit()


# -----------------------------------------------------------------------
def kinect_puppetry():
    """ Main module run in eventlet """
    global kinect_capture_app
    kinect_capture_app = SLPuppetRuntime()
    kinect_capture_app.run()


#puppetry.setLogLevel(logging.DEBUG)


# hun? from pygame setup
__main__ = "Kinect v2 Puppetry"


# start the real work
puppetry.start()
spinner = eventlet.spawn(kinect_puppetry)

while puppetry.isRunning():
    eventlet.sleep(0.2)

# cleanup
spinner.wait()