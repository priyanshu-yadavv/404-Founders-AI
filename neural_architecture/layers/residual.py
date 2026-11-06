"""
404 FOUNDERS — Residual Connection Layers
Implements pre-normalized residual connections with learnable LayerScale coefficients.
"""

from typing import Callable, Optional
import torch
import torch.nn as nn

from neural_architecture.layers.normalization import CustomRMSNorm


class ResidualConnection(nn.Module):
    """
    Pre-Normalized Residual Connection wrapper.
    Executes:
        output = x + layer_scale * SubLayer(RMSNorm(x))
    
    Using pre-normalization guarantees that gradients flow cleanly across
    arbitrary layer depths without vanishing or exploding.
    """

    def __init__(
        self,
        dim: int,
        use_layer_scale: bool = True,
        initial_scale: float = 1.0,
        dropout: float = 0.0,
    ) -> None:
        super().__init__()
        self.dim = dim
        self.norm = CustomRMSNorm(dim)
        self.dropout = nn.Dropout(dropout) if dropout > 0.0 else nn.Identity()

        if use_layer_scale:
            self.scale = nn.Parameter(torch.full((dim,), initial_scale))
        else:
            self.register_parameter("scale", None)

    def forward(self, x: torch.Tensor, sublayer: Callable[[torch.Tensor], torch.Tensor]) -> torch.Tensor:
        """
        Execute pre-norm residual step.
        Args:
            x: Input tensor (*, dim)
            sublayer: Callable submodule (e.g. Attention or FeedForward)
        Returns:
            Residual output (*, dim)
        """
        normed = self.norm(x)
        sub_out = sublayer(normed)
        if self.scale is not None:
            sub_out = sub_out * self.scale
        return x + self.dropout(sub_out)
