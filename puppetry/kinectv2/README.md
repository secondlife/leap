An example of using the Kinectv2 sensor to capture live mocap puppetry animations

PREREQUISITES:
    Second Life Viewer supporting the most recent puppetry features and protocol format
    Kinect v2 sdk from https://www.microsoft.com/en-us/download/details.aspx?id=44561
    Install the https://github.com/Kinect/PyKinect2 python library latest code
    Install pygame: https://www.pygame.org/wiki/GettingStarted

FIRST TIME:
    After installing the Kinect v2 sdk from Microsoft, confirm have a working Kinect v2 device.
    Modify the PyKinect2 library code with the updates listed here in ReadMe_PyKinect2_diffs.txt
    Run the PyKinect2\examples\PyKinectBodyGame.py program to confirm you have a working python installation

IN SECOND LIFE:
    Go to a region where the Puppetry feature is supported
    Under the Advanced / Puppetry / Launch plug-in menu command, find and open the \leap\puppetry\kinectv2\kinectv2_puppetry.py module.
    If nothing happens, look in the SecondLife viewer log for errors.   You probably need to fix the various required code

MOCAP NOTES:
    The first step here is to lower your expectations.   This is an experimental plug-in.
    In the initial version, the positions of the neck, shoulder and elbow joints are read from the Kinect device and used to calculate the rotation for your avatar.   The SL skeleton motion is 2D only.
    The "Camera" button turns displaying the Kinect color camera live image on and off.
    The "Info" button toggles the black box with some diganoistic data
    This works best if you are centered and standing facing the camera, at least a meter away so it can locate your upper body
    Hold your arms straight out to the side, elbow at a right angle and hands up, plam facing the Kinect.  The Kinect may take a few seconds to start tracking.   Experiment with lighting, clothing and background to improve motion capture.

OPEN SOURCE:
    Want to add features or talk about Puppetry in Second Life?   Join the Second Life community through our forum, user group meetings, Discord channel and in-world regions.  Check out https://secondlife.com/ for more


