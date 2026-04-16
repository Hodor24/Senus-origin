from pathlib import Path

from citizenship_search.app import (
    apply_uploaded_documents,
    attach_translation,
    build_discovery_report,
    case_from_form,
    seed_case,
)
from citizenship_search.extract_claims import extract_claims_from_text
from citizenship_search.ingest import ingest_uploaded_file
from citizenship_search.storage import (
    accept_all_draft_extracted_claims,
    accept_draft_extracted_claims,
    list_saved_cases,
    load_case_snapshot,
    save_case_snapshot,
    reject_all_draft_extracted_claims,
    update_bundle_markdown,
)


def test_seed_case_has_core_claims() -> None:
    case_file = seed_case()
    fields = {claim.field_name for claim in case_file.claims}
    assert "birthplace" in fields
    assert "father_name" in fields
    assert "military_service" in fields


def test_report_detects_conflicts() -> None:
    case_file = seed_case()
    report = build_discovery_report(case_file, "Roman Senus Stryj 1957")
    conflict_fields = {conflict["field"] for conflict in report["conflicts"]}
    assert "father_name" in conflict_fields


def test_translation_is_preserved_with_original() -> None:
    case_file = seed_case()
    attach_translation(
        case_file=case_file,
        source_name="UA source",
        text="Ojciec: Mikolaj",
        original_language="uk",
    )
    report = build_discovery_report(case_file, "Roman Senus")
    assert report["translations"]
    assert report["translations"][0]["original_text"] == "Ojciec: Mikolaj"
    assert report["translations"][0]["english_text"].startswith("[EN translation]")


def test_case_from_form_parses_claims() -> None:
    case_file = case_from_form(
        full_name="Roman Senus",
        aliases="Roman Senus",
        father_names="Michal\nMikolaj",
        birthplaces="Poland\nStryj",
        occupations="Painter",
        timeline_cues="1957",
        claims_text="father_name | Michal | Marriage certificate | civil | en | 0.8 | primary civil record",
    )
    assert case_file.subject.full_name == "Roman Senus"
    assert case_file.claims[0].field_name == "father_name"
    assert case_file.claims[0].confidence == 0.8


def test_uploaded_documents_create_claims_and_translations() -> None:
    case_file = seed_case()
    summary = apply_uploaded_documents(
        case_file,
        [
            ingest_uploaded_file("record-ua.txt", "Narodzony w Stryju".encode("utf-8"), "uk", "Uploaded file: record-ua.txt")
        ],
    )
    assert summary
    assert any(claim.field_name == "uploaded_document" for claim in case_file.claims)
    assert case_file.translations
    assert summary[0]["extracted_claims"]


def test_save_case_snapshot_writes_files(tmp_path) -> None:
    case_file = seed_case()
    report = build_discovery_report(case_file, "Roman Senus Stryj 1957")
    result = save_case_snapshot(
        case_file,
        report,
        uploaded_docs=[{"filename": "record.txt", "text": "example text"}],
        base_dir=str(tmp_path),
    )
    assert Path(result["snapshot_path"]).exists()
    assert Path(result["documents_dir"], "record.txt").exists()
    assert Path(result["bundle_md_path"]).exists()
    assert Path(result["bundle_json_path"]).exists()
    md = Path(result["bundle_md_path"]).read_text(encoding="utf-8")
    assert "Evidence Bundle" in md
    assert "Roman Senus" in md
    assert "bundle_md_preview" in result
    assert "Evidence Bundle" in str(result["bundle_md_preview"])


def test_ingest_uploaded_file_handles_pdf_fallback() -> None:
    result = ingest_uploaded_file("scan.pdf", b"%PDF-1.4 Roman Senus Stryj", "en")
    assert result["media_type"] == "pdf"
    assert result["extractor"] in {"printable-text-fallback", "textutil"}
    assert result["extraction_status"] in {
        "partial_pdf_text",
        "pdf_no_text_extractor",
        "textutil_pdf_text_extracted",
        "pdf_no_text_from_textutil",
    }
    assert isinstance(result["original_bytes"], bytes)


def test_ingest_uploaded_file_marks_image_without_ocr() -> None:
    result = ingest_uploaded_file("photo.jpg", b"\xff\xd8\xff", "pl")
    assert result["media_type"] == "image"
    assert result["extraction_status"] == "image_saved_ocr_unavailable"


