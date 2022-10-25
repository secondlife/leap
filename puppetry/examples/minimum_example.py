#!/usr/bin/env python3
import logging
import time

import eventlet
import puppetry

'''
Note: When you debug this script at the command line it will block
because the leap.py framework is waiting for the initial message
from the viewer.  To unblock the system paste the following
string into the script's stdin:

119:{'data':{'command':'18ce5015-b651-1d2e-2470-0de841fd3635','features':{}},'pump':'54481a53-c41f-4fc2-606e-516daed03636'}

Also when debugging, for more readable text with newlines between
messages uncomment the print("") line in the main loop below.
'''

update_period = 0.1
t0 = time.monotonic()
t = 0.0

def computeData(time_step):
    global t
    t += time_step
    # supported fields are 'pos', 'rot', 'local_rot'
    # 'scale' is not yet supported
    data = { 'mJointName':{'pos':[0.123, 0.456, 0.789]} }
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

