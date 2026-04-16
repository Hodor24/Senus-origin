from citizenship_search.models import CaseFile
from citizenship_search.security import AuditLog, decrypt_data, encrypt_data
from citizenship_search.translation import translate_document
from citizenship_search.workflow import build_discovery_outputs


def test_discovery_outputs_have_expected_sections() -> None:
    case_file = CaseFile.for_roman_senus()
    outputs = build_discovery_outputs(case_file, "Roman Senus Stryj 1957")
    assert "discovery_report" in outputs
    assert "bundle_draft" in outputs
    assert "archive_requests" in outputs
    assert "translation_records" in outputs
    assert isinstance(outputs["discovery_report"]["strong_matches"], list)


def test_encrypt_decrypt_round_trip() -> None:
    clear = b"roman senus evidence"
    cipher = encrypt_data(clear, "secret-key")
    assert decrypt_data(cipher, "secret-key") == clear


def test_audit_log_chain_links() -> None:
    log = AuditLog(secret="test-secret")
    first = log.append("user1", "create_claim", {"field": "father_name"})
    second = log.append("user1", "resolve_conflict", {"field": "father_name"})
    assert second["prev_hash"] == first["entry_hash"]


def test_translation_preserves_original_hash() -> None:
    record = translate_document(
        document_id="ua-1",
        original_bytes="Сенус".encode("utf-8"),
        original_language="uk",
    )
    assert record.original_sha256
    assert record.target_language == "en"
