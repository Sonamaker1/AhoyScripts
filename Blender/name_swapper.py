bl_info = {
    "name": "Swap Names of Outliner Selections",
    "author": "ChatGPT",
    "version": (1, 3),
    "blender": (3, 0, 0),
    "location": "Outliner > Right Click Menu",
    "description": "Swaps names of exactly two selected datablocks in Outliner (objects, collections, etc.)",
    "category": "Interface",
}

import bpy

class OUTLINER_OT_swap_names(bpy.types.Operator):
    bl_idname = "outliner.swap_names"
    bl_label = "Swap Names of Selected Items"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        ids = getattr(context, "selected_ids", [])
        return len(ids) == 2 and all(hasattr(item, "name") for item in ids)

    def execute(self, context):
        ids = context.selected_ids
        if len(ids) != 2 or not all(hasattr(item, "name") for item in ids):
            self.report({'WARNING'}, "Exactly two named items must be selected.")
            return {'CANCELLED'}

        id1, id2 = ids
        name1 = id1.name
        name2 = id2.name

        temp_name = "__temp_swap_name__"
        id1.name = temp_name
        id2.name = name1
        id1.name = name2

        self.report({'INFO'}, f"Swapped names: {name1} <--> {name2}")
        return {'FINISHED'}

def menu_func(self, context):
    if OUTLINER_OT_swap_names.poll(context):
        self.layout.operator(OUTLINER_OT_swap_names.bl_idname, icon='SORTALPHA')

def register():
    bpy.utils.register_class(OUTLINER_OT_swap_names)
    bpy.types.OUTLINER_MT_context_menu.append(menu_func)

def unregister():
    bpy.types.OUTLINER_MT_context_menu.remove(menu_func)
    bpy.utils.unregister_class(OUTLINER_OT_swap_names)

if __name__ == "__main__":
    register()
