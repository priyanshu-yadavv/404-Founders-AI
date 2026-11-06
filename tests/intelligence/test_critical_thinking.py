"""
404 FOUNDERS — Critical Thinking Engine Unit Tests
"""

import pytest
from core.reasoning.critical import CriticalThinkingEngine


@pytest.fixture
def engine() -> CriticalThinkingEngine:
    return CriticalThinkingEngine()


def test_detect_ad_hominem(engine: CriticalThinkingEngine) -> None:
    text = "We should reject his proposal because he is a fool and incompetent."
    fallacies = engine.detect_fallacies(text)
    assert len(fallacies) > 0
    assert any(f.fallacy_type == "AD_HOMINEM" for f in fallacies)


def test_detect_false_dilemma(engine: CriticalThinkingEngine) -> None:
    text = "Either you support our software architecture completely or you want the system to fail."
    fallacies = engine.detect_fallacies(text)
    assert len(fallacies) > 0
    assert any(f.fallacy_type == "FALSE_DILEMMA" for f in fallacies)


def test_detect_confirmation_bias(engine: CriticalThinkingEngine) -> None:
    text = "We should only evaluate evidence that supports our initial conclusion."
    biases = engine.detect_biases(text)
    assert len(biases) > 0
    assert any(b.bias_name == "CONFIRMATION_BIAS" for b in biases)


def test_evaluate_evidence_rigor(engine: CriticalThinkingEngine) -> None:
    anecdotal_text = "In my experience, this algorithm always runs fast."
    eval_anecdote = engine.evaluate_evidence(anecdotal_text)
    assert eval_anecdote.sample_adequacy == "ANECDOTAL"
    assert eval_anecdote.empirical_support_score <= 0.40

    empirical_text = "In benchmark tests across 1000 trials, latency averaged 4.2ms."
    eval_emp = engine.evaluate_evidence(empirical_text)
    assert eval_emp.sample_adequacy == "SUFFICIENT"
    assert eval_emp.empirical_support_score >= 0.80


def test_full_critical_analysis(engine: CriticalThinkingEngine) -> None:
    arg = "Everyone knows this design is best; if we do not adopt it, it will inevitably lead to disaster."
    res = engine.analyze(arg)
    assert res.soundness_rating in ["FALLACIOUS", "QUESTIONABLE"]
    assert len(res.fallacies_detected) >= 1
    assert len(res.alternative_interpretations) >= 2
