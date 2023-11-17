from helper import *

normals_enabled = True
colors_enabled = False

class ModelImport():
    def __init__(self, positions, normals, textureCoords, textureGroups, textures, bones):
        positions = ([Position(0, 0, 0)] * 10) + positions + ([Position(0, 0, 0)] * 10)
        for group in textureGroups:
            for triangle in group.triangles:
                triangle.positionInds = [x + 10 for x in triangle.positionInds]
        for bone in bones.values():
            for influence in bone.influences:
                influence.absolute_vertex_ind += 10
        # for bone in bones.values():
        #     for influence in bone.influences:
        #         positions[influence.absolute_vertex_ind] = influence.default
        self.gpl = GPL(positions, normals, textureCoords, textureGroups)
        self.act = ACT(bones)
        self.tpl = TPL(textures)
        # print(hex(self.gpl.layout.positionHeader.quantizeInfo))
        self.skn = SKN(bones, self.gpl.layout.positionHeader.quantizeInfo, 0x80, self.gpl.layout.positionHeader.numPositions - 10)
    
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

        outHeader.extend(itb(offset, 4))
        sknBinary = self.skn.binary(offset)
        outData.extend(sknBinary)
        offset += len(sknBinary)
        padding = offset32(offset)
        outData.extend(itb(0, padding))
        offset += padding
        # outHeader.extend(itb(0, 4))

        outHeader.extend(itb(0, 4))
        outHeader.extend(itb(0, 4))
        outHeader.extend(itb(0, 4))
        outHeader.extend(outData)

        return outHeader

class Bone():
    def __init__(self, id, name, orientation):
        self.name = name
        self.id = id
        self.influences = []
        self.orientation = orientation
        # print(self.orientation)
        # self.orientation = np.identity(4)
        self.s, self.r, self.t = mtosrt(orientation)
        # print(r)
        self.parent = None
        self.children = []

    def new_orientation(self, orientation):
        self.orientation = orientation
        self.s, self.r, self.t = mtosrt(orientation)

    def add_influence(self, geo_name, vertex_ind, weight):
        influence = Object()
        influence.geo_name = geo_name
        influence.vertex_ind = vertex_ind
        influence.weight = weight
        # absolute_vertex_ind and default properties added too
        self.influences.append(influence)

class SRT():
    def __init__(self, s=[1, 1, 1], r=[1, 0, 0, 0], t=[0, 0, 0]):
        self.scale = s
        self.quaternion = r
        self.translation = t
        pass

    def from_matrix(self, matrix):
        self.scale, self.quaternion, self.translation = mtosrt(matrix)
        # self.translation = [0, 0, 0]
        # self.scale = [1, 1, 1]
        # self.quaternion = [1, 0, 0, 0]

    def binary(self):
        # self.translation = [0, 0, 0]
        # self.scale = [1, 1, 1]
        # self.quaternion = [1, 0, 0, 0]
        out = bytearray()
        # control type (SRT)
        out.extend(itb(0xc, 1))
        # padding
        out.extend(itb(0, 3))
        # scale
        out.extend(writeQuantizedData(0x40, self.scale))
        # rotation (it's in wxyz, write as xyz-w for some reason)
        out.extend(writeQuantizedData(0x40, [self.quaternion[1], self.quaternion[2], self.quaternion[3], self.quaternion[0]]))
        # translation
        out.extend(writeQuantizedData(0x40, self.translation))
        # padding? idk
        out.extend(itb(0, 8))
        return out

