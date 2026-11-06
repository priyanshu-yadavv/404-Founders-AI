"""
404 FOUNDERS — Cluster Security & Governance Tests
Validates zero-trust RBAC authorization, SSH key requirements, secret sanitization,
container profiles, and audit log generation.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
import pytest

from infrastructure.security import (
    ClusterRole,
    ClusterSecurityManager,
)


def test_rbac_authorization_matrix() -> None:
    """Verify RBAC permissions for admin, ml_engineer, researcher, and auditor."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        audit_path = Path(tmp_dir) / "audit.jsonl"
        sec = ClusterSecurityManager(audit_log_path=audit_path)

        # Admin can drain nodes and reconfigure fabric
        assert sec.authorize_action("alice", ClusterRole.CLUSTER_ADMIN, "node:drain") is True
        assert sec.authorize_action("alice", ClusterRole.CLUSTER_ADMIN, "fabric:reconfigure") is True

        # ML Engineer can submit jobs and write checkpoints, but cannot drain nodes
        assert sec.authorize_action("bob", ClusterRole.ML_ENGINEER, "job:submit") is True
        assert sec.authorize_action("bob", ClusterRole.ML_ENGINEER, "checkpoint:write") is True
        assert sec.authorize_action("bob", ClusterRole.ML_ENGINEER, "node:drain") is False

        # Researcher can read checkpoints and metrics, but cannot write checkpoints
        assert sec.authorize_action("carol", ClusterRole.RESEARCHER, "checkpoint:read") is True
        assert sec.authorize_action("carol", ClusterRole.RESEARCHER, "metrics:read") is True
        assert sec.authorize_action("carol", ClusterRole.RESEARCHER, "checkpoint:write") is False

        # Auditor can read metrics and audit logs, but cannot submit jobs
        assert sec.authorize_action("dave", ClusterRole.AUDITOR_OBSERVER, "metrics:read") is True
        assert sec.authorize_action("dave", ClusterRole.AUDITOR_OBSERVER, "job:submit") is False

        # Audit records should exist
        assert audit_path.exists()
        lines = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines() if line]
        assert len(lines) >= 7


def test_ssh_key_validation_policy() -> None:
    """Verify Ed25519 keys are approved while RSA and malformed keys are rejected."""
    sec = ClusterSecurityManager()

    # Valid Ed25519 key
    ed25519_key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIExampleKey12345 user@workstation"
    is_valid, msg = sec.validate_ssh_public_key(ed25519_key)
    assert is_valid is True
    assert "Approved" in msg

    # Deprecated RSA key
    rsa_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC... user@workstation"
    is_valid_rsa, msg_rsa = sec.validate_ssh_public_key(rsa_key)
    assert is_valid_rsa is False
    assert "deprecated" in msg_rsa.lower()

    # Invalid garbage text
    is_valid_bad, msg_bad = sec.validate_ssh_public_key("invalid_key_string")
    assert is_valid_bad is False


def test_secret_sanitization() -> None:
    """Verify automated redaction of sensitive credentials, API keys, and tokens."""
    sec = ClusterSecurityManager()

    raw_log = (
        "Starting job with token: hf_AbCdEfGhIjKlMnOpQrStUvWxYz01234567 "
        "and OpenAI secret sk-1234567890abcdef1234567890abcdef12 "
        "and AWS key AKIAIOSFODNN7EXAMPLE."
    )

    clean_log = sec.sanitize_text(raw_log)
    assert "hf_" not in clean_log
    assert "sk-" not in clean_log
    assert "AKIA" not in clean_log
    assert "[REDACTED_SECRET]" in clean_log


def test_container_security_profile() -> None:
    """Verify container security options enforce non-root and least-privilege."""
    sec = ClusterSecurityManager()
    profile = sec.get_container_security_profile()

    assert profile["run_as_user"] == "1000:1000"
    assert profile["read_only_root_filesystem"] is True
    assert "ALL" in profile["drop_capabilities"]
    assert profile["no_new_privileges"] is True
    assert profile["ipc_mode"] == "host"  # Required for PyTorch CUDA IPC
