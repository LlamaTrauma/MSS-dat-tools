from model0 import *
import os
import shutil

def itb (val, n):
    return val.to_bytes(n, 'big')

def bti (b):
    return int.from_bytes(b, 'big')

outdir = "daes_model_only/"
if not os.path.exists(outdir):
    os.mkdir(outdir)

# An array of FILE_POINTER[]'s in the US dol
DIRS_START = 0x69C828
DIRS_END = 0x69CAD8
DIRS_LEN = (DIRS_END - DIRS_START) // 0x4
DIR_PTR_PTRS = range(DIRS_START, DIRS_END, 4)
DAT_FNAME_PTR = 0x8067f658

dol = open('bin/main.dol', 'rb')
DIR_PTRS = []
for addr in DIR_PTR_PTRS:
    dol.seek(addr, 0)
    DIR_PTRS.append(bti(dol.read(4)) - 0x80003f00)

dirs = {}

# for x in DIR_PTRS:
#     print(hex(x))

for dir_ind in range(DIRS_LEN):
    dirs[dir_ind] = []
    file_ptr = DIR_PTRS[dir_ind]
    while file_ptr not in DIR_PTRS[:dir_ind] + DIR_PTRS[dir_ind + 1:]:
        # print(hex(file_ptr))
        dol.seek(file_ptr, 0)
        file_data = [bti(dol.read(4)) for _ in range(12)]
        if file_data[0] != DAT_FNAME_PTR:
            break
        offset_en = file_data[2]
        len_en = file_data[1]
        offset_sp = file_data[6]
        len_sp = file_data[5]
        offset_fr = file_data[10]
        len_fr = file_data[9]
        dirs[dir_ind].append({'en':[offset_en, len_en], 'sp':[offset_sp, len_sp], 'fr':[offset_fr, len_fr]})
        file_ptr += 12 * 4

# dirs = {2:dirs[2]}
# mario
# dirs = {0: [{'en': [0x4AA6C20, 0x69E60], 'sp': [0x4AA6C20, 0x69E60], 'fr': [0x4AA6C20, 0x69E60]}]}
# dirs = {18: dirs[18][:1]}
# dirs = {18: dirs[18][3:5]}
# dirs = {19: dirs[19][3:5]}
# mario stadium
# dirs = {7: dirs[7]}
# baby dk
# dirs = {83: dirs[83]}
# hammer bro
# dirs = {45: dirs[45]}
# funky
# dirs = {74: dirs[74]}
# dirs = {132: dirs[132]}

# for dir in list(dirs.keys()):
#     if dir < 18:
#         del dirs[dir]
#     else:
#         dirs[dir] = dirs[dir][3:5]

class Dat(File):
    def __init__(self, f):
        super().__init__(f)

dat = Dat(open('bin/dt_na.dat', 'rb'))

for dir_ind, file_arr in dirs.items():
    dir_dir = outdir + str(dir_ind) + '/'
    if not os.path.exists(dir_dir):
        os.mkdir(dir_dir)
    for file in file_arr:
        languages = ['en']
        # if file['en'][0] != file['sp'][0]:
        #     languages = ['en', 'sp', 'fr']
        try:
            for lan in languages:
                offset = file[lan][0]
                # print(hex(offset))
                l = file[lan][1]
                lan_dir = dir_dir
                if len(languages) > 1:
                    lan_dir += lan + '/'
                    if not os.path.exists(lan_dir):
                        os.mkdir(lan_dir)
                child = dat.add_child(offset, l, MaybeArchive)
                child.analyze()
                if child.child:
                    child.child.analyze()
                    child.child.toFile(lan_dir)
                del child
        except Exception as e:
            print ("failed in export")
            print (e)
            pass
    if len(os.listdir(dir_dir)) == 0:
        os.rmdir(dir_dir)
    print ("Analyzed dir " + str(dir_ind))