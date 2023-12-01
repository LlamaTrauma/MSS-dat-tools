import xml.etree.cElementTree as et
import numpy as np

# Pycollada 0.7.2 doesn't support exporting controllers, so I've got to do this manually
# A lot of this is the result of looking at the colladas exported by BrawlBox, and it looks like they had to do this all manually too, so thanks for figuring it out for me
# These apply to version 1.4 of the collada specification. 1.5 messes with the bind_material tag at least, so isn't compatible with this

def controller_xml(id, geom_id, bind_shape_matrix, joint_names, joint_matrices, joint_weights, vcounts, vertex_weight_index):
    controller_xml = et.Element('controller', id=id)
    skin_xml = et.SubElement(controller_xml, 'skin', source='#'+geom_id)
    bind_shape_matrix_xml = et.SubElement(skin_xml, 'bind_shape_matrix')
    bind_shape_matrix_xml.text = ' '.join(["{:.20f}".format(x) for x in np.transpose(np.array(bind_shape_matrix)).flatten()])

    joint_source_xml = et.SubElement(skin_xml, 'source', id=controller_xml.attrib['id']+'_joints')
    joint_names_xml = et.SubElement(joint_source_xml, 'Name_array', id=joint_source_xml.attrib['id']+'_arr', count=str(len(joint_names)))
    joint_names_xml.text = ' '.join(joint_names)
    technique_common_xml = et.SubElement(joint_source_xml, 'technique_common')
    accessor_xml = et.SubElement(technique_common_xml, 'accessor', source='#'+joint_names_xml.attrib['id'], count=str(len(joint_names)))
    accessor_param_1 = et.SubElement(accessor_xml, 'param', name='JOINT', type='Name')

    matrix_source_xml = et.SubElement(skin_xml, 'source', id=controller_xml.attrib['id']+'_matrices')
    joint_matrices_xml = et.SubElement(matrix_source_xml, 'float_array', id=matrix_source_xml.attrib['id']+'_arr', count=str(len(joint_matrices) * 16))
    joint_matrices_xml.text = ' '.join([' '.join(["{:.20f}".format(x) for x in np.transpose(mat).flatten()]) for mat in joint_matrices])
    technique_common_xml = et.SubElement(matrix_source_xml, 'technique_common')
    accessor_xml = et.SubElement(technique_common_xml, 'accessor', source='#'+joint_matrices_xml.attrib['id'], count=str(len(joint_matrices)), stride='16')
    accessor_param_1 = et.SubElement(accessor_xml, 'param', type='float4x4')

    weight_source_xml = et.SubElement(skin_xml, 'source', id=controller_xml.attrib['id']+'_weights')
    joint_weights_xml = et.SubElement(weight_source_xml, 'float_array', id=weight_source_xml.attrib['id']+'_arr', count=str(len(joint_weights)))
    joint_weights_xml.text = ' '.join(["{:.20f}".format(x) for x in joint_weights])
    technique_common_xml = et.SubElement(weight_source_xml, 'technique_common')
    accessor_xml = et.SubElement(technique_common_xml, 'accessor', source='#'+joint_weights_xml.attrib['id'], count=str(len(joint_weights)))
    accessor_param_1 = et.SubElement(accessor_xml, 'param', type='float')

    joints_xml = et.SubElement(skin_xml, 'joints')
    joints_input_1 = et.SubElement(joints_xml, 'input', semantic='JOINT', source='#'+joint_source_xml.attrib['id'])
    joints_input_2 = et.SubElement(joints_xml, 'input', semantic='INV_BIND_MATRIX', source='#'+matrix_source_xml.attrib['id'])

    vertex_weights_xml = et.SubElement(skin_xml, 'vertex_weights', count=str(len(vcounts)))
    joint_offset_xml = et.SubElement(vertex_weights_xml, 'input', semantic='JOINT', offset='0', source='#'+joint_source_xml.attrib['id'])
    weight_offset_xml = et.SubElement(vertex_weights_xml, 'input', semantic='WEIGHT', offset='1', source='#'+weight_source_xml.attrib['id'])
    vcount_xml = et.SubElement(vertex_weights_xml, 'vcount')
    vcount_xml.text = ' '.join([str(int(x)) for x in vcounts])
    v_xml = et.SubElement(vertex_weights_xml, 'v')
    v_xml.text = ' '.join([str(int(x)) for x in vertex_weight_index])
    # print(vertex_weight_index)
    return controller_xml

def controller_library(controller_xmls):
    library_xml = et.Element('library_controllers')
    for xml in controller_xmls:
        library_xml.append(xml)
    return library_xml

def insert_controller_library(f_path, c_library):
    collada_xml = et.parse(f_path)
    root = collada_xml.getroot()
    for ind, child in enumerate(root):
        if child.tag.split('}')[-1] == 'library_geometries':
            root.insert(ind + 1, c_library)
    tree = et.ElementTree(root)
    et.indent(tree, space="\t", level=0)
    tree.write(f_path, encoding="utf-8")

