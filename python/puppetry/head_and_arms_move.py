#!/usr/bin/env python3
"""\
@file head_and_arms.py
@brief simple LEAP script to move the avatar

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
head_and_arms_move.py -- use IK to animate the head and arms

Run this script via viewer menu...
    Advanced --> Puppetry --> Launch LEAP plug-in...
This script uses the LEAP framework for sending messages to the viewer.
The joint data is a dictionary with the following format:
    data={"joint_name":{"type":[1.23,4.56,7.89]}, ...}
Where:
    joint_name = string recognized by LLVOAvatar::getJoint(const std::string&),
        e.g. something like: "mWristLeft"
    type = "local_rot" | "rot" | "pos" | "scale"
    type's value = array of three floats (e.g. [x,y,z])
Multiple joints can be combined into the same dictionary.

Note: When you test this script at the command line it will block
because the leap.py framework is waiting for the initial message
from the viewer.  To unblock the system paste the following
string into the script's stdin:

119:{'data':{'command':'18ce5015-b651-1d2e-2470-0de841fd3635','features':{}},'pump':'54481a53-c41f-4fc2-606e-516daed03636'}

Also, for more readable text with newlines between messages
uncomment the print("") line in the main loop below.
'''

import eventlet
import glm
import logging
import math
import time

import puppetry

# The avatar's coordinate frame:
#             ___
#            /o o\
#            \___/
#              |
#  R o--+--+-+ | +-+--+--o L
#              +
#              |
#              +         z
#              |         |
#            +-@-+       @--y
#            |   |      /
#            +   +     x
#            |   |
#            |   |
#           /   /
#
# Puppetry expects position data to be in the normalized pelvis-relative frame
# where 2.0 is the effective "arm span" of the avatar (e.g. the distance from
# the "end" of one wrist bone to the other).
#
# In this space the approximate pelvise-relative positions of significant Joint
# ends are as follows:
#
# end_of_head = [ -0.0323109, 0, 0.963779 ]
# tip_of_chest = [ -0.020593, 0, 0.400766 ]
# end_of_shoulder_left = [ -0.0497143, 0.610328, 0.629576 ]
# end_of_elbow_left = [ -0.0497143, 0.967967, 0.629576 ]
# end_of_wrist_left = [ -0.0497143, 1, 0.629576 ]
# end_of_shoulder_right = [ -0.0497143, -0.610328, 0.629576 ]
# end_of_elbow_right = [ -0.0497143, -0.967967, 0.629576 ]
# end_of_wrist_right = [ -0.0497143, -1, 0.629576 ]

orbit_radius = 0.236
orbit_period = 8.0
wave_speed = 2.0 * math.pi / orbit_period

# head will wag its local rot
head_wag_amplitude = 0.1 * math.pi
head_wag_period = orbit_period / 4.0
head_wag_wave_speed = 2.0 * math.pi / head_wag_period

update_period = 0.1

WRIST_X = 0.0
WRIST_Y = 1.0
WRIST_Z = 0.63

HEAD_X = -0.0323
HEAD_Y = 0.0
HEAD_Z = 0.964

# we will move each arm in a circle:
# compute circle center, axis,
# and planar components (up and in)
head = glm.vec3(HEAD_X, HEAD_Y, HEAD_Z)
neck = glm.vec3(0.0, 0.0, WRIST_Z)
up_axis = glm.vec3(0.0, 0.0, 1.0)

# pull the circle closer to the body a little bit
left_center = glm.vec3(orbit_radius, 0.8 * WRIST_Y, 1.0 * WRIST_Z)
left_axis = glm.normalize(left_center - neck)
left_vertical = glm.normalize(glm.cross(left_axis, glm.cross(up_axis, left_axis)))
left_horizontal = glm.normalize(glm.cross(left_axis, left_vertical))

right_center = glm.vec3(WRIST_X, -0.8 * WRIST_Y, 1.0 * WRIST_Z)
right_axis = glm.normalize(right_center - neck)
right_vertical = glm.normalize(glm.cross(right_axis, glm.cross(up_axis, right_axis)))
right_horizontal = glm.normalize(glm.cross(right_vertical, right_axis))


t0 = time.monotonic()
t = 0.0

def computeData(time_step):
    global t
    t += time_step
    # cycle t by orbit_period
    # to avoid floating point error after running several days
    if t > orbit_period or t < -orbit_period:
        t -= int(t / orbit_period) * orbit_period

    # compute the sinusoidal components
    theta = t * wave_speed
    s = math.sin(theta)
    c = math.cos(theta)

    # compute the circle positions
    left = left_center + (orbit_radius * s) * left_vertical + (orbit_radius * c) * left_horizontal

    # compue left hand rotation:
    # we will point the wrist bone along the axis
    # from shoulder to wrist, with palm facing downward
    left_lever = glm.normalize(left - neck)
    y_axis = glm.vec3(0.0, 1.0, 0.0)
    left_pivot = glm.normalize(glm.cross(left_lever, y_axis))
    real_part = glm.dot(left_lever, y_axis)
    imaginary_coef = - math.sqrt(1.0 - real_part * real_part)
    left_q = glm.quat(real_part, imaginary_coef * left_pivot.x, imaginary_coef * left_pivot.y, imaginary_coef * left_pivot.z)

    # Note: want right to be out of phase by pi, hence negate components
    right = right_center - (orbit_radius * s) * right_vertical - (orbit_radius * c) * right_horizontal

    # orbit the head position in a little circle
    head_orbit_radius = 0.08
    head_left = glm.vec3(0.0, 1.0, 0.0)
    head_forward = glm.vec3(1.0, 0.0, 0.0)
    head = 1.1* glm.vec3(HEAD_X, HEAD_Y, HEAD_Z) + (head_orbit_radius * s) * head_left + (head_orbit_radius * c) * head_forward

    # wag the head using local orientation
    head_wag = head_wag_amplitude * math.sin(t * head_wag_wave_speed)
    head_rot = glm.quat(math.cos(0.5 * head_wag), 0.0, 0.0, math.sin(0.5 * head_wag))

    # assemble the message
    # Note: we're updating three Joints at once in distinct ways:
    #
    #   The end of the left wrist gets a position and orientation in pelvis frame
    #
    #   The end of the right elbow (e.g. the end of the forearm or tip of wrist)
    #   gets a position in the pelvis frame, but no orientation so it just keeps
    #   whatever local orientation supplied by other animations.
    #
    #   The head gets a position and a local orientation relative to parent-local
    #
    data = {
        'mWristLeft':{'pos':[left.x, left.y, left.z],'rot':puppetry.packedQuaternion(left_q)},
        'mElbowRight':{'pos':[right.x, right.y, right.z]},
        'mHead':{'pos':[head.x, head.y, head.z], 'local_rot':puppetry.packedQuaternion(head_rot)}
    }
    return data

def spin():
    t0 = time.monotonic()
    delta_time = update_period
    while puppetry.isRunning():
        # sleep to yield to other eventlet coroutines
        eventlet.sleep(max(0.0, 2 * update_period - delta_time))
        t1 = time.monotonic()
        delta_time = t1 - t0
        t0 = t1
        data = computeData(delta_time)
        puppetry.sendPuppetryData(data)
        #print("") # uncomment this when debugging at command-line

puppetry.setLogLevel(logging.DEBUG)
puppetry.start()

# spin the animation
spinner = eventlet.spawn(spin)

# loop the UI until puppetry is stopped
while puppetry.isRunning():
    eventlet.sleep(0.2)

# cleanup
spinner.wait()

