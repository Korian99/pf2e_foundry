import json
from pathlib import Path
from transform_foundry_to_tracker import transform_foundry_to_tracker

BASE_DIR = Path(__file__).resolve().parent
packs_dir = BASE_DIR / "packs"
jsons_dir = BASE_DIR / "jsons"
jsons_dir.mkdir(exist_ok=True)

# load index
with open(BASE_DIR / "database_index.json", encoding="utf-8") as f:
    db_index = json.load(f)

# set of names already in index
index_names = {entry["name"] for entry in db_index}

def iter_json_files(root: Path):
    """Recursively yield .json files from folders containing 'bestiary' or 'core'."""
    for path in root.rglob("*.json"):
        # check if any part of the path contains the substring
        if any("bestiary" in part.lower() or "core" in part.lower() for part in path.parts):
            yield path

def main():
    for json_file in iter_json_files(packs_dir):
        try:
            with open(json_file, encoding="utf-8") as f:
                foundry_data = json.load(f)
        except Exception as e:
            # print(f"❌ Could not load {json_file}: {e}")
            continue
        try:
            creature_name = foundry_data.get("name")
        except Exception as e:
            print(e)
            # print(f"❌ Could not load {json_file}: {e}")
            continue
        if not creature_name:
            # print(f"⚠️ Skipping {json_file}, no 'name' field found")
            continue

        # if creature_name in index_names:
            # print(f"✔ Skipping {creature_name}, already in index")
            # continue

        # transform
        tracker_json = transform_foundry_to_tracker(foundry_data)
        if tracker_json:
            # safe filename
            out_name = creature_name.replace(" ", "_").replace("/", "_").replace('"', "'")+".json"
            out_path = jsons_dir / out_name

            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(tracker_json, f, indent=2, ensure_ascii=False)
            if creature_name == "Temteki":
                print(f"✅ Wrote {out_path}")

if __name__ == "__main__":
    main()