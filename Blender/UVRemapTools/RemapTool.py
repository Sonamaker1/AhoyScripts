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
        layout.operator("object.render_flat_uv_image")

class OBJECT_OT_render_flat_uv_image(bpy.types.Operator):
    bl_idname = "object.render_flat_uv_image"
    bl_label = "Render UV Flattened Mesh"
    bl_description = "Renders the UV-flattened mesh to a flat image"
    bl_options = {'REGISTER', 'UNDO'}

    image_name: bpy.props.StringProperty(name="Image Name", default="UV_Render")
    resolution: bpy.props.IntProperty(name="Resolution", default=1024, min=64, max=8192)

    def execute(self, context):
        obj = context.active_object
        if obj.type != 'MESH':
            self.report({'ERROR'}, "Select a UV-flattened mesh object")
            return {'CANCELLED'}

        # Create temporary scene
        scene = bpy.data.scenes.new("UV_Render_Scene")
        scene.render.engine = 'CYCLES'  # or 'BLENDER_EEVEE'
        scene.render.resolution_x = self.resolution
        scene.render.resolution_y = self.resolution
        scene.render.film_transparent = True

        # Create new camera
        cam_data = bpy.data.cameras.new("UV_Camera")
        cam_data.type = 'ORTHO'
        cam_data.ortho_scale = 2.0  # Match UV space (0-1 scaled up)
        cam_obj = bpy.data.objects.new("UV_Camera", cam_data)
        cam_obj.location = (1.0, 1.0, 5.0)
        cam_obj.rotation_euler = (0, 0, 0)
        scene.collection.objects.link(cam_obj)
        scene.camera = cam_obj

        # Copy the object to new scene
        obj_copy = obj.copy()
        obj_copy.data = obj.data.copy()
        scene.collection.objects.link(obj_copy)

        # Create flat emission material if none
        for slot in obj_copy.material_slots:
            mat = slot.material
            if mat and mat.use_nodes:
                bsdf = mat.node_tree.nodes.get("Principled BSDF")
                if bsdf:
                    # Replace with Emission shader
                    mat.node_tree.nodes.remove(bsdf)
                    emission = mat.node_tree.nodes.new("ShaderNodeEmission")
                    mat.node_tree.links.new(
                        emission.outputs["Emission"],
                        mat.node_tree.nodes["Material Output"].inputs["Surface"]
                    )

        # Set up render output
        tmp_image = bpy.data.images.new(self.image_name, width=self.resolution, height=self.resolution)
        scene.use_nodes = True
        tree = scene.node_tree
        tree.nodes.clear()

        render_layer = tree.nodes.new(type='CompositorNodeRLayers')
        comp_out = tree.nodes.new(type='CompositorNodeComposite')
        image_out = tree.nodes.new(type='CompositorNodeViewer')
        tree.links.new(render_layer.outputs["Image"], comp_out.inputs["Image"])
        tree.links.new(render_layer.outputs["Image"], image_out.inputs["Image"])

        # Render it
        bpy.ops.render.render(write_still=False, scene=scene.name)

        self.report({'INFO'}, f"Rendered to viewer node. Save manually or extend to write to file.")

        return {'FINISHED'}


def register():
    bpy.utils.register_class(OBJECT_OT_flatten_same_uv_to_geometry)
    bpy.utils.register_class(OBJECT_OT_flatten_uv_to_geometry)
    bpy.utils.register_class(OBJECT_OT_render_flat_uv_image)
    bpy.utils.register_class(VIEW3D_PT_uv_geometry_tools)

def unregister():
    bpy.utils.unregister_class(OBJECT_OT_flatten_same_uv_to_geometry)
    bpy.utils.unregister_class(OBJECT_OT_flatten_uv_to_geometry)
    bpy.utils.unregister_class(OBJECT_OT_render_flat_uv_image)
    bpy.utils.unregister_class(VIEW3D_PT_uv_geometry_tools)

if __name__ == "__main__":
    register()
