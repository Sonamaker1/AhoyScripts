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
from bpy.props import FloatProperty, PointerProperty, EnumProperty

class BoneTransformProperties(bpy.types.PropertyGroup):
    loc_x: FloatProperty(name="X", default=0.0)
    loc_y: FloatProperty(name="Y", default=0.0)
    loc_z: FloatProperty(name="Z", default=0.0)
    rot_x: FloatProperty(name="Rot X", default=0.0)
    rot_y: FloatProperty(name="Rot Y", default=0.0)
    rot_z: FloatProperty(name="Rot Z", default=0.0)

class ANIMPREVIEW_OT_load_bone_transform(bpy.types.Operator):
    bl_idname = "anim.load_bone_transform"
    bl_label = "Load Bone Transform"
    bl_description = "Load the current transform of the selected pose bone into the input fields"

    def execute(self, context):
        obj = context.object
        props = context.scene.bone_transform_props

        if not obj or obj.type != 'ARMATURE' or context.mode != 'POSE':
            self.report({'ERROR'}, "Must be in Pose Mode with an armature selected")
            return {'CANCELLED'}

        bone = context.active_pose_bone
        if not bone:
            self.report({'ERROR'}, "No active pose bone selected")
            return {'CANCELLED'}

        # Load location
        props.loc_x = bone.location.x
        props.loc_y = bone.location.y
        props.loc_z = bone.location.z

        # Load rotation (Euler)
        bone.rotation_mode = 'XYZ'
        euler = bone.rotation_euler
        props.rot_x = euler.x
        props.rot_y = euler.y
        props.rot_z = euler.z

        self.report({'INFO'}, f"Loaded transform from bone '{bone.name}'")
        return {'FINISHED'}


class ANIMPREVIEW_OT_set_bone_transform(bpy.types.Operator):
    bl_idname = "anim.set_bone_transform"
    bl_label = "Set Bone Transform"
    bl_description = "Set the location and rotation of the selected pose bone"

    def execute(self, context):
        obj = context.object
        props = context.scene.bone_transform_props

        if not obj or obj.type != 'ARMATURE' or context.mode != 'POSE':
            self.report({'ERROR'}, "Must be in Pose Mode with an armature selected")
            return {'CANCELLED'}

        bone = context.active_pose_bone
        if not bone:
            self.report({'ERROR'}, "No active pose bone selected")
            return {'CANCELLED'}

        # Apply location
        bone.location = (props.loc_x, props.loc_y, props.loc_z)

        # Apply rotation (Euler)
        bone.rotation_mode = 'XYZ'
        bone.rotation_euler = (props.rot_x, props.rot_y, props.rot_z)

        self.report({'INFO'}, f"Bone transform applied to '{bone.name}'")
        return {'FINISHED'}


class ANIMPREVIEW_OT_apply_transform_to_keyframe(bpy.types.Operator):
    bl_idname = "anim.apply_transform_to_keyframe"
    bl_label = "Apply Transform to Keyframe"
    bl_description = "Insert keyframes for the selected bones' current transform"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object

        if not obj or obj.type != 'ARMATURE' or context.mode != 'POSE':
            self.report({'ERROR'}, "Must be in Pose Mode with an armature selected")
            return {'CANCELLED'}

        action = obj.animation_data.action if obj.animation_data else None
        if not action:
            self.report({'ERROR'}, "No active animation/action found")
            return {'CANCELLED'}

        frame = context.scene.frame_current

        for bone in context.selected_pose_bones:
            bone_path = bone.name
            bone.keyframe_insert(data_path="location", frame=frame)
            bone.keyframe_insert(data_path="rotation_quaternion", frame=frame)
            bone.keyframe_insert(data_path="scale", frame=frame)

        self.report({'INFO'}, f"Transforms keyframed at frame {frame}")
        return {'FINISHED'}


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

class PREVIEW_OT_rest_pose(bpy.types.Operator):
    bl_idname = "anim.preview_rest_pose"
    bl_label = "Preview Rest Pose (No Animation)"
    bl_description = "Temporarily show the armature's neutral rest pose and stop any Action from driving it"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object

        if not obj or obj.type != 'ARMATURE':
            self.report({'WARNING'}, "Select an armature object.")
            return {'CANCELLED'}

        # Stop playback if playing
        if context.screen and context.screen.is_animation_playing:
            bpy.ops.screen.animation_play()

        # Ensure animation_data exists if we want to clear the action cleanly
        if obj.animation_data:
            obj.animation_data.action = None

        # Clear pose to match rest pose (neutral T/A pose of the rig)
        # Must be in pose mode for pose operators
        prev_mode = obj.mode
        try:
            bpy.ops.object.mode_set(mode='POSE')
            bpy.ops.pose.select_all(action='SELECT')
            bpy.ops.pose.transforms_clear()   # location/rotation/scale to default
        finally:
            # Go back to previous mode (nice UX)
            if prev_mode in {'OBJECT', 'POSE', 'EDIT'}:
                bpy.ops.object.mode_set(mode=prev_mode)

        # Force refresh (some rigs/drivers update cleaner with a frame nudge)
        scene = context.scene
        f = scene.frame_current
        scene.frame_set(f)
        # If you want an extra nudge:
        # scene.frame_set(f + 1)
        # scene.frame_set(f)

        self.report({'INFO'}, "Showing rest pose (no action).")
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

        if not obj:
            layout.label(text="Select an object")
            return

        layout.label(text="Preview:")
        layout.operator("anim.preview_rest_pose", icon='ARMATURE_DATA')  # NEW BUTTON

        if not obj.animation_data:
            layout.label(text="Select an animated object")
            return

        layout.separator()
        layout.label(text="Pose Tools:")
        layout.operator("anim.apply_transform_to_keyframe", icon='KEY_HLT')
        layout.operator("anim.load_bone_transform", icon='IMPORT')

        layout.label(text="Set Bone Transform:")

        col = layout.column(align=True)
        col.prop(context.scene.bone_transform_props, "loc_x")
        col.prop(context.scene.bone_transform_props, "loc_y")
        col.prop(context.scene.bone_transform_props, "loc_z")

        col = layout.column(align=True)
        col.prop(context.scene.bone_transform_props, "rot_x")
        col.prop(context.scene.bone_transform_props, "rot_y")
        col.prop(context.scene.bone_transform_props, "rot_z")

        layout.operator("anim.set_bone_transform", icon='CON_ROTLIKE')

        layout.separator()
        layout.label(text="Available Actions:")
        for action in bpy.data.actions:
            op = layout.operator("anim.preview_action", text=action.name)
            op.action_name = action.name


# Register
classes = [
    PREVIEW_OT_play_action,
    PREVIEW_OT_rest_pose,              # NEW
    PREVIEW_PT_action_panel,
    ANIMPREVIEW_OT_apply_transform_to_keyframe,
    BoneTransformProperties,
    ANIMPREVIEW_OT_set_bone_transform,
    ANIMPREVIEW_OT_load_bone_transform,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.bone_transform_props = bpy.props.PointerProperty(type=BoneTransformProperties)

def unregister():
    del bpy.types.Scene.bone_transform_props
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()

