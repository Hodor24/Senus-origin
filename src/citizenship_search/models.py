from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4


def _now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


class ClaimStatus(str, Enum):
    ACTIVE = "active"
    CONFLICTING = "conflicting"
    REJECTED = "rejected"


@dataclass
class SourceReference:
    source_id: str
    source_name: str
    jurisdiction: str
    archive: str
    retrieval_method: str
    retrieved_at: str = field(default_factory=_now_iso)
    source_url: str | None = None
    notes: str | None = None


@dataclass
class Claim:
    claim_id: str
    subject_id: str
    field_name: str
    extracted_text: str
    normalized_value: str
    confidence: float
    source: SourceReference
    status: ClaimStatus = ClaimStatus.ACTIVE
    conflict_group: str | None = None

    def as_record(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "subject_id": self.subject_id,
            "field_name": self.field_name,
            "extracted_text": self.extracted_text,
            "normalized_value": self.normalized_value,
            "confidence": round(self.confidence, 4),
            "status": self.status.value,
            "conflict_group": self.conflict_group,
            "source": self.source.__dict__,
        }


@dataclass
class PersonProfile:
    person_id: str
    canonical_name: str
    aliases: list[str] = field(default_factory=list)
    father_name_variants: list[str] = field(default_factory=list)
    place_variants: list[str] = field(default_factory=list)
    occupation_variants: list[str] = field(default_factory=list)
    timeline_facts: list[str] = field(default_factory=list)


@dataclass
class RetrievalAttempt:
    attempt_id: str
    source_name: str
    query: str
    success: bool
    message: str
    attempted_at: str = field(default_factory=_now_iso)


@dataclass
class CaseFile:
    case_id: str
    subject: PersonProfile
    claims: list[Claim] = field(default_factory=list)
    retrieval_attempts: list[RetrievalAttempt] = field(default_factory=list)

    @classmethod
    def for_roman_senus(cls) -> "CaseFile":
        subject = PersonProfile(
            person_id=str(uuid4()),
            canonical_name="Roman Senus",
            aliases=["Roman Senus"],
            father_name_variants=["Michal", "Michael", "Mikolaj"],
            place_variants=["Stryj", "Stryi", "Stryy"],
            occupation_variants=["property repairer", "painter"],
            timeline_facts=["migrated to UK in 1957", "army service 1945-1947", "army service 1945-1948"],
        )
        return cls(case_id=str(uuid4()), subject=subject)
