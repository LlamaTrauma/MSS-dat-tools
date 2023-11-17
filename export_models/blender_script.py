dat_tools_dir = '[...]/MSS_dat_tools/'
import shutil

import sys
sys.path.append(dat_tools_dir + 'export_models')
from model0 import *

bin_dir = dat_tools_dir + 'bin/'

model = Model0(open(bin_dir + 'mario.wc3', 'rb'), 0, 0, '')
# model = Model0(open('import/lucas/out', 'rb'), 0, 0, '')
model.analyze()
model.blender_import()