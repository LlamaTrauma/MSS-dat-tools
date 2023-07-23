import numpy as np
import math
import struct

def itb (val, n):
    return val.to_bytes(n, 'big')

def nullCoalesce(v, a):
    if v == None:
        return a
    return v

# https://automaticaddison.com/how-to-convert-a-quaternion-to-a-rotation-matrix/
def quaternion_rotation_matrix(Q):
    """
    Covert a quaternion into a full three-dimensional rotation matrix.
 
    Input
    :param Q: A 4 element array representing the quaternion (q0,q1,q2,q3) 
 
    Output
    :return: A 3x3 element matrix representing the full 3D rotation matrix. 
             This rotation matrix converts a point in the local reference 
             frame to a point in the global reference frame.
    """
    # Extract the values from Q
    q0 = Q[3]
    q1 = Q[0]
    q2 = Q[1]
    q3 = Q[2]

    l = math.sqrt(q0*q0+q1*q1+q2*q2+q3*q3)
    if l < 0.001:
        return np.identity(4)
    else:
        q0 /= l
        q1 /= l
        q2 /= l
        q3 /= l

    # First row of the rotation matrix
    r00 = 2 * (q0 * q0 + q1 * q1) - 1
    r01 = 2 * (q1 * q2 - q0 * q3)
    r02 = 2 * (q1 * q3 + q0 * q2)
     
    # Second row of the rotation matrix
    r10 = 2 * (q1 * q2 + q0 * q3)
    r11 = 2 * (q0 * q0 + q2 * q2) - 1
    r12 = 2 * (q2 * q3 - q0 * q1)
     
    # Third row of the rotation matrix
    r20 = 2 * (q1 * q3 - q0 * q2)
    r21 = 2 * (q2 * q3 + q0 * q1)
    r22 = 2 * (q0 * q0 + q3 * q3) - 1
     
    # 3x3 rotation matrix
    rot_matrix = np.array([[r00, r01, r02, 0],
                           [r10, r11, r12, 0],
                           [r20, r21, r22, 0],
                           [0,   0,   0,   1]])
                            
    return rot_matrix

def getQuantizedData(f, offset, count, dimensions, quantizeInfo):
    dataArr = []
    positionStore = f.tell()
    f.seek(offset)
    for i in range(count):
        component = []
        for j in range(dimensions):
            data = 0
            format = quantizeInfo >> 4
            shift = quantizeInfo & 0b00001111
            if format not in [3, 4, 7, 0xa, 0]:
                format = 4
            # 3 is short, 4 is float, documentation is outdated. This isn't correct for some formats probably
            # print("format is " + hex(format))
            # print (hex(parent.absolute + offset))
            # print(hex(quantizeInfo))
            bytes = f.read({3: 2, 0: 2, 4: 4, 0xa: 4, 7: 4}[format])
            data = struct.unpack('>'+{3: 'h', 0: 'h', 4: 'f', 0xa: 'f', 7: 'f'}[format], bytes)[0]
            data /= 1 << shift
            component.append(data)
        dataArr.append(component)
    f.seek(positionStore)
    return dataArr