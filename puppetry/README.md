# Puppetry via LEAP script
LEAP = LLSD Event API Plug-in

## Requirements

- [python](https://www.python.org/)
- [cmake](https://cmake.org/) (for installing dlib)
- [git](https://git-scm.com/)

### Installation

Checkout the leap repository

```
git clone git@bitbucket.org:lindenlab/leap.git
cd leap
```

**leap** and the puppetry system are provided as a python package. You can install both
puppetry and its requirements by installing leap with the optional puppetry and opencv
dependency lists:
```
pip install -e .[puppetry,opencv]
```

## Run LEAP scripts from the viewer

There are two ways to launch a leap script from the viewer:
**(1)** Start the LEAP script at runtime via the menu: **Advanced --> Puppeteering --> Launch LEAP plug-in...**
**(2)** Alternatively Launch the viewer from the command line interface (CLI) with an option of the form:
```
    --leap "path/to/venv/bin/python /path/to/script.py"
```

Please note: if you want to run puppetry scripts from the **Advanced** menu then you must install them outside
of a virtual environment so that the dependencies are accessible to python interpreter at a user or system level:

## Writing Puppetry Plug-ins
The simplest example script is probably `arm_wave.py` which animates one arm to wave hello/goodbye,
and is probably the best place to start, but a basic summary is:

Your script will have a main loop which constantly computes new Puppetry `data` and sends it to the viewer via:
```
    puppetry.sendPuppetryData(data)
```

Note: leap.py uses **eventlet** which is a module for writing **coroutines**,
so any Python Puppetry script will have to play-well with eventlet.
Specifically this means: your script's main loop must call `eventlet.sleep(seconds)`
to yield to `leap.py` polling work.

The format for `data` is basically:
```
data = {'mJointName':{'field_name':value, ...}, ...}
```
Where: `mJointName` is something like `'mWristLeft'`,
`field_name` is: `'position'` or `'rotation'`,
and `value` is either an array of Cartesian coordinates `[x,y,z]` for `position`
or the imaginary part `[x,y,z]` of a Quaternion (when it has a positive real component `w`) for `rotation`.
`field_name:value` can also be `'no_constraint':1` to disable constraint for that Joint.

It is recommended you use the **PyGLM** module for 3D math.
The `puppetry.py` module has utils for converting `glm.quat`, or Euler Angles `[yaw,pitch,roll]`, to `array_value` format.

## Testing LEAP scripts at the command line
Sometimes you might want to test a LEAP script on the commandline to debug it.
For some of the scripts there is a trick you need to know in order to do that:

The `leap.py` module uses **evenlet** to simultaneously read from **stdin** and write to **stdout** in a single-threaded process without blocking (via coroutines).
When the framework starts up the first thing it does is block: waiting for the initial LEAP initialization message on **stdin**.
To push your script past this stage you need to past a valid init string into the shell, like this:
```
119:{'data':{'command':'18ce5015-b651-1d2e-2470-0de841fd3635','features':{}},'pump':'54481a53-c41f-4fc2-606e-516daed03636'}
```
After the script reads that from **stdin** it will proceed with the rest of its logic.
