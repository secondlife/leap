The current repository at https://github.com/Kinect/PyKinect2 is stale and needs a few
minor changes.   You'll need to update your version to work with these alterations.  Don't
be intimated by them, it's actually pretty simple:

    1) time.clock() calls must change to time.perf_counter()
    2) one import version check should be removed or adjusted to your version


diff --git a/pykinect2/PyKinectRuntime.py b/pykinect2/PyKinectRuntime.py
index 0454875..9dd0c40 100644
--- a/pykinect2/PyKinectRuntime.py
+++ b/pykinect2/PyKinectRuntime.py
@@ -163,7 +163,7 @@ class PyKinectRuntime(object):
         self._last_long_exposure_infrared_frame = None
         self._last_audio_frame = None

-        start_clock = time.clock()
+        start_clock = time.perf_counter()
         self._last_color_frame_access = self._last_color_frame_time = start_clock
         self._last_body_frame_access = self._last_body_frame_time = start_clock
         self._last_body_index_frame_access = self._last_body_index_frame_time = start_clock
@@ -243,7 +243,7 @@ class PyKinectRuntime(object):
         with self._color_frame_lock:
             if self._color_frame_data is not None:
                 data = numpy.copy(numpy.ctypeslib.as_array(self._color_frame_data, shape=(self._color_frame_data_capacity.value,)))
-                self._last_color_frame_access = time.clock()
+                self._last_color_frame_access = time.perf_counter()
                 return data
             else:
                 return None
@@ -252,7 +252,7 @@ class PyKinectRuntime(object):
         with self._infrared_frame_lock:
             if self._infrared_frame_data is not None:
                 data = numpy.copy(numpy.ctypeslib.as_array(self._infrared_frame_data, shape=(self._infrared_frame_data_capacity.value,)))
-                self._last_infrared_frame_access = time.clock()
+                self._last_infrared_frame_access = time.perf_counter()
                 return data
             else:
                 return None
@@ -261,7 +261,7 @@ class PyKinectRuntime(object):
         with self._depth_frame_lock:
             if self._depth_frame_data is not None:
                 data = numpy.copy(numpy.ctypeslib.as_array(self._depth_frame_data, shape=(self._depth_frame_data_capacity.value,)))
-                self._last_depth_frame_access = time.clock()
+                self._last_depth_frame_access = time.perf_counter()
                 return data
             else:
                 return None
@@ -270,7 +270,7 @@ class PyKinectRuntime(object):
         with self._body_index_frame_lock:
             if self._body_index_frame_data is not None:
                 data = numpy.copy(numpy.ctypeslib.as_array(self._body_index_frame_data, shape=(self._body_index_frame_data_capacity.value,)))
-                self._last_body_index_frame_access = time.clock()
+                self._last_body_index_frame_access = time.perf_counter()
                 return data
             else:
                 return None
@@ -278,7 +278,7 @@ class PyKinectRuntime(object):
     def get_last_body_frame(self):
         with self._body_frame_lock:
             if self._body_frame_bodies is not None:
-                self._last_body_frame_access = time.clock()
+                self._last_body_frame_access = time.perf_counter()
                 return self._body_frame_bodies.copy()
             else:
                 return None
@@ -340,7 +340,7 @@ class PyKinectRuntime(object):
             try:
                 with self._color_frame_lock:
                     colorFrame.CopyConvertedFrameDataToArray(self._color_frame_data_capacity, self._color_frame_data, PyKinectV2.ColorImageFormat_Bgra)
-                    self._last_color_frame_time = time.clock()
+                    self._last_color_frame_time = time.perf_counter()
             except:
                 pass
             colorFrame = None
@@ -358,7 +358,7 @@ class PyKinectRuntime(object):
             try:
                 with self._depth_frame_lock:
                     depthFrame.CopyFrameDataToArray(self._depth_frame_data_capacity, self._depth_frame_data)
-                    self._last_depth_frame_time = time.clock()
+                    self._last_depth_frame_time = time.perf_counter()
             except:
                 pass
             depthFrame = None
@@ -378,7 +378,7 @@ class PyKinectRuntime(object):
                 with self._body_frame_lock:
                     bodyFrame.GetAndRefreshBodyData(self._body_frame_data_capacity, self._body_frame_data)
                     self._body_frame_bodies = KinectBodyFrameData(bodyFrame, self._body_frame_data, self.max_body_count)
-                    self._last_body_frame_time = time.clock()
+                    self._last_body_frame_time = time.perf_counter()

                 # need these 2 lines as a workaround for handling IBody referencing exception
                 self._body_frame_data = None
@@ -402,7 +402,7 @@ class PyKinectRuntime(object):
             try:
                 with self._body_index_frame_lock:
                     bodyIndexFrame.CopyFrameDataToArray(self._body_index_frame_data_capacity, self._body_index_frame_data)
-                    self._last_body_index_frame_time = time.clock()
+                    self._last_body_index_frame_time = time.perf_counter()
             except:
                 pass
             bodyIndexFrame = None
@@ -419,7 +419,7 @@ class PyKinectRuntime(object):
             try:
                 with self._infrared_frame_lock:
                     infraredFrame.CopyFrameDataToArray(self._infrared_frame_data_capacity, self._infrared_frame_data)
-                    self._last_infrared_frame_time = time.clock()
+                    self._last_infrared_frame_time = time.perf_counter()
             except:
                 pass
             infraredFrame = None
diff --git a/pykinect2/PyKinectV2.py b/pykinect2/PyKinectV2.py
index 6fdb0ca..5823642 100644
--- a/pykinect2/PyKinectV2.py
+++ b/pykinect2/PyKinectV2.py
@@ -2865,7 +2865,7 @@ __all__ = [ 'IKinectSensor', 'IAudioBeamSubFrame',
            'JointType_HipLeft', 'ColorImageFormat_Rgba',
            'IColorCameraSettings', '_DetectionResult',
            'IColorFrameReader', 'ColorImageFormat_Yuy2', '_Activity']
-from comtypes import _check_version; _check_version('')
+#from comtypes import _check_version; _check_version('1.1.11')


 KINECT_SKELETON_COUNT = 6
