bl_info = {
    "name": "Slope Edge Split (Z/Y)",
    "author": "ChatGPT",
    "version": (1, 0, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Slope Split",
    "description": "Split mesh edges into floor vs vertical sets by Z/Y slope (ignoring X).",
    "category": "Mesh",
}

import bpy
import bmesh
from bpy.props import (
    FloatProperty,
    BoolProperty,
    EnumProperty,
)
from mathutils import Matrix


def _edge_class(v1, v2, eps, slope_threshold):
    """
    Classify an edge using only (Y,Z):
      dy == 0  -> vertical (undefined slope, y = constant)
      else slope = dz/dy
           abs(slope) <= threshold -> floor
           abs(slope) >  threshold -> vertical
    """
    dy = v2.y - v1.y
    dz = v2.z - v1.z

    if abs(dy) <= eps:
        return "VERTICAL"

    slope = dz / dy
    if abs(slope) <= slope_threshold:
        return "FLOOR"
    return "VERTICAL"


def _build_edge_only_object(context, name, coords_edges, collection, replace_existing=True):
    """
    coords_edges: list of (co1, co2) pairs (mathutils.Vector)
    Builds a new mesh object containing only those edges.
    """
    # Remove existing object with same name (optional)
    if replace_existing:
        existing = bpy.data.objects.get(name)
        if existing:
            # Unlink from all collections then remove
            for c in list(existing.users_collection):
                c.objects.unlink(existing)
            bpy.data.objects.remove(existing, do_unlink=True)

        existing_mesh = bpy.data.meshes.get(name)
        if existing_mesh and existing_mesh.users == 0:
            bpy.data.meshes.remove(existing_mesh)

    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)

    collection.objects.link(obj)

    bm = bmesh.new()
    vert_map = {}  # key: (x,y,z) rounded tuple or id -> bmvert

    def get_bmvert(co):
        # rounding to avoid tiny float duplicates; adjust if needed
        key = (round(co.x, 6), round(co.y, 6), round(co.z, 6))
        bv = vert_map.get(key)
        if bv is None:
            bv = bm.verts.new(co)
            vert_map[key] = bv
        return bv

    for co1, co2 in coords_edges:
        bv1 = get_bmvert(co1)
        bv2 = get_bmvert(co2)
        if bv1 != bv2:
            try:
                bm.edges.new((bv1, bv2))
            except ValueError:
                # edge already exists
                pass

    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.to_mesh(mesh)
    bm.free()

    # Make it easy to see
    obj.display_type = 'WIRE'
    obj.show_in_front = True

    return obj


class MESH_OT_split_edges_by_zy_slope(bpy.types.Operator):
    bl_idname = "mesh.split_edges_by_zy_slope"
    bl_label = "Split Edges by Z/Y Slope"
    bl_options = {'REGISTER', 'UNDO'}

    slope_threshold: FloatProperty(
        name="Floor Slope |dz/dy| ≤",
        description="Edges with abs(dz/dy) <= threshold are considered floor",
        default=1.0,
        min=0.0,
        soft_max=10.0,
    )

    eps: FloatProperty(
        name="dy Epsilon",
        description="Treat abs(dy) <= epsilon as dy==0 (undefined slope)",
        default=1e-6,
        min=0.0,
        soft_max=1e-3,
        precision=8,
    )

    space: EnumProperty(
        name="Coordinate Space",
        description="Compute slope in local or world space",
        items=[
            ('LOCAL', "Local", "Use object local coordinates"),
            ('WORLD', "World", "Use world-space coordinates (includes object transforms)"),
        ],
        default='WORLD',
    )

    use_evaluated: BoolProperty(
        name="Use Evaluated Mesh",
        description="Use evaluated mesh (applies modifiers). For most converted Grease Pencil meshes, OFF is fine.",
        default=False,
    )

    replace_existing: BoolProperty(
        name="Replace Existing Outputs",
        description="If output objects already exist, delete and recreate them",
        default=True,
    )

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Active object must be a Mesh.")
            return {'CANCELLED'}

        # Choose source mesh (evaluated or original)
        depsgraph = context.evaluated_depsgraph_get()
        if self.use_evaluated:
            obj_eval = obj.evaluated_get(depsgraph)
            mesh_src = obj_eval.to_mesh()
            src_matrix = obj.matrix_world.copy()
        else:
            mesh_src = obj.data
            src_matrix = obj.matrix_world.copy()

        bm = bmesh.new()
        bm.from_mesh(mesh_src)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()

        # Transform basis for classification
        if self.space == 'WORLD':
            xform = src_matrix
        else:
            xform = Matrix.Identity(4)

        floor_edges = []
        vertical_edges = []

        # classify edges
        for e in bm.edges:
            v1 = xform @ e.verts[0].co
            v2 = xform @ e.verts[1].co
            cls = _edge_class(v1, v2, self.eps, self.slope_threshold)
            if cls == "FLOOR":
                floor_edges.append((v1.copy(), v2.copy()))
            else:
                vertical_edges.append((v1.copy(), v2.copy()))

        # cleanup bm + evaluated mesh if used
        bm.free()
        if self.use_evaluated:
            obj_eval.to_mesh_clear()

        # Output collection: same collection as the source object, if possible
        if obj.users_collection:
            out_coll = obj.users_collection[0]
        else:
            out_coll = context.scene.collection

        base = obj.name
        floor_name = f"{base}_floorEdges"
        vert_name = f"{base}_verticalEdges"

        _build_edge_only_object(context, floor_name, floor_edges, out_coll, replace_existing=self.replace_existing)
        _build_edge_only_object(context, vert_name, vertical_edges, out_coll, replace_existing=self.replace_existing)

        self.report({'INFO'}, f"Created: {floor_name} ({len(floor_edges)} edges), {vert_name} ({len(vertical_edges)} edges)")
        return {'FINISHED'}


