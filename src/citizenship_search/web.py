from __future__ import annotations

import argparse
import cgi
import html
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

from citizenship_search.app import (
    apply_uploaded_documents,
    attach_translation,
    build_discovery_report,
    case_from_form,
    seed_case,
)
from citizenship_search.ingest import ingest_uploaded_file
from citizenship_search.storage import (
    accept_all_draft_extracted_claims,
    accept_draft_extracted_claims,
    accept_safe_draft_extracted_claims,
    reject_all_draft_extracted_claims,
    list_saved_cases,
    load_case_snapshot,
    save_case_snapshot,
    update_bundle_markdown,
)


def _join_lines(values: list[str]) -> str:
    return "\n".join(values)


def default_form_state() -> dict[str, str]:
    case_file = seed_case()
    claims_text = "\n".join(
        [
            " | ".join(
                [
                    claim.field_name,
                    claim.value,
                    claim.source_name,
                    claim.source_type,
                    claim.language,
                    str(claim.confidence),
                    claim.note,
                ]
            ).strip()
            for claim in case_file.claims
        ]
    )
    return {
        "query": "Roman Senus Stryj 1957",
        "full_name": case_file.subject.full_name,
        "aliases": _join_lines(case_file.subject.aliases),
        "father_names": _join_lines(case_file.subject.father_name_variants),
        "birthplaces": _join_lines(case_file.subject.birthplace_variants),
        "occupations": _join_lines(case_file.subject.occupation_variants),
        "timeline_cues": _join_lines(case_file.subject.timeline_cues),
        "claims_text": claims_text,
        "translation_source": "Example Ukrainian note",
        "translation_language": "uk",
        "translation_text": "Narodzony w Stryju, ojciec: Mikolaj.",
    }


def form_state_from_snapshot(payload: dict) -> dict[str, str]:
    case_file = payload.get("case_file", {})
    subject = case_file.get("subject", {})
    claims = case_file.get("claims", [])
    translations = case_file.get("translations", [])
    claims_text = "\n".join(
        " | ".join(
            [
                str(claim.get("field_name", "")),
                str(claim.get("value", "")),
                str(claim.get("source_name", "")),
                str(claim.get("source_type", "")),
                str(claim.get("language", "")),
                str(claim.get("confidence", "")),
                str(claim.get("note", "")),
            ]
        ).strip()
        for claim in claims
    )
    first_translation = translations[0] if translations else {}
    return {
        "query": str(payload.get("report", {}).get("query", "")),
        "full_name": str(subject.get("full_name", "")),
        "aliases": _join_lines(subject.get("aliases", [])),
        "father_names": _join_lines(subject.get("father_name_variants", [])),
        "birthplaces": _join_lines(subject.get("birthplace_variants", [])),
        "occupations": _join_lines(subject.get("occupation_variants", [])),
        "timeline_cues": _join_lines(subject.get("timeline_cues", [])),
        "claims_text": claims_text,
        "translation_source": str(first_translation.get("source_name", "")),
        "translation_language": str(first_translation.get("original_language", "")),
        "translation_text": str(first_translation.get("original_text", "")),
        "selected_case_id": "",
        "bundle_editor_text": "",
    }


def _esc(value: str) -> str:
    return html.escape(value, quote=True)


def _render_list(items: list[str]) -> str:
    if not items:
        return "<p class='hint'>None</p>"
    return "<ul>" + "".join(f"<li>{_esc(item)}</li>" for item in items) + "</ul>"


def _render_table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "<p class='hint'>None</p>"
    head_html = "".join(f"<th>{_esc(h)}</th>" for h in headers)
    body_html = "".join(
        "<tr>" + "".join(f"<td>{_esc(cell)}</td>" for cell in row) + "</tr>"
        for row in rows
    )
    return f"<table><thead><tr>{head_html}</tr></thead><tbody>{body_html}</tbody></table>"


def render_saved_cases_panel(saved_cases: list[dict[str, str]], selected_case_id: str = "") -> str:
    rows = [
        [
            case["saved_at"],
            case["subject"],
            case["id"],
            "Loaded" if case["id"] == selected_case_id else "",
        ]
        for case in saved_cases
    ]
    return f"""
    <section class="card">
      <h2>Saved Case History</h2>
      {_render_table(["Saved At", "Subject", "Case ID", "Status"], rows)}
    </section>
    """


