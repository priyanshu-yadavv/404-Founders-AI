"""
404 FOUNDERS — Pytest Configuration & Fixtures
"""

import os
import sys
from pathlib import Path
import pytest

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.config import SystemConfig
from security.audit import SecurityAuditLogger


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fixture providing clean environment variable baseline for testing."""
    env_keys = [
        "FOUNDERS_ENV",
        "FOUNDERS_OPERATING_MODE",
        "FOUNDERS_LOG_LEVEL",
        "FOUNDERS_LOG_FORMAT",
        "FOUNDERS_SECURITY_DEFAULT_TIER",
        "FOUNDERS_REQUIRE_USER_CONFIRMATION",
        "FOUNDERS_COMPUTE_BACKEND",
        "FOUNDERS_MAX_LOCAL_MEMORY_MB",
        "FOUNDERS_REST_PORT",
    ]
    for key in env_keys:
        monkeypatch.delenv(key, raising=False)


@pytest.fixture
def temp_audit_logger(tmp_path: Path) -> SecurityAuditLogger:
    """Fixture providing an active SecurityAuditLogger writing to a temp file."""
    log_file = tmp_path / "test_audit.log"
    return SecurityAuditLogger(log_path=str(log_file), enabled=True)
