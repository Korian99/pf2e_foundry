import re
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
lang_file = BASE_DIR / "static" / "lang" / "en.json"
with open(lang_file, encoding="utf-8") as f:
    lang_json = json.load(f)
compendium_file = BASE_DIR / "compendium.json"
with open(compendium_file, encoding="utf-8") as f:
    compendium = json.load(f)
saving_throws = {
    "fortitude", "reflex", "will"
}
skills = {
    "acrobatics": "dexterity",
    "arcana": "intelligence",
    "athletics": "strength",
    "crafting": "intelligence",
    "deception": "charisma",
    "diplomacy": "charisma",
    "intimidation": "charisma",
    "medicine": "wisdom",
    "nature": "wisdom",
    "occultism": "intelligence",
    "performance": "charisma",
    "religion": "wisdom",
    "society": "intelligence",
    "stealth": "dexterity",
    "survival": "wisdom",
    "thievery": "dexterity",
}
actions_type = {
    "free": 0,
    "reaction": -1,
}
dc_by_level = {
    -2: "DC 12",
    -1: "DC 13",
    0: "DC 14",
    1: "DC 15",
    2: "DC 16",
    3: "DC 18",
    4: "DC 19",
    5: "DC 20",
    6: "DC 22",
    7: "DC 23",
    8: "DC 24",
    9: "DC 26",
    10: "DC 27",
    11: "DC 28",
    12: "DC 30",
    13: "DC 31",
    14: "DC 32",
    15: "DC 34",
    16: "DC 35",
    17: "DC 36",
    18: "DC 38",
    19: "DC 39",
    20: "DC 40",
    21: "DC 42",
    22: "DC 44",
    23: "DC 46",
    24: "DC 48",
    25: "DC 50",
}
skill_by_tradition = {
    "Aberration": "Occultism",
    "Animal": "Nature",
    "Astral": "Occultism",
    "Beast": "Arcana or Nature",
    "Celestial": "Religion",
    "Construct": "Arcana or Crafting",
    "Dragon": "Arcana",
    "Dream": "Occultism",
    "Elemental": "Arcana or Nature",
    "Ethereal": "Occultism",
    "Fey": "Nature",
    "Fiend": "Religion",
    "Fungus": "Nature",
    "Humanoid": "Society",
    "Monitor": "Religion",
    "Ooze": "Occultism",
    "Plant": "Nature",
    "Shade": "Religion",
    "Spirit": "Occultism",
    "Time": "Occultism",
    "Undead": "Religion",
}
excluded_abilities = {
    "tremorsense",
    "telepathy",
    "status to all saves",
    "constant spell",
    "darkvision",
}



macro_pattern = re.compile(r"\[\[\/[^\]]+\]\]\{(?P<val>[^\}]+)\}")
clean_pattern = re.compile(r"@\w+\[[^\]]+\]\{(?P<val>[^\}]+)\}")
uuid_pattern = re.compile(r"@UUID\[(?P<key>[^\]]+)\]")
check_pattern = re.compile(r"@Check\[(?P<skill>[a-zA-Z]+)\|dc:(?P<dc>\d+)(?:\|[^\]]+)?\]")
localize_pattern = re.compile(r"@Localize\[(?P<key>[^\]]+)\]")
damage_pattern = re.compile(r"@Damage\[(?P<dice>[^\[]+)\[(?P<element>[^\]]+)\].*?\]")
template_pattern = re.compile(r"@Template\[(?P<type>[^\|]+)\|distance:(?P<dist>\d+)\]")


def get_nested(data, dotted_key: str, default=None):
    """Walk through nested dicts using dot notation."""
    current = data
    for part in dotted_key.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return default
    return current

