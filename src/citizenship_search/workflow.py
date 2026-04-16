from __future__ import annotations

from uuid import uuid4

from citizenship_search.matching import likely_explanation_for_conflict, rank_candidates, reconcile_claim_conflicts
from citizenship_search.models import CaseFile, Claim, RetrievalAttempt, SourceReference
from citizenship_search.normalization import normalize_name, normalize_occupation, normalize_place
from citizenship_search.outputs import citizenship_bundle_draft, discovery_report, missing_document_packet
from citizenship_search.sources import build_default_adapters, create_archive_request
from citizenship_search.translation import TranslationRecord, translate_document


def discover_case_documents(case_file: CaseFile, query: str) -> tuple[list, list[TranslationRecord]]:
    hits = []
    translations: list[TranslationRecord] = []
    for adapter in build_default_adapters():
        adapter_hits = adapter.search(query)
        if adapter_hits:
            hits.extend(adapter_hits)
            case_file.retrieval_attempts.append(
                RetrievalAttempt(
                    attempt_id=str(uuid4()),
                    source_name=adapter.name,
                    query=query,
                    success=True,
                    message=f"found {len(adapter_hits)} hits",
                )
            )
        else:
            case_file.retrieval_attempts.append(
                RetrievalAttempt(
                    attempt_id=str(uuid4()),
                    source_name=adapter.name,
                    query=query,
                    success=False,
                    message="no hits",
                )
            )
    ranked = rank_candidates(case_file, hits)

    for candidate in ranked[:4]:
        doc_bytes = candidate.hit.summary.encode("utf-8")
        if candidate.hit.jurisdiction in {"Poland", "Ukraine", "Russia"}:
            translations.append(
                translate_document(
                    document_id=candidate.hit.document_id,
                    original_bytes=doc_bytes,
                    original_language="pl" if candidate.hit.jurisdiction == "Poland" else "uk",
                )
            )
    return ranked, translations


def seed_claims(case_file: CaseFile) -> None:
    source = SourceReference(
        source_id=str(uuid4()),
        source_name="seed_certificates",
        jurisdiction="UK",
        archive="User-provided",
        retrieval_method="manual_upload",
    )
    case_file.claims.extend(
        [
            Claim(
                claim_id=str(uuid4()),
                subject_id=case_file.subject.person_id,
                field_name="birthplace",
                extracted_text="Born in Poland",
                normalized_value=normalize_place("Poland"),
                confidence=0.9,
                source=source,
            ),
            Claim(
                claim_id=str(uuid4()),
                subject_id=case_file.subject.person_id,
                field_name="father_name",
                extracted_text="Michal",
                normalized_value=normalize_name("Michal"),
                confidence=0.7,
                source=source,
            ),
            Claim(
                claim_id=str(uuid4()),
                subject_id=case_file.subject.person_id,
                field_name="father_name",
                extracted_text="Mikolaj",
                normalized_value=normalize_name("Mikolaj"),
                confidence=0.65,
                source=source,
            ),
            Claim(
                claim_id=str(uuid4()),
                subject_id=case_file.subject.person_id,
                field_name="occupation",
                extracted_text="property repairer & painter",
                normalized_value=normalize_occupation("property repairer"),
                confidence=0.8,
                source=source,
            ),
        ]
    )
    case_file.claims = reconcile_claim_conflicts(case_file)


def build_discovery_outputs(case_file: CaseFile, query: str) -> dict[str, object]:
    seed_claims(case_file)
    ranked, translations = discover_case_documents(case_file, query)
    request = create_archive_request(
        repository_name="Archiwum Panstwowe",
        language="pl",
        contact_email="archive@example.org",
        person_name=case_file.subject.canonical_name,
        birthplace="Stryj",
        year_range="1930-1960",
    )

    conflict_values = {c.normalized_value for c in case_file.claims if c.field_name == "father_name"}
    return {
        "discovery_report": discovery_report(ranked),
        "missing_documents": missing_document_packet(case_file, ranked),
        "bundle_draft": citizenship_bundle_draft(case_file),
        "archive_requests": [request],
        "translation_records": translations,
        "conflict_explanation": likely_explanation_for_conflict("father_name", conflict_values),
    }
