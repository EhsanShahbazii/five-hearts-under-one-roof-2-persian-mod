"""
Five Hearts Under One Roof 2 - Persian Subtitle Mod Patcher & Manager
Features:
- Automated non-destructive backup and 1-click restore
- Automatic Addressables CRC bypass in catalog.json
- RTL & BiDi text shaping for Unity TextMeshPro
- Custom font injection (Lahzeh / Vazirmatn)
- Scene-by-scene or full batch patching
- Standalone mod packaging for easy distribution
"""

import os
import glob
import json
import base64
import re
import shutil
import argparse
import UnityPy

from rtl_formatter import shape_persian
from sdf_font_baker import patch_resources_assets_in_place

TOOLKIT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_GAME_PATH = "/Applications/Five Hearts Under One Roof 2.app"
BACKUP_DIR = os.path.join(TOOLKIT_DIR, "backup")
PERSIAN_DIR = os.path.join(TOOLKIT_DIR, "translations", "persian")
FONTS_DIR = os.path.join(TOOLKIT_DIR, "fonts")

def get_bundle_dir(game_app_path: str) -> str:
    return os.path.join(
        game_app_path,
        "Contents", "Resources", "Data", "StreamingAssets", "aa", "StandaloneOSX"
    )

def get_catalog_path(game_app_path: str) -> str:
    return os.path.join(
        game_app_path,
        "Contents", "Resources", "Data", "StreamingAssets", "aa", "catalog.json"
    )

def patch_catalog_crc(game_app_path: str, backup_dir: str = None) -> bool:
    catalog_path = get_catalog_path(game_app_path)
    if not os.path.exists(catalog_path):
        print(f"[!] catalog.json not found at: {catalog_path}")
        return False

    if backup_dir:
        os.makedirs(backup_dir, exist_ok=True)
        bak_file = os.path.join(backup_dir, "catalog.json.original")
        if not os.path.exists(bak_file):
            shutil.copy2(catalog_path, bak_file)
            print(f"[✔] Backed up original catalog.json")

    with open(catalog_path, "r", encoding="utf-8") as f:
        cat = json.load(f)

    raw = base64.b64decode(cat["m_ExtraDataString"])

    def replace_crc(match):
        full = match.group(0)
        prefix = '"m_Crc":'.encode("utf-16le")
        digits_bytes = full[len(prefix):]
        digit_count = len(digits_bytes) // 2
        replacement_str = "0" + " " * (digit_count - 1)
        return prefix + replacement_str.encode("utf-16le")

    pattern = re.compile(re.escape('"m_Crc":'.encode("utf-16le")) + rb'(?:[\x30-\x39]\x00)+')
    new_raw = pattern.sub(replace_crc, raw)
    cat["m_ExtraDataString"] = base64.b64encode(new_raw).decode("ascii")

    with open(catalog_path, "w", encoding="utf-8") as f:
        json.dump(cat, f, separators=(",", ":"))

    print("[✔] Successfully bypassed Addressables CRC validation in catalog.json")
    return True

def find_bundle_for_scene(bundle_dir: str, scene_id: str) -> str:
    pattern = os.path.join(bundle_dir, f"ccscripts_assets_{scene_id}.json_*.bundle")
    matches = glob.glob(pattern)
    if not matches:
        pattern_lower = os.path.join(bundle_dir, f"ccscripts_assets_{scene_id.lower()}.json_*.bundle")
        matches = glob.glob(pattern_lower)
    return matches[0] if matches else None

def patch_subtitle_bundle(bundle_path: str, translated_json_path: str, backup_dir: str = None) -> bool:
    if not os.path.exists(bundle_path):
        print(f"[!] Bundle not found: {bundle_path}")
        return False

    with open(translated_json_path, "r", encoding="utf-8") as f:
        translations = json.load(f)

    # Backup original bundle if not already backed up
    if backup_dir:
        os.makedirs(backup_dir, exist_ok=True)
        bak_file = os.path.join(backup_dir, os.path.basename(bundle_path) + ".original")
        if not os.path.exists(bak_file):
            shutil.copy2(bundle_path, bak_file)
            print(f"[✔] Backed up original: {os.path.basename(bundle_path)}")

    # Map translations by INDEX
    trans_map = {}
    for item in translations:
        idx = item.get("INDEX")
        script = item.get("SCRIPT", {})
        fa_text = script.get("PERSIAN") or script.get("ENGLISH")
        if idx is not None and fa_text:
            trans_map[idx] = fa_text

    # Load from original backup if available to ensure pristine ENGLISH text is preserved
    source_bundle = bak_file if (backup_dir and os.path.exists(bak_file)) else bundle_path
    env = UnityPy.load(source_bundle)
    modified = False

    for obj in env.objects:
        if obj.type.name == "TextAsset":
            data = obj.read()
            script_json = json.loads(data.m_Script)
            for item in script_json:
                idx = item.get("INDEX")
                if idx in trans_map and "SCRIPT" in item and isinstance(item["SCRIPT"], dict):
                    raw_persian = trans_map[idx]
                    shaped = shape_persian(raw_persian)
                    # Inject Persian into KOREAN slot; ENGLISH remains 100% factory English!
                    item["SCRIPT"]["KOREAN"] = shaped
                    modified = True

            if modified:
                data.m_Script = json.dumps(script_json, ensure_ascii=False)
                data.save()

    if modified:
        with open(bundle_path, "wb") as f:
            f.write(env.file.save())
        return True
    return False

