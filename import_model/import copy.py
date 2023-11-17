from helper import *
import re
import math
import numpy
import os

normals_enabled = True
colors_enabled = False

class OBJImport():
    def __init__(self, dir):
        positions = []
        normals = []
        textureCoords = []
        global textureID
        global triangles
        global textureGroups
        global textures
        global mtlMap
        textureGroups = []
        triangles = []
        textureID = 0
        textures = []
        mtlMap = {}
        textureMap = {}

        def flushTriangles(mtl):
            global textureID
            global triangles
            global textureGroups
            global textures
            global mtlMap
            if len(triangles) == 0:
                return
            group = TextureGroup(triangles, textures.index(mtlMap[mtl]))
            textureGroups.append(group)
            textureID += 1
            triangles = []

        with open(dir + '/stadium.mtl', 'r', errors='ignore') as f:
            lines = f.readlines()
            mtlName = ''
            path = ''
            for line in lines:
                line = line.replace('\n', '')
                if line.split(' ')[0] == 'newmtl':
                    mtlName = line.split(' ')[1]
                elif line.split(' ')[0] == 'map_Kd':
                    path = dir + line[line.find(' ') + 1:]
                    if path not in textures:
                        textures.append(path)
                        textureMap[path] = mtlName
                        if not os.path.exists(dir + '/tpl/'):
                            os.mkdir(dir + '/tpl/')
                        os.system('wimgt encode --transform="TPL.CMPR" -d ' + dir + '/tpl/' + mtlName + ' "' + path + '"')
                    mtlMap[mtlName] = path

        mtl = ''
        with open(dir + '/stadium.obj', 'r', errors='ignore') as f:
            lines = f.readlines()
            for line in lines:
                line = line.replace('\n', '')
                type = line.split(' ')[0]
                if type == 'v':
                    coords = [float(x) for x in line.split(' ')[1:]]
                    positions.append(Position(coords[0], coords[1], coords[2]))
                elif type == 'vt':
                    coords = [float(x) for x in line.split(' ')[1:]]
                    textureCoords.append(TextureCoord(coords[0], -coords[1]))
                elif type == 'vn':
                    coords = [float(x) for x in line.split(' ')[1:]]
                    normals.append(Normal(coords[0], coords[1], coords[2]))
                elif type == 'usemtl':
                    flushTriangles(mtl)
                    mtl = line.split(' ')[1]
                elif type == 'o':
                    flushTriangles(mtl)
                elif type == 'f':
                    coords = [int(x) - 1 for x in re.findall(r'[0-9]+', line)]
                    if len(coords) == 12:
                        triangles.append(Triangle(
                            [coords[0], coords[3], coords[6]],
                            [coords[2], coords[5], coords[8]],
                            [coords[1], coords[4], coords[7]]))
                        triangles.append(Triangle(
                            [coords[0], coords[6], coords[9]],
                            [coords[2], coords[8], coords[11]],
                            [coords[1], coords[7], coords[10]]))
                    else:
                        triangles.append(Triangle(
                            [coords[0], coords[3], coords[6]],
                            [coords[2], coords[5], coords[8]],
                            [coords[1], coords[4], coords[7]]))
        flushTriangles(mtl)
        textures = [dir + '/tpl/' + textureMap[x] for x in textures]
        model = ModelImport(positions, normals, textureCoords, textureGroups, textures)
        with open(dir + '/out', 'wb') as f:
            f.write(model.binary())

class ModelImport():
    def __init__(self, positions, normals, textureCoords, textureGroups, textures):
        self.gpl = GPL(positions, normals, textureCoords, textureGroups)
        self.act = ACT()
        self.tpl = TPL(textures)
    
    def binary(self):
        outHeader = bytearray()
        outData = bytearray()
        offset = 0x20
        outHeader.extend(itb(0, 4))
        
        outHeader.extend(itb(offset, 4))
        gplBinary = self.gpl.binary(offset)
        outData.extend(gplBinary)
        offset += len(gplBinary)
        padding = offset32(offset)
        outData.extend(itb(0, padding))
        offset += padding

        outHeader.extend(itb(offset, 4))
        actBinary = self.act.binary()
        outData.extend(actBinary)
        offset += len(actBinary)
        padding = offset32(offset)
        outData.extend(itb(0, padding))
        offset += padding

        outHeader.extend(itb(offset, 4))
        tplBinary = self.tpl.binary()
        outData.extend(tplBinary)
        offset += len(tplBinary)
        padding = offset32(offset)
        outData.extend(itb(0, padding))
        offset += padding

        outHeader.extend(itb(0, 4))
        outHeader.extend(itb(0, 4))
        outHeader.extend(itb(0, 4))
        outHeader.extend(itb(0, 4))
        outHeader.extend(outData)

        return outHeader

