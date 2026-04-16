from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from uuid import uuid4

from citizenship_search.models import CaseFile, Claim, ClaimStatus
from citizenship_search.normalization import expand_aliases, normalize_name, normalize_occupation, normalize_place
from citizenship_search.sources.base import SourceHit

WEIGHTS = {
    "name": 0.35,
    "father_name": 0.2,
    "place": 0.2,
    "occupation": 0.1,
    "timeline": 0.15,
}


@dataclass
class RankedCandidate:
    hit: SourceHit
    score: float
    explanation: list[str]


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def rank_candidates(case_file: CaseFile, hits: list[SourceHit]) -> list[RankedCandidate]:
    subject = case_file.subject
    ranked: list[RankedCandidate] = []
    for hit in hits:
        blob = f"{hit.title} {hit.summary}".lower()
        score = 0.0
        explanation: list[str] = []

        name_similarity = max(_similarity(normalize_name(alias), normalize_name(blob)) for alias in subject.aliases)
        score += name_similarity * WEIGHTS["name"]
        explanation.append(f"name similarity={name_similarity:.2f}")

        father_aliases = set()
        for father_name in subject.father_name_variants:
            father_aliases.update(expand_aliases(father_name))
        father_match = 1.0 if any(alias in blob for alias in father_aliases) else 0.0
        score += father_match * WEIGHTS["father_name"]
        explanation.append(f"father variant match={father_match:.2f}")

        place_match = 1.0 if any(normalize_place(p) in normalize_place(blob) for p in subject.place_variants) else 0.0
        score += place_match * WEIGHTS["place"]
        explanation.append(f"place match={place_match:.2f}")

        occupation_match = 1.0 if any(normalize_occupation(o) in normalize_occupation(blob) for o in subject.occupation_variants) else 0.0
        score += occupation_match * WEIGHTS["occupation"]
        explanation.append(f"occupation match={occupation_match:.2f}")

        timeline_match = 1.0 if any(fact.split()[-1] in blob for fact in subject.timeline_facts) else 0.0
        score += timeline_match * WEIGHTS["timeline"]
        explanation.append(f"timeline cue match={timeline_match:.2f}")

        ranked.append(RankedCandidate(hit=hit, score=round(score, 4), explanation=explanation))
    ranked.sort(key=lambda item: item.score, reverse=True)
    return ranked


def reconcile_claim_conflicts(case_file: CaseFile) -> list[Claim]:
    grouped: dict[str, list[Claim]] = {}
    for claim in case_file.claims:
        grouped.setdefault(claim.field_name, []).append(claim)

    resolved: list[Claim] = []
    for field_name, claims in grouped.items():
        unique_values = {c.normalized_value for c in claims}
        if len(unique_values) <= 1:
            resolved.extend(claims)
            continue

        conflict_group = str(uuid4())
        strongest = max(claims, key=lambda c: c.confidence)
        for claim in claims:
            claim.conflict_group = conflict_group
            if claim is strongest:
                claim.status = ClaimStatus.ACTIVE
            else:
                claim.status = ClaimStatus.CONFLICTING
            resolved.append(claim)
    return resolved


def likely_explanation_for_conflict(field_name: str, values: set[str]) -> str:
    if field_name == "father_name":
        return (
            "Father name variation may come from transliteration differences "
            "(e.g., Michal/Michael/Mikolaj) or clerical entry inconsistencies."
        )
    if field_name == "military_service":
        return "Different military indexes may reflect overlapping service systems and archival coding."
    return f"Multiple values observed: {', '.join(sorted(values))}."
