#!/usr/bin/env python3
"""
Stripped down webcam access for testing
"""

# This is a testing program for poking at the system and finding cameras.   It is not
# used in production

import cv2
from pygrabber.dshow_graph import FilterGraph

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
