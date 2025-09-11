import re
from file_jsons import get_compendium, get_lang_json
from dicts import saving_throws

compendium = get_compendium()
lang_json = get_lang_json()


macro_pattern = re.compile(r"\[\[\/[^\]]+\]\]\{(?P<val>[^\}]+)\}")
clean_pattern = re.compile(r"@\w+\[[^\]]+\]\{(?P<val>[^\}]+)\}")
uuid_pattern = re.compile(r"@UUID\[(?P<key>[^\]]+)\]")
check_pattern = re.compile(
    r"@Check\[(?P<skill>[a-zA-Z]+)\|dc:(?P<dc>\d+)(?:\|[^\]]+)?\]")
localize_pattern = re.compile(r"@Localize\[(?P<key>[^\]]+)\]")
damage_pattern = re.compile(
    r"@Damage\[(?P<dice>[^\[]+)\[(?P<element>[^\]]+)\].*?\]")
template_pattern = re.compile(
    r"@Template\[(?P<type>[^\|]+)\|distance:(?P<dist>\d+)\]")


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
        basic = "Basic " if "basic" in text else ""
        return replace_uuid(check_pattern.sub(lambda m: f"{basic}DC {m.group('dc')} {m.group('skill').capitalize()} {'Saving Throw' if m.group('skill') in saving_throws else ''}", text))

    def replace_template(text: str) -> str:
        def repl(match):
            t_type = match.group("type").capitalize()  # e.g., "burst"
            dist = match.group("dist")
            return f"{dist}ft {t_type}"

        return replace_check(template_pattern.sub(repl, text))

    def replace_damage(text: str) -> str:
        text = clean_pattern.sub(lambda m: m.group("val"), text)
        text = macro_pattern.sub(lambda m: m.group("val"), text)
        def repl(match):
            dice = match.group("dice")  # e.g., "9d6"
            # e.g., "fire" → "Fire"
            element = match.group("element").capitalize()
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