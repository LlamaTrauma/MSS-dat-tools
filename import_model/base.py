import warnings
import struct
import os
import shutil
import pprint
pp = pprint.PrettyPrinter(indent=0)

def tabs(n):
    return '    ' * n

def intFromBytes(b):
    return int.from_bytes(b, 'big')

# Abstract
class SequentialData:
    def __init__(self, f, s, l = -1, name="unnamed"):
        self.f = f
        self.name = name
        self.offset = s
        if l < 0:
            self.f.seek(0, 2)
            self.length = self.f.tell()
            self.f.seek(0)
        else:
            self.length = l
        self.unassigned = [[0, self.length]]
        self.children = []
        self.parent = None
        self.absolute = s
        self.pos = 0

    def tell(self):
        return self.pos

    def seek(self, addr):
        self.pos = addr

    def eof(self):
        return self.pos == self.length

    def assign(self, s, l):
        if self.length == 0:
            return
        i = self.unassigned
        containing = 0
        while 1:
            if containing == len(i):
                # warnings.warn("Did not find containing block")
                return
            elif i[containing][0] <= s and s + l <= i[containing][1]:
                break
            containing += 1
        containing_arr = i[containing]
        remaining = i[:containing]
        if s > containing_arr[0]:
            remaining.append([s, containing_arr[0]])
        if s + l < containing_arr[1]:
            remaining.append([s + l, containing_arr[1]])
        if containing < len(i):
            remaining.extend(i[containing + 1:])
        self.unassigned = remaining

    def add_child(self, s, l, c, name = "unnamed", relative=True):
        child = c(self.f, s, l, name)
        self.children.append(child)
        child.parent = self
        child.absolute = s
        if relative:
            child.absolute += self.absolute
        return child

    def adopt_child(self, child):
        child.parent = self
        child.absolute = self.absolute + child.offset
        self.assign(child.offset, child.length)
        return child

    def word(self):
        if self.length > 0 and self.pos + 4 > self.length:
            warnings.warn("Read oob at " + hex(self.absolute) + " + " + hex(self.pos))
        self.f.seek(self.absolute + self.pos)
        self.pos += 4
        return struct.unpack('>I', self.f.read(4))[0]
    
    def float(self):
        if self.length > 0 and self.pos + 4 > self.length:
            warnings.warn("Read oob at " + hex(self.absolute) + " + " + hex(self.pos))
        self.f.seek(self.absolute + self.pos)
        self.pos += 4
        return struct.unpack('>f', self.f.read(4))[0]
    
    def half(self):
        if self.length > 0 and self.pos + 2 > self.length:
            warnings.warn("Read oob at " + hex(self.absolute) + " + " + hex(self.pos))
        self.f.seek(self.absolute + self.pos)
        self.pos += 2
        return struct.unpack('>H', self.f.read(2))[0]
    
    def byte(self):
        if self.length > 0 and self.pos + 1 > self.length:
            warnings.warn("Read oob at " + hex(self.absolute) + " + " + hex(self.pos))
        self.f.seek(self.absolute + self.pos)
        self.pos += 1
        return struct.unpack('>B', self.f.read(1))[0]

    def read(self, l):
        if self.length > 0 and self.pos + l > self.length:
            warnings.warn("Read oob at " + hex(self.absolute) + " + " + hex(self.pos))
        self.f.seek(self.absolute + self.pos)
        self.pos += l
        return self.f.read(l)

    def word_at(self, addr):
        self.f.seek(self.absolute + addr)
        return struct.unpack('>I', self.f.read(4))[0]

    def read_at(self, addr, l):
        self.f.seek(self.absolute + addr)
        return self.f.read(l)

    def description(self):
        return hex(self.absolute) + ' - ' + self.name

    def print(self, level=0):
        desc = self.description()
        if len(desc):
            try:
                print ('\n'.join([tabs(level + (c > 0)) + l for c, l in enumerate(desc.split('\n'))]))
            except UnicodeEncodeError as e:
                print(e)
        for child in self.children:
            child.print(level+1)
    
    def parentClass(self, c):
        if self.__class__ == c:
            return
        parent = self.parent
        while parent:
            if parent.__class__ == c:
                return parent
            parent = parent.parent
        return parent

    def readStr(self, addr):
        name = ''
        char = int.from_bytes(self.read_at(addr + len(name), 1), 'big')
        while char > 0:
            name += chr(char)
            # Not DRY, sue me
            char = int.from_bytes(self.read_at(addr + len(name), 1), 'big')
        return name

class File(SequentialData):
    def __init__(self, f):
        super().__init__(f, 0, -1)

class FileChunk(SequentialData):
    def __init__(self, f, s, l, name):
        super().__init__(f, s, l, name)