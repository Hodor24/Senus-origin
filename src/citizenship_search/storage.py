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
    uploaded_docs: list[dict[str, str]],
    base_dir: str = "data/cases",
) -> dict[str, str]:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    case_slug = _slugify(case_file.subject.full_name)
    case_dir = Path(base_dir) / f"{timestamp}-{case_slug}"
    documents_dir = case_dir / "documents"
    documents_dir.mkdir(parents=True, exist_ok=True)

    uploaded_file_paths: list[str] = []
    for item in uploaded_docs:
        filename = item.get("filename", "uploaded.txt")
        text = item.get("text", "")
        doc_path = documents_dir / filename
        doc_path.write_text(text, encoding="utf-8")
        uploaded_file_paths.append(str(doc_path))

    case_payload = {
        "saved_at": timestamp,
        "case_file": case_file.as_dict(),
        "report": report,
        "uploaded_documents": uploaded_docs,
    }
    snapshot_path = case_dir / "case.json"
    snapshot_path.write_text(json.dumps(case_payload, indent=2), encoding="utf-8")

    return {
        "case_dir": str(case_dir),
        "snapshot_path": str(snapshot_path),
        "documents_dir": str(documents_dir),
        "uploaded_count": str(len(uploaded_file_paths)),
    }