def render_report_sections(report: dict) -> str:
    query_hits = report.get("query_hits", {})
    claims = report.get("claims", [])
    conflicts = report.get("conflicts", [])
    uploads = report.get("uploaded_documents", [])
    translations = report.get("translations", [])
    archive_requests = report.get("archive_requests", [])
    storage = report.get("storage", {})
    bundle_preview = storage.get("bundle_md_preview", "")
    extracted_claims = report.get("extracted_claims", [])

    claims_rows = [
        [
            str(item.get("field_name", "")),
            str(item.get("value", "")),
            str(item.get("source_name", "")),
            str(item.get("source_type", "")),
            str(item.get("language", "")),
            str(item.get("confidence", "")),
        ]
        for item in claims
    ]
    conflict_rows = [
        [
            str(item.get("field", "")),
            ", ".join(item.get("values", [])),
            ", ".join(item.get("sources", [])),
        ]
        for item in conflicts
    ]
    upload_rows = [
        [
            str(item.get("filename", "")),
            str(item.get("language", "")),
            str(item.get("media_type", "")),
            str(item.get("extractor", "")),
            str(item.get("extraction_status", "")),
            str(item.get("size_chars", "")),
            str(item.get("source_name", "")),
            str(item.get("preview", "")),
        ]
        for item in uploads
    ]
    translation_rows = [
        [
            str(item.get("source_name", "")),
            str(item.get("original_language", "")),
            str(item.get("original_text", ""))[:100],
            str(item.get("english_text", ""))[:100],
        ]
        for item in translations
    ]
    archive_rows = [
        [
            str(item.get("repository", "")),
            str(item.get("request_focus", "")),
            str(item.get("priority", "")),
        ]
        for item in archive_requests
    ]
    case_id = ""
    try:
        storage_case_dir = str(storage.get("case_dir", ""))
        if storage_case_dir:
            case_id = storage_case_dir.rstrip("/").split("/")[-1]
    except Exception:
        case_id = ""
    draft_claims_json = json.dumps(extracted_claims, ensure_ascii=False)
    accept_form_html = ""
    if extracted_claims:
        accept_rows_html = "".join(
            f"<tr>"
            f"<td><input type='checkbox' name='accepted_draft_indices' value='{i}'></td>"
            f"<td>{_esc(str(item.get('field_name', '')))}</td>"
            f"<td>{_esc(str(item.get('value', '')))}</td>"
            f"<td>{_esc(str(item.get('source_name', '')))}</td>"
            f"<td>{_esc(str(item.get('confidence', '')))}</td>"
            f"<td>{_esc(str(item.get('note', '')))}</td>"
            f"</tr>"
            for i, item in enumerate(extracted_claims)
        )
        accept_form_html = f"""
        <form method="post">
          <input type="hidden" name="action" value="accept_draft_claims">
          <input type="hidden" name="selected_case_id" value="{_esc(case_id)}">
          <input type="hidden" name="draft_claims_json" value="{_esc(draft_claims_json)}">
          <h3>Draft Extracted Claims</h3>
          <table><thead><tr>
            <th>Accept</th>
            <th>Field</th>
            <th>Value</th>
            <th>Source</th>
            <th>Confidence</th>
            <th>Note</th>
          </tr></thead><tbody>{accept_rows_html}</tbody></table>
          <button type="submit" style="margin-top: 12px;">Accept selected claims</button>
        </form>
        """

        accept_all_form_html = f"""
        <form method="post">
          <input type="hidden" name="action" value="accept_all_draft_claims">
          <input type="hidden" name="selected_case_id" value="{_esc(case_id)}">
          <button type="submit" style="margin-top: 10px; background: #16a34a;">Accept all drafts</button>
        </form>
        """

        reject_all_form_html = f"""
        <form method="post">
          <input type="hidden" name="action" value="reject_all_draft_claims">
          <input type="hidden" name="selected_case_id" value="{_esc(case_id)}">
          <button type="submit" style="margin-top: 10px; background: #b91c1c;">Reject all drafts</button>
        </form>
        """

        accept_safe_form_html = f"""
        <form method="post">
          <input type="hidden" name="action" value="accept_safe_draft_claims">
          <input type="hidden" name="selected_case_id" value="{_esc(case_id)}">
          <input type="hidden" name="draft_claims_json" value="{_esc(draft_claims_json)}">
          <label for="min_confidence">Minimum confidence</label>
          <input id="min_confidence" name="min_confidence" type="text" value="0.6" style="width: 120px; margin-right: 8px;">
          <button type="submit" style="margin-top: 10px; background: #0ea5e9;">Accept safe drafts</button>
        </form>
        """

        accept_form_html = accept_form_html + accept_all_form_html + reject_all_form_html + accept_safe_form_html

    return f"""
    <section class="card">
      <h2>Discovery Summary</h2>
      <p><strong>Subject:</strong> {_esc(str(report.get("subject", "")))}</p>
      <p><strong>Query:</strong> {_esc(str(report.get("query", "")))}</p>
      <p><strong>Saved case:</strong> {_esc(str(storage.get("case_dir", "Not saved yet")))}</p>
      <p><strong>Snapshot file:</strong> {_esc(str(storage.get("snapshot_path", "Not saved yet")))}</p>
      <p><strong>Evidence bundle:</strong> {_esc(str(storage.get("bundle_md_path", "Not generated yet")))}</p>
      {"<h3>Evidence Bundle Preview</h3><pre>"+_esc(bundle_preview)+"</pre>" if bundle_preview else ""}
      <h3>Query Hits</h3>
      <p><strong>Aliases:</strong></p>
      {_render_list([str(item) for item in query_hits.get("aliases", [])])}
      <p><strong>Places:</strong></p>
      {_render_list([str(item) for item in query_hits.get("places", [])])}

      <h3>Father Name Alias Pool</h3>
      {_render_list([str(item) for item in report.get("father_name_alias_pool", [])])}

      <h3>Claims</h3>
      {_render_table(["Field", "Value", "Source", "Type", "Lang", "Confidence"], claims_rows)}

      <h3>Conflicts</h3>
      {_render_table(["Field", "Values", "Sources"], conflict_rows)}

      <h3>Uploaded Documents</h3>
      {_render_table(["Filename", "Language", "Type", "Extractor", "Status", "Chars", "Source", "Preview"], upload_rows)}

      <h3>Translations</h3>
      {_render_table(["Source", "Language", "Original (preview)", "English (preview)"], translation_rows)}

      <h3>Archive Requests</h3>
      {_render_table(["Repository", "Focus", "Priority"], archive_rows)}
      {accept_form_html}
    </section>
    """


