#!/usr/bin/env python3
"""\
@file playback.py
@brief simple LEAP script to read a data file and move the avatar

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
This script uses the LEAP framework for sending messages to the viewer that 
are read from a file.

To create a data file:

    * Edit puppetry.py and change _save_data_log on line 106 to True
    * Use the "Launch LEAP plug-in" command and pick "webcam_puppetry.py"
    * Smile for the camera, wave hands and do something.
    * Stop the puppetry module
    * Edit puppetry.py and change _save_data_log on line 106 to False   DON'T FORGET THIS STEP!!
    * Look for a file 'puppetry.log' saved next to your viewer
    * Rename that to 'puppet_data.txt'  or change that name in this file
    * Use the "Launch LEAP plug-in" command and pick this module

Here is a sample data set, which may or may not be correct captured data.   This was taken from the 
webcam with the left hand raised, elbow at about a 90 degree angle, forearm vertical.   Save it
as 'puppet_data.txt' next to your viewer executable

{'mHead': {'rot': [-0.07607924193143845, 0.06911587715148926, -0.05753650888800621]}, 'mWristLeft': {'pos': [0.05, 0.166595717963902, 0.5359430452740218]}, 'mHandThumb3Left': {'pos': [0.06564589377492287, 0.12334611772519452, 0.5686074440892029]}, 'mHandIndex3Left': {'pos': [0.06642778499301683, 0.13929063624809937, 0.6217418699780863]}, 'mHandMiddle3Left': {'pos': [0.06575047275198581, 0.15123645261489777, 0.6307282804431861]}, 'mHandRing3Left': {'pos': [0.06663258099820249, 0.16339769459061, 0.6293762328347551]}, 'mHandPinky3Left': {'pos': [0.06611388508227065, 0.18135500294687903, 0.6164326068523661]}, 'command': 'move', 'time': '2022-05-06 17:23:57.413465+00:00'}
{'mHead': {'rot': [-0.07562679052352905, 0.07091937214136124, -0.057033516466617584]}, 'mWristLeft': {'pos': [0.05, 0.16653922432756235, 0.535830288855632]}, 'mHandThumb3Left': {'pos': [0.06478160067892592, 0.12399815593709126, 0.568228381170082]}, 'mHandIndex3Left': {'pos': [0.06592536222115006, 0.1399731221144453, 0.6206751302488502]}, 'mHandMiddle3Left': {'pos': [0.0654764419263402, 0.15185432789532152, 0.6294457078528349]}, 'mHandRing3Left': {'pos': [0.06627713927381965, 0.16381900100804792, 0.6275474763231684]}, 'mHandPinky3Left': {'pos': [0.06569030102931626, 0.18124425635537927, 0.6151926108926513]}, 'command': 'move', 'time': '2022-05-06 17:23:57.517194+00:00'}
{'mHead': {'rot': [-0.07549858093261719, 0.0711248517036438, -0.05154349282383919]}, 'mWristLeft': {'pos': [0.05, 0.16699472720560288, 0.5360983752110315]}, 'mHandThumb3Left': {'pos': [0.06577550265864768, 0.12420206248532964, 0.568657138555926]}, 'mHandIndex3Left': {'pos': [0.06680847723631266, 0.14015025894701544, 0.6217283297761285]}, 'mHandMiddle3Left': {'pos': [0.06638520308997253, 0.15212387180171721, 0.6306653598844102]}, 'mHandRing3Left': {'pos': [0.06725008696693952, 0.16428886615866556, 0.6293541402543581]}, 'mHandPinky3Left': {'pos': [0.06662559514806715, 0.181890181998128, 0.6164928700099712]}, 'command': 'move', 'time': '2022-05-06 17:23:57.637169+00:00'}
{'mHead': {'rot': [-0.074874147772789, 0.07309883832931519, -0.053112126886844635]}, 'mWristLeft': {'pos': [0.05, 0.1666441680848929, 0.5361760958797911]}, 'mHandThumb3Left': {'pos': [0.06557511942638677, 0.1238459229496201, 0.5685419267889305]}, 'mHandIndex3Left': {'pos': [0.06649966372576824, 0.13990722607879413, 0.6214197636888931]}, 'mHandMiddle3Left': {'pos': [0.06599927814892675, 0.15181121086193672, 0.6304161669505961]}, 'mHandRing3Left': {'pos': [0.06695252754889616, 0.16380042221241212, 0.6293469683533942]}, 'mHandPinky3Left': {'pos': [0.0662077297881874, 0.18146555132956932, 0.6161608207081005]}, 'command': 'move', 'time': '2022-05-06 17:23:57.773805+00:00'}
{'mHead': {'rot': [-0.07448343932628632, 0.06885180622339249, -0.035997889935970306]}, 'mWristLeft': {'pos': [0.05, 0.16729896764942478, 0.5361882011149134]}, 'mHandThumb3Left': {'pos': [0.06574690041785626, 0.12442234070665525, 0.5685525689166656]}, 'mHandIndex3Left': {'pos': [0.06662216794813625, 0.14029842110667906, 0.6212556577420765]}, 'mHandMiddle3Left': {'pos': [0.06620718293644166, 0.15229872926471846, 0.6300273446697175]}, 'mHandRing3Left': {'pos': [0.0670738089351241, 0.1642334542108759, 0.6287173451620537]}, 'mHandPinky3Left': {'pos': [0.06639558466617584, 0.18190129982428496, 0.6160302439715732]}, 'command': 'move', 'time': '2022-05-06 17:23:57.888231+00:00'}

There seems to be a bug ? where only sending the same line over and over does not position correctly, but alternating between these two data sets works fine.
'''

import datetime
import eventlet
import logging
import os
import sys
import time

import puppetry

# The avatar's coordinate frame:
#          ___
#         /o o\
#         \___/
#           |
# R o--+--+-+-+--+--o L
#           |
#           +         z
#           |         |
#         +-@-+       @--y
#         |   |      /
#         +   +     x
#         |   |
#         |   |
#        /   /
#
# mWristRight     -0.01617,-0.34352, 0.34870     0.731521
# mWristLeft      -0.01617, 0.34352, 0.34870     0.731521


data_file_name = 'puppet_data.txt'
puppet_data = None
current_line_num = 0

# --------------------------------------------------------------------------

def read_puppet_data(data_file_name):
    """ return a dict of animation data to send to the viewer """
    global puppet_data

    num_lines = 0
    if puppet_data is None:
        # open the data file the first time
        try:
            open_mode = 'rb'
            with open(data_file_name, open_mode) as data_file:
                raw_data = data_file.readlines()
                if raw_data is not None and len(raw_data) > 0:
                    puppetry.log("read %d data lines" % len(raw_data))
                    puppet_data = []
                    for cur_line in raw_data:
                        # to do - ignore lines starting with '#'
                        #       - handle the time value
                        puppet_data.append(cur_line.strip())
        
        except Exception as exp:
            puppetry.log("exception reading data file: %s" % str(exp))
            puppetry.log("*** Check the file in %s" % os.path.join(os.getcwd(), data_file_name))

    if puppet_data is not None:
        num_lines = len(puppet_data)
         
    return num_lines

# --------------------------------------------------------------------------

def fetch_puppetry_data(line_num):
    """ Fetch the next line of data as a dict, along with time extracted from there """
    pup_data = None
    play_date = None
    try:
        pup_data = eval(puppet_data[line_num])
        #puppetry.log("line %d, pup_data: %r" % (line_num, pup_data))

        # extract the original time
        play_str = pup_data.pop('time', None)
        if play_str is not None:
            play_date = datetime.datetime.strptime(play_str[0:26], '%Y-%m-%d %H:%M:%S.%f')
            #puppetry.log('play_date %r is type %s' % (play_date, type(play_date)))

    except IndexError as exp:
        puppetry.log("exception %s evaluating line %d" % (str(exp), line_num))

    return pup_data, play_date

# --------------------------------------------------------------------------

def main_loop():
    """ read and send data until stopped """
    global current_line_num
    
    num_lines = read_puppet_data(data_file_name)
    if num_lines < 2:
        puppetry.log("Must have at least two lines of puppetry data, exiting")
        puppetry.stop()
        return

    sleepy_time = datetime.timedelta(milliseconds=100)   # default
    next_play_date = None

    # get the first line of data
    pup_data, play_date = fetch_puppetry_data(current_line_num)

    while puppetry.isRunning():
        if pup_data is None:
            puppetry.log("Unexpected loss of data, exiting")
            puppetry.stop()
            return

        # Send the data to the viewer
        puppetry.sendPuppetryData(pup_data)

        # Bump the line number and get the next data
        current_line_num = current_line_num + 1
        if current_line_num >= len(puppet_data):
            current_line_num = 0    # loop back to start if needed

        # get the next data and time
        pup_data, next_play_date = fetch_puppetry_data(current_line_num)

        if next_play_date is None or play_date is None or (next_play_date <= play_date):
            sleepy_time = datetime.timedelta(milliseconds=100)   # default
            #puppetry.log("sleep default at %r line %d" % (sleepy_time.total_seconds(), current_line_num))
        else:   # Figure out how long to sleep
            sleepy_time = next_play_date - play_date
            #puppetry.log("sleep calculated at %r line %d" % (sleepy_time.total_seconds(), current_line_num))

        play_date = next_play_date

        # sleep to yield to other eventlet coroutines
        sleepy_seconds = max(0.05, sleepy_time.total_seconds())
        sleepy_seconds = min(sleepy_seconds, 5.0)   # enforce a minimum so a long sleep doesn't totally stall out
        eventlet.sleep(sleepy_seconds)

    # Loop and send more

# --------------------------------------------------------------------------

puppetry.setLogLevel(logging.DEBUG)
puppetry.start()

# spin the animation playback
spinner = eventlet.spawn(main_loop)

# loop the UI until puppetry is stopped
while puppetry.isRunning():
    # do nothing while the coroutines have all the fun
    eventlet.sleep(0.1)

# cleanup
spinner.wait()
puppetry.stop()

