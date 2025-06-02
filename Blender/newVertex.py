bl_info = {
    "name": "Edit Mode Vertex Tool",
    "author": "Your Name",
    "version": (1, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Edit Vertex",
    "description": "Add an unconnected vertex at the 3D cursor in Edit Mode",
    "category": "Mesh",
}

import bpy
import bmesh

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
        context.workspace.tools.from_space_view3d_mode('EDIT', create=True).idname = 'builtin.move'

        self.report({'INFO'}, "Vertex added at 3D Cursor and Move tool enabled")
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
        layout.operator("mesh.add_vertex_at_cursor")

# Register
classes = (
    EDITVERTEX_OT_add_vertex_cursor,
    EDITVERTEX_PT_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
