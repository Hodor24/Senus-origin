from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime


def _now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


@dataclass
class TranslationRecord:
    document_id: str
    original_language: str
    target_language: str
    translated_text: str
    translation_type: str
    translator_method: str
    quality_flag: str
    translated_at: str
    original_sha256: str


def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def translate_document(
    document_id: str,
    original_bytes: bytes,
    original_language: str,
    target_language: str = "en",
    translation_type: str = "machine",
    translator_method: str = "placeholder-engine",
) -> TranslationRecord:
    text = original_bytes.decode("utf-8", errors="replace")
    translated_text = f"[translated {original_language}->{target_language}] {text}"
    quality_flag = "review_required" if translation_type == "machine" else "certified"
    return TranslationRecord(
        document_id=document_id,
        original_language=original_language,
        target_language=target_language,
        translated_text=translated_text,
        translation_type=translation_type,
        translator_method=translator_method,
        quality_flag=quality_flag,
        translated_at=_now_iso(),
        original_sha256=compute_sha256(original_bytes),
    )