class ACTBoneLayout():
    def __init__(self, bone, bones_by_id):
        self.bones_by_id = bones_by_id
        self.bone = bone

    def binary(self):
        out = bytearray()
        # orientation control ptr
        # orientation controls are right after bone layouts (0x20 + 0x1c * len(self.bones_by_id)) and 0x34 bytes each
        out.extend(itb(0x20 + 0x1c * len(self.bones_by_id) + self.bone.id * 0x34, 4))
        # tree branch
        # assumptions:
            # bones have sequential ids
            # bones are ordered by id in ascending order
            # each bone layout is 7 words = 0x1C bytes
            # so each bone layout starts at actlayout length + id * actbonelayout length
            # 0x20 + 0x1C * id
        previous = 0
        next = 0
        parent = 0
        child = 0
        if self.bone.parent is not None:
            parent = self.bone.parent * 0x1c + 0x20
            parent_bone = self.bones_by_id[self.bone.parent]
            # print(max(parent_bone.children))
            sibling_position = 0
            while parent_bone.children[sibling_position] != self.bone.id:
                sibling_position += 1
            if sibling_position > 0:
                # print(hex(self.bone.id))
                # print('    ' + hex(parent_bone.children[sibling_position - 1]))
                previous = parent_bone.children[sibling_position - 1] * 0x1c + 0x20
            if sibling_position < len(parent_bone.children) - 1:
                next = parent_bone.children[sibling_position + 1] * 0x1c + 0x20
        if len(self.bone.children) > 0:
            child = self.bone.children[0] * 0x1c + 0x20
        out.extend(itb(previous, 4))
        out.extend(itb(next, 4))
        out.extend(itb(parent, 4))
        out.extend(itb(child, 4))
        # geo file id
        # I think 0xFFFF means the skinned GEO or something, idk
        out.extend(itb(0xFFFF, 2))
        # bone id
        out.extend(itb(self.bone.id, 2))
        # Is transform relative to parent?
        out.extend(itb(1, 1))
        # Something priority related, idk
        out.extend(itb(0, 1))
        # padding
        out.extend(itb(0, 2))
        return out

class ACT():
    def __init__(self, bones):
        self.bones = bones

    def binary(self):
        out = bytearray()
        root_bone = 0
        while self.bones[root_bone].parent is not None:
            # print(self.bones[root_bone].parent)
            root_bone += 1
        # for bone in self.bones.values():
        #     print(bone.id)
        #     print(bone.parent)
        #     print(bone.children)
        #     print('_____')
        layout = ACTLayout(len(self.bones), root_bone)
        out.extend(layout.binary())
        id = 0
        while id in self.bones:
            bone_layout = ACTBoneLayout(self.bones[id], self.bones)
            out.extend(bone_layout.binary())
            id += 1
        # print(hex(len(out)))
        orientation_controls = ACTLayoutCTRLs(self.bones)
        out.extend(orientation_controls.binary())
        linking_data = ACTLayoutLinkingData(len(self.bones))
        out.extend(linking_data.binary())
        return out

    def simple_binary(self):
        # Nothing too special about a single-bone act layout, so just copied this verbatim
        # Currently implementing bone support but keeping this around in case I ever have need of it
        return itb(0x007B7960000000010000000C000000200000003CFFFF00000000001000000060000000000000000000000000000000000000000000000000010000006261742E67706C000000000000000000000000000000000000000000000000000000000000000010000300000000000CFFFF000000000000000000000000000000000000, 0x80)

class ACTLayout():
    def __init__(self, bone_count, root_bone):
        self.bone_count = bone_count
        self.root_bone = root_bone

    def binary(self):
        out = bytearray()
        # version number
        out.extend(itb(0x007B7960, 4))
        # actor id
        out.extend(itb(0, 2))
        # bone count
        out.extend(itb(self.bone_count, 2))
        # tree (don't know what the first word does here)
        out.extend(itb(0x0000000C, 4))
        out.extend(itb(self.root_bone * 0x1c + 0x20, 4))
        # geo name ptr
        # hoping this can be null
        out.extend(itb(0, 4))
        # skin file id
        out.extend(itb(0, 2))
        # padding
        out.extend(itb(0, 2))
        # user data size and ptr
        out.extend(itb(0xc + self.bone_count * 2 + 0xc + self.bone_count * 2, 4))
        out.extend(itb(0x20 + (0x1c + 0x34) * self.bone_count, 4))
        return out

