"""
404 FOUNDERS — Integration Tests for 10-Step Preflight Verification & Toy Overfitting
"""

from training.configs.model_config import EXPERIMENTAL_TINY_CONFIG
from training.validation.preflight_verifier import PreflightVerifier


def test_ten_step_preflight_verification() -> None:
    """Verify all 10 preflight integrity checks pass on CPU."""
    verifier = PreflightVerifier(model_config=EXPERIMENTAL_TINY_CONFIG)
    report = verifier.run_all_checks()

    assert report.all_passed is True
    assert len(report.results) == 10

    for step_res in report.results:
        assert step_res.passed is True, f"Failed step {step_res.step_number}: {step_res.step_name} - {step_res.detail}"


def test_toy_overfitting_loss_reduction() -> None:
    """Verify step 10 specifically proves model parameter adaptation by reducing loss > 20%."""
    verifier = PreflightVerifier(model_config=EXPERIMENTAL_TINY_CONFIG)
    report = verifier.run_all_checks()

    step_10 = next(r for r in report.results if r.step_number == 10)
    assert step_10.passed is True
    assert "reduction" in step_10.detail.lower()
