from tpl import *
from gpl import *
from act import *
from anm import *
import numpy as np
from collada import *
import shutil
from collada import source, common
from xml_helper import *

class MaybeArchive(FileChunk):
    def analyze(self):
        word1 = self.word()
        self.child = None
        # print(hex(word1))
        if word1 in (0x01321AFD, 0x013240DB):
            # self.child = self.add_child(0, 0, ANM)
            return
        elif word1 > 1000:
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

# This is not the mdl0 format, I think I just called the class that for some reason
class Model0(FileChunk):
    def analyze(self):
        # Initial testing if this is a valid file
        firstWord = self.word()
        if firstWord != 0:
            raise Exception("gpl doesn't start with 0")
        self.gplPtr = self.word()
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
        # print(hex(self.absolute))
        # print(self.ptr5)
        if self.ptr5:
            self.SKN = self.add_child(self.ptr5, nextSection[self.ptr5] - self.ptr5, SKN, "Skin")
            self.SKN.analyze()
        self.name = str(self.absolute)
        self.bones = {}
        self.skinned = 0
        if self.ACT:
            self.name += '_' + self.ACT.geoName
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
        self.skinned = False
        for bone in self.bones.values():
            if bone.skinned:
                self.skinned = True
            for vertex_id in bone.vertexInfluences:
                key = str(bone.GEOID) + '_' + str(vertex_id)
                if key not in vertex_weight_totals:
                    vertex_weight_totals[key] = 0
                vertex_weight_totals[key] += bone.vertexInfluences[vertex_id][0]
        # for bone in self.bones.values():
        #     for vertex_id in bone.vertexInfluences:
        #         key = str(bone.GEOID) + '_' + str(vertex_id)
        #         bone.vertexInfluences[vertex_id][0] /= vertex_weight_totals[key]

    def boneInfluences(self):
        boneInfluences = []
        if self.SKN and self.ACT:
            boneInfluences = self.SKN.boneInfluences()
            # DIFFERENCE (well not really, bone ids are just in sequential increasing order in Sluggers so this would be redundant)
            ids_by_ind = self.ACT.ids_by_ind()
            for influence in boneInfluences:
                influence.boneID = ids_by_ind[influence.boneID]

        for geoID in list(self.ACT.non_skinned_bones.keys()):
            if geoID > 0 or len(self.bones) == self.GPL.numDescriptors:
                geoBone = self.ACT.non_skinned_bones[geoID]
            else:
                continue
            boneInfluences += [BoneInfluence(geoBone, 256, i, (100, 100, 100), 'Non-skinned assumption') for i in range(self.GPL.geoDescriptors[geoID].layout.DOPositionHeader.numPositions)]
        return boneInfluences

    def toFile(self, outdir):
        # try:
            self.name = 'model'
            file_dir = outdir + self.name
            if os.path.exists(file_dir):
                shutil.rmtree(file_dir)
            os.mkdir(file_dir)
            file_dir += '/'
            data = self.model_data()
            data.to_dae(file_dir)
        # except Exception as e:
        #     print ("Failed in model0 tofile")
        #     print (e)
        #     pass

    def model_data(self):
        all_bones = []
        texture_paths = []

        # textures are simple enough
        if self.TEXPalette:
            if os.path.exists('tex'):
                shutil.rmtree('tex')
            os.mkdir('tex')
            for tex_ind, tex in enumerate(self.TEXPalette.descriptors):
                tex_path = 'tex/'+str(tex_ind)
                tex.toFile(tex_path)
                texture_paths.append(tex_path + '.png')

        geometries = []
        vertex_deletions = {}
        # vertex data/triangles are a little more complicated because of the multiple geodescriptors
        for descriptor_ind, descriptor in enumerate(self.GPL.geoDescriptors):
            vertex_deletions[descriptor_ind] = {0: 0}
            geometry = Object()
            layout = descriptor.layout
            coords = np.array(layout.DOPositionHeader.data)
            coords = [coord[:3] for coord in coords]

            if self.skinned:
                deletion_count = 0
                vertex_ind = 0
                while vertex_ind < len(coords):
                    if coords[vertex_ind][0] != 0 or coords[vertex_ind][1] != 0 or coords[vertex_ind][2] != 0:
                        vertex_ind += 1
                        continue
                    include = 0
                    for bone in self.bones.values():
                        influences = bone.vertexInfluences
                        if vertex_ind + deletion_count in influences and bone.GEOID == descriptor_ind:
                            include = 1
                            break
                    if include:
                        vertex_ind += 1
                    else:
                        coords = np.delete(coords, vertex_ind, 0)
                        deletion_count += 1
                        vertex_deletions[descriptor_ind][vertex_ind + deletion_count] = deletion_count
            # if descriptor_ind == 0:
            #     print(vertex_deletions)
            #     print(prior_deletions(vertex_deletions[0], 120))

            normals = np.array(layout.DOLightingHeader.data)
            normals = [normal[:3] for normal in normals]
            colors = np.array(layout.DOColorHeader.data)
            tex_coords = [np.array(tex_layer.data) for tex_layer in layout.DOTextureDataHeaders]

            geometry.positions = coords
            geometry.normals = normals
            geometry.colors = colors
            geometry.tex_coords = tex_coords
            geometry.meshes = []
            meshes = layout.getTriangles()
            for mesh in meshes:
                state = mesh['state']
                triangles = mesh['triangles']
                if len(triangles) == 0:
                    continue
                active_descriptors = [descriptor['key'] for descriptor in state['descriptors']]
                if 'color1' in active_descriptors:
                    print('model uses color1')
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
                        mesh_vertex.position = vertex['position'] - prior_deletions(vertex_deletions[descriptor_ind], vertex['position'])
                        # if mesh_vertex.position < 0 or mesh_vertex.position >= len(geometry.positions):
                        #     print(mesh_vertex.position)
                        #     print(len(geometry.positions))
                        #     print('------------')
                        if 'lighting' in vertex:
                            mesh_vertex.lighting = vertex['lighting']
                        mesh_vertex.colors = {}
                        if 'color0' in active_descriptors:
                            mesh_vertex.colors[0] = vertex['color0']
                        if 'color1' in active_descriptors:
                            mesh_vertex.colors[1] = vertex['color1']
                        mesh_vertex.tex_coords = {}
                        for texture_layer in active_textures:
                            mesh_vertex.tex_coords[texture_layer] = vertex['texture' + str(texture_layer)]
                        mesh_triangle.append(mesh_vertex)
                    mesh_triangles.append(mesh_triangle)

                mesh = Object()
                mesh.triangles = mesh_triangles
                mesh.texture_layers = active_textures
                mesh.active_descriptors = active_descriptors
                geometry.meshes.append(mesh)
            geometries.append(geometry)

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
            bone_copy.pose = bone.orientation
            bone_copy.absolute_transform = bone_copy.pose.transform
            parent = bone.parent
            while parent:
                bone_copy.absolute_transform = np.matmul(bone_copy.absolute_transform, parent.orientation.transform)
                parent = parent.parent
            bone_copy.track_id = bone.track_id
            bone_copy.GEOID = bone.GEOID
            bone_copy.influences = {}
            for vertex_id in bone.vertexInfluences:
                new_vertex_ind = vertex_id - prior_deletions(vertex_deletions[bone.GEOID], vertex_id)
                bone_copy.influences[new_vertex_ind] = bone.vertexInfluences[vertex_id][0]
                # if new_vertex_ind < 0 or new_vertex_ind >= len(geometries[bone.GEOID].positions):
                #     print(new_vertex_ind)
                #     print(len(geometries[bone.GEOID].positions))
                #     print('------------')
            all_bones.append(bone_copy)
        # influence_counts = {}
        # influence_log = {}
        # for g_ind, geom in enumerate(geometries):
        #     for v_ind, pos in enumerate(geom.positions):
        #         # if pos[0] == 0 and pos[1] == 0 and pos[2] == 0:
        #         #     continue
        #         vert_id = str(g_ind) + '_' + str(v_ind)
        #         influence_counts[vert_id] = 0
        #         influence_log[vert_id] = {}
        #         for bone in all_bones:
        #             if bone.GEOID == g_ind:
        #                 if v_ind in bone.influences:
        #                     influence_counts[vert_id] += bone.influences[v_ind]
        #                     influence_log[vert_id][bone.id] = {'weight': bone.influences[v_ind], 'sources': self.bones[bone.id].vertexInfluences[v_ind][2]}
        # for id, val in influence_counts.items():
            # if val < 255 or val > 257:
            # if 31 in influence_log[id]:
            #     print(id)
            #     print(val)
            #     for bone, details in influence_log[id].items():
            #         print(str(bone) + ': ' + str(details['weight']) + ' (' + ', '.join(details['sources']) + ')')
            #     print('---------------')

        # return the tidy object
        return ModelData(geometries, texture_paths, all_bones, self)

