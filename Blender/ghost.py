bl_info = {
    "name": "Ghost Object Tool",
    "author": "Your Name",
    "version": (1, 0),
    "blender": (2, 93, 0),
    "blender": (3, 0, 0),
    "location": "3D View > Sidebar > Ghost Tools",
    "description": "Makes selected objects 'ghosted' (unselectable but visible)",
    "category": "Object",
}

import bpy

def ghost_object(obj):
    obj.hide_select = True
    obj.display_type = 'WIRE'  # Optional: you can use 'SOLID' + transparency
    obj.show_in_front = True   # Draw on top of other objects

def unghost_object(obj):
    obj.hide_select = False
    obj.display_type = 'TEXTURED'
    obj.show_in_front = False

class OBJECT_OT_ghost(bpy.types.Operator):
    bl_idname = "object.make_ghost"
    bl_label = "Ghost Selected Object(s)"
    bl_description = "Makes selected object(s) visible but unselectable in viewport"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        for obj in context.selected_objects:
            ghost_object(obj)
        return {'FINISHED'}

class OBJECT_OT_unghost(bpy.types.Operator):
    bl_idname = "object.undo_ghost"
    bl_label = "Un-Ghost Selected Object(s)"
    bl_description = "Restores object(s) to normal visibility and selectability"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        for obj in context.selected_objects:
            unghost_object(obj)
        return {'FINISHED'}

class GHOST_PT_panel(bpy.types.Panel):
    bl_label = "Ghost Tools"
    bl_idname = "GHOST_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Ghost'

    def draw(self, context):
        layout = self.layout
        layout.label(text="Ghost Object Visibility")
        layout.operator("object.make_ghost", icon='HIDE_OFF')
        layout.operator("object.undo_ghost", icon='HIDE_ON')


classes = [
    OBJECT_OT_ghost,
    OBJECT_OT_unghost,
    GHOST_PT_panel,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
