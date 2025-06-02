bl_info = {
    "name": "Animation Preview Panel",
    "author": "Your Name",
    "version": (1, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Anim Preview",
    "description": "Preview animations by selecting from a list of Actions",
    "category": "Animation",
}

import bpy

class PREVIEW_OT_play_action(bpy.types.Operator):
    bl_idname = "anim.preview_action"
    bl_label = "Preview Action"
    bl_options = {'REGISTER', 'UNDO'}

    action_name: bpy.props.StringProperty()

    def execute(self, context):
        obj = context.object
        action = bpy.data.actions.get(self.action_name)

        if not obj or not obj.animation_data:
            self.report({'WARNING'}, "Select an object with animation data.")
            return {'CANCELLED'}
        
        if not action:
            self.report({'WARNING'}, f"Action '{self.action_name}' not found.")
            return {'CANCELLED'}

        obj.animation_data.action = action

        # Set frame range based on action
        if action.frame_range:
            context.scene.frame_start = int(action.frame_range[0])
            context.scene.frame_end = int(action.frame_range[1])
            context.scene.frame_current = int(action.frame_range[0])

        bpy.ops.screen.animation_play()
        return {'FINISHED'}

class PREVIEW_PT_action_panel(bpy.types.Panel):
    bl_label = "Animation Preview"
    bl_idname = "PREVIEW_PT_action_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Anim Preview"

    def draw(self, context):
        layout = self.layout
        obj = context.object

        if not obj or not obj.animation_data:
            layout.label(text="Select an animated object")
            return

        layout.label(text="Available Actions:")
        for action in bpy.data.actions:
            op = layout.operator("anim.preview_action", text=action.name)
            op.action_name = action.name

# Register
classes = [
    PREVIEW_OT_play_action,
    PREVIEW_PT_action_panel,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
