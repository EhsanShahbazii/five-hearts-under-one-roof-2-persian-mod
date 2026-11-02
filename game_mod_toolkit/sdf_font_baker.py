"""
SDF Font Baker for TextMeshPro in Unity
Bakes Persian/Arabic glyphs and presentation forms directly into the TMP SDF atlas
and registers them in m_CharacterTable and m_GlyphTable via safe in-place binary patching.
"""

import os
import glob
import json
import shutil
import numpy as np
from PIL import Image, ImageFont
from scipy.ndimage import distance_transform_edt
from fontTools.ttLib import TTFont
import UnityPy

from rtl_formatter import shape_persian

def get_font_typetree_node(bundle_path: str):
    env_bundle = UnityPy.load(bundle_path)
    sf_bundle = list(env_bundle.file.files.values())[0]
    for obj in env_bundle.objects:
        if obj.path_id == 2275452363925841441:
            t = sf_bundle.types[obj.type_id]
            return t.node
    return None

def collect_persian_unicodes(translations_dir: str):
    unicodes = set()
    for f in glob.glob(os.path.join(translations_dir, "*.json")):
        with open(f, "r", encoding="utf-8") as jf:
            data = json.load(jf)
        for item in data:
            script = item.get("SCRIPT", {})
            text = script.get("PERSIAN") or script.get("ENGLISH") or ""
            if not text:
                continue
            shaped = shape_persian(text)
            for ch in shaped:
                if ord(ch) > 32:
                    unicodes.add(ord(ch))
    return sorted(list(unicodes))

