import struct
import math
import os
import numpy as np

MODEL_SCALE = 1/4

def itb (val, n):
    return int(val).to_bytes(n, 'big')

def ftb(f):
    return struct.pack('>f', f)

def bti (b):
    return int.from_bytes(b, 'big')

def it2c(x, n):
    val = x & ((1 << (n - 1)) - 1)
    val -= x & (1 << (n - 1))
    return val

def writeQuantizedData (quantizeInfo, data):
    format = quantizeInfo >> 4
    shift = quantizeInfo & 0b00001111
    format = {3: 'h', 0: 'h', 4: 'f', 0xa: 'f', 7: 'f'}[format]
    shift = 1 << shift
    shiftedData = []
    if format == 'f':
        shiftedData = [x for x in data]
    else:
        shiftedData = [math.floor(x * shift) for x in data]
    out = bytearray()
    for num in shiftedData:
        out.extend(struct.pack('>' + format, num))
    return out

def align32 (x):
    if x % 0x20 == 0:
        return x
    return x + 0x20 - (x % 0x20)

def offset32(x):
    if x % 0x20 == 0:
        return 0
    return 0x20 - (x % 0x20)

def maxShift (quantizeInfo, data):
    highest = max([abs(x) for x in data])
    highest = max(highest, 1)
    if highest * (1 << (quantizeInfo & 0x0F)) > 30000:
        shift = math.floor(math.log2(30000/highest))
        quantizeInfo = 0x30 + shift
    return quantizeInfo

def maxHalfShift (data):
    highest = max([abs(x) for x in data])
    highest = max(highest, 1)
    shift = math.floor(math.log2(30000/highest))
    return shift

def png_to_tpl(png_path, tpl_path):
    os.system('wimgt encode --transform="TPL.CMPR" -d ' + tpl_path + ' "' + png_path + '"')

def mtosrt(M):
    M = np.copy(M)
    # print(M)
    translate = [M[0][3], M[1][3], M[2][3]]

    M[0][3] = 0
    M[1][3] = 0
    M[2][3] = 0

    # scale = [1, 1, 1]
    scale = [(M[0][0] ** 2 + M[1][0] ** 2 + M[2][0] ** 2) ** 0.5,
             (M[0][1] ** 2 + M[1][1] ** 2 + M[2][1] ** 2) ** 0.5,
             (M[0][2] ** 2 + M[1][2] ** 2 + M[2][2] ** 2) ** 0.5]

    M[0][0] /= scale[0]
    M[1][0] /= scale[0]
    M[2][0] /= scale[0]

    M[0][1] /= scale[1]
    M[1][1] /= scale[1]
    M[2][1] /= scale[1]

    M[0][2] /= scale[2]
    M[1][2] /= scale[2]
    M[2][2] /= scale[2]

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

def pad32(a):
    offby = 0x20 - a % 0x20
    if offby == 0x20:
        offby = 0
    newa = a + offby
    return newa, offby

def euler_to_quaternion(roll, pitch, yaw):
    qx = np.sin(roll/2) * np.cos(pitch/2) * np.cos(yaw/2) - np.cos(roll/2) * np.sin(pitch/2) * np.sin(yaw/2)
    qy = np.cos(roll/2) * np.sin(pitch/2) * np.cos(yaw/2) + np.sin(roll/2) * np.cos(pitch/2) * np.sin(yaw/2)
    qz = np.cos(roll/2) * np.cos(pitch/2) * np.sin(yaw/2) - np.sin(roll/2) * np.sin(pitch/2) * np.cos(yaw/2)
    qw = np.cos(roll/2) * np.cos(pitch/2) * np.cos(yaw/2) + np.sin(roll/2) * np.sin(pitch/2) * np.sin(yaw/2)
 
    return [qw, qx, qy, qz]

def quaternion_to_euler(w, x, y, z):
    t0 = +2.0 * (w * x + y * z)
    t1 = +1.0 - 2.0 * (x * x + y * y)
    roll_x = math.atan2(t0, t1)
    
    t2 = +2.0 * (w * y - z * x)
    t2 = +1.0 if t2 > +1.0 else t2
    t2 = -1.0 if t2 < -1.0 else t2
    pitch_y = math.asin(t2)
    
    t3 = +2.0 * (w * z + x * y)
    t4 = +1.0 - 2.0 * (y * y + z * z)
    yaw_z = math.atan2(t3, t4)
    
    return roll_x, pitch_y, yaw_z # in radians