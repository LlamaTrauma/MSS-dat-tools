from base import *
from ds import *
import numpy as np
from helper import *
from model0 import *

# The general output of all of this
# Each bone has a child, a parent, a base transform, and a list of affected vertexes and weights
class Bone():
    def __init__(self, id, GEOID, orientation, children, parent, relative, track_id, skinned):
        self.id = id
        self.GEOID = GEOID
        self.orientation = orientation
        if self.orientation is None:
            self.orientation = Object()
            self.orientation.scale = [1, 1, 1]
            self.orientation.quaternion = [1, 0, 0, 0]
            self.orientation.axis_angle = [1, 0, 0, 0]
            self.orientation.translation = [0, 0, 0]
            self.orientation.transform = np.identity(4)
        self.skinned = skinned
        self.parent = parent
        self.relative = relative
        if not relative:
            print('bone ' + str(self.id) + ' is not relative')
        self.track_id = track_id
        self.vertexInfluences = {}

    def absolute_transform(self):
        parent = self.parent
        transform = self.orientation.transform
        while parent is not None:
            transform = np.matmul(transform, parent.orientation.transform)
            parent = parent.parent
        return transform

    def head(self):
        return np.matmul([0, 0, 0, 1], self.absolute_transform())[:3]
        # return np.matmul([0, 0, 0, 1], self.transform)[:3]

    def addInfluence (self, influence):
        vertex = influence.vertexIndex
        if vertex in self.vertexInfluences:
            # print('initial position set again')
            # if sum([influence.source_position[i] != self.vertexInfluences[vertex][1][i] for i in range(3)]) > 0:
            #     print('    attempt to set initial position differently')
            self.vertexInfluences[vertex][0] += influence.weight
            # self.vertexInfluences[vertex][0] = influence.weight
            self.vertexInfluences[vertex][2].append(influence.source)
        else:
            self.vertexInfluences[vertex] = [influence.weight, influence.source_position, [influence.source]]

class ACTLayout(FileChunk):
    def analyze(self):
        # 0x007B7960
        self.versionNum = self.word()
        self.actorID = self.half()
        self.boneCount = self.half()
        # There's a tree structure here with a node embedded in each bone layout
        self.tree = self.add_child(0x8, 0, Tree, "Bone Hierarchy")
        self.tree.analyze()
        self.read(0x8)
        self.geoNamePtr = self.word()
        self.skinFileID = intFromBytes(self.read(2))
        self.pad16 = self.read(2)
        self.userDataSize = self.word()
        self.userDataPtr = self.word()
        self.geoName = self.readStr(self.geoNamePtr)

        # The user-defined data section holds the linking information between bones and animation tracks (for some reason)
        # That gets read here and stored in the bone objects when they're created
        track_ids = []
        old_pos = self.tell()
        self.seek(self.userDataPtr + 0x2)
        self.track_bone_offset = self.half()
        track_type = self.half()
        self.seek(self.userDataPtr + 0xC)
        for i in range(self.boneCount):
            track_ids.append(self.half())
        # print(track_ids)
        bone_track_pairs = {}
        self.seek(self.userDataPtr + self.track_bone_offset + 0xC)
        for i in range(self.boneCount):
            bone_id = self.byte()
            type = self.byte()
            bone_track_pairs[bone_id] = track_ids[i]
        self.seek(old_pos)

        self.bone_layouts = {}
        node_stack = self.tree.hierarchy()
        self.non_skinned_bones = {}
        while len(node_stack):
            node = node_stack.pop()
            # Start of Tree + address directly after node - node length - 4 (because there's an orientation thing before the node)
            # I should have had the hierarchy return the address the node starts at but oh well it's all relative anyway
            bone_layout = self.add_child(0x8 + node.addr - 0x14, 0, ACTBoneLayout, "Bone Layout #" + hex(i))
            bone_layout.analyze()
            self.non_skinned_bones[bone_layout.geoFileId] = bone_layout.id
            if node.parent is None:
                bone_layout.parent = None
            else:
                bone_layout.parent = self.bone_layouts[node.parent.addr]
            # if bone_layout.id in bone_track_pairs:
            #     bone_layout.track_id = bone_track_pairs[bone_layout.id]
            # else:
            #     bone_layout.track_id = -1
            self.bone_layouts[node.addr] = bone_layout
            for child in node.children:
                node_stack.append(child)

        ordered_layouts = list(self.bone_layouts.keys())
        ordered_layouts.sort()
        for i, addr in enumerate(ordered_layouts):
            bone = self.bone_layouts[addr]
            bone.track_id = 0

    def bones(self):
        # Hash of bones by bone id
        bones = {}
        # Feed this into some more abstract object
        for bone_addr in self.bone_layouts:
            bone = self.bone_layouts[bone_addr]
            bone_obj = Bone(bone.id, bone.geoFileId, bone.orientation_srt, [], None, bone.inheritance, bone.track_id, bone.skinned)
            bones[bone.id] = bone_obj
        # Second pass to set parents
        for bone_addr in self.bone_layouts:
            bone = self.bone_layouts[bone_addr]
            if bone.parent is not None:
                bones[bone.id].parent = bones[bone.parent.id]
        return bones

    def ids_by_ind(self):
        ids = []
        addrs = list(self.bone_layouts.keys())
        addrs.sort()
        for layout_addr in addrs:
            layout = self.bone_layouts[layout_addr]
            ids.append(layout.id)
        return ids

    def description(self):
        desc = super().description()
        desc += "\nBones: " + str(self.boneCount)
        desc += "\nGPL Name: " + self.geoName
        desc += "\nSkin File ID: " + hex(self.skinFileID)
        desc += "\nUser defined data size: " + hex(self.userDataSize)
        desc += "\nUser defined data ptr: " + hex(self.absolute + self.userDataPtr)
        return desc

