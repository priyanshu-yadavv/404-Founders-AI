"""
404 FOUNDERS — Unit Tests for Multi-Mechanism Attention
"""

import pytest
import torch

from core.attention.fusion_controller import AttentionFusionController
from core.attention.global_attention import GlobalAttention
from core.attention.hierarchical_attention import HierarchicalAttention
from core.attention.sparse_attention import SparseAttention


def test_global_attention_forward_and_mask() -> None:
    """Verify GlobalAttention output shapes, padding masks, and gradient flow."""
    attn = GlobalAttention(d_model=64, num_heads=4)
    x = torch.randn(2, 12, 64, requires_grad=True)

    # 1. Unmasked forward pass
    out, weights = attn(x)
    assert out.shape == (2, 12, 64)
    assert weights.shape == (2, 4, 12, 12)

    # 2. Masked forward pass (mask out last 4 tokens)
    mask = torch.zeros(2, 1, 12, 12)
    mask[:, :, :, 8:] = -1e9
    out_masked, weights_masked = attn(x, attention_mask=mask)
    assert out_masked.shape == (2, 12, 64)
    # Check that attention to masked tokens is near zero
    assert weights_masked[:, :, :, 8:].sum().item() < 1e-4

    # 3. Gradient propagation
    loss = out_masked.sum()
    loss.backward()
    assert x.grad is not None
    assert attn.q_proj.weight.grad is not None


def test_sparse_attention_sliding_window() -> None:
    """Verify SparseAttention output shapes and banded mask sparsity."""
    attn = SparseAttention(d_model=64, num_heads=4, window_size=3)
    x = torch.randn(2, 16, 64, requires_grad=True)

    out, weights = attn(x)
    assert out.shape == (2, 16, 64)
    assert weights.shape == (2, 4, 16, 16)

    # Check that tokens beyond window distance are zeroed out
    # For token 0, distance to token 10 is 10 > window_size 3 -> weight should be 0.0
    assert weights[:, :, 0, 10].sum().item() < 1e-5

    loss = out.sum()
    loss.backward()
    assert x.grad is not None


def test_hierarchical_attention() -> None:
    """Verify HierarchicalAttention micro/macro attention and padding."""
    attn = HierarchicalAttention(d_model=64, num_heads=4, chunk_size=8)
    # Test on sequence length that is not a clean multiple of chunk_size (19 % 8 != 0)
    x = torch.randn(2, 19, 64, requires_grad=True)

    out, _ = attn(x)
    assert out.shape == (2, 19, 64)

    loss = out.sum()
    loss.backward()
    assert x.grad is not None
    assert attn.intra_q.weight.grad is not None
    assert attn.inter_q.weight.grad is not None


def test_attention_fusion_controller() -> None:
    """Verify AttentionFusionController executes all 3 branches and normalizes gate weights."""
    fusion = AttentionFusionController(d_model=64, num_heads=4, window_size=8, chunk_size=4)
    x = torch.randn(2, 12, 64, requires_grad=True)

    out, gate_weights = fusion(x)
    assert out.shape == (2, 12, 64)
    assert gate_weights.shape == (2, 12, 3)

    # Verify that gate weights across the 3 branches sum to 1.0 per token
    gate_sum = gate_weights.sum(dim=-1)
    assert torch.allclose(gate_sum, torch.ones_like(gate_sum), atol=1e-5)

    # Verify gradient flows back to all three branches
    loss = out.sum()
    loss.backward()
    assert x.grad is not None
    assert fusion.global_branch.q_proj.weight.grad is not None
    assert fusion.sparse_branch.q_proj.weight.grad is not None
    assert fusion.hierarchical_branch.intra_q.weight.grad is not None
    assert fusion.gate_proj.weight.grad is not None
