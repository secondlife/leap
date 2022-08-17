#!/usr/bin/env python3
"""\
@file puppet_utils.py
@brief

$LicenseInfo:firstyear=2022&license=viewerlgpl$
Second Life Viewer Source Code
Copyright (C) 2022, Linden Research, Inc.

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

'''
utility functions
'''

import argparse
import time
import numpy as np
import cv2
import itertools
import mediapipe as mp
import eventlet
import puppetry
from camera import Camera
from display import Display
import sys
import traceback
import logging
import glm
from math import sin, cos, pi, sqrt, atan2, asin

def pfv(vec):
    '''SPATTERS temporary debug function to print vectors'''
    outstr = '('
    outstr = outstr + ', '.join('{:.3f}'.format(float(f)) for f in vec)
    outstr = outstr + ')'
    return outstr

def quat_to_euler( w, x, y, z ):
    '''Translate quaternion into Euler angles.
       returns list in X Y Z order.'''

    out = [ 0.0, 0.0, 0.0 ]

    t0 = 2.0 * ( (w * x) + (y * z) )
    t1 = 1.0 - ( 2.0 * ( ( x * y ) + ( y * y ) ) )
    out[0] = atan2(t0, t1)

    t2 = 2.0 * ( w * y - z * x )
    t2 = min(1.0, t2)
    t2 = max(-1.0, t2)
    out[1] = asin(t2)

    t3 = 2.0 * (w * z + x * y)
    t4 = 1.0 - 2.0 * (y * y + z * z)
    out[2] = atan2(t3,t4)

    return out
    

def make_zxy_effector( name, point, output ):
    '''Switches point to from webcam-capture-frame 
    to SL-avatar-frame.
                ___
               /o o\
               \___/
                 |
     R o--+--+-+ | +-+--+--o L
                 +
                 |
                 +              z     z
                 |             /      |
               +-@-+          @--x    @--y
               |   |          |      /
               +   +          y     x
               |   |
               |   |      webcam    SL-avatar
              /   /       capture   frame
                          frame
    '''
    pos = [ float( -point[2] ), float( point[0] ), float( -point[1] )  ]
    if name in output:
        output[name]['pos'] = pos
    else:
        output[name] = { 'pos' : pos }

    return

def normalize(vec):
    return glm.normalize(glm.vec3(vec))

def magnitude(vec):
    return glm.length(glm.vec3(vec))

def get_zxy(points, index):
    '''Passed in the set of points and an index, returns a vector 3 in ZYX order'''
    return [points[index][2], \
            points[index][1], \
            points[index][0]]

def get_landmark_vector3(landmarks, index):
    '''Passed in the set of points and an index, returns a vector 3 in ZYX order'''
    return [landmarks.landmark[index].x, \
            landmarks.landmark[index].y, \
            landmarks.landmark[index].z]

def get_landmark_direction(v1, v2):
    '''Passed in two vector3, returns a directional vector from v1 to v2
       NOTE: Does not normalize!'''
    return [ v2.x - v1.x,
             v2.y - v1.y,
             v2.z - v1.z ]

def get_direction(v1, v2):
    '''Passed in two vector3, returns a directional vector from v1 to v2
       NOTE: Does not normalize!'''
    return [ v2[0] - v1[0],
             v2[1] - v1[1],
             v2[2] - v1[2] ]

def distance_3d(v1, v2):
    return magnitude(get_direction(v1, v2))

def get_dimensions(points, indicies):
    '''Given a set of points, returns bounding cube, min, max, and center'''

    xs = []
    ys = []
    zs = []
    for index in indicies:
        xs.append(points[index][0])
        ys.append(points[index][1])
        zs.append(points[index][2])
            
    minx = min(xs)
    miny = min(ys)
    minz = min(zs)
    maxx = max(xs)
    maxy = max(ys)
    maxz = max(zs)

    result={ 'min' : [minx,miny,minz],
             'max' : [maxx,maxy,maxz], 
             'height' : maxx-minx, 
             'width'  : maxy-miny,
             'depth'  : maxz-minz }
    result['center'] = [ minx + result['width']/2.0, \
                         miny + result['height']/2.0, \
                         minz + result['depth']/2.0 ]

    return result

def make_perpendicular(origin, point1, point2, distance):
    '''Using one point as an origin and2 more (non-colinear) points
       create a point perpendicular to the origin at distance.
       returns the perpendicular point'''

    #Normalized direction from orign to points on a plane
    dir1 = np.array( normalize( get_direction(origin, point1) ) )
    dir2 = np.array( normalize( get_direction(origin, point2) ) )
       
    perp_dir = np.cross(dir1, dir2) #Cross product is perp direction

    return origin + (distance * perp_dir)

def make_perpendicular_from_quat(origin, quat, distance):
    '''Create a point relative the origin in the direction 
       of the passed in quaternion at the specified distance.'''
    return None     #stubbed

def make_perpendicular_from_subset(points, ids, distance):
    '''Passed the set of points, extracts the 3 ids passed in
       as a list, assuming the first is origin and the other
       two non-colinear points.
       Returns a point perpendicular to the origin at the 
       specified distance.'''

    p2 = []
    for id in ids:
        p2.append(points[id].copy())
    return make_perpendicular(p2[0], p2[1], p2[2], distance)


def clamp(num, lim):
    '''  Clamps number to +- the passed value.'''

    if num > lim:
        num = lim
    if num < -1.0 * lim:
        num = -1.0 * lim
    return num

def get_weighted_average( val, avg, wgt ):
    '''Find the exponentially weighted average'''

    return (1-wgt)*avg + wgt*val

def get_weighted_average_vec( vec, avg_vec, wgt ):
    '''Find exponentially weighted average for vector'''

    l = len(vec)
    if len(avg_vec) != l:
        raise Exception('vectors must be same length')

    if wgt == 1.0:
        return vec.copy()

    result =[]
    for i in range(0,l):
        result.append( get_weighted_average( vec[i], avg_vec[i], wgt ) )
    return result

def get_average( dataset ):
    '''Given a set of 2d points, generate a simple average'''

    divisor = len(dataset)
    total = None

    for data in dataset:
        if total is None:
            total = np.array( data )
        else:
            total = np.add( total, data )
    return np.divide( total, float(divisor) )

def clear_average(dest):
    '''Fills with NaN'''

    for d in dest:
        d[0] =  np.double('nan')
        d[1] =  np.double('nan')
        d[2] =  np.double('nan')

def rotate_vector( point, origin, rotation ):
    '''Rotate point around origin by rotation'''
    return rotation * get_direction(origin, point)

def scale_z(factor, dest):
    '''Scales the Z aspect of all points in dest by factor'''
    for d in dest:
        d[2] = d[2] * factor

def average_landmarks(landmarks, dest, dlen, weight):
    '''Get values from the landmarks
       and apply an exponentially weighted average'''

    #dlen = len(dest)
    index=0
    while (index < dlen):
        if np.isnan(dest[index][0]):
            dest[index] = [ landmarks.landmark[index].x, \
                            landmarks.landmark[index].y, \
                            landmarks.landmark[index].z ]
        else:
            dest[index] = get_weighted_average_vec( 
                          [ landmarks.landmark[index].x, \
                            landmarks.landmark[index].y, \
                            landmarks.landmark[index].z ], \
                            dest[index], \
                            weight)
        index = index + 1

def average_sequential_landmarks(start, end, landmarks):
    '''start and end are the sequential indicies to be averaged into a centeral point.
       points is the dataset the indicies are found in.
       retuns [ x, y, z ] averaged.'''

    num = (end - start) + 1 
    avg = [ 0.0, 0.0, 0.0 ]
    for p in range(start,end+1):
        avg[0] = avg[0] + landmarks.landmark[p].x
        avg[1] = avg[1] + landmarks.landmark[p].y
        avg[2] = avg[2] + landmarks.landmark[p].z
    for a in range (0,3):
        avg[a] = avg[a] / float(num)

    return avg

def average_sequential_points(start, end, points):
    '''start and end are the sequential indicies to be averaged into a centeral point.
       points is the dataset the indicies are found in.
       retuns [ x, y, z ] averaged.'''

    num = (end - start) + 1 
    avg = [ 0.0, 0.0, 0.0 ]
    for p in range(start,end+1):
        for a in range (0,3):
            avg[a] = avg[a] + points[p][a]
    for a in range (0,3):
        avg[a] = avg[a] / float(num)

    return avg

def average_subset_points(indicies, points):
    '''indicies are the indices to a subset of points in the
       larger set of points to be averaged into a centeral point.
       retuns [ x, y, z ] averaged.'''

    num = len(indicies)
    avg = [ 0.0, 0.0, 0.0 ]
    for p in range(indicies):
        for a in range (0,3):
            avg[a] = avg[a] + points[p][a]
    for a in range (0,3):
        avg[a] = avg[a] / float(num)

    return avg

def distance_2d(a,b):
    '''Given two points, find the 2D dist between'''
    dist = None

    dx = b[0] - a[0]
    dy = b[1] - a[1]

    if dx==0:
        dist = dy
    elif dy==0:
        dist = dx
    else:
        dist = np.sqrt( (dx ** 2) + (dy ** 2) )
    return dist

def perspective_transform(x, y, mat):
    '''Uses the transformation matrix to skew points from perspective to ortho'''

    rx = ( x * mat[0][0] + y * mat[0][1] + mat[0][2] ) / \
         ( x * mat[2][0] + y * mat[2][1] + mat[2][2] )
    ry = ( x * mat[1][0] + y * mat[1][1] + mat[1][2] ) / \
         ( x * mat[2][0] + y * mat[2][1] + mat[2][2] )
    return rx,ry

def get_perspective_matrix(ortho, indicies, live_data):
    '''ortho is a simple array containing the X,Y elements of 4 points
       in the front orthographic view of the model which form a
       parallelogram.
       live_data is the observed datapoints
       indicies into live_data correspond to the points in ortho.
       These MUST be same number of elements and same order.
       Returns a transformation matrix from A to B.
    '''

    numi = len(indicies)
    live = np.zeros([numi,2], dtype="float32")
    
    for i in range(0, numi):
        live[i][0] = live_data[indicies[i]][0]
        live[i][1] = live_data[indicies[i]][1]

    return cv2.getPerspectiveTransform(live, ortho) 
