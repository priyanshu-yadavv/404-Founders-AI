"""
404 FOUNDERS — Unit Tests for Neural Routing Mechanisms
"""

import torch

from core.routing.dynamic_router import DynamicRouter
from core.routing.learned_router import LearnedRouter
from core.routing.rule_based import RuleBasedRouter


def test_rule_based_router_decisions() -> None:
    """Verify RuleBasedRouter deterministic expert selections."""
    router = RuleBasedRouter(num_experts=4)
    dummy_x = torch.zeros(1, 64)

    # 1. Default general mode
    dec_gen = router.route(dummy_x, context_hints={"operating_mode": "general"})
    assert dec_gen.selected_expert_ids == [0]
    assert dec_gen.routing_weights[0].item() == 1.0

    # 2. Personal AI mode
    dec_pers = router.route(dummy_x, context_hints={"operating_mode": "personal"})
    assert dec_pers.selected_expert_ids == [1]

    # 3. Code assistance task tag
    dec_code = router.route(dummy_x, context_hints={"task_tag": "code_refactor"})
    assert dec_code.selected_expert_ids == [2]


def test_learned_router_top_k_and_aux_loss() -> None:
    """Verify LearnedRouter top-k selection, re-normalization, and auxiliary loss."""
    router = LearnedRouter(d_model=64, num_experts=4, top_k=2)
    x = torch.randn(2, 8, 64, requires_grad=True)

    weights, indices, aux_loss = router(x)

    assert weights.shape == (2, 8, 2)
    assert indices.shape == (2, 8, 2)
    assert aux_loss.item() >= 0.0

    # Verify top-k weights sum to 1.0
    weight_sum = weights.sum(dim=-1)
    assert torch.allclose(weight_sum, torch.ones_like(weight_sum), atol=1e-5)

    # Verify gradient flow
    loss = weights.sum() + aux_loss
    loss.backward()
    assert x.grad is not None
    assert router.gate.weight.grad is not None


def test_dynamic_router_dispatch() -> None:
    """Verify DynamicRouter routes via rule when hints exist and falls back to learned."""
    router = DynamicRouter(d_model=64, num_experts=4, top_k=2)
    dummy_x = torch.randn(1, 8, 64)

    # 1. Forced mode policy triggers rule path
    dec_rule = router.route(dummy_x, context_hints={"force_mode": True, "operating_mode": "personal"})
    assert dec_rule.router_type == "rule_based"
    assert dec_rule.selected_expert_ids == [1]

    # 2. Unforced input triggers learned dynamic path
    dec_learned = router.route(dummy_x, context_hints={})
    assert dec_learned.router_type == "learned_top_k"
    assert len(dec_learned.selected_expert_ids) == 2
