"""
404 FOUNDERS — Unit Tests for Exception Taxonomy
"""

from core.exceptions import (
    ArchitectureError,
    BackendNotAvailableError,
    ConfigurationError,
    ContextWindowExceededError,
    FoundersBaseException,
    PermissionDeniedError,
    PromptInjectionDetectedError,
    SecurityViolationError,
    ToolExecutionError,
)


def test_base_exception_serialization() -> None:
    """Validate base exception attributes and dictionary conversion."""
    exc = FoundersBaseException("Test failure", error_code="TEST_CODE", details={"k": "v"})
    assert exc.message == "Test failure"
    assert exc.error_code == "TEST_CODE"
    d = exc.to_dict()
    assert d["error_code"] == "TEST_CODE"
    assert d["details"]["k"] == "v"


def test_backend_not_available_error() -> None:
    """Validate compute backend error message format."""
    exc = BackendNotAvailableError("cuda")
    assert "cuda" in str(exc)
    assert exc.error_code == "BACKEND_NOT_AVAILABLE"


def test_permission_denied_error() -> None:
    """Validate permission denied error format and attributes."""
    exc = PermissionDeniedError("format_disk", required_tier="dangerous", active_tier="read_only")
    assert exc.error_code == "PERMISSION_DENIED"
    assert "format_disk" in exc.message
    assert exc.details["required_tier"] == "dangerous"
    assert exc.details["active_tier"] == "read_only"


def test_context_window_exceeded_error() -> None:
    """Validate context window overflow error reporting."""
    exc = ContextWindowExceededError(current_tokens=20000, max_tokens=16384)
    assert exc.error_code == "CONTEXT_WINDOW_EXCEEDED"
    assert exc.details["current_tokens"] == 20000
    assert exc.details["max_tokens"] == 16384
