from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from citizenship_search.app import build_discovery_report
from citizenship_search.models import CaseFile, EvidenceClaim, SubjectProfile, TranslationCopy
from citizenship_search.export_bundle import write_evidence_bundle_files


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "case"


def save_case_snapshot(
    case_file: CaseFile,
    report: dict,
    uploaded_docs: list[dict[str, object]],
    base_dir: str = "data/cases",
) -> dict[str, str]:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    case_slug = _slugify(case_file.subject.full_name)
    case_dir = Path(base_dir) / f"{timestamp}-{case_slug}"
    documents_dir = case_dir / "documents"
    documents_dir.mkdir(parents=True, exist_ok=True)

    uploaded_file_paths: list[str] = []
    uploaded_doc_payloads: list[dict[str, str]] = []
    for item in uploaded_docs:
        filename = str(item.get("filename", "uploaded.txt"))
        text = str(item.get("text", ""))
        original_bytes = item.get("original_bytes")
        doc_path = documents_dir / filename
        if isinstance(original_bytes, bytes):
            doc_path.write_bytes(original_bytes)
        else:
            doc_path.write_text(text, encoding="utf-8")
        uploaded_file_paths.append(str(doc_path))
        uploaded_doc_payloads.append(
            {
                "filename": filename,
                "source_name": str(item.get("source_name", "")),
                "language": str(item.get("language", "")),
                "media_type": str(item.get("media_type", "")),
                "extractor": str(item.get("extractor", "")),
                "extraction_status": str(item.get("extraction_status", "")),
                "text": text,
            }
        )

    case_payload = {
        "saved_at": timestamp,
        "case_file": case_file.as_dict(),
        "report": report,
        "uploaded_documents": uploaded_doc_payloads,
    }
    snapshot_path = case_dir / "case.json"
    snapshot_path.write_text(json.dumps(case_payload, indent=2), encoding="utf-8")

    bundle_paths = write_evidence_bundle_files(
        case_dir=case_dir,
        case_file=case_file,
        report=report,
        uploaded_documents_summary=uploaded_doc_payloads,
    )

    bundle_preview = ""
    try:
        bundle_preview = Path(bundle_paths["bundle_md_path"]).read_text(encoding="utf-8")[:8000]
    except Exception:
        bundle_preview = ""

    return {
        "case_dir": str(case_dir),
        "snapshot_path": str(snapshot_path),
        "documents_dir": str(documents_dir),
        "uploaded_count": str(len(uploaded_file_paths)),
        **bundle_paths,
        "bundle_md_preview": bundle_preview,
    }


def list_saved_cases(base_dir: str = "data/cases") -> list[dict[str, str]]:
    base_path = Path(base_dir)
    if not base_path.exists():
        return []
    cases: list[dict[str, str]] = []
    for case_dir in sorted(base_path.iterdir(), reverse=True):
        snapshot_path = case_dir / "case.json"
        if not snapshot_path.exists():
            continue
        try:
            payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
            subject = payload.get("report", {}).get("subject") or payload.get("case_file", {}).get("subject", {}).get("full_name", case_dir.name)
            saved_at = payload.get("saved_at", case_dir.name.split("-", 1)[0])
        except json.JSONDecodeError:
            subject = case_dir.name
            saved_at = case_dir.name
        cases.append(
            {
                "id": case_dir.name,
                "subject": str(subject),
                "saved_at": str(saved_at),
                "snapshot_path": str(snapshot_path),
                "bundle_md_path": str(case_dir / "evidence_bundle.md"),
                "bundle_json_path": str(case_dir / "bundle.json"),
            }
        )
    return cases


def load_case_snapshot(case_id: str, base_dir: str = "data/cases") -> dict:
    snapshot_path = Path(base_dir) / case_id / "case.json"
    return json.loads(snapshot_path.read_text(encoding="utf-8"))


