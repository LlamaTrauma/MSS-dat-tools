import struct
import math
import random

def itb (val, n):
    return val.to_bytes(n, 'big')

def ftb(val):
    return bytearray(struct.pack(">f", val + 0))

def bti (b):
    return int.from_bytes(b, 'big')

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
    if highest * (1 << (quantizeInfo & 0x0F)) > 30000:
        shift = math.floor(math.log2(30000/highest))
        quantizeInfo = 0x30 + shift
    return quantizeInfo

def rand():
    return random.random()