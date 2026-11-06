"""
404 FOUNDERS — Unit Tests for Foundation Model Configurations
"""

import pytest

from training.configs.model_config import (
    EXPERIMENTAL_LOCAL_CPU_CONFIG,
    EXPERIMENTAL_TINY_CONFIG,
    PRODUCTION_CLUSTER_SPEC,
    RESEARCH_PILOT_CONFIG,
    FoundationModelConfig,
    InitStrategy,
    PrecisionType,
    PretrainingConfig,
)


def test_foundation_model_config_validation() -> None:
    """Verify validation boundaries and exception handling on malformed configurations."""
    cfg = FoundationModelConfig(
        vocab_size=512,
        d_model=64,
        n_layers=2,
        n_heads=2,
        max_seq_len=64,
    )
    assert cfg.vocab_size == 512
    assert cfg.d_model == 64
    assert cfg.n_layers == 2
    assert cfg.n_heads == 2

    # Incompatible d_model and n_heads
    with pytest.raises(ValueError, match="divisible by n_heads"):
        FoundationModelConfig(d_model=65, n_heads=4)

    # Invalid vocab_size
    with pytest.raises(ValueError, match="vocab_size must be positive"):
        FoundationModelConfig(vocab_size=0)

    # Invalid dropout
    with pytest.raises(ValueError, match="dropout must be in"):
        FoundationModelConfig(dropout=1.5)


def test_pretraining_config_effective_batch_size() -> None:
    """Verify effective batch size calculation and serialization."""
    cfg = PretrainingConfig(
        batch_size=4,
        gradient_accumulation_steps=8,
        learning_rate=2e-4,
        max_steps=500,
    )
    assert cfg.effective_batch_size == 32

    # Serialization roundtrip
    d = cfg.to_dict()
    assert d["batch_size"] == 4
    assert d["gradient_accumulation_steps"] == 8

    reloaded = PretrainingConfig.from_dict(d)
    assert reloaded.effective_batch_size == 32
    assert reloaded.learning_rate == 2e-4


def test_preset_profiles_validity() -> None:
    """Verify all 4 approved standard profiles instantiate cleanly without error."""
    profiles = [
        EXPERIMENTAL_TINY_CONFIG,
        EXPERIMENTAL_LOCAL_CPU_CONFIG,
        RESEARCH_PILOT_CONFIG,
        PRODUCTION_CLUSTER_SPEC,
    ]
    for p in profiles:
        assert p.vocab_size > 0
        assert p.d_model % p.n_heads == 0
        assert p.n_layers > 0
        nc_cfg = p.to_neural_core_config()
        assert nc_cfg.d_model == p.d_model
        assert nc_cfg.n_layers == p.n_layers
        assert nc_cfg.n_heads == p.n_heads
