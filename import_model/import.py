from helper import *
from helper_classes import *
import re
import math
import numpy
import os

class OBJImport():
    def __init__(self, dir):
        positions = []
        normals = []
        textureCoords = []
        global textureID
        global triangles
        global textureGroups
        global textures
        global mtlMap
        textureGroups = []
        triangles = []
        textureID = 0
        textures = []
        mtlMap = {}
        textureMap = {}

        def flushTriangles(mtl):
            global textureID
            global triangles
            global textureGroups
            global textures
            global mtlMap
            if len(triangles) == 0:
                return
            group = TextureGroup(triangles, textures.index(mtlMap[mtl]))
            textureGroups.append(group)
            textureID += 1
            triangles = []

        with open(dir + '/stadium.mtl', 'r', errors='ignore') as f:
            lines = f.readlines()
            mtlName = ''
            path = ''
            for line in lines:
                line = line.replace('\n', '')
                if line.split(' ')[0] == 'newmtl':
                    mtlName = line.split(' ')[1]
                elif line.split(' ')[0] == 'map_Kd':
                    path = dir + line[line.find(' ') + 1:]
                    if path not in textures:
                        textures.append(path)
                        textureMap[path] = mtlName
                        if not os.path.exists(dir + '/tpl/'):
                            os.mkdir(dir + '/tpl/')
                        os.system('wimgt encode --transform="TPL.CMPR" -d ' + dir + '/tpl/' + mtlName + ' "' + path + '"')
                    mtlMap[mtlName] = path

        mtl = ''
        with open(dir + '/stadium.obj', 'r', errors='ignore') as f:
            lines = f.readlines()
            for line in lines:
                line = line.replace('\n', '')
                type = line.split(' ')[0]
                if type == 'v':
                    coords = [float(x) for x in line.split(' ')[1:]]
                    positions.append(Position(coords[0], coords[1], coords[2]))
                elif type == 'vt':
                    coords = [float(x) for x in line.split(' ')[1:]]
                    textureCoords.append(TextureCoord(coords[0], -coords[1]))
                elif type == 'vn':
                    coords = [float(x) for x in line.split(' ')[1:]]
                    normals.append(Normal(coords[0], coords[1], coords[2]))
                elif type == 'usemtl':
                    flushTriangles(mtl)
                    mtl = line.split(' ')[1]
                elif type == 'o':
                    flushTriangles(mtl)
                elif type == 'f':
                    coords = [int(x) - 1 for x in re.findall(r'[0-9]+', line)]
                    if len(coords) == 12:
                        triangles.append(Triangle(
                            [coords[0], coords[3], coords[6]],
                            [coords[2], coords[5], coords[8]],
                            [coords[1], coords[4], coords[7]]))
                        triangles.append(Triangle(
                            [coords[0], coords[6], coords[9]],
                            [coords[2], coords[8], coords[11]],
                            [coords[1], coords[7], coords[10]]))
                    else:
                        triangles.append(Triangle(
                            [coords[0], coords[3], coords[6]],
                            [coords[2], coords[5], coords[8]],
                            [coords[1], coords[4], coords[7]]))
        flushTriangles(mtl)
        textures = [dir + '/tpl/' + textureMap[x] for x in textures]
        model = ModelImport(positions, normals, textureCoords, textureGroups, textures)
        with open(dir + '/out', 'wb') as f:
            f.write(model.binary())

OBJImport('wii_sports/')