bl_info = {
    "name": "Face Material Painter",
    "author": "Your Name",
    "version": (1, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Face Color",
    "description": "Apply or create a solid color material to selected faces",
    "category": "Mesh",
}

import bpy
import bmesh
import re
from bpy.props import FloatVectorProperty, StringProperty, PointerProperty
from bpy.types import Operator, Panel, PropertyGroup


# --- HEX to RGB Helper ---
def hex_to_rgb_float(hex_code):
    hex_code = hex_code.strip().lstrip('#')
    if len(hex_code) != 6 or not re.match(r'^[0-9A-Fa-f]{6}$', hex_code):
        return None
    r = int(hex_code[0:2], 16) / 255.0
    g = int(hex_code[2:4], 16) / 255.0
    b = int(hex_code[4:6], 16) / 255.0
    return (r, g, b)


# --- Create or Retrieve Material by Hex Color ---
def get_or_create_color_material(color_hex, rgb):
    name = f"Mat_{color_hex.upper().lstrip('#')}"
    if name in bpy.data.materials:
        return bpy.data.materials[name]

    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    if "Specular" in bsdf.inputs:
        bsdf.inputs["Specular"].default_value = 0.1

    return mat


# --- Property Group ---
class FaceColorMaterialProps(PropertyGroup):
    hex_color: StringProperty(
        name="Hex Color",
        description="Hex color code (e.g. #ff8800)",
        default="#ffffff"
    )

    color_picker: FloatVectorProperty(
        name="Color Picker",
        subtype='COLOR',
        min=0.0, max=1.0,
        default=(1.0, 1.0, 1.0)
    )


# --- Operator ---
class FACECOLOR_OT_apply_material(bpy.types.Operator):
    bl_idname = "mesh.face_apply_material_color"
    bl_label = "Apply Color Material to Faces"
    bl_description = "Apply a new or existing solid color material to selected faces"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.edit_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Must be in Edit Mode with a mesh object selected")
            return {'CANCELLED'}

        props = context.scene.face_color_material_props
        rgb = hex_to_rgb_float(props.hex_color)

        if not rgb:
            self.report({'WARNING'}, "Invalid hex color, using color picker")
            rgb = props.color_picker

        hex_label = props.hex_color.strip().upper() if re.match(r'^#?[0-9A-Fa-f]{6}$', props.hex_color.strip()) else \
                    "#{:02X}{:02X}{:02X}".format(int(rgb[0]*255), int(rgb[1]*255), int(rgb[2]*255))

        mat = get_or_create_color_material(hex_label, rgb)

        # Ensure material exists on the object material slots
        if mat.name not in [m.name for m in obj.data.materials]:
            obj.data.materials.append(mat)

        mat_index = obj.data.materials.find(mat.name)

        bm = bmesh.from_edit_mesh(obj.data)
        bm.faces.ensure_lookup_table()

        for face in bm.faces:
            if face.select:
                face.material_index = mat_index

        bmesh.update_edit_mesh(obj.data, loop_triangles=True)
        self.report({'INFO'}, f"Applied material '{mat.name}' to selected faces")
        return {'FINISHED'}


# --- Panel ---
class FACECOLOR_PT_panel(bpy.types.Panel):
    bl_label = "Face Color Tool"
    bl_idname = "FACECOLOR_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Face Color"

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    def draw(self, context):
        layout = self.layout
        props = context.scene.face_color_material_props

        layout.label(text="Material Color Input:")
        layout.prop(props, "hex_color")
        layout.prop(props, "color_picker", text="Color Picker")

        layout.operator("mesh.face_apply_material_color", icon='MATERIAL')


# --- Register ---
classes = (
    FaceColorMaterialProps,
    FACECOLOR_OT_apply_material,
    FACECOLOR_PT_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.face_color_material_props = PointerProperty(type=FaceColorMaterialProps)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.face_color_material_props

if __name__ == "__main__":
    register()
