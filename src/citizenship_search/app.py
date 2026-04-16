from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict
from typing import Any

from citizenship_search.models import CaseFile, EvidenceClaim, SubjectProfile, TranslationCopy
from citizenship_search.normalize import expand_name_aliases, expand_place_aliases


def seed_case() -> CaseFile:
    subject = SubjectProfile(
        full_name="Roman Senus",
        aliases=["Roman Senus"],
        father_name_variants=["Michal", "Michael", "Mikolaj"],
        birthplace_variants=["Poland", "Stryj", "Stryi"],
        occupation_variants=["Property repairer", "Painter"],
        timeline_cues=["1945-1947", "1945-1948", "1957", "2014"],
    )
    claims = [
        EvidenceClaim("birthplace", "Poland", "Death certificate", "civil", "en", 0.95),
        EvidenceClaim("father_name", "Michal", "Marriage certificate", "civil", "en", 0.78),
        EvidenceClaim("father_name", "Mikolaj", "Armed Forces in West index", "military", "en", 0.63),
        EvidenceClaim("birthplace", "Stryj", "Manchester alien record", "police", "en", 0.86),
        EvidenceClaim("migration_year", "1957", "Manchester alien record", "police", "en", 0.91),
        EvidenceClaim("military_service", "1945-1947 Soviet-linked", "military card", "military", "en", 0.74),
        EvidenceClaim("military_service", "1945-1948 West forces return", "PAFW return list", "military", "en", 0.66),
    ]
    return CaseFile(subject=subject, claims=claims, translations=[])


def attach_translation(case_file: CaseFile, source_name: str, text: str, original_language: str) -> None:
    english = f"[EN translation] {text}"
    case_file.translations.append(
        TranslationCopy(
            source_name=source_name,
            original_language=original_language,
            original_text=text,
            english_text=english,
        )
    )


def build_discovery_report(case_file: CaseFile, query: str) -> dict[str, Any]:
    query_l = query.lower()
    alias_hits = [alias for alias in case_file.subject.aliases if alias.lower() in query_l]
    place_hits = []
    for place in case_file.subject.birthplace_variants:
        if expand_place_aliases(place) & {query_l, *query_l.split()}:
            place_hits.append(place)

    grouped = defaultdict(list)
    for claim in case_file.claims:
        grouped[claim.field_name].append(claim)

    conflicts: list[dict[str, Any]] = []
    for field_name, field_claims in grouped.items():
        values = {claim.value.lower() for claim in field_claims}
        if len(values) > 1:
            conflicts.append(
                {
                    "field": field_name,
                    "values": sorted(values),
                    "sources": sorted({claim.source_name for claim in field_claims}),
                }
            )

    father_alias_pool = set()
    for name in case_file.subject.father_name_variants:
        father_alias_pool |= expand_name_aliases(name)

    archive_requests = [
        {
            "repository": "Manchester Archive and Local Studies",
            "request_focus": "Alien registration file scan and full metadata",
            "priority": "high",
        },
        {
            "repository": "Polish State Archives",
            "request_focus": "Military personnel confirmation for 1945-1948 period",
            "priority": "high",
        },
        {
            "repository": "Lviv Regional Archives (Stryi records)",
            "request_focus": "Birth/baptism candidates and household registers",
            "priority": "medium",
        },
    ]

    return {
        "subject": case_file.subject.full_name,
        "query": query,
        "query_hits": {"aliases": alias_hits, "places": sorted(set(place_hits))},
        "father_name_alias_pool": sorted(father_alias_pool),
        "claims": [asdict(c) for c in case_file.claims],
        "conflicts": conflicts,
        "translations": [asdict(t) for t in case_file.translations],
        "archive_requests": archive_requests,
    }
