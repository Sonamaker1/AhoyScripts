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
    bl_label = "Flatten to UV Geometry (2 objects)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        import bmesh
        from mathutils import Vector

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

        # Read UVs from source
        bm_source = bmesh.new()
        bm_source.from_mesh(source_mesh)
        uv_layer_src = bm_source.loops.layers.uv.active
        if not uv_layer_src:
            self.report({'ERROR'}, "Source object has no UV map")
            bm_source.free()
            return {'CANCELLED'}

        # Prepare target UVs
        bm_target = bmesh.new()
        bm_target.from_mesh(target_mesh)
        uv_layer_tgt = bm_target.loops.layers.uv.active
        if not uv_layer_tgt:
            uv_layer_tgt = bm_target.loops.layers.uv.new()

        for face_src, face_tgt in zip(bm_source.faces, bm_target.faces):
            for loop_src, loop_tgt in zip(face_src.loops, face_tgt.loops):
                loop_tgt[uv_layer_tgt].uv = loop_src[uv_layer_src].uv

        bm_target.to_mesh(target_mesh)
        bm_source.free()

        # Flattened geometry with material slots
        new_mesh = bpy.data.meshes.new(target_obj.name + "_Flattened")
        new_obj = bpy.data.objects.new(target_obj.name + "_Flattened", new_mesh)
        context.collection.objects.link(new_obj)

        for mat in target_obj.data.materials:
            new_obj.data.materials.append(mat)

        bm_flat = bmesh.new()
        bm_flat.from_mesh(target_mesh)
        uv_layer_flat = bm_flat.loops.layers.uv.active

        for face in bm_flat.faces:
            mat_index = face.material_index
            for loop in face.loops:
                uv = loop[uv_layer_flat].uv
                loop.vert.co = Vector((uv.x * 2.0, uv.y * 2.0, 0))
            face.material_index = mat_index

        bm_flat.to_mesh(new_mesh)
        bm_flat.free()

        # Create UV guide plane
        plane_mesh = bpy.data.meshes.new("UV_BasePlane")
        plane_obj = bpy.data.objects.new("UV_BasePlane", plane_mesh)
        context.collection.objects.link(plane_obj)

        verts = [
            Vector((0, 0, -0.01)),
            Vector((2.0, 0, -0.01)),
            Vector((2.0, 2.0, -0.01)),
            Vector((0, 2.0, -0.01)),
        ]
        faces = [(0, 1, 2, 3)]
        plane_mesh.from_pydata(verts, [], faces)
        plane_mesh.update()

        # Add UVs to the guide plane
        bm_plane = bmesh.new()
        bm_plane.from_mesh(plane_mesh)
        uv_layer_plane = bm_plane.loops.layers.uv.new()
        uv_coords = [(0, 0), (1, 0), (1, 1), (0, 1)]
        for face in bm_plane.faces:
            for loop, uv in zip(face.loops, uv_coords):
                loop[uv_layer_plane].uv = uv
        bm_plane.to_mesh(plane_mesh)
        bm_plane.free()

        # Parent the flattened object to the guide plane
        new_obj.parent = plane_obj

        # Cleanup: Merge by distance and recalculate normals
        bpy.ops.object.select_all(action='DESELECT')
        context.view_layer.objects.active = new_obj
        new_obj.select_set(True)

        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.merge_by_distance(threshold=0.0001)
        bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.object.mode_set(mode='OBJECT')

        # Select the final base plane
        bpy.ops.object.select_all(action='DESELECT')
        plane_obj.select_set(True)
        context.view_layer.objects.active = plane_obj

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
