#!/usr/bin/env python3
"""\
@file helloworld.py
@brief simple LEAP script which will send a message to SecondLifeViewer every second

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

# example init input:
#
# '119:{'data':{'command':'18ce5015-b651-1d2e-2470-0de841fd3635','features':{}},'pump':'54481a53-c41f-4fc2-606e-516daed03636'}'

# these standard modules required
import eventlet
import os
import sys

# modify sys.path so we can find leap module in parent directory
#sys.path.append(os.path.abspath('../'))
currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)
import leap

running = True

def readStdin():
    '''route inbound events (run this as eventlet coroutine)'''
    global running
    try:
        while True:
            data = leap.get()
            processEvent(data)
    except Exception as e:
        running = False
        pass

def processEvent(data) :
    '''this is where we would process inbound events'''
    pass


def writeStdout():
    '''write outgoing events to stdout in coroutine loop'''
    global running
    count = 0;
    SLEEP_DURATION = 1
    while running:
        # sleep to yield to other eventlet coroutines
        eventlet.sleep(SLEEP_DURATION)
        data = {'msg': 'Hello world!', 'count': count }
        count = count + 1
        # the leap module does the actual writing for us
        leap.request("helloworld", data)

leap.__init__()
eventlet.spawn(readStdin)
writeStdout()
