bl_info = {
    "name": "Paint3D-Style Color Fill",
    "blender": (3, 0, 0),
    "category": "Mesh",
    "author": "ChatGPT",
    "description": "Create a 1x1 color texture, unwrap selected faces, and assign color-based material"
}

import bpy
import bmesh
from bpy.types import Panel, Operator, PropertyGroup
from bpy.props import FloatVectorProperty, PointerProperty


def rgba_to_hex(rgba):
    r, g, b = (int(c * 255) for c in rgba[:3])
    return f"{r:02x}{g:02x}{b:02x}".lower()


def create_color_image(color):
    hex_code = rgba_to_hex(color)
    image_name = f"color_{hex_code}"

    if image_name in bpy.data.images:
        return bpy.data.images[image_name]

    image = bpy.data.images.new(image_name, width=1, height=1, alpha=True)
    r, g, b, a = color
    image.pixels = [r, g, b, a]
    image.pack()
    return image


def create_material_with_image(color):
    hex_code = rgba_to_hex(color)
    material_name = f"color_{hex_code}"

    # Check for existing material
    if material_name in bpy.data.materials:
        return bpy.data.materials[material_name]

    # Create image texture
    image = create_color_image(color)

    # Create material
    mat = bpy.data.materials.new(name=material_name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    nodes.clear()

    output_node = nodes.new(type="ShaderNodeOutputMaterial")
    output_node.location = (300, 0)

    bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
    bsdf.location = (100, 0)

    tex_node = nodes.new(type="ShaderNodeTexImage")
    tex_node.image = image
    tex_node.label = image.name
    tex_node.name = image.name
    tex_node.location = (-100, 0)

    links.new(tex_node.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(bsdf.outputs["BSDF"], output_node.inputs["Surface"])

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
    bl_description = "Create a color texture, unwrap, and assign it to selected faces"
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

        # Get or create material
        mat = create_material_with_image(color)

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
        layout.operator("mesh.fill_color_faces", icon='COLOR')


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
