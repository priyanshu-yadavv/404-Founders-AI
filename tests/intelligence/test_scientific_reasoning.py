"""
404 FOUNDERS — Scientific Reasoning Engine Unit Tests
"""

import pytest
from core.reasoning.scientific import ScientificReasoningEngine


@pytest.fixture
def engine() -> ScientificReasoningEngine:
    return ScientificReasoningEngine()


def test_kinematics_time_distance(engine: ScientificReasoningEngine) -> None:
    # u = 0, a = 9.8, t = 2 -> s = 0.5 * 9.8 * 4 = 19.6 m
    res = engine.solve_kinematics(initial_velocity=0.0, acceleration=9.8, time=2.0)
    assert pytest.approx(res.calculated_value) == 19.6
    assert "kinematics" in res.domain


def test_ohms_law(engine: ScientificReasoningEngine) -> None:
    # V = 12V, R = 4 Ohm -> I = 3A
    res = engine.solve_ohms_law(voltage=12.0, resistance=4.0)
    assert pytest.approx(res.calculated_value) == 3.0
    assert res.units == "Amperes"


def test_ideal_gas_law(engine: ScientificReasoningEngine) -> None:
    # P = (n * R * T) / V
    # n = 1, T = 300K, V = 0.025 m^3
    res = engine.solve_ideal_gas(volume=0.025, moles=1.0, temperature_kelvin=300.0)
    expected_p = (1.0 * 8.314462618 * 300.0) / 0.025
    assert pytest.approx(res.calculated_value, rel=1e-3) == expected_p


def test_hypothesis_evaluation(engine: ScientificReasoningEngine) -> None:
    res = engine.evaluate_hypothesis(
        hypothesis="Increasing optimizer batch size linearly decreases gradient variance.",
        independent_variable="batch size",
        dependent_variable="gradient variance",
        controlled_variables=["learning rate", "architecture depth"],
    )
    assert res.is_falsifiable is True
    assert "batch size" in res.falsification_criteria
    assert len(res.recommended_experimental_controls) >= 3


def test_evidence_comparison(engine: ScientificReasoningEngine) -> None:
    dataset_a = [10.0, 15.0, 20.0, 25.0]
    dataset_b = [10.2, 14.8, 19.9, 25.1]
    res = engine.compare_evidence(dataset_a, dataset_b, tolerance=0.05)
    assert res.is_consistent is True
    assert res.mean_discrepancy < 0.25
    assert res.confidence_score > 0.90


def test_grounded_citation_tracking(engine: ScientificReasoningEngine) -> None:
    sources = [
        {"title": "Attention Is All You Need", "author": "Vaswani et al.", "year": "2017"},
        {"title": "Deep Residual Learning", "author": "He et al.", "year": "2016"},
    ]
    res = engine.analyze("Transformer scaling dynamics", provided_sources=sources)
    assert len(res.attributed_citations) == 2
    assert "Vaswani et al." in res.attributed_citations[0]

    # Without sources, engine must declare unverified claims rather than hallucinating
    res_empty = engine.analyze("Cold fusion discovery", provided_sources=[])
    assert len(res_empty.attributed_citations) == 0
    assert len(res_empty.unverified_claims) > 0
    assert "No external citations" in res_empty.unverified_claims[0]
