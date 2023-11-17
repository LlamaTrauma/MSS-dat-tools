import numpy as np
import math
from base import *
import struct

def itb (val, n):
    return val.to_bytes(n, 'big')

def bti (b):
    return int.from_bytes(b, 'big')

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
    q0 = Q[0]
    q1 = Q[1]
    q2 = Q[2]
    q3 = Q[3]

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

def scaling_matrix(arr):
    x = arr[0]
    y = arr[1]
    z = arr[2]
    return np.array([
                [x, 0, 0, 0],
                [0, y, 0, 0],
                [0, 0, z, 0],
                [0, 0, 0, 1],
            ])

def translation_matrix(arr):
    x = arr[0]
    y = arr[1]
    z = arr[2]
    # return np.array([
    #             [1, 0, 0, 0],
    #             [0, 1, 0, 0],
    #             [0, 0, 1, 0],
    #             [x, y, z, 1]
    #         ])
    return np.array([
                [1, 0, 0, x],
                [0, 1, 0, y],
                [0, 0, 1, z],
                [0, 0, 0, 1]
            ])

def translation_diff(a, b):
    return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]

def scaling_diff(a, b):
    return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]

def quaternion_inverse(q):
    inv = [q[0], -q[1], -q[2], -q[3]]
    length = (q[0] ** 2 + q[1] ** 2 + q[2] ** 2 + q[3] ** 2) ** 0.5
    return [inv[0]/length, inv[1]/length, inv[2]/length, inv[3]/length]

def quaternion_multiply(Q0,Q1):
    # Stolen from https://automaticaddison.com/how-to-multiply-two-quaternions-together-using-python/
    """
    Multiplies two quaternions.
 
    Input
    :param Q0: A 4 element array containing the first quaternion (q01,q11,q21,q31) 
    :param Q1: A 4 element array containing the second quaternion (q02,q12,q22,q32) 
 
    Output
    :return: A 4 element array containing the final quaternion (q03,q13,q23,q33) 
 
    """
    # Extract the values from Q0
    w0 = Q0[0]
    x0 = Q0[1]
    y0 = Q0[2]
    z0 = Q0[3]
     
    # Extract the values from Q1
    w1 = Q1[0]
    x1 = Q1[1]
    y1 = Q1[2]
    z1 = Q1[3]
     
    # Computer the product of the two quaternions, term by term
    Q0Q1_w = w0 * w1 - x0 * x1 - y0 * y1 - z0 * z1
    Q0Q1_x = w0 * x1 + x0 * w1 + y0 * z1 - z0 * y1
    Q0Q1_y = w0 * y1 - x0 * z1 + y0 * w1 + z0 * x1
    Q0Q1_z = w0 * z1 + x0 * y1 - y0 * x1 + z0 * w1
     
    # Create a 4 element array containing the final quaternion
    final_quaternion = np.array([Q0Q1_w, Q0Q1_x, Q0Q1_y, Q0Q1_z])
     
    # Return a 4 element array containing the final quaternion (q02,q12,q22,q32) 
    return final_quaternion

def quaternion_diff(a, b):
    return quaternion_multiply(a, quaternion_inverse(b))

def mtosrt(M):
    # print(M)
    translate = [M[3][0], M[3][1], M[3][2]]

    M[3][0] = 0
    M[3][1] = 0
    M[3][2] = 0

    scale = [1, 1, 1]
    # scale = [(M[0][0] ** 2 + M[1][0] ** 2 + M[2][0] ** 2) ** 0.5,
    #          (M[0][1] ** 2 + M[1][1] ** 2 + M[2][1] ** 2) ** 0.5,
    #          (M[0][2] ** 2 + M[1][2] ** 2 + M[2][2] ** 2) ** 0.5]

    # M[0][0] /= scale[0]
    # M[1][0] /= scale[0]
    # M[2][0] /= scale[0]

    # M[0][1] /= scale[1]
    # M[1][1] /= scale[1]
    # M[2][1] /= scale[1]

    # M[0][2] /= scale[2]
    # M[1][2] /= scale[2]
    # M[2][2] /= scale[2]

    rotation = rotationMatrixToQuaternion3(M[:3][:3])

    return [scale, rotation, translate]

