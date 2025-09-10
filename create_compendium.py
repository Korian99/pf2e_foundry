import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
packs_dir = BASE_DIR / "packs"

def iter_json_files(root: Path):
    """Recursively yield .json files from folders containing 'bestiary' or 'core'."""
    for path in root.rglob("*.json"):
        yield path

def create_compendium():
    tracker_json = {}  # list of dicts

    for json_file in iter_json_files(packs_dir):
        try:
            with open(json_file, encoding="utf-8") as f:
                data = json.load(f)
            
            if "_id" in data and "name" in data:
                tracker_json[data["_id"]] = data["name"]

        except Exception as e:
            print(f"Error with {json_file}: {e}")

    out_path = BASE_DIR / "compendium.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(tracker_json, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(tracker_json)} entries to {out_path}")

if __name__ == "__main__":
    create_compendium()