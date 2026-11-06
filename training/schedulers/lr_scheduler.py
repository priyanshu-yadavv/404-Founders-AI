"""
404 FOUNDERS — Learning Rate Schedulers
Implements linear warmup with cosine decay scheduling for stable pretraining dynamics.
"""

from __future__ import annotations

from typing import Any, Dict, List
import math
import torch
from torch.optim import Optimizer


class CosineWarmupScheduler:
    """
    Learning rate schedule with linear warmup followed by cosine annealing decay.
    
    Equations:
        Warmup (t <= warmup_steps):
            lr(t) = min_lr + (max_lr - min_lr) * (t / warmup_steps)
            
        Cosine Decay (warmup_steps < t <= max_steps):
            progress = (t - warmup_steps) / (max_steps - warmup_steps)
            lr(t) = min_lr + 0.5 * (max_lr - min_lr) * (1 + cos(pi * progress))
            
        Post-Decay (t > max_steps):
            lr(t) = min_lr
    """

    def __init__(
        self,
        optimizer: Optimizer,
        warmup_steps: int,
        max_steps: int,
        min_lr: float = 0.0,
        initial_step: int = 0,
    ) -> None:
        self.optimizer = optimizer
        self.warmup_steps = max(0, warmup_steps)
        self.max_steps = max(1, max_steps)
        self.min_lr = min_lr
        self.current_step = initial_step

        # Capture base learning rates for each parameter group
        self.base_lrs: List[float] = [group["lr"] for group in optimizer.param_groups]
        self._update_optimizer_lrs()

    def get_current_lrs(self) -> List[float]:
        """Compute the learning rate for each param group at the current step."""
        t = self.current_step
        lrs = []

        for max_lr in self.base_lrs:
            if self.warmup_steps > 0 and t < self.warmup_steps:
                # Linear warmup: step from 1/warmup to 1.0
                ratio = float(t + 1) / float(self.warmup_steps)
                lr = self.min_lr + (max_lr - self.min_lr) * ratio
            elif t >= self.max_steps:
                # Floor at min_lr
                lr = self.min_lr
            else:
                # Cosine annealing
                decay_steps = self.max_steps - self.warmup_steps
                progress = float(t - self.warmup_steps) / float(decay_steps) if decay_steps > 0 else 1.0
                cosine_coeff = 0.5 * (1.0 + math.cos(math.pi * progress))
                lr = self.min_lr + (max_lr - self.min_lr) * cosine_coeff

            lrs.append(lr)

        return lrs

    def step(self) -> None:
        """Advance schedule by one step and update optimizer parameter groups."""
        self.current_step += 1
        self._update_optimizer_lrs()

    def _update_optimizer_lrs(self) -> None:
        """Apply computed learning rates to optimizer param groups."""
        new_lrs = self.get_current_lrs()
        for group, lr in zip(self.optimizer.param_groups, new_lrs):
            group["lr"] = lr

    def get_last_lr(self) -> List[float]:
        """Return list of current learning rates."""
        return [group["lr"] for group in self.optimizer.param_groups]

    def state_dict(self) -> Dict[str, Any]:
        """Serialize scheduler state."""
        return {
            "current_step": self.current_step,
            "warmup_steps": self.warmup_steps,
            "max_steps": self.max_steps,
            "min_lr": self.min_lr,
            "base_lrs": self.base_lrs,
        }

    def load_state_dict(self, state_dict: Dict[str, Any]) -> None:
        """Restore scheduler state."""
        self.current_step = state_dict.get("current_step", 0)
        self.warmup_steps = state_dict.get("warmup_steps", self.warmup_steps)
        self.max_steps = state_dict.get("max_steps", self.max_steps)
        self.min_lr = state_dict.get("min_lr", self.min_lr)
        self.base_lrs = state_dict.get("base_lrs", self.base_lrs)
        self._update_optimizer_lrs()