class ACTLayoutCTRLs():
    def __init__(self, bones_by_id):
        self.bones_by_id = bones_by_id

    def binary(self):
        out = bytearray()
        id = 0
        while id in self.bones_by_id:
            bone = self.bones_by_id[id]
            srt = SRT(bone.s, bone.r, bone.t)
            # srt.from_matrix(bone.orientation)
            out.extend(srt.binary())
            id += 1
        return out

class ACTLayoutLinkingData():
    def __init__(self, bone_count):
        self.bone_count = bone_count

    def binary(self):
        out = bytearray()
        pad = self.bone_count % 2
        # length of this section
        out.extend(itb(0xc + (self.bone_count + pad) * 2, 4))
        # shrug
        out.extend(itb(3, 2))
        out.extend(itb(0, 2))
        # ptr to start of track ids
        out.extend(itb(0xc, 4))
        # track ids
        for i in range(self.bone_count):
            out.extend(itb(i, 2))
        if pad:
            out.extend(itb(0, 2))
        # Don't know the details of this next section, it's important for the batting animation at least
        out.extend(itb(0xc + (self.bone_count + pad) * 2, 4))
        out.extend(itb(2, 2))
        out.extend(itb(0, 2))
        out.extend(itb(0xc, 4))
        for i in range(self.bone_count):
            out.extend(itb(i, 1))
            if i == 0:
                out.extend(itb(0, 1))
            else:
                out.extend(itb(0, 1))
        if pad:
            out.extend(itb(0, 2))
        return out

class SKN():
    def __init__(self, bones, quantizeInfo, positionHeaderOffset, positionCount):
        # self.quantizeInfo = quantizeInfo
        # print(hex(quantizeInfo))
        # Setting this to the same as the position data's quantization (0x3b or so) didn't work, dunno why
        self.quantizeInfo = 0x0b
        self.positionHeaderOffset = positionHeaderOffset
        self.positionCount = positionCount
        self.bones = {}
        self.all_inds = []
        # return
        id = 0
        while id in bones:
            if len(bones[id].influences) > 0:
                self.bones[id] = bones[id]
            id += 1
        unique_inds = {}
        for bone in self.bones.values():
            for influence in bone.influences:
                unique_inds[influence.absolute_vertex_ind] = 0
        self.all_inds = list(unique_inds.keys())
        # weight_counts = {}
        # for ind in self.all_inds:
        #     weight_counts[ind] = 0
        # for bone in self.bones.values():
        #     for influence in bone.influences:
        #         weight_counts[influence.absolute_vertex_ind] += 1
        # for ind in self.all_inds:
        #     print(weight_counts[ind])

    def binary(self, absolute):
        # Going to use only SKAcc structures for this, which is easiest to implement but probably inefficient
        out = bytearray()
        # SK1 count
        out.extend(itb(0, 2))
        # SK2 count
        out.extend(itb(0, 2))
        # SKAcc count
        out.extend(itb(len(self.bones), 2))
        # Quantization info
        out.extend(itb(self.quantizeInfo, 1))
        # padding
        out.extend(itb(0, 1))
        # SK1 ptr
        out.extend(itb(0, 4))
        # SK2 ptr
        out.extend(itb(0, 4))
        # SKAcc ptr
        out.extend(itb(4 * 9, 4))
        # memory clear ptr/size
        # points to memory in the gpl position data (honestly don't know what it's relative to) to zero before calculating accumulation skinning stuff
        # without this, the vertex data isn't cleared from the last frame and just adds on itself across frames
        # because everything is accumulation headers here, clear the entire position data section
        out.extend(itb(self.positionHeaderOffset, 4))
        # out.extend(itb(0, 4))
        # 7890
        out.extend(itb(self.positionCount * 0xc, 4))
        # out.extend(itb(0, 4))
        # flush index array/size (idk)
        extra_data = bytearray()
        extra_data_ptr = 4 * 9 + len(self.bones) * 0x44
        out.extend(itb(extra_data_ptr, 4))
        # out.extend(itb(len(self.all_inds), 4))
        out.extend(itb(0, 4))
        for ind in self.all_inds:
            extra_data.extend(struct.pack('>H', ind))
        extra_data_ptr += len(self.all_inds) * 2
        _, pad = pad32(extra_data_ptr + absolute)
        extra_data_ptr += pad
        extra_data.extend(itb(0, pad))
        # Make the skinning records
        records = bytearray()
        bone_ids = list(self.bones.keys())
        bone_ids.sort()
        for id in bone_ids:
            bone = self.bones[id]
            influences = bone.influences
            while(len(influences)):
                skacc = SKAcc(id, extra_data_ptr, self.quantizeInfo, influences)
                b, extra_b, extra_data_ptr = skacc.binary(bone.name)
                records.extend(b)
                extra_data.extend(extra_b)
                # influences = influences[250:]
                influences = []
            id += 1
        return out + records + extra_data