def apply_patch(game_app_path: str, scene_filter: str = None, font_choice: str = "lahzeh"):
    bundle_dir = get_bundle_dir(game_app_path)
    if not os.path.exists(bundle_dir):
        print(f"[!] Game directory not found at: {game_app_path}")
        return

    print("==================================================")
    print(" Five Hearts Under One Roof 2 - Subtitle Patcher")
    print("==================================================")
    print(f"[*] Target Game: {game_app_path}")
    print(f"[*] Backup Dir:  {BACKUP_DIR}")

    # 1. Bypass CRC in catalog.json
    patch_catalog_crc(game_app_path, BACKUP_DIR)

    # 2. Bake Font SDF (In-Place)
    primary_font = os.path.join(FONTS_DIR, "Lahzeh-Bold.ttf" if font_choice.lower() == "lahzeh" else "Vazirmatn-Bold.ttf")
    patch_resources_assets_in_place(game_app_path, primary_font, PERSIAN_DIR, BACKUP_DIR)

    # 3. Patch Subtitles
    translation_files = glob.glob(os.path.join(PERSIAN_DIR, "*.json"))
    if not translation_files:
        print(f"[!] No translation files found in {PERSIAN_DIR}")
        return

    patched_count = 0
    for tf in translation_files:
        scene_id = os.path.basename(tf).replace(".json", "")
        if scene_filter and scene_filter not in scene_id:
            continue

        bundle_path = find_bundle_for_scene(bundle_dir, scene_id)
        if not bundle_path:
            print(f"[!] Warning: No bundle found for scene {scene_id}")
            continue

        ok = patch_subtitle_bundle(bundle_path, tf, BACKUP_DIR)
        if ok:
            print(f"[✔] Successfully patched scene: {scene_id}")
            patched_count += 1

    print(f"\n[✨] Complete! Patched {patched_count} scenes.")
    print("Run the game and make sure Language is set to 'English' to see Persian subtitles!")

def restore_all(game_app_path: str):
    bundle_dir = get_bundle_dir(game_app_path)
    catalog_path = get_catalog_path(game_app_path)
    if not os.path.exists(BACKUP_DIR):
        print("[!] No backup directory found to restore.")
        return

    print("==================================================")
    print(" Restoring Original Game Files...")
    print("==================================================")

    # Restore catalog.json
    catalog_bak = os.path.join(BACKUP_DIR, "catalog.json.original")
    if os.path.exists(catalog_bak):
        shutil.copy2(catalog_bak, catalog_path)
        print("[✔] Restored original catalog.json")

    backups = glob.glob(os.path.join(BACKUP_DIR, "*.original"))
    restored = 0
    for b in backups:
        orig_name = os.path.basename(b).replace(".original", "")
        if orig_name == "catalog.json":
            continue
        elif orig_name == "resources.assets":
            dest = os.path.join(game_app_path, "Contents", "Resources", "Data", orig_name)
        else:
            dest = os.path.join(bundle_dir, orig_name)
        shutil.copy2(b, dest)
        print(f"[✔] Restored: {orig_name}")
        restored += 1

    print(f"\n[✨] Restore complete! {restored + 1} original files restored.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Subtitle & Font Patcher")
    parser.add_argument("--game-path", default=DEFAULT_GAME_PATH, help="Path to game .app")
    parser.add_argument("--apply", action="store_true", help="Apply Persian subtitles & font")
    parser.add_argument("--restore", action="store_true", help="Restore factory original game files")
    parser.add_argument("--scene", default=None, help="Patch specific scene, e.g. 1_06_0_1")
    parser.add_argument("--font", default="lahzeh", choices=["lahzeh", "vazirmatn"], help="Font family to use")
    args = parser.parse_args()

    if args.restore:
        restore_all(args.game_path)
    elif args.apply or args.scene:
        apply_patch(args.game_path, scene_filter=args.scene, font_choice=args.font)
    else:
        parser.print_help()