def casefile_from_dict(case_file_dict: dict) -> CaseFile:
    subject_dict = case_file_dict.get("subject", {})
    subject = SubjectProfile(
        full_name=str(subject_dict.get("full_name", "")),
        aliases=list(subject_dict.get("aliases", [])),
        father_name_variants=list(subject_dict.get("father_name_variants", [])),
        birthplace_variants=list(subject_dict.get("birthplace_variants", [])),
        occupation_variants=list(subject_dict.get("occupation_variants", [])),
        timeline_cues=list(subject_dict.get("timeline_cues", [])),
    )
    claims: list[EvidenceClaim] = []
    for claim_dict in case_file_dict.get("claims", []):
        try:
            conf = float(claim_dict.get("confidence", 0.5))
        except (TypeError, ValueError):
            conf = 0.5
        claims.append(
            EvidenceClaim(
                field_name=str(claim_dict.get("field_name", "")),
                value=str(claim_dict.get("value", "")),
                source_name=str(claim_dict.get("source_name", "")),
                source_type=str(claim_dict.get("source_type", "")),
                language=str(claim_dict.get("language", "")),
                confidence=conf,
                note=str(claim_dict.get("note", "")),
            )
        )
    translations: list[TranslationCopy] = []
    for t_dict in case_file_dict.get("translations", []):
        translations.append(
            TranslationCopy(
                source_name=str(t_dict.get("source_name", "")),
                original_language=str(t_dict.get("original_language", "")),
                original_text=str(t_dict.get("original_text", "")),
                english_text=str(t_dict.get("english_text", "")),
            )
        )
    return CaseFile(subject=subject, claims=claims, translations=translations)


def accept_draft_extracted_claims(
    case_id: str,
    accepted_indices: list[int],
    draft_claims: list[dict],
    base_dir: str = "data/cases",
) -> dict[str, object]:
    case_dir = Path(base_dir) / case_id
    snapshot_path = case_dir / "case.json"
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))

    report_dict = payload.get("report", {}) if isinstance(payload, dict) else {}
    query = str(report_dict.get("query", ""))
    uploaded_documents_summary = report_dict.get("uploaded_documents", payload.get("uploaded_documents", []))

    case_file = casefile_from_dict(payload.get("case_file", {}))

    existing_keys = {(c.field_name, c.value.lower(), c.source_name) for c in case_file.claims}
    for idx in accepted_indices:
        if idx < 0 or idx >= len(draft_claims):
            continue
        dc = draft_claims[idx] or {}
        field_name = str(dc.get("field_name", ""))
        value = str(dc.get("value", ""))
        source_name = str(dc.get("source_name", ""))
        key = (field_name, value.lower(), source_name)
        if key in existing_keys:
            continue

        try:
            conf = float(dc.get("confidence", 0.5))
        except (TypeError, ValueError):
            conf = 0.5
        case_file.claims.append(
            EvidenceClaim(
                field_name=field_name,
                value=value,
                source_name=source_name,
                source_type=str(dc.get("source_type", "extracted")),
                language=str(dc.get("language", "unknown")),
                confidence=conf,
                note=str(dc.get("note", "")) or "Accepted extracted draft claim",
            )
        )
        existing_keys.add(key)

    new_report = build_discovery_report(case_file, query)
    new_report["uploaded_documents"] = uploaded_documents_summary
    new_report["extracted_claims"] = []

    # Regenerate evidence bundle in-place.
    write_evidence_bundle_files(
        case_dir=case_dir,
        case_file=case_file,
        report=new_report,
        uploaded_documents_summary=uploaded_documents_summary,
    )

    payload["case_file"] = case_file.as_dict()
    payload["report"] = new_report
    snapshot_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    bundle_md_path = str(case_dir / "evidence_bundle.md")
    return {
        "case_dir": str(case_dir),
        "snapshot_path": str(snapshot_path),
        "bundle_md_path": bundle_md_path,
        "bundle_md_preview": Path(bundle_md_path).read_text(encoding="utf-8")[:8000]
        if Path(bundle_md_path).exists()
        else "",
        "report": new_report,
    }


def update_bundle_markdown(case_id: str, markdown_text: str, base_dir: str = "data/cases") -> dict[str, str]:
    case_dir = Path(base_dir) / case_id
    bundle_md_path = case_dir / "evidence_bundle.md"
    bundle_md_path.write_text(markdown_text, encoding="utf-8")
    return {
        "case_dir": str(case_dir),
        "bundle_md_path": str(bundle_md_path),
        "bundle_md_preview": markdown_text[:8000],
    }
