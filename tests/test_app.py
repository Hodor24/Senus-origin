from citizenship_search.app import attach_translation, build_discovery_report, seed_case


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
