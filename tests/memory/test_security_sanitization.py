"""
404 FOUNDERS — Memory Security, Secret Sanitization & Audit Tests
Verifies that high-entropy credentials and secrets are scrubbed before storage,
tenant isolation is strictly enforced, and audit logs are recorded.
"""

import pytest

from core.exceptions import SecurityViolationError
from database.connection import DatabaseManager
from memory.security import MemorySecurityManager


def test_secret_scrubbing_private_keys_and_tokens():
    raw_text = (
        "Here is my RSA key:\n"
        "-----BEGIN RSA PRIVATE KEY-----\n"
        "MIIEowIBAAKCAQEA0444FakeKeyContent\n"
        "-----END RSA PRIVATE KEY-----\n"
        "And OpenAI key sk-1234567890abcdef1234567890abcdef\n"
        "And AWS key AKIAIOSFODNN7EXAMPLE\n"
        "And password: 'SuperSecretPassword123!'"
    )

    clean_text, detected = MemorySecurityManager.scrub_secrets(raw_text)

    # Invariants: no actual credential strings remain
    assert "-----BEGIN RSA PRIVATE KEY-----" not in clean_text
    assert "sk-1234567890abcdef1234567890abcdef" not in clean_text
    assert "AKIAIOSFODNN7EXAMPLE" not in clean_text
    assert "SuperSecretPassword123!" not in clean_text

    # Standardized redaction tags present
    assert "[REDACTED_PRIVATE_KEY]" in clean_text
    assert "[REDACTED_API_TOKEN]" in clean_text
    assert "[REDACTED_AWS_ACCESS_KEY]" in clean_text
    assert "[REDACTED_CREDENTIAL]" in clean_text
    assert len(detected) >= 4


def test_cross_user_tenant_isolation_guard():
    # Same user passes
    MemorySecurityManager.validate_user_access("user_alpha", "user_alpha")

    # Mismatched users must trigger SecurityViolationError
    with pytest.raises(SecurityViolationError) as exc_info:
        MemorySecurityManager.validate_user_access("user_alpha", "user_beta")

    assert "Unauthorized memory access attempt across tenant boundaries" in str(exc_info.value)


def test_immutable_audit_logging(tmp_path):
    db_file = tmp_path / "test_audit.db"
    db_mgr = DatabaseManager(str(db_file))

    with db_mgr.get_connection() as conn:
        event_id = MemorySecurityManager.log_audit_event(
            conn,
            user_id="user_test_01",
            action="RECORD_ACCESS",
            session_id="sess_123",
            memory_id="rec_456",
            details={"ip": "127.0.0.1", "status": "authorized"},
        )

        assert event_id.startswith("aud_")

        cursor = conn.cursor()
        cursor.execute("SELECT user_id, action, memory_id, details_json FROM memory_audit_logs WHERE id = ?", (event_id,))
        row = cursor.fetchone()

        assert row is not None
        assert row["user_id"] == "user_test_01"
        assert row["action"] == "RECORD_ACCESS"
        assert row["memory_id"] == "rec_456"
        assert "127.0.0.1" in row["details_json"]
