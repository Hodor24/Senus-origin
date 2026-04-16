from __future__ import annotations

import argparse
import html
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

from citizenship_search.app import attach_translation, build_discovery_report, case_from_form, seed_case


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


def _esc(value: str) -> str:
    return html.escape(value, quote=True)


def render_page(form: dict[str, str], report: dict | None = None, error: str = "") -> str:
    report_html = ""
    if report is not None:
        report_html = f"""
        <section class="card">
          <h2>Discovery Summary</h2>
          <pre>{_esc(json.dumps(report, indent=2))}</pre>
        </section>
        """
    error_html = f'<p class="error">{_esc(error)}</p>' if error else ""
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
    pre {{ white-space: pre-wrap; word-break: break-word; background: #0f172a; color: #e2e8f0; padding: 16px; border-radius: 8px; overflow: auto; }}
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
        <form method="post">
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

          <button type="submit">Generate discovery summary</button>
        </form>
      </section>
      <section>
        {report_html}
      </section>
    </div>
  </main>
</body>
</html>
"""


class AppHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        form = default_form_state()
        body = render_page(form)
        self._send_html(body)

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        payload = self.rfile.read(length).decode("utf-8")
        data = {key: values[-1] for key, values in parse_qs(payload, keep_blank_values=True).items()}
        form = {**default_form_state(), **data}
        try:
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
            report = build_discovery_report(case_file, form["query"])
            self._send_html(render_page(form, report=report))
        except Exception as exc:  # pragma: no cover - defensive UI path
            self._send_html(render_page(form, error=str(exc)), status=HTTPStatus.BAD_REQUEST)

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send_html(self, body: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        body_bytes = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body_bytes)))
        self.end_headers()
        self.wfile.write(body_bytes)


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