class ACT():
    def __init__(self):
        pass

    def binary(self):
        # Nothing too special about a single-bone act layout, so just copied this verbatim
        return itb(0x007B7960000000010000000C000000200000003CFFFF00000000001000000060000000000000000000000000000000000000000000000000010000006261742E67706C000000000000000000000000000000000000000000000000000000000000000010000300000000000CFFFF000000000000000000000000000000000000, 0x80)

class GPL():
    def __init__(self, positions, normals, textureCoords, textureGroups):
        self.layout = DOLayout(positions, normals, textureCoords, textureGroups)

    def binary(self, absolute):
        out = bytearray()
        # version number
        out.extend(itb(0x00B749E0, 4))
        # user data size and pointer (I think usually holds strings)
        out.extend(itb(0, 4))
        out.extend(itb(0, 4))
        # number of GEODescriptors
        out.extend(itb(1, 4))
        # descriptor pointer
        out.extend(itb(0x14, 4))
        # descriptor's layout pointer
        out.extend(itb(0x1c, 4))
        # descriptor's name pointer
        out.extend(itb(0, 4))
        out.extend(self.layout.binary(absolute + 0x1c))
        return out

class DOLayout():
    def __init__(self, positions, normals, textureCoords, textureGroups): 
        self.positionHeader = DOPositionHeader(positions)
        self.lightingHeader = DOLightingHeader(normals)
        self.textureHeader = DOTextureHeader(textureCoords)
        self.colorHeader = DOColorHeader()
        self.displayHeader = DODisplayHeader(textureGroups, positions)

    def binary(self, absolute):
        out = bytearray()
        offset = 0x18
        # position header offset
        out.extend(itb(offset, 4))
        positionBinary = self.positionHeader.binary(offset)
        offset += len(positionBinary)
        padding = offset32(offset + absolute)
        positionBinary.extend(itb(0, padding))
        offset += padding
        # color header offset
        out.extend(itb(offset, 4))
        colorBinary = self.colorHeader.binary(offset)
        offset += len(colorBinary)
        padding = offset32(offset + absolute)
        colorBinary.extend(itb(0, padding))
        offset += padding
        # texture header offset
        out.extend(itb(offset, 4))
        textureBinary = self.textureHeader.binary(offset)
        offset += len(textureBinary)
        padding = offset32(offset + absolute)
        textureBinary.extend(itb(0, padding))
        offset += padding
        # lighting header offset
        out.extend(itb(offset, 4))
        lightingBinary = self.lightingHeader.binary(offset)
        offset += len(lightingBinary)
        padding = offset32(offset + absolute)
        lightingBinary.extend(itb(0, padding))
        offset += padding
        # display header offset
        out.extend(itb(offset, 4))
        displayBinary = self.displayHeader.binary(offset, offset + absolute)
        padding = offset32(offset + absolute)
        displayBinary.extend(itb(0, padding))
        offset += padding
        # number of textures and padding
        out.extend(itb(0x01000000, 4))

        out.extend(positionBinary)
        out.extend(colorBinary)
        out.extend(textureBinary)
        out.extend(lightingBinary)
        out.extend(displayBinary)

        return out

