"""
Unit tests for MultimodalFusionEngine.
Verifies Early (modality embedding concatenation), Intermediate (cross-modal attention),
and Late (adaptive softmax gating) fusion layers, missing modality handling,
and tensor dimension contracts.
"""

import pytest
import torch

from neural_architecture.fusion.multimodal_fusion import (
    EarlyFusionLayer,
    CrossModalAttentionFusion,
    LateFusionAggregator,
    MultimodalFusionEngine,
    MultimodalInput,
    FusionOutput,
    ModalityType,
)


@pytest.fixture
def fusion_engine():
    return MultimodalFusionEngine(d_model=128, n_heads=4)


def test_early_fusion_layer():
    layer = EarlyFusionLayer(d_model=128)
    inputs = MultimodalInput(
        text_tensor=torch.randn(1, 10, 128),
        image_tensor=torch.randn(1, 16, 768),  # 768 will be projected to 128
    )
    fused_seq, mask = layer(inputs)

    assert fused_seq.shape == (1, 26, 128)  # 10 + 16 = 26 tokens
    assert mask.shape == (1, 26)
    assert mask.sum().item() == 26


def test_cross_modal_attention_fusion():
    cross_attn = CrossModalAttentionFusion(d_model=128, n_heads=4)
    x_target = torch.randn(2, 8, 128)
    x_source = torch.randn(2, 16, 128)
    out = cross_attn(x_target, x_source)

    assert out.shape == (2, 8, 128)
    # Check LayerScale parameter is present
    assert cross_attn.gamma.shape == (128,)


def test_late_fusion_aggregator():
    late = LateFusionAggregator(d_model=128)
    rep1 = torch.randn(2, 128)
    rep2 = torch.randn(2, 128)
    rep3 = torch.randn(2, 128)

    fused, weights = late([rep1, rep2, rep3])
    assert fused.shape == (2, 128)
    assert weights.shape == (2, 3)
    # Check softmax sum is 1.0 per batch item
    assert torch.allclose(weights.sum(dim=-1), torch.ones(2), atol=1e-5)


def test_multimodal_fusion_engine_early(fusion_engine):
    inputs = MultimodalInput(
        text_tensor=torch.randn(1, 12, 128),
        image_tensor=torch.randn(1, 16, 768),
        audio_tensor=torch.randn(1, 20, 257),
    )
    res = fusion_engine.fuse(inputs, stage="EARLY")

    assert isinstance(res, FusionOutput)
    assert res.fusion_stage == "EARLY"
    assert "TEXT" in res.active_modalities
    assert "IMAGE" in res.active_modalities
    assert "AUDIO" in res.active_modalities
    assert "VIDEO" in res.missing_modalities
    assert res.fused_representation.shape[1] == 12 + 16 + 20  # 48 tokens
    assert res.fused_representation.shape[2] == 128


def test_multimodal_fusion_engine_intermediate(fusion_engine):
    inputs = MultimodalInput(
        text_tensor=torch.randn(1, 8, 128),
        image_tensor=torch.randn(1, 8, 768),
    )
    res = fusion_engine.fuse(inputs, stage="INTERMEDIATE")

    assert res.fusion_stage == "INTERMEDIATE"
    assert res.fused_representation.shape == (1, 16, 128)


def test_multimodal_fusion_engine_late(fusion_engine):
    inputs = MultimodalInput(
        text_tensor=torch.randn(1, 10, 128),
        image_tensor=torch.randn(1, 16, 768),
    )
    res = fusion_engine.fuse(inputs, stage="LATE")

    assert res.fusion_stage == "LATE"
    assert res.fused_representation.shape == (1, 128)
    assert sum(res.modality_weights.values()) == pytest.approx(1.0, abs=1e-3)


def test_fusion_all_none_raises(fusion_engine):
    empty_inputs = MultimodalInput()
    with pytest.raises(ValueError, match="all input modality tensors are None"):
        fusion_engine.fuse(empty_inputs, stage="EARLY")


def test_fusion_invalid_stage_raises(fusion_engine):
    inputs = MultimodalInput(text_tensor=torch.randn(1, 5, 128))
    with pytest.raises(ValueError, match="Invalid fusion stage"):
        fusion_engine.fuse(inputs, stage="NON_EXISTENT")
