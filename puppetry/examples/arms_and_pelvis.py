#!/usr/bin/env python3
"""\
@file arms_and_pelvis.py
@brief simple LEAP script to demonstraint movable pelvis

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

Run this script via viewer menu...
    Advanced --> Puppetry --> Launch LEAP plug-in...

This script uses the LEAP framework for sending messages to the viewer.

Typically you just want to send a "set" command:
    puppetry.sendSet(data)

The 'set' data is a dictionary with the following format:
    data={"inverse_kinematics":{"joint_name":{"type":[1.23,4.56,7.89] ,...} ,...},
          "joint_state":{"joint_name":{"type":[1.23,4.56,7.89] ,...} ,...}}
Where:
    'inverse_kinematics' for specifying avatar-frame target transforms
    'joint_state' for specifying parent-frame joint transforms
        alternatively can use terse format: 'i' instead of 'inverse_kinematics' and 'j' instead of 'joint_state'

    'joint_name' = string recognized by LLVOAvatar::getJoint(const std::string&),
        e.g. something like: "mWristLeft"

    'type' = "rotation" | "position" | "scale"
        alternatively can use terse format: 'r', 'p', and 's'

    type's value = array of three floats (e.g. [x,y,z])
'''

import logging
import math
import sys
import time

import eventlet
import glm
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
# In this space the approximate pelvis-relative positions of significant Joint
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

orbit_radius = 0.0
orbit_period = 8.0
wave_speed = 2.0 * math.pi / orbit_period

update_period = 0.1

WRIST_X = 0.3
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
left_center = glm.vec3(WRIST_X, 0.5 * WRIST_Y, 1.0 * WRIST_Z)
left_axis = glm.normalize(left_center - neck)
left_vertical = glm.normalize(glm.cross(left_axis, glm.cross(up_axis, left_axis)))
left_horizontal = glm.normalize(glm.cross(left_axis, left_vertical))

right_center = glm.vec3(WRIST_X, -0.5 * WRIST_Y, 1.0 * WRIST_Z)
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
    left = left_center

    # compute an avatar-frame orientation of the left hand
    # to bring palm forward, fingers up
    angle = math.pi / 4.0
    s_angle = math.sin(angle)
    c_angle = math.cos(angle)
    q_y = glm.quat(s_angle, c_angle, 0.0, 0.0)
    q_z = glm.quat(s_angle, 0.0, 0.0, -c_angle)
    left_q = q_z * q_y

    # similarly for right hand
    q_y = glm.quat(s_angle, -c_angle, 0.0, 0.0)
    q_z = glm.quat(s_angle, 0.0, 0.0, c_angle)
    right_q = q_z * q_y

    # Note: want right to be out of phase by pi, hence negate components
    right = right_center - (orbit_radius * s) * right_vertical - (orbit_radius * c) * right_horizontal
    right = right_center

    pelvis_orbit_radius = 0.2
    left_direction = glm.vec3(0.0, 1.0, 0.0)

    # custom vertical adjustment to keep feet above ground
    up_direction = glm.vec3(0.0, 0.0, 1.0)

    #pelvis_orbit = (pelvis_orbit_radius * s) * left_direction + 0.07 * up_direction
    pelvis_orbit = (pelvis_orbit_radius * s) * left_direction

    # assemble the message
    # Note: we're using kinematics to place the right and left hands in the avatar-frame
    # and we're slamming the pelvis position in its parent-frame (however the parent-frame
    # of the pelvis is the avatar-frame)
    #
    data = {
        'inverse_kinematics': {
            'mWristLeft':{'p':[left.x, left.y, left.z],'r':puppetry.packedQuaternion(left_q)},
            'mWristRight':{'p':[right.x, right.y, right.z],'r':puppetry.packedQuaternion(right_q)} },
        'joint_state': {
            'mPelvis':{'p':[pelvis_orbit.x, pelvis_orbit.y, pelvis_orbit.z]}}
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
        puppetry.sendSet(data)
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

