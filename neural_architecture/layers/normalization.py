"""
404 FOUNDERS — Custom Normalization Layers
Implements Root Mean Square Normalization (RMSNorm) with numerical stability controls.
"""

from typing import Tuple
import torch
import torch.nn as nn

from core.exceptions import ShapeMismatchError


class CustomRMSNorm(nn.Module):
    """
    Root Mean Square Layer Normalization (RMSNorm).
    Replaces standard LayerNorm by normalizing inputs based on the root mean square
    statistic rather than calculating both mean and variance, reducing compute overhead
    while preserving training stability.
    
    Formula:
        y = (x / sqrt(mean(x^2, dim=-1, keepdim=True) + eps)) * weight
    """

    def __init__(self, dim: int, eps: float = 1e-6) -> None:
        super().__init__()
        if dim <= 0:
            raise ValueError(f"Normalized dimension must be positive, got {dim}")
        self.dim = dim
        self.eps = eps
        # Learnable gain parameter initialized to 1.0
        self.weight = nn.Parameter(torch.ones(dim))

    def _norm(self, x: torch.Tensor) -> torch.Tensor:
        """Compute the RMS scaling factor."""
        # Mean square along the hidden feature dimension
        rms = torch.rsqrt(x.pow(2).mean(dim=-1, keepdim=True) + self.eps)
        return x * rms

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward normalization pass.
        Args:
            x: Input tensor of shape (batch_size, seq_len, dim) or (*, dim)
        Returns:
            Normalized tensor of the same shape as x
        """
        if x.shape[-1] != self.dim:
            raise ShapeMismatchError(
                f"Expected final dimension {self.dim}, but got {x.shape[-1]} in shape {tuple(x.shape)}"
            )
        output = self._norm(x.float()).type_as(x)
        return output * self.weight

    def extra_repr(self) -> str:
        return f"dim={self.dim}, eps={self.eps}"
