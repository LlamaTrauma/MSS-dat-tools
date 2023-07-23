from base import *
from ds import *
import numpy as np
from helper import *

class ACTLayout(FileChunk):
    def analyze(self):
        # 0x007B7960
        self.versionNum = self.word()
        self.actorID = self.half()
        self.boneCount = self.half()
        self.tree = self.add_child(0x8, 0x8, Tree, "Bone Hierarchy")
        self.read(0x8)
        self.geoNamePtr = self.word()
        self.skinFileID = intFromBytes(self.read(2))
        self.pad16 = self.read(2)
        self.userDataSize = self.word()
        self.userDataPtr = self.word()
        self.geoName = self.readStr(self.geoNamePtr)
        self.boneLayouts = []
        self.GEOBones = {}
        for i in range(self.boneCount):
            bone = self.add_child(0x20 + 0x1c * i, 0x1c, ACTBoneLayout, "Bone Layout #" + hex(i))
            bone.analyze()
            self.boneLayouts.append(bone)
            if bone.geoFileId != 0xFFFF:
                self.GEOBones[bone.geoFileId] = i
        self.tree.analyze(-0x4)
        # print (self.tree.description())
    
    def geoTransformation(self, index):
        transformation = np.identity(4)
        if index not in self.GEOBones:
            if index != 0:
                print ("GEO index not found")
            return transformation
        # I'm assuming every branch in a bonelayout is connected to the tree, which seems sane
        boneIndex = self.GEOBones[index]
        while 1:
            node = self.tree.nodeByIndex(boneIndex)
            bone = self.boneLayouts[boneIndex]
            # print ("\nbone " + hex(boneIndex) 
            #        + " at offset " + hex(bone.srt.absolute)
            #        + ' / ' + hex(bone.srt.absolute + 0x04aa6c20)
            #        + ' inherits: ' + hex(bone.inheritance))
            # print (str(bone.srt.to_string()))
            transformation = np.matmul(transformation, bone.srt.transformation)
            if not bone.inheritance or node.parent == 0:
                break
            boneIndex = self.tree.nodeByOffset(node.parent).id
        return transformation

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

# May want to add a matrix type into this and move some of the code to that class later
class SRT(FileChunk):
    def analyze(self, type = None):
        if type == 0:
            self.type = type
            self.transformation = np.identity(4)
            return
        self.values = ['{:02x}'.format(self.byte())]
        self.read(3)
        self.values += ['{:.2f}'.format(self.float()) for x in range(12)]
        self.seek(0)
        self.type = self.byte()
        self.read(3)
        if type != None:
            self.type = type
        self.transformation = np.identity(4)
        # None
        if self.type == 0x0:
            return self
        elif self.type in [0x4, 0x8, 0xc]:
            self.scale = [self.float(), self.float(), self.float()]
            self.quaternion = [self.float(), self.float(), self.float(), -self.float()]
            self.translation = [self.float(), self.float(), self.float()]
            self.scalingMatrix = np.array([
                [self.scale[0], 0, 0, 0],
                [0, self.scale[1], 0, 0],
                [0, 0, self.scale[2], 0],
                [0, 0, 0,             1],
            ])
            self.rotationMatrix = quaternion_rotation_matrix(
                [self.quaternion[x] for x in [0, 1, 2, 3]]
            )
            self.translationMatrix = np.array([
                [1, 0, 0, 0],
                [0, 1, 0, 0],
                [0, 0, 1, 0],
                [self.translation[0], self.translation[1], self.translation[2], 1]
            ])
            self.transformation = np.matmul(np.matmul(self.scalingMatrix, self.rotationMatrix), self.translationMatrix)
        return self

    def to_string(self):
        if self.type == None:
            return "none"
        out = "format: " + '{:02x}'.format(self.type)
        out = "data: " + ', '.join([x for x in self.values])
        return out

class ACTBoneLayout(FileChunk):
    def analyze(self):
        self.orientationPTR = self.word()
        self.branch = ['{:04x}'.format(self.word()) for i in range(4)]
        self.geoFileId = self.half()
        self.id = self.half()
        self.inheritance = self.byte()
        self.priority = self.byte()
        self.half()
        self.srt = SRT(self.f, self.parent.absolute + self.orientationPTR, 0x34, "Transformation")
        if self.orientationPTR == 0:
            self.srt.analyze(0)
        else:
            self.srt.analyze()
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

    def description(self):
        desc = super().description()
        # desc += "\nLayout Ptr: " + hex(self.layoutPtr)
        desc += "\nSK1 count: " + hex(self.SK1Cnt)
        desc += "\nSK2 count: " + hex(self.SK2Cnt)
        desc += "\nSKAcc count: " + hex(self.SKAccCnt)
        desc += "\nQuantization info: " + hex(self.quantizeInfo)
        return desc

class SK1(FileChunk):
    def analyze(self):
        # Gets populated at runtime
        # self.mtx = self.add_child(0, 0x30, MTX, "Runtime Matrix")
        self.seek(0x30)
        self.vertexArr = self.word()
        self.gplVertexArr = self.word()
        self.boneIndex = self.half()
        self.vertexCnt = self.half()
        self.vertexOffset = self.byte()
        self.read(3)
        self.vertices = getQuantizedData(self.f, self.parent.absolute + self.vertexArr + self.vertexOffset, self.vertexCnt, 6, self.parent.quantizeInfo)
        self.positions = [[x[0], x[1], x[2]] for x in self.vertices]
        self.normals = [[x[3], x[4], x[5]] for x in self.vertices]
        # print(self.vertices)
        return self
    
    def description(self):
        desc = super().description()
        desc += "\nVertex arr: " + hex(self.parent.absolute + self.vertexArr)
        desc += "\nOffset: " + hex(self.vertexOffset)
        desc += "\nVertex arr in GPL: " + hex(self.gplVertexArr)
        desc += "\nVertex count: " + hex(self.vertexCnt)
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
        self.vertexCnt = self.half()
        self.vertexOffset = self.byte()
        self.read(1)
        return self
    
    def description(self):
        desc = super().description()
        desc += "\nVertex arr: " + hex(self.parent.absolute + self.vertexArr)
        desc += "\nVertex arr in GPL: " + hex(self.gplVertexArr)
        desc += "\nWeight arr: " + hex(self.parent.absolute + self.weightArr)
        desc += "\nVertex count: " + hex(self.vertexCnt)
        desc += "\nBone index 1: " + hex(self.boneIndex1)
        desc += "\nBone index 2: " + hex(self.boneIndex2)
        return desc

class SKAcc(FileChunk):
    def analyze(self):
        # Gets populated at runtime
        # self.mtx = self.add_child(0, 0x30, MTX, "Runtime Matrix")
        self.seek(0x30)
        self.vertexArr = self.word()
        self.destArr = self.word()
        self.gplDestArr = self.word()
        self.weightArr = self.word()
        self.boneIndex = self.half()
        self.vertexCnt = self.half()
        return self
    
    def description(self):
        desc = super().description()
        desc += "\nVertex arr: " + hex(self.parent.absolute + self.vertexArr)
        desc += "\nDestination arr: " + hex(self.parent.absolute + self.destArr)
        desc += "\nDestination arr in GPL: " + hex(self.gplDestArr)
        desc += "\nWeight arr: " + hex(self.parent.absolute + self.weightArr)
        desc += "\nVertex count: " + hex(self.vertexCnt)
        desc += "\nBone index: " + hex(self.boneIndex)
        return desc