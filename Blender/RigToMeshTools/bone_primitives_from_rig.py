bl_info = {
    "name": "Bone Primitives From Rig",
    "author": "ChatGPT",
    "version": (0, 1, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > Rig Tools > Bone Primitives",
    "description": "Generate one primitive object per bone aligned to bone direction (box or ellipsoid).",
    "category": "Object",
}

import bpy
import bmesh
from mathutils import Matrix


def ensure_collection(name: str, parent_collection: bpy.types.Collection) -> bpy.types.Collection:
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        parent_collection.children.link(col)
    return col


def make_unit_cube_mesh(mesh_name: str) -> bpy.types.Mesh:
    mesh = bpy.data.meshes.get(mesh_name)
    if mesh:
        return mesh

    mesh = bpy.data.meshes.new(mesh_name)
    bm = bmesh.new()
    # Default cube from -1..1 (size 2), centered at origin.
    bmesh.ops.create_cube(bm, size=2.0)
    bm.to_mesh(mesh)
    mesh.update()
    bm.free()
    return mesh


def make_unit_uv_sphere_mesh(mesh_name: str, u_segments=24, v_segments=16) -> bpy.types.Mesh:
    mesh = bpy.data.meshes.get(mesh_name)
    if mesh:
        return mesh

    mesh = bpy.data.meshes.new(mesh_name)
    bm = bmesh.new()
    # radius=1 => diameter 2, centered at origin.
    bmesh.ops.create_uvsphere(bm, u_segments=u_segments, v_segments=v_segments, radius=1.0)
    bm.to_mesh(mesh)
    mesh.update()
    bm.free()
    return mesh


def bone_matrix_armature_space(arm_obj: bpy.types.Object, bone_name: str, use_pose: bool) -> Matrix:
    """
    Returns the bone transform in ARMATURE OBJECT SPACE.
    - pose_bone.matrix is in object space for the armature object (armature space). :contentReference[oaicite:2]{index=2}
    - bone.matrix_local is rest pose in armature space. :contentReference[oaicite:3]{index=3}
    """
    if use_pose:
        pb = arm_obj.pose.bones.get(bone_name)
        if pb is None:
            return Matrix.Identity(4)
        return pb.matrix.copy()
    else:
        b = arm_obj.data.bones.get(bone_name)
        if b is None:
            return Matrix.Identity(4)
        return b.matrix_local.copy()


def bone_length(arm_obj: bpy.types.Object, bone_name: str) -> float:
    b = arm_obj.data.bones.get(bone_name)
    return float(b.length) if b else 0.0


class BONEPRIMS_Props(bpy.types.PropertyGroup):
    shape: bpy.props.EnumProperty(
        name="Shape",
        items=[
            ("BOX", "Box", "Rectangular prism aligned to the bone"),
            ("ELLIPSOID", "Ellipsoid", "Stretched UV sphere aligned to the bone"),
        ],
        default="BOX",
    )

    use_pose: bpy.props.BoolProperty(
        name="Use Current Pose",
        description="Align to current pose (PoseBone.matrix). If off, use rest pose (Bone.matrix_local).",
        default=True,
    )

    only_selected: bpy.props.BoolProperty(
        name="Only Selected Bones",
        default=False,
    )

    deform_only: bpy.props.BoolProperty(
        name="Deform Bones Only",
        description="Only generate for bones with Deform enabled (useful for Rigify control rigs).",
        default=True,
    )

    thickness_ratio: bpy.props.FloatProperty(
        name="Thickness Ratio",
        description="Thickness as a ratio of bone length",
        default=0.18,
        min=0.001,
        soft_max=1.0,
    )

    min_thickness: bpy.props.FloatProperty(
        name="Min Thickness",
        default=0.01,
        min=0.0,
    )

    collection_name: bpy.props.StringProperty(
        name="Collection",
        default="BonePrimitives",
    )

    name_prefix: bpy.props.StringProperty(
        name="Name Prefix",
        default="BP_",
    )

    clear_existing: bpy.props.BoolProperty(
        name="Clear Existing",
        description="Delete previously generated objects in the target collection before generating new ones",
        default=True,
    )

    bone_parent: bpy.props.BoolProperty(
        name="Bone Parent",
        description="Parent each primitive to its bone so it follows animation automatically",
        default=True,
    )


class OBJECT_OT_generate_bone_primitives(bpy.types.Operator):
    bl_idname = "object.generate_bone_primitives"
    bl_label = "Generate Bone Primitives"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj is not None and obj.type == 'ARMATURE'

    def execute(self, context):
        generated = []

        arm = context.object
        props = context.scene.boneprims_props

        # Target collection
        root_col = context.scene.collection
        tgt_col = ensure_collection(props.collection_name, root_col)

        if props.clear_existing:
            # Delete objects in that collection that match our prefix
            to_remove = [o for o in list(tgt_col.objects) if o.name.startswith(props.name_prefix)]
            for o in to_remove:
                # Unlink from all collections then remove datablock
                for c in list(o.users_collection):
                    c.objects.unlink(o)
                bpy.data.objects.remove(o, do_unlink=True)

        # Base meshes (reused by many objects)
        cube_mesh = make_unit_cube_mesh(f"{props.collection_name}_UNIT_CUBE")
        sphere_mesh = make_unit_uv_sphere_mesh(f"{props.collection_name}_UNIT_SPHERE")

        if props.only_selected:
            if context.mode == 'POSE':
                bone_names = [b.name for b in context.selected_pose_bones] if context.selected_pose_bones else []
            else:
                # Fallback: selected bones not available unless in pose/edit; use all.
                bone_names = [b.name for b in arm.data.bones]
        else:
            bone_names = [b.name for b in arm.data.bones]

        # Filter deform-only (helpful for Rigify: avoid control bones)
        if props.deform_only:
            bone_names = [n for n in bone_names if arm.data.bones[n].use_deform]

        if not bone_names:
            self.report({'WARNING'}, "No bones found to generate from.")
            return {'CANCELLED'}

        for bn in bone_names:
            L = bone_length(arm, bn)
            if L <= 1e-8:
                continue

            thickness = max(props.min_thickness, L * props.thickness_ratio)

            base_mesh = cube_mesh if props.shape == "BOX" else sphere_mesh

            obj = bpy.data.objects.new(f"{props.name_prefix}{bn}", base_mesh)
            tgt_col.objects.link(obj)

            # IMPORTANT: make the mesh unique per object (vertex weights are stored on the mesh datablock)
            obj.data = base_mesh.copy()
            obj.data.name = f"{obj.name}_MESH"

            # Vertex group named the same as the object, and assign ALL vertices
            vg = obj.vertex_groups.new(name=obj.name)
            all_vidx = list(range(len(obj.data.vertices)))
            if all_vidx:
                vg.add(all_vidx, 1.0, 'REPLACE')

            generated.append(obj)

            # Align object axes to the bone axes.
            bone_mat = bone_matrix_armature_space(arm, bn, props.use_pose)

            # We want the primitive centered along the bone (bone head -> tail along +Y).
            # Since our primitive is centered at origin, translate it +Y by L/2 in bone space.
            local_offset = Matrix.Translation((0.0, L * 0.5, 0.0))

            # Bone parenting so it follows animation:
            if props.bone_parent:
                obj.parent = arm
                obj.parent_type = 'BONE'
                obj.parent_bone = bn

                # Make the child inherit bone transform directly, then apply our local offset in bone space.
                # A common reliable setup is identity parent inverse + basis holding the desired offset. :contentReference[oaicite:4]{index=4}
                local_offset = Matrix.Translation((0.0, -L * 0.5, 0.0))
                obj.matrix_parent_inverse = Matrix.Identity(4)
                obj.matrix_basis = local_offset
            else:
                # No parenting: place in world space directly using the bone matrix.
                obj.matrix_world = arm.matrix_world @ bone_mat @ local_offset

            # Scale: base cube/sphere is diameter 2, so scale is half the desired dimensions.
            # Bone length along Y.
            obj.scale.x = thickness * 0.5
            obj.scale.y = L * 0.5
            obj.scale.z = thickness * 0.5

            # If not bone-parenting, also rotate/position fully by setting world matrix.
            # If bone-parenting, rotation is handled by parenting relationship itself.

            # For bone-parenting, ensure the object’s orientation is aligned to the bone:
            # Put rotation into parent relationship by setting the child's local rotation to identity
            # and relying on bone parent to supply orientation.
            obj.rotation_mode = 'QUATERNION'
            obj.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
        
        # Apply transforms to generated objects (bake loc/rot/scale into mesh)
        prev_active = context.view_layer.objects.active
        prev_selected = [o for o in context.selected_objects]

        # Deselect everything
        for o in prev_selected:
            o.select_set(False)

        for o in generated:
            if o.name not in context.view_layer.objects:
                continue
            o.select_set(True)
            context.view_layer.objects.active = o
            # Ensure we're in Object Mode for transform_apply
            if context.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
            o.select_set(False)

        # Restore selection/active
        for o in prev_selected:
            if o and o.name in context.view_layer.objects:
                o.select_set(True)
        context.view_layer.objects.active = prev_active

        return {'FINISHED'}


class VIEW3D_PT_bone_primitives_panel(bpy.types.Panel):
    bl_label = "Bone Primitives"
    bl_idname = "VIEW3D_PT_bone_primitives_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Rig Tools"

    def draw(self, context):
        layout = self.layout
        props = context.scene.boneprims_props

        layout.label(text="Generate one primitive per bone")
        col = layout.column(align=True)
        col.prop(props, "shape")
        col.prop(props, "use_pose")
        col.prop(props, "only_selected")
        col.prop(props, "deform_only")
        col.separator()
        col.prop(props, "thickness_ratio")
        col.prop(props, "min_thickness")
        col.separator()
        col.prop(props, "collection_name")
        col.prop(props, "name_prefix")
        col.prop(props, "clear_existing")
        col.prop(props, "bone_parent")
        col.separator()
        col.operator("object.generate_bone_primitives", icon="OUTLINER_OB_MESH")


classes = (
    BONEPRIMS_Props,
    OBJECT_OT_generate_bone_primitives,
    VIEW3D_PT_bone_primitives_panel,
)


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.boneprims_props = bpy.props.PointerProperty(type=BONEPRIMS_Props)


def unregister():
    del bpy.types.Scene.boneprims_props
    for c in reversed(classes):
        bpy.utils.unregister_class(c)


if __name__ == "__main__":
    register()
