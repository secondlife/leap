#!/usr/bin/env python3

import argparse
import cv2
import itertools
import glm
import logging
import mediapipe as mp
import numpy as np
import os
import sys
import time
import traceback
import eventlet

from math import sin, cos, pi, sqrt, degrees, radians

try:
    import puppetry
except ImportError as err:
    # modify sys.path so we can find puppetry module in parent directory
    currentdir = os.path.dirname(os.path.realpath(__file__))
    parentdir = os.path.dirname(currentdir)
    sys.path.append(parentdir)
    parentdir = os.path.dirname(parentdir)
    sys.path.append(parentdir)

# now we can really import puppetry
try:
    import puppetry
except ImportError as err:
    sys.exit("Can't find puppetry module")

# set up a logger sending to stderr, which gets routed to viewer logs
LOGGER_FORMAT = "%(filename)s:%(lineno)s %(funcName)s: %(message)s"
LOGGER_LEVEL = logging.INFO

logging.basicConfig( format=LOGGER_FORMAT, handlers=[logging.StreamHandler(sys.stderr)], level=LOGGER_LEVEL)
_logger = logging.getLogger(__name__)

UPDATE_PERIOD = 0.1     # time between puppetry updates

WINDOW_NAME = "Image"

class Expression:
    '''The Expression class manages mapping input from
        face tracking to the leap puppetry stream'''

    def __init__(self, camera_num = 0):

        self.expected_normalized_neck_height = 0.63
        self.neck_vertical_offset = 0.0

    def get_initial_skeleton(self):
        '''On startup, mediapipe blocks heavily, temporarily disrupting leap communication
           So here we'll request/wait for skeleton data from the viewer before continuing.

           NOTE: After skeleton data is received, we continue on.  The first frame of
           webcam capture may still be blocking, which means there is a small window of time
           where if the agent changes skeletons in the viewer, this information may not
           be obtained by this plug-in module.
        '''

        #puppetry.sendPuppetryData(dict(command='send_skeleton'))    #Request skeleton
        puppetry.sendGet('skeleton')    #Request skeleton
        retries = 3
        end_time = time.time() + 2.0

        while puppetry.isRunning() and retries > 0:
            if puppetry.get_skeleton_data('scale') is not None:
                puppetry.log("Got skeleton woot!")
                return True           #We've got some data, can continue.

            eventlet.sleep(0.1) #Sleep 1/10th of a second

            cur_time = time.time()
            if cur_time > end_time:
                retries = retries - 1
                end_time = cur_time + 3.0
                if retries > 0:
                    puppetry.sendGet('skeleton')    #Re-request skeleton data.
        return False

    def main_loop(self):
        '''The main loop of expression processing'''

        try:
            cv2.namedWindow(WINDOW_NAME)  # Create a window.   This is initially blank, but shows the user something is going on
        except cv2.error as excp:
            puppetry.log("cv2 exception creating window: %s" % str(excp))

        frame_start_time=None       #Time for start of frame.
        data={}                     #Data structure to be output to LEAP
        counter=0

        while puppetry.isRunning():
            success = True

            frame_start_time = time.time()

            if success:
                #Send the puppetry info to viewer first.
                puppetry.sendSet(data)

                counter += 1
                if (counter % 10) == 0:
                    sendAgentIOGet('look_at')

                cur_time = time.time()
                frame_compute_time = cur_time - frame_start_time
                nap_duration = max(0.0, UPDATE_PERIOD - frame_compute_time)
                eventlet.sleep(nap_duration)


            # Window has been closed or hit 'q' to quit
            try:
                key_press = cv2.waitKey(1) & 0xFF
                if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) == 0 or \
                    key_press == ord('q') or \
                    key_press == 27:
                    puppetry.stop()   # will exit loop
            except cv2.error as excp:
                # Will throw exceptions before we get a window set up
                puppetry.log("quit check cv2 exception %s" % str(excp))
                pass

        try:
            # attempt to clean up
            cv2.destroyAllWindows()
        except Exception as ex:
            pass

def inbound_handler(message):
    '''This routine handles non-puppetry leap messages received
        by the module'''
    #handled = False
    handled = True
    try:
        command_name = message['data']['command']
        command_args = message['data'].get("args", {})
        puppetry.log("CMD: %s; ARGS: %s" % (command_name,str(command_args)))
    except Exception as e:
        puppetry.log(f"failed command='{command_name}' err='{e}'")
    return handled


def sendAgentIOGet(data):
    """ Send a get request to the viewer for an agentIO message.
          data can be a single string, or a list/tuple of strings
    """
    data_out = []
    if isinstance(data, str):
        data_out = [data]
    elif isinstance(data, list):
        data_out = data
    elif isinstance(data, tuple):
        for item in data:
            if isinstance(item, str):
                data_out.append(item)
    else:
        puppetry.log(f"malformed 'get' data={data}")
        return
    if data_out:
        msg = { 'command':'get', 'get':data_out}
        msg.setdefault('reqid', puppetry.get_next_request_id())
        puppetry.sendLeapRequest('agentio',msg)

def main(camera_num = 0):
    '''pylint wants to docstring for the main function'''
    # _logger.setLevel(logging.DEBUG)

    puppetry.start()                                    #Initiate puppetry communication
    puppetry.setInboundDataHandler(inbound_handler)
    try:
        face = Expression(camera_num = camera_num)      #Init the expression plug-in
    except Exception as exerr:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        puppetry.log("stacktrace: %r" % traceback.format_tb(exc_traceback))
        puppetry.log("Unable to create Expression for camera %r : %r" % (camera_num, str(exerr)))
        return

    face.get_initial_skeleton()     #Get skeleton data from viewer.
    face.main_loop()
    puppetry.stop()

if __name__ == "__main__":
    """ Deal with command line arguments """

    parser = argparse.ArgumentParser(description='Second Life face motion capture',
        epilog="Pass in camera number to use")
    parser.add_argument('-c', '--camera', dest='camera_number',
        default=0, help='Camera device number to use')
    args = parser.parse_args()

    main(camera_num = int(args.camera_number))
