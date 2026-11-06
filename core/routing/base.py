"""
404 FOUNDERS — Neural Routing Base Interfaces
Defines abstract contracts for rule-based, learned, and dynamic routing mechanisms.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import torch


@dataclass
class RoutingDecision:
    """Encapsulates the decision made by a neural router."""
    selected_expert_ids: List[int]
    routing_weights: torch.Tensor
    router_type: str
    metadata: Dict[str, Any]


class AbstractRouter(ABC):
    """Abstract interface governing all task and expert routing components."""

    @property
    @abstractmethod
    def num_experts(self) -> int:
        """Total number of available expert pathways."""
        pass

    @abstractmethod
    def route(self, x: torch.Tensor, context_hints: Optional[Dict[str, Any]] = None) -> RoutingDecision:
        """
        Evaluate inputs and determine routing pathway.
        Args:
            x: Input tensor (*, d_model)
            context_hints: Optional contextual metadata (task mode, tags)
        Returns:
            RoutingDecision object
        """
        pass
