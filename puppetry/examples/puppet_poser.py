#!/usr/bin/env python3
"""
Simple LEAP script to read a data file and send puppetry data.
The file is re-read every cycle, so can be live edited to see changes

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

import copy
import json
import logging
import math
import os
import time

import eventlet
import glm

import puppetry

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
IK_SCALE_FACTOR = 1.0 / 1.76

WRIST_X = 0.2
WRIST_Y = 0.50
WRIST_Z = 0.38

PI = math.pi
Z_AXIS = glm.vec3(0.0, 0.0, 1.0)

UPDATE_PERIOD = 0.25     # seconds interval sending updates to SL viewer
PUPPET_DATA_FILE = 'puppet_poser_data.json'

# -----------------------------------------------------------------------

dump_data = True
previous_data = {}

def read_data():
    """ Read from puppet_pose_data.txt to send to SL.   The file is read
    each time so that it can be edited and saved while the plug-in is running,
    thus you can try values and immmediately see results """

    global dump_data, previous_data

    dirname = os.path.dirname(__file__)
    target = os.path.join(dirname, PUPPET_DATA_FILE)

    raw_data = {}
    try:
        with open(target, encoding="utf-8") as data_file:
            # read in a dictionary
            raw_data = json.load(data_file)
    except IOError as ex:
        puppetry.log(f"Could not read puppet data file {target} : {ex}")
        return {}
    except ValueError as ex:   # also catches simplejson.decoder.JSONDecodeError
        puppetry.log(f"Unable to parse puppet data file {target} : {ex}")
        return {}

    # Filter out any items that begin with '#' so they can be treated like a comment
    clean_data = {}
    for key, value in raw_data.items():
        if key[0] != '#':
            clean_data[key] = value

    if clean_data != previous_data:
        dump_data = True
        previous_data = copy.deepcopy(clean_data)

    if dump_data:
        puppetry.log(f"Raw puppetry json data: {clean_data}")
        dump_data = False

    return clean_data



def puppetry_coroutine():
    """ Main loop reading and sending data """
    start_time = time.monotonic()
    delta_time = UPDATE_PERIOD
    while puppetry.isRunning():
        # sleep to yield to other eventlet coroutines
        eventlet.sleep(max(0.0, UPDATE_PERIOD - delta_time))
        cur_time = time.monotonic()
        delta_time = cur_time - start_time
        start_time = cur_time
        data = read_data()
        if data:
            puppetry.sendSet({"joint_state":data})
            #puppetry.log(f"sent {data}")
        #print("") # uncomment this when debugging at command-line


# -----------------------------------------------------------------------
# startup / main code

puppetry.setLogLevel(logging.DEBUG)

# start the real work
puppetry.start()
spinner = eventlet.spawn(puppetry_coroutine)

while puppetry.isRunning():
    eventlet.sleep(0.2)

# cleanup
spinner.wait()