class VIEW3D_PT_slope_split_panel(bpy.types.Panel):
    bl_label = "Slope Split"
    bl_idname = "VIEW3D_PT_slope_split_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Slope Split"

    def draw(self, context):
        layout = self.layout
        layout.label(text="Split edges by Z/Y slope (ignore X)")

        op = layout.operator(MESH_OT_split_edges_by_zy_slope.bl_idname, text="Split Edges", icon='MOD_WIREFRAME')

        # Show operator props in the panel for convenience (Blender will store last-used values)
        col = layout.column(align=True)
        col.prop(context.scene, "slope_split_threshold")
        col.prop(context.scene, "slope_split_eps")
        col.prop(context.scene, "slope_split_space")
        col.prop(context.scene, "slope_split_use_evaluated")
        col.prop(context.scene, "slope_split_replace_existing")

        # Push scene properties into operator defaults
        op.slope_threshold = context.scene.slope_split_threshold
        op.eps = context.scene.slope_split_eps
        op.space = context.scene.slope_split_space
        op.use_evaluated = context.scene.slope_split_use_evaluated
        op.replace_existing = context.scene.slope_split_replace_existing


def register():
    bpy.utils.register_class(MESH_OT_split_edges_by_zy_slope)
    bpy.utils.register_class(VIEW3D_PT_slope_split_panel)

    # Scene-level properties so the panel can remember settings without custom UILists
    bpy.types.Scene.slope_split_threshold = FloatProperty(
        name="Floor Slope |dz/dy| ≤",
        default=1.0,
        min=0.0,
        soft_max=10.0,
    )
    bpy.types.Scene.slope_split_eps = FloatProperty(
        name="dy Epsilon",
        default=1e-6,
        min=0.0,
        soft_max=1e-3,
        precision=8,
    )
    bpy.types.Scene.slope_split_space = EnumProperty(
        name="Coordinate Space",
        items=[
            ('LOCAL', "Local", "Use object local coordinates"),
            ('WORLD', "World", "Use world-space coordinates (includes object transforms)"),
        ],
        default='WORLD',
    )
    bpy.types.Scene.slope_split_use_evaluated = BoolProperty(
        name="Use Evaluated Mesh",
        default=False,
    )
    bpy.types.Scene.slope_split_replace_existing = BoolProperty(
        name="Replace Existing Outputs",
        default=True,
    )


def unregister():
    del bpy.types.Scene.slope_split_threshold
    del bpy.types.Scene.slope_split_eps
    del bpy.types.Scene.slope_split_space
    del bpy.types.Scene.slope_split_use_evaluated
    del bpy.types.Scene.slope_split_replace_existing

    bpy.utils.unregister_class(VIEW3D_PT_slope_split_panel)
    bpy.utils.unregister_class(MESH_OT_split_edges_by_zy_slope)


if __name__ == "__main__":
    register()
