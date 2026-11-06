"""
404 FOUNDERS — Rule-Based Deterministic Router
Selects expert pathways based on explicit metadata, operating mode tags, and heuristics.
"""

from typing import Any, Dict, List, Optional
import torch

from core.routing.base import AbstractRouter, RoutingDecision


class RuleBasedRouter(AbstractRouter):
    """
    Deterministic rule-based router.
    Evaluates context hints (e.g. 'operating_mode': 'general' vs 'personal', or task tags)
    to select target expert modules.
    
    Default Expert Mapping:
        Expert 0: General Intelligence / Reasoning Expert
        Expert 1: Personal AI / Endpoint Copilot Expert
        Expert 2: Code & AST Analysis Expert
        Expert 3: Multimodal Synthesis Expert
    """

    def __init__(self, num_experts: int = 4) -> None:
        self._num_experts = num_experts

    @property
    def num_experts(self) -> int:
        return self._num_experts

    def route(self, x: torch.Tensor, context_hints: Optional[Dict[str, Any]] = None) -> RoutingDecision:
        hints = context_hints or {}
        mode = str(hints.get("operating_mode", "general")).lower()
        task_tag = str(hints.get("task_tag", "")).lower()

        # Rule evaluation
        if mode == "personal" or "system" in task_tag or "cyber" in task_tag:
            expert_id = 1  # Personal AI expert
        elif "code" in task_tag or "programming" in task_tag:
            expert_id = min(2, self._num_experts - 1)
        elif "vision" in task_tag or "multimodal" in task_tag:
            expert_id = min(3, self._num_experts - 1)
        else:
            expert_id = 0  # General reasoning expert

        # One-hot routing weights
        weights = torch.zeros(self._num_experts, device=x.device, dtype=torch.float32)
        weights[expert_id] = 1.0

        return RoutingDecision(
            selected_expert_ids=[expert_id],
            routing_weights=weights,
            router_type="rule_based",
            metadata={"assigned_mode": mode, "task_tag": task_tag},
        )