def replace_visual_scenes(f_path, bones, instancing_details, non_skinned_map):
    collada_xml = et.parse(f_path)
    root = collada_xml.getroot()
    # Not sure why I have to run this twice, if I had to guess removing an element while looping through the children is skipping the next element
    for child in root:
        if child.tag.split('}')[-1] in ('library_visual_scenes', 'scene'):
            root.remove(child)
    for child in root:
        if child.tag.split('}')[-1] in ('library_visual_scenes', 'scene'):
            root.remove(child)
    new_visual_scenes_xml = et.Element('library_visual_scenes')
    new_visual_scene_xml = et.SubElement(new_visual_scenes_xml, 'visual_scene', id='RootNode', name='RootNode')
    
    if len(bones):
        base_joint_xml = et.SubElement(new_visual_scene_xml, 'node', id='BaseJoint', name='BaseJoint', sid='BaseJoint', type='JOINT')
        bone_stack = []
        for bone in bones:
            if bone.parent == -1:
                bone_stack.append([base_joint_xml, bone])
        while len(bone_stack):
            first_elem = bone_stack[0]
            bone_stack = bone_stack[1:]
            parent_xml = first_elem[0]
            joint = first_elem[1]
            name = 'bone_' + str(joint.id)
            joint_xml = et.SubElement(parent_xml, 'node', id=name, name=name, sid=name, type='JOINT')
            transform_xml = et.SubElement(joint_xml, 'matrix', sid='transform')
            transform_xml.text = ' '.join(["{:.20f}".format(x) for x in np.transpose(joint.pose.transform).flatten()])
            # if joint.id in non_skinned_map:
            #     g_ind = non_skinned_map[joint.id]
            #     vals = instancing_details[g_ind]
            #     node_xml = et.SubElement(joint_xml, 'node', id='geometry_node_'+str(g_ind), name='geometry_'+str(g_ind), type='NODE')
            #     geom_instance_xml = et.SubElement(node_xml, 'instance_geometry', url='#'+vals['geometry'])
            #     for material_symbol, target in vals['materials'].items():
            #         bind_material_xml = et.SubElement(geom_instance_xml, 'bind_material')
            #         technique_common_xml = et.SubElement(bind_material_xml, 'technique_common')
            #         instance_material_xml = et.SubElement(technique_common_xml, 'instance_material', symbol=material_symbol, target='#'+target)
            #         bind_vertex_input_1 = et.SubElement(instance_material_xml, 'bind_vertex_input', semantic='TEX', input_semantic='TEXCOORD', input_set='0')
            for bone in bones:
                if bone.parent == joint.id:
                    bone_stack.append([joint_xml, bone])

    for g_ind, vals in instancing_details.items():
        if 'controller' in vals:
            node_xml = et.SubElement(new_visual_scene_xml, 'node', id='geometry_node_'+str(g_ind), name=vals['geometry'], type='NODE')
            controller_id = vals['controller']
            controller_instance_xml = et.SubElement(node_xml, 'instance_controller', url='#'+controller_id)
            skeleton_base_xml = et.SubElement(controller_instance_xml, 'skeleton')
            skeleton_base_xml.text = '#' + base_joint_xml.attrib['id']
            bind_material_xml = et.SubElement(controller_instance_xml, 'bind_material')
            technique_common_xml = et.SubElement(bind_material_xml, 'technique_common')    
            for material_symbol, target in vals['materials'].items():
                instance_material_xml = et.SubElement(technique_common_xml, 'instance_material', symbol=material_symbol, target='#'+target)
                bind_vertex_input_1 = et.SubElement(instance_material_xml, 'bind_vertex_input', semantic='TEX', input_semantic='TEXCOORD', input_set='0')
        elif 'no_bone' in vals:
            vals = instancing_details[g_ind]
            node_xml = et.SubElement(new_visual_scene_xml, 'node', id='geometry_node_'+str(g_ind), name=vals['geometry'], type='NODE')
            geom_instance_xml = et.SubElement(node_xml, 'instance_geometry', url='#'+vals['geometry'])
            bind_material_xml = et.SubElement(geom_instance_xml, 'bind_material')
            technique_common_xml = et.SubElement(bind_material_xml, 'technique_common')    
            for material_symbol, target in vals['materials'].items():
                instance_material_xml = et.SubElement(technique_common_xml, 'instance_material', symbol=material_symbol, target='#'+target)
                bind_vertex_input_1 = et.SubElement(instance_material_xml, 'bind_vertex_input', semantic='TEX', input_semantic='TEXCOORD', input_set='0')


    new_scene_xml = et.Element('scene')
    visual_scene_instance_xml = et.SubElement(new_scene_xml, 'instance_visual_scene', url='#'+new_visual_scene_xml.attrib['id'])

    root.append(new_visual_scenes_xml)
    root.append(new_scene_xml)

    tree = et.ElementTree(root)
    et.indent(tree, space="\t", level=0)
    tree.write(f_path, encoding="utf-8")

    collada_xml.write(f_path)