def simplify_uuid(text: str) -> str:
    def repl(match):
        inside = match.group(1)          # everything inside [ ... ]
        last_part = inside.split(".")[-1]  # take the last piece
        return last_part
    def replace_uuid(text: str) -> str:
        def replacer(match):

            full_key = match.group("key")
            last_key = full_key.split(".")[-1]
            return compendium.get(last_key, last_key)  
        return uuid_pattern.sub(replacer, text)
    def replace_check(text: str) -> str:
        basic = "Basic "  if "basic" in text else ""
        return replace_uuid(check_pattern.sub(lambda m: f"{basic}DC {m.group('dc')} {m.group('skill').capitalize()} {'Saving Throw' if m.group('skill') in saving_throws else ''}", text))
    def replace_template(text: str) -> str:
        def repl(match):
            t_type = match.group("type").capitalize()  # e.g., "burst"
            dist = match.group("dist")
            return f"{dist}ft {t_type}"
        
        return replace_check(template_pattern.sub(repl, text))
    def replace_damage(text: str) -> str:
        def repl(match):
            dice = match.group("dice")  # e.g., "9d6"
            element = match.group("element").capitalize()  # e.g., "fire" → "Fire"
            return f"{dice} {element} Damage"
        
        return replace_template(damage_pattern.sub(repl, text))
    def localize(text: str) -> str:
        def replacer(match):
            key = match.group("key")
            localized_value = get_nested(lang_json, key, key)
            return (
                f"<details><summary>See rules...</summary>\n"
                f"<p>{localized_value}</p></details>"
            )
        return replace_damage(localize_pattern.sub(replacer, text))
    if text:
        text = clean_pattern.sub(lambda m: m.group("val"), text)
        text = macro_pattern.sub(lambda m: m.group("val"), text)
        return re.sub(r"@\w+\[([^\]]+)\]", repl, localize(text))
    return text

def clean_uuid(text: str) -> str:
    first = re.sub(r"@UUID\[Compendium\.pf2e\.spell-effects[^\]]*\]", "", text)
    return simplify_uuid(first)

def get_spellcasting(items):
    traditions = []
    spells = []
    for item in items:
        item_detail = item["system"]
        if item["type"] == "spellcastingEntry":
            focusPoints = {
                "current": item_detail["resources"]["focus"]["max"],
                "max": item_detail["resources"]["focus"]["max"]
            }if item_detail["prepared"]["value"] == "focus" and "resources" in item_detail else {
                "current": 0,
                "max": 0
            }

            def get_slots(detail, slot):
                if slot in detail and detail[slot].get("max", None):
                    return {
                        "current": detail[slot]["max"],
                        "max": detail[slot]["max"]
                    }
                return {
                    "current": 0,
                    "max": 0
                }
            item_detail_slots = item_detail["slots"]
            traditions.append(
                {"name": item["name"],
                 "type": item_detail["prepared"]["value"],
                 "bonus": item_detail["spelldc"]["value"],
                 "dc": item_detail["spelldc"]["dc"],
                 "focusPoints": focusPoints,
                 "autoHeightenLevel": 1,
                 "cantrips": [],
                 "lv1spells": [],
                 "lv2spells": [],
                 "lv3spells": [],
                 "lv4spells": [],
                 "lv5spells": [],
                 "lv6spells": [],
                 "lv7spells": [],
                 "lv8spells": [],
                 "lv9spells": [],
                 "lv10spells": [],
                 "rituals": [],
                 "lv1slots": get_slots(item_detail_slots, "slot1"),
                 "lv2slots": get_slots(item_detail_slots, "slot2"),
                 "lv3slots": get_slots(item_detail_slots, "slot3"),
                 "lv4slots": get_slots(item_detail_slots, "slot4"),
                 "lv5slots": get_slots(item_detail_slots, "slot5"),
                 "lv6slots": get_slots(item_detail_slots, "slot6"),
                 "lv7slots": get_slots(item_detail_slots, "slot7"),
                 "lv8slots": get_slots(item_detail_slots, "slot8"),
                 "lv9slots": get_slots(item_detail_slots, "slot9"),
                 "lv10slots": get_slots(item_detail_slots, "slot10"),
                 }
            )
            
        elif item["type"] == "spell":
            spell_type = "cantrip" if "cantrip" in item_detail["traits"]["value"] else "spell"
            save_type = ""
            if item_detail.get("defense", None) and item_detail["defense"].get("save", None):
                save_type = ("Basic " if item_detail["defense"]["save"]["basic"]
                             else "") + item_detail["defense"]["save"]["statistic"]
            sustain = "Sustained up to " if item_detail["duration"]["sustained"] else ""
            traits = [t for t in item_detail["traits"]
                      ["value"] if t != "cantrip"]
            area = ''
            if item_detail["area"] and item_detail["area"]["value"]:
                area = str(item_detail["area"]["value"]) + \
                    "ft " + item_detail["area"]["type"]
            uses = 1
            if item_detail["location"].get("uses", None):
                uses = item_detail["location"]["uses"].get("max", 1)
            ritual = item_detail.get("ritual", None)
            if ritual:
                primaryCheck = ritual["primary"]["check"]
                secondaryCasters = ritual["secondary"]["casters"]
                secondaryCheck = ritual["secondary"]["checks"]
                spell_type = "ritual"
            spells.append(
                {"name": item["name"],
                 "type": spell_type,
                 "level": item_detail["level"]["value"],
                 "heightenedLevel": item_detail["location"].get("heightenedLevel", item_detail["level"]["value"]),
                 "timesPrepared": uses,
                 "traits": traits,
                 "castingTime": item_detail["time"]["value"],
                 "duration": f"{sustain}{item_detail['duration']['value']}",
                 "range": item_detail["range"]["value"],
                 "area": area,
                 "targets": item_detail["target"]["value"],
                 "save": save_type,
                 "description": clean_uuid(item_detail["description"]["value"]),
                 "cast": False,
                 "cost": item_detail["cost"]["value"],
                 # TODO RITUAL
                 "primaryCheck": primaryCheck if ritual else "",
                 "secondaryCasters":  secondaryCasters if ritual else "",
                 "secondaryChecks":  secondaryCheck if ritual else "",
                 "id": item["_id"]
                 }
            )
    for spell in spells:
        if "focus" in spell["traits"]:
            tradition_type = ["focus"]
        else:
            tradition_type = ["spontaneous", "prepared", "innate"]
        dict_name = spell["type"] + "s"
        if dict_name == "spells":
            dict_name = "lv"+str(spell["heightenedLevel"])+"spells"
        for tradition in traditions:
            if tradition["type"] in tradition_type:
                i = 0
                while i < spell["timesPrepared"]:
                    i+=1
                    tradition[dict_name].append(spell)
                    tradition["autoHeightenLevel"] = max(spell["heightenedLevel"], tradition["autoHeightenLevel"])
    return traditions


