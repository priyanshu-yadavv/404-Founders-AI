"""
404 FOUNDERS — Hybrid Dynamic Router
Dynamically chooses between deterministic rule-based policies and learned neural gating.
"""

from typing import Any, Dict, Optional
import torch

from core.routing.base import AbstractRouter, RoutingDecision
from core.routing.learned_router import LearnedRouter
from core.routing.rule_based import RuleBasedRouter


class DynamicRouter(AbstractRouter):
    """
    Hybrid Dynamic Router.
    Evaluates policy priority:
    1. If strict system override or explicit task hints exist, enforces rule-based routing.
    2. Otherwise, passes through to learned neural routing.
    """

    def __init__(self, d_model: int, num_experts: int = 4, top_k: int = 2) -> None:
        self.rule_router = RuleBasedRouter(num_experts=num_experts)
        self.learned_router = LearnedRouter(d_model=d_model, num_experts=num_experts, top_k=top_k)
        self._num_experts = num_experts

    @property
    def num_experts(self) -> int:
        return self._num_experts

    def route(self, x: torch.Tensor, context_hints: Optional[Dict[str, Any]] = None) -> RoutingDecision:
        hints = context_hints or {}

        # If explicit security tier or forced mode is present, use deterministic rule routing
        if "force_mode" in hints or "security_tier" in hints:
            decision = self.rule_router.route(x, hints)
            decision.metadata["routing_path"] = "rule_override"
            return decision

        # Otherwise use learned neural gating
        decision = self.learned_router.route(x, hints)
        decision.metadata["routing_path"] = "learned_dynamic"
        return decision