def animate_dae(f_path, out_path, sequence_dict, track_dict):
    animation_lib_xml = et.Element('library_animations')
    for track_id, keyframe_dict in sequence_dict.items():
        times = list(keyframe_dict.keys())
        values = [keyframe_dict[time] for time in times]

        animation_xml = et.SubElement(animation_lib_xml, 'animation', id='animation_'+str(track_id))

        timestamps_source_xml = et.SubElement(animation_xml, 'source', id=animation_xml.attrib['id']+'_input')
        timestamps_arr_xml = et.SubElement(timestamps_source_xml, 'float_array', id=timestamps_source_xml.attrib['id']+'_array', count=str(int(len(keyframe_dict))))
        timestamps_arr_xml.text = ' '.join(["{:.20f}".format(x/30) for x in times])
        # print(list(keyframe_dict.keys()))
        technique_common_xml = et.SubElement(timestamps_source_xml, 'technique_common')
        accessor_xml = et.SubElement(technique_common_xml, 'accessor', source='#'+timestamps_arr_xml.attrib['id'], count=timestamps_arr_xml.attrib['count'])
        accessor_param_1_xml = et.SubElement(accessor_xml, 'param', name='TIME', type='float')

        data_source_xml = et.SubElement(animation_xml, 'source', id=animation_xml.attrib['id']+'_output')
        data_arr_xml = et.SubElement(data_source_xml, 'float_array', id=data_source_xml.attrib['id']+'_array', count=str(int(timestamps_arr_xml.attrib['count'])*16))
        data_arr_xml.text = ' '.join(' '.join(["{:.20f}".format(x) for x in np.transpose(mat).flatten()]) for mat in values)
        technique_common_xml = et.SubElement(data_source_xml, 'technique_common')
        accessor_xml = et.SubElement(technique_common_xml, 'accessor', source='#'+data_arr_xml.attrib['id'], count=timestamps_arr_xml.attrib['count'], stride='16')
        accessor_param_xml = et.SubElement(accessor_xml, 'param', name='TRANSFORM', type='float4x4')

        interpolations_source_xml = et.SubElement(animation_xml, 'source', id=animation_xml.attrib['id']+'_interpolation')
        interpolations_arr_xml = et.SubElement(interpolations_source_xml, 'Name_array', id=interpolations_source_xml.attrib['id']+'_array', count=str(int(len(keyframe_dict))))
        interpolations_arr_xml.text = ' '.join(['LINEAR'] * len(keyframe_dict))
        technique_common_xml = et.SubElement(interpolations_source_xml, 'technique_common')
        accessor_xml = et.SubElement(technique_common_xml, 'accessor', source='#'+interpolations_arr_xml.attrib['id'], count=interpolations_arr_xml.attrib['count'])
        accessor_param_1_xml = et.SubElement(accessor_xml, 'param', name='INTERPOLATION', type='name')

        sampler_xml = et.SubElement(animation_xml, 'sampler', id=animation_xml.attrib['id']+'_sampler')
        sampler_input_1_xml = et.SubElement(sampler_xml, 'input', semantic='INPUT', source='#'+timestamps_source_xml.attrib['id'])
        sampler_input_2_xml = et.SubElement(sampler_xml, 'input', semantic='OUTPUT', source='#'+data_source_xml.attrib['id'])
        sampler_input_3_xml = et.SubElement(sampler_xml, 'input', semantic='INTERPOLATION', source='#'+interpolations_source_xml.attrib['id'])

        channel_xml = et.SubElement(animation_xml, 'channel', source='#'+sampler_xml.attrib['id'], target=track_dict[track_id]+'/transform')

    collada_xml = et.parse(f_path)
    root = collada_xml.getroot()
    for ind, child in enumerate(root):
        if child.tag.split('}')[-1] == 'library_visual_scenes':
            root.insert(ind, animation_lib_xml)
            break
    tree = et.ElementTree(root)
    et.indent(tree, space="\t", level=0)
    tree.write(out_path, encoding="utf-8")

def add_misc(f_path):
    collada_xml = et.parse(f_path)
    contributor_xml_1 = et.Element('contributor')
    author_xml_1 = et.SubElement(contributor_xml_1, 'author')
    author_xml_1.text = 'LlamaTrauma'
    contributor_xml_2 = et.Element('contributor')
    author_xml_2 = et.SubElement(contributor_xml_2, 'author')
    author_xml_2.text = 'Geno Penguin'
    root = collada_xml.getroot()
    for ind, child in enumerate(root):
        if child.tag.split('}')[-1] == 'asset':
            child.append(contributor_xml_1)
            child.append(contributor_xml_2)
            break
    tree = et.ElementTree(root)
    et.indent(tree, space="\t", level=0)
    tree.write(f_path, encoding="utf-8")
    f = open(f_path, 'r')
    contents = f.read()
    f.close()
    f = open(f_path, 'w')
    f.write('<?xml version="1.0" encoding="utf-8"?>\n')
    f.write(contents)
    f.close()