def get_abilities(items, ability_type):
    # TODO CHECK
    def should_include(item):
        name = item["name"].lower()
        return all(excluded.lower() not in name for excluded in excluded_abilities)
    def get_actions(item):
        action_type = item["actionType"]["value"]
        action_number = item["actions"]["value"]
        if action_number:
            return action_number
        else:
            return actions_type.get(action_type, None)
    return [{"name": item["name"], "actions": get_actions(item["system"]), "traits": item["system"]["traits"]["value"],
             "description": simplify_uuid(item["system"]["description"]["value"]), "collapsed": False}
            for item in items
            if "category" in item["system"] and item["type"] == "action" and should_include(item) and (
                (ability_type and item["system"]["category"] == ability_type) or
                (not ability_type and item["system"]["category"] not in (
                    "offensive", "defensive"))
    )
    ]

def get_common_0(npc, foundry_json, npc_type, lores=[]):
    
    sys = foundry_json["system"]
    init_bonus = 0
    if "initiative" in sys:
        skill = sys["initiative"]["statistic"]
        skill_dict = sys["perception"]
        if "skills" in sys and sys["skills"].get(skill):
            skill_dict = sys["skills"][skill]
        else:
            for lore in lores:
                if lore.get(skill.replace("-", " ").capitalize, None):
                    skill_dict = sys["skills"][skill]
        if "mod" in skill_dict:
            init_bonus = skill_dict["mod"]
        elif "base" in skill_dict:
            init_bonus = skill_dict["base"]
    elif "stealth" in sys["attributes"]:
        init_bonus = sys["attributes"]["stealth"]["value"]
    size = sys["traits"]["size"]["value"]
    match size:
        case "sm": size = "Small"
        case "med": size = "Medium"
        case "lg": size = "Large"
        case "grg": size = "Gargantuan"
    traits = [sys["traits"]["rarity"].capitalize()] + [size] + [t.capitalize()
                                                                for t in sys["traits"]["value"]]
    npc.update({
        "initiative": 0,
        "initiativebonus": init_bonus,
        "comments": "",
        "conditions": [],
        "color": "#fff",
        "duplicateIndex": 0,
        "name": foundry_json["name"],
        "type": npc_type,
        "level": sys["details"]["level"]["value"],
        "traits": traits,
        "source": sys["details"]["publication"]["title"],
    })

    return npc
