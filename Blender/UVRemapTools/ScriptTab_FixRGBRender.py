import bpy

# Get the current scene's color management settings
scene = bpy.context.scene
color_management = scene.render.image_settings
display_settings = scene.display_settings
view_settings = scene.view_settings

# --- 1. Set the main render output settings (affects final file save) ---

# Set the file format for typical sRGB output (e.g., PNG or JPEG)
# OpenEXR is typically linear and bypasses the view transform.
color_management.file_format = 'PNG' # Or 'JPEG' etc.
color_management.color_mode = 'RGBA' # Or 'RGB'
color_management.color_depth = '8' # 8-bit is standard for sRGB

# Set the color space for the *output file*. 
# For standard image formats like PNG/JPEG, this is usually 'sRGB' or 'Filmic sRGB' 
# depending on your OCIO config and desired 'look'.
# 'sRGB' is a common default for the *data* in the file.
#color_management.color_space = 'sRGB' #

# Note: The 'color_space' attribute here refers to the color space used when writing the file, 
# not the display transform.

# --- 2. Set the *scene's* color management (affects how the render is generated and viewed) ---

# Set the Display Device to sRGB (standard for most monitors)
scene.display_settings.display_device = 'sRGB' #

# Set the View Transform to 'Standard' to get a direct sRGB output 
# without 'Filmic' or 'AgX' tone mapping.
scene.view_settings.view_transform = 'Standard' #

# Optional: Set the 'Look' to 'None' for no additional contrast/exposure changes
scene.view_settings.look = 'None'

print("Render color management set to sRGB 'Standard' view transform.")
