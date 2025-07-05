bl_info = {
    "name": "Paint3D-Style Color Fill",
    "blender": (3, 0, 0),
    "category": "Mesh",
    "author": "ChatGPT",
    "description": "Create 1x1 color texture, unwrap selected faces, and assign the colored material"
}

import bpy
import bmesh
from bpy.types import Panel, Operator, PropertyGroup
from bpy.props import FloatVectorProperty, PointerProperty
import gpu
import gpu.types
from mathutils import Color


def rgba_to_hex(rgba):
    r, g, b = (int(c * 255) for c in rgba[:3])
    return f"{r:02x}{g:02x}{b:02x}".lower()


def create_color_texture(color):
    hex_code = rgba_to_hex(color)
    tex_name = f"color_{hex_code}"

    # Check if texture already exists
    if tex_name in bpy.data.images:
        return bpy.data.images[tex_name]

    img = bpy.data.images.new(tex_name, width=1, height=1)
    r, g, b, a = color
    img.pixels = [r, g, b, a] * 1  # 1 pixel
    img.pack()
    return img


def get_or_create_material_with_texture(color):
    hex_code = rgba_to_hex(color)
    mat_name = f"color_{hex_code}"
    tex_name = mat_name

    # Check for existing material
    if mat_name in bpy.data.materials:
        return bpy.data.materials[mat_name]

    # Create texture
    image = create_color_texture(color)

    # Create material
    mat = bpy.data.materials.new(name=mat_name)
    mat.use_nodes = True

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new(type='ShaderNodeOutputMaterial')
    output.location = (400, 0)

    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.location = (200, 0)

    tex_node = nodes.new(type='ShaderNodeTexImage')
    tex_node.image = image
    tex_node.label = tex_name
    tex_node.name = tex_name
    tex_node.location = (0, 0)

    links.new(tex_node.outputs['Color'], bsdf.inputs['Base Color'])
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    return mat


class Paint3DColorProperties(PropertyGroup):
    fill_color: FloatVectorProperty(
        name="Fill Color",
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0, 1.0)
    )


class MESH_OT_fill_color_faces(Operator):
    bl_idname = "mesh.fill_color_faces"
    bl_label = "Fill Selected Faces with Color"
    bl_description = "Create texture from color, unwrap and assign to selected faces"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object
        color = context.scene.paint3d_color_props.fill_color

        if obj.mode != 'EDIT' or obj.type != 'MESH':
            self.report({'ERROR'}, "Must be in Edit Mode with a mesh object selected")
            return {'CANCELLED'}

        bm = bmesh.from_edit_mesh(obj.data)
        uv_layer = bm.loops.layers.uv.verify()
        bmesh.update_edit_mesh(obj.data)

        # Unwrap selected faces
        bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=0.001)

        # Get or create the material
        mat = get_or_create_material_with_texture(color)

        # Add material to object if needed
        if mat.name not in [m.name for m in obj.data.materials]:
            obj.data.materials.append(mat)
        mat_index = obj.data.materials.find(mat.name)

        # Assign material index to selected faces
        for face in bm.faces:
            if face.select:
                face.material_index = mat_index

        bmesh.update_edit_mesh(obj.data)
        self.report({'INFO'}, f"Applied material: {mat.name}")
        return {'FINISHED'}


class VIEW3D_PT_paint3d_color_fill(Panel):
    bl_label = "Paint3D-Style Fill"
    bl_idname = "VIEW3D_PT_paint3d_color_fill"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Paint3D Fill"

    def draw(self, context):
        layout = self.layout
        props = context.scene.paint3d_color_props

        layout.prop(props, "fill_color")
        layout.operator("mesh.fill_color_faces", icon='BRUSH_DATA')


def register():
    bpy.utils.register_class(Paint3DColorProperties)
    bpy.utils.register_class(MESH_OT_fill_color_faces)
    bpy.utils.register_class(VIEW3D_PT_paint3d_color_fill)
    bpy.types.Scene.paint3d_color_props = PointerProperty(type=Paint3DColorProperties)


def unregister():
    bpy.utils.unregister_class(Paint3DColorProperties)
    bpy.utils.unregister_class(MESH_OT_fill_color_faces)
    bpy.utils.unregister_class(VIEW3D_PT_paint3d_color_fill)
    del bpy.types.Scene.paint3d_color_props


if __name__ == "__main__":
    register()
