bl_info = {
    "name": "Viewport Render 2048x2048 Fit Selection",
    "author": "ChatGPT + Sonamaker Q",
    "version": (1, 0),
    "blender": (4, 0, 0),
    "location": "View3D > View",
    "description": "Renders the current viewport, scaling selected geometry to 2048x2048 image",
    "category": "3D View",
}

import bpy
import mathutils

def get_selection_bounds(context):
    objs = [obj for obj in context.selected_objects if obj.type == 'MESH']
    if not objs:
        return None

    min_bound = mathutils.Vector((float('inf'), float('inf'), float('inf')))
    max_bound = mathutils.Vector((float('-inf'), float('-inf'), float('-inf')))

    for obj in objs:
        for v in obj.bound_box:
            world_v = obj.matrix_world @ mathutils.Vector(v)
            min_bound = mathutils.Vector(map(min, min_bound, world_v))
            max_bound = mathutils.Vector(map(max, max_bound, world_v))

    return min_bound, max_bound

def fit_camera_to_bounds(camera, bounds_min, bounds_max):
    # Center point
    center = (bounds_min + bounds_max) / 2
    size = bounds_max - bounds_min

    # Set camera position for top-down view
    camera.location = (center.x, center.y, center.z + 10)
    camera.rotation_euler = (0, 0, 0)

    # Orthographic scale needs to cover the larger dimension
    ortho_scale = max(size.x, size.y) * 0.5
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = ortho_scale * 2  # Full width/height

def set_render_settings():
    render = bpy.context.scene.render
    render.resolution_x = 2048
    render.resolution_y = 2048
    render.resolution_percentage = 100

class VIEW3D_OT_render_selection_to_2048(bpy.types.Operator):
    """Render selected geometry to 2048x2048 image"""
    bl_idname = "view3d.render_selection_2048"
    bl_label = "Render Selection (2048x2048)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bounds = get_selection_bounds(context)
        if not bounds:
            self.report({'ERROR'}, "No mesh objects selected")
            return {'CANCELLED'}

        scene = context.scene
        cam = scene.camera
        if not cam:
            self.report({'ERROR'}, "No camera found in scene")
            return {'CANCELLED'}

        fit_camera_to_bounds(cam, *bounds)
        set_render_settings()

        # Ensure camera view is active
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                override = context.copy()
                override['area'] = area
                override['region'] = area.regions[-1]
                bpy.ops.view3d.view_camera(override)
                break

        bpy.ops.view3d.viewport_render_image()
        return {'FINISHED'}

def draw_menu(self, context):
    self.layout.separator()
    self.layout.operator(VIEW3D_OT_render_selection_to_2048.bl_idname)

classes = (VIEW3D_OT_render_selection_to_2048,)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.VIEW3D_MT_view.append(draw_menu)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    bpy.types.VIEW3D_MT_view.remove(draw_menu)

if __name__ == "__main__":
    register()
