from base import *
import numpy as np
from helper import *

addrs = {}

class MDL0BoneDefaults(FileChunk):
    def analyze(self):
        # magic (CHR0)
        self.seek(0x14)
        bone_offset = self.word()
        self.seek(bone_offset + 0x4)
        bone_count = self.word()
        self.seek(bone_offset + 0x18)
        self.defaults = {}
        for _ in range(bone_count):
            self.word()
            self.word()
            name_ptr = self.word()
            name = self.readStr(name_ptr + bone_offset)
            self.defaults[name] = {}
            data_ptr = self.word()
            pos = self.tell()
            self.seek(data_ptr + bone_offset)
            if self.word() != 0xD0:
                print('len is not 0xD0')
            self.read(0xc)
            id = self.word()
            self.read(0xc)
            scale = [self.float(), self.float(), self.float()]
            rotation = [self.float(), self.float(), self.float()]
            translation = [self.float(), self.float(), self.float()]
            self.defaults[name]['s'] = scale
            self.defaults[name]['r'] = rotation
            self.defaults[name]['t'] = translation
            self.seek(pos)

if __name__ == '__main__':
    a = MDL0BoneDefaults(open('import/lucas/FitLucas00.mdl0', 'rb'), 0, 0, '')
    a.analyze()