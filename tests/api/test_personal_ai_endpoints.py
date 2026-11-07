"""
404 FOUNDERS — Personal AI REST API Endpoints Integration Tests
Validates all /api/v1/personal-ai/... endpoints including status, sessions, chat,
system vitals, process guards, sandboxed filesystem, command safety advisor,
network diagnostics, git topology, security posture, approvals, and emergency stop.
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from api.rest.app import create_app, initialize_runtime_services


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Creates a test client with pre-initialized runtime services."""
    services = initialize_runtime_services()
    app = create_app(services=services)
    with TestClient(app) as test_client:
        yield test_client


def test_personal_ai_status(client: TestClient) -> None:
    """Verify runtime vitals and localhost binding status."""
    res = client.get("/api/v1/personal-ai/status")
    assert res.status_code == 200
    data = res.json()
    assert data["is_running"] is True
    assert data["host"] == "127.0.0.1"
    assert data["port"] == 8000
    assert data["emergency_shutdown_active"] is False
    assert data["uptime_seconds"] >= 0.0


def test_personal_ai_session_creation(client: TestClient) -> None:
    """Verify isolated authenticated session creation."""
    res = client.post("/api/v1/personal-ai/sessions", json={"user_id": "operator_test"})
    assert res.status_code == 200
    data = res.json()
    assert data["session_id"].startswith("PAI-")
    assert len(data["auth_token"]) >= 32
    assert data["user_id"] == "operator_test"
    assert data["is_active"] is True


def test_personal_ai_chat_multilingual(client: TestClient) -> None:
    """Verify chat interaction and intent classification across English, Hindi, and Hinglish."""
    # English system diagnosis
    r1 = client.post(
        "/api/v1/personal-ai/chat",
        json={"user_id": "operator_test", "query": "Diagnose my system performance and check resource consumers"}
    )
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["intent"] == "DIAGNOSE_SYSTEM_PERFORMANCE"
    assert "System Health Analysis" in d1["assistant_response"]
    assert "cpu_usage_pct" in d1["data_payload"]

    # Hindi performance query
    r2 = client.post(
        "/api/v1/personal-ai/chat",
        json={"user_id": "operator_test", "query": "सिस्टम का रैम और सीपीयू यूटिलाइजेशन चेक करो"}
    )
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["intent"] == "DIAGNOSE_SYSTEM_PERFORMANCE"

    # Hinglish query
    r3 = client.post(
        "/api/v1/personal-ai/chat",
        json={"user_id": "operator_test", "query": "Mera RAM aur CPU check karo"}
    )
    assert r3.status_code == 200
    d3 = r3.json()
    assert d3["intent"] == "INSPECT_HARDWARE"


def test_personal_ai_system_summary_and_hardware(client: TestClient) -> None:
    """Verify system summary and real hardware telemetry endpoints."""
    r_sum = client.get("/api/v1/personal-ai/system/summary")
    assert r_sum.status_code == 200
    d_sum = r_sum.json()
    assert d_sum["os_name"] in ["Linux", "Windows"]
    assert d_sum["cpu"]["logical_cores"] >= 1
    assert d_sum["memory"]["total_ram_mb"] > 0
    assert d_sum["uptime_hours"] >= 0.0

    r_hw = client.get("/api/v1/personal-ai/system/hardware")
    assert r_hw.status_code == 200
    d_hw = r_hw.json()
    assert "cpu_model" in d_hw
    assert "ram_used_pct" in d_hw


def test_personal_ai_processes(client: TestClient) -> None:
    """Verify process listing and protected system process flagging."""
    res = client.get("/api/v1/personal-ai/processes?limit=30")
    assert res.status_code == 200
    procs = res.json()
    assert len(procs) > 0
    assert any(p["is_protected"] is True for p in procs)


def test_personal_ai_filesystem_list_and_read(client: TestClient) -> None:
    """Verify safe directory listing and secret-scrubbed reading."""
    r_list = client.post(
        "/api/v1/personal-ai/filesystem/list",
        json={"dir_path": "personal_ai", "limit": 20}
    )
    assert r_list.status_code == 200
    d_list = r_list.json()
    assert len(d_list["entries"]) > 0

    r_read = client.post(
        "/api/v1/personal-ai/filesystem/read",
        json={"file_path": "personal_ai/__init__.py", "max_bytes": 10240}
    )
    assert r_read.status_code == 200
    d_read = r_read.json()
    assert "404 FOUNDERS" in d_read["content"]
    assert d_read["scrubbed_secrets_count"] >= 0


