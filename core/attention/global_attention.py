"""
404 FOUNDERS — Global Multi-Head Attention
Implements numerically stable scaled dot-product attention with mask support.
Complexity: O(N^2 * d)
"""

from typing import Optional, Tuple
import math
import torch
import torch.nn as nn
import torch.nn.functional as F

from core.exceptions import ShapeMismatchError


class GlobalAttention(nn.Module):
    """
    Standard full-rank Global Multi-Head Attention.
    Computes dense pairwise token affinities across the entire sequence.
    
    Formula:
        Attention(Q, K, V) = Softmax((Q @ K^T) / sqrt(d_k) + Mask) @ V
    
    Computational Complexity:
        Time: O(B * H * N^2 * d_k)
        Space: O(B * H * N^2) for attention matrix
    """

    def __init__(
        self,
        d_model: int,
        num_heads: int = 8,
        dropout: float = 0.0,
        bias: bool = False,
    ) -> None:
        super().__init__()
        if d_model % num_heads != 0:
            raise ValueError(f"d_model ({d_model}) must be divisible by num_heads ({num_heads})")

        self.d_model = d_model
        self.num_heads = num_heads
        self.head_dim = d_model // num_heads
        self.scale = 1.0 / math.sqrt(self.head_dim)

        # Projections
        self.q_proj = nn.Linear(d_model, d_model, bias=bias)
        self.k_proj = nn.Linear(d_model, d_model, bias=bias)
        self.v_proj = nn.Linear(d_model, d_model, bias=bias)
        self.out_proj = nn.Linear(d_model, d_model, bias=bias)

        self.dropout = nn.Dropout(dropout) if dropout > 0.0 else nn.Identity()

        # Random parameter initialization
        std = 1.0 / math.sqrt(d_model)
        for proj in (self.q_proj, self.k_proj, self.v_proj, self.out_proj):
            nn.init.normal_(proj.weight, mean=0.0, std=std)

    def forward(
        self,
        x: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Execute global multi-head attention.
        Args:
            x: Input tensor of shape (batch, seq_len, d_model)
            attention_mask: Optional mask of shape (batch, 1, seq_len, seq_len) or broadcastable.
                            Positions with value -inf or True (if bool) are masked out.
        Returns:
            Tuple of (output tensor of shape (batch, seq_len, d_model), attention weights)
        """
        batch_size, seq_len, d_model = x.shape
        if d_model != self.d_model:
            raise ShapeMismatchError(f"Expected input d_model {self.d_model}, got {d_model}")

        # Linear projections & split into heads: (batch, num_heads, seq_len, head_dim)
        q = self.q_proj(x).view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(x).view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(x).view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)

        # Scaled dot product scores: (batch, num_heads, seq_len, seq_len)
        scores = torch.matmul(q, k.transpose(-2, -1)) * self.scale

        if attention_mask is not None:
            if attention_mask.dtype == torch.bool:
                scores = scores.masked_fill(attention_mask, -1e9)
            else:
                scores = scores + attention_mask

        # Numerically stable softmax
        attn_weights = F.softmax(scores, dim=-1)
        attn_weights_drop = self.dropout(attn_weights)

        # Context aggregation
        context = torch.matmul(attn_weights_drop, v)  # (batch, num_heads, seq_len, head_dim)

        # Concatenate heads and project out
        context = context.transpose(1, 2).contiguous().view(batch_size, seq_len, d_model)
        output = self.out_proj(context)

        return output, attn_weights
