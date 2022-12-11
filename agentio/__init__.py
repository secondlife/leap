#!/usr/bin/env python3
"""\
@file agentio.py
@brief simple framework for handling agentio messages received by puppetry

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

$LicenseInfo:firstyear=2022&license=viewerlgpl$
Copyright (c) 2022, Linden Research, Inc.
$/LicenseInfo$
"""

CONTROLLER_PUMP = 'agentio.controller'

#Globals
_commandRegistry = {}       #List of callbacks for handling messages.
_controller = None          #The class handling leapIO (EX puppetry)

_look_at=None
_camera=None
_agent_orientation=None

def registerCommand(command, func=None):
    """ decorator usage: @registerCommand('command')
                  def do_command(...):  ..."""
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
    global _commandRegistry
    try:
        del _commandRegistry[command]
    except:
        _controller.log(f"failed deregister command='{command}'")

def __init__():
    pass

def _handleCommand(message):
    """  Process message as a dict from the viewer
    message = { data: { command: 'foo', args: { ... } }, pump: ... }
    """

    _controller._logger.debug(f"leap has command '{message}'")
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
                    _controller.log(f"failed command='{command_name}' err='{e}'")
        except:
            _controller.log(f"unknown command='{command_name}'")
            known_commands = _commandRegistry.keys()
            _controller.log(f"known command are {known_commands}")
    except:
        _controller.log(f"failed command message='{message}'")
    return handled

#Registry of verbs.
@registerCommand("look_at")
def look_at(args):
    """Handles receipt of look_at data from viewer.
        Look at contains a vector relative the head position
        which provides the direction to the look at target.
        The distance from the agent to the target is specified in
        world space (meters)"""

    global _look_at

    if "direction" in args and "distance" in args and float(args["distance"]) != 0.0:
        _look_at = { "direction":args["direction"], \
                     "distance" :args["distance"] }
    else:
        _look_at = None

@registerCommand("viewer_camera")
def viewer_camera(args):
    """Receives the camera position and target position in world units (meters)
       relative to the avatar's position and orientation."""
    global _camera

    if "camera" in args and "target" in args:
        _camera = { "camera":args["camera"], \
                    "target":args["target"] }
    else:
        _camera = None

@registerCommand("agent_orientation")
def agent_orientation(args):
    """Receives the agent's absolute position and rotation
       within the region."""
    global _agent_orientation

    if "position" in args and "rotation" in args:
        _agent_orientation = { "position":args["position"], \
                               "rotation":args["rotation"] }
    else:
        _agent_orientation = None

#Public functions
def init( controller ):
    """Send a message to the server to activate the lazy leap loader for agentIO"""

    global _controller

    _controller = controller
    _controller.setInboundDataHandler(_handleCommand)

    reqid = -1
    request = dict(
        op='listen',
        reqid=reqid,
        source="agentio.controller",
        listener=_controller.leap.replypump())
    pump=_controller.leap.cmdpump() # targets the viewer's LLLeapListener
    _controller.leap.request(pump=pump, data=request)

def sendSet(data):
    """ Send a set request to the viewer
            data must be a dict
    """
    if isinstance(data, dict):
        msg = { 'command':'set', 'data':data }
        msg.setdefault('reqid', get_next_request_id())
        _controller.sendLeapRequest(msg)
    else:
        _controller.log(f"malformed 'set' data={data}")

def sendGet(data):
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
        _controller.log(f"malformed 'get' data={data}")
        return
    if data_out:
        reqID = _controller.get_next_request_id()
        msg = { 'command':'get', 'data':data_out}
        msg.setdefault('reqid', reqID)
        _controller.sendLeapRequest('agentio',msg)

def getLookAt():
    """Returns look_at data if the viewer has sent it or None"""
    return _look_at

def getCamera():
    """Returns camera data if the viewer has sent it or None"""
    return _camera

def getAgentOrientation():
    """Returns agent orientation data if the viewer has sent it or None"""
    return _agent_orientation


if __name__ == '__main__':
    # run for 10 seconds then stop
    raise Exception("Library cannot be run")