def render_page(form: dict[str, str], report: dict | None = None, error: str = "", saved_cases: list[dict[str, str]] | None = None) -> str:
    report_html = ""
    if report is not None:
        report_html = render_report_sections(report)
    error_html = f'<p class="error">{_esc(error)}</p>' if error else ""
    saved_case_options = "".join(
        f"<option value=\"{_esc(case['id'])}\"{' selected' if case['id'] == form.get('selected_case_id', '') else ''}>{_esc(case['saved_at'])} - {_esc(case['subject'])}</option>"
        for case in (saved_cases or [])
    )
    saved_cases_html = render_saved_cases_panel(saved_cases or [], form.get("selected_case_id", ""))
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Citizenship Search App</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 0; background: #f5f7fb; color: #1f2937; }}
    main {{ max-width: 1200px; margin: 0 auto; padding: 24px; }}
    h1, h2 {{ margin-top: 0; }}
    .layout {{ display: grid; grid-template-columns: 1.1fr 0.9fr; gap: 20px; }}
    .card {{ background: white; border-radius: 12px; padding: 20px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }}
    label {{ display: block; font-weight: 600; margin: 14px 0 6px; }}
    input, textarea {{ width: 100%; box-sizing: border-box; border: 1px solid #cbd5e1; border-radius: 8px; padding: 10px; font: inherit; }}
    textarea {{ min-height: 96px; resize: vertical; }}
    button {{ margin-top: 18px; background: #2563eb; color: white; border: none; padding: 12px 18px; border-radius: 8px; cursor: pointer; }}
    button:hover {{ background: #1d4ed8; }}
    .hint {{ color: #475569; font-size: 0.95rem; }}
    .error {{ color: #b91c1c; font-weight: 600; }}
    table {{ width: 100%; border-collapse: collapse; margin: 8px 0 16px; font-size: 0.93rem; }}
    th, td {{ border: 1px solid #e2e8f0; padding: 8px; text-align: left; vertical-align: top; }}
    th {{ background: #f8fafc; }}
    ul {{ margin: 8px 0 16px 20px; padding: 0; }}
    h3 {{ margin-bottom: 8px; margin-top: 22px; }}
    @media (max-width: 900px) {{ .layout {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <main>
    <h1>Citizenship Search App</h1>
    <p class="hint">Enter the subject profile, paste claims from certificates or indexes, and optionally attach non-English source text for side-by-side translation retention.</p>
    {error_html}
    <div class="layout">
      <section class="card">
        <h2>Case Input</h2>
        <form method="get">
          <label for="load_case_id">Load saved case</label>
          <select id="load_case_id" name="load_case_id">
            <option value="">Choose a saved case</option>
            {saved_case_options}
          </select>
          <button type="submit">Load saved case</button>
        </form>
        <form method="post">
          <input type="hidden" name="action" value="reexport_bundle">
          <input type="hidden" name="selected_case_id" value="{_esc(form.get('selected_case_id', ''))}">
          <label for="bundle_editor_text">Evidence bundle editor</label>
          <textarea id="bundle_editor_text" name="bundle_editor_text">{_esc(form.get('bundle_editor_text', ''))}</textarea>
          <p class="hint">Load a saved case, edit the bundle markdown here, then re-export it back to disk.</p>
          <button type="submit">Re-export bundle</button>
        </form>
        <form method="post" enctype="multipart/form-data">
          <input type="hidden" name="action" value="generate_report">
          <label for="query">Search query</label>
          <input id="query" name="query" value="{_esc(form['query'])}">

          <label for="full_name">Full name</label>
          <input id="full_name" name="full_name" value="{_esc(form['full_name'])}">

          <label for="aliases">Aliases (one per line)</label>
          <textarea id="aliases" name="aliases">{_esc(form['aliases'])}</textarea>

          <label for="father_names">Father name variants (one per line)</label>
          <textarea id="father_names" name="father_names">{_esc(form['father_names'])}</textarea>

          <label for="birthplaces">Birthplace variants (one per line)</label>
          <textarea id="birthplaces" name="birthplaces">{_esc(form['birthplaces'])}</textarea>

          <label for="occupations">Occupation variants (one per line)</label>
          <textarea id="occupations" name="occupations">{_esc(form['occupations'])}</textarea>

          <label for="timeline_cues">Timeline cues (one per line)</label>
          <textarea id="timeline_cues" name="timeline_cues">{_esc(form['timeline_cues'])}</textarea>

          <label for="claims_text">Claims</label>
          <textarea id="claims_text" name="claims_text">{_esc(form['claims_text'])}</textarea>
          <p class="hint">Format each line as: field | value | source_name | source_type | language | confidence | optional_note</p>

          <label for="translation_source">Translation source label</label>
          <input id="translation_source" name="translation_source" value="{_esc(form['translation_source'])}">

          <label for="translation_language">Original language code</label>
          <input id="translation_language" name="translation_language" value="{_esc(form['translation_language'])}">

          <label for="translation_text">Original non-English text</label>
          <textarea id="translation_text" name="translation_text">{_esc(form['translation_text'])}</textarea>

          <label for="uploaded_documents">Upload document text files (.txt, .md, .csv)</label>
          <input id="uploaded_documents" name="uploaded_documents" type="file" multiple>
          <p class="hint">Uploaded files are parsed as text and added as source evidence. Non-English files are copied to translation records.</p>

          <button type="submit">Generate discovery summary</button>
        </form>
      </section>
      <section>
        {saved_cases_html}
        {report_html}
      </section>
    </div>
  </main>
</body>
</html>
"""


class AppHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        saved_cases = list_saved_cases()
        query = parse_qs(self.path.split("?", 1)[1] if "?" in self.path else "", keep_blank_values=True)
        case_id = query.get("load_case_id", [""])[-1]
        form = default_form_state()
        report = None
        if case_id:
            try:
                payload = load_case_snapshot(case_id)
                form = {**form, **form_state_from_snapshot(payload)}
                report = payload.get("report")
                # Compute storage paths and include a markdown preview.
                # This avoids needing to store non-JSON fields in the snapshot.
                case_dir = f"data/cases/{case_id}"
                bundle_md_path = f"{case_dir}/evidence_bundle.md"
                snapshot_path = f"{case_dir}/case.json"
                bundle_preview = ""
                try:
                    bundle_preview = open(bundle_md_path, "r", encoding="utf-8").read()
                except OSError:
                    bundle_preview = ""
                if isinstance(report, dict):
                    report["storage"] = {
                        "case_dir": case_dir,
                        "snapshot_path": snapshot_path,
                        "bundle_md_path": bundle_md_path,
                        "bundle_md_preview": bundle_preview[:8000],
                    }
                form["selected_case_id"] = case_id
                form["bundle_editor_text"] = bundle_preview
            except Exception as exc:  # pragma: no cover
                body = render_page(form, error=str(exc), saved_cases=saved_cases)
                self._send_html(body, status=HTTPStatus.BAD_REQUEST)
                return
        body = render_page(form, report=report, saved_cases=saved_cases)
        self._send_html(body)

    def do_POST(self) -> None:  # noqa: N802
        data, uploaded_docs = self._parse_post_data()
        form = {**default_form_state(), **data}
        saved_cases = list_saved_cases()
        try:
            action = form.get("action", "generate_report")
            if action == "accept_draft_claims":
                case_id = str(form.get("selected_case_id", "")).strip()
                if not case_id:
                    raise ValueError("No selected case for accepting draft claims.")
                draft_claims_json = str(form.get("draft_claims_json", "[]"))
                draft_claims = json.loads(draft_claims_json) if draft_claims_json else []
                accepted = form.get("accepted_draft_indices", [])
                if isinstance(accepted, str):
                    accepted_indices = [int(x) for x in accepted.split(",") if x.strip()]
                else:
                    accepted_indices = [int(x) for x in list(accepted)]
                if not accepted_indices:
                    raise ValueError("Select at least one draft extracted claim to accept.")

                result = accept_draft_extracted_claims(
                    case_id=case_id,
                    accepted_indices=accepted_indices,
                    draft_claims=draft_claims,
                )
                report = result.get("report", {})
                report["storage"] = {
                    "case_dir": result.get("case_dir", ""),
                    "snapshot_path": result.get("snapshot_path", ""),
                    "bundle_md_path": result.get("bundle_md_path", ""),
                    "bundle_md_preview": result.get("bundle_md_preview", ""),
                }
                form["selected_case_id"] = case_id
                form["bundle_editor_text"] = str(result.get("bundle_md_preview", ""))
                self._send_html(render_page(form, report=report, saved_cases=saved_cases))
                return

            if action == "accept_all_draft_claims":
                case_id = str(form.get("selected_case_id", "")).strip()
                if not case_id:
                    raise ValueError("Select a saved case before accepting all drafts.")
                result = accept_all_draft_extracted_claims(case_id=case_id)
                report = result.get("report", {})
                report["storage"] = {
                    "case_dir": result.get("case_dir", ""),
                    "snapshot_path": result.get("snapshot_path", ""),
                    "bundle_md_path": result.get("bundle_md_path", ""),
                    "bundle_md_preview": result.get("bundle_md_preview", ""),
                }
                form["selected_case_id"] = case_id
                form["bundle_editor_text"] = str(result.get("bundle_md_preview", ""))
                self._send_html(render_page(form, report=report, saved_cases=saved_cases))
                return

            if action == "reject_all_draft_claims":
                case_id = str(form.get("selected_case_id", "")).strip()
                if not case_id:
                    raise ValueError("Select a saved case before rejecting drafts.")
                result = reject_all_draft_extracted_claims(case_id=case_id)
                report = result.get("report", {})
                report["storage"] = {
                    "case_dir": result.get("case_dir", ""),
                    "snapshot_path": result.get("snapshot_path", ""),
                    "bundle_md_path": result.get("bundle_md_path", ""),
                    "bundle_md_preview": result.get("bundle_md_preview", ""),
                }
                form["selected_case_id"] = case_id
                form["bundle_editor_text"] = str(result.get("bundle_md_preview", ""))
                self._send_html(render_page(form, report=report, saved_cases=saved_cases))
                return

            if action == "reexport_bundle":
                case_id = form.get("selected_case_id", "").strip()
                if not case_id:
                    raise ValueError("Select a saved case before re-exporting the bundle.")
                storage = update_bundle_markdown(case_id, form.get("bundle_editor_text", ""))
                payload = load_case_snapshot(case_id)
                report = payload.get("report") if isinstance(payload, dict) else {}
                if isinstance(report, dict):
                    report["storage"] = {
                        "case_dir": storage["case_dir"],
                        "snapshot_path": f"{storage['case_dir']}/case.json",
                        "bundle_md_path": storage["bundle_md_path"],
                        "bundle_md_preview": storage["bundle_md_preview"],
                    }
                self._send_html(render_page(form, report=report, saved_cases=saved_cases))
                return

            if action == "accept_safe_draft_claims":
                case_id = str(form.get("selected_case_id", "")).strip()
                if not case_id:
                    raise ValueError("Select a saved case before accepting safe drafts.")
                draft_claims_json = str(form.get("draft_claims_json", "[]"))
                draft_claims = json.loads(draft_claims_json) if draft_claims_json else []
                min_conf = form.get("min_confidence", "0.6")
                try:
                    min_confidence = float(min_conf)
                except (TypeError, ValueError):
                    min_confidence = 0.6

                if not draft_claims:
                    raise ValueError("No draft claims found to accept.")

                result = accept_safe_draft_extracted_claims(
                    case_id=case_id,
                    draft_claims=draft_claims,
                    min_confidence=min_confidence,
                )
                report = result.get("report", {})
                report["storage"] = {
                    "case_dir": result.get("case_dir", ""),
                    "snapshot_path": result.get("snapshot_path", ""),
                    "bundle_md_path": result.get("bundle_md_path", ""),
                    "bundle_md_preview": result.get("bundle_md_preview", ""),
                }
                form["selected_case_id"] = case_id
                form["bundle_editor_text"] = str(result.get("bundle_md_preview", ""))
                self._send_html(render_page(form, report=report, saved_cases=saved_cases))
                return

            case_file = case_from_form(
                full_name=form["full_name"],
                aliases=form["aliases"],
                father_names=form["father_names"],
                birthplaces=form["birthplaces"],
                occupations=form["occupations"],
                timeline_cues=form["timeline_cues"],
                claims_text=form["claims_text"],
            )
            if form["translation_text"].strip():
                attach_translation(
                    case_file=case_file,
                    source_name=form["translation_source"].strip() or "Uploaded translation source",
                    text=form["translation_text"],
                    original_language=form["translation_language"].strip() or "unknown",
                )
            uploaded_summary = apply_uploaded_documents(case_file, uploaded_docs)
            report = build_discovery_report(case_file, form["query"])
            report["uploaded_documents"] = uploaded_summary
            report["extracted_claims"] = [
                claim
                for item in uploaded_summary
                for claim in item.get("extracted_claims", [])
            ]
            report["storage"] = save_case_snapshot(case_file, report, uploaded_docs)
            form["bundle_editor_text"] = str(report["storage"].get("bundle_md_preview", ""))
            try:
                form["selected_case_id"] = str(report["storage"].get("case_dir", "")).rstrip("/").split("/")[-1]
            except Exception:
                form["selected_case_id"] = ""
            self._send_html(render_page(form, report=report, saved_cases=saved_cases))
        except Exception as exc:  # pragma: no cover - defensive UI path
            self._send_html(render_page(form, error=str(exc), saved_cases=saved_cases), status=HTTPStatus.BAD_REQUEST)

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send_html(self, body: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        body_bytes = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body_bytes)))
        self.end_headers()
        self.wfile.write(body_bytes)

    def _parse_post_data(self) -> tuple[dict[str, object], list[dict[str, object]]]:
        content_type, _ = cgi.parse_header(self.headers.get("Content-Type", ""))
        if content_type == "multipart/form-data":
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={
                    "REQUEST_METHOD": "POST",
                    "CONTENT_TYPE": self.headers.get("Content-Type", ""),
                    "CONTENT_LENGTH": self.headers.get("Content-Length", "0"),
                },
            )
            data: dict[str, object] = {}
            uploaded_docs: list[dict[str, str]] = []
            for key in form.keys():
                field = form[key]
                fields = field if isinstance(field, list) else [field]
                for item in fields:
                    if getattr(item, "filename", None):
                        uploaded_docs.append(
                            ingest_uploaded_file(
                                filename=item.filename or "uploaded.txt",
                                file_bytes=item.file.read() if item.file else b"",
                                language=(form.getvalue("translation_language") or "unknown").strip() or "unknown",
                                source_name=f"Uploaded file: {item.filename or 'uploaded.txt'}",
                            )
                        )
                    else:
                        value = str(item.value or "")
                        if key not in data:
                            data[key] = value
                        else:
                            existing = data[key]
                            if isinstance(existing, list):
                                existing.append(value)
                            else:
                                data[key] = [existing, value]
            return data, uploaded_docs

        length = int(self.headers.get("Content-Length", "0"))
        payload = self.rfile.read(length).decode("utf-8")
        data = {key: values[-1] for key, values in parse_qs(payload, keep_blank_values=True).items()}
        return data, []


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local citizenship search web app.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), AppHandler)
    print(f"Serving Citizenship Search App at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
