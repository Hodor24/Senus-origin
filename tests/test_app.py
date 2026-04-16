from pathlib import Path

from citizenship_search.app import (
    apply_uploaded_documents,
    attach_translation,
    build_discovery_report,
    case_from_form,
    seed_case,
)
from citizenship_search.storage import list_saved_cases, load_case_snapshot, save_case_snapshot


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
            {
                "filename": "record-ua.txt",
                "source_name": "Uploaded file: record-ua.txt",
                "language": "uk",
                "text": "Narodzony w Stryju",
            }
        ],
    )
    assert summary
    assert any(claim.field_name == "uploaded_document" for claim in case_file.claims)
    assert case_file.translations


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


def test_list_and_load_saved_case_snapshot(tmp_path) -> None:
    case_file = seed_case()
    report = build_discovery_report(case_file, "Roman Senus Stryj 1957")
    result = save_case_snapshot(case_file, report, uploaded_docs=[], base_dir=str(tmp_path))
    cases = list_saved_cases(base_dir=str(tmp_path))
    assert cases
    case_id = Path(result["case_dir"]).name
    payload = load_case_snapshot(case_id, base_dir=str(tmp_path))
    assert payload["report"]["subject"] == "Roman Senus"
