from tpl import *
from gpl import *
from act import *

class MaybeArchive(FileChunk):
    def analyze(self):
        word1 = self.word()
        self.child = None
        if word1 > 1000:
            return
        elif word1 > 0:
            self.child = self.add_child(0, 0, Archive)
        else:
            self.child = self.add_child(0, 0, Model0)

class Archive(FileChunk):
    def analyze(self):
        self.fileCount = self.word()
        self.files = [self.add_child(self.word(), 0, Model0) for x in range(self.fileCount)]
        for x in range(1, self.fileCount):
            if self.files[x].absolute < self.files[x - 1].absolute:
                raise Exception('Archive files not ascending')
        self.success = []
        for i, file in enumerate(self.files):
            try:
                file.analyze()
                self.success.append(i)
            except Exception as e:
                print ("failed analyzing in archive")
                print (e)
                pass

    def toFile(self, outdir):
        if not len(self.success):
            return
        archivedir = outdir + str(self.absolute) + '/'
        if not os.path.exists(archivedir):
            os.mkdir(archivedir)
        for success in self.success:
            f = self.files[success]
            f.toFile(archivedir)

class Model0(FileChunk):
    def analyze(self):
        # Initial testing if this is a valid file
        firstWord = self.word()
        if firstWord != 0:
            raise Exception("gpl doesn't start with 0")
        self.gplPtr = self.word()
        if self.gplPtr > 0x40 or self.gplPtr < 0x20:
            raise Exception("gpl pointer is " + hex(self.gplPtr))
        self.ptr3 = self.word()
        self.texPtr = self.word()
        self.ptr5 = self.word()
        self.ptr6 = self.word()
        self.ptr7 = self.word()
        self.ptr8 = self.word()
        positions = [self.gplPtr, self.ptr3, self.texPtr, self.ptr5, self.ptr6, self.ptr7, self.ptr8]
        positions.sort()
        nextSection = {}
        self.ACT = None
        self.GPL = None
        self.TEXPalette = None
        self.SKN = None
        for i in range(0, len(positions) - 1):
            nextSection[positions[i]] = positions[i + 1]
        nextSection[positions[-1]] = self.length
        if self.ptr3:
            self.ACT = self.add_child(self.ptr3, nextSection[self.ptr3] - self.ptr3, ACTLayout, "ACT Layout")
            self.ACT.analyze()
        if self.gplPtr:
            self.GPL = self.add_child(self.gplPtr, nextSection[self.gplPtr] - self.gplPtr, GPL, "GPL")
            self.GPL.analyze()
        if self.texPtr:
            self.TEXPalette = self.add_child(self.texPtr, nextSection[self.texPtr] - self.texPtr, TEXPalette, "TPL")
            self.TEXPalette.analyze()
        # self.SKN = self.add_child(self.ptr5, nextSection[self.ptr5] - self.ptr5, SKN, "Skin")
        # self.SKN.analyze()
        self.name = str(self.absolute)
        if self.ACT:
            self.name += '_' + self.ACT.geoName
        elif self.GPL:
            self.name += '_' + self.GPL.geoDescriptors[0].layout.DOTextureDataHeaders[0].paletteName

    def toFile(self, outdir):
        try:
            file_dir = outdir + self.name
            while os.path.exists(file_dir):
                file_dir += '_'
            os.mkdir(file_dir)
            file_dir += '/'
            if self.TEXPalette:
                self.TEXPalette.writeChildrenToFile(file_dir)
            if self.GPL:
                self.GPL.toFile(file_dir, self.ACT)
        except Exception as e:
            print ("Failed in model0 tofile")
            print(e)
            pass    