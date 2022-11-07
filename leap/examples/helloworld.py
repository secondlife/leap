#!/usr/bin/env python3
"""
Simple LEAP script which will send a message to SecondLifeViewer every second
"""

# example init input:
#
# '119:{'data':{'command':'18ce5015-b651-1d2e-2470-0de841fd3635','features':{}},'pump':'54481a53-c41f-4fc2-606e-516daed03636'}'

# these standard modules required
import eventlet

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
