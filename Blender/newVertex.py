bl_info = {
    "name": "Edit Mode Vertex Tool",
    "author": "Your Name",
    "version": (1, 2),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Edit Vertex",
    "description": "Tools for adding and transforming vertices in Edit Mode",
    "category": "Mesh",
}

import bpy
import bmesh
from bpy.props import CollectionProperty, FloatVectorProperty
from bpy.props import FloatProperty

# Global buffer for copied vertex positions
copied_vertex_positions = []

class EDITVERTEX_OT_add_vertex_cursor(bpy.types.Operator):
    bl_idname = "mesh.add_vertex_at_cursor"
    bl_label = "Add Vertex at 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.edit_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "You must be in Edit Mode on a mesh object")
            return {'CANCELLED'}

        bm = bmesh.from_edit_mesh(obj.data)
        # Get cursor location in local space
        cursor_world = context.scene.cursor.location
        cursor_local = obj.matrix_world.inverted() @ cursor_world

        # Create vertex at cursor position
        new_vert = bm.verts.new(cursor_local)
        bm.verts.index_update()
        bm.verts.ensure_lookup_table()

        # Deselect all, select new vertex
        for v in bm.verts:
            v.select = False
        new_vert.select = True
        bm.select_history.clear()
        bm.select_history.add(new_vert)

        bmesh.update_edit_mesh(obj.data)

        # Change to Move tool
        context.workspace.tools.from_space_view3d_mode(bpy.context.mode, create=True).idname = 'builtin.move'
        self.report({'INFO'}, "Vertex added at 3D Cursor")
        return {'FINISHED'}

class EDITVERTEX_OT_copy_vertices(bpy.types.Operator):
    bl_idname = "mesh.copy_selected_vertices"
    bl_label = "Copy Selected Vertices"
    bl_description = "Copy positions of selected vertices"

    def execute(self, context):
        global copied_vertex_positions
        copied_vertex_positions.clear()

        obj = context.edit_object
        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()

        for v in bm.verts:
            if v.select:
                copied_vertex_positions.append(v.co.copy())

        self.report({'INFO'}, f"Copied {len(copied_vertex_positions)} vertices")
        return {'FINISHED'}

class EDITVERTEX_OT_paste_vertices(bpy.types.Operator):
    bl_idname = "mesh.paste_copied_vertices"
    bl_label = "Paste Copied Vertices"
    bl_description = "Paste copied vertices as new ones"

    def execute(self, context):
        global copied_vertex_positions
        if not copied_vertex_positions:
            self.report({'WARNING'}, "No vertices copied")
            return {'CANCELLED'}

        obj = context.edit_object
        bm = bmesh.from_edit_mesh(obj.data)

        # Deselect all first
        for v in bm.verts:
            v.select = False

        new_verts = []
        for pos in copied_vertex_positions:
            v = bm.verts.new(pos)
            v.select = True
            new_verts.append(v)

        bm.verts.index_update()
        bm.select_history.clear()
        for v in new_verts:
            bm.select_history.add(v)

        bmesh.update_edit_mesh(obj.data)
        context.workspace.tools.from_space_view3d_mode(bpy.context.mode, create=True).idname = 'builtin.move'
        self.report({'INFO'}, f"Pasted {len(new_verts)} vertices")
        return {'FINISHED'}

class EDITVERTEX_OT_move_selected_axis(bpy.types.Operator):
    bl_idname = "mesh.move_selected_on_axis"
    bl_label = "Move Selected on Axis"

    axis: bpy.props.EnumProperty(
        items=[
            ('X', "X Axis", ""),
            ('Y', "Y Axis", ""),
            ('Z', "Z Axis", ""),
        ],
        name="Axis"
    )

    def execute(self, context):
        obj = context.edit_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Edit Mode required on a mesh")
            return {'CANCELLED'}

        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()

        amount = context.scene.edit_vertex_move_amount

        for v in bm.verts:
            if v.select:
                if self.axis == 'X':
                    v.co.x += amount
                elif self.axis == 'Y':
                    v.co.y += amount
                elif self.axis == 'Z':
                    v.co.z += amount

        bmesh.update_edit_mesh(obj.data)
        return {'FINISHED'}

class EDITVERTEX_PT_panel(bpy.types.Panel):
    bl_label = "Edit Vertex Tools"
    bl_idname = "EDITVERTEX_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Edit Vertex"

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    def draw(self, context):
        layout = self.layout
        layout.label(text="Add Vertex:")
        layout.operator("mesh.add_vertex_at_cursor", icon='CURSOR')

        layout.separator()
        layout.label(text="Copy/Paste Vertices:")
        layout.operator("mesh.copy_selected_vertices", icon='COPYDOWN')
        layout.operator("mesh.paste_copied_vertices", icon='PASTEDOWN')

        layout.separator()
        layout.label(text="Move Selected Vertices:")
        layout.prop(context.scene, "edit_vertex_move_amount")
        row = layout.row(align=True)
        row.operator("mesh.move_selected_on_axis", text="X").axis = 'X'
        row.operator("mesh.move_selected_on_axis", text="Y").axis = 'Y'
        row.operator("mesh.move_selected_on_axis", text="Z").axis = 'Z'

# Register
classes = (
    EDITVERTEX_OT_add_vertex_cursor,
    EDITVERTEX_OT_copy_vertices,
    EDITVERTEX_OT_paste_vertices,
    EDITVERTEX_OT_move_selected_axis,
    EDITVERTEX_PT_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.edit_vertex_move_amount = FloatProperty(
        name="Move Amount",
        description="Distance to move selected vertices",
        default=0.1,
        precision=3
    )

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.edit_vertex_move_amount

if __name__ == "__main__":
    register()
