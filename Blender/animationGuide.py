bl_info = {
    "name": "Character Animation Guide",
    "blender": (4, 0, 0),
    "category": "Animation",
}

import bpy
from bpy.props import FloatProperty, BoolProperty


# --- Operators ---

class CHARANIM_OT_SetMode(bpy.types.Operator):
    bl_idname = "charanim.set_mode"
    bl_label = "Set Mode"
    mode: bpy.props.StringProperty()

    def execute(self, context):
        obj = context.object

        if not obj:
            self.report({'ERROR'}, "No object selected.")
            return {'CANCELLED'}

        # Unhide and select the armature if necessary
        obj.hide_set(False)
        obj.hide_viewport = False
        obj.hide_select = False

        if obj.type == 'ARMATURE':
            context.view_layer.objects.active = obj
            obj.select_set(True)

        try:
            bpy.ops.object.mode_set(mode=self.mode)
        except RuntimeError as e:
            self.report({'ERROR'}, f"Could not switch mode: {e}")
            return {'CANCELLED'}

        return {'FINISHED'}



class CHARANIM_OT_CreateAction(bpy.types.Operator):
    bl_idname = "charanim.create_action"
    bl_label = "Create Animation"

    def execute(self, context):
        obj = context.object
        if obj.type == 'ARMATURE':
            obj.animation_data_create()
            new_action = bpy.data.actions.new(name="NewAction")
            obj.animation_data.action = new_action
            self.report({'INFO'}, "New action created and assigned")
        return {'FINISHED'}


class CHARANIM_OT_ApplyBoneTransform(bpy.types.Operator):
    bl_idname = "charanim.apply_bone_transform"
    bl_label = "Apply Bone Transform"

    offset_x: FloatProperty(name="X Offset")
    offset_y: FloatProperty(name="Y Offset")
    offset_z: FloatProperty(name="Z Offset")
    mirror: BoolProperty(name="Mirror Second Bone", default=False)

    def execute(self, context):
        obj = context.object
        if obj is None or obj.mode != 'POSE':
            self.report({'ERROR'}, "Select an armature in Pose Mode.")
            return {'CANCELLED'}

        selected_bones = context.selected_pose_bones
        if not selected_bones:
            self.report({'ERROR'}, "No bones selected.")
            return {'CANCELLED'}

        if len(selected_bones) > 2:
            self.report({'WARNING'}, "Only first two selected bones will be affected.")

        for i, bone in enumerate(selected_bones[:2]):
            mirror_factor = -1 if self.mirror and i == 1 else 1
            bone.location.x += self.offset_x * mirror_factor
            bone.location.y += self.offset_y * mirror_factor
            bone.location.z += self.offset_z * mirror_factor

        self.report({'INFO'}, "Transforms applied.")
        return {'FINISHED'}


class CHARANIM_OT_RemoveKeyframeCurrent(bpy.types.Operator):
    bl_idname = "charanim.remove_current_keyframe"
    bl_label = "Remove Keyframe (Current Frame)"

    def execute(self, context):
        obj = context.object
        if obj is None or obj.type != 'ARMATURE' or obj.mode != 'POSE':
            self.report({'ERROR'}, "Must be in Pose Mode with an armature.")
            return {'CANCELLED'}

        frame = context.scene.frame_current
        for bone in obj.pose.bones:
            bone.keyframe_delete(data_path="location", frame=frame)
            bone.keyframe_delete(data_path="rotation_quaternion", frame=frame)
            bone.keyframe_delete(data_path="scale", frame=frame)

        self.report({'INFO'}, f"Removed keyframes at frame {frame}.")
        return {'FINISHED'}


class CHARANIM_OT_CopyKeyframeCurrent(bpy.types.Operator):
    bl_idname = "charanim.copy_current_keyframe"
    bl_label = "Copy Keyframe (Current Frame)"

    def execute(self, context):
        obj = context.object
        if obj is None or obj.type != 'ARMATURE' or obj.mode != 'POSE':
            self.report({'ERROR'}, "Must be in Pose Mode with an armature.")
            return {'CANCELLED'}

        buffer = {}
        for bone in obj.pose.bones:
            buffer[bone.name] = {
                "location": tuple(bone.location),
                "rotation_quaternion": tuple(bone.rotation_quaternion),
                "scale": tuple(bone.scale),
            }

        context.scene.charanim_copied_keyframe = buffer
        self.report({'INFO'}, "Copied current keyframe pose.")
        return {'FINISHED'}


