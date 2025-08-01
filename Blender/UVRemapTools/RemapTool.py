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
        # Enter edit mode on the flattened object
        bpy.context.view_layer.objects.active = new_obj

        try:
            bpy.ops.object.mode_set(mode='EDIT')
        except RuntimeError as e:
            self.report({'ERROR'}, f"Could not switch mode: {e}")
            return {'CANCELLED'}

        # Select all geometry
        bpy.ops.mesh.select_all(action='SELECT')

        # Merge by distance (very small threshold)
        bpy.ops.mesh.remove_doubles(threshold=0.000001)
        #bpy.ops.mesh.merge_by_distance(threshold=0.000001)

        # Recalculate normals to face outward
        bpy.ops.mesh.normals_make_consistent(inside=False)

        # Return to object mode
        bpy.ops.object.mode_set(mode='OBJECT')

        # Select the final base plane
        bpy.ops.object.select_all(action='DESELECT')
        plane_obj.select_set(True)
        context.view_layer.objects.active = plane_obj

        return {'FINISHED'}

class OBJECT_OT_flatten_same_uv_to_geometry(bpy.types.Operator):
    bl_idname = "object.flatten_same_uv_to_geometry"
    bl_label = "Flatten UV to Geometry (Per Object)"
    bl_description = "For each selected mesh object, unwraps geometry to match UV layout. Preserves UVs, materials, adds base plane, cleans up geometry."
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        selected_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not selected_objects:
            self.report({'WARNING'}, "No mesh objects selected")
            return {'CANCELLED'}

        for obj in selected_objects:
            mesh = obj.data
            bm_old = bmesh.new()
            bm_old.from_mesh(mesh)
            uv_layer_old = bm_old.loops.layers.uv.active

            if uv_layer_old is None:
                self.report({'WARNING'}, f"{obj.name} has no active UV map")
                bm_old.free()
                continue

            # Gather all UVs
            all_uvs = [loop[uv_layer_old].uv.copy() for face in bm_old.faces for loop in face.loops]
            if not all_uvs:
                self.report({'WARNING'}, f"{obj.name} has no UV coordinates")
                bm_old.free()
                continue

            # Find bounds of UVs
            min_uv = Vector((min(uv.x for uv in all_uvs), min(uv.y for uv in all_uvs)))
            max_uv = Vector((max(uv.x for uv in all_uvs), max(uv.y for uv in all_uvs)))

            # Create base plane object
            plane_mesh = bpy.data.meshes.new(f"{obj.name}_uv_plane")
            plane_obj = bpy.data.objects.new(f"{obj.name}_UVBase", plane_mesh)
            context.collection.objects.link(plane_obj)

            verts = [
                (0, 0, -0.001),
                (1, 0, -0.001),
                (1, 1, -0.001),
                (0, 1, -0.001)
            ]
            faces = [(0, 1, 2, 3)]
            plane_mesh.from_pydata(verts, [], faces)
            plane_mesh.update()

            # Transform to match UV bounds
            center = (min_uv + max_uv) / 2
            scale = max(max_uv.x - min_uv.x, max_uv.y - min_uv.y)
            plane_obj.scale = (scale, scale, 1)
            plane_obj.location = (center.x, center.y, 0)

            # Flattened mesh from UVs
            bm_new = bmesh.new()

            use_materials = len(mesh.materials) > 0
            mat_layer = None
            if use_materials:
                mat_layer = bm_new.faces.layers.material.verify() 
            

            for face in bm_old.faces:
                new_verts = []
                for loop in face.loops:
                    uv = loop[uv_layer_old].uv
                    v = bm_new.verts.new((uv.x, uv.y, 0))
                    new_verts.append(v)
                try:
                    new_face = bm_new.faces.new(new_verts)
                except ValueError:
                    continue  # Skip duplicate face
                if use_materials:
                    new_face[mat_layer] = face.material_index

            bm_new.normal_update()
            bm_old.free()

            # Create new object from flattened mesh
            new_mesh = bpy.data.meshes.new(f"{obj.name}_flattened")
            bm_new.to_mesh(new_mesh)
            bm_new.free()
            new_obj = bpy.data.objects.new(f"{obj.name}_Flattened", new_mesh)
            context.collection.objects.link(new_obj)

            # Inherit materials
            if use_materials:
                for mat in mesh.materials:
                    new_mesh.materials.append(mat)

            # Parent flattened object to plane
            new_obj.parent = plane_obj

            # Cleanup: Merge by distance and recalculate normals
            bpy.ops.object.select_all(action='DESELECT')
            bpy.context.view_layer.objects.active = new_obj
            new_obj.select_set(True)

            try:
                bpy.ops.object.mode_set(mode='EDIT')
            except RuntimeError as e:
                self.report({'ERROR'}, f"Could not switch to edit mode: {e}")
                return {'CANCELLED'}

            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.remove_doubles(threshold=0.000001)
            bpy.ops.mesh.normals_make_consistent(inside=False)

            bpy.ops.object.mode_set(mode='OBJECT')

            # Select the plane for convenience
            bpy.ops.object.select_all(action='DESELECT')
            plane_obj.select_set(True)
            context.view_layer.objects.active = plane_obj

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
