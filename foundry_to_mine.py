import json
import requests
from pathlib import Path
import os
from django.core.management.base import BaseCommand

# where this file lives
BASE_DIR = Path(__file__).resolve().parent.parent.parent
json_path = BASE_DIR / "database_index.json"
save_dir = BASE_DIR / "downloaded_jsons"
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
skills = {
    "free action": 0,
    "reaction": -1,
}
dc_by_level = {
    0:"DC 14",
    1:"DC 15",
    2:"DC 16",
    3:"DC 18",
    4:"DC 19",
    5:"DC 20",
    6:"DC 22",
    7:"DC 23",
    8:"DC 24",
    9:"DC 26",
    10:"DC 27",
    11:"DC 28",
    12:"DC 30",
    13:"DC 31",
    14:"DC 32",
    15:"DC 34",
    16:"DC 35",
    17:"DC 36",
    18:"DC 38",
    19:"DC 39",
    20:"DC 40",
    21:"DC 42",
    22:"DC 44",
    23:"DC 46",
    24:"DC 48",
    25:"DC 50",
}
skill_by_tradition = {
    "Construct":"Arcana or Crafting",
    "Elemental":"Arcana",
    "Beast":"Arcana or Nature",
    "Animal":"Nature",
    "Fey":"Nature",
    "Plant":"Nature",
    "Aberration":"Occultism",
    "Spirit":"Occultism",
    "Ooze":"Occultism",
    "Celestial":"Religion",
    "Fiend":"Religion",
    "Undead":"Religion",
}

def get_spellcasting(items):
    traditions = []
    spells = []
    for item in items:
        if item["type"] == "spellcastingEntry":
            item_detail = item["system"]
            focusPoints = {
                    "current": item_detail["resources"]["focus"]["max"],
                    "max": item_detail["resources"]["focus"]["max"]
                }if item_detail["prepared"]["value"] == "focus" else {
                    "current": 0,
                    "max": 0
                }
            def get_slots(detail, slot):
                if slot in detail:
                    return {
                        "current": detail[slot]["max"],
                        "max": detail[slot]["max"]
                        }
 
                return {
                    "current": 0,
                    "max": 0
                    }
            traditions.append(
                {"name": item["name"],
                "type": item_detail["prepared"]["value"],
                "bonus": item_detail["spelldc"]["value"],
                "dc": item_detail["spelldc"]["dc"],
                "focusPoints": focusPoints,
                #TODO
                "autoHeightenLevel": item_detail["spelldc"]["dc"],
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
                "lv1slots": get_slots(item_detail, "slot1"),
                "lv2slots": get_slots(item_detail, "slot2"),
                "lv3slots": get_slots(item_detail, "slot3"),
                "lv4slots": get_slots(item_detail, "slot4"),
                "lv5slots": get_slots(item_detail, "slot5"),
                "lv6slots": get_slots(item_detail, "slot6"),
                "lv7slots": get_slots(item_detail, "slot7"),
                "lv8slots": get_slots(item_detail, "slot8"),
                "lv9slots": get_slots(item_detail, "slot9"),
                "lv10slots": get_slots(item_detail, "slot10"),
                } 
            )
        elif item["type"] == "spell":
            spell_type = "cantrip" if "cantrip" in item_detail["traits"]["value"] else "spell"
            save_type = ""
            if "defense" in item_detail and "save" in item_detail["defense"]:
                save_type = ("Basic" if item_detail["defense"]["save"]["basic"] else "") + item_detail["defense"]["save"]["statistic"]
            spells.append(
                {"name": item["name"],
                "type": spell_type,
                "level": item_detail["level"]["value"],
                "traits": item_detail["traits"]["value"] - "cantrip",
                "castingTime": item_detail["time"]["value"],
                "duration": f"{"Sustained up to" if item_detail["duration"]["sustained"] else ""} {item_detail["duration"]["value"]}",
                "range": item_detail["range"]["value"],
                "area": item_detail["area"],
                "targets": item_detail["target"]["value"],
                "save": save_type,
                "description": item_detail["description"]["value"],
                "cast": False,
                "cost": item_detail["cost"]["value"],
                #TODO RITUAL
                "primaryCheck": "",
                "secondaryCasters": "",
                "secondaryChecks": "",
                "id": item["_id"]
                } 
            )
        for spell in spells:
            if "focus" in spell["traits"]:
                tradition_type = ["focus"]
            else:
                tradition_type = ["spontaneous", "prepared"]
            dict_name = spell["type"] + "s"
            if dict_name == "spells":
                dict_name = f"lvl{spell["level"]}spells"   
            for tradition in traditions:
                if tradition["type"] in tradition_type:
                    tradition[dict_name].append(spell)

def get_abilities(items, ability_type):
    # TODO CHECK
    def get_actions(item):
        action_type = item["actionType"]["value"]
        action_number = item["actions"]["value"]
        if action_number:
            return action_number
        else:
            return skills.get(action_type, None)
    return [{"name": item["name"], "actions": get_actions(item), "traits": item["system"]["traits"]["value"],
             "description": item["system"]["description"]["value"], "collapsed": False}
            for item in items
            if "category" in item["system"] and (
                (ability_type and item["system"]["category"] == ability_type) or
                (not ability_type and item["system"]["category"] not in (
                    "offensive", "defensive"))
    )
    ]