class DOPositionHeader():
    def __init__(self, positions):
        self.quantizeInfo = 0x3b
        self.positions = positions
        self.componentCount = 3
        self.numPositions = len(positions)

    def binary(self, offset):
        maxVal = 0
        self.quantizeInfo = maxShift(self.quantizeInfo, [x for item in self.positions for x in item.raw()])
        out = bytearray()
        dataPtr = offset + 0x8
        out.extend(itb(dataPtr, 4))
        out.extend(itb(self.numPositions, 2))
        out.extend(itb(self.quantizeInfo, 1))
        out.extend(itb(self.componentCount, 1))
        flatPositions = []
        for position in self.positions:
            flatPositions.extend(position.raw())
        out.extend(writeQuantizedData(self.quantizeInfo, flatPositions))
        return out

class DOLightingHeader():
    def __init__(self, normals):
        self.quantizeInfo = 0x3e
        self.normals = normals
        self.componentCount = 3
        self.numNormals = len(normals)

    def binary(self, offset):
        self.quantizeInfo = maxShift(self.quantizeInfo, [x for item in self.normals for x in item.raw()])
        out = bytearray()
        dataPtr = offset + 0xc
        if not normals_enabled:
            dataPtr = 0
        out.extend(itb(dataPtr, 4))
        out.extend(itb(self.numNormals, 2))
        out.extend(itb(self.quantizeInfo, 1))
        out.extend(itb(self.componentCount, 1))
        # ambient percentage
        out.extend(itb(0, 4))
        if normals_enabled:
            flatNormals = []
            for normal in self.normals:
                flatNormals.extend(normal.raw())
            out.extend(writeQuantizedData(self.quantizeInfo, flatNormals))
        return out

class DOTextureHeader():
    def __init__(self, textureCoords):
        self.quantizeInfo = 0x3e
        self.textureCoords = textureCoords
        self.componentCount = 2
        self.numTextureCoords = len(textureCoords)

    def binary(self, offset):
        self.quantizeInfo = maxShift(self.quantizeInfo, [x for item in self.textureCoords for x in item.raw()])
        out = bytearray()
        dataPtr = offset + 0x10
        out.extend(itb(dataPtr, 4))
        out.extend(itb(self.numTextureCoords, 2))
        out.extend(itb(self.quantizeInfo, 1))
        out.extend(itb(self.componentCount, 1))
        # Palette name ptr
        out.extend(itb(0, 4))
        # Palette ptr
        out.extend(itb(0, 4))
        flatTextureCoords = []
        for textureCoord in self.textureCoords:
            flatTextureCoords.extend(textureCoord.raw())
        out.extend(writeQuantizedData(self.quantizeInfo, flatTextureCoords))
        return out

class DOColorHeader():
    def __init__(self):
        pass

    def binary(self, offset):
        out = bytearray()
        # data ptr
        out.extend(itb(offset + 0x8, 4))
        # color count
        out.extend(itb(1, 2))
        # quantize info
        out.extend(itb(0, 1))
        # component count (rgb/rgba)
        out.extend(itb(3, 1))
        # black I guess? Don't know how this gets used.
        out.extend(itb(0xFFFFFF00, 4))
        return out