class DSTree(FileChunk):
    def analyze(self):
        pass

class MTX(FileChunk):
    def analyze(self):
        self.data = self.read(0x30)

class ACTBoneLayout(FileChunk):
    def analyze(self):
        self.orientationPTR = self.word()
        # print(hex(self.parent.absolute + self.orientationPTR))
        self.branch = ['{:04x}'.format(self.word()) for i in range(4)]
        self.geoFileId = self.half()
        self.skinned = self.geoFileId == 65535
        if self.geoFileId == 65535:
            self.geoFileId = 0
        self.id = self.half()
        self.inheritance = self.byte()
        self.priority = self.byte()
        self.half()
        if self.orientationPTR == 0:
            self.orientation_srt = None
        else:
            # print('bone id is ' + str(self.id))
            # print(hex(0x04aa6c20 + self.parent.absolute + self.orientationPTR))
            self.orientation_srt = SRT(self.f, self.parent.absolute + self.orientationPTR, 0x34, "Transformation")
            self.orientation_srt.analyze()
            # print(self.id)
            # print(["{:.2f}".format(x) for x in self.orientation_srt.scale])
            # print(["{:.2f}".format(x) for x in self.orientation_srt.quaternion])
            # print(["{:.2f}".format(x) for x in self.orientation_srt.translation])
            # print('-------------------------')
        return self
    
    def description(self):
        # return ''
        desc = super().description()
        if self.orientationPTR:
            desc += "\nOrientation ptr: " + hex(self.parent.absolute + self.orientationPTR)
        if self.geoFileId != 0xFFFF:
            desc += "\nGEO File ID: " + hex(self.geoFileId)
        # else:
        #     return ''
        desc += "\nBone ID: " + hex(self.id)
        desc += "\nPriority: " + hex(self.priority)
        if self.inheritance:
            desc += "\nInherits transform from parent"
        return desc

# The influence a bone has on a vertex. Parameters are bone id, weight, the address of a vertex array in the gpl this vertex is a part of, and the index in that array
# Don't know if it's safe to combine the gplArrAddr and index into a single param, because the size of a single vertex's data can vary between gpls 
class BoneInfluence():
    def __init__(self, boneID, weight, vertexIndex, source_position, source=''):
        self.boneID = boneID
        self.weight = weight
        self.vertexIndex = vertexIndex
        self.source_position = source_position
        # string description of where this came from for debugging
        self.source = source

    def calculateVertexIndex(self, vertexSize):
        # Given the size of a vertex, we can combine the gplArrAddr and arrIndex into a single value
        self.vertexIndex = self.arrAddr // vertexSize + self.arrIndex
        # Now we have a tidy struct with a vertex id, a bone id, and a weight

