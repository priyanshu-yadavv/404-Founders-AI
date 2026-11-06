"""
404 FOUNDERS — Attention Fusion Controller
Dynamically balances Global, Sparse, and Hierarchical attention mechanisms.
"""

from typing import Dict, Optional, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F

from core.attention.global_attention import GlobalAttention
from core.attention.sparse_attention import SparseAttention
from core.attention.hierarchical_attention import HierarchicalAttention
from core.exceptions import ShapeMismatchError


class AttentionFusionController(nn.Module):
    """
    Hybrid Multi-Mechanism Attention Fusion Controller.
    Computes parallel attention representations across:
        1. Global Attention (Dense full-sequence affinity)
        2. Sparse Attention (Local sliding-window context)
        3. Hierarchical Attention (Micro/Macro multi-resolution context)
        
    A dynamic gating network computes input-conditioned mixing coefficients:
        alpha = Softmax(Linear(x)) in R^3
        Fused_Output = alpha_0 * Global + alpha_1 * Sparse + alpha_2 * Hierarchical
    """

    def __init__(
        self,
        d_model: int,
        num_heads: int = 4,
        window_size: int = 128,
        chunk_size: int = 16,
        dropout: float = 0.0,
    ) -> None:
        super().__init__()
        self.d_model = d_model

        # Multi-mechanism branches
        self.global_branch = GlobalAttention(d_model=d_model, num_heads=num_heads, dropout=dropout)
        self.sparse_branch = SparseAttention(d_model=d_model, num_heads=num_heads, window_size=window_size, dropout=dropout)
        self.hierarchical_branch = HierarchicalAttention(d_model=d_model, num_heads=num_heads, chunk_size=chunk_size, dropout=dropout)

        # Dynamic gating projection (produces 3 logits corresponding to the 3 branches)
        self.gate_proj = nn.Linear(d_model, 3, bias=True)
        nn.init.zeros_(self.gate_proj.weight)
        # Initialize biases equally to start with uniform 1/3 prior
        nn.init.zeros_(self.gate_proj.bias)

        self.out_proj = nn.Linear(d_model, d_model, bias=False)
        self.dropout = nn.Dropout(dropout) if dropout > 0.0 else nn.Identity()

    def forward(
        self,
        x: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Execute multi-mechanism attention fusion.
        Args:
            x: Input tensor of shape (batch, seq_len, d_model)
            attention_mask: Optional attention mask
        Returns:
            Tuple of (fused output tensor, gating weights of shape (batch, seq_len, 3))
        """
        if x.shape[-1] != self.d_model:
            raise ShapeMismatchError(f"Expected d_model {self.d_model}, got {x.shape[-1]}")

        # Compute branch outputs
        out_global, _ = self.global_branch(x, attention_mask=attention_mask)
        out_sparse, _ = self.sparse_branch(x, attention_mask=attention_mask)
        out_hier, _ = self.hierarchical_branch(x, attention_mask=attention_mask)

        # Compute dynamic gating weights: (batch, seq_len, 3)
        gate_logits = self.gate_proj(x)
        gate_weights = F.softmax(gate_logits, dim=-1)

        # Weighted combination across branches
        alpha_global = gate_weights[..., 0:1]
        alpha_sparse = gate_weights[..., 1:2]
        alpha_hier = gate_weights[..., 2:3]

        fused = (
            (alpha_global * out_global)
            + (alpha_sparse * out_sparse)
            + (alpha_hier * out_hier)
        )

        output = self.out_proj(self.dropout(fused))
        return output, gate_weights
