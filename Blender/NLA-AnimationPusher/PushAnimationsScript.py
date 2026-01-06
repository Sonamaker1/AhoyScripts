import bpy

# Get all actions in the blend file
all_actions = bpy.data.actions

# Iterate through all objects in the scene
for obj in bpy.context.scene.objects:
    # Check if the object has animation data and is an armature (modify as needed for other object types)
    if obj.animation_data and obj.type == 'ARMATURE':
        # Ensure the NLA system is active
        obj.animation_data.use_nla = True

        # Clear existing NLA tracks for a clean slate if desired (optional)
        # while obj.animation_data.nla_tracks:
        #     obj.animation_data.nla_tracks.remove(obj.animation_data.nla_tracks[0])

        offset = 0
        # Iterate through all actions and add them as strips to the object's NLA tracks
        # Note: You might need a way to filter which actions belong to which object
        # The example below assumes all actions in bpy.data.actions are applicable to this object.
        # A more robust solution might involve naming conventions or other filtering.
        for action in all_actions:
            if(action.name.endswith("001")):
                continue
            # Create a new NLA track
            track = obj.animation_data.nla_tracks.new()
            track.name = action.name
            
            # Add the action as a new strip to the track
            # The start frame for the strip is set to an increasing offset in this example
            strip = track.strips.new(action.name, int(action.frame_range[0]) + offset, action)
            
            # Optional: Adjust offset for sequential placement
            # offset += int(action.frame_range[1] - action.frame_range[0]) + 1
            
        # Clear the active action slot after pushing to NLA
        obj.animation_data.action = None

print("All actions pushed to NLA tracks for applicable armatures.")
