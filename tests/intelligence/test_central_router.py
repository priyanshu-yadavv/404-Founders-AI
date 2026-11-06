"""
404 FOUNDERS — Central Intelligence Router Unit Tests
"""

import pytest
import torch
from core.intelligence.central_router import CentralIntelligenceRouter


@pytest.fixture
def router() -> CentralIntelligenceRouter:
    return CentralIntelligenceRouter()


def test_intent_classification(router: CentralIntelligenceRouter) -> None:
    # Math intent
    plan_math = router.classify_intent("calculate the derivative and integral of x^2")
    assert plan_math.primary_engine == "mathematical"

    # Coding intent
    plan_code = router.classify_intent("review this python function and calculate its time complexity")
    assert plan_code.primary_engine == "coding"

    # Security intent
    plan_sec = router.classify_intent("analyze suspicious firewall log entries for injection attacks")
    assert plan_sec.primary_engine == "cybersecurity"

    # Fallback to knowledge for generic questions
    plan_gen = router.classify_intent("tell me something interesting")
    assert plan_gen.primary_engine == "knowledge"


def test_neural_dynamic_router_integration(router: CentralIntelligenceRouter) -> None:
    x = torch.randn(1, 16, 128)
    res = router.dispatch("evaluate logic and premises", x_tensor=x)
    assert res.dispatch_plan.routing_decision is not None
    assert len(res.dispatch_plan.routing_decision.selected_expert_ids) > 0


def test_multi_engine_composition(router: CentralIntelligenceRouter) -> None:
    # A query mentioning both code and security triggers composite execution
    res = router.dispatch("review this unsafe code snippet for security vulnerabilities")
    assert "coding" in res.engine_outputs
    assert "cybersecurity" in res.engine_outputs
    assert len(res.combined_summary) > 20


def test_cross_engine_conflict_detection(router: CentralIntelligenceRouter) -> None:
    # Inject code that has valid syntax but high threat patterns
    code_with_threat = "exec(__import__('base64').b64decode('c3lzdGVt'))"
    hints = {
        "code": code_with_threat,
        "logs": ["GET /?q=' OR 1=1 HTTP/1.1"],
    }
    res = router.dispatch("review code with security audit", context_hints=hints)
    assert res.conflicts_detected is not None
