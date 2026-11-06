"""
404 FOUNDERS — FastAPI REST API Tests
Validates health check, telemetry, phase status, tokenizer encoding/decoding,
neural generation, and OpenAPI documentation endpoints.
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


def test_health_endpoints(client: TestClient) -> None:
    """Verify both /health and /api/v1/health return 200 with active subsystem states."""
    for path in ("/health", "/api/v1/health"):
        res = client.get(path)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert data["version"] == "0.5.0"
        assert data["operating_mode"] == "hybrid"
        assert data["neural_core_ready"] is True
        assert data["tokenizer_ready"] is True
        assert data["model_parameter_count"] > 0
        assert data["uptime_seconds"] >= 0.0


def test_system_telemetry_endpoint(client: TestClient) -> None:
    """Verify telemetry endpoint returns host hardware and memory budget."""
    res = client.get("/api/v1/system/telemetry")
    assert res.status_code == 200
    data = res.json()
    assert "cpu_model" in data
    assert data["physical_cores"] >= 1
    assert data["total_ram_gb"] > 0
    assert data["safe_memory_budget_gb"] > 0
    assert data["execution_mode"] == "local_cpu"


def test_phase_status_endpoint(client: TestClient) -> None:
    """Verify phase status returns roadmap phases and completed milestones."""
    res = client.get("/api/v1/phases/status")
    assert res.status_code == 200
    data = res.json()
    assert "Phase 05" in data["current_phase"]
    assert len(data["completed_phases"]) >= 4


def test_tokenizer_encode_and_decode(client: TestClient) -> None:
    """Verify tokenizer endpoints encode text and decode IDs."""
    test_text = "404 FOUNDERS Localhost Testing"

    # 1. Encode
    enc_res = client.post(
        "/api/v1/tokenizer/encode",
        json={"text": test_text, "add_bos": True, "add_eos": False},
    )
    assert enc_res.status_code == 200
    enc_data = enc_res.json()
    assert enc_data["text"] == test_text
    assert len(enc_data["ids"]) > 0
    assert len(enc_data["tokens"]) == len(enc_data["ids"])
    token_ids = enc_data["ids"]

    # 2. Decode
    dec_res = client.post(
        "/api/v1/tokenizer/decode",
        json={"ids": token_ids, "skip_special_tokens": True},
    )
    assert dec_res.status_code == 200
    dec_data = dec_res.json()
    assert dec_data["text"] == test_text


def test_neural_generate_endpoint(client: TestClient) -> None:
    """Verify neural generation produces genuine greedy tokens from model weights."""
    res = client.post(
        "/api/v1/neural/generate",
        json={"prompt": "Systems check", "max_new_tokens": 4, "mode": "general"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["prompt"] == "Systems check"
    assert len(data["prompt_ids"]) > 0
    assert len(data["generated_ids"]) == 4
    assert len(data["generated_tokens"]) == 4
    assert data["total_parameters"] > 0
    assert data["is_random_initialization"] is True
    assert data["latency_ms"] > 0.0


def test_openapi_docs_endpoint(client: TestClient) -> None:
    """Verify Swagger UI and OpenAPI JSON endpoints are accessible."""
    docs_res = client.get("/docs")
    assert docs_res.status_code == 200
    assert "text/html" in docs_res.headers.get("content-type", "")

    schema_res = client.get("/openapi.json")
    assert schema_res.status_code == 200
    schema_data = schema_res.json()
    assert schema_data["info"]["title"] == "404 FOUNDERS API"
    assert "/health" in schema_data["paths"]
    assert "/api/v1/neural/generate" in schema_data["paths"]
