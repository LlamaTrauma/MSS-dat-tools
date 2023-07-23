import warnings

def assign_generic(o, s, l):
    i = o.unassigned
    containing = 0
    while 1:
        if containing == len(i):
            warnings.warn("Did not find containing block")
            return
        elif i[containing][0] <= s and s + l <= i[containing][1]:
            break
        containing += 1
    containing_arr = i[containing]
    remaining = i[:containing]
    if s > containing_arr[0]:
        remaining.append([s, containing_arr[0]])
    if s + l < containing_arr[1]:
        remaining.append([s + l, containing_arr[1]])
    if containing < len(i):
        remaining.extend(i[containing + 1:])
    o.unassigned = remaining

def add_child(o, s, l):
    o.children

class File:
    def __init__(self, fname):
        self.fname = fname
        self.f = open(fname, 'r')
        self.f.seek(0, 2)
        self.l = self.f.tell() + 1
        self.f.seek(0)
        self.absolute = 0
        self.unassigned = [[0, self.l]]
        self.children = []

    def assign(self, s, l):
        self.unassigned = assign_generic(s, l, self.unassigned)

class FileChunk:
    def __init__(self, p, s, l):
        self.parent = p
        self.offset = s
        self.absolute = self.offset + self.parent.absolute
        self.children = []
        self.l = l
        self.unassigned = [[0, self.l]]

    def assign(self, s, l):
        self.unassigned = assign_generic(s, l, self.unassigned)