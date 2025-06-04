bl_info = {
    "name": "Grid Sorter XZ",
    "author": "Your Name",
    "version": (1, 1),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Grid Sorter",
    "description": "Arrange selected objects alphabetically in a grid (X and Z axis)",
    "category": "Object",
}

import bpy
from bpy.props import IntProperty

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

        # Sort alphabetically
        selected.sort(key=lambda o: o.name.lower())

        for i, obj in enumerate(selected):
            row = i // per_row
            col = i % per_row
            obj.location.x = col * spacing
            obj.location.z = -row * spacing  # Negative Z to move "downward"
        self.report({'INFO'}, f"Arranged {len(selected)} objects in grid (X/Z)")
        return {'FINISHED'}

class GRIDSORTER_PT_panel(bpy.types.Panel):
    bl_label = "Grid Sorter (X/Z)"
    bl_idname = "GRIDSORTER_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Grid Sorter'

    def draw(self, context):
        layout = self.layout
        props = context.scene.grid_sorter_props

        layout.prop(props, "per_row")
        layout.prop(props, "spacing")
        layout.operator("object.arrange_objects_grid_xz")

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

classes = (
    GRIDSORTER_OT_arrange_grid,
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
