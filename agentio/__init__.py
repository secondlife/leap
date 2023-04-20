'''\
@file agentio.py
@brief simple framework for handling agentio messages received by puppetry
'''

CONTROLLER_PUMP = 'agentio.controller'

#Globals
_commandRegistry = {}       #List of callbacks for handling messages.
_controller = None          #The class handling leapIO (EX puppetry)

_look_at=None
_camera=None
_agent_orientation=None

def registerCommand(command, func=None):
    ''' decorator usage: @registerCommand('command')
                  def do_command(...):  ...'''
    def _register(fn):
        global _commandRegistry
        _commandRegistry[command] = fn
        return fn
    if func is not None:
        # function call usage: register('command', func)
        return _register(func)
    return _register

def deregisterCommand(command):
    ''' not really used, but here for completeness.  Removes a command from handled data '''
    global _commandRegistry
    try:
        del _commandRegistry[command]
    except KeyError:
        _controller.log(f"failed deregister command='{command}'")

def __init__():
    pass

def _handleCommand(message):
    '''  Process message as a dict from the viewer
    message = { data: { command: 'foo', args: { ... } }, pump: ... }
    '''

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
        except KeyError:
            _controller.log(f"unknown command='{command_name}'")
            known_commands = _commandRegistry.keys()
            _controller.log(f"known command are {known_commands}")
    except KeyError:
        _controller.log(f"failed command message='{message}'")
    return handled

#Registry of verbs.
@registerCommand("look_at")
def look_at(args):
    '''Handles receipt of look_at data from viewer.
        Look at contains a vector relative the head position
        which provides the direction to the look at target.
        The distance from the agent to the target is specified in
        world space (meters)'''

    global _look_at

    if "direction" in args and "distance" in args and float(args["distance"]) != 0.0:
        _look_at = { "direction":args["direction"], \
                     "distance" :args["distance"] }
    else:
        _look_at = None

@registerCommand("viewer_camera")
def viewer_camera(args):
    '''Receives the camera position and target position in world units (meters)
       relative to the avatar's position and orientation.'''
    global _camera

    if "camera" in args and "target" in args:
        _camera = { "camera":args["camera"], \
                    "target":args["target"] }
    else:
        _camera = None

@registerCommand("agent_orientation")
def agent_orientation(args):
    '''Receives the agent's absolute position and rotation
       within the region.'''
    global _agent_orientation

    if "position" in args and "rotation" in args:
        _agent_orientation = { "position":args["position"], \
                               "rotation":args["rotation"] }
    else:
        _agent_orientation = None

#Public functions
def init( controller ):
    '''Send a message to the server to activate the lazy leap loader for agentIO'''

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

def set_camera(params):
    '''Send a request to set the agent's in-world camera position.
       Expects a data structure containing world-space XYZ
       coordinates for the camera's position and the camera's
       focal target. target_id may optionally be set to focus the
       camera on the object identified by the UUID if it is
       present.  Camera and target positions may be clamped to
       some range relative to the agent's position in world.
       Example message:  { 'camera':(x,y,z), 'target':(x,y,z), 'target_id':<UUID> }
    '''

    msg = { 'command':'set_camera', 'data':params }
    _controller.sendLeapRequest(msg)

def request_camera():
    '''Send get_camera request to agentio module.  Viewer responds with viewer_camera'''
    msg = { 'command':'get_camera', 'data':{} }
    _controller.sendLeapRequest(msg)


def request_lookat():
    '''Send get_lookat request to agentio module. Viewer responds with look_at'''
    msg = { 'command':'get_lookat', 'data':{} }
    _controller.sendLeapRequest(msg)


def request_agent_orientation():
    '''Send get_agent_orientation request to agentio module.
       Viewer responds with agent_orientation'''
    msg = { 'command':'get_agent_orientation', 'data':{} }
    _controller.sendLeapRequest(msg)


def getLookAt():
    '''Returns look_at data if the viewer has sent it or None
        data contains a direction relative the agent's head orientation and a distance.
        EX: {'direction': (x,y,z), 'distance':d}'''
    return _look_at

def getCamera():
    '''Returns camera data if the viewer has sent it or None.
        data contains the world space position of the camera and the focal target of the camera.
        EX: {'camera':(x,y,z), 'target':(x,y,z)}'''
    return _camera

def getAgentOrientation():
    '''Returns agent orientation data if the viewer has sent it or None
        data structure is the agent's world-space position and world-frame rotation.
        EX: {'position':(x,y,z), 'rotation':(q,x,y,z)}'''
    return _agent_orientation