class SKN(FileChunk):
    def analyze(self):
        self.SK1Cnt = self.half()
        self.SK2Cnt = self.half()
        self.SKAccCnt = self.half()
        self.quantizeInfo = self.byte()
        self.byte()
        self.SK1Ptr = self.word()
        self.SK2Ptr = self.word()
        self.SKAccPtr = self.word()
        self.memClrPtr = self.word()
        self.memClrSze = self.word()
        self.flushIndArr = self.word()
        self.flushIndSze = self.word()
        self.SK1s = [self.add_child(self.SK1Ptr + 0x40 * x, 0x40, SK1, "SK1 struct").analyze() for x in range(self.SK1Cnt)]
        self.SK2s = [self.add_child(self.SK2Ptr + 0x74 * x, 0x74, SK2, "SK2 struct").analyze() for x in range(self.SK2Cnt)]
        self.SKAccs = [self.add_child(self.SKAccPtr + 0x44 * x, 0x44, SKAcc, "SKAcc struct").analyze() for x in range(self.SKAccCnt)]
        # self.print()

    def boneInfluences(self):
        boneInfluences = []
        for sk1 in self.SK1s:
            boneInfluences += sk1.boneInfluences()
        for sk2 in self.SK2s:
            boneInfluences += sk2.boneInfluences()
        for skacc in self.SKAccs:
            boneInfluences += skacc.boneInfluences()
        return boneInfluences

    def description(self):
        desc = super().description()
        # desc += "\nLayout Ptr: " + hex(self.layoutPtr)
        desc += "\nSK1 count: " + hex(self.SK1Cnt)
        desc += "\nSK2 count: " + hex(self.SK2Cnt)
        desc += "\nSKAcc count: " + hex(self.SKAccCnt)
        desc += "\nQuantization info: " + hex(self.quantizeInfo)
        desc += "\nFlush ind size: " + hex(self.absolute + self.flushIndArr)
        desc += "\nFlush ind cnt: " + str(self.flushIndSze)
        return desc

class SK1(FileChunk):
    def analyze(self):
        # Gets populated at runtime
        # self.mtx = self.add_child(0, 0x30, MTX, "Runtime Matrix")
        self.seek(0x30)
        self.vertexArr = self.word()
        # print(hex(self.parent.absolute + self.vertexArr + 0x04aa6c20))
        self.gplVertexArr = self.word()
        self.boneIndex = self.half()
        # print('SK1')
        # print(str(self.boneIndex))
        # print('------------------------')
        self.vertexCnt = self.half()
        # print(hex(self.vertexCnt))
        self.vertexOffset = self.byte()
        # print(self.vertexOffset)
        self.read(3)
        return self

    def boneInfluences(self):
        position_normal_data = getQuantizedData(self.f, self.parent.absolute + self.vertexArr + self.vertexOffset, self.vertexCnt * 2, 3, self.parent.quantizeInfo)
        vertexSize = 6 * quantizedDataSize(self.parent.quantizeInfo)
        boneInfluences = [BoneInfluence(self.boneIndex, 256, (self.gplVertexArr + self.vertexOffset) // vertexSize + i, position_normal_data[i * 2], 'SK1'
            ) for i in range(self.vertexCnt)]
        return boneInfluences

    def description(self):
        desc = super().description()
        desc += "\nVertex arr: " + hex(self.parent.absolute + self.vertexArr)
        desc += "\nOffset: " + hex(self.vertexOffset)
        desc += "\nVertex arr in GPL: " + hex(self.gplVertexArr)
        desc += "\nVertex count: " + hex(self.vertexCnt)
        desc += "\nVertex offset: " + hex(self.vertexOffset)
        desc += "\nBone index: " + hex(self.boneIndex)
        # desc += "\nPositions: " + ' / '.join(
        #     ', '.join(
        #         ["{:.2f}".format(x) for x in self.positions[y]]
        #     ) for y in range(len(self.positions))
        # )
        # desc += "\nNormals: " + ' / '.join(
        #     ', '.join(
        #         ["{:.2f}".format(x) for x in self.normals[y]]
        #     ) for y in range(len(self.normals))
        # )
        return desc

