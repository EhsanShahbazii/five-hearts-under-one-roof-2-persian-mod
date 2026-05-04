"""
Subtitle Extractor for Five Hearts Under One Roof 2
Extracts subtitle JSON files from Unity AssetBundles into readable JSON.
"""

import os
import glob
import json
import argparse
import UnityPy

DEFAULT_GAME_PATH = "/Applications/Five Hearts Under One Roof 2.app"

def get_bundle_dir(game_app_path: str) -> str:
    return os.path.join(
        game_app_path,
        "Contents", "Resources", "Data", "StreamingAssets", "aa", "StandaloneOSX"
    )

def extract_bundle(bundle_path: str, output_dir: str) -> str:
    env = UnityPy.load(bundle_path)
    extracted_file = None
    for obj in env.objects:
        if obj.type.name == "TextAsset":
            data = obj.read()
            name = getattr(data, "m_Name", None) or os.path.basename(bundle_path).split(".")[0]
            script_content = getattr(data, "m_Script", "")
            try:
                parsed = json.loads(script_content)
                out_path = os.path.join(output_dir, f"{name}.json")
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(parsed, f, ensure_ascii=False, indent=2)
                extracted_file = out_path
            except Exception as e:
                print(f"[!] Error parsing JSON in {bundle_path}: {e}")
    return extracted_file

def extract_all(game_app_path: str, output_dir: str, filter_scene: str = None):
    bundle_dir = get_bundle_dir(game_app_path)
    if not os.path.exists(bundle_dir):
        raise FileNotFoundError(f"Cannot find bundle directory: {bundle_dir}")
    
    os.makedirs(output_dir, exist_ok=True)
    pattern = os.path.join(bundle_dir, "ccscripts_assets_*.bundle")
    bundles = glob.glob(pattern)
    print(f"[*] Found {len(bundles)} subtitle bundle files in {bundle_dir}")
    
    count = 0
    for b in bundles:
        base = os.path.basename(b)
        if filter_scene and filter_scene not in base:
            continue
        res = extract_bundle(b, output_dir)
        if res:
            count += 1
            if count <= 5 or filter_scene:
                print(f" [+] Extracted: {os.path.basename(res)}")
    print(f"[✔] Successfully extracted {count} subtitle files to {output_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract game subtitles from AssetBundles")
    parser.add_argument("--game-path", default=DEFAULT_GAME_PATH, help="Path to game app bundle")
    parser.add_argument("--out-dir", default=os.path.join(os.path.dirname(__file__), "translations", "raw"), help="Output directory")
    parser.add_argument("--scene", default=None, help="Extract only specific scene, e.g. 1_06_0_1")
    args = parser.parse_args()

    extract_all(args.game_path, args.out_dir, args.scene)
