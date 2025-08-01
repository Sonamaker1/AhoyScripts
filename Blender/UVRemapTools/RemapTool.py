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
    bl_label = "Flatten UV to Geometry (From Another Object)"
    bl_description = "Physically flattens the active object's geometry using the UV map of another selected object"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        selection = context.selected_objects
        if len(selection) != 2:
            self.report({'ERROR'}, "Select exactly two objects: UV Source then Target")
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
        for mat in target_obj.data.materials:
            new_obj.data.materials.append(mat)
        context.collection.objects.link(new_obj)
        new_obj.select_set(True)
        context.view_layer.objects.active = new_obj

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


        self.report({'INFO'}, "Flattened mesh created using UVs from source object.")
        return {'FINISHED'}


class OBJECT_OT_flatten_same_uv_to_geometry(bpy.types.Operator):
    bl_idname = "object.flatten_same_uv_to_geometry"
    bl_label = "Flatten UV to Geometry"
    bl_description = "Creates a new object with geometry matching the UV map layout"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        selection = context.selected_objects
        # this is a very dumb way to do this but I couldn't get it working the other way
        first = True
        for target_obj in selection:
            # Sort: target = active, source = other
            source_obj = target_obj

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
            for mat in target_obj.data.materials:
                new_obj.data.materials.append(mat)
            context.collection.objects.link(new_obj)
            new_obj.select_set(True)
            context.view_layer.objects.active = new_obj

            if first:
                first = False
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
