"""
404 FOUNDERS — Creative Problem-Solving Engine Unit Tests
"""

import pytest
from core.reasoning.creative import CreativeProblemSolvingEngine


@pytest.fixture
def engine() -> CreativeProblemSolvingEngine:
    return CreativeProblemSolvingEngine()


def test_problem_inversion(engine: CreativeProblemSolvingEngine) -> None:
    problem = "Optimize database write throughput during peak load."
    inverted = engine.invert_problem(problem)
    assert "Inverted Problem Formulation" in inverted
    assert "Optimize database write throughput" in inverted


def test_constraint_relaxation(engine: CreativeProblemSolvingEngine) -> None:
    relaxations = engine.relax_constraints(["Synchronous execution", "Single node bottleneck"])
    assert len(relaxations) == 2
    assert "Synchronous execution" in relaxations[0].assumed_constraint
    assert len(relaxations[0].unlocked_solution_space) > 20


def test_cross_domain_analogies(engine: CreativeProblemSolvingEngine) -> None:
    res = engine.solve("Design resilient traffic backpressure for inference API.")
    assert len(res.analogies) >= 3
    domains = [a.source_domain for a in res.analogies]
    assert any("Biological" in d for d in domains)
    assert any("Civil Engineering" in d for d in domains)


def test_solution_vector_synthesis(engine: CreativeProblemSolvingEngine) -> None:
    res = engine.solve("Scale multi-tenant vector index lookup.")
    assert len(res.solution_vectors) >= 3
    for vec in res.solution_vectors:
        assert 0.0 <= vec.feasibility_score <= 1.0
        assert 0.0 <= vec.novelty_score <= 1.0
        assert len(vec.pros) > 0
