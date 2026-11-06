"""
404 FOUNDERS — Training Loss Engine & Objectives
Implements the causal autoregressive next-token prediction objective for foundation model
pretraining, with padding suppression, numerical finiteness checks, and token accuracy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple
import math
import torch
import torch.nn as nn
import torch.nn.functional as F

from core.exceptions import FoundersBaseException


class LossComputationError(FoundersBaseException):
    """Raised when loss evaluation yields non-finite, NaN, or invalid values."""
    pass


@dataclass
class LossOutput:
    """Structured container for loss and auxiliary objective metrics."""
    loss: torch.Tensor
    loss_value: float
    token_accuracy: float
    perplexity: float
    valid_tokens_count: int


class AutoregressiveLossEngine:
    """
    Standard autoregressive next-token prediction objective.
    Calculates CrossEntropyLoss over sequence positions:
        For sequence tokens x_1, x_2, ..., x_T,
        Logits at positions 1 .. T-1 predict tokens at positions 2 .. T.

    Limitation Documented:
        This objective trains the foundational language and symbolic token sequence
        representations. It does not train continuous multimodal encoders or
        vision/audio cross-attention layers, which are introduced in multimodal phases.
    """

    def __init__(self, ignore_index: int = 0, label_smoothing: float = 0.0) -> None:
        self.ignore_index = ignore_index
        self.label_smoothing = label_smoothing

    def compute_loss(
        self,
        logits: torch.Tensor,
        labels: torch.Tensor,
    ) -> LossOutput:
        """
        Compute autoregressive shifted cross-entropy loss.
        Args:
            logits: FloatTensor of shape (batch_size, seq_len, vocab_size)
            labels: LongTensor of shape (batch_size, seq_len)
        Returns:
            LossOutput containing scalar loss tensor, float value, and metrics
        """
        if logits.dim() != 3:
            raise ValueError(f"Expected 3D logits tensor (B, T, V), got {tuple(logits.shape)}")
        if labels.dim() != 2:
            raise ValueError(f"Expected 2D labels tensor (B, T), got {tuple(labels.shape)}")
        if logits.shape[:2] != labels.shape:
            raise ValueError(
                f"Logits shape prefix {logits.shape[:2]} must match labels shape {labels.shape}"
            )

        batch_size, seq_len, vocab_size = logits.shape
        if seq_len < 2:
            raise ValueError(f"Sequence length must be >= 2 for autoregressive prediction, got {seq_len}")

        # Shift logits and labels by 1 position for next-token prediction
        # Logits: predict tokens at t+1 using tokens at 0..t
        shift_logits = logits[:, :-1, :].contiguous()
        shift_labels = labels[:, 1:].contiguous()

        flat_logits = shift_logits.view(-1, vocab_size)
        flat_labels = shift_labels.view(-1)

        loss = F.cross_entropy(
            flat_logits,
            flat_labels,
            ignore_index=self.ignore_index,
            label_smoothing=self.label_smoothing,
        )

        # Numerical sanity check
        if torch.isnan(loss) or torch.isinf(loss):
            raise LossComputationError(
                f"Autoregressive loss produced non-finite value: {loss.item()}"
            )
        if loss.item() < 0.0:
            raise LossComputationError(f"Autoregressive loss produced negative value: {loss.item()}")

        # Calculate token accuracy on valid (non-padding) tokens
        with torch.no_grad():
            preds = flat_logits.argmax(dim=-1)
            valid_mask = flat_labels != self.ignore_index
            valid_tokens = int(valid_mask.sum().item())
            if valid_tokens > 0:
                acc = float((preds[valid_mask] == flat_labels[valid_mask]).float().mean().item())
            else:
                acc = 0.0

            loss_val = float(loss.item())
            ppl = math.exp(min(loss_val, 20.0))  # Cap exponent at 20 to prevent overflow

        return LossOutput(
            loss=loss,
            loss_value=loss_val,
            token_accuracy=acc,
            perplexity=ppl,
            valid_tokens_count=valid_tokens,
        )
