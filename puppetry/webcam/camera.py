import cv2
import numpy as np


class Camera:
    '''A utility class to manage the camera and captured images'''

    def __init__(self, camera_num = 0):
        self.device = None          #Handler to the webcam
        self.capture_id = int(camera_num) #Which camera to use
        self.downsample = None      #Use [x,y] to downsample
        self.bgr_image = None       #Image in Blue Green Red order
        self.rgb_image = None       #Image in Red Green Blue order
        self.size = [0,0]           #Contains captured image dimensions
        self.matrix = None          #Details about the camera
        self.dist_coeff = None      #Distortion coefficients


    def configure_camera(self):
        '''
            Initialize the capture device to the selected camera
            set the sample size to be read from the camera
        '''

        self.device = cv2.VideoCapture(self.capture_id)

        #If capture dimensions is not None, assume it is a
        #2 item array descripting the X and Y dimensions of
        #the image to be taken from the camera.
        #A smaller scan area will process faster.
        if self.downsample is not None:
            self.device.set(cv2.CAP_PROP_FRAME_WIDTH, \
                                    self.downsample[0])
            self.device.set(cv2.CAP_PROP_FRAME_HEIGHT, \
                                    self.downsample[1])
        self.get_rgb_frame()    #Get a frame to finish init.

        # Camera internals
        focal_length = self.size[0]
        center = (self.size[0]/2, self.size[1]/2)
        self.matrix = np.array( [[focal_length, 0, center[0]],
                                 [0, focal_length, center[1]],
                                 [0, 0, 1]],
                                 dtype = "double" )

        #Just pretend the camera has no distortion.
        self.dist_coeffs = np.zeros((4,1))

    def get_rgb_frame(self):
        '''Captures a frame from the camera, converts it to rgb
            and returns the image or None if failed'''

        ret, self.bgr_image = self.device.read()

        if not ret:
            return False

        self.size[1], self.size[0], _ = self.bgr_image.shape
        self.rgb_image = cv2.cvtColor(self.bgr_image, cv2.COLOR_BGR2RGB)

        return True

