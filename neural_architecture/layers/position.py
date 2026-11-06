"""
404 FOUNDERS — Rotary Position Embeddings (RoPE)
Implements relative position encoding through 2D complex plane rotations.
"""

from typing import Tuple
import torch
import torch.nn as nn


class RotaryPositionEmbedding(nn.Module):
    """
    Rotary Position Embedding (RoPE).
    Rotates queries and keys in pairwise 2D sub-planes:
        R_theta,m * x = (x_1 * cos(m*theta) - x_2 * sin(m*theta),
                         x_1 * sin(m*theta) + x_2 * cos(m*theta))
    Provides relative position decay and length generalization.
    """

    def __init__(self, dim: int, max_seq_len: int = 4096, base: float = 10000.0) -> None:
        super().__init__()
        if dim % 2 != 0:
            raise ValueError(f"RoPE dimension must be even, got {dim}")
        self.dim = dim
        self.max_seq_len = max_seq_len
        self.base = base

        # Precompute inverted frequencies: 1.0 / (base ^ (2i / dim))
        inv_freq = 1.0 / (base ** (torch.arange(0, dim, 2).float() / dim))
        self.register_buffer("inv_freq", inv_freq, persistent=False)

        # Precompute table
        self._build_cos_sin_tables(max_seq_len)

    def _build_cos_sin_tables(self, seq_len: int) -> None:
        t = torch.arange(seq_len, dtype=torch.float32)
        freqs = torch.outer(t, self.inv_freq)  # (seq_len, dim / 2)
        emb = torch.cat((freqs, freqs), dim=-1)  # (seq_len, dim)
        self.register_buffer("cos_cached", emb.cos(), persistent=False)
        self.register_buffer("sin_cached", emb.sin(), persistent=False)

    def _rotate_half(self, x: torch.Tensor) -> torch.Tensor:
        """Rotate half the hidden dimensions: (-x2, x1)."""
        x1 = x[..., : x.shape[-1] // 2]
        x2 = x[..., x.shape[-1] // 2 :]
        return torch.cat((-x2, x1), dim=-1)

    def forward(self, q: torch.Tensor, k: torch.Tensor, seq_len: int) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Apply RoPE rotations to query and key tensors.
        Args:
            q: Tensor of shape (batch, num_heads, seq_len, head_dim)
            k: Tensor of shape (batch, num_heads, seq_len, head_dim)
            seq_len: Active sequence length
        Returns:
            Tuple of rotated (q, k) tensors
        """
        if seq_len > self.cos_cached.shape[0]:
            self._build_cos_sin_tables(seq_len)

        cos = self.cos_cached[:seq_len, :].unsqueeze(0).unsqueeze(1)  # (1, 1, seq_len, head_dim)
        sin = self.sin_cached[:seq_len, :].unsqueeze(0).unsqueeze(1)

        q_rot = (q * cos) + (self._rotate_half(q) * sin)
        k_rot = (k * cos) + (self._rotate_half(k) * sin)
        return q_rot, k_rot
