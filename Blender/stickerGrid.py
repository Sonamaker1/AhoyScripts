bl_info = {
    "name": "Grid Sorter + Axis Aligner + Mover",
    "author": "Your Name",
    "version": (1, 4),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Grid Sorter",
    "description": "Arrange, align, and move objects in space. Syncs with selection.",
    "category": "Object",
}

import bpy
from bpy.props import IntProperty, FloatProperty, PointerProperty, EnumProperty
from bpy.app.handlers import persistent

last_selected_object = None  # Tracks last selected object for comparison

# -------- GRID ARRANGER --------

# ---------- OPERATORS ----------

class GRIDSORTER_OT_arrange_grid(bpy.types.Operator):
    bl_idname = "object.arrange_objects_grid_xz"
    bl_label = "Arrange in Grid (X/Z)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.grid_sorter_props
        per_row = props.per_row
        spacing = props.spacing

        selected = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if per_row < 1 or not selected:
            self.report({'WARNING'}, "Check selection and grid count")
            return {'CANCELLED'}

        selected.sort(key=lambda o: o.name.lower())

        for i, obj in enumerate(selected):
            row = i // per_row
            col = i % per_row
            obj.location.x = col * spacing
            obj.location.z = -row * spacing

        return {'FINISHED'}

# -------- AXIS ALIGNERS --------

class ALIGN_OT_axis(bpy.types.Operator):
    bl_idname = "object.align_objects_axis"
    bl_label = "Align Objects to Axis"
    bl_options = {'REGISTER', 'UNDO'}

    axis: EnumProperty(
        items=[('X', "X Axis", ""), ('Y', "Y Axis", ""), ('Z', "Z Axis", "")]
    )

    def execute(self, context):
        props = context.scene.grid_sorter_props
        value = getattr(props, f'align_{self.axis.lower()}')
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                setattr(obj.location, self.axis.lower(), value)
        return {'FINISHED'}


class MOVE_OT_axis(bpy.types.Operator):
    bl_idname = "object.move_objects_axis"
    bl_label = "Move Objects on Axis"
    bl_options = {'REGISTER', 'UNDO'}

    axis: EnumProperty(
        items=[('X', "X Axis", ""), ('Y', "Y Axis", ""), ('Z', "Z Axis", "")]
    )

    def execute(self, context):
        props = context.scene.grid_sorter_props
        offset = getattr(props, f'move_{self.axis.lower()}')
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                old_val = getattr(obj.location, self.axis.lower())
                setattr(obj.location, self.axis.lower(), old_val + offset)
        return {'FINISHED'}


# ---------- UI PANEL ----------

class GRIDSORTER_PT_panel(bpy.types.Panel):
    bl_label = "Grid Sorter + Axis Tools"
    bl_idname = "GRIDSORTER_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Grid Sorter'

    def draw(self, context):
        layout = self.layout
        props = context.scene.grid_sorter_props

        # Grid section
        layout.label(text="Grid Arrangement (X/Z):")
        layout.prop(props, "per_row")
        layout.prop(props, "spacing")
        layout.operator("object.arrange_objects_grid_xz", icon='GRID')

        layout.separator()
        layout.label(text="Align to Axis:")
        row = layout.row()
        row.prop(props, "align_x")
        row.operator("object.align_objects_axis", text="Align X").axis = 'X'

        row = layout.row()
        row.prop(props, "align_y")
        row.operator("object.align_objects_axis", text="Align Y").axis = 'Y'

        row = layout.row()
        row.prop(props, "align_z")
        row.operator("object.align_objects_axis", text="Align Z").axis = 'Z'

        layout.separator()
        layout.label(text="Move by Axis Offset:")
        row = layout.row()
        row.prop(props, "move_x")
        row.operator("object.move_objects_axis", text="Move X").axis = 'X'

        row = layout.row()
        row.prop(props, "move_y")
        row.operator("object.move_objects_axis", text="Move Y").axis = 'Y'

        row = layout.row()
        row.prop(props, "move_z")
        row.operator("object.move_objects_axis", text="Move Z").axis = 'Z'


# ---------- PROPERTIES ----------

class GRIDSORTER_Properties(bpy.types.PropertyGroup):
    per_row: IntProperty(name="Objects per Row", default=5, min=1)
    spacing: IntProperty(name="Grid Spacing", default=3, min=1)

    align_x: FloatProperty(name="X", default=0.0)
    align_y: FloatProperty(name="Y", default=0.0)
    align_z: FloatProperty(name="Z", default=0.0)

# -------- REGISTER --------
    move_x: FloatProperty(name="Move X", default=0.0)
    move_y: FloatProperty(name="Move Y", default=0.0)
    move_z: FloatProperty(name="Move Z", default=0.0)


# ---------- SYNC HANDLER ----------

@persistent
def update_axis_properties(scene):
    global last_selected_object
    obj = scene.view_layers[0].objects.active
    if obj and obj != last_selected_object and obj.select_get() and obj.type == 'MESH':
        props = scene.grid_sorter_props
        props.align_x = obj.location.x
        props.align_y = obj.location.y
        props.align_z = obj.location.z
        last_selected_object = obj


# ---------- REGISTER ----------

classes = (
    GRIDSORTER_OT_arrange_grid,
    ALIGN_OT_axis,
    MOVE_OT_axis,
    GRIDSORTER_PT_panel,
    GRIDSORTER_Properties,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.grid_sorter_props = PointerProperty(type=GRIDSORTER_Properties)
    bpy.app.handlers.depsgraph_update_post.append(update_axis_properties)

def unregister():
    bpy.app.handlers.depsgraph_update_post.remove(update_axis_properties)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.grid_sorter_props

if __name__ == "__main__":
    register()
