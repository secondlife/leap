import matplotlib.pyplot as plot
from mpl_toolkits.mplot3d import Axes3D


class Plot:
    '''Plots landmarks in a -1 to 1 space.'''

    def __init__(self):
        self.interval = 3       #Plot every nth frame.
        self.frame_number = 0   #Last recorded frame number.
        self.pose_pts = [ [], [], [] ]      #Raw pose data.
        self.output_pts = [ [], [], [] ]    #Points being sent to viewer.
        self.perp_pts = [ [], [], [] ]      #Perpendiculars for rotations to viewer.

        plot.ion()      #Turn on interactive mode
        #The figsize=(5,5) somehow sets the window size
        self.figure = plot.figure(figsize=(5,5))

        #Draw the axis
        self.axis = Axes3D(self.figure)
        #Elevation and azimuth are in degrees.
        #self.axis.view_init(elev=120, azim=90)
        self.axis.view_init(elev=0, azim=0)

        # setting title and labels
        self.axis.set_title("Camera data")
        self.axis.set_xlabel('X-axis')
        self.axis.set_ylabel('Y-axis')
        self.axis.set_zlabel('Z-axis')

        # set the range of the graphed area
        self.axis.set_xlim(-1.0, 1.0)
        self.axis.set_ylim(-1.0, 1.0)
        self.axis.set_zlim(-1.0, 1.0)

        self.plotted_pose = None
        self.plotted_output = None
        self.plotted_perp = None

    def set_frame_number(self, frame_number):
        self.frame_number = frame_number

    def flush(self):
        '''Flush the plotted points'''
        self.pose_pts = [ [], [], [] ]
        self.output_pts = [ [], [], [] ]
        self.perp_pts = [ [], [], [] ]

    def add_perp_point(self, point):
        '''Add a point to the perpendicular data to be plotted.'''

        if (self.frame_number % self.interval != 0):
            return

        self.perp_pts[0].append(point[0])
        self.perp_pts[1].append(point[1]*-1.0)
        self.perp_pts[2].append(point[2])

    def add_output_point(self, point):
        '''Add a point to the output data to be plotted.'''

        if (self.frame_number % self.interval != 0):
            return

        self.output_pts[0].append(point[0])
        self.output_pts[1].append(point[1]*-1.0)
        self.output_pts[2].append(point[2])

    def add_pose_landmarks(self, landmarks):
        '''Add landmarks to pose data to be plotted'''

        if (self.frame_number % self.interval != 0):
            return

        for landmark in landmarks.landmark:
            #Don't draw landmarks we can't really see.
            if landmark.visibility < 0.5:
                continue

            #NOTE:  Axis are deliberately swapped due to viewport
            # rotation's poor behavior.
            self.pose_pts[0].append(landmark.x)
            self.pose_pts[1].append(landmark.y*-1.0)
            self.pose_pts[2].append(landmark.z)

    def stop(self):
        '''Releases the plot'''
        plot.cla()

    def draw(self):
        if (self.frame_number % self.interval != 0):
            return

        if self.plotted_pose is not None:
            self.plotted_pose.remove()
        self.plotted_pose = self.axis.scatter( \
                                self.pose_pts[0], \
                                self.pose_pts[1], \
                                self.pose_pts[2], \
                                color='green')

        if self.plotted_output is not None:
            self.plotted_output.remove()
        self.plotted_output = self.axis.scatter( \
                                self.output_pts[0], \
                                self.output_pts[1], \
                                self.output_pts[2], \
                                color='red')

        if self.plotted_perp is not None:
            self.plotted_perp.remove()
        self.plotted_perp = self.axis.scatter( \
                                self.perp_pts[0], \
                                self.perp_pts[1], \
                                self.perp_pts[2], \
                                color='cyan')
        plot.draw()
        plot.pause(0.01)
        self.flush()
