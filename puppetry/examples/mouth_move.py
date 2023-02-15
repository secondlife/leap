#!/usr/bin/env python3
"""
simple LEAP script to move the avatar's mouth

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
"""

import math
import time

import eventlet
import glm

import puppetry

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
        self.joints['mFaceLipCornerLeft'] = {'rotation': [0.0, 0.0, 0.0], 'coef': 1.0 }
        self.joints['mFaceLipCornerRight'] = {'rotation': [0.0, 0.0, 0.0], 'coef': -1.0 }
        self.amplitude = math.pi / 8.0

    def setIntensity(self, intensity):
        for key, value in self.joints.items():
            # rotate each bone about SMILE_AXIS varied by its coef
            angle = self.amplitude * intensity * value['coef']
            s = math.sin(angle/2.0)
            c = math.cos(angle/2.0)
            q = glm.quat(c, s * SMILE_AXIS)
            value['rotation'] = puppetry.packedQuaternion(q)

    def getData(self):
        data = {}
        for key, value in self.joints.items():
            data[key] = {'rotation': value['rotation']}
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
            'mFaceJaw':{'rotation': puppetry.packedQuaternionFromEulerAngles(yaw, pitch, roll)}
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
        puppetry.sendSet({"joint_state":data})
        #print("") # uncomment this when debugging at command-line

# start the real work
puppetry.start()
spinner = eventlet.spawn(puppetry_coroutine)

while puppetry.isRunning():
    eventlet.sleep(0.2)

# cleanup
spinner.wait()
