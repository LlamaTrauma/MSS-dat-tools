from base import *
from act import *
import numpy as np
from helper import *
from model0 import *

# np.set_printoptions(precision=3, suppress=True, threshold=np.inf)

class GPL(FileChunk):
    def analyze(self):
        # 0x00B749E0
        self.versionNum = self.word()
        self.userDataSize = self.word()
        self.userDataPtr = self.word()
        self.numDescriptors = self.word()
        self.descriptorPtr = self.word()
        self.geoDescriptors = [
            self.add_child(self.descriptorPtr + x * 8, 8, GEODescriptor, "descriptor").analyze(x) for x in range(self.numDescriptors)
        ]
    
    def toFile(self, outdir, actor):
        for i, descriptor in enumerate(self.geoDescriptors):
            descriptor.layout.toFile(
                outdir + str(i) + '_' + descriptor.n + '.obj',
                actor.geoTransformation(i) if actor else [],
            )

    def description(self):
        desc = super().description()
        desc += "\nversion number: " + str(hex(self.versionNum))
        desc += "\nuser data size: " + str(hex(self.userDataSize))
        desc += "\nuser data addr: " + str(hex(self.userDataPtr))
        desc += "\ndescriptor cnt: " + str(hex(self.numDescriptors))
        desc += "\ndescriptor ptr: " + str(hex(self.descriptorPtr))
        return desc

class GEODescriptor(FileChunk):
    def analyze(self, id):
        self.DOLayoutPtr = self.word()
        self.id = id
        self.layout = self.parent.add_child(self.DOLayoutPtr, 0, DOLayout, "DOLayout").analyze()
        self.namePtr = self.word()
        self.n = self.parent.readStr(self.namePtr)
        return self

    def description(self):
        desc = super().description()
        desc += "\nname: " + str(self.n) + " at " + hex(self.parent.absolute + self.namePtr)
        return desc

class DummyAttribute():
    def __init__(self) -> None:
        pass
    def at(self, index):
        return None

class DOLayout(FileChunk):
    def analyze(self):
        self.DOPositionHeaderptr = self.word()
        self.DOColorHeaderPtr = self.word()
        self.DOTextureDataHeaderPtr = self.word()
        self.DOLightingHeaderPtr = self.word()
        self.DODisplayHeaderPtr = self.word()
        self.numTextureChannels = intFromBytes(self.read(1))
        self.DOPositionHeader = self.add_child(self.DOPositionHeaderptr, 0, DOPositionHeader, "DOPositionHeader").analyze()
        self.DOColorHeader = self.add_child(self.DOColorHeaderPtr, 0, DOColorHeader, "DOColorHeader").analyze()
        self.DOTextureDataHeaders = [
            self.add_child(self.DOTextureDataHeaderPtr + x * 16, 0, DOTextureDataHeader, "DOTextureDataHeader").analyze()
            for x in range(self.numTextureChannels)
        ]
        self.DOLightingHeader = self.add_child(self.DOLightingHeaderPtr, 0, DOLightingHeader, "DOLightingHeader").analyze()
        self.DODisplayHeader = self.add_child(self.DODisplayHeaderPtr, 0, DODisplayHeader, "DODisplayHeader").analyze()
        self.pad8 = intFromBytes(self.read(1))
        self.pad16 = intFromBytes(self.read(2))
        return self

    def toFile(self, outname, transformation = []):
        # print ("\nWriting to " + outname + '\n')
        if len(transformation) == 0:
            transformation = np.identity(4)
        positions = self.DOPositionHeader.data
        if len(positions) == 0:
            return
        positions = [np.matmul(np.array([pos[:3] + [1]]), transformation)[0][:3] for pos in positions]
        normals = self.DOLightingHeader.data
        transformation = np.linalg.inv(transformation)
        transformation = transformation.transpose()
        normals = [np.matmul(np.array([normal[:3] + [1]]), transformation)[0][:3] for normal in normals]
        # for i, tex in enumerate(self.DOTextureDataHeaders):
        #     print ("texture " + str(i) + " has " + str(tex.numTextureCoords) + " coords")
        texChannel = 0
        textureCoords = []
        if len(self.DOTextureDataHeaders):
            textureCoords = self.DOTextureDataHeaders[0].data
            textureCoords = [[c[0], c[1]] for c in textureCoords]
        outfile = open(outname, 'w')
        outfile.write('mtllib textures.mtl\n')
        for position in positions:
            outfile.write('v ' + str(position[0]) + ' ' + str(position[1]) + ' ' + str(position[2]) + '\n')
        for coord in textureCoords:
            x = coord[0]
            y = coord[1]
            # It goes clamp, repeat, mirror, max tex wrap mode
            # wraps and wrapt are typically 1 (GX_REPEAT)
            # Because blender flips the y axis
            y = -y
            outfile.write('vt ' + str(x) + ' ' + str(y) + '\n')
        for normal in normals:
            l = (normal[0] ** 2 + normal[1] ** 2 + normal[2] ** 2) ** 0.5
            if l > 0.1:
                outfile.write('vn ' + str(normal[0]) + ' ' + str(normal[1]) + ' ' + str(normal[2]) + '\n')
            else:
                outfile.write('vn 1 0 0\n')
        state = {
            'texture': {
                'index': 0,
                'wrapt': 0,
                'wraps': 0,
            },
            'attributes': {
                'color0': DummyAttribute(),
                'color1': DummyAttribute(),
            },
            'descriptors': [],
            'settings': {
                7: 0
            }
        }
        state['attributes']['position'] = self.DOPositionHeader
        state['attributes']['lighting'] = self.DOLightingHeader
        for ind, val in enumerate(self.DOTextureDataHeaders):
            state['attributes']['texture' + str(ind)] = val
        # print ("Textures: " + ', '.join([
        #     str(x.paletteName) 
        #     + " at ptr " + hex(x.palettePtr)
        #     + " with component count " + str(x.compCount) for x in self.DOTextureDataHeaders]))
        includeLighting = len(normals) > 10
        includeTextures = len(textureCoords) > 0
        for displayState in self.DODisplayHeader.displayStates:
            displayState.updateState(state)
            faces = displayState.primitiveList.draw(state)
            outfile.write('usemtl ' + str(state['texture']['index']) + '\n')
            outfile.write('s off\n')
            for face in faces:
                out = 'f '
                for vertex in face:
                    position = vertex['position'] if 'position' in vertex else ''
                    textureKey = "texture" + str(texChannel)
                    texture = vertex[textureKey] if textureKey in vertex else ''
                    lighting = vertex['lighting'] if 'lighting' in vertex else ''
                    if includeLighting:
                        out += str(position) + '/' + str(texture) + '/' + str(lighting) + ' '
                    else:
                        out += str(position) + '/' + str(texture) + ' '
                outfile.write(out[:-1] + '\n')
        # print ("wrote to " + str(outname))
        outfile.close()

    def description(self):
        desc = super().description()
        desc += "\nTexture channels: " + str(self.numTextureChannels)
        return desc

