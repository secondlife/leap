# Puppetry via LEAP script
LEAP = LLSD Event API Plug-in
## Install python3
## Required modules:
To run the simple example puppetry scripts you must install the Python module dependencies.
On **Windows** you probably want to do this in a **Windows Power Shell** terminal.
```
pip install eventlet llbase PyGLM tkinter
```
The webcam capture scripts have more dependencies.
First try to install **dlib** (a dependency of **opencv-python**) which could take a while:
```
pip install dlib
```
Note: if the above fails to install **dlib** case it must be done manually.
Instructions can be found at the the [davisking/dlib github page](https://github.com/davisking/dlib).

Then install the rest of the dependencies which should Just Work:
```
pip install numpy opencv-python mediapipe
```
## Run LEAP scripts from the viewer
There are two ways to launch a leap script from the viewer:
**(1)** Start the LEAP script at runtime via the menu: **Advanced --> Puppeteering --> Launch LEAP plug-in...**
**(2)** Alternatively Launch the viewer from the command line interface (CLI) with an option of the form:
```
    --leap "python /path/to/script.py"
```
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
`field_name` is: `'pos'`, `'rot'`, or `'local_rot'`,
and `value` is either an array of Cartesian coordinates `[x,y,z]` for `pos`
or the imaginary part `[x,y,z]` of a Quaternion (when it has a positive real component `w`) for `rot` and `local_rot`.
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
