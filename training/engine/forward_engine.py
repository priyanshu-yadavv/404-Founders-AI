"""
404 FOUNDERS — Forward Computation Engine
Executes model forward inference with causal autoregressive attention masks,
dimension assertions, and device/precision context management.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple
import torch

from core.intelligence.neural_core import NeuralCore
from neural_architecture.interfaces import ModelOutput
from training.engine.device_manager import DeviceManager


class ForwardEngine:
    """
    Coordinates causal autoregressive forward passes through NeuralCore.
    """

    def __init__(self, model: NeuralCore, device_manager: DeviceManager) -> None:
        self.model = model
        self.device_manager = device_manager

    @staticmethod
    def create_causal_mask(seq_len: int, device: torch.device) -> torch.Tensor:
        """
        Construct upper-triangular boolean causal mask:
        Positions where column > row (future tokens) are set to True,
        instructing attention modules to mask out future context.
        Shape: (1, 1, seq_len, seq_len)
        """
        # Upper triangle without diagonal is True
        mask = torch.triu(torch.ones(seq_len, seq_len, dtype=torch.bool, device=device), diagonal=1)
        return mask.unsqueeze(0).unsqueeze(0)

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
        context_hints: Optional[Dict[str, Any]] = None,
        is_causal: bool = True,
    ) -> torch.Tensor:
        """
        Execute forward pass and return output logits.
        Args:
            input_ids: LongTensor of shape (batch, seq_len)
            attention_mask: Optional user-supplied mask
            context_hints: Optional metadata hints (e.g. {'operating_mode': 'general'})
            is_causal: Whether to apply autoregressive causal upper-triangular mask
        Returns:
            Logits FloatTensor of shape (batch, seq_len, vocab_size)
        """
        input_ids = self.device_manager.to_device(input_ids)
        batch_size, seq_len = input_ids.shape

        # Construct or combine causal mask if required
        active_mask = None
        if is_causal:
            active_mask = self.create_causal_mask(seq_len, self.device_manager.device)

        with self.device_manager.autocast_context():
            output: ModelOutput = self.model(
                input_ids=input_ids,
                attention_mask=active_mask,
                context_hints=context_hints,
                return_hidden_states=False,
            )

        logits = output.logits
        if logits.dim() != 3 or logits.shape[:2] != (batch_size, seq_len):
            raise ValueError(
                f"Unexpected forward logits shape: {tuple(logits.shape)}, expected ({batch_size}, {seq_len}, V)"
            )

        return logits
