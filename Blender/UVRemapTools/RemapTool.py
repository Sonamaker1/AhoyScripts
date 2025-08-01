bl_info = {
    "name": "UV Geometry Flattener",
    "author": "YourName",
    "version": (1, 0),
    "blender": (3, 0, 0),
    "description": "Unwraps mesh into 3D plane using UV map",
    "category": "UV",
}

import os
import bpy
from bpy_extras.io_utils import ExportHelper
import bmesh
from mathutils import Vector

class OBJECT_OT_flatten_uv_to_geometry(bpy.types.Operator):
    bl_idname = "object.flatten_uv_to_geometry"
    bl_label = "Flatten to UV Geometry with Base Plane"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        selected = context.selected_objects
        if len(selected) != 2:
            self.report({'ERROR'}, "Select exactly two objects: UV Source then Target")
            return {'CANCELLED'}

        source_obj, target_obj = selected
        if source_obj.type != 'MESH' or target_obj.type != 'MESH':
            self.report({'ERROR'}, "Both objects must be meshes")
            return {'CANCELLED'}

        source_mesh = source_obj.data
        target_mesh = target_obj.data

        # Get UVs from source mesh
        bm_source = bmesh.new()
        bm_source.from_mesh(source_mesh)
        uv_layer_source = bm_source.loops.layers.uv.active
        if not uv_layer_source:
            self.report({'ERROR'}, "Source object has no UV map")
            return {'CANCELLED'}

        source_faces = list(bm_source.faces)

        # Get material indices from target mesh
        bm_target = bmesh.new()
        bm_target.from_mesh(target_mesh)
        target_faces = list(bm_target.faces)
        target_face_materials = [f.material_index for f in target_faces]

        # Create new mesh and object
        new_mesh = bpy.data.meshes.new(target_obj.name + "_UVFlat")
        new_obj = bpy.data.objects.new(target_obj.name + "_UVFlat", new_mesh)
        context.collection.objects.link(new_obj)

        # Copy target object's materials
        for mat in target_obj.data.materials:
            new_obj.data.materials.append(mat)

        # Create a base plane material
        base_plane_mat = bpy.data.materials.get("UV_Base_Plane_Material")
        if not base_plane_mat:
            base_plane_mat = bpy.data.materials.new(name="UV_Base_Plane_Material")
        new_obj.data.materials.append(base_plane_mat)
        base_plane_index = len(new_obj.data.materials) - 1

        # Build flattened geometry
        bm_flat = bmesh.new()
        uv_layer_flat = bm_flat.loops.layers.uv.new("FlattenedUVs")

        all_uvs = []

        for i, (src_face, tgt_face) in enumerate(zip(source_faces, target_faces)):
            verts = []
            face_uvs = []
            for src_loop in src_face.loops:
                uv = src_loop[uv_layer_source].uv.copy()
                vert = bm_flat.verts.new((uv.x * 2.0, uv.y * 2.0, 0))
                verts.append(vert)
                face_uvs.append(uv)
                all_uvs.append(uv)

            try:
                new_face = bm_flat.faces.new(verts)
                new_face.material_index = target_face_materials[i]
                for loop, uv in zip(new_face.loops, face_uvs):
                    loop[uv_layer_flat].uv = uv
            except ValueError:
                pass  # Skip duplicate faces

        # Add a UV base plane under the geometry
        if all_uvs:
            min_uv = Vector((min(uv.x for uv in all_uvs), min(uv.y for uv in all_uvs)))
            max_uv = Vector((max(uv.x for uv in all_uvs), max(uv.y for uv in all_uvs)))

            margin = 0.05  # Optional: small margin around UV island
            min_uv -= Vector((margin, margin))
            max_uv += Vector((margin, margin))

            p1 = bm_flat.verts.new((min_uv.x * 2.0, min_uv.y * 2.0, -0.01))
            p2 = bm_flat.verts.new((max_uv.x * 2.0, min_uv.y * 2.0, -0.01))
            p3 = bm_flat.verts.new((max_uv.x * 2.0, max_uv.y * 2.0, -0.01))
            p4 = bm_flat.verts.new((min_uv.x * 2.0, max_uv.y * 2.0, -0.01))

            base_face = bm_flat.faces.new([p1, p2, p3, p4])
            base_face.material_index = base_plane_index
            for loop, uv in zip(base_face.loops, [min_uv, (max_uv.x, min_uv.y), max_uv, (min_uv.x, max_uv.y)]):
                loop[uv_layer_flat].uv = Vector(uv)

        # Apply to mesh and finish
        bm_flat.to_mesh(new_mesh)
        bm_flat.free()
        bm_source.free()
        bm_target.free()

        new_obj.select_set(True)
        context.view_layer.objects.active = new_obj

        return {'FINISHED'}


class OBJECT_OT_flatten_same_uv_to_geometry(bpy.types.Operator):
    bl_idname = "object.flatten_same_uv_to_geometry"
    bl_label = "Flatten UV to Geometry"
    bl_description = "Creates a new object with geometry matching the UV map layout"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if obj.type != 'MESH':
            self.report({'ERROR'}, "Active object must be a mesh")
            return {'CANCELLED'}

        mesh = obj.data
        bm = bmesh.new()
        bm.from_mesh(mesh)
        uv_layer = bm.loops.layers.uv.active

        if uv_layer is None:
            self.report({'ERROR'}, "Mesh has no UV map")
            return {'CANCELLED'}

        # Create flattened mesh
        flat_bm = bmesh.new()
        uv_to_vert = {}

        for face in bm.faces:
            verts = []
            for loop in face.loops:
                uv = loop[uv_layer].uv
                # Convert UV to 3D (X = U, Y = V, Z = 0)
                new_vert = flat_bm.verts.new((uv.x * 2.0, uv.y * 2.0, 0))
                verts.append(new_vert)
            flat_bm.faces.new(verts)

        flat_bm.normal_update()
        new_mesh = bpy.data.meshes.new(obj.name + "_UVFlat")
        flat_bm.to_mesh(new_mesh)
        flat_bm.free()

        new_obj = bpy.data.objects.new(obj.name + "_UVFlat", new_mesh)
        context.collection.objects.link(new_obj)
        new_obj.select_set(True)
        context.view_layer.objects.active = new_obj

        return {'FINISHED'}

class VIEW3D_PT_uv_geometry_tools(bpy.types.Panel):
    bl_label = "UV Geometry Tools"
    bl_idname = "VIEW3D_PT_uv_geometry_tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'UV Tools'

    def draw(self, context):
        layout = self.layout
        layout.operator("object.flatten_same_uv_to_geometry")
        layout.operator("object.flatten_uv_to_geometry")

def register():
    bpy.utils.register_class(OBJECT_OT_flatten_same_uv_to_geometry)
    bpy.utils.register_class(OBJECT_OT_flatten_uv_to_geometry)
    bpy.utils.register_class(VIEW3D_PT_uv_geometry_tools)

def unregister():
    bpy.utils.unregister_class(OBJECT_OT_flatten_same_uv_to_geometry)
    bpy.utils.unregister_class(OBJECT_OT_flatten_uv_to_geometry)
    bpy.utils.unregister_class(VIEW3D_PT_uv_geometry_tools)

if __name__ == "__main__":
    register()