class DOPositionHeader(FileChunk):
    def analyze(self):
        self.positionArrPtr = self.word()
        self.numPositions = self.half()
        self.quantizeInfo = self.byte()
        self.compCount = self.byte()
        self.data = getQuantizedData(self.f, self.parentClass(DOLayout).absolute + self.positionArrPtr, self.numPositions, self.compCount, self.quantizeInfo)
        return self

    def description(self):
        desc = super().description()
        desc += "\nNum positions: " + hex(self.numPositions)
        desc += "\nData ptr: " + hex(self.parentClass(DOLayout).absolute + self.positionArrPtr)
        desc += "\nQuantize info: " + hex(self.quantizeInfo)
        desc += "\nComponent count: " + str(self.compCount)
        return desc

class DOColorHeader(FileChunk):
    def analyze(self):
        self.colorArrPtr = self.word()
        self.numColors = intFromBytes(self.read(2))
        self.quantizeInfo = intFromBytes(self.read(1))
        self.compCount = intFromBytes(self.read(1))
        return self

    def description(self):
        desc = super().description()
        desc += "\nNum colors: " + str(self.numColors)
        desc += "\nColor arr ptr: " + hex(self.parent.absolute + self.colorArrPtr)
        return desc

class DOTextureDataHeader(FileChunk):
    def analyze(self):
        self.textureCoordsArrPtr = self.word()
        self.numTextureCoords = self.half()
        self.quantizeInfo = self.byte()
        self.compCount = self.byte()
        self.paletteName = self.parent.readStr(self.word())
        self.palettePtr = self.word()
        self.data = getQuantizedData(self.f, self.parentClass(DOLayout).absolute + self.textureCoordsArrPtr, self.numTextureCoords, self.compCount, self.quantizeInfo)
        return self

    def description(self):
        desc = super().description()
        desc += "\nName: " + str(self.paletteName)
        desc += "\nData ptr: " + hex(self.parent.absolute + self.textureCoordsArrPtr)
        desc += "\nNum coords: " + str(self.numTextureCoords)
        desc += "\nQuantize info: " + hex(self.quantizeInfo)
        desc += "\nComp. count: " + str(self.compCount)
        desc += "\nPalette ptr: " + hex(self.palettePtr)
        return desc

