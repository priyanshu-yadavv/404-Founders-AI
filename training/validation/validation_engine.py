"""
404 FOUNDERS — Validation Engine
Evaluates foundation model on held-out validation datasets, computes perplexity,
and monitors generalization without training/validation data leakage.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple
import math
import torch
from torch.utils.data import DataLoader

from core.intelligence.neural_core import NeuralCore
from training.engine.forward_engine import ForwardEngine
from training.objectives.loss_engine import AutoregressiveLossEngine


@dataclass
class ValidationMetrics:
    """Aggregated validation evaluation metrics."""
    val_loss: float
    perplexity: float
    token_accuracy: float
    total_tokens: int
    num_batches: int


class ValidationEngine:
    """
    Executes non-gradient evaluation on validation splits.
    """

    def __init__(
        self,
        forward_engine: ForwardEngine,
        loss_engine: AutoregressiveLossEngine,
    ) -> None:
        self.forward_engine = forward_engine
        self.loss_engine = loss_engine

    def evaluate(
        self,
        val_loader: DataLoader,
        max_batches: Optional[int] = None,
    ) -> ValidationMetrics:
        """
        Evaluate model across validation batches in zero-grad eval mode.
        """
        model = self.forward_engine.model
        was_training = model.training
        model.eval()

        total_loss = 0.0
        total_tokens = 0
        total_correct = 0.0
        batch_count = 0

        with torch.no_grad():
            for i, batch in enumerate(val_loader):
                if max_batches is not None and i >= max_batches:
                    break

                input_ids = batch["input_ids"]
                labels = batch["labels"]

                logits = self.forward_engine.forward(input_ids, is_causal=True)
                loss_out = self.loss_engine.compute_loss(logits, labels)

                batch_tokens = loss_out.valid_tokens_count
                total_loss += loss_out.loss_value * batch_tokens
                total_tokens += batch_tokens
                total_correct += loss_out.token_accuracy * batch_tokens
                batch_count += 1

        if was_training:
            model.train()

        if total_tokens == 0:
            return ValidationMetrics(
                val_loss=0.0,
                perplexity=1.0,
                token_accuracy=0.0,
                total_tokens=0,
                num_batches=0,
            )

        avg_loss = total_loss / float(total_tokens)
        avg_acc = total_correct / float(total_tokens)
        ppl = math.exp(min(avg_loss, 20.0))

        return ValidationMetrics(
            val_loss=round(avg_loss, 5),
            perplexity=round(ppl, 3),
            token_accuracy=round(avg_acc, 4),
            total_tokens=total_tokens,
            num_batches=batch_count,
        )

    @staticmethod
    def detect_overfitting(
        train_loss: float,
        val_loss: float,
        threshold: float = 1.0,
    ) -> Tuple[bool, float]:
        """
        Compute divergence between training and validation loss.
        Returns (is_overfitting, gap).
        """
        gap = val_loss - train_loss
        is_overfit = gap > threshold
        return is_overfit, gap
