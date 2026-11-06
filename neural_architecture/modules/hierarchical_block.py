"""
404 FOUNDERS — Hierarchical Transformer Block
Integrates RMSNorm, Multi-Mechanism Attention, and Gated SwiGLU / Expert Feedforward.
"""

from typing import Callable, Dict, Optional, Tuple
import torch
import torch.nn as nn

from core.attention.fusion_controller import AttentionFusionController
from core.attention.global_attention import GlobalAttention
from neural_architecture.layers.normalization import CustomRMSNorm
from neural_architecture.layers.projections import FeatureTransformationLayer
from neural_architecture.layers.residual import ResidualConnection


class HierarchicalTransformerBlock(nn.Module):
    """
    Core building block of the 404 FOUNDERS architecture.
    Applies pre-normalized attention and feed-forward operations with residual pathways.
    
    Structure:
        x_1 = x + LayerScale_1 * Attention(RMSNorm(x))
        x_2 = x_1 + LayerScale_2 * SwiGLU(RMSNorm(x_1))
    """

    def __init__(
        self,
        d_model: int,
        num_heads: int = 4,
        use_fusion_attention: bool = True,
        window_size: int = 64,
        chunk_size: int = 16,
        intermediate_dim: Optional[int] = None,
        dropout: float = 0.0,
    ) -> None:
        super().__init__()
        self.d_model = d_model
        self.use_fusion_attention = use_fusion_attention

        # 1. Attention sublayer with pre-norm and LayerScale residual
        if use_fusion_attention:
            self.attention = AttentionFusionController(
                d_model=d_model,
                num_heads=num_heads,
                window_size=window_size,
                chunk_size=chunk_size,
                dropout=dropout,
            )
        else:
            self.attention = GlobalAttention(
                d_model=d_model,
                num_heads=num_heads,
                dropout=dropout,
            )

        self.attn_residual = ResidualConnection(d_model, use_layer_scale=True, dropout=dropout)

        # 2. Feedforward sublayer with pre-norm and LayerScale residual
        self.ffn = FeatureTransformationLayer(d_model=d_model, intermediate_dim=intermediate_dim, dropout=dropout)
        self.ffn_residual = ResidualConnection(d_model, use_layer_scale=True, dropout=dropout)

    @property
    def attn_norm(self) -> CustomRMSNorm:
        return self.attn_residual.norm

    @property
    def ffn_norm(self) -> CustomRMSNorm:
        return self.ffn_residual.norm

    def forward(
        self,
        x: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor]]:
        """
        Forward pass through hierarchical block.
        Args:
            x: Input tensor (*, d_model)
            attention_mask: Optional attention mask
        Returns:
            Tuple of (output tensor, attention weights or gate telemetry)
        """
        attn_meta = None

        def _attn_sublayer(normed_x: torch.Tensor) -> torch.Tensor:
            nonlocal attn_meta
            out, attn_meta = self.attention(normed_x, attention_mask=attention_mask)
            return out

        x = self.attn_residual(x, _attn_sublayer)
        x = self.ffn_residual(x, self.ffn)

        return x, attn_meta
