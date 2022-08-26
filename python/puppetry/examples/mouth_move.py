#!/usr/bin/env python3
"""\
@file mouth_move.py
@brief simple LEAP script to move the avatar's mouth

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
mouth_move.py -- use puppetry to animate the mouth

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
import math
import os
import sys
import time

try:
    import puppetry
except ImportError as err:
    # modify sys.path so we can find puppetry module in parent directory
    currentdir = os.path.dirname(os.path.realpath(__file__))
    parentdir = os.path.dirname(currentdir)
    sys.path.append(parentdir)

# now we can really import puppetry
try:
    import puppetry
except ImportError as err:
    sys.exit(f"Failed to load puppetry module: err={err}")

# The avatar's head coordinate frame:
#
#             ______       turn(z)
#            /o   o \       | 
#           |   C    |      @-nod(Y)
#           |  ---   |     /
#            \______/   tilt(X)
#               |       
#     R-+-+-+-+ | +-+-+-+-L
#               +
#               |
#               |
#             +-@-+
#             |   |
#             +   +
#             |   |
#            /   /
#
# Mouth lips have several skin points:
#                    a
#        c  _________b_________  d
#       .-'          e          '-.
#     <   -----------------------   >
#       '-.__________f__________.-'
#                    g
#                    h
# mFaceTeethUpper-->
#  a  mFaceLipUpperLeft local_pos={ 0.045, 0, -0.003 }
#  b  mFaceLipUpperRight local_pos={ 0.045, 0, -0.003 }
#  c  mFaceLipCornerLeft local_pos={ 0.028, -0.019, -0.01 }
#  d  mFaceLipCornerRight local_pos={ 0.028, 0.019, -0.01 }
#  e  mFaceLipUpperCenter local_pos={ 0.045, 0, -0.003 }
# mFaceJaw-->
#     mFaceTeethLower' local_pos={ 0.021, 0, -0.039 }
# mFaceTeethLower-->
#  f  mFaceLipLowerLeft local_pos={ 0.045, 0, 0 }
#  g  mFaceLipLowerRight local_pos={ 0.045, 0, 0 }
#  h  mFaceLipLowerCenter local_pos={ 0.045, 0, 0 }
# 

# hard-coded axis of rotation for lip movement
SMILE_AXIS = glm.normalize(glm.vec3(0.5, 0.0, 1.0))

class Smile:
    def __init__(self):
        self.joints = {}
        self.joints['mFaceLipCornerLeft'] = {'local_rot': [0.0, 0.0, 0.0], 'coef': 1.0 }
        self.joints['mFaceLipCornerRight'] = {'local_rot': [0.0, 0.0, 0.0], 'coef': -1.0 }
        self.amplitude = math.pi / 8.0

    def setIntensity(self, intensity):
        for key, value in self.joints.items():
            # rotate each bone about SMILE_AXIS varied by its coef
            angle = self.amplitude * intensity * value['coef']
            s = math.sin(angle/2.0)
            c = math.cos(angle/2.0)
            q = glm.quat(c, s * SMILE_AXIS)
            value['local_rot'] = puppetry.packedQuaternion(q)

    def getData(self):
        data = {}
        for key, value in self.joints.items():
            data[key] = {'local_rot': value['local_rot']}
        return data


class Sho:
    '''Simple Harmonic Oscillator'''
    def __init__(self, frequency=1.0, phase=0.0):
        frequency = abs(frequency)
        self.wave_speed = 2.0 * math.pi * frequency
        self.period = 1.0 / frequency
        self.t = phase / self.wave_speed
        if self.t > self.period or self.t < -self.period:
            self.t -= int(self.t / self.period) * self.period
    def advance(self, dt):
        self.t += dt
        if self.t > self.period or self.t < -self.period:
            self.t -= int(self.t / self.period) * self.period
    def sin(self):
        return math.sin(self.t * self.wave_speed)
    def cos(self):
        return math.cos(self.t * self.wave_speed)
    def theta(self):
        return self.t * self.wave_speed

# we will alterately open mouth and smile
pulse_period = 8.0
oscillation_period = 0.75
pulse_speed = 2.0 * math.pi / pulse_period
oscillation_speed = 2.0 * math.pi / oscillation_period

pulsor = Sho(frequency = 1.0 / pulse_period, phase=0)
rotator = Sho(frequency = 1.0 / oscillation_period, phase=0)
jaw_amplitude = math.pi / 8.0

update_period = 0.1


def computeData(time_step):
    # advance the oscillators
    global pulsor
    global rotator
    pulsor.advance(time_step)
    rotator.advance(time_step)

    ps = pulsor.sin()
    if ps < 0.0:
        # wag jaw
        yaw = 0.0
        pitch = (jaw_amplitude * abs(ps)) * abs(rotator.sin())
        roll = 0.0
        data = {
            'mFaceJaw':{'local_rot': puppetry.packedQuaternionFromEulerAngles(yaw, pitch, roll)}
        }
    else:
        # smile
        smile = Smile()
        smile.setIntensity(ps)
        data = smile.getData()
    return data

def puppetry_coroutine():
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

# start the real work
puppetry.start()
spinner = eventlet.spawn(puppetry_coroutine)

while puppetry.isRunning():
    eventlet.sleep(0.2)

# cleanup
spinner.wait()