class DOLightingHeader(FileChunk):
    def analyze(self):
        self.normalsPtr = self.word()
        self.numNormals = intFromBytes(self.read(2))
        self.quantizeInfo = intFromBytes(self.read(1))
        self.compCount = intFromBytes(self.read(1))
        # This is a float, worry about it later if necessary
        self.ambientPercentage = self.read(4)
        self.data = []
        if self.normalsPtr != 0:
            self.data = getQuantizedData(self.f, self.parentClass(DOLayout).absolute + self.normalsPtr, self.numNormals, self.compCount, self.quantizeInfo)
        return self

    def description(self):
        desc = super().description()
        desc += "\nNum normals: " + str(self.numNormals)
        desc += "\nData pr: " + hex(self.parent.absolute + self.normalsPtr)
        desc += "\nQuantize info: " + hex(self.quantizeInfo)
        desc += "\nComponent count: " + str(self.compCount)
        return desc

class DODisplayHeader(FileChunk):
    def analyze(self):
        self.primitivePtr = self.word()
        self.displayStatePtr = self.word()
        self.numStateEntries = intFromBytes(self.read(2))
        if self.numStateEntries > 10000:
            raise Exception ("Too many state entries: " + str(self.numStateEntries))
        self.displayStates = [
            self.parent.add_child(self.displayStatePtr + 16 * x, 0, DODisplayState, "DODisplayState").analyze() for x in range(self.numStateEntries)
        ]
        self.p16 = self.read(2)
        return self

    def description(self):
        desc = super().description()
        desc += "\nNum state entries: " + str(self.numStateEntries)
        desc += "\nPrimitive pointer: " + hex(self.parent.absolute + self.primitivePtr)
        desc += "\nDisplay pointer: " + hex(self.parent.absolute + self.displayStatePtr)
        return desc

class DODisplayState(FileChunk):
    def analyze(self):
        # I think 03 is DISPLAY_STATE_VCD
        # descriptors are 10 for bat, 11 for mario
        # 00 is GX_NONE, 01 is GX_DIRECT, 10 is GX_INDEX8, 11 is GX_INDEX16
        self.id = intFromBytes(self.read(1))
        pad = self.read(3)
        self.setting = self.word()
        self.primitiveListPtr = self.word()
        self.primitiveListSize = self.word()
        base = self.parentClass(DOLayout)
        self.primitiveList = PrimitiveList(self.f, self.primitiveListPtr, self.primitiveListSize, "")
        base.adopt_child(self.primitiveList)
        self.primitiveList.analyze()
        return self
    
    def updateState(self, state):
        match self.id:
            case 1:
                setting = self.setting
                # print("setting is " + '{:032b}'.format(setting))
                index = setting & 0b0001111111111111
                # TODO: Fix this with a bitshift if coord ever becomes relevant
                # Why don't I just do it now? idk
                coord = setting & 0b1110000000000000
                setting >>= 16
                wraps = setting & 0b1111
                setting >>= 4
                wrapt = setting & 0b1111
                # print ("texture coord " + str(coord) + " set to texture " + str(index))
                # I think textures with a non-zero coord are just specular something-or-other generally, not gonna worry about it
                if coord == 0:                    
                    state['texture']['index'] = index
                    state['texture']['wraps'] = wraps
                    state['texture']['wrapt'] = wrapt
                    # print ("texture layer 0 set to index " + hex(index) + " and wraps " + hex(wraps) + " and wrapt " + hex(wrapt))
                # else:
                #     print("skipped setting texture index to " + str(index))
            case 3:
                def updateStateDict(state, key, setting):
                    setting = setting & 0b11
                    if setting == 0b00:
                        return
                    out = {}
                    # Not using a dictionary because this has to be ordered
                    out['key'] = key
                    out['direct'] = setting == 0b01
                    out['index_size'] = 1 + (setting & 0b01)
                    state['descriptors'].append(out)
                setting = self.setting
                state['descriptors'] = []
                keys = ['position', 'lighting', 'color0', 'color1', 'texture0', 'texture1', 'texture2', 'texture3', 'texture4', 'texture5', 'texture6', 'texture7']
                # Skip position matrix for now
                setting >>= 2
                for key in keys:
                    updateStateDict(state, key, setting & 0b11)
                    setting >>= 2
                # print ("state dict is " + ', '.join([x['key'] for x in state['descriptors']]))
            case 7:
                state['settings'][7] = self.setting
            case _:
                pass

    def description(self):
        desc = super().description()
        desc += "\nid: " + str(self.id)
        desc += "\nsetting: " + '{:032b}'.format(self.setting)
        desc += "\nPrimitive list size: " + hex(self.primitiveListSize)
        desc += "\nPrimitive list ptr: " + hex(self.parent.absolute + self.primitiveListPtr)
        # desc += "\nPrimitive list: " + self.primitiveList.to_str()
        return desc

