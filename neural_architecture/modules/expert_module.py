"""
404 FOUNDERS — Specialized Expert Modules
Implements domain-tailored feed-forward expert pathways.
"""

from typing import Optional
import torch
import torch.nn as nn

from neural_architecture.layers.projections import FeatureTransformationLayer


class SpecializedExpert(nn.Module):
    """
    Base expert module wrapper.
    Encapsulates dedicated SwiGLU feed-forward networks for domain-specific tasks.
    """

    def __init__(self, d_model: int, expert_id: int, expert_name: str, intermediate_dim: Optional[int] = None) -> None:
        super().__init__()
        self.expert_id = expert_id
        self.expert_name = expert_name
        self.d_model = d_model
        self.ffn = FeatureTransformationLayer(d_model=d_model, intermediate_dim=intermediate_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.ffn(x)


class GeneralReasoningExpert(SpecializedExpert):
    """Expert module tuned for symbolic, logical, and natural language reasoning."""

    def __init__(self, d_model: int, expert_id: int = 0) -> None:
        super().__init__(d_model=d_model, expert_id=expert_id, expert_name="general_reasoning")


class PersonalAISystemExpert(SpecializedExpert):
    """Expert module tuned for operating system telemetry, code ASTs, and cybersecurity signals."""

    def __init__(self, d_model: int, expert_id: int = 1) -> None:
        super().__init__(d_model=d_model, expert_id=expert_id, expert_name="personal_ai_system")
