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

    def getTriangles(self):
        state = {
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
        out = []
        for displayState in self.DODisplayHeader.displayStates:
            displayState.updateState(state)
            out.append({'state': state.copy(), 'triangles': displayState.primitiveList.draw(state)})
        return out

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
        # print(hex(self.quantizeInfo))
        # print(hex(self.parentClass(DOLayout).absolute + self.positionArrPtr))
        # print(hex(self.numPositions * 6 * 2))
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
        # print("color quantize info is " + hex(self.quantizeInfo))
        # print("color count is " + hex(self.numColors))
        # print("data arr is at " + hex(self.parentClass(DOLayout).absolute + self.colorArrPtr))
        self.compCount = intFromBytes(self.read(1))
        self.data = getQuantizedColorData(self.f, self.parentClass(DOLayout).absolute + self.colorArrPtr, self.numColors, self.compCount, self.quantizeInfo)
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
                coord = (setting >> 13) & 0b111
                setting >>= 16
                wraps = setting & 0b1111
                setting >>= 4
                wrapt = setting & 0b1111
                state['texture'+str(coord)] = {}
                state['texture'+str(coord)]['index'] = index
                state['texture'+str(coord)]['wraps'] = wraps
                state['texture'+str(coord)]['wrapt'] = wrapt
            # DIFFERENCE (was id 3)
            case 2:
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
        data_index = 0
        faces = []
        while data_index < len(self.data) and self.data[data_index] != 0:
            # print(hex(self.absolute))
            if debug:
                print ("\nDRAWING\n")
            command = self.data[data_index]
            # DIFFERENCE (shift)
            primitive = command >> 3
            data_index += 1
            # DIFFERENCE (jump forward if 0x61)
            if command == 0x61:
                data_index += 4
                continue
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
                # print (
                #     '\n'.join([
                #         ','.join(['{:02x}'.format(d) for d in self.data[data_index + x : data_index + x + vertexSize]])
                #         for x in range(0, vertexSize*vertexCount, vertexSize)])
                # )
                print(len(self.data)/vertexSize)
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
                    vertex[key] = index
                vertexes.append(vertex)
                vertexCount -= 1
            match primitive:
                # DIFFERENCE (new id)
                case 0x12:
                    # GX_TRIANGLES
                    if len(vertexes) % 3 != 0:
                        print("drawing triangles with " + str(len(vertexes)) + " vertexes")
                    faces += [[vertexes[x+2], vertexes[x+1], vertexes[x]] for x in range(0, len(vertexes), 3)]
                # DIFFERENCE (new id)
                case 0x13:
                    # GX_TRIANGLESTRIP
                    order = 0
                    for i in range(0, len(vertexes) - 2, 1):
                        if order:
                            faces.append([vertexes[i], vertexes[i + 1], vertexes[i + 2]])
                        else:
                            faces.append([vertexes[i + 2], vertexes[i + 1], vertexes[i]])
                        order = not order
                # DIFFERENCE (new id)
                case 0x10:
                    # GX_QUADS
                    if len(vertexes) % 4 != 0:
                        print("drawing quads with " + str(len(vertexes)) + " vertexes")
                    for x in range(0, len(vertexes), 4):
                        faces.append([vertexes[x+2], vertexes[x+1], vertexes[x]])
                        faces.append([vertexes[x], vertexes[x+3], vertexes[x+2]])
                # DIFFERENCE (triangle fan support added)
                case 0x14:
                    # GX_FANS
                    for x in range(len(vertexes) - 2):
                        faces.append([vertexes[x+2], vertexes[x+1], vertexes[0]])    
                case _:
                    print ("primitive type " + hex(primitive) + " not supported")
                    # exit(0)
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