def test_list_and_load_saved_case_snapshot(tmp_path) -> None:
    case_file = seed_case()
    report = build_discovery_report(case_file, "Roman Senus Stryj 1957")
    result = save_case_snapshot(case_file, report, uploaded_docs=[], base_dir=str(tmp_path))
    cases = list_saved_cases(base_dir=str(tmp_path))
    assert cases
    case_id = Path(result["case_dir"]).name
    payload = load_case_snapshot(case_id, base_dir=str(tmp_path))
    assert payload["report"]["subject"] == "Roman Senus"


def test_update_bundle_markdown_overwrites_bundle(tmp_path) -> None:
    case_file = seed_case()
    report = build_discovery_report(case_file, "Roman Senus Stryj 1957")
    result = save_case_snapshot(case_file, report, uploaded_docs=[], base_dir=str(tmp_path))
    case_id = Path(result["case_dir"]).name
    updated = update_bundle_markdown(case_id, "# Edited Bundle\n\nCustom note.", base_dir=str(tmp_path))
    text = Path(updated["bundle_md_path"]).read_text(encoding="utf-8")
    assert "Edited Bundle" in text
    assert "Custom note." in text


def test_accept_draft_extracted_claims_updates_snapshot(tmp_path) -> None:
    case_file = seed_case()
    report = build_discovery_report(case_file, "Roman Senus Stryj 1957")
    # Ensure required keys exist for the accept logic.
    report["uploaded_documents"] = []
    result = save_case_snapshot(case_file, report, uploaded_docs=[], base_dir=str(tmp_path))
    case_id = Path(result["case_dir"]).name

    draft_claims = [
        {
            "field_name": "father_name",
            "value": "Michal",
            "source_name": "Extracted text",
            "source_type": "extracted",
            "language": "en",
            "confidence": "0.65",
            "note": "Auto-extracted",
        }
    ]
    updated = accept_draft_extracted_claims(
        case_id=case_id,
        accepted_indices=[0],
        draft_claims=draft_claims,
        base_dir=str(tmp_path),
    )
    assert updated["bundle_md_path"]
    payload = load_case_snapshot(case_id, base_dir=str(tmp_path))
    case_payload = payload["case_file"]
    assert any(
        c.get("field_name") == "father_name" and c.get("value") == "Michal" for c in case_payload.get("claims", [])
    )


def test_accept_all_draft_extracted_claims_updates_snapshot(tmp_path) -> None:
    case_file = seed_case()
    report = build_discovery_report(case_file, "Roman Senus Stryj 1957")
    report["uploaded_documents"] = []
    draft_claims = [
        {
            "field_name": "father_name",
            "value": "Michal",
            "source_name": "Extracted text",
            "source_type": "extracted",
            "language": "en",
            "confidence": "0.65",
            "note": "Auto-extracted",
        }
    ]
    report["extracted_claims"] = draft_claims
    result = save_case_snapshot(case_file, report, uploaded_docs=[], base_dir=str(tmp_path))
    case_id = Path(result["case_dir"]).name

    accept_all_draft_extracted_claims(case_id=case_id, base_dir=str(tmp_path))
    payload = load_case_snapshot(case_id, base_dir=str(tmp_path))
    case_payload = payload["case_file"]
    assert any(
        c.get("field_name") == "father_name" and c.get("value") == "Michal" for c in case_payload.get("claims", [])
    )


def test_reject_all_draft_extracted_claims_clears_snapshot(tmp_path) -> None:
    case_file = seed_case()
    report = build_discovery_report(case_file, "Roman Senus Stryj 1957")
    report["uploaded_documents"] = []
    report["extracted_claims"] = [
        {"field_name": "father_name", "value": "Michal", "source_name": "Extracted text"}
    ]
    result = save_case_snapshot(case_file, report, uploaded_docs=[], base_dir=str(tmp_path))
    case_id = Path(result["case_dir"]).name

    reject_all_draft_extracted_claims(case_id=case_id, base_dir=str(tmp_path))
    payload = load_case_snapshot(case_id, base_dir=str(tmp_path))
    assert payload["report"]["extracted_claims"] == []


def test_extract_claims_from_text_finds_core_fields() -> None:
    claims = extract_claims_from_text(
        text="Born in Stryj. Father name Michal. Migrated in 1957. Occupation painter. Army service recorded.",
        source_name="Test source",
        language="en",
    )
    fields = {claim["field_name"] for claim in claims}
    assert "birthplace" in fields
    assert "father_name" in fields
    assert "migration_year" in fields
    assert "occupation" in fields
    assert "military_service" in fields
