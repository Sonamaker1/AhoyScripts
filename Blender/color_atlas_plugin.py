bl_info = {
    "name": "Color Atlas Filler",
    "blender": (3, 0, 0),
    "category": "UV",
    "author": "ChatGPT",
    "description": "Fill selected faces with a solid color from a shared 512x512 color atlas"
}

import bpy
import bmesh
import json
from bpy.props import FloatVectorProperty, StringProperty, EnumProperty
from bpy.types import Operator, Panel, PropertyGroup
from bpy_extras.image_utils import load_image

ATLAS_NAME = "MainColorAtlas"
ATLAS_SIZE = 512
BLOCK_SIZE = 8
INNER_SIZE = 4


def encode_color_key(color):
    return ",".join(str(round(c * 255)) for c in color)

def decode_color_key(key):
    return tuple(int(k) / 255.0 for k in key.split(","))


class ColorAtlasProperties(PropertyGroup):
    fill_color: FloatVectorProperty(
        name="Fill Color",
        subtype='COLOR',
        min=0.0, max=1.0,
        size=3,
        default=(1.0, 0.0, 1.0)
    )
    color_index_map_json: StringProperty(
        name="Serialized Color Map",
        default="{}"
    )
    
    selected_color: EnumProperty(
        name="Atlas Color",
        items=lambda self, context: self.get_color_enum_items()
    )

    def get_color_index_map(self):
        return json.loads(self.color_index_map_json)

    def set_color_index_map(self, color_map):
        self.color_index_map_json = json.dumps(color_map)

    def get_color_enum_items(self):
        color_map = self.get_color_index_map()
        items = []
        for key, idx in color_map.items():
            label = f"#{''.join(f'{int(k):02X}' for k in key.split(','))}"
            items.append((key, label, f"Block {idx}"))
        return items


def get_or_create_atlas():
    if ATLAS_NAME in bpy.data.images:
        return bpy.data.images[ATLAS_NAME]
    image = bpy.data.images.new(ATLAS_NAME, width=ATLAS_SIZE, height=ATLAS_SIZE, alpha=False, float_buffer=False)
    image.generated_color = (1, 1, 1, 1)
    image.pixels = [1.0] * (ATLAS_SIZE * ATLAS_SIZE * 4)
    image.pack()
    return image


def get_or_assign_color_index(color, props):
    color_map = props.get_color_index_map()
    key = encode_color_key(color)
    if key in color_map:
        return color_map[key]
    index = len(color_map)
    if index >= 64:
        raise RuntimeError("Color atlas full (max 64 colors)")
    color_map[key] = index
    props.set_color_index_map(color_map)
    return index


def write_color_to_atlas(image, color_index, color):
    x = (color_index % 8) * BLOCK_SIZE
    y = (color_index // 8) * BLOCK_SIZE
    pixels = list(image.pixels)
    for j in range(BLOCK_SIZE):
        for i in range(BLOCK_SIZE):
            px = (y + j) * ATLAS_SIZE + (x + i)
            idx = px * 4
            r, g, b = color
            pixels[idx:idx + 3] = [r, g, b]
            pixels[idx + 3] = 1.0
    image.pixels = pixels


def get_uv_coords(color_index):
    x = (color_index % 8) * BLOCK_SIZE + 2
    y = (color_index // 8) * BLOCK_SIZE + 2
    min_u = x / ATLAS_SIZE
    min_v = y / ATLAS_SIZE
    max_u = (x + INNER_SIZE) / ATLAS_SIZE
    max_v = (y + INNER_SIZE) / ATLAS_SIZE
    return [(min_u, min_v), (max_u, min_v), (max_u, max_v), (min_u, max_v)]


class UV_OT_fill_color_block(Operator):
    bl_idname = "uv.fill_color_block"
    bl_label = "Fill with Atlas Color"
    bl_description = "Map selected faces to a solid color block in the shared atlas"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object
        if not obj or obj.type != 'MESH' or obj.mode != 'EDIT':
            self.report({'ERROR'}, "Must be in Edit Mode on a mesh")
            return {'CANCELLED'}

        bm = bmesh.from_edit_mesh(obj.data)
        uv_layer = bm.loops.layers.uv.verify()
        image = get_or_create_atlas()

        props = context.scene.color_atlas_props
        color = props.fill_color

        if not obj.data.uv_layers:
            bpy.ops.uv.unwrap(method='ANGLE_BASED')

        if obj.active_material is None:
            mat = bpy.data.materials.new("AtlasMaterial")
            mat.use_nodes = True
            bsdf = mat.node_tree.nodes.get("Principled BSDF")
            tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
            tex.image = image
            tex.image.colorspace_settings.name = 'Non-Color'
            mat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
            obj.data.materials.append(mat)
            obj.active_material = mat

        color_index = get_or_assign_color_index(color, props)
        write_color_to_atlas(image, color_index, color)
        coords = get_uv_coords(color_index)

        for face in bm.faces:
            if face.select:
                for loop, uv in zip(face.loops, coords):
                    loop[uv_layer].uv = uv

        bmesh.update_edit_mesh(obj.data)
        self.report({'INFO'}, f"Assigned color block {color_index}")
        return {'FINISHED'}


class UV_OT_assign_existing_block(Operator):
    bl_idname = "uv.assign_existing_block"
    bl_label = "Assign Existing Atlas Color"
    bl_description = "Assign a color block already in the atlas to selected faces"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object
        if not obj or obj.type != 'MESH' or obj.mode != 'EDIT':
            self.report({'ERROR'}, "Must be in Edit Mode on a mesh")
            return {'CANCELLED'}

        props = context.scene.color_atlas_props
        key = props.selected_color
        color = decode_color_key(key)
        color_map = props.get_color_index_map()
        color_index = color_map.get(key)
        if color_index is None:
            self.report({'ERROR'}, "Selected color not in atlas")
            return {'CANCELLED'}

        image = get_or_create_atlas()
        bm = bmesh.from_edit_mesh(obj.data)
        uv_layer = bm.loops.layers.uv.verify()

        coords = get_uv_coords(color_index)

        for face in bm.faces:
            if face.select:
                for loop, uv in zip(face.loops, coords):
                    loop[uv_layer].uv = uv

        bmesh.update_edit_mesh(obj.data)
        self.report({'INFO'}, f"Applied existing atlas color block {color_index}")
        return {'FINISHED'}


class UV_PT_color_block_fill(Panel):
    bl_label = "Color Atlas Filler"
    bl_idname = "UV_PT_color_block_fill"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'UV'

    def draw(self, context):
        layout = self.layout
        props = context.scene.color_atlas_props
        layout.prop(props, "fill_color")
        layout.operator("uv.fill_color_block")
        layout.separator()
        layout.prop(props, "selected_color")
        layout.operator("uv.assign_existing_block")


def register():
    bpy.utils.register_class(ColorAtlasProperties)
    bpy.utils.register_class(UV_OT_fill_color_block)
    bpy.utils.register_class(UV_OT_assign_existing_block)
    bpy.utils.register_class(UV_PT_color_block_fill)
    bpy.types.Scene.color_atlas_props = bpy.props.PointerProperty(type=ColorAtlasProperties)


def unregister():
    bpy.utils.unregister_class(ColorAtlasProperties)
    bpy.utils.unregister_class(UV_OT_fill_color_block)
    bpy.utils.unregister_class(UV_OT_assign_existing_block)
    bpy.utils.unregister_class(UV_PT_color_block_fill)
    del bpy.types.Scene.color_atlas_props


if __name__ == "__main__":
    register()