class DODisplayHeader():
    def __init__(self, textureGroups, positions):
        self.textureGroups = textureGroups
        self.positions = positions
    
    def binary(self, offset, absolute):
        displayBinary = 0b00000000000000000000110000001100
        if normals_enabled:
            displayBinary |= 0b00110000
        if colors_enabled:
            displayBinary |= 0b11000000
        initialHeaders = [
            # shrug
            DODisplayState(0x04000000, 0b11111111111111111111111111110000, 0, 0),
            # enable position, lighting, and texture layer 0, all with 2-byte addressing
            DODisplayState(0x03000000, displayBinary, 0, 0),
            # shrug
            DODisplayState(0x06010000, 0b00000000000000000000010101110101, 0, 0),
            # shadows?
            # DODisplayState(7, 0x53686477, 0, 0),
        ]
        displayHeaderCount = len(initialHeaders) + 2 * len(self.textureGroups)
        primitiveListCount = len(self.textureGroups)
        data = bytearray()
        # Populate primitive list data parallel to display state data
        primitiveData = bytearray()
        primitiveListPtr = offset + displayHeaderCount * 0x10 + 0xc
        primitiveListAbsolute = primitiveListPtr - offset + absolute

        padding = offset32(primitiveListAbsolute)
        primitiveData.extend(itb(0, padding))
        primitiveListPtr += padding
        primitiveListAbsolute += padding

        # Primitive list pointer
        data.extend(itb(primitiveListPtr, 4))
        # Display state list pointer
        data.extend(itb(offset + 0xc, 4))
        data.extend(itb(displayHeaderCount, 2))
        data.extend(itb(0, 2))

        for header in initialHeaders:
            data.extend(header.binary())
        for group in self.textureGroups:
            padding = offset32(primitiveListAbsolute)
            primitiveData.extend(itb(0, padding))
            primitiveListPtr += padding
            primitiveListAbsolute += padding
            
            setTexture = self.setTexture(group.textureID)
            data.extend(setTexture.binary())
            primitiveList = PrimitiveList(group.triangles)
            binary = primitiveList.binary()
            # shrug
            # drawState = DODisplayState(0x07000000, 0b01010011011100000110010101100011, primitiveListPtr, len(binary))
            shadowType = group.shadowType(self.positions)
            setting = 0x53686477 if shadowType else 0
            drawState = DODisplayState(0x07000000 | (shadowType << 16), setting, primitiveListPtr, len(binary) + padding)
            data.extend(drawState.binary())
            primitiveData.extend(binary)
            primitiveListPtr += len(binary)
            primitiveListAbsolute += len(binary)
        data.extend(primitiveData)
        return data

    def setTexture(self, id):
        return DODisplayState(0x01000000, 0b00010001000100010000000000000000 | id, 0, 0)

class DODisplayState():
    def __init__(self, id, setting, primitivePtr, primitiveSize):
        self.id = id
        self.setting = setting
        self.primitivePtr = primitivePtr
        self.primitiveSize = primitiveSize
        pass

    def binary(self):
        out = bytearray()
        out.extend(itb(self.id, 4))
        out.extend(itb(self.setting, 4))
        out.extend(itb(self.primitivePtr, 4))
        out.extend(itb(self.primitiveSize, 4))
        return out

class PrimitiveList():
    def __init__(self, triangles):
        self.triangles = triangles
    
    def binary(self):
        out = bytearray()
        out.extend(itb(0x90, 1))
        vertexCount = len(self.triangles) * 3
        out.extend(itb(vertexCount, 2))
        for triangle in self.triangles:
            out.extend(itb(triangle.positionInds[0],     2))
            if normals_enabled:
                out.extend(itb(triangle.normalInds[0],   2))
            if colors_enabled:
                out.extend(itb(0,                        2))
            out.extend(itb(triangle.textureCoordInds[0], 2))
            out.extend(itb(triangle.positionInds[1],     2))
            if normals_enabled:
                out.extend(itb(triangle.normalInds[1],   2))
            if colors_enabled:
                out.extend(itb(0,                        2))
            out.extend(itb(triangle.textureCoordInds[1], 2))
            out.extend(itb(triangle.positionInds[2],     2))
            if normals_enabled:
                out.extend(itb(triangle.normalInds[2],   2))
            if colors_enabled:
                out.extend(itb(0,                        2))
            out.extend(itb(triangle.textureCoordInds[2], 2))
        return out

class TextureGroup():
    def __init__(self, triangles, textureID):
        self.textureID = textureID
        self.triangles = triangles
        pass

    def shadowType(self, positions):
        y_levels = [positions[tri.positionInds[i]].y for tri in self.triangles for i in range(3)]
        if max(y_levels) > 1:
            return 0
        if max(y_levels) > 0.4:
            return 2
        return 1

class Triangle():
    def __init__(self, positionInds, normalInds, textureCoordInds):
        self.positionInds = positionInds
        self.normalInds = normalInds
        self.textureCoordInds = textureCoordInds

class Vect2():
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def raw(self):
        return [self.x, self.y]

class Vect3():
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def raw(self):
        return [self.x, self.y, self.z]

class TextureCoord(Vect2):
    def __init__(self, x, y):
        super().__init__(x, y)

class Position(Vect3):
    def __init__(self, x, y, z):
        super().__init__(x, y, z)

