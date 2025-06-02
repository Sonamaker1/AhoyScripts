bl_info = {
    "name": "Viewport Background Color",
    "author": "Your Name",
    "version": (1, 0),
    "blender": (3, 0, 0),
    "location": "3D View > Sidebar > Viewport Color",
    "description": "Set 3D Viewport background color using hex or RGB",
    "category": "3D View",
}

import bpy
import re

def hex_to_rgb(hex_color):
    """Convert hex string (e.g. #ffaa33) to RGB float tuple (0-1)."""
    hex_color = hex_color.strip().lstrip('#')
    if len(hex_color) != 6 or not re.fullmatch(r'[0-9a-fA-F]{6}', hex_color):
        return None
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0
    return (r, g, b)

class VIEWPORTCOLOR_OT_set_from_hex(bpy.types.Operator):
    bl_idname = "view3d.set_viewport_color_hex"
    bl_label = "Set Background from Hex"
    bl_description = "Apply hex color to viewport background"
    
    def execute(self, context):
        prefs = context.scene.viewport_color_settings
        rgb = hex_to_rgb(prefs.bg_hex)
        if rgb is None:
            self.report({'ERROR'}, "Invalid hex format. Use #RRGGBB.")
            return {'CANCELLED'}

        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.shading.background_type = 'VIEWPORT'
                        space.shading.background_color = rgb
        return {'FINISHED'}

class VIEWPORTCOLOR_PT_panel(bpy.types.Panel):
    bl_label = "Viewport Background"
    bl_idname = "VIEWPORTCOLOR_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Viewport Color"

    def draw(self, context):
        layout = self.layout
        prefs = context.scene.viewport_color_settings

        layout.label(text="Set Color from Hex:")
        layout.prop(prefs, "bg_hex", text="Hex")
        layout.operator("view3d.set_viewport_color_hex")

        layout.separator()
        layout.label(text="Or Pick RGB:")
        layout.prop(prefs, "bg_rgb", text="")
        layout.operator("view3d.set_viewport_color_rgb")

class VIEWPORTCOLOR_OT_set_from_rgb(bpy.types.Operator):
    bl_idname = "view3d.set_viewport_color_rgb"
    bl_label = "Set Background from RGB"
    bl_description = "Apply RGB color to viewport background"

    def execute(self, context):
        rgb = context.scene.viewport_color_settings.bg_rgb
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.shading.background_type = 'VIEWPORT'
                        space.shading.background_color = rgb
        return {'FINISHED'}

class VIEWPORTCOLOR_Settings(bpy.types.PropertyGroup):
    bg_hex: bpy.props.StringProperty(
        name="Hex Color",
        description="Hex color (e.g. #ff8800)",
        default="#ffffff",
        maxlen=7
    )

    bg_rgb: bpy.props.FloatVectorProperty(
        name="RGB",
        subtype='COLOR',
        size=3,
        min=0.0, max=1.0,
        default=(1.0, 1.0, 1.0)
    )

classes = (
    VIEWPORTCOLOR_PT_panel,
    VIEWPORTCOLOR_OT_set_from_hex,
    VIEWPORTCOLOR_OT_set_from_rgb,
    VIEWPORTCOLOR_Settings,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.viewport_color_settings = bpy.props.PointerProperty(type=VIEWPORTCOLOR_Settings)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.viewport_color_settings

if __name__ == "__main__":
    register()
