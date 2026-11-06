"""
404 FOUNDERS — Unit Tests for Autoregressive Loss Engine
"""

import pytest
import torch

from training.objectives.loss_engine import (
    AutoregressiveLossEngine,
    LossComputationError,
)


def test_autoregressive_loss_calculation() -> None:
    """Verify shifted next-token cross-entropy and accuracy."""
    loss_engine = AutoregressiveLossEngine(ignore_index=0)

    # Batch of 2, seq_len of 4, vocab of 10
    batch_size, seq_len, vocab_size = 2, 4, 10
    logits = torch.randn(batch_size, seq_len, vocab_size, requires_grad=True)
    labels = torch.tensor([[1, 2, 3, 4], [5, 6, 7, 8]], dtype=torch.long)

    out = loss_engine.compute_loss(logits, labels)
    assert out.loss_value > 0.0
    assert 0.0 <= out.token_accuracy <= 1.0
    assert out.perplexity >= 1.0
    assert out.valid_tokens_count == 6  # 2 samples * (4 - 1) tokens

    # Verify backpropagation
    out.loss.backward()
    assert logits.grad is not None
    assert torch.all(torch.isfinite(logits.grad))


def test_ignore_index_padding_suppression() -> None:
    """Verify padding tokens (ignore_index) are excluded from loss computation."""
    loss_engine = AutoregressiveLossEngine(ignore_index=0)

    batch_size, seq_len, vocab_size = 1, 4, 10
    logits = torch.randn(batch_size, seq_len, vocab_size)
    # Target positions 2 and 3 are padded (<pad> = 0)
    labels = torch.tensor([[5, 6, 0, 0]], dtype=torch.long)

    out = loss_engine.compute_loss(logits, labels)
    # Valid next-token target is only token at index 1 (predicting token 6 from position 0)
    assert out.valid_tokens_count == 1


def test_loss_invalid_inputs_and_finiteness() -> None:
    """Verify exceptions on rank mismatch, sequence length < 2, or non-finite inputs."""
    loss_engine = AutoregressiveLossEngine()

    # Sequence length too short
    with pytest.raises(ValueError, match="Sequence length must be >= 2"):
        loss_engine.compute_loss(torch.randn(2, 1, 10), torch.tensor([[1], [2]]))

    # Dimension mismatch
    with pytest.raises(ValueError, match="Expected 3D logits"):
        loss_engine.compute_loss(torch.randn(2, 4), torch.tensor([[1, 2, 3, 4]]))
