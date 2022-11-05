import numpy as np

class Model:
    '''Model contains data that pertains to a generic notion of a person
       in T-Pose and provides a frame of reference for comparision against 
       the live-capture'''

    #Key points on the face that we use for identifying the rotation
    face_points = np.array([      # 3D model points.
       (   0.0,    0.0,    0.0),             # Nose tip
       (   0.0, -330.0,  -65.0),        # Chin
       (-225.0,  170.0, -135.0),     # Left eye left corner
       ( 225.0,  170.0, -135.0),      # Right eye right corner
       (-150.0, -150.0, -125.0),    # Left Mouth corner
       ( 150.0, -150.0, -125.0)      # Right mouth corner
    ])

    #Key points on the hands we use for identifying the rotation. wrist+base of fingers
    #NOTE:  There is no 'Heel' in the model. This is created by taking the wrist position
    #and adding Pinky1.x - Index1.x to X.   
    #L/R U/D Z
    hand_points = {
        'Left': np.array([
            ( 0.38233915, 0.34869850, -0.01617340), #Left Wrist
            ( 0.40562886, 0.34481689, -0.00517549), #Index1Left
            ( 0.40821660, 0.34481689, -0.01682033), #Middle1Left
            ( 0.40692270, 0.34352300, -0.02458357), #Ring1Left
            ( 0.39851254, 0.34481689, -0.03169986), #Pinky1Left
            ( 0.37522283, 0.34869850, -0.01617340) #Left Heel (See NOTE above)
                        ]),
        'Right': np.array([
            ( -0.38233915, 0.34869850, -0.01617340), #Right Wrist
            ( -0.40562886, 0.34481689, -0.00517549), #Index1Right
            ( -0.40821660, 0.34481689, -0.01682033), #Middle1Right
            ( -0.40692270, 0.34352300, -0.02458357), #Ring1Right
            ( -0.39851254, 0.34481689, -0.03169986), #Pinky1Right
            ( -0.37522283, 0.34869850, -0.01617340)  #Right Heel (See NOTE above)
                                ]) }
    hand_unit = 0.1108114 #0.0568304 + 0.053981 wrist to index1 + wrist to pinky1
    hand_width = 0.1

class LandmarkIndicies:
    '''Subsets of indicies into the Mediapipe data, used mostly for translating
       between the observed points in the image and the joints in the avatar.'''

    #IDs ot the points that identify orientation of the face.
    #Orientation landmarks are in the same order as model_points
    face_orientation = [
          1,    #Nose tip
        175,    #Chin
        130,    #Left eye left corner
        359,    #Right eye right corner
         62,    #Left Mouth Corner
        308 ]   #Right mouth corner

    #Landmark IDs which define the plane of the face.
    face_rect = [ 54, 284, 352, 123 ]  #Top left,right; bottom right, left

    #ID to points ued to orient the face.
    #NOTE:  21 does NOT exist in the model.  We manufacture it.
    hand_orientation = [ 0, 5, 9, 13, 17, 21 ]

    left_arm_visibility  = [ 23, 15, 13, 11]
    right_arm_visibility = [ 24, 16, 14, 12 ]
    lower = [23, 24, 25, 26, 27, 28]

    #Indicies of the fingertips in the tracking model.
    fingertips = { 'Thumb':4, \
                   'Index':8, \
                   'Middle':12, \
                   'Ring':16, \
                   'Pinky':20 }
    fingerbases = { 'Thumb':1, \
                   'Index':5, \
                   'Middle':9, \
                   'Ring':13, \
                   'Pinky':17 }
