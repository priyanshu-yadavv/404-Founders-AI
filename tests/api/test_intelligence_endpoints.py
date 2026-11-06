"""
404 FOUNDERS — Intelligence API Endpoints Integration Tests
"""

import pytest
from fastapi.testclient import TestClient

from api.rest.app import create_app


@pytest.fixture(scope="module")
def client() -> TestClient:
    from api.rest.app import initialize_runtime_services
    services = initialize_runtime_services()
    app = create_app(services=services)
    with TestClient(app) as test_client:
        yield test_client


def test_list_intelligence_modules(client: TestClient) -> None:
    resp = client.get("/api/v1/intelligence/modules")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "active"
    assert data["total_modules"] == 12
    assert len(data["modules"]) == 12


def test_route_intelligence_query(client: TestClient) -> None:
    resp = client.post("/api/v1/intelligence/query", json={"query": "calculate 25 * 4"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["primary_engine"] == "mathematical"
    assert "100.0" in data["combined_summary"]


def test_logical_endpoint(client: TestClient) -> None:
    payload = {
        "problem": "Evaluate system stability",
        "premises": ["Server memory is at 95%", "High memory triggers garbage collection"],
    }
    resp = client.post("/api/v1/intelligence/logical", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["premises_count"] == 2
    assert 0.0 <= data["epistemic_uncertainty"] <= 1.0


def test_math_endpoint(client: TestClient) -> None:
    resp = client.post("/api/v1/intelligence/math", json={"expression": "100 / 4 + 15"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["exact_solution"] == 40.0
    assert data["is_verified"] is True


def test_coding_endpoint(client: TestClient) -> None:
    py_code = "def add(x, y):\n    return x + y\n"
    resp = client.post("/api/v1/intelligence/coding", json={"code": py_code, "language": "python"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["language"] == "python"
    assert data["is_valid_syntax"] is True
    assert "add" in data["functions"]
    assert data["sandbox_execution_permitted"] is False


def test_security_endpoint(client: TestClient) -> None:
    logs = ["GET /api?user=' OR 1=1 -- HTTP/1.1 200"]
    resp = client.post("/api/v1/intelligence/security", json={"logs": logs})
    assert resp.status_code == 200
    data = resp.json()
    assert data["threats_detected_count"] >= 1
    assert data["is_defensive_compliant"] is True


def test_planning_endpoint(client: TestClient) -> None:
    subtasks = [
        {"id": "T1", "title": "Inspect disk usage", "dependencies": []},
        {"id": "T2", "title": "Delete temporary logs", "dependencies": ["T1"]},
    ]
    resp = client.post("/api/v1/intelligence/plan", json={"objective": "Log cleanup", "subtasks": subtasks})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_tasks"] == 2
    assert data["requires_human_approval"] is True


def test_self_evaluate_endpoint(client: TestClient) -> None:
    payload = {
        "query": "What is the capital of France?",
        "candidate_output": "The capital of France is Paris.",
    }
    resp = client.post("/api/v1/intelligence/self_evaluate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_valid"] is True
    assert data["quality_score"] >= 0.70
