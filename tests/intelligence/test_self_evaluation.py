"""
404 FOUNDERS — Self-Evaluation and Error Detection Engine Unit Tests
"""

import pytest
from core.intelligence.self_evaluation import SelfEvaluationEngine


@pytest.fixture
def engine(tmp_path) -> SelfEvaluationEngine:
    return SelfEvaluationEngine(log_dir=tmp_path)


def test_internal_contradiction_detection(engine: SelfEvaluationEngine) -> None:
    text = "The firewall rule is enabled on port 443. Notice that the firewall rule is disabled on port 443."
    findings = engine.check_contradictions(text)
    assert len(findings) >= 1
    assert findings[0].category == "CONTRADICTION"


def test_unsupported_absolute_claim(engine: SelfEvaluationEngine) -> None:
    text = "This encryption implementation is 100% guaranteed unhackable and undeniably proven safe."
    findings = engine.check_unsupported_claims(text)
    assert len(findings) >= 1
    assert findings[0].category == "UNSUPPORTED_CLAIM"


def test_epistemic_modesty_recognition(engine: SelfEvaluationEngine) -> None:
    honest_output = "I do not know the exact configuration since the cluster manifest was not provided."
    res = engine.evaluate(query="What is the cluster topology?", output=honest_output)
    assert res.epistemic_modesty_status == "UNKNOWN_DECLARED"
    assert res.is_valid is True


def test_missing_information_audit(engine: SelfEvaluationEngine) -> None:
    calc_query = "Calculate the throughput of 4 GPUs at 50 TFLOPS each."
    bad_output = "The GPUs are very fast and performant."
    res = engine.evaluate(query=calc_query, output=bad_output)
    assert len(res.missing_elements) > 0
    assert any("numerical figures" in m for m in res.missing_elements)


def test_offline_feedback_logging(engine: SelfEvaluationEngine, tmp_path) -> None:
    res = engine.evaluate(
        query="Explain gradient descent",
        output="Gradient descent minimizes loss by moving opposite the gradient.",
        log_feedback=True,
    )
    assert res.is_valid is True
    assert res.logged_record_id is not None
    log_file = tmp_path / "evaluation_feedback.jsonl"
    assert log_file.is_file()
    assert len(log_file.read_text(encoding="utf-8").strip()) > 20
