import collada
from collada import *
from helper import *
import numpy as np
from helper_classes import *
from import_chr0 import *
from mdl0 import *

DAE_FILENAME = 'import/lucas/lucas.dae'
# DAE_FILENAME = 'import/lucas/FitLucas00.dae'
DAE_FILEPATH = '/'.join(DAE_FILENAME.split('/')[:-1])

class DAEImport():
    def __init__(self, dae_filename):
        self.dae_filename = dae_filename
        self.mesh = Collada(dae_filename)
        self.textures = []
        self.parse_materials()
        self.parse_controllers()
        defaults = MDL0BoneDefaults(open('import/lucas/FitLucas00.mdl0', 'rb'), 0, 0, '')
        defaults.analyze()
        for bone in self.bones.values():
            if bone.name in defaults.defaults:
                bone.s = defaults.defaults[bone.name]['s']
                bone.r = euler_to_quaternion(*[x*math.pi/180 for x in defaults.defaults[bone.name]['r']])
                bone.t = [x * MODEL_SCALE for x in defaults.defaults[bone.name]['t']]
            # else:
            #     bone.s = [1, 1, 1]
            #     bone.r = [1, 0, 0, 0]
            #     bone.t = [0, 0, 0]
        # print(bone_track_map)
        cnts = [0x2c, 0x1c, 0x11, 0xc, 0x4, 0x9, 0x18, 0x2, 0x5]
        for i, cnt in enumerate(cnts):
            chr0 = CHR0Import([CHR0_FILENAME] * cnt, self.bones)
            chr0.toFile('anm_' + str(i + 5))
        self.log_bone_srt()
        self.parse_geometries()

    def parse_geometries(self):
        geometries = self.mesh.geometries
        offsets = {
            'position': 0,
            'normal': 0,
            'texture_coord': 0
        }
        positions = []
        normals = []
        texture_coords = []
        texture_groups = []
        textures = []
        for geometry in geometries:
            primitives = geometry.primitives
            for primitive in primitives:
                offsets['position'] = len(positions)
                offsets['normal'] = len(normals)
                offsets['texture_coord'] = len(texture_coords)
                if isinstance(primitive, collada.triangleset.TriangleSet):
                    triangles = []
                    primitive_positions = [Position(a[0] * MODEL_SCALE, a[1] * MODEL_SCALE, a[2] * MODEL_SCALE) for a in primitive.vertex]
                    # for position in primitive_positions:
                    #     print(position.raw())
                    primitive_normals = [Normal(a[0], a[1], a[2]) for a in primitive.normal]
                    # I believe there's one texture coord per surface in the material?
                    # Have only run into materials with one surface
                    primitive_texture_coords = [TextureCoord(a[0], -a[1]) for a in primitive.texcoordset[0]]
                    positions.extend(primitive_positions)
                    normals.extend(primitive_normals)
                    texture_coords.extend(primitive_texture_coords)
                    for n in range(primitive.ntriangles):
                        triangle = Triangle(
                            [x + offsets['position'] for x in primitive.vertex_index[n]],
                            [x + offsets['normal'] for x in primitive.normal_index[n]],
                            [x + offsets['texture_coord'] for x in primitive.texcoord_indexset[0][n]]
                        )
                        triangles.append(triangle)
                    texture_path = self.material_surface_map[primitive.material][0]
                    if texture_path not in textures:
                        textures.append(texture_path)
                    texture_id = textures.index(texture_path)
                    texture_groups.append(TextureGroup(triangles, texture_id))
                    # Loop through bone influences to see if the original vertex position is defined here, store the default position value if it is
                    # The controller only seems to store the geometry name and vertex index, so don't know how that'd work for geometries with multiple primitives
                    # Don't have to worry about that now though, these geometries have one primitive each
                    for bone in self.bones.values():
                        for influence in bone.influences:
                            if influence.geo_name == geometry.name:
                                influence.default = [0, 0, 0, 1, 0, 0]
                                influence.absolute_vertex_ind = influence.vertex_ind + offsets['position']
                                for triangle in triangles:
                                    for i, positionInd in enumerate(triangle.positionInds):
                                        if positionInd == influence.absolute_vertex_ind:
                                            influence.default = positions[positionInd].raw() + normals[triangle.normalInds[i]].raw()
                else:
                    print('not triangleset')
        model = ModelImport(positions, normals, texture_coords, texture_groups, textures, self.bones)
        with open(DAE_FILEPATH + '/out', 'wb') as f:
            f.write(model.binary())

    def parse_materials(self):
        materials = self.mesh.materials
        self.material_surface_map = {}
        if not os.path.exists('tex'):
            os.mkdir('tex')
        for material in materials:
            self.material_surface_map[material.id] = []
            effect = material.effect
            surfaces = []
            for elem in effect.params:
                if isinstance(elem, collada.material.Surface):
                    surfaces.append(elem)
            for surface in surfaces:
                png_path = DAE_FILEPATH + '/' + surface.image.path
                tpl_path = png_path.replace('.png', '.tpl')
                png_to_tpl(png_path, tpl_path)
                self.material_surface_map[material.id].append(tpl_path)

    # This probably ought to be part of the parse_geometries method but meh
    def parse_controllers(self):
        self.bones = {}
        controllers = self.mesh.controllers
        for controller in controllers:
            if not isinstance(controller, collada.controller.Skin):
                print('Controller is not a skin')
            else:
                # sum(controller.vcounts) * len(controller.offsets) = len(controller.vertex_weight_index) = len(weight_source) * 2
                # bind_shape_matrix is identity matrix from what I see
                sources = controller.sourcebyid
                joint_source = sources[controller.joint_source]
                joint_matrix_source = sources[controller.joint_matrix_source]
                for i, bone_name in enumerate(joint_source.data):
                    name = bone_name[0]
                    if name not in self.bones:
                        # the default transform (third argument) has a non-1 scale in the daes brawlbox gave me
                        self.bones[name] = Bone(i, name, joint_matrix_source.data[i])
                    # else:
                    #     print('id ' + str(i))
                weight_source = sources[controller.weight_source]
                geometry = controller.geometry
                vertex_weight_index = controller.vertex_weight_index
                joint_offset, weight_offset = controller.offsets
                vertex_weight_index_offset = 0
                for vertex_ind, vcount in enumerate(controller.vcounts):
                    for _ in range(vcount):
                        joint_ind = vertex_weight_index[vertex_weight_index_offset + joint_offset]
                        weight_ind = vertex_weight_index[vertex_weight_index_offset + weight_offset]
                        joint_name = joint_source.data[joint_ind][0]
                        weight = weight_source.data[weight_ind][0]
                        self.bones[joint_name].add_influence(geometry.name, vertex_ind, weight)
                        vertex_weight_index_offset += 2
        # This whole mess for parsing the bone hierarchy is not good, couldn't find a clean way to do it with pycollada
        # Wouldn't be surprised if there is one and I just don't understand colladas or the library enough
        # Dunno or care if this works with colladas in general
        scene = self.mesh.scenes[0]
        scene_nodes = scene.nodes
        armature = None
        for node in scene_nodes:
            if node.id == 'Armature':
                armature = node
        if armature:
            stack = []
            for child in armature.children:
                # For some reason I had pycollada 0.4.1 installed so this was throwing errors, fun
                if isinstance(child, collada.scene.Node) and child.name in self.bones:
                    stack.append(child)
            while len(stack):
                parent = stack.pop()
                for child in parent.children:
                    if isinstance(child, collada.scene.Node) and child.name in self.bones:
                        self.bones[parent.name].children.append(child.name)
                        self.bones[child.name].parent = parent.name
                        stack.append(child)
        # Assign ids, switch from using names to ids as identifiers
        next_id = 0
        for i, bone in enumerate(self.bones.values()):
            bone.id = next_id
            next_id += 1

        # vals = list(self.bones.values())
        # for bone in vals:
        #     if bone.name == 'RHandN':
        #         new_child = Bone(2, 'Bat', np.identity(4))
        #         new_child.parent = bone.name
        #         new_child.children = bone.children
        #         bone.children = [new_child.name]
        #         for child in new_child.children:
        #             self.bones[child].parent = new_child.name
        #         for bone_ in self.bones.values():
        #             if bone_.id == 2:
        #                 bone_.id = next_id
        #                 next_id += 1
        #         self.bones[new_child.name] = new_child
        #         new_child.t = [0.25, 0, -0.033]
        #         new_child.t = [999, 999, 999]
        #         new_child.r = [0.707, 0, 0, 0.707]

        # for bone_ in self.bones.values():
        #     if bone_.id == 2:
        #         bone_.id = next_id
        #         next_id += 1

        parentless_count = 0
        for bone in self.bones.values():
            if bone.parent:
                bone.parent = self.bones[bone.parent].id
            else:
                parentless_count += 1
            for i in range(len(bone.children)):
                bone.children[i] = self.bones[bone.children[i]].id
        # Not supporting multiple base bones (the first base bone won't list any siblings in the tree)
        # documenting that here instead of fixing the tree code in the ACTBoneLayout 
        if parentless_count != 1:
            print(str(parentless_count) + ' parentless bones found')
        bones_by_id = {}
        for bone in self.bones.values():
            bones_by_id[bone.id] = bone
        self.bones = bones_by_id
        # The max size of a skacc list's destinations is 4092 bytes, so each bone can only have at max 340 vertex influences
        # bypass this by making a new child to inherit the overflow influences
        next_id = max(list(self.bones.keys())) + 1
        ids_to_iterate = list(self.bones.keys())
        for bone_id in ids_to_iterate:
            bone = self.bones[bone_id]
            max_influence_count = 340
            while len(bone.influences) > max_influence_count:
                new_child = Bone(next_id, bone.name + '_', np.identity(4))
                next_id += 1
                new_child.children = bone.children
                for child in new_child.children:
                    self.bones[child].parent = new_child.id
                bone.children = [new_child.id]
                new_child.parent = bone.id
                new_child.influences = bone.influences[max_influence_count:]
                bone.influences = bone.influences[:max_influence_count]
                self.bones[new_child.id] = new_child
                bone = new_child
        # print(len(self.bones))
        # for i in range(0x40):
        #     new_bone = Bone(next_id, 'a', np.identity(4))
        #     next_id += 1
        #     self.bones[0].children.append(new_bone.id)
        #     new_bone.parent = 0
        #     new_bone.children = []
        #     self.bones[new_bone.id] = new_bone

    def log_bone_srt(self):
        for bone in self.bones.values():
            # print(bone.name)
            # print(bone.s)
            f = open('import/bone_txt/' + bone.name, 'a')
            f.write('\n')
            f.write('s: ' + ','.join([str(round(x, 3)) for x in bone.s]) + '\n')
            f.write('r: ' + ','.join([str(round(x, 3)) for x in bone.r]) + '\n')
            f.write('t: ' + ','.join([str(round(x, 3)) for x in bone.t]) + '\n')
            # f.write('\n')
            # f.write('\n'.join([', '.join([str(round(y, 3)) for y in x]) for x in bone.orientation]))
            f.close()

my_import = DAEImport(DAE_FILENAME)