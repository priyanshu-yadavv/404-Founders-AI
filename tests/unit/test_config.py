"""
404 FOUNDERS — Unit Tests for Configuration Management
"""

import os
from pathlib import Path
import pytest

from core.config import SystemConfig
from core.exceptions import ConfigurationError


def test_default_config_initialization(clean_env: None) -> None:
    """Validate default configuration values."""
    cfg = SystemConfig()
    assert cfg.env == "development"
    assert cfg.operating_mode == "hybrid"
    assert cfg.log_level == "INFO"
    assert cfg.compute.backend == "cpu"
    assert cfg.compute.max_local_memory_mb == 4096
    assert cfg.security.default_tier == "read_only"
    assert cfg.security.require_user_confirmation is True


def test_config_from_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    """Validate that environment variables properly override defaults."""
    monkeypatch.setenv("FOUNDERS_ENV", "production")
    monkeypatch.setenv("FOUNDERS_OPERATING_MODE", "personal")
    monkeypatch.setenv("FOUNDERS_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("FOUNDERS_COMPUTE_BACKEND", "cuda")
    monkeypatch.setenv("FOUNDERS_MAX_LOCAL_MEMORY_MB", "8192")
    monkeypatch.setenv("FOUNDERS_REST_PORT", "9000")

    cfg = SystemConfig.from_env()
    assert cfg.env == "production"
    assert cfg.operating_mode == "personal"
    assert cfg.log_level == "DEBUG"
    assert cfg.compute.backend == "cuda"
    assert cfg.compute.max_local_memory_mb == 8192
    assert cfg.api.rest_port == 9000


def test_invalid_integer_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """Validate that invalid integer environment variables raise ConfigurationError."""
    monkeypatch.setenv("FOUNDERS_MAX_LOCAL_MEMORY_MB", "invalid_number")
    with pytest.raises(ConfigurationError):
        SystemConfig.from_env()


def test_config_from_file(tmp_path: Path) -> None:
    """Validate loading config from a YAML file."""
    config_file = tmp_path / "test_config.yaml"
    config_file.write_text(
        "env: staging\n"
        "operating_mode: general\n"
        "compute:\n"
        "  backend: jax\n"
        "  max_cpu_threads: 16\n",
        encoding="utf-8",
    )

    cfg = SystemConfig.from_file(config_file)
    assert cfg.env == "staging"
    assert cfg.operating_mode == "general"
    assert cfg.compute.backend == "jax"
    assert cfg.compute.max_cpu_threads == 16


def test_config_serialization() -> None:
    """Validate dictionary serialization and roundtrip."""
    cfg = SystemConfig()
    d = cfg.to_dict()
    assert isinstance(d, dict)
    assert d["env"] == "development"
    assert d["compute"]["backend"] == "cpu"
