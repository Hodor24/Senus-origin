from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from citizenship_search.models import CaseFile


def _md_escape(value: str) -> str:
    # keep it simple; user content is embedded in markdown
    return value.replace("\r\n", "\n").strip()


def write_evidence_bundle_files(
    case_dir: Path,
    case_file: CaseFile,
    report: dict[str, Any],
    uploaded_documents_summary: list[dict[str, object]],
) -> dict[str, str]:
    bundle_md_path = case_dir / "evidence_bundle.md"
    bundle_json_path = case_dir / "bundle.json"

    claims = report.get("claims", [])
    conflicts = report.get("conflicts", [])
    translations = report.get("translations", [])
    archive_requests = report.get("archive_requests", [])

    claims_by_field: dict[str, list[dict[str, Any]]] = {}
    for claim in claims:
        field_name = str(claim.get("field_name", "unknown"))
        claims_by_field.setdefault(field_name, []).append(claim)

    parts: list[str] = []
    parts.append(f"# Evidence Bundle: {_md_escape(str(case_file.subject.full_name))}")
    parts.append("")
    parts.append(f"Saved at: {_md_escape(str(report.get('saved_at', 'unknown')))}")
    parts.append("")

    parts.append("## Key identity facts")
    for field_name in sorted(claims_by_field.keys()):
        # show only the most useful fields first (everything else still listed)
        parts.append("")
        parts.append(f"### {field_name}")
        for claim in claims_by_field[field_name]:
            value = _md_escape(str(claim.get("value", "")))
            src = _md_escape(str(claim.get("source_name", "")))
            src_type = _md_escape(str(claim.get("source_type", "")))
            lang = _md_escape(str(claim.get("language", "")))
            conf = _md_escape(str(claim.get("confidence", "")))
            note = _md_escape(str(claim.get("note", "")))
            parts.append(f"- {value} (source: {src} [{src_type}], lang: {lang}, confidence: {conf})")
            if note:
                parts.append(f"  - note: {note}")

    parts.append("")
    parts.append("## Conflicting facts")
    if not conflicts:
        parts.append("_No conflicts detected in this snapshot._")
    else:
        for conflict in conflicts:
            field = _md_escape(str(conflict.get("field", "")))
            values = ", ".join(_md_escape(v) for v in conflict.get("values", []))
            sources = ", ".join(_md_escape(s) for s in conflict.get("sources", []))
            parts.append(f"- {field}: {values} (sources: {sources})")

    parts.append("")
    parts.append("## Translations (original + English copy)")
    if not translations:
        parts.append("_No translation records in this snapshot._")
    else:
        for t in translations:
            src = _md_escape(str(t.get("source_name", "")))
            orig_lang = _md_escape(str(t.get("original_language", "")))
            orig_text_preview = _md_escape(str(t.get("original_text", "")))[:400]
            en_preview = _md_escape(str(t.get("english_text", "")))[:400]
            parts.append(f"- {src} ({orig_lang})")
            parts.append(f"  - original (preview): {orig_text_preview}")
            parts.append(f"  - English (preview): {en_preview}")

    parts.append("")
    parts.append("## Uploaded documents")
    if not uploaded_documents_summary:
        parts.append("_No uploaded documents in this snapshot._")
    else:
        for doc in uploaded_documents_summary:
            filename = _md_escape(str(doc.get("filename", "")))
            lang = _md_escape(str(doc.get("language", "")))
            media_type = _md_escape(str(doc.get("media_type", "")))
            extractor = _md_escape(str(doc.get("extractor", "")))
            extraction_status = _md_escape(str(doc.get("extraction_status", "")))
            parts.append(f"- {filename} (lang: {lang}, type: {media_type}, extractor: {extractor}, status: {extraction_status})")

    parts.append("")
    parts.append("## Archive requests (draft)")
    if not archive_requests:
        parts.append("_No archive requests in this snapshot._")
    else:
        for req in archive_requests:
            repo = _md_escape(str(req.get("repository", "")))
            focus = _md_escape(str(req.get("request_focus", "")))
            priority = _md_escape(str(req.get("priority", "")))
            parts.append(f"- {repo} (priority: {priority}) — {focus}")

    bundle_md_path.write_text("\n".join(parts) + "\n", encoding="utf-8")

    bundle_payload = {
        "case": case_file.as_dict(),
        "report": report,
        "uploaded_documents": uploaded_documents_summary,
    }
    bundle_json_path.write_text(json.dumps(bundle_payload, indent=2), encoding="utf-8")

    return {
        "bundle_md_path": str(bundle_md_path),
        "bundle_json_path": str(bundle_json_path),
    }

