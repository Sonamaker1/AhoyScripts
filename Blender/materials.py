bl_info = {
    "name": "Material Tools Panel",
    "author": "Your Name",
    "version": (1, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Material Tools",
    "description": "Copy and duplicate materials with options",
    "category": "Material",
}

import bpy

# Property group for name input
class MATERIALTOOLS_Properties(bpy.types.PropertyGroup):
    new_material_name: bpy.props.StringProperty(
        name="New Material Name",
        description="Name for duplicated material",
        default="DuplicatedMaterial"
    )

# Operator to copy materials from active to selected
class MATERIALTOOLS_OT_copy_materials(bpy.types.Operator):
    bl_idname = "material.copy_materials"
    bl_label = "Copy Materials to Selected"
    bl_description = "Copy all materials from active object to selected objects"

    def execute(self, context):
        active = context.active_object
        selected = [obj for obj in context.selected_objects if obj != active]

        if not active or not active.data.materials:
            self.report({'WARNING'}, "Active object has no materials")
            return {'CANCELLED'}

        for obj in selected:
            if obj.type == 'MESH':
                obj.data.materials.clear()
                for mat in active.data.materials:
                    obj.data.materials.append(mat)
        self.report({'INFO'}, "Materials copied to selected objects")
        return {'FINISHED'}

# Operator to duplicate active material
class MATERIALTOOLS_OT_duplicate_material(bpy.types.Operator):
    bl_idname = "material.duplicate_material"
    bl_label = "Duplicate Active Material"
    bl_description = "Duplicate the active material and assign it to the active object"

    def execute(self, context):
        props = context.scene.material_tools_props
        obj = context.object

        if not obj or not obj.active_material:
            self.report({'WARNING'}, "No active material to duplicate")
            return {'CANCELLED'}

        original = obj.active_material
        new_mat = original.copy()
        new_mat.name = props.new_material_name

        obj.active_material = new_mat

        self.report({'INFO'}, f"Material duplicated as '{new_mat.name}'")
        return {'FINISHED'}

# UI Panel
class MATERIALTOOLS_PT_panel(bpy.types.Panel):
    bl_label = "Material Tools"
    bl_idname = "MATERIALTOOLS_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Material Tools"

    def draw(self, context):
        layout = self.layout
        props = context.scene.material_tools_props

        layout.label(text="Copy Materials:")
        layout.operator("material.copy_materials")

        layout.separator()
        layout.label(text="Duplicate Material:")
        layout.prop(props, "new_material_name")
        layout.operator("material.duplicate_material")

# Registration
classes = (
    MATERIALTOOLS_Properties,
    MATERIALTOOLS_OT_copy_materials,
    MATERIALTOOLS_OT_duplicate_material,
    MATERIALTOOLS_PT_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.material_tools_props = bpy.props.PointerProperty(type=MATERIALTOOLS_Properties)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.material_tools_props

if __name__ == "__main__":
    register()
