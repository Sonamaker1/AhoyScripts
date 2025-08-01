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
import bpy
import bmesh

class OBJECT_OT_flatten_uv_to_geometry(bpy.types.Operator):
    bl_idname = "object.flatten_uv_to_geometry"
    bl_label = "Flatten UV to Geometry (From Another Object)"
    bl_description = "Physically flattens the active object's geometry using the UV map of another selected object"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        selection = context.selected_objects
        if len(selection) != 2:
            self.report({'ERROR'}, "Select exactly 2 mesh objects: target and source (UV)")
            return {'CANCELLED'}

        # Sort: target = active, source = other
        target_obj = context.active_object
        source_obj = [obj for obj in selection if obj != target_obj][0]

        if target_obj.type != 'MESH' or source_obj.type != 'MESH':
            self.report({'ERROR'}, "Both selected objects must be meshes")
            return {'CANCELLED'}

        target_mesh = target_obj.data
        source_mesh = source_obj.data

        if len(target_mesh.polygons) != len(source_mesh.polygons):
            self.report({'ERROR'}, "Objects must have identical geometry (same face count)")
            return {'CANCELLED'}

        # Prepare bmeshes
        target_bm = bmesh.new()
        target_bm.from_mesh(target_mesh)
        source_bm = bmesh.new()
        source_bm.from_mesh(source_mesh)
        uv_layer = source_bm.loops.layers.uv.active

        if uv_layer is None:
            self.report({'ERROR'}, "Source object has no UV map")
            return {'CANCELLED'}

        flat_bm = bmesh.new()

        # Use a matching-by-face-order approach
        source_faces = list(source_bm.faces)
        target_faces = list(target_bm.faces)

        for src_face, tgt_face in zip(source_faces, target_faces):
            new_verts = []
            for src_loop, tgt_loop in zip(src_face.loops, tgt_face.loops):
                uv = src_loop[uv_layer].uv
                # Place new vertex at UV coordinates in XY space
                vert = flat_bm.verts.new((uv.x * 2.0, uv.y * 2.0, 0))
                new_verts.append(vert)
            try:
                flat_bm.faces.new(new_verts)
            except ValueError:
                # Face might already exist due to shared verts; skip
                pass
        
        # Create UV layer in new mesh and copy target UVs
        uv_target_layer = target_bm.loops.layers.uv.active
        uv_new_layer = flat_bm.loops.layers.uv.new("OriginalUV")

        for flat_face, tgt_face in zip(flat_bm.faces, target_bm.faces):
            for flat_loop, tgt_loop in zip(flat_face.loops, tgt_face.loops):
                flat_loop[uv_new_layer].uv = tgt_loop[uv_target_layer].uv.copy()

        flat_bm.normal_update()
        new_mesh = bpy.data.meshes.new(target_obj.name + "_UVFlat")
        flat_bm.to_mesh(new_mesh)
        flat_bm.free()
        target_bm.free()
        source_bm.free()

        new_obj = bpy.data.objects.new(target_obj.name + "_UVFlat", new_mesh)
        context.collection.objects.link(new_obj)
        new_obj.select_set(True)
        context.view_layer.objects.active = new_obj

        self.report({'INFO'}, "Flattened mesh created using UVs from source object.")
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
