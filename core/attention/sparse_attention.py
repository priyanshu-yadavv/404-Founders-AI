"""
404 FOUNDERS — Sparse Multi-Head Attention
Implements sliding-window banded attention for linear-time context scaling.
Complexity: O(N * W * d) where W << N.
"""

from typing import Optional, Tuple
import math
import torch
import torch.nn as nn
import torch.nn.functional as F

from core.exceptions import ShapeMismatchError


class SparseAttention(nn.Module):
    """
    Sliding-Window Sparse Multi-Head Attention.
    Restricts attention queries to a symmetric local neighborhood window of size W.
    Tokens outside |i - j| <= window_size are masked out.
    
    Formula:
        A_{i,j} = Q_i @ K_j^T / sqrt(d_k)   if |i - j| <= W
                  -inf                      otherwise
                  
    Computational Complexity:
        Time: O(B * H * N * W * d_k)
        Space: O(B * H * N * W)
    """

    def __init__(
        self,
        d_model: int,
        num_heads: int = 8,
        window_size: int = 256,
        dropout: float = 0.0,
        bias: bool = False,
    ) -> None:
        super().__init__()
        if d_model % num_heads != 0:
            raise ValueError(f"d_model ({d_model}) must be divisible by num_heads ({num_heads})")
        if window_size <= 0:
            raise ValueError(f"window_size must be positive, got {window_size}")

        self.d_model = d_model
        self.num_heads = num_heads
        self.head_dim = d_model // num_heads
        self.window_size = window_size
        self.scale = 1.0 / math.sqrt(self.head_dim)

        self.q_proj = nn.Linear(d_model, d_model, bias=bias)
        self.k_proj = nn.Linear(d_model, d_model, bias=bias)
        self.v_proj = nn.Linear(d_model, d_model, bias=bias)
        self.out_proj = nn.Linear(d_model, d_model, bias=bias)

        self.dropout = nn.Dropout(dropout) if dropout > 0.0 else nn.Identity()

        # Random parameter initialization
        std = 1.0 / math.sqrt(d_model)
        for proj in (self.q_proj, self.k_proj, self.v_proj, self.out_proj):
            nn.init.normal_(proj.weight, mean=0.0, std=std)

    def _generate_banded_mask(self, seq_len: int, device: torch.device) -> torch.Tensor:
        """Create boolean mask where True indicates masked out (|i - j| > window_size)."""
        idx = torch.arange(seq_len, device=device)
        # Distance matrix: |i - j|
        dist = torch.abs(idx.unsqueeze(0) - idx.unsqueeze(1))
        # Mask positions exceeding window size
        mask = dist > self.window_size
        return mask.unsqueeze(0).unsqueeze(0)  # (1, 1, seq_len, seq_len)

    def forward(
        self,
        x: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Execute sliding-window sparse attention.
        Args:
            x: Input tensor of shape (batch, seq_len, d_model)
            attention_mask: Optional additional mask (e.g. padding/causal)
        Returns:
            Tuple of (output tensor, attention weights)
        """
        batch_size, seq_len, d_model = x.shape
        if d_model != self.d_model:
            raise ShapeMismatchError(f"Expected input d_model {self.d_model}, got {d_model}")

        q = self.q_proj(x).view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(x).view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(x).view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)

        scores = torch.matmul(q, k.transpose(-2, -1)) * self.scale

        # Apply sliding window banded mask
        sparse_mask = self._generate_banded_mask(seq_len, x.device)
        scores = scores.masked_fill(sparse_mask, -1e9)

        if attention_mask is not None:
            if attention_mask.dtype == torch.bool:
                scores = scores.masked_fill(attention_mask, -1e9)
            else:
                scores = scores + attention_mask

        attn_weights = F.softmax(scores, dim=-1)
        attn_weights_drop = self.dropout(attn_weights)

        context = torch.matmul(attn_weights_drop, v)
        context = context.transpose(1, 2).contiguous().view(batch_size, seq_len, d_model)
        output = self.out_proj(context)

        return output, attn_weights
