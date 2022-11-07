#!/usr/bin/env python3
"""
Simple LEAP script to move the avatar
"""

'''
arm_wave.py -- use IK to animate the arm like it is waving hello/goodbye

Run this script via viewer menu...
    Advanced --> Puppetry --> Launch LEAP plug-in...
This script uses the LEAP framework for sending messages to the viewer.
The joint data is a dictionary with the following format:
    data={"joint_name":{"type":[1.23,4.56,7.89]}, ...}
Where:
    joint_name = string recognized by LLVOAvatar::getJoint(const std::string&),
        e.g. something like: "mWristLeft"
    type = "rot" | "pos" | "scale"
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

import logging
import math
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
#
# Which means... the forearm has a normalized length of approximately 0.3576
# in the normalized space.

arm = 'left'
#arm = 'right'

orbit_period = 8.0
wave_speed = 2.0 * math.pi / orbit_period
update_period = 0.1

# elbow_tip is the same as shoulder_end
elbow_tip = glm.vec3(-0.0497143, 0.610328, 0.629576)
forearm_length = 0.3576

y_axis = glm.vec3(0.0, 1.0, 0.0)
z_axis = glm.vec3(0.0, 0.0, 1.0)

t0 = time.monotonic()
t = 0.0

def computeData(time_step):
    global t
    t += time_step
    # cycle t by orbit_period
    # to avoid floating point error after running several days
    if t > orbit_period or t < -orbit_period:
        t -= int(t / orbit_period) * orbit_period

    # compute wrist_tip in pelvis-frame
    theta = t * wave_speed
    s = abs(math.sin(theta))
    c = abs(math.cos(theta))
    wrist_tip = elbow_tip + forearm_length * (c * y_axis + s * z_axis)

    # remember: the 'pos' always refers to the 'end' of the bone
    # in this case it is the elbow whose 'end' is also the 'tip' of the wrist
    if arm == 'right':
        wrist_tip.y = - wrist_tip.y
        data = { 'mElbowRight':{'pos':[wrist_tip.x, wrist_tip.y, wrist_tip.z]} }
    else:
        data = { 'mElbowLeft':{'pos':[wrist_tip.x, wrist_tip.y, wrist_tip.z]} }
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
        puppetry.sendSet({"inverse_kinematics":data})
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

