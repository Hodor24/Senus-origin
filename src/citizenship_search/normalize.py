from __future__ import annotations


NAME_ALIAS_MAP = {
    "michal": {"michal", "michael", "mykhailo"},
    "mikolaj": {"mikolaj", "mykola", "nikolai", "nikolay"},
}

PLACE_ALIAS_MAP = {
    "stryi": {"stryi", "stryj", "stryi", "stryj, poland", "stryj, ukraine"},
}


def normalize_token(value: str) -> str:
    return " ".join(value.lower().strip().split())


def expand_name_aliases(name: str) -> set[str]:
    token = normalize_token(name)
    aliases = {token}
    for values in NAME_ALIAS_MAP.values():
        if token in values:
            aliases |= values
    return aliases


def expand_place_aliases(place: str) -> set[str]:
    token = normalize_token(place)
    aliases = {token}
    for values in PLACE_ALIAS_MAP.values():
        if token in values:
            aliases |= values
    return aliases
