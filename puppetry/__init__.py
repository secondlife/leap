#!/usr/bin/env python3

"""\
@file puppetry.py
@brief simple framework for sending puppetry data to SL viewer

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
This module uses the LEAP framework for sending messages to the SL viewer.

Tell the viewer to launch some script.py with the following option:
    --leap "python /path/to/script.py"

Alternatively, launch the script from the menu:
    Advanced --> Puppeteering --> Launch LEAP plug-in... --> pick file

The viewer will start the script in a side process and will send messages
to the process's stdin while receiving messages the script writes to its stdout.

The messages have the form:
num_bytes:{pump="puppetry",data='{"joint_name":{"param_name":[r1.23,r4.56,r7.89]}, ...}"'}

Where:

    num_byes = number of characters following the first colon.

    joint_name = string recognized by LLVOAvatar::getJoint(const std::string&),
        e.g. something like: "mWristLeft"

    param_name = "local_rot" | "rot" | "pos" | "scale"

    param_name's value = LLSD array of three floats (e.g. [x,y,z])

Multiple joints can be combined into the same LLSD formatted string.

When you test a LEAP script at the command line it will block because the
leap.py module is waiting for the initial message from the viewer.  To unblock
the system paste the following string into the script's stdin:

119:{'data':{'command':'18ce5015-b651-1d2e-2470-0de841fd3635','features':{}},'pump':'54481a53-c41f-4fc2-606e-516daed03636'}

$LicenseInfo:firstyear=2022&license=viewerlgpl$
Copyright (c) 2022, Linden Research, Inc.
$/LicenseInfo$
'''

import datetime
import logging
import math
import sys

import glm
import leap
import eventlet

CONTROLLER_PUMP = 'puppetry.controller'


# set up a logger sending to stderr, which gets routed to viewer logs
LOGGER_FORMAT = "%(filename)s:%(lineno)s %(funcName)s: %(message)s"
LOGGER_LEVEL = logging.INFO

logging.basicConfig( format=LOGGER_FORMAT, handlers=[logging.StreamHandler(sys.stderr)], level=LOGGER_LEVEL)
_logger = logging.getLogger(__name__)

_running = False
_inboundDataHandler = None
_commandRegistry = {}

_next_request_id = 0

# Diagnostic data logging.
# Set _save_data_log True to record the puppetry data sent to the SL viewer
_save_data_log = False
_first_data_save = True


#GLOBALS

# It's up to the module to use the current puppetry.parts_mask value
part_names = { 'head'   :1, \
               'face'   :2, \
               'lhand'  :4, \
               'rhand'  :8, \
               'fingers':16 \
             }

parts_mask = 0x001F

skeleton_data = {}  #Gets populated with skleton info by the viewer.

def get_next_request_id():
    """ Return a number, hopefully unique """
    global _next_request_id
    _next_request_id = _next_request_id + 1
    return _next_request_id;


# decorator usage: @registerCommand('command')
#                  def do_command(...):  ...
def registerCommand(command, func=None):
    def _register(fn):
        global _commandRegistry
        _commandRegistry[command] = fn
        return fn
    if func is not None:
        # function call usage: register('command', func)
        return _register(func)
    return _register

def deregisterCommand(command):
    """ not really used, but here for completeness.  Removes a command from handled data """
    _logger.debug(f"command='{command}'")
    global _commandRegistry
    try:
        del _commandRegistry[command]
    except:
        _logger.info(f"failed deregister command='{command}'")
        pass

def __init__():
    pass

def start():
    """ should be called at the start of a puppetry module """
    global _running
    if _running:
        return
    _logger.info("puppetry now running")
    _running = True
    eventlet.spawn(_spin)

def isRunning():
    """ True if puppetry is running, False to quit """
    return _running

def sendLeapRequest(namespace,data):
    """ Once gets and sets are wrapped up, send them. """
    if _running:
        try:
            leap.request(namespace, data)

            # Diagnostic data logging
            if _save_data_log:
                global _first_data_save
                open_mode = 'ab'
                if _first_data_save:
                    _first_data_save = False
                    open_mode = 'wb'
                with open('puppetry.log', open_mode) as log_file:
                    data['time'] = str(datetime.datetime.now(datetime.timezone.utc))
                    log_file.write(b'%r\n' % (data))  # Write bytes to file

        except Exception as e:
            _logger.info(f"failed data='{data}' err='{e}'")
    else:
        _logger.info('puppetry not running')

def _sendPuppetryRequest(data):
    """ Once gets and sets are wrapped up, send them. """
    sendLeapRequest('puppetry', data)

def sendGet(data):
    """ Send a get request to the viewer
          data can be a single string, or a list/tuple of strings
    """
    if _running:
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
            _logger.info(f"malformed 'get' data={data}")
            return
        if data_out:
            msg = { 'command':'get', 'data':data_out}
            msg.setdefault('reqid', get_next_request_id())
            _sendPuppetryRequest(msg)

def sendSet(data):
    """ Send a set request to the viewer
            data must be a dict
    """
    if _running:
        if isinstance(data, dict):
            msg = { 'command':'set', 'data':data }
            msg.setdefault('reqid', get_next_request_id())
            _sendPuppetryRequest(msg)
        else:
            _logger.info(f"malformed 'set' data={data}")

@registerCommand("stop")
def stop(args = None):
    """ Stop command from viewer to terminate puppetry module """
    global _running
    _running = False
    _logger.info("puppetry stopping running")

@registerCommand("log")
def log(args):
    """ send args off to viewer's log
    This is registered as a command just for testing, allowing echo back from the viewer"""
    _logger.info(args)


# set_camera command
# This command selects the camera device number used by a puppetry module
# It's up to the module to monitor puppetry.camera_number for changes,
# so it can execute device changes at a known good point in the main processing loop
camera_number = None
@registerCommand("set_camera")
def set_camera(args):
    """ set_camera command from viewer to set camera device number """
    global camera_number
    #_logger.info(f"have set_camera with args ='{args}'")    # {'camera_id': 2}
    cam_num = args.get('camera_id', None)
    if cam_num is not None:
        camera_number = int(cam_num)
        _logger.info(f"set_camera set camera to {camera_number}")

# enable_parts command
# This command selects the camera device number used by a puppetry module

def part_active(name):
    """Returns True if the viewer has the named part marked as 
       active."""
    if name in part_names:
        return (part_names[name] & parts_mask)
    else:
        return False    #Partname not in list.

@registerCommand("enable_parts")
def enable_parts(args):
    """ enable_parts command from viewer to set bitmask for capturing head, face, left and right hands """
    global parts_mask
    #_logger.info(f"have enable_parts with args ='{args}'")    # {'parts_mask': 3}
    new_parts_mask = args.get('parts_mask', None)
    if new_parts_mask is not None:
        parts_mask = int(new_parts_mask)
        _logger.info(f"enable_parts set mask to {parts_mask}")

@registerCommand("set_skeleton")
def set_skeleton(args):
    """ Receive update of the skeleton data. """

    global skeleton_data

    skeleton_dict = args
    if skeleton_dict is not None:
        skeleton_data = skeleton_dict

def get_skeleton_data(name):
    """Looks for toplevel field named 'name' in skeleton_data
        returns None if not found, otherwise data."""

    if type(skeleton_data) is dict:
        if name in skeleton_data:
            return skeleton_data[name]
    return None

def setLogLevel(level):
    try:
        _logger.setLevel(level)
    except Exception as e:
        _logger.info(f"failed level={str(level)}")

def setInboundDataHandler(callback):
    global _inboundDataHandler
    _inboundDataHandler = callback



def packedQuaternion(q):
    '''\
    A Quaternion is a 4D object but the group isomorphic with rotations is
    limited to the surface of the unit hypersphere (radius = 1). Consequently
    the quaternions we care about have only three degrees of freedom and
    we can store them in three floats.  To do this we always make sure the
    real component (W) is positive by negating the Quaternion as necessary
    and then we store only the imaginary part (XYZ).  The real part can be
    obtained with the formula: W = sqrt(1.0 - X*X + Y*Y + Z*Z)
    '''
    if q.w < 0.0:
        q *= -1.0
    return [q.x, q.y, q.z]

def packedQuaternionFromEulerAngles(yaw, pitch, roll):
    # angles are expected to be in radians (NOT DEGREES)
    q = glm.quat(glm.vec3(yaw, pitch, roll))
    return packedQuaternion(q)

def unpackedQuaternion(xyz):
    '''\
    A packed Quaternion only includes the imaginary part (XYZ) and the
    real part (W) is obtained with the formula:
    W = sqrt(1.0 - X*X + Y*Y + Z*Z)
    '''
    imaginary_length_squared = xyz[0] * xyz[0] + xyz[1] * xyz[1] + xyz[2] * xyz[2]
    q = glm.quat()
    q.x = xyz[0]
    q.y = xyz[1]
    q.z = xyz[2]
    if imaginary_length_squared > 1.0:
        imaginary_length = math.sqrt(imaginary_length_squared)
        q.x /= imaginary_length
        q.y /= imaginary_length
        q.z /= imaginary_length
        q.w = 0.0
    else:
        q.w = math.sqrt(1.0 - imaginary_length_squared)
    return q


def _handleCommand(message):
    """  Process message as a dict from the viewer
    message = { data: { command: 'foo', args: { ... } }, pump: ... }
    
    Default handled commands are:
        stop
        log
        ...
    """
    _logger.debug(f"leap has command '{message}'")
    handled = False
    try:
        command_name = message['data']['command']
        command_args = message['data'].get("args", {})
        try:
            operator = _commandRegistry[command_name]
            if operator:
                try:
                    operator(command_args)
                    handled = True
                except Exception as e:
                    _logger.info(f"failed command='{command_name}' err='{e}'")
        except:
            _logger.debug(f"unknown command='{command_name}'")
            known_commands = _commandRegistry.keys()
            _logger.debug(f"known command are {known_commands}")
    except:
        _logger.info(f"failed command message='{message}'")
    return handled

def _spin():
    """ Coroutine that sets up data pipeline with the viewer, then runs
        forever and and checks for incoming commands and data """
    global _running
    _logger.debug('')

    leap.__init__()
    try:
        # Find-or-create "puppetry.controller" LLEventPump so viewer code can
        # send unsolicited events our way without having to know our default
        # (UUID) LLEventPump name.
        reqid = -1
        request = dict(
            op='listen',
            reqid=reqid,
            source=CONTROLLER_PUMP,
            # 'listen' reuses any existing 'puppetry.controller' pump, so
            # every event sent to 'puppetry.controller' will be forwarded
            # to every LEAP child listening on that pump. BUT we must
            # ensure that every listener has a distinct listener name,
            # else LLEventPump::listen() will fail with DupListenerName.
            # Fortunately we already have a unique name handy.
            listener=leap.replypump())
        pump=leap.cmdpump() # targets the viewer's LLLeapListener
        leap.request(pump=pump, data=request)

        # wait for response from viewer with echoed reqid
        while True:
            response = leap.get()
            if response.get('data', {}).get('reqid') == reqid:
                _logger.debug(f"connected to pump={CONTROLLER_PUMP}")
                # we expect response.data.status to be True
                assert response['data']['status']
                break
            else:
                # skip all other messages
                _logger.debug(f"skip bad response='{response}'")
                pass

        # finally spin on stdin and handle inbound commands/messages
        while _running:
            message = leap.get()
            # puppetry gets first chance to handle data
            handled = _handleCommand(message)
            if not handled:
                # otherwise it is delegated to the custom _inboundDataHandler
                if _inboundDataHandler:
                    try:
                        _inboundDataHandler(message)
                    except Exception as e:
                        _logger.info(f"inboundDataHandler: err={e}")

    except Exception as e:
        _logger.info(f"err='{e.message}'")
        _running = False

if __name__ == '__main__':
    # run for 10 seconds then stop
    _logger.setLevel(logging.DEBUG)
    start()
    count = 0
    while _running:
        eventlet.sleep(1.0)
        count += 1
        if count > 10:
            stop()
