from model0 import *
import os
import shutil

def itb (val, n):
    return val.to_bytes(n, 'big')

def bti (b):
    return int.from_bytes(b, 'big')

outdir = "../export/"
if not os.path.exists(outdir):
    os.mkdir(outdir)

dirsf = open('../bin/groups', 'rb')
dirbytes = dirsf.read()
dirs = [bti(dirbytes[x:x+4]) for x in range(0, len(dirbytes), 4)]
dirs.sort()
dirsf.close()

directories = {}
for dir in dirs:
    directories[str(dir)] = []

filesf = open('../bin/dat_files', 'rb')
filesbytes = filesf.read()
fileswords = [bti(filesbytes[x:x+4]) for x in range(0, len(filesbytes), 4)]
filesstart = 0x8067f668
filesf.close()

for x in range(0, len(fileswords), 12):
    offset_en = fileswords[x+2]
    len_en = fileswords[x+3]
    offset_sp = fileswords[x+6]
    len_sp = fileswords[x+7]
    offset_fr = fileswords[x+10]
    len_fr = fileswords[x+11]
    absolute = filesstart + x * 4
    dir_ind = 0
    while dir_ind < len(dirs) - 1 and dirs[dir_ind + 1] <= absolute:
        dir_ind += 1
    dir = dirs[dir_ind]
    directories[str(dir)].append({'en':[offset_en, len_en], 'sp':[offset_sp, len_sp], 'fr':[offset_fr, len_fr]})

# dirs = [0]
# directories = {'0': [
#     {'en': [0x04B23B20, 0x23c0],
#     'sp': [0x04B23B20, 0x23c0],
#     'fr': [0x04B23B20, 0x23c0]}
# ]}

class Dat(File):
    def __init__(self, f):
        super().__init__(f)

dat = Dat(open('../bin/dt_na.dat', 'rb'))

for i, dir in enumerate(dirs):
    # if i < 16:
    #     continue
    dir_dir = outdir + str(i) + '/'
    if not os.path.exists(dir_dir):
        os.mkdir(dir_dir)
    files = directories[str(dir)]
    for file in files:
        languages = ['en']
        if file['en'][0] != file['sp'][0]:
            languages = ['en', 'sp', 'fr']
        try:
            for lan in languages:
                offset = file[lan][0]
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
    print ("Analyzed group " + str(dir))