class Normal(Vect3):
    def __init__(self, x, y, z):
        super().__init__(x, y, z)
        l = (self.x ** 2 + self.y ** 2 + self.z ** 2) ** 0.5
        if abs(l) < 0.01:
            self.x = 1
            self.y = 0
            self.z = 0
        else:
            self.x /= l
            self.y /= l
            self.z /= l

class TPL():
    def __init__(self, paths):
        self.paths = paths
        self.textures = []
        for path in self.paths:
            self.textures.append(Texture(path))

    def binary(self):
        # 4 bytes for image and palette counts
        data = bytearray()
        data.extend(itb(len(self.textures), 2))
        data.extend(itb(0, 2))
        # 0x20 bytes per image header
        dataAddr = 0x20 * len(self.textures) + 0x20
        for tex in self.textures:
            data.extend(tex.header(dataAddr))
            dataAddr += tex.data['dataLen']
        # An extra 0x1c bytes to pad the data to a multiple of 0x20
        data.extend(itb(0, 0x1c))
        for tex in self.textures:
            data.extend(tex.body())
        return data

class Texture():
    def __init__(self, path):
        self.path = path
        self.id = id
        self.data = None
        self.parseHeader()

    def dataLen(self):
        return self.data['dataLen']

    def parseHeader(self):
        if self.data != None:
            return
        with open(self.path, 'rb') as f:
            f.seek(0x4)
            imgCount = bti(f.read(4))
            if imgCount != 1:
                raise Exception('Texture ' + self.path + ' has ' + str(imgCount) + ' images, not 1')
            f.seek(bti(f.read(4)))
            self.data = {}
            imgHeader = bti(f.read(4))
            self.data['imgHeader'] = imgHeader
            paletteHeader = bti(f.read(4))
            self.data['paletteHeader'] = paletteHeader
            if paletteHeader:
                print ("texture has a palette")
                exit(0)
            f.seek(imgHeader)
            self.data['height'] = bti(f.read(2))
            self.data['width'] = bti(f.read(2))
            self.data['format'] = bti(f.read(4))
            self.data['dataAddr'] = bti(f.read(4))
            self.data['wrapS'] = bti(f.read(4))
            self.data['wrapT'] = bti(f.read(4))
            self.data['minFilter'] = bti(f.read(4))
            self.data['magFilter'] = bti(f.read(4))
            # LODbias is a float, add if needed
            f.read(4)
            self.data['edgeLODEnable'] = bti(f.read(1))
            self.data['minLOD'] = bti(f.read(1))
            self.data['maxLOD'] = bti(f.read(1))
            self.data['unpacked'] = bti(f.read(1))
            self.data['wrapS'] = 1 
            self.data['wrapT'] = 1
            # Assuming the image dimensions are a multiple of the block dimensions, don't know if that's implied
            self.data['dataLen'] = (
                {0: 4, 1: 8, 2: 8, 3: 16, 4: 16, 5: 16, 6: 32, 8: 4, 9: 8, 0xa: 16, 0xe: 4}[self.data['format']]
                * self.data['height']
                * self.data['width']
            ) >> 3
            if paletteHeader:
                f.seek(paletteHeader)
                self.data['paletteEntries'] = bti(f.read(2))
                self.data['paletteUnpacked'] = bti(f.read(1))
                f.read(1)
                self.data['paletteFormat'] = bti(f.read(4))
                self.data['paletteAddr'] = bti(f.read(4))
            # print(f.name)
            # print(self.data)
            # exit(0)
        
    def body(self):
        with open(self.path, 'rb') as f:
            f.seek(self.data['dataAddr'])
            return f.read(self.data['dataLen'])
    
    def header(self, dataPtr):
        header = bytearray()
        # Image data ptr
        header.extend(itb(dataPtr, 4))
        # Palette data ptr (null)
        header.extend(itb(0, 4))
        header.extend(itb(self.data['height'], 2))
        header.extend(itb(self.data['width'], 2))
        # Don't know what these two are
        header.extend(itb(0x01010101, 4))
        header.extend(itb(0, 4))
        header.extend(itb(self.data['format'], 4))
        # Or what these two are
        header.extend(itb(0, 4))
        header.extend(itb(0, 4))
        return header

OBJImport('wii_sports/')