class ModelData():
    def __init__(self, geometries, textures, bones, model):
        self.geometries = geometries
        self.textures = textures
        self.bones = bones
        self.model = model

    def create_tex_dir(self, dir):
        tex_pngs = os.listdir('tex')
        tex_dir = dir + 'tex/'
        if os.path.exists(tex_dir):
            os.rmdir(tex_dir)
        os.mkdir(tex_dir)
        for png in tex_pngs:
            shutil.copyfile('tex/'+png, tex_dir+png)

    def create_materials(self, dir, collada):
        pngs = os.listdir(dir + 'tex/')
        out = {}
        for png in pngs:
            ind = int(png.split('.')[0])
            ind_str = str(ind)
            image = material.CImage('image_'+ind_str, './tex/'+png)
            collada.images.append(image)
            surface = material.Surface('surface_'+ind_str, image)
            sampler2d = material.Sampler2D('sampler_'+ind_str, surface)
            map = material.Map(sampler2d, 'TEX')
            effect = material.Effect("effect_"+ind_str, [surface, sampler2d], "lambert",  diffuse=map, transparent=map, double_sided=True)
            mat = material.Material("material_"+ind_str, "material_"+ind_str, effect)
            out[ind] = (effect, mat)
        return out

    def to_dae(self, dir):
        # texture setup stuff
        self.create_tex_dir(dir)
        collada = Collada()
        controller_xmls = []
        instancing_details = {}
        effect_materials = self.create_materials(dir, collada)
        mat_nodes = {}
        for ind in effect_materials:
            effect, material = effect_materials[ind]
            collada.effects.append(effect)
            collada.materials.append(material)
            mat_node = scene.MaterialNode('material_'+str(ind), material, inputs=[('TEX', 'TEXCOORD', '0')])
            mat_nodes[ind] = mat_node

        # create geometries
        geom_nodes = []
        non_skinned_map = {}
        g_ind = 0
        for geom_ind, g in enumerate(self.geometries):
            for tex_layer in range(len(g.tex_coords)):
                g_positions = np.array(g.positions).flatten()
                vert_id = 'verts_arr_'+str(g_ind)
                vert_src = source.FloatSource(vert_id, g_positions, ('X', 'Y', 'Z'))
                g_normals = np.array(g.normals + [[1, 0, 0]]).flatten()
                normal_id = 'normals_arr_'+str(g_ind)
                normal_src = source.FloatSource(normal_id, g_normals, ('X', 'Y', 'Z'))
                g_colors = np.array(g.colors).flatten()
                color_id = 'colors_arr_'+str(g_ind)
                color_components = ('R', 'G', 'B')
                if len(g.colors) and len(g.colors[0]) == 4:
                    color_components = ('R', 'G', 'B', 'A')
                color_src = source.FloatSource(color_id, g_colors, color_components)
                texcoord_id = 'texcoords_arr_'+str(g_ind)
                data = np.array(g.tex_coords[tex_layer]).flatten()
                for i in range(1, len(data), 2):
                    data[i] = -data[i]
                texcoord_src = source.FloatSource(texcoord_id, data, ('S', 'T'))
                instancing_details[g_ind] = {}
                instancing_details[g_ind]['materials'] = {}
                geometry_id = 'geom_'+str(geom_ind)+'_layer_'+str(tex_layer)
                geom = geometry.Geometry(collada, geometry_id, geometry_id, [vert_src, normal_src, color_src, texcoord_src])
                instancing_details[g_ind]['geometry'] = geometry_id
                geom_mat_nodes = []
                for m_ind, mesh in enumerate(g.meshes):
                    # for l in list(mesh.texture_layers.keys()):
                    #     if l != 0:
                    #         del mesh.texture_layers[l]
                    if tex_layer not in mesh.texture_layers:
                        continue
                    active_descriptors = mesh.active_descriptors
                    material_ind = mesh.texture_layers[tex_layer]
                    effect, material = effect_materials[material_ind]
                    material_symbol = 'material_'+str(material_ind)
                    instancing_details[g_ind]['materials'][material_symbol] = 'material_'+str(material_ind)
                    geom_mat_nodes.append(mat_nodes[material_ind])

                    input_list = source.InputList()
                    input_list.addInput(0, 'VERTEX', '#'+vert_id)
                    offset = 1
                    if 'lighting' in active_descriptors:
                        input_list.addInput(offset, 'NORMAL', '#'+normal_id)
                        offset += 1
                    if 'color0' in active_descriptors:
                        input_list.addInput(offset, 'COLOR', '#'+color_id)
                        offset += 1
                    input_list.addInput(offset, 'TEXCOORD', '#'+texcoord_id, set='0')
                    offset += 1
                    indices = []
                    triangles = mesh.triangles
                    for triangle in triangles:
                        for vertex in triangle:
                            indices.append(vertex.position)
                            if 'lighting' in active_descriptors:
                                indices.append(vertex.lighting)
                            if 'color0' in active_descriptors:
                                indices.append(vertex.colors[0])
                            indices.append(vertex.tex_coords[tex_layer])
                    triset = geom.createTriangleSet(np.array(indices), input_list, material_symbol)
                    geom.primitives.append(triset)
                collada.geometries.append(geom)
                geom_nodes.append(scene.GeometryNode(geom, geom_mat_nodes))
            
                # Create the controller for this geometry
                controller_id = 'controller_'+str(geom_ind)+'_layer_'+str(tex_layer)
                # First get the bones that influence this geometry
                relevant_bones = []
                for bone in self.bones:
                    if bone.GEOID == geom_ind:
                        relevant_bones.append(bone)
                
                # Joint name source
                joint_names = np.array(['bone_' + str(b.id) for b in self.bones])
                # Joint matrix source
                joint_matrices = np.array([np.linalg.inv(b.absolute_transform) for b in self.bones])
                # joint_matrices = np.array([b.pose.transform for b in self.bones])
                # joint_matrices = np.array([np.identity(4) for b in self.bones])
                # Weight source
                joint_weights = []

                joint_weight_inds = {}
                vertex_totals = {}

                for vert_ind in range(len(g.positions)):
                    weights = []
                    total = 0
                    for bone_ind, bone in enumerate(self.bones):
                        if bone.GEOID == geom_ind and vert_ind in bone.influences:
                            w = bone.influences[vert_ind]
                            if w not in weights:
                                weights.append(w)
                            total += w
                    vertex_totals[vert_ind] = total
                    if total not in joint_weight_inds:
                        joint_weight_inds[total] = {}
                    for w in weights:
                        if w not in joint_weight_inds[total]:
                            joint_weight_inds[total][w] = len(joint_weights)
                            joint_weights.append(w/total)

                joint_weights = np.array(joint_weights)

                vcounts = []
                vertex_weight_index = []
                for vert_ind in range(len(g.positions)):
                    vcount = 0
                    for bone_ind, bone in enumerate(self.bones):
                        if bone.GEOID == geom_ind and vert_ind in bone.influences:
                            vcount += 1
                            vertex_weight_index.append(bone_ind)
                            vertex_weight_index.append(joint_weight_inds[vertex_totals[vert_ind]][bone.influences[vert_ind]])
                    data = (vertex_weight_index[-vcount*2:])
                    if vcount == 0:
                        data = []
                    total_weight = 0
                    ws = []
                    for i in range(0, len(data), 2):
                        b_ind = data[i]
                        w_ind = data[i+1]
                        # print(joint_names[b_ind] + ': ' + '{:.10f}'.format(joint_weights[w_ind]))
                        total_weight += joint_weights[w_ind]
                        ws.append(joint_weights[w_ind])
                    # if total_weight != 0 and abs(total_weight - 1) > 0.00000000000000000001:
                        # print(total_weight)
                        # print(' '.join(str(x) for x in ws))
                        # print(data)
                        # print('--------------')
                    vcounts.append(vcount)
                vcounts = np.array(vcounts)
                vertex_weight_index = np.array(vertex_weight_index)
                bind_matrix = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
                # print(self.model.SKN)
                if self.model.ACT is None:
                    instancing_details[g_ind]['no_bone'] = 1
                else:
                    if geom_ind > 0 or self.model.SKN is None:
                        for bone in self.bones:
                            if bone.GEOID == geom_ind:
                                bind_matrix = bone.absolute_transform
                    controller = controller_xml(controller_id, geometry_id, bind_matrix, joint_names, joint_matrices, joint_weights, vcounts, vertex_weight_index)
                    controller_xmls.append(controller)
                    instancing_details[g_ind]['controller'] = controller_id
                g_ind += 1

        geom_node = scene.Node("geom_node", children=geom_nodes)
        # controller_node = scene.Node("geom_node", children=controller_nodes)
        myscene = scene.Scene("myscene", [geom_node])
        collada.scenes.append(myscene)
        collada.scene = myscene
        c_filepath = dir + 'model.dae'
        collada.write(c_filepath)
        if len(controller_xmls):
            insert_controller_library(c_filepath, controller_library(controller_xmls))
        replace_visual_scenes(c_filepath, self.bones, instancing_details, non_skinned_map)
        add_misc(c_filepath)
        anim_log_path = dir + '../anim_info'
        if not os.path.exists(anim_log_path):
            f = open(anim_log_path, 'w+')
            f.write(dir + 'model.dae')
            f.write('\n')
            for bone in self.bones:
                f.write(str('bone_' + str(bone.id)) + ' ' + str(bone.track_id) + '\n')
                f.write(' '.join(["{:.5f}".format(x) for x in bone.pose.translation])+'\n')
                f.write(' '.join(["{:.5f}".format(x) for x in bone.pose.quaternion])+'\n')

if __name__ == '__main__':
    mdl = Model0(open('export_daes_mssb/mario.dat', 'rb'), 0, 0, '')
    mdl.analyze()
    mdl.toFile('export_daes_mssb/mario/')