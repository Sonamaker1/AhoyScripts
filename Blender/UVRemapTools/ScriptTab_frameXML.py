import bpy
import os
import re
import xml.etree.ElementTree as ET
from mathutils import Vector

# ============================================================
# USER SETTINGS
# ============================================================

XML_PATH = r"C:\path\to\your\atlas.xml"
ATLAS_IMAGE_PATH = r"C:\path\to\your\NOTE_assets.png"

# If image loading fails, these are used as fallback.
ATLAS_WIDTH_FALLBACK = 2048
ATLAS_HEIGHT_FALLBACK = 2048

# Blender units per pixel.
PIXEL_SCALE = 0.01

# Space between animation groups.
ANIMATION_SPACING = 3.0

# Put all created objects in this collection.
COLLECTION_NAME = "Starling Atlas Import"

# Reuse one material for all planes.
MATERIAL_NAME = "StarlingAtlasMaterial"

# If True, delete old collection with same name first.
DELETE_OLD_COLLECTION = True


# ============================================================
# HELPERS
# ============================================================

def ensure_collection(name: str, delete_old: bool = False):
    if delete_old and name in bpy.data.collections:
        old_col = bpy.data.collections[name]

        # Unlink from parent collections
        for scene in bpy.data.scenes:
            if old_col.name in scene.collection.children:
                scene.collection.children.unlink(old_col)

        # Remove contained objects
        for obj in list(old_col.objects):
            bpy.data.objects.remove(obj, do_unlink=True)

        bpy.data.collections.remove(old_col)

    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    return col


def load_image_get_size(image_path: str, fallback_w: int, fallback_h: int):
    image = None
    atlas_w = fallback_w
    atlas_h = fallback_h

    if os.path.exists(image_path):
        image = bpy.data.images.get(os.path.basename(image_path))
        if image is None:
            image = bpy.data.images.load(image_path)

        if image is not None and len(image.size) >= 2:
            atlas_w = int(image.size[0])
            atlas_h = int(image.size[1])

    return image, atlas_w, atlas_h


def ensure_material(material_name: str, image):
    mat = bpy.data.materials.get(material_name)
    if mat is None:
        mat = bpy.data.materials.new(name=material_name)

    mat.use_nodes = True
    nt = mat.node_tree
    nodes = nt.nodes
    links = nt.links

    # Clear and rebuild for predictability.
    nodes.clear()

    out = nodes.new(type="ShaderNodeOutputMaterial")
    out.location = (300, 0)

    bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
    bsdf.location = (0, 0)

    tex = nodes.new(type="ShaderNodeTexImage")
    tex.location = (-300, 0)
    tex.image = image

    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    # Alpha-friendly defaults.
    mat.blend_method = 'BLEND'
    #mat.shadow_method = 'NONE'
    mat.use_backface_culling = False

    return mat


def parse_frame_name(name: str):
    """
    Splits:
        'left press0003' -> ('left press', 3)
        'blue0000'       -> ('blue', 0)
    If no trailing digits:
        returns (name, 0)
    """
    m = re.match(r"^(.*?)(\d+)$", name)
    if m:
        base = m.group(1).rstrip()
        frame_index = int(m.group(2))
        return base, frame_index
    return name, 0


def parse_starling_xml(xml_path: str):
    tree = ET.parse(xml_path)
    root = tree.getroot()

    image_path_in_xml = root.attrib.get("imagePath", "")

    animations = {}

    for sub in root.findall("SubTexture"):
        name = sub.attrib["name"]

        x = float(sub.attrib.get("x", 0))
        y = float(sub.attrib.get("y", 0))
        w = float(sub.attrib.get("width", 0))
        h = float(sub.attrib.get("height", 0))

        frame_x = float(sub.attrib.get("frameX", 0))
        frame_y = float(sub.attrib.get("frameY", 0))
        frame_w = float(sub.attrib.get("frameWidth", w))
        frame_h = float(sub.attrib.get("frameHeight", h))

        anim_name, frame_index = parse_frame_name(name)

        frame_data = {
            "name": name,
            "anim_name": anim_name,
            "frame_index": frame_index,
            "x": x,
            "y": y,
            "w": w,
            "h": h,
            "frame_x": frame_x,
            "frame_y": frame_y,
            "frame_w": frame_w,
            "frame_h": frame_h,
        }

        animations.setdefault(anim_name, []).append(frame_data)

    for anim_name in animations:
        animations[anim_name].sort(key=lambda f: f["frame_index"])

    return animations, image_path_in_xml


