from __future__ import annotations

import re


FATHER_PATTERNS = [
    re.compile(r"\bfather(?:'s)?\s+name[:\s]+([A-Z][A-Za-z]+)", re.IGNORECASE),
    re.compile(r"\bojciec[:\s]+([A-Z][A-Za-z]+)", re.IGNORECASE),
]

PLACE_PATTERNS = [
    re.compile(r"\bborn\s+in\s+([A-Z][A-Za-z]+)", re.IGNORECASE),
    re.compile(r"\burodzon[ya]\s+w\s+([A-Z][A-Za-z]+)", re.IGNORECASE),
    re.compile(r"\bnarodzony\s+w\s+([A-Z][A-Za-z]+)", re.IGNORECASE),
]

MIGRATION_PATTERNS = [
    re.compile(r"\bmigrat(?:ed|ion).{0,20}\b(19\d{2}|20\d{2})\b", re.IGNORECASE),
    re.compile(r"\barrived.{0,20}\b(19\d{2}|20\d{2})\b", re.IGNORECASE),
]

OCCUPATION_HINTS = ["painter", "property repairer", "repairer", "decorator"]
MILITARY_HINTS = ["army", "armed forces", "military", "soviet", "west forces"]


def extract_claims_from_text(text: str, source_name: str, language: str = "unknown") -> list[dict[str, str]]:
    claims: list[dict[str, str]] = []
    cleaned = " ".join(text.split())

    for pattern in FATHER_PATTERNS:
        for match in pattern.finditer(cleaned):
            claims.append(
                {
                    "field_name": "father_name",
                    "value": match.group(1),
                    "source_name": source_name,
                    "source_type": "extracted",
                    "language": language,
                    "confidence": "0.65",
                    "note": "Auto-extracted from uploaded text",
                }
            )

    for pattern in PLACE_PATTERNS:
        for match in pattern.finditer(cleaned):
            claims.append(
                {
                    "field_name": "birthplace",
                    "value": match.group(1),
                    "source_name": source_name,
                    "source_type": "extracted",
                    "language": language,
                    "confidence": "0.62",
                    "note": "Auto-extracted from uploaded text",
                }
            )

    for pattern in MIGRATION_PATTERNS:
        for match in pattern.finditer(cleaned):
            claims.append(
                {
                    "field_name": "migration_year",
                    "value": match.group(1),
                    "source_name": source_name,
                    "source_type": "extracted",
                    "language": language,
                    "confidence": "0.6",
                    "note": "Auto-extracted from uploaded text",
                }
            )

    lowered = cleaned.lower()
    for occupation in OCCUPATION_HINTS:
        if occupation in lowered:
            claims.append(
                {
                    "field_name": "occupation",
                    "value": occupation,
                    "source_name": source_name,
                    "source_type": "extracted",
                    "language": language,
                    "confidence": "0.55",
                    "note": "Occupation keyword found in uploaded text",
                }
            )

    for military in MILITARY_HINTS:
        if military in lowered:
            claims.append(
                {
                    "field_name": "military_service",
                    "value": military,
                    "source_name": source_name,
                    "source_type": "extracted",
                    "language": language,
                    "confidence": "0.5",
                    "note": "Military keyword found in uploaded text",
                }
            )

    seen: set[tuple[str, str, str]] = set()
    unique_claims: list[dict[str, str]] = []
    for claim in claims:
        key = (claim["field_name"], claim["value"].lower(), claim["source_name"])
        if key in seen:
            continue
        seen.add(key)
        unique_claims.append(claim)
    return unique_claims