def get_common_1(npc, foundry_json):
    sys = foundry_json["system"]
    attributes = sys["attributes"]
     # TODO CHECK SPECIAL
    npc["items"] = [
        {
            "name": item["name"],
            "quantity": item["system"].get("quantity", 1),
            "description": item["system"]["description"]["value"],
            "level": item["system"]["level"]["value"],
            "price": " ".join(f"{v} {k}" for k, v in item["system"]["price"]["value"].items()),
            "traits": item["system"]["traits"]["value"],
        }
        for item in foundry_json["items"]
        if item["type"] in ("weapon", "armor", "equipment")
    ]

    npc["generalAbilities"] = get_abilities(foundry_json["items"], None)

    # AC and Saves #TODO CHECK SPECIAL CASES LIKE ANIMATED SWORD or similar
    npc["ac"] = {"value": attributes["ac"]["value"],
                 "note": attributes["ac"].get("details"), "usedAttribute": "dexterity", "modifications": []}
    if attributes.get("hardness", None):
        npc["hardness"] = {"value": attributes["hardness"]}
    npc["fortitude"] = {"value": sys["saves"]["fortitude"]["value"],
                        "note": sys["saves"]["fortitude"].get("saveDetail"), "usedAttribute": "constitution", "modifications": []}
    npc["reflex"] = {"value": sys["saves"]["reflex"]["value"],
                     "note": sys["saves"]["reflex"].get("saveDetail"), "usedAttribute": "dexterity", "modifications": []}
    npc["will"] = {"value": sys["saves"]["will"]["value"],
                   "note": sys["saves"]["will"].get("saveDetail"), "usedAttribute": "wisdom", "modifications": []}
    npc["savenote"] = ""
    if attributes.get("allSaves", None):
        npc["savenote"] = attributes["allSaves"]["value"]

    npc["hp"] = {
        "value": attributes["hp"]["value"],
        "max": attributes["hp"]["max"],
        "note": attributes["hp"]["details"],
        "modifications": []
    }

    for st in ["immunities", "resistances", "weaknesses"]:
        npc[st] = []
        if st in attributes:
            npc[st] = [s["type"] if not s.get("value", None) else s for s in attributes[st]]
        
        # DefensiveAbilities
    npc["defensiveAbilities"] = get_abilities(
        foundry_json["items"], "defensive")

    # Speed
    npc["speed"] = ""
    if attributes.get("speed", None):
        other_speeds = [speed["type"]+" " +
                        str(speed["value"])+"ft" for speed in sys['attributes']['speed']['otherSpeeds']]
        other_speeds = ", ".join(other_speeds)
        npc["speed"] = f"{sys['attributes']['speed']['value']} ft, " + other_speeds

    # Strikes (melee/ranged)
    npc["strikes"] = []
    for item in foundry_json["items"]:
        if item["type"] == "melee" or item["type"] == "ranged":
            range_attack = item["system"]["weaponType"]["value"] if "weaponType" in item["system"] else item["type"]
            strike = {
                "type": range_attack,
                "name": item["name"],
                "bonus": item["system"]["bonus"]["value"],
                "traits": item["system"]["traits"]["value"],
                "damageRolls": [{"roll": d["damage"], "type": d["damageType"]}
                                for d in item["system"]["damageRolls"].values()],
                "critRolls": [{"roll": f"({d['damage']})*2", "type": d["damageType"]}
                              for d in item["system"]["damageRolls"].values()],
                # TODO WHAT IS THIS
                "effects": item["system"]["attackEffects"]["value"],
                "usedAttributeToHit": "strength" if range_attack == "melee" and not "finesse" in item["system"]["traits"]["value"] else "dexterity",
                "usedAttributeDamage": "strength",
                # TODO CHECK THIS
                "toHitModifications": [],
                "damageModifications": []
            }
            npc["strikes"].append(strike)

    npc["offensiveAbilities"] = get_abilities(
        foundry_json["items"], "offensive")

    # TODO IMPROVE
    npc["spellcastingEntries"] = get_spellcasting(foundry_json["items"])

    traits =  [t.capitalize() for t in sys["traits"]["value"]]
    rk_skills = []
    for trait in traits:
        if trait in skill_by_tradition:
            rk_skills.append(skill_by_tradition[trait])
    npc["recallKnowledge"] = " or ".join(
        rk_skills) + ", " + dc_by_level[npc["level"]]

    return npc


