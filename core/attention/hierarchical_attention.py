"""
404 FOUNDERS — Hierarchical Multi-Head Attention
Decomposes long sequences into hierarchical micro (intra-chunk) and macro (inter-chunk) stages.
Complexity: O(N * C + (N/C)^2 * d)
"""

from typing import Optional, Tuple
import math
import torch
import torch.nn as nn
import torch.nn.functional as F

from core.exceptions import ShapeMismatchError


class HierarchicalAttention(nn.Module):
    """
    Hierarchical Two-Tier Attention.
    Segments sequence of length N into non-overlapping chunks of size C.
    Tier 1 (Intra-Chunk): Detailed token-to-token attention within each local chunk.
    Tier 2 (Inter-Chunk): Coarse summary-to-summary attention across all chunks.
    Tier 3 (Fusion): Interpolates coarse macro-context back into fine micro-tokens.
    """

    def __init__(
        self,
        d_model: int,
        num_heads: int = 4,
        chunk_size: int = 16,
        dropout: float = 0.0,
        bias: bool = False,
    ) -> None:
        super().__init__()
        if d_model % num_heads != 0:
            raise ValueError(f"d_model ({d_model}) must be divisible by num_heads ({num_heads})")
        if chunk_size <= 0:
            raise ValueError(f"chunk_size must be positive, got {chunk_size}")

        self.d_model = d_model
        self.num_heads = num_heads
        self.head_dim = d_model // num_heads
        self.chunk_size = chunk_size
        self.scale = 1.0 / math.sqrt(self.head_dim)

        # Intra-chunk projection
        self.intra_q = nn.Linear(d_model, d_model, bias=bias)
        self.intra_k = nn.Linear(d_model, d_model, bias=bias)
        self.intra_v = nn.Linear(d_model, d_model, bias=bias)

        # Inter-chunk summary projection
        self.inter_q = nn.Linear(d_model, d_model, bias=bias)
        self.inter_k = nn.Linear(d_model, d_model, bias=bias)
        self.inter_v = nn.Linear(d_model, d_model, bias=bias)

        # Merge & Output
        self.merge_gate = nn.Linear(d_model * 2, d_model, bias=True)
        self.out_proj = nn.Linear(d_model, d_model, bias=bias)
        self.dropout = nn.Dropout(dropout) if dropout > 0.0 else nn.Identity()

        std = 1.0 / math.sqrt(d_model)
        for p in (self.intra_q, self.intra_k, self.intra_v, self.inter_q, self.inter_k, self.inter_v, self.out_proj):
            nn.init.normal_(p.weight, mean=0.0, std=std)

    def forward(
        self,
        x: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Execute hierarchical attention.
        Args:
            x: Input tensor of shape (batch, seq_len, d_model)
            attention_mask: Optional mask
        Returns:
            Tuple of (output tensor, intra_attn_weights)
        """
        batch_size, seq_len, d_model = x.shape
        if d_model != self.d_model:
            raise ShapeMismatchError(f"Expected d_model {self.d_model}, got {d_model}")

        # Pad sequence to multiple of chunk_size if necessary
        pad_len = (self.chunk_size - (seq_len % self.chunk_size)) % self.chunk_size
        if pad_len > 0:
            x_padded = F.pad(x, (0, 0, 0, pad_len))
        else:
            x_padded = x

        padded_len = x_padded.shape[1]
        num_chunks = padded_len // self.chunk_size

        # Reshape into chunks: (batch * num_chunks, chunk_size, d_model)
        x_chunks = x_padded.view(batch_size * num_chunks, self.chunk_size, d_model)

        # 1. Intra-chunk attention
        q_intra = self.intra_q(x_chunks).view(batch_size * num_chunks, self.chunk_size, self.num_heads, self.head_dim).transpose(1, 2)
        k_intra = self.intra_k(x_chunks).view(batch_size * num_chunks, self.chunk_size, self.num_heads, self.head_dim).transpose(1, 2)
        v_intra = self.intra_v(x_chunks).view(batch_size * num_chunks, self.chunk_size, self.num_heads, self.head_dim).transpose(1, 2)

        scores_intra = torch.matmul(q_intra, k_intra.transpose(-2, -1)) * self.scale
        attn_intra = F.softmax(scores_intra, dim=-1)
        out_intra = torch.matmul(self.dropout(attn_intra), v_intra)
        out_intra = out_intra.transpose(1, 2).contiguous().view(batch_size, padded_len, d_model)

        # 2. Inter-chunk macro attention using mean chunk representations
        chunk_summaries = x_padded.view(batch_size, num_chunks, self.chunk_size, d_model).mean(dim=2)  # (batch, num_chunks, d_model)
        q_inter = self.inter_q(chunk_summaries).view(batch_size, num_chunks, self.num_heads, self.head_dim).transpose(1, 2)
        k_inter = self.inter_k(chunk_summaries).view(batch_size, num_chunks, self.num_heads, self.head_dim).transpose(1, 2)
        v_inter = self.inter_v(chunk_summaries).view(batch_size, num_chunks, self.num_heads, self.head_dim).transpose(1, 2)

        scores_inter = torch.matmul(q_inter, k_inter.transpose(-2, -1)) * self.scale
        attn_inter = F.softmax(scores_inter, dim=-1)
        out_inter = torch.matmul(self.dropout(attn_inter), v_inter)
        out_inter = out_inter.transpose(1, 2).contiguous().view(batch_size, num_chunks, d_model)

        # Expand macro context back to token level: (batch, num_chunks, chunk_size, d_model) -> (batch, padded_len, d_model)
        out_inter_expanded = out_inter.unsqueeze(2).repeat(1, 1, self.chunk_size, 1).view(batch_size, padded_len, d_model)

        # 3. Fuse micro and macro contexts with learned gating
        combined = torch.cat([out_intra, out_inter_expanded], dim=-1)
        gate = torch.sigmoid(self.merge_gate(combined))
        fused = (gate * out_intra) + ((1.0 - gate) * out_inter_expanded)

        # Unpad
        fused = fused[:, :seq_len, :]
        output = self.out_proj(fused)

        return output, attn_intra
