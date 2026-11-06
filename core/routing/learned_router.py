"""
404 FOUNDERS — Learned Neural Router (Prototype)
Implements top-k learned gating routing with random parameter initialization.
Note: This router is an experimental architecture prototype with randomly initialized weights;
it has NOT been pretrained.
"""

from typing import Any, Dict, List, Optional, Tuple
import math
import torch
import torch.nn as nn
import torch.nn.functional as F

from core.routing.base import AbstractRouter, RoutingDecision


class LearnedRouter(nn.Module, AbstractRouter):
    """
    Learned Top-k MoE Router.
    Projects hidden representations into expert logit space:
        logits = x @ W_gate
        top_k_indices = TopK(logits, k)
        weights = Softmax(top_k_logits)
        
    Includes auxiliary load balancing loss:
        L_balance = E * sum(f_i * P_i)
    """

    def __init__(
        self,
        d_model: int,
        num_experts: int = 4,
        top_k: int = 2,
        jitter_noise: float = 0.0,
    ) -> None:
        super().__init__()
        self.d_model = d_model
        self._num_experts = num_experts
        self.top_k = min(top_k, num_experts)
        self.jitter_noise = jitter_noise

        self.gate = nn.Linear(d_model, num_experts, bias=False)
        # Random normal initialization with small variance
        nn.init.normal_(self.gate.weight, mean=0.0, std=1.0 / math.sqrt(d_model))

    @property
    def num_experts(self) -> int:
        return self._num_experts

    def forward(
        self,
        x: torch.Tensor,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Compute learned routing weights and indices.
        Args:
            x: Input tensor of shape (batch, seq_len, d_model) or (*, d_model)
        Returns:
            Tuple of:
                top_k_weights: (batch, seq_len, top_k) normalized softmax probabilities
                top_k_indices: (batch, seq_len, top_k) selected expert IDs
                aux_loss: Scalar auxiliary load-balancing loss
        """
        logits = self.gate(x)  # (*, num_experts)

        if self.training and self.jitter_noise > 0.0:
            noise = torch.randn_like(logits) * self.jitter_noise
            logits = logits + noise

        # Softmax probabilities over all experts
        probs = F.softmax(logits, dim=-1)

        # Select Top-K
        top_k_weights, top_k_indices = torch.topk(probs, self.top_k, dim=-1)
        # Re-normalize top-k weights so they sum to 1.0
        top_k_weights = top_k_weights / (top_k_weights.sum(dim=-1, keepdim=True) + 1e-9)

        # Compute auxiliary load-balancing loss across batch and sequence tokens
        flat_probs = probs.view(-1, self._num_experts)
        flat_indices = top_k_indices.view(-1, self.top_k)
        
        tokens_per_expert = torch.zeros(self._num_experts, device=x.device)
        for i in range(self.top_k):
            tokens_per_expert.scatter_add_(0, flat_indices[:, i], torch.ones_like(flat_indices[:, i], dtype=torch.float32))
        
        fraction_tokens = tokens_per_expert / (flat_indices.numel() / self.top_k)
        fraction_prob = flat_probs.mean(dim=0)
        aux_loss = self._num_experts * torch.sum(fraction_tokens * fraction_prob)

        return top_k_weights, top_k_indices, aux_loss

    def route(self, x: torch.Tensor, context_hints: Optional[Dict[str, Any]] = None) -> RoutingDecision:
        """Satisfy AbstractRouter contract for evaluation."""
        self.eval()
        with torch.no_grad():
            # Pool token dimension for sequence-level decision if 3D
            if x.dim() == 3:
                x_pooled = x.mean(dim=1)
            else:
                x_pooled = x
            weights, indices, _ = self.forward(x_pooled)
            selected_ids = indices[0].tolist() if indices.dim() >= 2 else indices.tolist()
            if isinstance(selected_ids, int):
                selected_ids = [selected_ids]

            return RoutingDecision(
                selected_expert_ids=selected_ids,
                routing_weights=weights[0] if weights.dim() >= 2 else weights,
                router_type="learned_top_k",
                metadata={"top_k": self.top_k, "is_trained": False},
            )
