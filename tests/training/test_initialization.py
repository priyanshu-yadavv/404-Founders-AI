"""
404 FOUNDERS — Unit Tests for Model Random Initialization
"""

import torch

from training.configs.model_config import EXPERIMENTAL_TINY_CONFIG, InitStrategy
from training.initialization.initializer import ModelInitializer


def test_random_initialization_finiteness_and_report() -> None:
    """Verify all parameters are finite and initialization report is complete."""
    initializer = ModelInitializer(EXPERIMENTAL_TINY_CONFIG)
    model, report = initializer.initialize_model(seed=404)

    assert report.all_finite is True
    assert report.total_parameters > 0
    assert report.trainable_parameters == report.total_parameters
    assert report.is_random_initialization is True
    assert report.pretrained_weights_loaded is False
    assert len(report.weight_digest_sha256) == 64
    assert len(report.layers) > 0

    # Verify no NaN or Inf in actual parameter tensors
    for name, param in model.named_parameters():
        assert torch.all(torch.isfinite(param)).item() is True


def test_deterministic_reproducibility() -> None:
    """Verify identical seeds produce identical weights, different seeds diverge."""
    initializer = ModelInitializer(EXPERIMENTAL_TINY_CONFIG)
    is_reproducible = initializer.verify_reproducibility(seed=404)
    assert is_reproducible is True


def test_alternate_initialization_strategies() -> None:
    """Verify Xavier uniform and Kaiming normal initialization schemes."""
    cfg_xavier = EXPERIMENTAL_TINY_CONFIG
    cfg_xavier.init_strategy = InitStrategy.XAVIER_UNIFORM.value
    init_x = ModelInitializer(cfg_xavier)
    m_x, rep_x = init_x.initialize_model(seed=42)
    assert rep_x.all_finite is True

    cfg_kaiming = EXPERIMENTAL_TINY_CONFIG
    cfg_kaiming.init_strategy = InitStrategy.KAIMING_NORMAL.value
    init_k = ModelInitializer(cfg_kaiming)
    m_k, rep_k = init_k.initialize_model(seed=42)
    assert rep_k.all_finite is True