class PrimitiveList(FileChunk):
    # Starts with 3 bytes (I think?)
    # 0x90 for GXStart
    # 0x0 - 0x7 for vertex format table index
    # Primitive type (triangles are 0x3, quads are 0x6?)
    # The bat is hitting 0x98 which is out of the reange of all the indexes, some kind of control value? Maybe there's a value for the number of vertices after all
    def analyze(self):
        self.data = []
        l = self.length
        while (l):
            self.data.append(self.byte())
            l -= 1
        return self

    def to_str(self):
        data_str =  '\n' + ' /\n'.join(
                        '\n'.join(
                            '    ' + ' '.join(
                                ''.join('{:02x}'.format(x)
                                    for x in self.data[a+z+y:a+z+y+4]
                                ) for y in range(0, 16, 4)
                            ) for z in range(0, 64, 16)
                        ) for a in range(0, len(self.data), 64)
                    )
        return data_str
    
    def draw(self, state):
        debug = 0
        if debug:
            print ("\n\nDRAWING\n\n")
        data_index = 0
        faces = []
        while data_index < len(self.data) and self.data[data_index] != 0:
            primitive = self.data[data_index]
            data_index += 1
            vertexCount = self.data[data_index] * 256 + self.data[data_index + 1]
            data_index += 2
            vertexSize = 0

            descriptors = state['descriptors']
            for entry in descriptors:
                attribute = entry['key']
                if attribute not in state['attributes']:
                    print ("did not find attribute " + str(attribute))
                    exit(0)
                if entry['direct']:
                    print ("attribute " + str(attribute) + " uses direct mode")
                    exit(0)
                vertexSize += entry['index_size']
            if debug:
                print ("\nprimitive is " + hex(primitive) + ", count is " + hex(vertexCount) + ", vertex size is " + str(vertexSize))
                print ('data is ')
                print (
                    '\n'.join([
                        ','.join(['{:02x}'.format(d) for d in self.data[data_index + x : data_index + x + vertexSize]])
                        for x in range(0, vertexSize*vertexCount, vertexSize)])
                )
            vertexes = []
            while vertexCount > 0:
                vertex = {}
                for entry in descriptors:
                    key = entry['key']
                    attribute = state['attributes'][key]
                    index_size = entry['index_size']
                    index = 0
                    # print ("face size is " + str(faceSize))
                    while index_size:
                        index <<= 8
                        index += self.data[data_index]
                        index_size -= 1
                        data_index += 1
                    # if attribute.at(index) != None:
                        # key = ''.join(c for c in key if not (ord(c) >= ord('0') and ord(c) <= ord('9')))
                    vertex[key] = index + 1
                vertexes.append(vertex)
                vertexCount -= 1
            match primitive:
                case 0x90:
                    # GX_TRIANGLES
                    faces += [vertexes[x:x+3] for x in range(0, len(vertexes), 3)]
                case 0x98:
                    # GX_TRIANGLESTRIP
                    order = 1
                    for i in range(0, len(vertexes) - 2, 1):
                        if order:
                            faces.append([vertexes[i], vertexes[i + 1], vertexes[i + 2]])
                        else:
                            faces.append([vertexes[i], vertexes[i + 2], vertexes[i + 1]])
                        order = not order
                case 0x80:
                    # GX_QUADS
                    faces += [vertexes[x:x+4] for x in range(0, len(vertexes), 4)]
                case _:
                    print ("primitive type " + hex(primitive) + " not supported")
                    exit(0)
        return faces

    def description(self, empty = True):
        if empty:
            return ''
        desc = super().description()
        return desc

# Very temporary
class GPLWrapper(File):
    def __init__(self, f):
        super().__init__(f)

    def analyze(self, offset = 0x20):
        self.gpl = self.add_child(offset, 0, GPL, "gpl")
        self.gpl.analyze()
    
    def toFile(self, outdir):
        for descriptor in self.gpl.geoDescriptors:
            fname = hex(descriptor.absolute) + ".obj"
            descriptor.layout.toFile(outdir + fname)