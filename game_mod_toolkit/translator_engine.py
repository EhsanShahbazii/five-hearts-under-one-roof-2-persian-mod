"""
Master Translation Engine for Five Hearts Under One Roof 2
Uses high-speed Google Chrome Extension translation endpoint with colloquial Persian post-processor.
"""

import os
import glob
import json
import re
import html
import time
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

TOOLKIT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(TOOLKIT_DIR, "translations", "raw")
PERSIAN_DIR = os.path.join(TOOLKIT_DIR, "translations", "persian")
CACHE_FILE = os.path.join(TOOLKIT_DIR, "translations", "translation_cache.json")

os.makedirs(PERSIAN_DIR, exist_ok=True)

# -------------------------------------------------------------
# Colloquial Persian Post-Processor (محاوره‌ساز پیشرفته)
# -------------------------------------------------------------

REPLACEMENTS = [
    # Remove formal question particles
    (r"^\s*آیا\s+", ""),
    (r"\bآیا\s+", ""),
    
    # Common verb contractions (formal -> colloquial)
    (r"\bمی‌توانم\b", "می‌تونم"),
    (r"\bمی‌توانی\b", "می‌تونی"),
    (r"\bمی‌تواند\b", "می‌تونه"),
    (r"\bمی‌توانیم\b", "می‌تونیم"),
    (r"\bمی‌توانید\b", "می‌تونین"),
    (r"\bمی‌توانند\b", "می‌تونن"),
    (r"\bنمی‌توانم\b", "نمی‌تونم"),
    (r"\bنمی‌توانی\b", "نمی‌تونی"),
    (r"\bنمی‌تواند\b", "نمی‌تونه"),
    (r"\bنمی‌توانیم\b", "نمی‌تونیم"),
    (r"\bنمی‌توانید\b", "نمی‌تونین"),
    (r"\bنمی‌توانند\b", "نمی‌تونن"),

    (r"\bمی‌خواهم\b", "می‌خوام"),
    (r"\bمی‌خواهی\b", "می‌خوای"),
    (r"\bمی‌خواهد\b", "می‌خواد"),
    (r"\bمی‌خواهیم\b", "می‌خوایم"),
    (r"\bمی‌خواهید\b", "می‌خواین"),
    (r"\bمی‌خواهند\b", "می‌خوان"),
    (r"\bنمی‌خواهم\b", "نمی‌خوام"),
    (r"\bنمی‌خواهی\b", "نمی‌خوای"),
    (r"\bنمی‌خواهد\b", "نمی‌خواد"),
    (r"\bنمی‌خواهیم\b", "نمی‌خوایم"),
    (r"\bنمی‌خواهید\b", "نمی‌خواین"),
    (r"\bنمی‌خواهند\b", "نمی‌خوان"),

    (r"\bمی‌گویم\b", "می‌گم"),
    (r"\bمی‌گویی\b", "می‌گی"),
    (r"\bمی‌گوید\b", "می‌گه"),
    (r"\bمی‌گوییم\b", "می‌گیم"),
    (r"\bمی‌گویید\b", "می‌گین"),
    (r"\bمی‌گویند\b", "می‌گن"),
    (r"\bنمی‌گویم\b", "نمی‌گم"),
    (r"\bنمی‌گویی\b", "نمی‌گی"),
    (r"\bنمی‌گوید\b", "نمی‌گه"),
    (r"\bنمی‌گویند\b", "نمی‌گن"),

    (r"\bمی‌روم\b", "می‌رم"),
    (r"\bمی‌روی\b", "می‌ری"),
    (r"\bمی‌رود\b", "می‌ره"),
    (r"\bمی‌رویم\b", "می‌ریم"),
    (r"\bمی‌روید\b", "می‌رین"),
    (r"\bمی‌روند\b", "می‌رن"),
    (r"\bنمی‌روم\b", "نمی‌رم"),
    (r"\bنمی‌روی\b", "نمی‌ری"),
    (r"\bنمی‌رود\b", "نمی‌ره"),
    (r"\bنمی‌روند\b", "نمی‌رن"),

    (r"\bمی‌شوم\b", "می‌شم"),
    (r"\bمی‌شوی\b", "می‌شی"),
    (r"\bمی‌شود\b", "می‌شه"),
    (r"\bمی‌شویم\b", "می‌شیم"),
    (r"\bمی‌شوید\b", "می‌شین"),
    (r"\bمی‌شوند\b", "می‌شن"),
    (r"\bنمی‌شوم\b", "نمی‌شم"),
    (r"\bنمی‌شوی\b", "نمی‌شی"),
    (r"\bنمی‌شود\b", "نمی‌شه"),
    (r"\bنمی‌شویم\b", "نمی‌شیم"),
    (r"\bنمی‌شوید\b", "نمی‌شین"),
    (r"\bنمی‌شوند\b", "نمی‌شن"),

    (r"\bمی‌کند\b", "می‌کنه"),
    (r"\bمی‌کنید\b", "می‌کنین"),
    (r"\bمی‌کنند\b", "می‌کنن"),
    (r"\bنمی‌کند\b", "نمی‌کنه"),
    (r"\bنمی‌کنید\b", "نمی‌کنین"),
    (r"\bنمی‌کنند\b", "نمی‌کنن"),

    (r"\bمی‌دانم\b", "می‌دونم"),
    (r"\bمی‌دانی\b", "می‌دونی"),
    (r"\bمی‌داند\b", "می‌دونه"),
    (r"\bمی‌دانیم\b", "می‌دونیم"),
    (r"\bمی‌دانید\b", "می‌دونین"),
    (r"\bمی‌دانند\b", "می‌دونن"),
    (r"\bنمی‌دانم\b", "نمی‌دونم"),
    (r"\bنمی‌دانی\b", "نمی‌دونی"),
    (r"\bنمی‌داند\b", "نمی‌دونه"),
    (r"\bنمی‌دانیم\b", "نمی‌دونیم"),
    (r"\bنمی‌دانید\b", "نمی‌دونین"),
    (r"\bنمی‌دانند\b", "نمی‌دونن"),

    (r"\bخواهید بود\b", "می‌شین"),
    (r"\bخواهد بود\b", "می‌شه"),
    (r"\bخواهیم بود\b", "می‌شیم"),
    (r"\bخواهم بود\b", "می‌شم"),
    (r"\bممکن است\b", "ممکنه"),
    (r"\bخیر،\b", "نه،"),
    (r"\bخیر\b", "نه"),

    # Pronouns & Demonstratives
    (r"\bاین را\b", "اینو"),
    (r"\bآن را\b", "اونو"),
    (r"\bآنها را\b", "اونا رو"),
    (r"\bاینها را\b", "اینا رو"),
    (r"\bآنها\b", "اونا"),
    (r"\bآنان\b", "اونا"),
    (r"\bآن\b", "اون"),
    (r"\bاینها\b", "اینا"),
    (r"\bاینطور\b", "اینطوری"),
    (r"\bآنطور\b", "اونطوری"),
    (r"\bاینجا است\b", "اینجاست"),
    (r"\bآنجا است\b", "اونجاست"),
    (r"\bکجا است\b", "کجاست"),
    (r"\bچه کسی است\b", "کیه"),
    (r"\bکیست\b", "کیه"),
    (r"\bچیست\b", "چیه"),
    (r"\bشما هستید\b", "شمایین"),
    (r"\bما هستیم\b", "ماییم"),
    (r"\bایشان\b", "ایشون"),
    (r"\bاو را\b", "اونو"),

    # Conversational nouns
    (r"\bخانه\b", "خونه"),
    (r"\bنان\b", "نون"),
    (r"\bجان\b", "جون"),
    (r"\bتهران\b", "تهرون"),
    (r"\bباران\b", "بارون"),
    (r"\bدندان\b", "دندون"),
    (r"\bآسمان\b", "آسمون"),
    (r"\bهمان\b", "همون"),
    (r"\bمیان\b", "میون"),

    # Common phrases & expressions
    (r"\bچه خبر است\b", "چه خبره"),
    (r"\bچه اتفاقی افتاده است\b", "چی شده مگه"),
    (r"\bچه اتفاقی افتاده\b", "چی شده"),
    (r"\bچه کار می‌کنی\b", "چیکار می‌کنی"),
    (r"\bچه‌کار می‌کنی\b", "چیکار می‌کنی"),
    (r"\bچه می‌کنی\b", "چیکار می‌کنی"),
    (r"\bچه می‌گویی\b", "چی داری می‌گی"),
    (r"\bچه شد\b", "چی شد"),
    (r"\bچطور است\b", "چطوره"),
    (r"\bچگونه است\b", "چطوره"),
    (r"\bبسیار خب\b", "خیلی خب"),
    (r"\bمتشکرم\b", "ممنونم"),
    (r"\bسپاسگزارم\b", "دستت درد نکنه"),
    (r"\bنگران نباشید\b", "نگران نباش"),
    (r"\bمعذرت می‌خواهم\b", "ببخشید، شرمنده"),
    (r"\bبه نظر می‌رسد\b", "انگار"),
    (r"\bبرای چه\b", "واسه چی"),
    (r"\bاز این جهت\b", "واسه همین"),
    (r"\bبه این دلیل\b", "به خاطر همین"),
    (r"\bواقعاً؟\b", "جدی؟"),
    (r"\bخداحافظ\b", "فعلاً، خدافظ"),

    # Character names
    (r"\bیو مان\b", "یومان"),
    (r"\bیومان\b", "یومان"),
    (r"\bمالسوک\b", "مال‌سوک"),
    (r"\bمال سوک\b", "مال‌سوک"),
    (r"\bیونا\b", "یونا"),
    (r"\bمینجونگ\b", "مین‌جونگ"),
    (r"\bمین جونگ\b", "مین‌جونگ"),
    (r"\bگران\b", "گران"),
    (r"\bایونبی\b", "ایون‌بی"),
    (r"\bایون بی\b", "ایون‌بی"),
    (r"\bسئونگیی\b", "سئونگ‌یی"),
    (r"\bسوجی\b", "سوجی"),
    (r"\bیوجونگ\b", "یو-جونگ"),
    (r"\bاوننی\b", "آبجی"),
    (r"\bاوپا\b", "یومان"),
    (r"\bهیونگ\b", "داداش"),
    (r"\bآجوما\b", "خاله"),
    (r"\bآجوشی\b", "عمو"),
]

