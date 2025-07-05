bl_info = {
    "name": "Paint3D-Style Color Fill",
    "blender": (3, 0, 0),
    "category": "Mesh",
    "author": "ChatGPT",
    "description": "Create a 1x1 color texture from hex or color picker, unwrap selected faces, and assign a matching material"
}

import bpy
import bmesh
from bpy.types import Panel, Operator, PropertyGroup
from bpy.props import FloatVectorProperty, StringProperty, PointerProperty


def clamp_color(c):
    return max(0.0, min(1.0, c))


class Paint3DColorProperties(PropertyGroup):
    def update_fill_color(self, context):
        r = int(round(clamp_color(self.fill_color[0]) * 255))
        g = int(round(clamp_color(self.fill_color[1]) * 255))
        b = int(round(clamp_color(self.fill_color[2]) * 255))
        self.hex_string = f"{r:02x}{g:02x}{b:02x}"

    def update_hex_string(self, context):
        try:
            hex_val = self.hex_string.strip().lstrip('#')
            if len(hex_val) == 6:
                r = int(hex_val[0:2], 16) / 255.0
                g = int(hex_val[2:4], 16) / 255.0
                b = int(hex_val[4:6], 16) / 255.0
                self.fill_color = (r, g, b, 1.0)
        except Exception:
            pass

    fill_color: FloatVectorProperty(
        name="Fill Color",
        subtype='COLOR',
        size=4,
        min=0.0, max=1.0,
        default=(1.0, 1.0, 1.0, 1.0),
        update=update_fill_color
    )

    hex_string: StringProperty(
        name="Hex (#RRGGBB)",
        default="ffffff",
        update=update_hex_string
    )


def create_color_image(hex_code, color):
    image_name = f"color_{hex_code}"

    if image_name in bpy.data.images:
        return bpy.data.images[image_name]

    r_byte = int(round(color[0] * 255))
    g_byte = int(round(color[1] * 255))
    b_byte = int(round(color[2] * 255))
    a_byte = int(round(color[3] * 255))

    r = r_byte / 255.0
    g = g_byte / 255.0
    b = b_byte / 255.0
    a = a_byte / 255.0

    image = bpy.data.images.new(image_name, width=1, height=1, alpha=True)
    image.colorspace_settings.name = 'Non-Color'
    image.pixels = [r, g, b, a]
    image.pack()
    return image


def create_material_with_image(hex_code, color):
    mat_name = f"color_{hex_code}"

    if mat_name in bpy.data.materials:
        return bpy.data.materials[mat_name]

    image = create_color_image(hex_code, color)

    mat = bpy.data.materials.new(name=mat_name)
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
    tex_node.image.colorspace_settings.name = 'Non-Color'

    links.new(tex_node.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(bsdf.outputs["BSDF"], output_node.inputs["Surface"])

    return mat


class MESH_OT_fill_color_faces(Operator):
    bl_idname = "mesh.fill_color_faces"
    bl_label = "Fill Selected Faces with Color"
    bl_description = "Create a color texture from hex, unwrap, and assign it to selected faces"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object
        props = context.scene.paint3d_color_props
        color = props.fill_color
        hex_code = props.hex_string.lower()

        if obj.mode != 'EDIT' or obj.type != 'MESH':
            self.report({'ERROR'}, "Must be in Edit Mode with a mesh object selected")
            return {'CANCELLED'}

        bm = bmesh.from_edit_mesh(obj.data)
        uv_layer = bm.loops.layers.uv.verify()
        bmesh.update_edit_mesh(obj.data)

        bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=0.001)

        mat = create_material_with_image(hex_code, color)

        if mat.name not in [m.name for m in obj.data.materials]:
            obj.data.materials.append(mat)
        mat_index = obj.data.materials.find(mat.name)

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
        layout.prop(props, "hex_string", text="Hex Code")
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