def test_personal_ai_filesystem_traversal_blocked(client: TestClient) -> None:
    """Verify that path traversal attempts are rejected with 403 Forbidden."""
    res = client.post(
        "/api/v1/personal-ai/filesystem/read",
        json={"file_path": "../../../etc/shadow", "max_bytes": 1024}
    )
    assert res.status_code == 403


def test_personal_ai_command_advisor(client: TestClient) -> None:
    """Verify command advisory risk tiering and blocked pattern detection."""
    # Permitted read-only
    r1 = client.post(
        "/api/v1/personal-ai/terminal/advise",
        json={"proposed_command": "git status", "user_intent": "Check status"}
    )
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["risk_tier"] == "READ_ONLY"
    assert d1["requires_approval"] is False
    assert d1["is_blocked"] is False

    # Blocked hazardous
    r2 = client.post(
        "/api/v1/personal-ai/terminal/advise",
        json={"proposed_command": "rm -rf /", "user_intent": "Clean root"}
    )
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["is_blocked"] is True
    assert "Root directory recursive deletion" in d2["block_reason"]


def test_personal_ai_network_endpoints(client: TestClient) -> None:
    """Verify bounded ping and safe DNS resolution diagnostics."""
    r_diag = client.get("/api/v1/personal-ai/network/diagnostics")
    assert r_diag.status_code == 200

    r_ping = client.post(
        "/api/v1/personal-ai/network/ping",
        json={"host": "127.0.0.1", "count": 1}
    )
    assert r_ping.status_code == 200
    d_ping = r_ping.json()
    assert d_ping["is_reachable"] is True

    r_dns = client.post(
        "/api/v1/personal-ai/network/dns",
        json={"hostname": "localhost"}
    )
    assert r_dns.status_code == 200
    d_dns = r_dns.json()
    assert d_dns["is_successful"] is True


def test_personal_ai_coding_and_security(client: TestClient) -> None:
    """Verify repo topology, git inspection, and security posture."""
    r_repo = client.get("/api/v1/personal-ai/coding/repo")
    assert r_repo.status_code == 200
    assert r_repo.json()["is_git_repository"] is True

    r_git = client.get("/api/v1/personal-ai/coding/git")
    assert r_git.status_code == 200
    assert "branch" in r_git.json()

    r_sec = client.get("/api/v1/personal-ai/security/posture")
    assert r_sec.status_code == 200
    assert "risk_level" in r_sec.json()


def test_personal_ai_approvals_and_audit(client: TestClient) -> None:
    """Verify approval tickets listing and audit logs endpoint."""
    r_appr = client.get("/api/v1/personal-ai/approvals")
    assert r_appr.status_code == 200
    assert isinstance(r_appr.json(), list)

    r_audit = client.get("/api/v1/personal-ai/audit/logs?limit=10")
    assert r_audit.status_code == 200
    assert isinstance(r_audit.json(), list)


def test_personal_ai_emergency_shutdown_and_reset(client: TestClient) -> None:
    """Verify emergency kill switch activation and reset."""
    # Trigger kill switch
    r_kill = client.post(
        "/api/v1/personal-ai/emergency/shutdown",
        json={"triggered_by": "test_suite", "reason": "Testing kill switch"}
    )
    assert r_kill.status_code == 200
    d_kill = r_kill.json()
    assert d_kill["is_active"] is True

    # Assert status reflects shutdown
    r_st = client.get("/api/v1/personal-ai/status")
    assert r_st.json()["emergency_shutdown_active"] is True

    # Reset kill switch
    r_reset = client.post("/api/v1/personal-ai/emergency/reset")
    assert r_reset.status_code == 200
    assert r_reset.json()["is_active"] is False

    # Assert status restored
    r_st_restored = client.get("/api/v1/personal-ai/status")
    assert r_st_restored.json()["emergency_shutdown_active"] is False
