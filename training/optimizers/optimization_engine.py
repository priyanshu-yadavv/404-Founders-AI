"""
404 FOUNDERS — Optimization Engine
Implements decoupled AdamW optimization with selective weight decay grouping,
gradient clipping, and gradient accumulation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import torch
import torch.nn as nn
from torch.optim import AdamW

from core.intelligence.neural_core import NeuralCore
from training.configs.model_config import PretrainingConfig


class OptimizationEngine:
    """
    Manages optimizer lifecycle, parameter decay partitioning,
    gradient clipping, and gradient accumulation state.
    """

    def __init__(self, model: NeuralCore, config: PretrainingConfig) -> None:
        self.model = model
        self.config = config
        self.optimizer = self._build_optimizer()
        self.accumulation_counter = 0

    def _build_optimizer(self) -> AdamW:
        """
        Group model parameters into decayed (2D matrix weights) and
        non-decayed (1D biases, LayerScale, RMSNorm weights).
        """
        decay_params: List[nn.Parameter] = []
        no_decay_params: List[nn.Parameter] = []

        for name, param in self.model.named_parameters():
            if not param.requires_grad:
                continue

            # Exclude 1D tensors (biases, RMSNorm weights, LayerScale) from weight decay
            if param.dim() >= 2:
                decay_params.append(param)
            else:
                no_decay_params.append(param)

        optim_groups = [
            {"params": decay_params, "weight_decay": self.config.weight_decay},
            {"params": no_decay_params, "weight_decay": 0.0},
        ]

        optimizer = AdamW(
            optim_groups,
            lr=self.config.learning_rate,
            betas=(self.config.beta1, self.config.beta2),
            eps=self.config.eps,
        )
        return optimizer

    def zero_grad(self) -> None:
        """Clear parameter gradients."""
        self.optimizer.zero_grad(set_to_none=True)

    def backward_and_accumulate(self, loss: torch.Tensor) -> bool:
        """
        Compute backward gradients scaled by accumulation steps.
        Returns:
            True if gradient accumulation is complete and optimizer should step,
            False if still accumulating.
        """
        scaled_loss = loss / float(self.config.gradient_accumulation_steps)
        scaled_loss.backward()

        self.accumulation_counter += 1
        if self.accumulation_counter >= self.config.gradient_accumulation_steps:
            self.accumulation_counter = 0
            return True
        return False

    def step(self) -> float:
        """
        Clip gradients and step optimizer.
        Returns:
            Computed total gradient norm.
        """
        grad_norm = float(
            torch.nn.utils.clip_grad_norm_(
                self.model.parameters(),
                max_norm=self.config.max_grad_norm,
            ).item()
        )
        self.optimizer.step()
        self.zero_grad()
        return grad_norm

    def get_lr(self) -> float:
        """Return primary parameter group learning rate."""
        return float(self.optimizer.param_groups[0]["lr"])

    def state_dict(self) -> Dict[str, Any]:
        """Serialize optimizer state."""
        return self.optimizer.state_dict()

    def load_state_dict(self, state_dict: Dict[str, Any]) -> None:
        """Restore optimizer state."""
        self.optimizer.load_state_dict(state_dict)
