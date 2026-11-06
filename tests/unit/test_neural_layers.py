"""
404 FOUNDERS — Unit Tests for Custom Neural Layers
"""

import pytest
import torch

from core.exceptions import ShapeMismatchError
from neural_architecture.layers.normalization import CustomRMSNorm
from neural_architecture.layers.position import RotaryPositionEmbedding
from neural_architecture.layers.projections import (
    FeatureTransformationLayer,
    InputProjectionLayer,
    OutputProjectionLayer,
)
from neural_architecture.layers.residual import ResidualConnection


def test_custom_rmsnorm_forward_and_gradient() -> None:
    """Verify CustomRMSNorm output shapes, scaling, and gradient propagation."""
    norm = CustomRMSNorm(dim=64, eps=1e-6)
    x = torch.randn(2, 8, 64, requires_grad=True)
    out = norm(x)

    assert out.shape == (2, 8, 64)
    # Check that root mean square of output along last dim is approximately 1.0
    rms = torch.sqrt(torch.mean(out.pow(2), dim=-1))
    assert torch.allclose(rms, torch.ones_like(rms), atol=1e-2)

    # Test backward pass
    loss = out.sum()
    loss.backward()
    assert x.grad is not None
    assert not torch.isnan(x.grad).any()

    # Test invalid dimension exception
    with pytest.raises(ShapeMismatchError):
        norm(torch.randn(2, 8, 32))


def test_input_projection_discrete_and_continuous() -> None:
    """Verify InputProjectionLayer handles discrete tokens and continuous embeddings."""
    proj = InputProjectionLayer(d_model=64, vocab_size=500, input_dim=32)

    # 1. Discrete token input
    tokens = torch.randint(0, 500, (2, 10))
    out_tokens = proj(tokens)
    assert out_tokens.shape == (2, 10, 64)

    # 2. Continuous vector input
    continuous = torch.randn(2, 10, 32)
    out_cont = proj(continuous)
    assert out_cont.shape == (2, 10, 64)


def test_output_projection() -> None:
    """Verify OutputProjectionLayer maps hidden states to output dimensions."""
    out_proj = OutputProjectionLayer(d_model=64, output_dim=100)
    x = torch.randn(2, 5, 64)
    logits = out_proj(x)
    assert logits.shape == (2, 5, 100)

    with pytest.raises(ShapeMismatchError):
        out_proj(torch.randn(2, 5, 32))


def test_feature_transformation_swiglu() -> None:
    """Verify Gated SwiGLU forward pass and autograd gradients."""
    ffn = FeatureTransformationLayer(d_model=64, intermediate_dim=128)
    x = torch.randn(2, 4, 64, requires_grad=True)
    out = ffn(x)

    assert out.shape == (2, 4, 64)
    loss = out.sum()
    loss.backward()
    assert x.grad is not None
    assert ffn.w_gate.weight.grad is not None


def test_residual_connection() -> None:
    """Verify pre-normalized residual connection preserves dimensions."""
    residual = ResidualConnection(dim=64, use_layer_scale=True, initial_scale=1.0)
    x = torch.randn(2, 6, 64)

    def sublayer(h: torch.Tensor) -> torch.Tensor:
        return h * 2.0

    out = residual(x, sublayer)
    assert out.shape == (2, 6, 64)


def test_rotary_position_embedding() -> None:
    """Verify RoPE rotates queries and keys maintaining tensor shapes."""
    rope = RotaryPositionEmbedding(dim=32, max_seq_len=128)
    q = torch.randn(2, 4, 16, 32)  # (batch, heads, seq_len, head_dim)
    k = torch.randn(2, 4, 16, 32)

    q_rot, k_rot = rope(q, k, seq_len=16)
    assert q_rot.shape == q.shape
    assert k_rot.shape == k.shape
    # Ensure vectors were modified by rotation
    assert not torch.equal(q, q_rot)
