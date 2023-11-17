import bpy

def materialFromTexture (tex_path, mat_name):
    img = bpy.data.images.load(tex_path)
    mat = bpy.data.materials.new(mat_name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    principled_bsdf = nodes.get("Principled BSDF")
    if principled_bsdf is None:
        principled_bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
    principled_bsdf.inputs['Specular'].default_value = 0
    material_output = nodes.get("Material Output")
    if material_output is None:
        material_output = nodes.new(type="ShaderNodeOutputMaterial")
    links = mat.node_tree.links
    links.new(principled_bsdf.outputs["BSDF"], material_output.inputs["Surface"])
    tex_node = nodes.new(type='ShaderNodeTexImage')
    tex_node.image = img
    links.new(tex_node.outputs["Color"], principled_bsdf.inputs["Base Color"])
    return mat