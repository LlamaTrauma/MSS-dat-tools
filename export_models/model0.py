from tpl import *
from gpl import *
from act import *
from anm import *
from blender_helpers import *
import bpy
import numpy as np

# Isolate any potential messiness in the file reading
# This will conglomerate all the data from the file into a neat, sensible data structure
# We want to know
    # A list of vertex positions
    # A list of vertex normals
    # A list of texture filepaths
    # A list of meshes, each with:
        # A map of texture layer to texture path index
        # A list of triangles, each with
            # Three vertices, each with
                # A vertex position index
                # A vertex normal index
                # A map of texture layer to texture coordinate
    # A list of bones, each with
        # An id
        # A map of vertex position index to influence (0-255)
        # A parent id
        # A relative flag
        # A position (the bone's absolute transform)
class ModelData():
    def __init__(self, positions, normals, textures, meshes, bones):
        self.positions = positions
        self.normals = normals
        self.textures = textures
        self.meshes = meshes
        self.bones = bones

class BlenderImport(ModelData):
        def __init__(self, positions, normals, textures, meshes, bones):
            super().__init__(positions, normals, textures, meshes, bones)

        def do_import(self):
            self.make_materials()
            self.make_armature()
            bpy.ops.object.mode_set(mode='POSE')
            # self.orient_bones()
            bpy.ops.object.mode_set(mode='OBJECT')
            self.make_meshes()
            for obj in self.blender_meshes:
                obj.select_set(True)
            self.blender_armature.select_set(True)
            bpy.ops.object.parent_set(type='ARMATURE_NAME')
            bpy.context.view_layer.objects.active = self.blender_armature
            # self.animate('../mario_files/mario_animations_1', 1)

        def make_materials(self):
            self.blender_materials = {}
            for ind, path in enumerate(self.textures):
                mat_name = 'mat_' + str(ind)
                material = materialFromTexture(path, mat_name)
                self.blender_materials[ind] = material

        def make_armature(self):
            # Make/select an armature object
            armature = bpy.data.armatures.new('armature')
            armature_obj = bpy.data.objects.new('armature_obj', armature)
            self.blender_armature = armature_obj
            bpy.context.scene.collection.objects.link(armature_obj)   
            bpy.context.active_object.select_set(False)
            armature_obj.select_set(True)
            bpy.context.view_layer.objects.active = armature_obj
            # Need to set to edit mode here, ugly side effect
            bpy.ops.object.mode_set(mode='EDIT')

            # first pass - make/store a bone object for each bone
            self.blender_bones = {}
            for bone in self.bones:
                bone_name = 'bone_'+str(bone.id)
                blender_bone = armature_obj.data.edit_bones.new(bone_name)
                # testing
                bone.position = (0, 0, 0)
                blender_bone.head = bone.position
                blender_bone.tail = (bone.position[0], bone.position[1], bone.position[2] - 0.1)
                # ugh
                # you have to set the head/tail afaik to make an edit bone
                # but that messes up the default orientation of the bone so the transform isn't the identity matrix
                # and this gets saved as the rest position and setting the transform of the pose bone is relative to whatever this ends up as
                # why
                # this took a while to find
                # blender_bone.matrix = np.identity(4)
                blender_bone.matrix = np.linalg.inv(bone.orientation.transform)
                self.blender_bones[bone.id] = blender_bone

            # second pass - set parents/relative positioning
            for bone in self.bones:
                blender_bone = self.blender_bones[bone.id]
                if bone.parent >= 0:
                    blender_bone.parent = self.blender_bones[bone.parent]
                    blender_bone.use_relative_parent = bone.relative

        def make_meshes(self):
            self.blender_meshes = []
            for ind, mesh in enumerate(self.meshes):
                # Make a mesh object
                mesh_name = 'mesh_' + str(ind)
                blender_mesh = bpy.data.meshes.new(mesh_name)
                triangles = mesh.triangles
                # Set the vertex positions
                vert_inds = []
                mesh_verts = []
                mesh_vert_inds = []
                for i, triangle in enumerate(triangles):
                    vert_inds.append(triangle[0].position)
                    vert_inds.append(triangle[1].position)
                    vert_inds.append(triangle[2].position)
                    mesh_vert_inds.append([i * 3, i * 3 + 1, i * 3 + 2])
                # print(i)
                # print(len(self.positions))
                mesh_verts = [self.positions[i] for i in vert_inds]
                blender_mesh.from_pydata(mesh_verts, [], mesh_vert_inds)
                # Set the lighting data
                # mesh_normals = [[self.normals[x.lighting] for x in triangle] for triangle in triangles]
                # blender_mesh.use_auto_smooth = True
                # blender_mesh.normals_split_custom_set_from_vertices(sum(mesh_normals, []))
                # Apply the layer 0 texture
                tex_layer = 0
                if tex_layer in mesh.texture_layers:
                    blender_mesh.materials.append(self.blender_materials[mesh.texture_layers[tex_layer]])
                    blender_mesh.uv_layers.new(name = 'uv_' + str(tex_layer))
                    for loop in range(len(blender_mesh.uv_layers.active.data)):
                        coord = triangles[loop // 3][loop % 3].tex_coords[tex_layer]
                        blender_mesh.uv_layers.active.data[loop].uv = (coord[0], -coord[1])
                # Make the object
                obj = bpy.data.objects.new('obj_' + mesh_name, blender_mesh)
                self.blender_meshes.append(obj)
                # Set bone influences
                for bone in self.bones:
                    vgroup = obj.vertex_groups.new(name='bone_' + str(bone.id))
                    for ind, vert in enumerate(vert_inds):
                        if vert in bone.influences:
                            vgroup.add([ind], bone.influences[vert], 'ADD')
                bpy.context.scene.collection.objects.link(obj)

        # Once in object mode again, apply initial orientation
        def orient_bones(self):
            for bone in self.bones:
                blender_bone = self.blender_armature.pose.bones['bone_' + str(bone.id)]
                # blender_bone.location = bone.orientation.translation
                # blender_bone.scale = bone.orientation.scale
                # print(bone.orientation.quaternion)
                # blender_bone.rotation_quaternion = (bone.orientation.quaternion[0], bone.orientation.quaternion[1], bone.orientation.quaternion[2], bone.orientation.quaternion[3])
                # blender_bone.matrix_basis = np.identity(4)
                # blender_bone.scale = bone.orientation.scale
                # blender_bone.rotation_quaternion = bone.orientation.quaternion
                # blender_bone.location = bone.orientation.translation
                blender_bone.matrix_basis = bone.orientation.transform
                # blender_bone.matrix_basis = np.linalg.inv(bone.orientation.transform)

        def animate(self, filepath, sequence):
            # print(quaternion_rotation_matrix([0.7, 0.2, 0.4, 0.5]))
            # scale, quaternion, translate = mtosrt(quaternion_rotation_matrix([0.7, 0.2, 0.4, 0.5]))
            # print(quaternion)
            anm = ANM(open(
                filepath,
                'rb'), 0, 0, '')
            anm.analyze()
            data = ANMData(anm)
            sequence = data.sequences[sequence]
            for track in sequence.tracks:
                bpy.context.scene.frame_end = track.time
                found_bone = None
                for b in self.bones:
                    if track.id == b.track_id:
                        found_bone = b
                        # print ('animating bone ' + str(b.id) + ' with track ' + str(track.id))
                        continue
                if found_bone is None:
                    continue
                bone = self.blender_armature.pose.bones['bone_' + str(found_bone.id)]
                for keyframe in track.keyframes:
                    transform = found_bone.orientation.transform
                    transform = np.identity(4)
                    # continue
                    # if 3 not in keyframe.settings or 0 not in keyframe.settings or len(keyframe.settings.keys()) != 2:
                    #     continue
                    scale = found_bone.orientation.scale
                    quat = found_bone.orientation.quaternion
                    loc = found_bone.orientation.translation
                    if 3 in keyframe.settings:
                        # print('----------')
                        # print(found_bone.id)
                        # print(["{:.2f}".format(x) for x in original_quat])
                        # print(["{:.2f}".format(x) for x in keyframe.settings[3]])
                        # transform = np.matmul(transform, quaternion_rotation_matrix(keyframe.settings[3]))
                        quat = keyframe.settings[3]
                        bone.rotation_quaternion = quat
                        # bone.matrix_basis = np.matmul(quaternion_rotation_matrix(keyframe.settings[3]), np.linalg.inv(quaternion_rotation_matrix(quat)))
                        # bone.matrix_basis = quaternion_rotation_matrix(keyframe.settings[3])
                        # bone.matrix_basis = quaternion_rotation_matrix(quat)
                        # bone.rotation_quaternion = [quat[1], quat[2], quat[3], quat[0]]
                        bone.keyframe_insert(data_path='rotation_quaternion', frame=keyframe.time)
                        pass
                    if 0 in keyframe.settings:
                        # print('----------')
                        # print(found_bone.id)
                        # print(["{:.2f}".format(x) for x in original_loc])
                        # print(["{:.2f}".format(x) for x in keyframe.settings[0]])
                        # transform = np.matmul(transform, translation_matrix(keyframe.settings[0]))
                        # bone.location = [keyframe.settings[0][i] - original_loc[i] for i in range(3)]
                        # loc = keyframe.settings[0]
                        # bone.location = loc
                        # print(bone.matrix_basis)
                        # bone.keyframe_insert(data_path='location', frame=keyframe.time)
                        pass
                    # transform = np.matmul(translation_matrix(loc), quaternion_rotation_matrix(quat))
                    # transform = np.matmul(quaternion_rotation_matrix(quat), translation_matrix(loc))
                    bone.matrix_basis = found_bone.orientation.transform

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

# This is not the mdl0 format afaik, I think I just called the class that for some reason
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
        self.SKN = self.add_child(self.ptr5, nextSection[self.ptr5] - self.ptr5, SKN, "Skin")
        self.SKN.analyze()
        self.name = str(self.absolute)
        self.bones = {}
        if self.ACT:
            self.name += '_' + self.ACT.geoName
            if self.SKN:
                self.generateBones()
        elif self.GPL:
            self.name += '_' + self.GPL.geoDescriptors[0].layout.DOTextureDataHeaders[0].paletteName

    def generateBones(self):
        self.bones = self.ACT.bones()

        # At this point we have the list of bones, time to get the influences for each
        self.bone_influences = self.boneInfluences()
        vertex_weight_totals = {}
        for influence in self.bone_influences:
            self.bones[influence.boneID].addInfluence(influence)
        for bone in self.bones.values():
            for vertex_id in bone.vertexInfluences:
                key = str(bone.GEOID) + '_' + str(vertex_id)
                if key not in vertex_weight_totals:
                    vertex_weight_totals[key] = 0
                vertex_weight_totals[key] += bone.vertexInfluences[vertex_id][0]
        for bone in self.bones.values():
            for vertex_id in bone.vertexInfluences:
                key = str(bone.GEOID) + '_' + str(vertex_id)
                bone.vertexInfluences[vertex_id][0] /= vertex_weight_totals[key]

    def boneInfluences(self):
        boneInfluences = self.SKN.boneInfluences()
        for geoID in list(self.ACT.non_skinned_bones.keys()):
            if geoID > 0:
                geoBone = self.ACT.non_skinned_bones[geoID]
            boneInfluences += [BoneInfluence(geoBone, 256, i, (100, 100, 100)) for i in range(self.GPL.geoDescriptors[geoID].layout.DOPositionHeader.numPositions)]
        return boneInfluences

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
            print (e)
            pass

    def model_data(self):
        all_coords = []
        all_normals = []
        all_meshes = []
        all_bones = []
        texture_paths = []

        # textures are simple enough
        if not os.path.exists('tex'):
            os.mkdir('tex')
        for tex_ind, tex in enumerate(self.TEXPalette.descriptors):
            tex_path = 'tex/'+str(tex_ind)
            tex.toFile(tex_path)
            texture_paths.append(os.getcwd() + '/' + tex_path + '.png')

        descriptor_offsets = []
        # vertex data/triangles are a little more complicated because of the multiple geodescriptors
        for descriptor_ind, descriptor in enumerate(self.GPL.geoDescriptors):
            coord_offset = len(all_coords)
            # We'll need to know this for the bones, so might as well store it while already looping through the descriptors
            descriptor_offsets.append(coord_offset)
            normal_offset = len(all_normals)
            layout = descriptor.layout
            coords = np.array(layout.DOPositionHeader.data)
            normals = np.array(layout.DOLightingHeader.data)
            tex_coords = np.array([np.array(tex_layer.data) for tex_layer in layout.DOTextureDataHeaders])

            # for descriptor_inds past 0 (the skinned descriptor), transform the coordinates/vertices by the descriptor's bone's default transform
            # transform = self.ACT.geoTransformation(descriptor_ind)
            # coords = [np.matmul([*coord[:3], 1], transform)[:3] for coord in coords]
            # transform = np.linalg.inv(transform)
            # transform = transform.transpose()
            # normals = [np.matmul([*normal[:3], 1], transform)[:3] for normal in normals]
            coords = [coord[:3] for coord in coords]
            normals = [normal[:3] for normal in normals]

            # if descriptor_ind != 0:
            #     transform = self.bones[self.ACT.non_skinned_bones[descriptor_ind]].absolute_transform()
            #     coords = [np.matmul([*coord, 1], transform)[:3] for coord in coords]

            if descriptor_ind == 0:
                for bone in self.bones.values():
                    if bone.GEOID != 0:
                        continue
                    influences = bone.vertexInfluences
                    for vertex_ind in influences.keys():
                        coords[vertex_ind] = influences[vertex_ind][1]

            # attempt to use the inverse of the bone's transform to get initial positions
            # if descriptor_ind == 0:
            #     vertex_influences = {}
            #     for bone in self.bones.values():
            #         if bone.GEOID != 0:
            #             continue
            #         influences = bone.vertexInfluences
            #         for vertex_ind in influences.keys():
            #             if vertex_ind not in vertex_influences:
            #                 vertex_influences[vertex_ind] = [[], []]
            #             vertex_influences[vertex_ind][0].append(self.bones[bone.id].absolute_transform())
            #             vertex_influences[vertex_ind][1].append(influences[vertex_ind][0])
            #     for vertex_ind in range(len(coords)):
            #         if vertex_ind not in vertex_influences:
            #             continue
            #         transforms = vertex_influences[vertex_ind][0]
            #         weights = vertex_influences[vertex_ind][1]
            #         original = coords[vertex_ind]
            #         coords[vertex_ind] = original_pos_method_2(transforms, weights, coords[vertex_ind])
                    # new = coords[vertex_ind]
                    # back_to_original = [0, 0, 0]
                    # for i in range(len(transforms) - 1, 0, -1):
                    #     transformed = np.matmul([*new, 1], transforms[i])
                    #     back_to_original = [back_to_original[x] + transformed[x] * weights[i] for x in range(3)]
                    # # print(["{:.5f}".format(x) for x in original])
                    # # print(["{:.5f}".format(x) for x in back_to_original])
                    # diff = [back_to_original[i] - original[i] for i in range(3)]
                    # # if sum([abs(x) > 0.0001 for x in diff]) > 0:
                    #     # print("there's a diff")
                    #     # print(["{:.5f}".format(x) for x in diff])

            meshes = layout.getTriangles()
            for mesh in meshes:
                state = mesh['state']
                triangles = mesh['triangles']
                if len(triangles) == 0:
                    continue
                active_descriptors = [descriptor['key'] for descriptor in state['descriptors']]
                
                # first, get a list of the textures used by this mesh
                # a hash that maps a texture layer (0-7) to its texture id (index in the texture_paths arr)
                active_textures = {}
                for tex_layer_ind in range(8):
                    tex_layer_name = 'texture'+str(tex_layer_ind)
                    if tex_layer_name in active_descriptors:
                        active_textures[tex_layer_ind] = state[tex_layer_name]['index']

                # then, convert the triangle list to a format we want
                # probably ought to do this in the getTriangles method but I wrote that a while ago and don't wanna
                mesh_triangles = []
                for triangle in triangles:
                    mesh_triangle = []
                    for vertex in triangle:
                        mesh_vertex = Object()
                        mesh_vertex.position = vertex['position'] + coord_offset
                        mesh_vertex.lighting = vertex['lighting'] + normal_offset
                        mesh_vertex.tex_coords = {}
                        for texture_layer in active_textures:
                            mesh_vertex.tex_coords[texture_layer] = tex_coords[texture_layer][vertex['texture' + str(texture_layer)]]
                        mesh_triangle.append(mesh_vertex)
                    mesh_triangles.append(mesh_triangle)

                mesh = Object()
                mesh.triangles = mesh_triangles
                mesh.texture_layers = active_textures
                all_coords.extend(coords)
                all_normals.extend(normals)
                all_meshes.append(mesh)
        
        all_bones = []
        # Bones are simpler
        for bone_id in self.bones:
            bone = self.bones[bone_id]
            bone_copy = Object()
            bone_copy.id = bone_id
            bone_copy.parent = -1
            if bone.parent:
                bone_copy.parent = bone.parent.id
            bone_copy.relative = bone.relative
            bone_copy.position = bone.head()
            bone_copy.absolute_transform = bone.absolute_transform()
            bone_copy.orientation = bone.orientation
            bone_copy.track_id = bone.track_id
            bone_copy.GEOID = bone.GEOID
            bone_copy.influences = {}
            for vertex_id in bone.vertexInfluences:
                key = str(bone.GEOID) + '_' + str(vertex_id)
                bone_copy.influences[vertex_id + descriptor_offsets[bone.GEOID]] = bone.vertexInfluences[vertex_id][0]
            all_bones.append(bone_copy)

        # return the tidy object
        return ModelData(all_coords, all_normals, texture_paths, all_meshes, all_bones)

    def blender_import(self):
        import_obj = self.model_data()
        blender_obj = BlenderImport(import_obj.positions, import_obj.normals, import_obj.textures, import_obj.meshes, import_obj.bones)
        blender_obj.do_import()