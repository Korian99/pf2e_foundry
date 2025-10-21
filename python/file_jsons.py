import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
def get_lang_json():
    lang_file = BASE_DIR.parent / "static" / "lang" / "en.json"
    with open(lang_file, encoding="utf-8") as f:
        lang_json = json.load(f)
    return lang_json
def get_compendium():
    compendium_file = BASE_DIR / "compendium.json"
    with open(compendium_file, encoding="utf-8") as f:
        compendium = json.load(f)
    return compendium