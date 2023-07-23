from helper import *
import re
import os

class OBJImport:
    def __init__(self, dir):
        triangles = []
        mtl = 0

        for file in os.listdir(dir):
            if file.split('.')[-1] != 'obj':
                continue
            positions = []
            with open(dir + file, 'r', errors='ignore') as f:
                lines = f.readlines()
                for line in lines:
                    line = line.replace('\n', '')
                    type = line.split(' ')[0]
                    if type == 'v':
                        coords = [round(float(x), 3) for x in line.split(' ')[1:]]
                        positions.append(coords)
        
            mtl = int(file.split('.')[0], 16)
            with open(dir + file, 'r', errors='ignore') as f:
                lines = f.readlines()
                for line in lines:
                    line = line.replace('\n', '')
                    type = line.split(' ')[0]
                    if type == 'f':
                        coords = [int(x.split('/')[0]) - 1 for x in line.split(' ')[1:]]
                        if len(coords) == 3:
                            triangles.append(Triangle([
                                    Coord(positions[coords[0]], mtl),
                                    Coord(positions[coords[1]], mtl),
                                    Coord(positions[coords[2]], mtl)
                                ]))
                        elif len(coords) == 4:
                            triangles.append(Triangle([
                                    Coord(positions[coords[0]], mtl),
                                    Coord(positions[coords[1]], mtl),
                                    Coord(positions[coords[2]], mtl)
                                ]))
                            triangles.append(Triangle([
                                    Coord(positions[coords[0]], mtl),
                                    Coord(positions[coords[2]], mtl),
                                    Coord(positions[coords[3]], mtl)
                                ]))
                        else:
                            print(str(len(coords)) + '-gon found')
        s = Stadium(triangles)
        print (str(len(triangles)) + " triangles found")
        with open(dir + '/out', 'wb') as f:
            f.write(s.binary())

def sortOrder(triangle):
    prop = triangle.coords[-1].prop & 0xF
    order = 0x10
    try:
        order = [1, 6, 2, 5, 4, 3].index(prop)
    except ValueError as e:
        order = 0x10
    return order

class Stadium:
    def __init__(self, triangles):
        self.triangles = triangles
        self.triangles.sort(key=sortOrder)
    
    def binary(self):
        sections = [_A(), _B(self.triangles)]
        out = bytearray()
        out.extend(itb(len(sections) - 1, 2))
        out.extend(itb(0x4300, 2))
        offset = 0x4 + len(sections) * 4
        binary = []
        for section in sections:
            out.extend(itb(offset, 4))
            b = section.binary()
            binary.append(b)
            offset += len(b)
        for b in binary:
            out.extend(b)
        if len(out) % 0x20:
            out.extend(itb(0, 0x20 - len(out) % 0x20))
        return out

class _A:
    def __init__(self):
        pass

    def binary(self):
        out = bytearray()
        # Just get one box covering everything
        out.extend(ftb(-200))
        out.extend(ftb(-80))
        out.extend(ftb(-200))
        out.extend(ftb(200))
        out.extend(ftb(5))
        out.extend(ftb(200))
        return out

class _B:
    def __init__(self, triangles):
        self.triangles = triangles
    
    def binary(self):
        out = bytearray()
        # triangles
        out.extend(itb(0, 2))
        out.extend(itb(len(self.triangles), 2))
        for triangle in self.triangles:
            for coord in triangle.coords:
                out.extend(coord.binary())
        out.extend(itb(0, 4))
        return out

class Triangle:
    def __init__(self, coords):
        self.coords = coords
        c1 = self.coords[0].data
        c2 = self.coords[1].data
        c3 = self.coords[2].data
        u = [(c1[x] - c3[x]) for x in range(3)]
        v = [(c2[x] - c3[x]) for x in range(3)]
        normal = [
            u[1] * v[2] - u[2] * v[1],
            u[2] * v[0] - u[0] * v[2],
            u[0] * v[1] - u[1] * v[0]
        ]
        correctFacing = [0 - c1[0], -50 - c1[1], 35 - c1[2]]
        if sum([normal[x] * correctFacing[x] for x in range(3)]) < 0:
            self.coords = [self.coords[0], self.coords[2], self.coords[1]]

class Coord:
    def __init__(self, data, prop):
        self.data = data
        self.x, self.y, self.z = data
        self.prop = prop

    def binary(self):
        out = bytearray()
        out.extend(ftb(self.x))
        out.extend(ftb(self.y))
        out.extend(ftb(self.z))
        out.extend(itb(self.prop, 2))
        out.extend(itb(0, 2))
        return out

OBJImport('stadium_files/wii_sports/')