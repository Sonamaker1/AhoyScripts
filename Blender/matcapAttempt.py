bl_info = {
    "name": "Matcap Tools",
    "blender": (4, 0, 0),
    "category": "Material",
}

import bpy
import os

def get_next_matcap_name():
    base_name = "Matcap"
    existing = [m.name for m in bpy.data.materials if m.name.startswith(base_name)]
    i = 0
    while True:
        name = base_name if i == 0 else f"{base_name}.{str(i).zfill(3)}"
        if name not in existing:
            return name
        i += 1

def create_matcap_material(matcap_path):
    mat = bpy.data.materials.new(name=get_next_matcap_name())
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    nodes.clear()

    output = nodes.new(type="ShaderNodeOutputMaterial")
    principled = nodes.new(type="ShaderNodeBsdfPrincipled")
    tex_img = nodes.new(type="ShaderNodeTexImage")
    geom = nodes.new(type="ShaderNodeNewGeometry")
    mapping = nodes.new(type="ShaderNodeMapping")
    sep_xyz = nodes.new(type="ShaderNodeSeparateXYZ")
    combine_rgb = nodes.new(type="ShaderNodeCombineRGB")

    tex_img.image = bpy.data.images.load(matcap_path)
    tex_img.interpolation = 'Closest'
    tex_img.projection = 'SPHERE'

    # Layout
    output.location = (400, 0)
    principled.location = (200, 0)
    combine_rgb.location = (-200, 0)
    sep_xyz.location = (-400, 0)
    geom.location = (-600, 0)
    tex_img.location = (0, -200)

    # Links
    links.new(principled.outputs["BSDF"], output.inputs["Surface"])
    links.new(combine_rgb.outputs["Image"], principled.inputs["Base Color"])
    links.new(sep_xyz.outputs["X"], combine_rgb.inputs["R"])
    links.new(sep_xyz.outputs["Y"], combine_rgb.inputs["G"])
    links.new(sep_xyz.outputs["Z"], combine_rgb.inputs["B"])
    links.new(geom.outputs["Normal"], sep_xyz.inputs["Vector"])

    return mat

class MATCAPTOOLS_OT_create(bpy.types.Operator):
    bl_idname = "matcap_tools.create"
    bl_label = "Create Matcap Material"

    def execute(self, context):
        # Try to detect current matcap
        matcap_path = bpy.context.preferences.themes[0].view_3d.matcap
        if not os.path.isfile(matcap_path):
            self.report({'WARNING'}, "Could not detect matcap image. Please select manually.")
            matcap_path = bpy.path.abspath(bpy.path.ensure_ext(bpy.path.basename("//matcap.png"), ".png"))
            bpy.ops.image.open('INVOKE_DEFAULT')
            return {'CANCELLED'}

        mat = create_matcap_material(matcap_path)
        if context.object:
            if context.object.data.materials:
                context.object.data.materials[0] = mat
            else:
                context.object.data.materials.append(mat)

        self.report({'INFO'}, f"Matcap material created: {mat.name}")
        return {'FINISHED'}

class MATCAPTOOLS_OT_bake(bpy.types.Operator):
    bl_idname = "matcap_tools.bake"
    bl_label = "Bake Material to Object UVs"

    def execute(self, context):
        obj = context.active_object
        if not obj or not obj.data.uv_layers:
            self.report({'ERROR'}, "Active object has no UV map.")
            return {'CANCELLED'}

        img = bpy.data.images.new("MatcapBake", width=2048, height=2048)
        mat = obj.active_material
        if not mat:
            self.report({'ERROR'}, "No active material to bake.")
            return {'CANCELLED'}

        tex_img = mat.node_tree.nodes.new("ShaderNodeTexImage")
        tex_img.image = img
        mat.node_tree.nodes.active = tex_img

        bpy.context.scene.render.engine = 'CYCLES'
        bpy.context.scene.cycles.samples = 1
        bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'}, use_clear=True)

        img.filepath_raw = bpy.path.abspath("//matcap_bake.png")
        img.file_format = 'PNG'
        img.save()

        self.report({'INFO'}, f"Baked to {img.filepath_raw}")
        return {'FINISHED'}

class MATCAPTOOLS_PT_panel(bpy.types.Panel):
    bl_label = "Matcap Tools"
    bl_idname = "MATCAPTOOLS_PT_panel"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Matcap"

    def draw(self, context):
        layout = self.layout
        layout.operator("matcap_tools.create", text="Create Matcap Material")
        layout.operator("matcap_tools.bake", text="Bake Material to UVs")

classes = (
    MATCAPTOOLS_OT_create,
    MATCAPTOOLS_OT_bake,
    MATCAPTOOLS_PT_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
