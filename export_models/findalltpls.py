from tpl import *
import os

files = os.listdir('out/all')

for fname in files:
    infile = 'out/all/'+fname
    outdir = 'out/tpl/'+fname+'/'
    wimdir = 'out/png/'+fname+'/'
    f = Model0(open(infile, 'rb'))
    try:
        f.analyze(outdir)
    except:
        continue
    if os.path.exists(outdir):
        if not os.path.exists(wimdir):
            os.mkdir(wimdir)
        os.system('wimgt decode -q -d ' + wimdir + ' ' + outdir + '*')