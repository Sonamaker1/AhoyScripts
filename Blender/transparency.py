bl_info = {
    "name": "Viewport Transparency Toggle",
    "author": "Your Name",
    "version": (1, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Transparency",
    "description": "Toggle semi-transparency for selected object",
    "category": "3D View",
}

import bpy

class TRANSPARENCY_OT_enable_viewport(bpy.types.Operator):
    bl_idname = "object.enable_viewport_transparency"
    bl_label = "Enable Viewport Transparency"
    bl_description = "Set up the selected object for semi-transparency in viewport"
    bl_options = {'REGISTER', 'UNDO'}

    alpha_value: bpy.props.FloatProperty(
        name="Alpha",
        description="Transparency level",
        default=0.5,
        min=0.0,
        max=1.0
    )

    def execute(self, context):
        obj = context.object
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "Please select a mesh object")
            return {'CANCELLED'}

        # Ensure the object has a material
        if not obj.data.materials:
            mat = bpy.data.materials.new(name="TransparentMaterial")
            obj.data.materials.append(mat)
        else:
            mat = obj.active_material

        # Enable transparency in material settings
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Alpha"].default_value = self.alpha_value

        # Set blend mode for transparency
        mat.blend_method = 'BLEND'
        mat.shadow_method = 'NONE'
        mat.show_transparent_back = False

        # Set viewport display alpha
        mat.diffuse_color[3] = self.alpha_value

        self.report({'INFO'}, f"Transparency set to {self.alpha_value}")
        return {'FINISHED'}

class TRANSPARENCY_PT_panel(bpy.types.Panel):
    bl_label = "Transparency"
    bl_idname = "TRANSPARENCY_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Transparency"

    def draw(self, context):
        layout = self.layout
        layout.label(text="Make Object Transparent:")
        layout.operator("object.enable_viewport_transparency")

# Register
classes = [
    TRANSPARENCY_OT_enable_viewport,
    TRANSPARENCY_PT_panel,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
