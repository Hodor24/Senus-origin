from __future__ import annotations

import re
import unicodedata

CYRILLIC_MAP = {
    "А": "A",
    "Б": "B",
    "В": "V",
    "Г": "H",
    "Ґ": "G",
    "Д": "D",
    "Е": "E",
    "Є": "Ye",
    "Ж": "Zh",
    "З": "Z",
    "И": "Y",
    "І": "I",
    "Ї": "Yi",
    "Й": "Y",
    "К": "K",
    "Л": "L",
    "М": "M",
    "Н": "N",
    "О": "O",
    "П": "P",
    "Р": "R",
    "С": "S",
    "Т": "T",
    "У": "U",
    "Ф": "F",
    "Х": "Kh",
    "Ц": "Ts",
    "Ч": "Ch",
    "Ш": "Sh",
    "Щ": "Shch",
    "Ю": "Yu",
    "Я": "Ya",
    "Ь": "",
    "Ъ": "",
}

CYRILLIC_MAP.update({k.lower(): v.lower() for k, v in CYRILLIC_MAP.items()})


NAME_ALIASES = {
    "michal": {"michael", "mikolaj", "mykhailo", "mihail"},
    "michael": {"michal", "mikolaj", "mykhailo", "mihail"},
    "mikolaj": {"michal", "michael", "mykola", "nikolai"},
    "stryj": {"stryi", "stryy", "стрий", "стрый"},
}

OCCUPATION_ALIASES = {
    "property repairer": {"repair worker", "handyman", "maintenance worker"},
    "painter": {"decorator", "house painter"},
}


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def transliterate_cyrillic(value: str) -> str:
    return "".join(CYRILLIC_MAP.get(ch, ch) for ch in value)


def canonical_text(value: str) -> str:
    value = transliterate_cyrillic(value.strip())
    value = strip_accents(value).lower()
    value = re.sub(r"[^a-z0-9\s-]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def expand_aliases(value: str) -> set[str]:
    canon = canonical_text(value)
    matches = {canon}
    if canon in NAME_ALIASES:
        matches.update(canonical_text(v) for v in NAME_ALIASES[canon])
    if canon in OCCUPATION_ALIASES:
        matches.update(canonical_text(v) for v in OCCUPATION_ALIASES[canon])
    return matches


def normalize_name(value: str) -> str:
    return canonical_text(value)


def normalize_place(value: str) -> str:
    canon = canonical_text(value)
    if canon in {"stryi", "stryy"}:
        return "stryj"
    return canon


def normalize_occupation(value: str) -> str:
    canon = canonical_text(value)
    if canon in {"decorator", "house painter"}:
        return "painter"
    if canon in {"repair worker", "maintenance worker", "handyman"}:
        return "property repairer"
    return canon