def hazard_data(foundry_json):
    npc = {}
    sys = foundry_json["system"]
    attributes = sys["attributes"]

    npc = get_common_0(npc, foundry_json, "Hazard")
    npc.update({
        "stealth": {"value": attributes["stealth"]["value"], "note": attributes["stealth"]["details"].replace("<p>", "").replace("</p>", "")},
        "description": simplify_uuid(sys["details"]["description"]),
        "disable": simplify_uuid(sys["details"]["disable"]),
        "reset": simplify_uuid(sys["details"]["reset"]),
        "routine": simplify_uuid(sys["details"]["routine"]),
    })
    npc = get_common_1(npc, foundry_json)

    return npc


def npc_data(foundry_json):
    npc = {}
    sys = foundry_json["system"]
    lores = [{
            "name": item["name"],
            "modifier": item["system"]["mod"]["value"],
            "note": "",
            "usedAttribute": "intelligence",
            # TODO SEE IF ANYTHING ELSE
            "modifications": []
        }
        for item in foundry_json["items"]
        if item["type"] == "lore"]
    npc = get_common_0(npc, foundry_json, "Creature", lores)

    # Perception
    npc["senses"] = []
    for sense in sys["perception"]["senses"]:
        s = sense.get("type", "").replace("-", " ").capitalize()
        if sense.get("range", ""):
            s += f" {str(sense.get('range'))}ft"
        if sense.get("acuity", None):
            s += f" {sense.get('acuity')}"
        npc["senses"].append(s)
    note = npc["senses"]
    if sys["perception"]["details"] != "":
        note.append(sys["perception"]["details"])
    npc["perception"] = {
        "value": sys["perception"]["mod"],
        # TODO CHECK THIS
        "note": ", ".join(note),
        "usedAttribute": "wisdom",
        "modifications": []
    }

    # Languages
    npc["languages"] = [lang.capitalize()
                        for lang in sys["details"]["languages"]["value"]]
    if sys["details"]["languages"].get("details", "") != "":
        npc["languages"].append(sys["details"]["languages"]["details"])
    # Skills
    def get_special(data):
        specials = []
        if "special" in data:
            for special in data["special"]:
                specials.append(special["label"]+" " + str(special["base"]))
        return specials

    npc["skills"] = [
        {
            "name": name,
            "modifier": data["base"],
            "note": get_special(data),
            "usedAttribute": attr,
            # TODO SEE IF ANYTHING ELSE
            "modifications": []
        }
        for name, data in sys.get("skills",{}).items()
        for attr in [  # attribute mapping and lore by default
            skills.get(name, "intelligence")]
    ]
    npc["skills"].extend(
        lores
    )

    # Ability scores
    for abbr, fullname in {
        "str": "strength", "dex": "dexterity", "con": "constitution",
        "int": "intelligence", "wis": "wisdom", "cha": "charisma"
    }.items():
        npc[fullname] = {"value": sys["abilities"][abbr]["mod"]}

    npc = get_common_1(npc, foundry_json)

    return npc


def transform_foundry_to_tracker(foundry_json):
    if foundry_json["type"] == 'npc':
        return npc_data(foundry_json)
    if foundry_json["type"] == 'hazard':
        return hazard_data(foundry_json)
