bl_info = {
    "name": "Grid Sorter and Axis Aligner",
    "author": "Your Name",
    "version": (1, 2),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Grid Sorter",
    "description": "Arrange selected objects in a grid and align to axis values",
    "category": "Object",
}

import bpy
from bpy.props import IntProperty, FloatProperty

# -------- GRID ARRANGER --------

class GRIDSORTER_OT_arrange_grid(bpy.types.Operator):
    bl_idname = "object.arrange_objects_grid_xz"
    bl_label = "Arrange in Grid (X/Z)"
    bl_description = "Arrange selected objects alphabetically in a grid using X and Z axes"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.grid_sorter_props
        per_row = props.per_row
        spacing = props.spacing

        if per_row < 1:
            self.report({'WARNING'}, "Objects per row must be at least 1")
            return {'CANCELLED'}

        selected = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not selected:
            self.report({'WARNING'}, "No mesh objects selected")
            return {'CANCELLED'}

        selected.sort(key=lambda o: o.name.lower())

        for i, obj in enumerate(selected):
            row = i // per_row
            col = i % per_row
            obj.location.x = col * spacing
            obj.location.z = -row * spacing

        self.report({'INFO'}, f"Arranged {len(selected)} objects in X/Z grid")
        return {'FINISHED'}

# -------- AXIS ALIGNERS --------

class ALIGN_OT_axis(bpy.types.Operator):
    bl_idname = "object.align_objects_axis"
    bl_label = "Align Objects to Axis"
    bl_options = {'REGISTER', 'UNDO'}

    axis: bpy.props.EnumProperty(
        items=[
            ('X', "X Axis", ""),
            ('Y', "Y Axis", ""),
            ('Z', "Z Axis", "")
        ]
    )

    def execute(self, context):
        props = context.scene.grid_sorter_props
        value = {
            'X': props.align_x,
            'Y': props.align_y,
            'Z': props.align_z
        }[self.axis]

        for obj in context.selected_objects:
            if obj.type == 'MESH':
                setattr(obj.location, self.axis.lower(), value)

        self.report({'INFO'}, f"Aligned to {self.axis} = {value}")
        return {'FINISHED'}

# -------- PANEL UI --------

class GRIDSORTER_PT_panel(bpy.types.Panel):
    bl_label = "Grid Sorter + Axis Aligner"
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

        # Axis align section
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

# -------- PROPERTIES --------

class GRIDSORTER_Properties(bpy.types.PropertyGroup):
    per_row: IntProperty(
        name="Objects per Row",
        default=5,
        min=1,
        description="Number of objects per row"
    )
    spacing: IntProperty(
        name="Grid Spacing",
        default=3,
        min=1,
        description="Space between objects"
    )

    align_x: FloatProperty(name="X", default=0.0)
    align_y: FloatProperty(name="Y", default=0.0)
    align_z: FloatProperty(name="Z", default=0.0)

# -------- REGISTER --------

classes = (
    GRIDSORTER_OT_arrange_grid,
    ALIGN_OT_axis,
    GRIDSORTER_PT_panel,
    GRIDSORTER_Properties,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.grid_sorter_props = bpy.props.PointerProperty(type=GRIDSORTER_Properties)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.grid_sorter_props

if __name__ == "__main__":
    register()
