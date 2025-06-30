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
        bpy.ops.object.mode_set(mode=self.mode)
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


class CHARANIM_OT_ClearKeyframes(bpy.types.Operator):
    bl_idname = "charanim.clear_keyframes"
    bl_label = "Clear All Keyframes"

    def execute(self, context):
        obj = context.object
        if obj and obj.animation_data and obj.animation_data.action:
            for fcurve in obj.animation_data.action.fcurves:
                obj.animation_data.action.fcurves.remove(fcurve)
            self.report({'INFO'}, "All keyframes removed.")
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


class CHARANIM_OT_CopyPose(bpy.types.Operator):
    bl_idname = "charanim.copy_pose"
    bl_label = "Copy Pose Keyframe"

    def execute(self, context):
        obj = context.object
        if obj is None or obj.type != 'ARMATURE' or obj.mode != 'POSE':
            self.report({'ERROR'}, "Must be in Pose Mode with an Armature selected.")
            return {'CANCELLED'}

        buffer = {}
        for bone in obj.pose.bones:
            buffer[bone.name] = {
                "location": tuple(bone.location),
                "rotation_quaternion": tuple(bone.rotation_quaternion),
                "scale": tuple(bone.scale),
            }

        context.scene.charanim_pose_buffer = buffer
        self.report({'INFO'}, f"Copied pose of {len(buffer)} bones.")
        return {'FINISHED'}


class CHARANIM_OT_PastePose(bpy.types.Operator):
    bl_idname = "charanim.paste_pose"
    bl_label = "Paste Pose Keyframe"

    def execute(self, context):
        obj = context.object
        if obj is None or obj.type != 'ARMATURE' or obj.mode != 'POSE':
            self.report({'ERROR'}, "Must be in Pose Mode with an Armature selected.")
            return {'CANCELLED'}

        buffer = context.scene.charanim_pose_buffer
        if not buffer:
            self.report({'ERROR'}, "No pose copied yet.")
            return {'CANCELLED'}

        current_frame = context.scene.frame_current

        for bone in obj.pose.bones:
            if bone.name in buffer:
                pose_data = buffer[bone.name]
                bone.location = pose_data["location"]
                bone.rotation_quaternion = pose_data["rotation_quaternion"]
                bone.scale = pose_data["scale"]

                bone.keyframe_insert(data_path="location", frame=current_frame)
                bone.keyframe_insert(data_path="rotation_quaternion", frame=current_frame)
                bone.keyframe_insert(data_path="scale", frame=current_frame)

        self.report({'INFO'}, f"Pasted pose to frame {current_frame}.")
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
        col.operator("charanim.clear_keyframes", text="Remove All Keyframes")

        col.separator()
        col.label(text="Step 5b: Copy & Paste Poses")
        col.operator("charanim.copy_pose", text="Copy Pose Keyframe")
        col.operator("charanim.paste_pose", text="Paste Pose Keyframe")


# --- Registration ---

classes = (
    CHARANIM_OT_SetMode,
    CHARANIM_OT_CreateAction,
    CHARANIM_OT_ClearKeyframes,
    CHARANIM_OT_ApplyBoneTransform,
    CHARANIM_OT_CopyPose,
    CHARANIM_OT_PastePose,
    CHARANIM_PT_MainPanel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.charanim_offset_x = FloatProperty(name="X Offset", default=0.0)
    bpy.types.Scene.charanim_offset_y = FloatProperty(name="Y Offset", default=0.0)
    bpy.types.Scene.charanim_offset_z = FloatProperty(name="Z Offset", default=0.0)
    bpy.types.Scene.charanim_mirror = BoolProperty(name="Mirror Second Bone", default=False)
    bpy.types.Scene.charanim_pose_buffer = {}


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.charanim_offset_x
    del bpy.types.Scene.charanim_offset_y
    del bpy.types.Scene.charanim_offset_z
    del bpy.types.Scene.charanim_mirror
    del bpy.types.Scene.charanim_pose_buffer


if __name__ == "__main__":
    register()
