import bpy
import bmesh
from mathutils import Vector
from bpy.props import EnumProperty

bl_info = {
    "name": "Vertex Group Weight Tools",
    "blender": (2, 80, 0),
    "category": "Object",
}

# Global temporary weight storage
temp_weights = {}

def get_active_vertex_group(obj):
    index = obj.vertex_groups.active_index
    return obj.vertex_groups[index] if index >= 0 else None

def get_vertex_group_weights(obj, group):
    weights = {}
    for v in obj.data.vertices:
        for g in v.groups:
            if g.group == group.index:
                weights[v.index] = g.weight
    return weights

def set_vertex_group_weights(obj, group, weights_dict):
    group.remove([v.index for v in obj.data.vertices])  # Clear old weights
    for v_index, weight in weights_dict.items():
        group.add([v_index], weight, 'REPLACE')

def mirror_weights(obj, axis):
    bpy.ops.object.mode_set(mode='OBJECT')
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()

    # Create lookup: position -> vertex index
    pos_to_index = {tuple(round(coord, 6) for coord in v.co): v.index for v in mesh.vertices}
    index_map = {}

    for v in bm.verts:
        mirrored = v.co.copy()
        if axis == 'X': mirrored.x *= -1
        elif axis == 'Y': mirrored.y *= -1
        elif axis == 'Z': mirrored.z *= -1

        key = tuple(round(c, 6) for c in mirrored)
        if key in pos_to_index:
            index_map[v.index] = pos_to_index[key]

    for group in obj.vertex_groups:
        original_weights = get_vertex_group_weights(obj, group)
        mirrored_weights = {}
        for src_idx, tgt_idx in index_map.items():
            if src_idx in original_weights:
                mirrored_weights[tgt_idx] = original_weights[src_idx]
        set_vertex_group_weights(obj, group, mirrored_weights)

    bm.free()

# Panel + Operators

class VGWT_OT_CopyWeights(bpy.types.Operator):
    bl_idname = "vgwt.copy_weights"
    bl_label = "Copy Weights"

    def execute(self, context):
        obj = context.object
        group = get_active_vertex_group(obj)
        if not group:
            self.report({'ERROR'}, "No active vertex group")
            return {'CANCELLED'}
        global temp_weights
        temp_weights = get_vertex_group_weights(obj, group)
        self.report({'INFO'}, f"Copied weights from group: {group.name}")
        return {'FINISHED'}

class VGWT_OT_PasteWeights(bpy.types.Operator):
    bl_idname = "vgwt.paste_weights"
    bl_label = "Paste Weights"

    def execute(self, context):
        obj = context.object
        group = get_active_vertex_group(obj)
        if not group:
            self.report({'ERROR'}, "No active vertex group")
            return {'CANCELLED'}
        global temp_weights
        if not temp_weights:
            self.report({'ERROR'}, "No weights stored. Use Copy first.")
            return {'CANCELLED'}
        set_vertex_group_weights(obj, group, temp_weights)
        self.report({'INFO'}, f"Pasted weights to group: {group.name}")
        return {'FINISHED'}

class VGWT_OT_MirrorWeights(bpy.types.Operator):
    bl_idname = "vgwt.mirror_weights"
    bl_label = "Mirror Weights"
    bl_description = "Mirror weights across the chosen axis"

    axis: EnumProperty(
        items=[
            ('X', "X Axis", "Mirror across X axis"),
            ('Y', "Y Axis", "Mirror across Y axis"),
            ('Z', "Z Axis", "Mirror across Z axis")
        ],
        name="Axis",
        default='X'
    )

    def execute(self, context):
        obj = context.object
        mirror_weights(obj, self.axis)
        self.report({'INFO'}, f"Mirrored all groups across {self.axis} axis")
        return {'FINISHED'}

class VGWT_PT_ToolsPanel(bpy.types.Panel):
    bl_label = "Vertex Group Tools"
    bl_idname = "VGWT_PT_ToolsPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Vertex Tools'

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        col.label(text="Copy/Paste Weights:")
        col.operator("vgwt.copy_weights")
        col.operator("vgwt.paste_weights")
        layout.separator()
        layout.label(text="Mirror Weights:")
        row = layout.row(align=True)
        row.operator("vgwt.mirror_weights", text="X").axis = 'X'
        row.operator("vgwt.mirror_weights", text="Y").axis = 'Y'
        row.operator("vgwt.mirror_weights", text="Z").axis = 'Z'

classes = [
    VGWT_OT_CopyWeights,
    VGWT_OT_PasteWeights,
    VGWT_OT_MirrorWeights,
    VGWT_PT_ToolsPanel,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