class SK2(FileChunk):
    def analyze(self):
        # Gets populated at runtime
        # self.mtx1 = self.add_child(0, 0x30, MTX, "Runtime Matrix")
        # self.mtx1 = self.add_child(0x30, 0x30, MTX, "Runtime Matrix")
        self.seek(0x60)
        self.vertexArr = self.word()
        self.weightArr = self.word()
        self.gplVertexArr = self.word()
        self.boneIndex1 = self.half()
        self.boneIndex2 = self.half()
        # print('SK2')
        # print(str(self.boneIndex1))
        # print(str(self.boneIndex2))
        # print('------------------------')
        self.vertexCnt = self.half()
        self.vertexOffset = self.byte()
        self.read(1)
        return self

    def boneInfluences(self):
        position_normal_data = getQuantizedData(self.f, self.parent.absolute + self.vertexArr + self.vertexOffset, self.vertexCnt * 2, 3, self.parent.quantizeInfo)
        vertexSize = 6 * quantizedDataSize(self.parent.quantizeInfo)
        self.parent.seek(self.weightArr)
        self.raw_weights = self.parent.read(self.vertexCnt * 2)
        self.weights = []
        for w in range(0, self.vertexCnt * 2, 2):
            w1 = self.raw_weights[w]
            w2 = self.raw_weights[w+1]
            self.weights.append([w1, w2])
        boneInfluences = []
        for i in range(self.vertexCnt):
            # self.vertexOffset = 0
            boneInfluences.append(BoneInfluence(self.boneIndex1, self.weights[i][0], (self.gplVertexArr + self.vertexOffset) // vertexSize + i, position_normal_data[i * 2], 'SK2'))
            boneInfluences.append(BoneInfluence(self.boneIndex2, self.weights[i][1], (self.gplVertexArr + self.vertexOffset) // vertexSize + i, position_normal_data[i * 2], 'SK2'))
        return boneInfluences

    def description(self):
        desc = super().description()
        desc += "\nVertex arr: " + hex(self.parent.absolute + self.vertexArr)
        desc += "\nVertex arr in GPL: " + hex(self.gplVertexArr)
        desc += "\nWeight arr: " + hex(self.parent.absolute + self.weightArr)
        desc += "\nVertex count: " + hex(self.vertexCnt)
        desc += "\nVertex offset: " + hex(self.vertexOffset)
        desc += "\nBone index 1: " + hex(self.boneIndex1)
        desc += "\nBone index 2: " + hex(self.boneIndex2)
        return desc

# uniqueDests = {}
class SKAcc(FileChunk):
    def analyze(self):
        self.seek(0x30)
        self.vertexArr = self.word()
        self.destArr = self.word()
        self.gplDestArr = self.word()
        self.weightArr = self.word()
        self.boneIndex = self.half()
        # print('SKAcc')
        # print(str(self.boneIndex))
        # print('------------------------')
        # print(self.boneIndex)
        # self.gplIndex = self.parent.parent.ACT.boneLayouts[self.boneIndex].geoFileId
        self.vertexCnt = self.half()
        return self

    def boneInfluences(self):
        position_normal_data = getQuantizedData(self.f, self.parent.absolute + self.vertexArr, self.vertexCnt * 2, 3, self.parent.quantizeInfo)
        vertexSize = 6 * quantizedDataSize(self.parent.quantizeInfo)
        self.parent.seek(self.weightArr)
        self.raw_weights = self.parent.read(self.vertexCnt)
        self.weights = []
        for w in range(self.vertexCnt):
            self.weights.append(self.raw_weights[w])
        self.parent.seek(self.destArr)
        self.raw_dests = self.parent.read(self.vertexCnt * 2)
        self.dests = []
        for d in range(0, self.vertexCnt * 2, 2):
            self.dests.append(struct.unpack('>H', self.raw_dests[d:d+2])[0])
        # global uniqueDests
        # for dest in self.dests:
        #     uniqueDests[dest] = 1
        # print(len(uniqueDests.keys()))
        # print(hex(self.parent.absolute + self.destArr))
        # print(self.weights)
        # print(self.dests)
        # print(position_normal_data)
        boneInfluences = [BoneInfluence(self.boneIndex, self.weights[i], self.gplDestArr // vertexSize + self.dests[i], position_normal_data[i * 2], 'SKAcc') for i in range(self.vertexCnt)]
        return boneInfluences
    
    def description(self):
        desc = super().description()
        desc += "\nVertex arr: " + hex(self.parent.absolute + self.vertexArr)
        desc += "\nDestination arr: " + hex(self.parent.absolute + self.destArr)
        desc += "\nDestination arr in GPL: " + hex(self.gplDestArr)
        desc += "\nWeight arr: " + hex(self.parent.absolute + self.weightArr)
        desc += "\nVertex count: " + hex(self.vertexCnt)
        desc += "\nBone index: " + hex(self.boneIndex)
        # desc += "\nBone geo file: " + hex(self.gplIndex)
        return desc