def patch_resources_assets_in_place(game_app_path: str, ttf_path: str, translations_dir: str, backup_dir: str = None) -> bool:
    res_path = os.path.join(game_app_path, "Contents", "Resources", "Data", "resources.assets")
    bundle_path = os.path.join(
        game_app_path, "Contents", "Resources", "Data", "StreamingAssets", "aa", "StandaloneOSX",
        "prefabs__696255eeff874f5e4aa086c2c2f7892f.bundle"
    )

    if not os.path.exists(res_path) or not os.path.exists(bundle_path):
        print("[!] Target files not found for font patching!")
        return False

    # 1. Backup if needed
    bak_res = os.path.join(backup_dir, "resources.assets.original") if backup_dir else None
    if bak_res and not os.path.exists(bak_res):
        shutil.copy2(res_path, bak_res)
        print("[✔] Backed up original resources.assets")

    # 2. Get font typetree node from bundle
    font_node = get_font_typetree_node(bundle_path)
    if not font_node:
        print("[!] Could not get font typetree node!")
        return False

    # 3. Collect unique unicodes
    unicodes_to_bake = collect_persian_unicodes(translations_dir)
    persian_unicodes = [u for u in unicodes_to_bake if (0x0600 <= u < 0x3000) or (0xFB50 <= u <= 0xFEFC)]
    print(f"[*] Total unique Persian glyphs to bake: {len(persian_unicodes)}")

    # 4. Load resources.assets (from backup if available to ensure pristine base)
    source_res = bak_res if (bak_res and os.path.exists(bak_res)) else res_path
    env_res = UnityPy.load(source_res)
    obj_249 = None
    obj_55 = None
    for obj in env_res.objects:
        if obj.path_id == 249:
            obj_249 = obj
        elif obj.path_id == 55:
            obj_55 = obj

    if not obj_249 or not obj_55:
        print("[!] Could not locate font asset or texture in resources.assets!")
        return False

    tree = obj_249.read_typetree(font_node)
    char_table = tree["m_CharacterTable"]
    glyph_table = tree["m_GlyphTable"]

    tex = obj_55.read()
    atlas_img = tex.image.convert("RGBA")
    atlas_w, atlas_h = atlas_img.size
    ch_r, ch_g, ch_b, ch_a = atlas_img.split()
    alpha_arr = np.array(ch_a)

    font_64 = ImageFont.truetype(ttf_path, size=64)

    # Place Persian glyphs in the unused top area of PIL image (Y=50..2500 is completely empty)
    cursor_x = 20
    cursor_y = 50
    row_height = 0
    padding = 2

    import copy
    max_g_idx = max(g["m_Index"] for g in glyph_table) if glyph_table else 0
    next_g_idx = max_g_idx + 1

    added_chars = 0
    existing_unicodes = {c["m_Unicode"] for c in char_table}
    c_proto = copy.deepcopy(char_table[0])
    g_proto = copy.deepcopy(glyph_table[0])

    for u in persian_unicodes:
        if u in existing_unicodes:
            continue

        ch = chr(u)
        try:
            mask = font_64.getmask(ch, mode="L")
            mw, mh = mask.size
            bbox = font_64.getbbox(ch, anchor="ls")
            adv = font_64.getlength(ch)
        except Exception:
            continue

        if not bbox or mw == 0 or mh == 0:
            w, h, bx, by = 0, 0, 0, 0
            unity_x, unity_y = 0, 0
        else:
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            bx = bbox[0]
            by = -bbox[1]

            mask_arr = np.array(mask).reshape((mh, mw)) > 128
            padded_mask = np.pad(mask_arr, padding, mode="constant", constant_values=False)
            patch_w = padded_mask.shape[1]
            patch_h = padded_mask.shape[0]

            inside = distance_transform_edt(padded_mask)
            outside = distance_transform_edt(~padded_mask)
            dist = inside - outside
            sdf_patch = np.clip(dist * 64.0 + 128.0, 0, 255).astype(np.uint8)

            if cursor_x + patch_w + 4 > atlas_w - 20:
                cursor_x = 20
                cursor_y += row_height + 4
                row_height = 0

            alpha_arr[cursor_y:cursor_y + patch_h, cursor_x:cursor_x + patch_w] = sdf_patch

            unity_y = atlas_h - cursor_y - patch_h + padding
            unity_x = cursor_x + padding

            cursor_x += patch_w + 4
            if patch_h > row_height:
                row_height = patch_h

        # Create new character entry
        new_c = copy.deepcopy(c_proto)
        new_c["m_Unicode"] = int(u)
        new_c["m_GlyphIndex"] = int(next_g_idx)
        new_c["m_Scale"] = 1.0
        char_table.append(new_c)

        # Create new glyph entry
        new_g = copy.deepcopy(g_proto)
        new_g["m_Index"] = int(next_g_idx)
        new_g["m_Metrics"] = {
            "m_Width": float(w),
            "m_Height": float(h),
            "m_HorizontalBearingX": float(bx),
            "m_HorizontalBearingY": float(by),
            "m_HorizontalAdvance": float(adv if adv else 0.0)
        }
        new_g["m_GlyphRect"] = {
            "m_X": int(unity_x),
            "m_Y": int(unity_y),
            "m_Width": int(w),
            "m_Height": int(h)
        }
        new_g["m_Scale"] = 1.0
        new_g["m_AtlasIndex"] = 0
        glyph_table.append(new_g)

        next_g_idx += 1
        added_chars += 1

    print(f"[✔] Appended {added_chars} new Persian characters and glyphs non-destructively!")

    # Save to obj.data
    obj_249.save_typetree(tree, font_node)

    new_alpha_img = Image.fromarray(alpha_arr, mode="L")
    new_atlas_img = Image.merge("RGBA", (ch_r, ch_g, ch_b, new_alpha_img))
    tex.image = new_atlas_img
    tex.save()

    # Save complete assets file
    res_bytes = env_res.file.save()
    with open(res_path, "wb") as f:
        f.write(res_bytes)

    print(f"[✔] Successfully saved non-destructive font patch into resources.assets ({len(res_bytes):,} bytes)!")
    return True

if __name__ == "__main__":
    game_path = "/Applications/Five Hearts Under One Roof 2.app"
    font = "/Users/ehsan/Documents/antigravity/bold-babbage/game_mod_toolkit/fonts/Lahzeh-Bold.ttf"
    trans = "/Users/ehsan/Documents/antigravity/bold-babbage/game_mod_toolkit/translations/persian"
    patch_resources_assets_in_place(game_path, font, trans)
