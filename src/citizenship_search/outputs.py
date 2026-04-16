from __future__ import annotations

from collections import defaultdict

from citizenship_search.matching import RankedCandidate
from citizenship_search.models import CaseFile, ClaimStatus
from citizenship_search.sources.manual_intake import ArchiveRequest


def build_timeline(case_file: CaseFile) -> list[dict[str, str]]:
    timeline = []
    for claim in case_file.claims:
        timeline.append(
            {
                "field": claim.field_name,
                "value": claim.normalized_value,
                "status": claim.status.value,
                "source": claim.source.source_name,
                "archive": claim.source.archive,
                "retrieved_at": claim.source.retrieved_at,
            }
        )
    timeline.sort(key=lambda item: item["retrieved_at"])
    return timeline


def discovery_report(candidates: list[RankedCandidate], threshold: float = 0.55) -> dict[str, list[dict[str, str]]]:
    strong: list[dict[str, str]] = []
    weak: list[dict[str, str]] = []
    for c in candidates:
        row = {
            "document_id": c.hit.document_id,
            "title": c.hit.title,
            "source": c.hit.source_name,
            "score": f"{c.score:.2f}",
            "note": "; ".join(c.explanation),
        }
        if c.score >= threshold:
            strong.append(row)
        else:
            weak.append(row)
    return {"strong_matches": strong, "needs_review": weak}


def missing_document_packet(case_file: CaseFile, candidates: list[RankedCandidate]) -> dict[str, list[str]]:
    by_archive = defaultdict(list)
    found_ids = {c.hit.document_id for c in candidates}
    required = {
        "uk-death-2014-roman-senus": "certified death certificate copy",
        "uk-marriage-roman-senus": "certified marriage certificate copy",
        "pl-military-1945-1947": "Polish military service confirmation",
        "paw-return-1948-senus": "Armed Forces in West return file",
    }
    for doc_id, desc in required.items():
        if doc_id not in found_ids:
            by_archive["unassigned"].append(desc)
    for attempt in case_file.retrieval_attempts:
        if not attempt.success:
            by_archive[attempt.source_name].append(f"retry query: {attempt.query}")
    return dict(by_archive)


def citizenship_bundle_draft(case_file: CaseFile) -> dict[str, object]:
    active_claims = [c for c in case_file.claims if c.status != ClaimStatus.REJECTED]
    warnings = []
    fields = {}
    for claim in active_claims:
        fields.setdefault(claim.field_name, set()).add(claim.normalized_value)
    for field_name, values in fields.items():
        if len(values) > 1:
            warnings.append(f"non-conclusive evidence for {field_name}: {', '.join(sorted(values))}")
    return {
        "subject": case_file.subject.canonical_name,
        "chronology": build_timeline(case_file),
        "warnings": warnings,
        "disclaimer": "Research support only; obtain legal advice before filing.",
    }


def archive_request_export(requests: list[ArchiveRequest]) -> list[dict[str, str]]:
    return [
        {
            "request_id": r.request_id,
            "repository": r.repository_name,
            "language": r.language,
            "due_date": r.due_date,
            "status": r.status,
            "fee_estimate": r.fee_estimate,
        }
        for r in requests
    ]