class SKAcc():
    def __init__(self, bone_id, extra_data_ptr, quantization, influences):
        self.bone_id = bone_id
        self.influences = influences
        self.extra_data_ptr = extra_data_ptr
        self.quantization = quantization

    def binary(self, name):
        influences = self.influences
        position_normals = []
        destinations = []
        weights = []
        if len(influences) > 341:
            print(len(influences))
            print('Your quantized destinations might be longer than 4092 bytes (this is bad)')
            print(name)
        for influence in influences:
            position_normals.extend(influence.default)
            destinations.append(influence.absolute_vertex_ind)
            weights.append(influence.weight)
        # position_normals = [math.sqrt(abs(x)) for x in position_normals]
        out = bytearray()
        # a runtime matrix
        out.extend(itb(0, 0x30))
        extra_data_ptr = self.extra_data_ptr
        self.extra_data = bytearray()
        # position/normal data ptr
        out.extend(itb(extra_data_ptr, 4))
        self.extra_data.extend(writeQuantizedData(self.quantization, position_normals))
        extra_data_ptr = self.extra_data_ptr + len(self.extra_data)
        _, pad = pad32(len(self.extra_data))
        self.extra_data.extend(itb(0, pad))
        extra_data_ptr += pad
        # destinations ptr
        out.extend(itb(extra_data_ptr, 4))
        for dest in destinations:
            self.extra_data.extend(struct.pack('>H', dest))
        extra_data_ptr = self.extra_data_ptr + len(self.extra_data)
        _, pad = pad32(len(self.extra_data))
        self.extra_data.extend(itb(0, pad))
        extra_data_ptr += pad
        # offset in gpl to add to
        out.extend(itb(0, 4))
        # weights ptr
        out.extend(itb(extra_data_ptr, 4))
        for weight in weights:
            w = math.floor(min(weight, 1) * 255)
            self.extra_data.extend(struct.pack('>B', w))
        extra_data_ptr = self.extra_data_ptr + len(self.extra_data)
        _, pad = pad32(len(self.extra_data))
        self.extra_data.extend(itb(0, pad))
        extra_data_ptr += pad
        # bone id
        out.extend(itb(self.bone_id, 2))
        # vertex count
        out.extend(itb(len(influences), 2))
        return out, self.extra_data, extra_data_ptr

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
        self.positionHeaderOffset = offset
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
        self.quantizeInfo = 0x3d
        self.quantizeInfo = maxShift(self.quantizeInfo, [x for item in positions for x in item.raw()])
        self.positions = positions
        self.componentCount = 6
        self.numPositions = len(positions)

    def binary(self, offset):
        out = bytearray()
        dataPtr = offset + 0x8
        out.extend(itb(dataPtr, 4))
        out.extend(itb(self.numPositions, 2))
        out.extend(itb(self.quantizeInfo, 1))
        out.extend(itb(self.componentCount, 1))
        flatPositions = []
        for position in self.positions:
            flatPositions.extend(position.raw())
            # placeholder normal value
            flatPositions.extend([1, 0, 0])
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

class Object(object):
    def __init__(self) -> None:
        pass