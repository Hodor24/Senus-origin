from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from citizenship_search.models import CaseFile


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

    return {
        "case_dir": str(case_dir),
        "snapshot_path": str(snapshot_path),
        "documents_dir": str(documents_dir),
        "uploaded_count": str(len(uploaded_file_paths)),
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
            }
        )
    return cases


def load_case_snapshot(case_id: str, base_dir: str = "data/cases") -> dict:
    snapshot_path = Path(base_dir) / case_id / "case.json"
    return json.loads(snapshot_path.read_text(encoding="utf-8"))
