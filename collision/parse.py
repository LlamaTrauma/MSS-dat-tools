from helper import *
import sys
sys.path.append('../export_models')
from base import *

def mtl_str(names):
    mtl_str = ''
    for name in names:
        n = int(name, 16)
        foul = (n & 0x00F0) / 0xF0
        high = (n & 0xFF00) / 0xFF00
        low = (n & 0xF) / 0xF
        r = str(foul * 0.5 + low * 0.5)
        g = str(1 - low)
        b = str(high * 0.5 + low * 0.5)
        mtl_str += 'newmtl ' + str(name)
        mtl_str += '\n'
        mtl_str += 'Ka ' + r + ' ' + g + ' ' + b
        mtl_str += '\n'
        mtl_str += 'Kd ' + r + ' ' + g + ' ' + b
        mtl_str += '\n'
        mtl_str += 'illum 1'
        mtl_str += '\n'
    return mtl_str

class Stadium(File):
    def analyze(self):
        self._bCount = self.half()
        # I see 0x4300?
        self.read(2)
        self._aPtr = self.word()
        self._bPtrs = [self.word() for i in range(self._bCount)] + [self.length]
        # exit(0)
        self._a = self.add_child(self._aPtr, self._bPtrs[0] - self._aPtr, _A, "_A")
        self._a.analyze()
        self._bs = [self.add_child(self._bPtrs[x], self._bPtrs[x + 1] - self._bPtrs[x], _B, "_B") for x in range(len(self._bPtrs) - 1)]
        for _b in self._bs:
            _b.analyze()

    def unique_types(self):
        types = set()
        for _b in self._bs:
            types = types.union(_b.unique_types())
        return ['{:04x}'.format(x) for x in sorted(types)]

    def objs(self, out_path=''):
        mtl_out = mtl_str(self.unique_types())
        out_dir = ''
        if len(out_path):
            out_dir = out_path
        else:
            out_dir = self.f.name + '_objs/'
        if not os.path.exists(out_dir):
            os.mkdir(out_dir)
        a_str = self._a.obj_str()
        fpath = out_dir + 'a.obj'
        with open(fpath, 'w') as f:
            f.write(a_str)
        with open(out_dir + 'mtl.mtl', 'w') as f:
            f.write(mtl_out)
        single_b = self.add_child(0, 0, _B)
        single_b.triangleGroups = []
        for ind in range(self._bCount):
            _b = self._bs[ind]
            single_b.triangleGroups.extend(_b.triangleGroups)
        kinds = list(single_b.unique_types())
        for kind in kinds:
            obj_str = single_b.obj_str(kind)
            fpath = out_dir + hex(kind) + '.obj'
            with open(fpath, 'w') as f:
                f.write(obj_str)
        

class _A(FileChunk):
    def analyze(self):
        self.data = [self.float() for x in range(0, self.length, 4)]
        self.coords = []
        i = 0
        while i < len(self.data):
            x = self.data[i]
            y = self.data[i + 1]
            z = self.data[i + 2]
            x2 = self.data[i + 3]
            y2 = self.data[i + 4]
            z2 = self.data[i + 5]
            self.coords.extend([[x, y, z], [x2, y, z], [x2, y2, z2], [x, y2, z2]])
            i += 6

    def obj_str(self):
        prettyCoords = [' '.join("{:.4f}".format(y) for y in x) for x in self.coords]
        out = ''
        out += '\n'.join(['v ' + x for x in prettyCoords])
        out += '\n'
        out += '\n'.join(['f ' + str(x + 1) + ' ' + str(x + 2) + ' ' + str(x + 3) + ' ' + str(x + 4) for x in range(0, len(prettyCoords), 4)])
        return out

printTriangles = 0
class _B(FileChunk):
    def analyze(self):
        self.triangleGroups = []
        while 1:
            kind = self.half()
            count = self.half()
            if kind == 0:
                count *= 3
            elif kind == 1:
                count += 2
            else:
                print("unused type found " + hex(type))
                exit(0)
            # Catch null padding at the end
            if count == 0:
                break
            coords = []
            while len(coords) < count:
                c_data = [self.float(), self.float(), self.float()]
                c_kind = self.half()
                self.read(2)
                coords.append(Coord(c_kind, c_data))
            triangles = []
            if kind == 0:
                triangles.extend([Triangle(coords[x:x+3], 1) for x in range(0, len(coords) - 2, 3)])
            elif kind == 1:
                for i in range(0, len(coords) - 2):
                    triangles.append(Triangle([coords[i], coords[i + 1], coords[i + 2]], 0))
            self.triangleGroups.append(TriangleGroup(triangles))
    
    def obj_str(self, kind):
        out = 'mtllib mtl.mtl\n'
        out += '\n'.join([x.formatted_vertices() for x in self.triangleGroups])
        offset = 0
        for group in self.triangleGroups:
            str, offset = group.formatted_faces(offset, kind)
            out += '\n' + str
        return out
    
    def unique_types(self):
        types = set()
        for group in self.triangleGroups:
            for triangle in group.triangles:
                types.add(triangle.kind())
                for coord in triangle.coords:
                    types.add(coord.type)
        return types

    # def description(self):
    #     return '\n'.join(x.description() for x in self.coordGroups)

class TriangleGroup():
    def __init__(self, triangles):
        self.triangles = triangles

    def formatted_vertices(self):
        return '\n'.join([x.formatted_vertices() for x in self.triangles])

    def formatted_faces(self, offset, kind):
        out = []
        for tri in self.triangles:
            if tri.kind() == kind:
                out.append(tri.formatted_face(offset))
            offset += 3
        return '\n'.join(out), offset
    
    def obj_str(self, kind):
        out = ''
        out += '\n'.join([x.formatted_vertices() for x in self.triangles])
        out += '\n'
        out += '\n'.join([tri.formatted_face(offset * 3) for offset, tri in enumerate(self.triangles) if tri.kind() == kind])
        return out

class Triangle:
    def __init__(self, coords, p = 0):
        self.coords = coords
        if p:
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
            # if (self.coords[2].type & 0xF) in (0x1, 0x6):
            #     print(', '.join(['{:.2f}'.format(n) for n in normal]))
            # print(','.join('{:.2f}'.format(c.data[1]) for c in self.coords))
    
    def formatted_vertices(self):
        return '\n'.join([x.formatted_vertex() for x in self.coords])
    
    def formatted_face(self, offset):
        out = "usemtl " + "{:04x}".format(self.kind())
        out += '\ns off'
        out += '\nf ' + str(offset + 1) + ' ' + str(offset + 2) + ' ' + str(offset + 3)
        return out

    def kind(self):
        types = [coord.type for coord in self.coords]
        # return types[0] | types[1] | types[2]
        # if types[0] == types[1]:
        #     return types[0]
        # if types[0] == types[2]:
        #     return types[0]
        # if types[1] == types[2]:
        #     return types[1]
        return types[2]
        # return self.coords[0].type & self.coords[1].type & self.coords[2].type

class Coord:
    def __init__(self, kind, data):
        self.type = kind
        self.data = data
    
    def description(self):
        return 'type ' + str(self.type) + ' | ' + ', '.join(['{:.4f}'.format(x) for x in self.data])

    def formatted_vertex(self):
        return 'v ' + ' '.join([str(x) for x in self.data])

s = Stadium(open('stadium_files/sta_01_3', 'rb'))
# s = Stadium(open('stadium_files/wii_sports/out', 'rb'))
s.analyze()
s.objs()