#!/usr/bin/env python3
"""\
@file webcam_test.py 
Stripped down webcam access for testing

$LicenseInfo:firstyear=2010&license=viewerlgpl$
Second Life Viewer Source Code
Copyright (C) 2022-2022, Linden Research, Inc.

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

# This is a testing program for poking at the system and finding cameras.   It is not 
# used in production

# check for pygrabber
try:
    from pygrabber.dshow_graph import FilterGraph
except ModuleNotFoundError as ex:
    print(str(ex))
    print("Try installing with 'pip install pygrabber'")
    exit(-1)

try:
    import cv2
except ModuleNotFoundError as ex:
    print(str(ex))
    print("Try installing with 'pip install opencv-python'")
    exit(-1)

# -------------------------------------------------------------------------------

def getCameraNames():
    """ Read cameras from the OS """
    f_graph = FilterGraph()
    cam_names = f_graph.get_input_devices()
    return cam_names

def returnInstalledCameras():
    """ returns tuples of (name, index) for cameras on the system """
    cams = []
    
    print("Searching for cameras...")
    cam_names = getCameraNames()

    index = 0
    while index < len(cam_names):
        cap = cv2.VideoCapture(index)
        if cap.read()[0]:
            print("VideoCapture index %d is valid for %s" % (index, cam_names[index]))
            cams.append((cam_names[index], index))
            cap.release()
        else:
            print("VideoCapture index %d failed for %s" % (index, cam_names[index]))
        index += 1
    return cams



def main():
  
    cams = returnInstalledCameras()
    if len(cams) == 0:
        print("No cameras detected")
        return
  
    # define a video capture object
    selected_camera = 0
    
    if selected_camera >= len(cams):
        print("selected_camera is out of range:  %d vs %d" % (selected_camera, len(cams)))
        return

    camera_name = cams[selected_camera][0]
    camera_index = cams[selected_camera][1]
    print("Using camera %s index %d" % (camera_name, camera_index))
    vid = cv2.VideoCapture(camera_index)
  
    while(True):
      
        # Capture the video frame
        # by frame
        ret, frame = vid.read()
  
        # Display the resulting frame
        cv2.imshow('frame', frame)
      
        # the 'q' key is set to quit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
  
    # After the loop release the cap object
    vid.release()
    # Destroy all the windows
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