# fully stolen from the quaternion module source
def rotationMatrixToQuaternion3(m):
    rot = np.array(m, copy=False)
    shape = rot.shape[:-2]
    diagonals = np.empty(shape+(4,))
    diagonals[..., 0] = rot[..., 0, 0]
    diagonals[..., 1] = rot[..., 1, 1]
    diagonals[..., 2] = rot[..., 2, 2]
    diagonals[..., 3] = rot[..., 0, 0] + rot[..., 1, 1] + rot[..., 2, 2]

    indices = np.argmax(diagonals, axis=-1)

    q = diagonals  # reuse storage space
    indices_i = (indices == 0)
    if np.any(indices_i):
        if indices_i.shape == ():
            indices_i = Ellipsis
        rot_i = rot[indices_i, :, :]
        q[indices_i, 0] = rot_i[..., 2, 1] - rot_i[..., 1, 2]
        q[indices_i, 1] = 1 + rot_i[..., 0, 0] - rot_i[..., 1, 1] - rot_i[..., 2, 2]
        q[indices_i, 2] = rot_i[..., 0, 1] + rot_i[..., 1, 0]
        q[indices_i, 3] = rot_i[..., 0, 2] + rot_i[..., 2, 0]
    indices_i = (indices == 1)
    if np.any(indices_i):
        if indices_i.shape == ():
            indices_i = Ellipsis
        rot_i = rot[indices_i, :, :]
        q[indices_i, 0] = rot_i[..., 0, 2] - rot_i[..., 2, 0]
        q[indices_i, 1] = rot_i[..., 1, 0] + rot_i[..., 0, 1]
        q[indices_i, 2] = 1 - rot_i[..., 0, 0] + rot_i[..., 1, 1] - rot_i[..., 2, 2]
        q[indices_i, 3] = rot_i[..., 1, 2] + rot_i[..., 2, 1]
    indices_i = (indices == 2)
    if np.any(indices_i):
        if indices_i.shape == ():
            indices_i = Ellipsis
        rot_i = rot[indices_i, :, :]
        q[indices_i, 0] = rot_i[..., 1, 0] - rot_i[..., 0, 1]
        q[indices_i, 1] = rot_i[..., 2, 0] + rot_i[..., 0, 2]
        q[indices_i, 2] = rot_i[..., 2, 1] + rot_i[..., 1, 2]
        q[indices_i, 3] = 1 - rot_i[..., 0, 0] - rot_i[..., 1, 1] + rot_i[..., 2, 2]
    indices_i = (indices == 3)
    if np.any(indices_i):
        if indices_i.shape == ():
            indices_i = Ellipsis
        rot_i = rot[indices_i, :, :]
        q[indices_i, 0] = 1 + rot_i[..., 0, 0] + rot_i[..., 1, 1] + rot_i[..., 2, 2]
        q[indices_i, 1] = rot_i[..., 2, 1] - rot_i[..., 1, 2]
        q[indices_i, 2] = rot_i[..., 0, 2] - rot_i[..., 2, 0]
        q[indices_i, 3] = rot_i[..., 1, 0] - rot_i[..., 0, 1]

    q /= np.linalg.norm(q, axis=-1)[..., np.newaxis]

    return q

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

def quantizedDataSize (quantizeInfo):
    format = quantizeInfo >> 4
    if format not in [3, 4, 7, 0xa, 0]:
        format = 4
    return {3: 2, 0: 2, 4: 4, 0xa: 4, 7: 4}[format]

class Object(object):
    def __init__(self) -> None:
        pass

class SRT(FileChunk):
    def analyze(self):
        self.values = ['{:02x}'.format(self.byte())]
        self.read(3)
        self.values += ['{:.2f}'.format(self.float()) for x in range(12)]
        self.seek(0)
        self.type = self.byte()
        self.read(3)
        if self.type in [0x4, 0x8, 0xc]:
            self.scale = [self.float(), self.float(), self.float()]
            self.quaternion = [self.float(), self.float(), self.float(), self.float()]
            self.quaternion = [-self.quaternion[3], self.quaternion[0], self.quaternion[1], self.quaternion[2]]
            self.translation = [self.float(), self.float(), self.float()]
            self.transform = np.matmul(np.matmul(scaling_matrix(self.scale), quaternion_rotation_matrix(self.quaternion)), translation_matrix(self.translation))
            # self.transform = np.matmul(np.matmul(translation_matrix(self.translation), quaternion_rotation_matrix(self.quaternion)), scaling_matrix(self.scale))
        else:
            self.scale = [1, 1, 1]
            self.quaternion = [1, 0, 0, 0]
            self.translation = [0, 0, 0]
            self.transform = np.identity(4)
        return self

    def to_string(self):
        if self.type == None:
            return "none"
        out = "format: " + '{:02x}'.format(self.type)
        out = "data: " + ', '.join([x for x in self.values])
        return out

def original_pos_method_1(transform_arr, weight_arr, final_pos):
    b = np.array([*final_pos, 1])
    c = np.zeros((4, 4))
    for ind, transform in enumerate(transform_arr):
        weight = weight_arr[ind]
        for i in range(4):
            for j in range(4):
                c[i][j] += transform[i][j] * weight
    # following is a bunch of longhand for 'return np.matmul(b, np.linalg.inv(c))[:3]'
    # b = out * c
    c = c.transpose()
    b = b.transpose()
    # b_t = c_t * out_t
    q, r = np.linalg.qr(c)
    # b_t = q * r * out_t
    # r * out_t = q_t * b_t
    c = np.matmul(q.transpose(), b)
    out = [0, 0, 0, 0]
    out[3] = c[3] / r[3][3]
    out[2] = (c[2] - r[2][3] * out[3]) / r[2][2]
    out[1] = (c[1] - r[1][3] * out[3] - r[1][2] * out[2]) / r[1][1]
    out[0] = (c[0] - r[0][3] * out[3] - r[0][2] * out[2] - r[0][1] * out[1]) / r[0][0]
    out = [x / out[3] for x in out[:3]]
    return out[:3]

def original_pos_method_2(transform_arr, weight_arr, final_pos):
    b = np.array([*final_pos, 1])
    c = np.zeros((4, 4))
    out = [0, 0, 0]
    total_weight = 0
    for ind, transform in enumerate(transform_arr):
        weight = weight_arr[ind]
        initial = np.matmul(b, np.linalg.inv(transform))
        out = [out[i] + initial[i] * weight for i in range(3)]
        total_weight += weight
    return [out[i] / total_weight for i in range(3)]