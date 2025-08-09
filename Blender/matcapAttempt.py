bl_info = {
    "name": "Matcap Material Creator & Baker",
    "blender": (4, 0, 0),
    "category": "Material",
}

import bpy
import os

class MATCAP_PT_panel(bpy.types.Panel):
    bl_label = "Matcap Material"
    bl_idname = "MATCAP_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Matcap'

    def draw(self, context):
        layout = self.layout
        layout.operator("matcap.create", text="Create Matcap Material")
        layout.operator("matcap.bake", text="Bake Material to UVs")


class MATCAP_OT_create(bpy.types.Operator):
    bl_idname = "matcap.create"
    bl_label = "Create Matcap Material"
    bl_description = "Pick a matcap image and create a material using it"

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        if not self.filepath or not os.path.isfile(self.filepath):
            self.report({'ERROR'}, "No valid image selected")
            return {'CANCELLED'}

        img = bpy.data.images.load(self.filepath)

        # Make unique material name
        base_name = "Matcap"
        name = base_name
        count = 1
        while name in bpy.data.materials:
            name = f"{base_name}.{count:03d}"
            count += 1

        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()

        # Create nodes
        output = nodes.new(type='ShaderNodeOutputMaterial')
        output.location = (400, 0)

        emission = nodes.new(type='ShaderNodeEmission')
        emission.location = (200, 0)

        tex = nodes.new(type='ShaderNodeTexImage')
        tex.image = img
        tex.location = (-200, 0)

        # Normal-based mapping
        normal = nodes.new(type='ShaderNodeNewGeometry')
        normal.location = (-600, 0)

        sep = nodes.new(type='ShaderNodeSeparateXYZ')
        sep.location = (-400, 0)

        combine = nodes.new(type='ShaderNodeCombineXYZ')
        combine.location = (-200, -200)

        mapping = nodes.new(type='ShaderNodeMapping')
        mapping.location = (0, -200)
        mapping.vector_type = 'NORMAL'

        tex_coord = nodes.new(type='ShaderNodeTexCoord')
        tex_coord.location = (-400, -200)

        # Simplified: Use normal directly to map to matcap
        # Normalize to UV space (0-1 range)
        normal_map = nodes.new(type='ShaderNodeVectorMath')
        normal_map.location = (-200, -400)
        normal_map.operation = 'MULTIPLY_ADD'
        normal_map.inputs[1].default_value = (0.5, 0.5, 0.5)
        normal_map.inputs[2].default_value = (0.5, 0.5, 0.5)

        links.new(normal.outputs['Normal'], normal_map.inputs[0])
        links.new(normal_map.outputs[0], tex.inputs['Vector'])

        links.new(tex.outputs['Color'], emission.inputs['Color'])
        links.new(emission.outputs['Emission'], output.inputs['Surface'])

        # Apply material to active object
        obj = context.active_object
        if obj and obj.type == 'MESH':
            if obj.data.materials:
                obj.data.materials[0] = mat
            else:
                obj.data.materials.append(mat)

        self.report({'INFO'}, f"Matcap material '{name}' created and applied")
        return {'FINISHED'}


class MATCAP_OT_bake(bpy.types.Operator):
    bl_idname = "matcap.bake"
    bl_label = "Bake Material to UVs"
    bl_description = "Bakes the active object's current material to its UV map"

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Select a mesh object")
            return {'CANCELLED'}

        mat = obj.active_material
        if not mat or not mat.use_nodes:
            self.report({'ERROR'}, "Active object has no node material")
            return {'CANCELLED'}

        # Create a new image to bake to
        img_name = f"{obj.name}_MatcapBake"
        img = bpy.data.images.new(img_name, width=2048, height=2048)

        # Create temporary image texture node
        nodes = mat.node_tree.nodes
        tex_node = nodes.new(type='ShaderNodeTexImage')
        tex_node.image = img
        nodes.active = tex_node

        # Bake
        bpy.ops.object.bake(type='EMIT', margin=2)

        # Remove temp node
        nodes.remove(tex_node)

        # Save image to file
        img.filepath_raw = bpy.path.abspath(f"//{img_name}.png")
        img.file_format = 'PNG'
        img.save()

        self.report({'INFO'}, f"Baked to {img.filepath_raw}")
        return {'FINISHED'}


classes = (MATCAP_PT_panel, MATCAP_OT_create, MATCAP_OT_bake)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
