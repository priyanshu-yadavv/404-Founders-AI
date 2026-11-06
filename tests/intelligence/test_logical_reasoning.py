"""
404 FOUNDERS — Logical Reasoning Engine Unit Tests
"""

import pytest
from core.reasoning.logical import (
    LogicalPremise,
    LogicalReasoningEngine,
    LogicalStep,
    Contradiction,
)


@pytest.fixture
def engine() -> LogicalReasoningEngine:
    return LogicalReasoningEngine()


def test_decompose_problem(engine: LogicalReasoningEngine) -> None:
    problem = "First inspect database schemas; second verify network connectivity; finally execute deployment."
    steps = engine.decompose_problem(problem)
    assert len(steps) >= 3
    assert any("inspect database" in s.lower() for s in steps)


def test_extract_assumptions(engine: LogicalReasoningEngine) -> None:
    text = "Assuming network latency is zero, if we scale the worker pool throughput will double."
    assumptions = engine.extract_assumptions(text)
    assert len(assumptions) > 0
    assert any("network latency is zero" in a.lower() for a in assumptions)


def test_detect_contradictions(engine: LogicalReasoningEngine) -> None:
    p1 = LogicalPremise("P1", "The encryption service is enabled for all endpoints.")
    p2 = LogicalPremise("P2", "The encryption service is disabled for all endpoints.")
    contradictions = engine.detect_contradictions([p1, p2])
    assert len(contradictions) == 1
    assert contradictions[0].severity == "CRITICAL"


def test_modus_ponens_deduction(engine: LogicalReasoningEngine) -> None:
    p1 = LogicalPremise("P1", "If authentication fails then the session is terminated.")
    p2 = LogicalPremise("P2", "Authentication fails for user 404.")
    steps = engine.evaluate_deduction([p1, p2])
    assert len(steps) >= 2
    assert any("Affirmed consequent" in s.statement for s in steps)


def test_candidate_comparison(engine: LogicalReasoningEngine) -> None:
    candidates = [
        {"id": "A", "description": "High throughput but violates zero-trust constraint", "pros": ["fast"], "cons": ["risky"]},
        {"id": "B", "description": "Compliant zero-trust architecture", "pros": ["secure", "scalable"], "cons": []},
    ]
    constraints = ["zero-trust"]
    evals = engine.compare_candidates(candidates, constraints)
    assert len(evals) == 2
    assert evals[0].id == "B"
    assert evals[0].satisfies_constraints is True
    assert evals[1].satisfies_constraints is False


def test_full_logical_analysis(engine: LogicalReasoningEngine) -> None:
    res = engine.analyze(
        problem="Determine optimal cache eviction policy assuming bounded RAM.",
        premises=["Memory is limited to 2GB.", "Workload follows power-law distribution."],
        target_conclusion="LRU cache is optimal",
    )
    assert res.problem.startswith("Determine optimal cache")
    assert len(res.premises) == 2
    assert 0.0 <= res.epistemic_uncertainty <= 1.0
    assert len(res.summary) > 20