class CHARANIM_OT_PasteCopiedKeyframe(bpy.types.Operator):
    bl_idname = "charanim.paste_copied_keyframe"
    bl_label = "Paste Copied Keyframe"

    def execute(self, context):
        obj = context.object
        if obj is None or obj.type != 'ARMATURE' or obj.mode != 'POSE':
            self.report({'ERROR'}, "Must be in Pose Mode with an armature.")
            return {'CANCELLED'}

        buffer = context.scene.charanim_copied_keyframe
        if not buffer:
            self.report({'ERROR'}, "No copied keyframe found.")
            return {'CANCELLED'}

        frame = context.scene.frame_current
        for bone in obj.pose.bones:
            if bone.name in buffer:
                pose = buffer[bone.name]
                bone.location = pose["location"]
                bone.rotation_quaternion = pose["rotation_quaternion"]
                bone.scale = pose["scale"]
                bone.keyframe_insert(data_path="location", frame=frame)
                bone.keyframe_insert(data_path="rotation_quaternion", frame=frame)
                bone.keyframe_insert(data_path="scale", frame=frame)

        self.report({'INFO'}, f"Pasted copied keyframe to frame {frame}.")
        return {'FINISHED'}


# --- UI Panel ---

class CHARANIM_PT_MainPanel(bpy.types.Panel):
    bl_label = "Character Animation Workflow"
    bl_idname = "CHARANIM_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'CharAnim'

    def draw(self, context):
        layout = self.layout
        col = layout.column()

        col.label(text="Step 1: Adjust Rig")
        col.operator("charanim.set_mode", text="Object Mode").mode = 'OBJECT'
        col.operator("charanim.set_mode", text="Pose Mode").mode = 'POSE'

        col.separator()
        col.label(text="Step 2: Create Animation")
        col.operator("charanim.create_action", text="New Animation Action")

        col.separator()
        col.label(text="Step 3: Select/Edit Animation")
        if context.object and context.object.animation_data:
            col.prop_search(context.object.animation_data, "action", bpy.data, "actions", text="Action")

        col.separator()
        col.label(text="Step 4: Bone Transform Tools")

        box = col.box()
        box.label(text="Transform Selected Bone(s):")
        box.prop(context.scene, "charanim_offset_x")
        box.prop(context.scene, "charanim_offset_y")
        box.prop(context.scene, "charanim_offset_z")
        box.prop(context.scene, "charanim_mirror")

        op = box.operator("charanim.apply_bone_transform", text="Apply Transform")
        op.offset_x = context.scene.charanim_offset_x
        op.offset_y = context.scene.charanim_offset_y
        op.offset_z = context.scene.charanim_offset_z
        op.mirror = context.scene.charanim_mirror

        col.separator()
        col.label(text="Step 5: Animate")
        col.operator("screen.animation_play", text="Play")

        col.separator()
        col.label(text="Step 5b: Keyframe Controls")
        col.operator("charanim.copy_current_keyframe", text="Copy Current Keyframe")
        col.operator("charanim.paste_copied_keyframe", text="Paste Copied Keyframe")
        col.operator("charanim.remove_current_keyframe", text="Remove Current Keyframe")


# --- Registration ---

classes = (
    CHARANIM_OT_SetMode,
    CHARANIM_OT_CreateAction,
    CHARANIM_OT_ApplyBoneTransform,
    CHARANIM_OT_RemoveKeyframeCurrent,
    CHARANIM_OT_CopyKeyframeCurrent,
    CHARANIM_OT_PasteCopiedKeyframe,
    CHARANIM_PT_MainPanel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.charanim_offset_x = FloatProperty(name="X Offset", default=0.0)
    bpy.types.Scene.charanim_offset_y = FloatProperty(name="Y Offset", default=0.0)
    bpy.types.Scene.charanim_offset_z = FloatProperty(name="Z Offset", default=0.0)
    bpy.types.Scene.charanim_mirror = BoolProperty(name="Mirror Second Bone", default=False)
    bpy.types.Scene.charanim_copied_keyframe = {}


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.charanim_offset_x
    del bpy.types.Scene.charanim_offset_y
    del bpy.types.Scene.charanim_offset_z
    del bpy.types.Scene.charanim_mirror
    del bpy.types.Scene.charanim_copied_keyframe


if __name__ == "__main__":
    register()
