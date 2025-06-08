bl_info = {
    "name": "Ghost Object Tool",
    "author": "Your Name",
    "version": (1, 1),
    "blender": (3, 0, 0),
    "location": "3D View > Sidebar > Ghost Tools",
    "description": "Makes objects 'ghosted' (unselectable, transparent, selectable through)",
    "category": "Object",
}

import bpy
from bpy.props import FloatProperty, PointerProperty


# ---------- Ghosting Logic ----------

def ghost_object(obj):
    obj.hide_select = True
    obj.show_in_front = True   # Draw on top of other objects
    obj.display_type = 'TEXTURED' # was using "WIRE",  Optional: you can use 'SOLID' + transparency

def unghost_object(obj):
    obj.hide_select = False
    obj.show_in_front = False
    obj.display_type = 'TEXTURED'


# ---------- Transparency Logic ----------

def ensure_material(obj):
    if not obj.data.materials:
        mat = bpy.data.materials.new(name="GhostMaterial")
        obj.data.materials.append(mat)
    return obj.data.materials[0]

def set_object_transparency(obj, alpha):
    mat = ensure_material(obj)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Clear old nodes if needed
    if "Principled BSDF" not in nodes:
        for node in nodes:
            nodes.remove(node)

    # Get or create necessary nodes
    if "Principled BSDF" in nodes:
        bsdf = nodes["Principled BSDF"]
    else:
        bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
        bsdf.location = (0, 0)

    if "Material Output" in nodes:
        output = nodes["Material Output"]
    else:
        output = nodes.new(type='ShaderNodeOutputMaterial')
        output.location = (400, 0)

    # Connect BSDF to Output
    if not links:
        links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

    # Set alpha and blend mode
    bsdf.inputs["Alpha"].default_value = alpha
    mat.blend_method = 'BLEND'
    mat.shadow_method = 'NONE'
    mat.show_transparent_back = False

def remove_transparency(obj):
    mat = ensure_material(obj)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes

    if "Principled BSDF" in nodes:
        nodes["Principled BSDF"].inputs["Alpha"].default_value = 1.0
    mat.blend_method = 'OPAQUE'


# ---------- Operators ----------

class OBJECT_OT_ghost(bpy.types.Operator):
    bl_idname = "object.make_ghost"
    bl_label = "Ghost Selected or Active Object(s)"
    bl_description = "Makes selected or active objects unselectable and visible"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        objs = context.selected_objects if context.selected_objects else [context.active_object]
        for obj in objs:
            if obj is not None and obj.type == 'MESH':
                ghost_object(obj)
        return {'FINISHED'}

class OBJECT_OT_unghost(bpy.types.Operator):
    bl_idname = "object.undo_ghost"
    bl_label = "Un-Ghost Selected or Active Object(s)"
    bl_description = "Restores visibility and selectability to selected or active objects"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        objs = context.selected_objects if context.selected_objects else [context.active_object]
        for obj in objs:
            if obj is not None and obj.type == 'MESH':
                unghost_object(obj)
        return {'FINISHED'}


class OBJECT_OT_apply_transparency(bpy.types.Operator):
    bl_idname = "object.apply_transparency"
    bl_label = "Apply Transparency"
    bl_description = "Applies viewport transparency to selected objects"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        alpha = context.scene.ghost_tool_props.transparency
        objs = context.selected_objects if context.selected_objects else [context.active_object]
        for obj in objs:
            if obj.type == 'MESH':
                set_object_transparency(obj, alpha)
        return {'FINISHED'}

class OBJECT_OT_remove_transparency(bpy.types.Operator):
    bl_idname = "object.remove_transparency"
    bl_label = "Remove Transparency"
    bl_description = "Restores full opacity to selected objects"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        objs = context.selected_objects if context.selected_objects else [context.active_object]
        for obj in objs:
            if obj.type == 'MESH':
                remove_transparency(obj)
        return {'FINISHED'}


# ---------- Panel ----------

class GHOST_PT_panel(bpy.types.Panel):
    bl_label = "Ghost Tools"
    bl_idname = "GHOST_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Ghost'

    def draw(self, context):
        layout = self.layout
        props = context.scene.ghost_tool_props

        layout.label(text="Ghost Selection:")
        layout.operator("object.make_ghost", icon='HIDE_OFF')
        layout.operator("object.undo_ghost", icon='HIDE_ON')

        layout.separator()
        layout.label(text="Transparency Control:")
        layout.prop(props, "transparency", text="Alpha")
        layout.operator("object.apply_transparency", icon='SHADING_TEXTURE')
        layout.operator("object.remove_transparency", icon='SHADING_SOLID')


# ---------- Properties ----------

class GhostToolProperties(bpy.types.PropertyGroup):
    transparency: FloatProperty(
        name="Transparency",
        description="Set object transparency (0 = fully transparent, 1 = opaque)",
        default=0.2,
        min=0.0,
        max=1.0
    )


# ---------- Register ----------

classes = [
    GhostToolProperties,
    OBJECT_OT_ghost,
    OBJECT_OT_unghost,
    OBJECT_OT_apply_transparency,
    OBJECT_OT_remove_transparency,
    GHOST_PT_panel,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.ghost_tool_props = PointerProperty(type=GhostToolProperties)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.ghost_tool_props

if __name__ == "__main__":
    register()
