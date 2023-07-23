from model0 import *
import os
import shutil

# infile = 'all/1_0x1_0_test_actor.gpl'
# fpath = 'all/32_0x20_0_teresa.gpl'
# infile = 'all/32_0x20_2_bat.gpl'
# infile = 'all/18_0x12_0_mario.gpl'
# infile = 'all/9_0x9_0_sta06.gpl'
# fpath = 'all/128_0x80_7_manhole_wario.gpl'
# files = os.listdir("all")
files = ['all/18_0x12_0_mario.gpl']
# files = ['all/18_0x12_2_bat.gpl']
# files = ['struct/import/wii_sports/out']
# files = ['struct/import/bat/out']
files = ['../import_model/wii_sports/out']
# files = ['10_0xa_0_sta03.gpl', '10_0xa_3_sta03b.gpl', '10_0xa_6_sta03c.gpl']
# files = ['all/129_0x81_0_donkeymap.gpl']
# files = ['all/20_0x14_0_donkey_kong.gpl']

for infile in files:
    fname = infile.split('/')[-1]
    outdir = '../export/' + fname + '/'

    if not os.path.exists('../export'):
        os.mkdir('../export')

    if not os.path.exists(outdir):
        os.mkdir(outdir)

    f = open(infile, 'rb')
    # try:
    model = Model0(f, 0, 0, 'test')
    model.analyze()
    # except:
    #     continue
    model.print()
    model.toFile(outdir)