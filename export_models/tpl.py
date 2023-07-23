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

    def writeChildrenToFile(self, outdir):
        # Generate the mtl file as we go along
        mtl = open(outdir + "textures.mtl", 'w')
        for ind, descriptor in enumerate(self.descriptors):
            child = descriptor
            dataLength = child.height * child.width * {0:4,1:8,2:8,3:16,4:16,5:16,6:32,8:4,9:8,10:16,14:4}[child.format] >> 3
            hasPalette = descriptor.paletteDataPtr > 0
            paletteInd = 0
            while paletteInd <= 2 * hasPalette:
                fname = outdir + str(ind) + '.tpl'
                pngname = str(ind) + '.png'
                if hasPalette:
                    fname = outdir + str(ind) + '_' + str(paletteInd) + '.tpl'
                    pngname = str(ind) + '_' + str(paletteInd) + '.png'

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
                out.write(itb(child.height, 2))
                out.write(itb(child.width, 2))
                out.write(itb(child.format, 4))
                out.write(itb(0x40 + hasPalette * 0x20, 4))
                out.write(itb(child.wrapS, 4))
                out.write(itb(child.wrapT, 4))
                out.write(itb(child.minFilter, 4))
                out.write(itb(child.magFilter, 4))
                out.write(itb(child.LODBias, 4))
                out.write(itb(child.edgeLODEnable, 1))
                out.write(itb(child.minLOD, 1))
                out.write(itb(child.maxLOD, 1))
                out.write(itb(child.unpacked, 1))

                paletteDataLen = self.dataLens[descriptor.paletteDataPtr]
                paletteDataOffset = 0
                paletteDataPad = 0
                if hasPalette:
                    paletteDataOffset = 0x60 + dataLength
                    mod = paletteDataOffset % 0x20
                    if mod != 0:
                        paletteDataPad = 0x20 - mod
                        paletteDataOffset += paletteDataPad
                    # Palette header
                    out.write(itb(paletteDataLen >> 1, 2))
                    out.write(itb(1, 1))
                    out.write(itb(0, 1))
                    # Guessing the format here - 2 seems to usually work
                    out.write(itb(paletteInd, 4))
                    out.write(itb(paletteDataOffset, 4))

                # Pad to multiple of 0x20 (0x40 or 0x60 here)
                out.write(itb(0, 0x8 + hasPalette * 0x14))
                self.seek(child.dataPtr)
                out.write(self.read(dataLength))
                if hasPalette:
                    out.write(itb(0, paletteDataPad))
                    self.seek(child.paletteDataPtr)
                    out.write(self.read(paletteDataLen))
                out.close()
                os.system('wimgt decode -q -d ' + outdir + pngname + ' ' + fname)
                # os.remove(fname)
                paletteInd += 1

            mtl.write('newmtl ' + str(ind) + '\n')
            # mtl.write('Ns 250\n')
            # mtl.write('Ka 1 1 1\n')
            mtl.write('Kd 1 1 1\n')
            # mtl.write('Ks 1 1 1\n')
            # mtl.write('Ni 1\n')
            # mtl.write('d 1\n')
            # mtl.write('illum 0\n')
            if hasPalette:
                mtl.write('map_Kd ' + str(ind) + '_2.png' + '\n')
            else:
                mtl.write('map_Kd ' + pngname + '\n')

        mtl.close()

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
        self.read(4)
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