def create_uv_plane(
    frame,
    atlas_w,
    atlas_h,
    material,
    collection,
    parent=None,
    pixel_scale=0.01
):
    """
    Create a quad whose local geometry restores Starling trimmed-frame placement.

    Coordinate logic:
    - Full logical frame = frame_w x frame_h
    - Visible trimmed rect = w x h
    - frameX/frameY place that visible rect within the full frame
    - Object origin stays at full-frame center
    """

    name = frame["name"]

    x = frame["x"]
    y = frame["y"]
    w = frame["w"]
    h = frame["h"]

    frame_x = frame["frame_x"]
    frame_y = frame["frame_y"]
    frame_w = frame["frame_w"]
    frame_h = frame["frame_h"]

    # Local rect in pixels, centered on full frame.
    # Starling frameX/frameY are commonly negative for trimmed sprites.
    left = (-frame_w / 2.0) - frame_x
    right = left + w
    top = (frame_h / 2.0) + frame_y
    bottom = top - h

    # Scale into Blender units.
    left *= pixel_scale
    right *= pixel_scale
    top *= pixel_scale
    bottom *= pixel_scale

    verts = [
        (left,  bottom, 0.0),  # 0 bottom-left
        (right, bottom, 0.0),  # 1 bottom-right
        (right, top,    0.0),  # 2 top-right
        (left,  top,    0.0),  # 3 top-left
    ]
    faces = [(0, 1, 2, 3)]

    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    # UVs: Starling x/y use top-left image origin.
    # Blender UVs use bottom-left.
    u0 = x / atlas_w
    u1 = (x + w) / atlas_w
    v1 = 1.0 - (y / atlas_h)
    v0 = 1.0 - ((y + h) / atlas_h)

    uv_layer = mesh.uv_layers.new(name="UVMap")
    uv_data = uv_layer.data

    # Face loop order matches verts order above.
    loop_uvs = [
        (u0, v0),  # bottom-left
        (u1, v0),  # bottom-right
        (u1, v1),  # top-right
        (u0, v1),  # top-left
    ]

    for i, uv in enumerate(loop_uvs):
        uv_data[i].uv = uv

    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)

    if parent is not None:
        obj.parent = parent

    if material is not None:
        if len(obj.data.materials) == 0:
            obj.data.materials.append(material)
        else:
            obj.data.materials[0] = material

    # Store useful metadata.
    obj["starling_anim"] = frame["anim_name"]
    obj["starling_frame"] = frame["frame_index"]
    obj["frame_w"] = frame_w
    obj["frame_h"] = frame_h
    obj["trimmed_w"] = w
    obj["trimmed_h"] = h
    obj["frame_x"] = frame_x
    obj["frame_y"] = frame_y

    return obj


def create_empty(name: str, collection, location=(0, 0, 0), parent=None):
    empty = bpy.data.objects.new(name, None)
    empty.empty_display_type = 'PLAIN_AXES'
    empty.location = location
    collection.objects.link(empty)
    if parent is not None:
        empty.parent = parent
    return empty


def import_starling_as_planes():
    if not os.path.exists(XML_PATH):
        raise FileNotFoundError(f"XML not found: {XML_PATH}")

    collection = ensure_collection(COLLECTION_NAME, delete_old=DELETE_OLD_COLLECTION)

    animations, xml_image_path = parse_starling_xml(XML_PATH)

    atlas_image_path = ATLAS_IMAGE_PATH
    if not os.path.exists(atlas_image_path) and xml_image_path:
        xml_dir = os.path.dirname(XML_PATH)
        candidate = os.path.join(xml_dir, xml_image_path)
        if os.path.exists(candidate):
            atlas_image_path = candidate

    image, atlas_w, atlas_h = load_image_get_size(
        atlas_image_path,
        ATLAS_WIDTH_FALLBACK,
        ATLAS_HEIGHT_FALLBACK,
    )

    material = ensure_material(MATERIAL_NAME, image)

    root_empty = create_empty("StarlingAtlas_Root", collection)

    current_x = 0.0

    # Stable ordering for layout.
    for anim_name in sorted(animations.keys()):
        frames = animations[anim_name]

        group_empty = create_empty(
            name=f"{anim_name}_GROUP",
            collection=collection,
            location=(current_x, 0.0, 0.0),
            parent=root_empty
        )

        # Create all frames at same local origin.
        max_frame_w = 0.0
        max_frame_h = 0.0

        for frame in frames:
            obj = create_uv_plane(
                frame=frame,
                atlas_w=atlas_w,
                atlas_h=atlas_h,
                material=material,
                collection=collection,
                parent=group_empty,
                pixel_scale=PIXEL_SCALE
            )
            obj.location = (0.0, 0.0, 0.0)

            max_frame_w = max(max_frame_w, frame["frame_w"])
            max_frame_h = max(max_frame_h, frame["frame_h"])

        # Optional: stack frame planes slightly along Y so all are visible in viewport.
        # Comment out if you want exact overlap.
        for i, child in enumerate(group_empty.children):
            child.location.y += i * (max_frame_h * PIXEL_SCALE * 1.1)

        # Advance to next animation group.
        group_width = max_frame_w * PIXEL_SCALE
        current_x += group_width + ANIMATION_SPACING

    print("Starling import complete.")
    print(f"Atlas size used: {atlas_w} x {atlas_h}")
    print(f"Animations imported: {len(animations)}")


# ============================================================
# RUN
# ============================================================

import_starling_as_planes()
