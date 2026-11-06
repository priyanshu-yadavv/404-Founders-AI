"""
404 FOUNDERS — Hierarchical Transformer Block
Integrates RMSNorm, Multi-Mechanism Attention, and Gated SwiGLU / Expert Feedforward.
"""

from typing import Dict, Optional, Tuple
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

        # 1. Attention sublayer
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

        self.attn_norm = CustomRMSNorm(d_model)
        self.attn_residual = ResidualConnection(d_model, use_layer_scale=True, dropout=dropout)

        # 2. Feedforward sublayer
        self.ffn = FeatureTransformationLayer(d_model=d_model, intermediate_dim=intermediate_dim, dropout=dropout)
        self.ffn_norm = CustomRMSNorm(d_model)
        self.ffn_residual = ResidualConnection(d_model, use_layer_scale=True, dropout=dropout)

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
        # Attention sublayer with pre-norm
        attn_out, attn_meta = self.attention(self.attn_norm(x), attention_mask=attention_mask)
        x = x + attn_out

        # Feedforward sublayer with pre-norm
        ffn_out = self.ffn(self.ffn_norm(x))
        x = x + ffn_out

        return x, attn_meta
