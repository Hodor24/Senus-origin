from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class SubjectProfile:
    full_name: str
    aliases: list[str]
    father_name_variants: list[str]
    birthplace_variants: list[str]
    occupation_variants: list[str]
    timeline_cues: list[str]


@dataclass
class EvidenceClaim:
    field_name: str
    value: str
    source_name: str
    source_type: str
    language: str
    confidence: float
    note: str = ""


@dataclass
class TranslationCopy:
    source_name: str
    original_language: str
    original_text: str
    english_text: str


@dataclass
class CaseFile:
    subject: SubjectProfile
    claims: list[EvidenceClaim] = field(default_factory=list)
    translations: list[TranslationCopy] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "subject": asdict(self.subject),
            "claims": [asdict(claim) for claim in self.claims],
            "translations": [asdict(copy) for copy in self.translations],
        }