def colloquialize(text: str) -> str:
    if not text:
        return ""
    t = html.unescape(text).strip()
    for pattern, rep in REPLACEMENTS:
        t = re.sub(pattern, rep, t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

def translate_google_chrome(text: str) -> str:
    """Translates text to Persian via Google Chrome translate endpoint."""
    if not text or not text.strip():
        return ""
    q = urllib.parse.quote(text)
    url = f"https://clients5.google.com/translate_a/t?client=dict-chrome-ex&sl=en&tl=fa&q={q}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        res = json.loads(resp.read().decode())
        if isinstance(res, list) and len(res) > 0:
            return res[0]
        elif isinstance(res, str):
            return res
        return text

def translate_scene_file(raw_path: str, persian_path: str) -> bool:
    with open(raw_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Check if file is already translated with real Persian
    if os.path.exists(persian_path):
        pdata = json.load(open(persian_path))
        has_all_persian = True
        for it in pdata:
            if "SCRIPT" in it:
                fa = it["SCRIPT"].get("PERSIAN", "")
                if not re.search(r"[\u0600-\u06FF]", fa) and (it["SCRIPT"].get("ENGLISH") or it["SCRIPT"].get("KOREAN")):
                    has_all_persian = False
                    break
        if has_all_persian:
            return True

    lines_to_translate = []
    indices_to_translate = []

    for idx, item in enumerate(data):
        if "SCRIPT" in item:
            en = str(item["SCRIPT"].get("ENGLISH") or "").strip()
            kr = str(item["SCRIPT"].get("KOREAN") or "").strip()
            text = en or kr
            if text:
                lines_to_translate.append(text)
                indices_to_translate.append(idx)
            else:
                item["SCRIPT"]["PERSIAN"] = ""

    if lines_to_translate:
        combined_text = "\n".join(lines_to_translate)
        try:
            translated_blob = translate_google_chrome(combined_text)
            translated_lines = translated_blob.split("\n")
            if len(translated_lines) == len(lines_to_translate):
                for orig_idx, fa_text in zip(indices_to_translate, translated_lines):
                    data[orig_idx]["SCRIPT"]["PERSIAN"] = colloquialize(fa_text)
            else:
                # Fallback line by line
                for orig_idx, orig_text in zip(indices_to_translate, lines_to_translate):
                    fa_line = translate_google_chrome(orig_text)
                    data[orig_idx]["SCRIPT"]["PERSIAN"] = colloquialize(fa_line)
                    time.sleep(0.02)
        except Exception as e:
            # Fallback line by line
            for orig_idx, orig_text in zip(indices_to_translate, lines_to_translate):
                try:
                    fa_line = translate_google_chrome(orig_text)
                    data[orig_idx]["SCRIPT"]["PERSIAN"] = colloquialize(fa_line)
                    time.sleep(0.02)
                except Exception:
                    data[orig_idx]["SCRIPT"]["PERSIAN"] = orig_text

    with open(persian_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return True

def translate_all_scenes(max_workers: int = 10):
    raw_files = sorted(glob.glob(os.path.join(RAW_DIR, "*.json")))
    print(f"[*] Starting full translation of {len(raw_files)} scenes using Chrome endpoint ({max_workers} threads)...")

    start_time = time.time()
    completed = 0
    total = len(raw_files)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {}
        for rf in raw_files:
            sid = os.path.basename(rf).replace(".json", "")
            pf = os.path.join(PERSIAN_DIR, f"{sid}.json")
            future = executor.submit(translate_scene_file, rf, pf)
            future_to_file[future] = sid

        for future in as_completed(future_to_file):
            sid = future_to_file[future]
            try:
                future.result()
                completed += 1
                if completed % 50 == 0 or completed == total:
                    elapsed = time.time() - start_time
                    rate = completed / (elapsed + 0.001)
                    rem = (total - completed) / rate if rate > 0 else 0
                    print(f"[{completed}/{total}] ({completed/total*100:.1f}%) Completed: {sid} | Speed: {rate:.1f} scenes/sec | Est. remaining: {rem:.1f}s")
            except Exception as e:
                print(f"[!] Error translating {sid}: {e}")

    print(f"[✔] Translation completed in {time.time()-start_time:.1f} seconds!")

if __name__ == "__main__":
    translate_all_scenes(max_workers=10)