def transform_foundry_to_tracker(foundry_json):
    npc = {}
    sys = foundry_json["system"]

    init_bonus = 0
    if "mod" in sys[sys["initiative"]["statistic"]]:
        init_bonus = sys[sys["initiative"]["statistic"]]["mod"]
    elif "base" in sys[sys["initiative"]["statistic"]]:
        init_bonus = sys[sys["initiative"]["statistic"]]["base"]
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
        "type": "Creature",
        "level": sys["details"]["level"]["value"],
        "traits": traits,
        "source": sys["details"]["publication"]["title"],
    })

    # Perception
    npc["perception"] = {
        "value": sys["perception"]["mod"],
        # TODO CHECK THIS
        "note": ([sys["perception"]["details"]] + sys["perception"].get("senses", [])).join(","),
        "usedAttribute": "wisdom",
        "modifications": []
    }

    npc["senses"] = sys["perception"].get("senses", [])

    # Languages
    npc["languages"] = [lang.capitalize()
                        for lang in sys["details"]["languages"]["value"]]

    # Skills
    def get_special(data):
        specials = []
        if "special" in data:
            for special in data["special"]:
                specials.append(f"{special["label"]} {special["base"]}")
        return specials.join(", ")

    npc["skills"] = [
        {
            "name": name,
            "modifier": data["base"],
            "note": get_special(data),
            "usedAttribute": attr,
            # TODO SEE IF ANYTHING ELSE
            "modifications": []
        }
        for name, data in sys["skills"].items()
        for attr in [  # attribute mapping and lore by default
            skills.get(name, "intelligence")]
    ]
    npc["skills"].append(
        {
            "name": item["name"],
            "modifier": item["mod"]["value"],
            "note": "",
            "usedAttribute": "intelligence",
            # TODO SEE IF ANYTHING ELSE
            "modifications": []
        }
        for item in foundry_json["items"]
        if item["type"] == "lore"
    )

    # Ability scores
    for abbr, fullname in {
        "str": "strength", "dex": "dexterity", "con": "constitution",
        "int": "intelligence", "wis": "wisdom", "cha": "charisma"
    }.items():
        npc[fullname] = {"value": sys["abilities"][abbr]["mod"]}

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

    npc["generalAbilities"] = get_abilities(foundry_json["items"], "general")

    # AC and Saves #TODO CHECK SPECIAL CASES LIKE ANIMATED SWORD or similar
    npc["ac"] = {"value": sys["attributes"]["ac"]["value"],
                 "note": sys["attributes"]["ac"]["details"], "usedAttribute": "dexterity", "modifications": []}
    npc["fortitude"] = {"value": sys["saves"]["fortitude"]["value"],
                        "note": sys["saves"]["fortitude"]["saveDetail"], "usedAttribute": "constitution", "modifications": []}
    npc["reflex"] = {"value": sys["saves"]["reflex"]["value"],
                     "note": sys["saves"]["reflex"]["saveDetail"], "usedAttribute": "dexterity", "modifications": []}
    npc["will"] = {"value": sys["saves"]["will"]["value"],
                   "note": sys["saves"]["will"]["saveDetail"], "usedAttribute": "wisdom", "modifications": []}

    # TODO SAVENOTE?
    npc["savenote"] = ""

    npc["hp"] = {
        "value": sys["attributes"]["hp"]["value"],
        "max": sys["attributes"]["hp"]["max"],
        "note": sys["attributes"]["hp"]["details"],
        "modifications": []
    }

    for st in ["immunities", "resistances", "weaknesses"]:
        if st in sys["attributes"]:
            npc[st] = [s["type"] for s in sys["attributes"][st]]

    # DefensiveAbilities
    npc["generalAbilities"] = get_abilities(foundry_json["items"], None)

    # Speed
    npc["speed"] = f"{sys['attributes']['speed']['value']} ft," + f"{sys['attributes']['speed']['otherSpeeds'].join("ft, ")}"

    # Strikes (melee/ranged)
    npc["strikes"] = []
    for item in foundry_json["items"]:
        if item["type"] == "melee" or item["type"] == "ranged":
            strike = {
                "type": item["system"]["weaponType"]["value"],
                "name": item["name"],
                "bonus": item["system"]["bonus"]["value"],
                "traits": item["system"]["traits"]["value"],
                # TODO CHECK THIS WEIRD NUMBER
                "damageRolls": [{"roll": d["damage"], "type": d["damageType"]}
                                for d in item["system"]["damageRolls"].values()],
                "critRolls": [{"roll": f"({d['damage']})*2", "type": d["damageType"]}
                              for d in item["system"]["damageRolls"].values()],
                # TODO WHAT IS THIS
                "effects": item["system"]["attackEffects"]["value"],
                "usedAttributeToHit": "strength" if item["system"]["weaponType"]["value"] == "melee" and not "finesse" in item["system"]["traits"]["value"] else "dexterity",
                "usedAttributeDamage": "strength",
                # TODO CHECK THIS
                "toHitModifications": [],
                "damageModifications": []
            }
            npc["strikes"].append(strike)

    npc["offensiveAbilities"] = get_abilities(
        foundry_json["items"], "offensive")

    # TODO
    npc["spellCasting"] = get_spellcasting(foundry_json["items"])

    rk_skills=[]
    for trait in traits:
        if trait in skill_by_tradition:
            rk_skills.append(skill_by_tradition[trait])
    npc["recallKnowledge"] = rk_skills.join(" or ") + ", " + dc_by_level[npc["level"]]

    return npc


class Command(BaseCommand):
    help = 'Create development data'

    def handle(self, *args, **kwargs):
        with open("foundry_npc.json", encoding="utf-8") as f:
            foundry_data = json.load(f)

        tracker_json = transform_foundry_to_tracker(foundry_data)
        print(json.dumps(tracker_json, indent=2, ensure_ascii=False))
