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

def mirror_vertex_group(obj, group, axis, replace=True):
    bpy.ops.object.mode_set(mode='OBJECT')
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()

    pos_to_index = { (round(v.co.x, 6), round(v.co.y, 6), round(v.co.z, 6)) : v.index for v in bm.verts }
    index_map = {}

    for v in bm.verts:
        mirrored = v.co.copy()
        if axis == 'X': mirrored.x *= -1
        elif axis == 'Y': mirrored.y *= -1
        elif axis == 'Z': mirrored.z *= -1

        key = tuple(round(c, 6) for c in mirrored)
        if key in pos_to_index:
            index_map[v.index] = pos_to_index[key]

    original_weights = get_vertex_group_weights(obj, group)

    for src_idx, tgt_idx in index_map.items():
        if src_idx in original_weights:
            if not replace:
                # Only add if there's no existing weight
                current = [g.weight for g in obj.data.vertices[tgt_idx].groups if g.group == group.index]
                if current:
                    continue
            group.add([tgt_idx], original_weights[src_idx], 'REPLACE')

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
    bl_label = "Mirror Weights (Active Group)"
    bl_description = "Mirror active vertex group weights across the chosen axis"

    axis: EnumProperty(
        items=[('X', "X Axis", ""), ('Y', "Y Axis", ""), ('Z', "Z Axis", "")],
        name="Axis",
        default='X'
    )

    def execute(self, context):
        obj = context.object
        group = get_active_vertex_group(obj)
        if not group:
            self.report({'ERROR'}, "No active vertex group")
            return {'CANCELLED'}
        replace = context.scene.vgwt_replace_weights
        mirror_vertex_group(obj, group, self.axis, replace)
        self.report({'INFO'}, f"Mirrored weights for '{group.name}' on {self.axis} axis (replace={replace})")
        return {'FINISHED'}

class VGWT_OT_ClearGroup(bpy.types.Operator):
    bl_idname = "vgwt.clear_weights"
    bl_label = "Clear Group Weights"
    bl_description = "Remove all weights from the active vertex group"

    def execute(self, context):
        obj = context.object
        group = get_active_vertex_group(obj)
        if not group:
            self.report({'ERROR'}, "No active vertex group")
            return {'CANCELLED'}
        group.remove([v.index for v in obj.data.vertices])
        self.report({'INFO'}, f"Cleared weights for group: {group.name}")
        return {'FINISHED'}

def mirror_weight_buffer(obj, axis):
    global temp_weights
    if not temp_weights:
        return False

    bpy.ops.object.mode_set(mode='OBJECT')
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()

    pos_to_index = {tuple(round(v.co.x, 6), round(v.co.y, 6), round(v.co.z, 6)): v.index for v in bm.verts}
    index_map = {}

    for v in bm.verts:
        mirrored = v.co.copy()
        if axis == 'X': mirrored.x *= -1
        elif axis == 'Y': mirrored.y *= -1
        elif axis == 'Z': mirrored.z *= -1

        key = tuple(round(c, 6) for c in mirrored)
        if key in pos_to_index:
            index_map[v.index] = pos_to_index[key]

    mirrored_weights = {}
    for src_idx, tgt_idx in index_map.items():
        if src_idx in temp_weights:
            mirrored_weights[tgt_idx] = temp_weights[src_idx]

    temp_weights = mirrored_weights
    bm.free()
    return True

class VGWT_OT_MirrorBuffer(bpy.types.Operator):
    bl_idname = "vgwt.mirror_buffer"
    bl_label = "Mirror Copied Weights"
    bl_description = "Mirror the copied buffer weights across selected axis (before pasting)"
    
    axis: EnumProperty(
        items=[('X', "X Axis", ""), ('Y', "Y Axis", ""), ('Z', "Z Axis", "")],
        name="Axis",
        default='X'
    )

    def execute(self, context):
        obj = context.object
        if not obj or not obj.type == 'MESH':
            self.report({'ERROR'}, "Object must be a mesh")
            return {'CANCELLED'}

        if not mirror_weight_buffer(obj, self.axis):
            self.report({'ERROR'}, "No copied weights to mirror")
            return {'CANCELLED'}

        self.report({'INFO'}, f"Mirrored buffer weights across {self.axis} axis")
        return {'FINISHED'}


class VGWT_PT_ToolsPanel(bpy.types.Panel):
    bl_label = "Vertex Group Tools"
    bl_idname = "VGWT_PT_ToolsPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Vertex Tools'

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        col = layout.column(align=True)
        col.label(text="Copy/Paste Weights:")
        col.operator("vgwt.copy_weights")
        col.operator("vgwt.paste_weights")
        
        layout.label(text="Mirror Copied Weights:")
        row = layout.row(align=True)
        row.operator("vgwt.mirror_buffer", text="X-co").axis = 'X'
        row.operator("vgwt.mirror_buffer", text="Y-co").axis = 'Y'
        row.operator("vgwt.mirror_buffer", text="Z-co").axis = 'Z'

        layout.separator()
        layout.label(text="Mirror Existing Weights:")
        layout.prop(scene, "vgwt_replace_weights")

        row = layout.row(align=True)
        row.operator("vgwt.mirror_weights", text="X-ex").axis = 'X'
        row.operator("vgwt.mirror_weights", text="Y-ex").axis = 'Y'
        row.operator("vgwt.mirror_weights", text="Z-ex").axis = 'Z'

        layout.separator()
        layout.operator("vgwt.clear_weights", icon='X')

classes = [
    VGWT_OT_CopyWeights,
    VGWT_OT_PasteWeights,
    VGWT_OT_MirrorWeights,
    VGWT_PT_ToolsPanel,
    VGWT_OT_ClearGroup,
    VGWT_OT_MirrorBuffer
]

def register():
    bpy.types.Scene.vgwt_replace_weights = bpy.props.BoolProperty(
        name="Replace Existing",
        description="Replace existing weights on mirrored side",
        default=True
    )
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    del bpy.types.Scene.vgwt_replace_weights
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
