from base import *
from helper import *
import os

globalcounter = 0

class TEXPalette(FileChunk):
    def analyze(self):
        global globalcounter
        self.numTPLs = self.half()
        if self.numTPLs > 10000:
            raise Exception("Too many tpls: " + str(self.numTPLs))
        self.numCLUTsMaybe = self.half()
        # if self.numCLUTsMaybe != 0:
        #     print ("non-zero clut count at " + str(self.absolute))
        self.descriptors = []
        dataOffsets = []
        for i in range (0, self.numTPLs):
            descriptor = self.add_child(4 + i * 0x20, 0, TEXDescriptor, "tex header")
            self.descriptors.append(descriptor)
            descriptor.analyze()
            dataOffsets.append(descriptor.dataPtr)
            dataOffsets.append(descriptor.paletteDataPtr)
        if len(self.descriptors) == 0:
            return
        dataOffsets.sort()
        self.dataLens = {}
        for i in range(len(dataOffsets) - 1):
            ptr = dataOffsets[i]
            self.dataLens[ptr] = dataOffsets[i + 1] - ptr
            # self.dataLens[ptr] = dataOffsets[-1] - ptr
        self.dataLens[dataOffsets[-1]] = self.length - dataOffsets[-1]

class TEXDescriptor(FileChunk):
    def analyze(self):
        self.dataPtr = self.word()
        self.paletteDataPtr = self.word()
        # if self.paletteDataPtr != 0:
        #     print ("Palette at " + hex(self.absolute) + " in " + self.f.name)
        self.height = self.half()
        self.width = self.half()
        self.edgeLODEnable = self.byte()
        self.minLOD = self.byte()
        self.maxLOD = self.byte()
        self.unpacked = self.byte()
        self.word()
        self.read(3)
        self.format = self.byte()
        # if self.format != 0xe:
        # print ("format is " + hex(self.format))
        # print ("offset is " + hex(self.offset) + ", data ptr is " + hex(self.dataPtr) + '\n')
        self.paletteEntries = self.half()
        self.paletteFormat = self.byte()
        self.read(1)
        self.read(4)
        # Don't know where these are
        self.LODBias = 0
        self.wrapS = 0
        self.wrapT = 0
        self.minFilter = 0
        self.magFilter = 0
    
    def description(self):
        desc = super().description()
        desc += "\nData ptr: " + hex(self.parent.absolute + self.dataPtr)
        desc += "\nFormat: " + hex(self.format)
        return desc

    def toFile(self, path):
        dataLength = self.height * self.width * {0:4,1:8,2:8,3:16,4:16,5:16,6:32,8:4,9:8,10:16,14:4}[self.format] >> 3
        hasPalette = self.paletteDataPtr > 0
        fname = path + '.tpl'
        pngname = path + '.png'

        out = open(fname, 'wb')
        # TEXPalette
        out.write(itb(0x0020AF30, 4))
        out.write(itb(1, 4))
        out.write(itb(0xC, 4))

        # TEXDescriptor
        out.write(itb(0x14, 4))
        if hasPalette:
            out.write(itb(0x38, 4))
        else:
            out.write(itb(0, 4))

        # TEXHeader
        out.write(itb(self.height, 2))
        out.write(itb(self.width, 2))
        out.write(itb(self.format, 4))
        out.write(itb(0x40 + hasPalette * 0x20, 4))
        out.write(itb(self.wrapS, 4))
        out.write(itb(self.wrapT, 4))
        out.write(itb(self.minFilter, 4))
        out.write(itb(self.magFilter, 4))
        out.write(itb(self.LODBias, 4))
        out.write(itb(self.edgeLODEnable, 1))
        out.write(itb(self.minLOD, 1))
        out.write(itb(self.maxLOD, 1))
        out.write(itb(self.unpacked, 1))

        paletteDataLen = self.paletteEntries * 2
        paletteDataOffset = 0
        paletteDataPad = 0
        if hasPalette:
            paletteDataOffset = 0x60 + dataLength
            mod = paletteDataOffset % 0x20
            if mod != 0:
                paletteDataPad = 0x20 - mod
                paletteDataOffset += paletteDataPad
            # Palette header
            out.write(itb(self.paletteEntries, 2))
            out.write(itb(1, 1))
            out.write(itb(0, 1))
            # Guessing the format here - 2 seems to usually work
            out.write(itb(self.paletteFormat, 4))
            out.write(itb(paletteDataOffset, 4))

        # Pad to multiple of 0x20 (0x40 or 0x60 here)
        out.write(itb(0, 0x8 + hasPalette * 0x14))
        self.parent.seek(self.dataPtr)
        out.write(self.parent.read(dataLength))
        if hasPalette:
            out.write(itb(0, paletteDataPad))
            self.parent.seek(self.paletteDataPtr)
            out.write(self.parent.read(paletteDataLen))
        out.close()
        os.system('wimgt decode -q -d ' + pngname + ' ' + fname)
        os.remove(fname)