"""
404 FOUNDERS — Central Neural Core Engine
Coordinates input ingestion, hierarchical transformer blocks, dynamic routing,
intermediate representation caching, and output prediction.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import torch
import torch.nn as nn

from core.exceptions import ArchitectureError, ShapeMismatchError
from core.routing.dynamic_router import DynamicRouter
from neural_architecture.interfaces import BackendType, ModelOutput, NeuralModuleInterface
from neural_architecture.layers.normalization import CustomRMSNorm
from neural_architecture.layers.projections import InputProjectionLayer, OutputProjectionLayer
from neural_architecture.modules.expert_module import GeneralReasoningExpert, PersonalAISystemExpert
from neural_architecture.modules.hierarchical_block import HierarchicalTransformerBlock


@dataclass
class NeuralCoreConfig:
    """Configurable hyperparameters for the experimental neural core."""
    d_model: int = 128
    n_layers: int = 2
    n_heads: int = 4
    vocab_size: int = 1024
    max_seq_len: int = 512
    use_fusion_attention: bool = True
    window_size: int = 64
    chunk_size: int = 16
    intermediate_dim: Optional[int] = None
    dropout: float = 0.0
    random_seed: Optional[int] = 404
    num_experts: int = 2


class NeuralCore(nn.Module, NeuralModuleInterface):
    """
    Central neural processing engine for 404 FOUNDERS.
    Coordinates:
    - Input token/continuous vector projection
    - Hierarchical Transformer blocks with intermediate state logging
    - Dynamic routing between specialized experts
    - Output projection to prediction logits
    - Reproducible random parameter initialization
    """

    def __init__(self, config: Optional[NeuralCoreConfig] = None) -> None:
        super().__init__()
        self.config = config or NeuralCoreConfig()
        cfg = self.config

        # Enforce deterministic random initialization if seed provided
        if cfg.random_seed is not None:
            torch.manual_seed(cfg.random_seed)

        # 1. Input Processing
        self.input_projection = InputProjectionLayer(
            d_model=cfg.d_model,
            vocab_size=cfg.vocab_size,
            dropout=cfg.dropout,
        )

        # 2. Hierarchical Transformer Stack
        self.layers = nn.ModuleList([
            HierarchicalTransformerBlock(
                d_model=cfg.d_model,
                num_heads=cfg.n_heads,
                use_fusion_attention=cfg.use_fusion_attention,
                window_size=cfg.window_size,
                chunk_size=cfg.chunk_size,
                intermediate_dim=cfg.intermediate_dim,
                dropout=cfg.dropout,
            )
            for _ in range(cfg.n_layers)
        ])

        # 3. Dynamic Router & Specialized Domain Experts
        self.router = DynamicRouter(d_model=cfg.d_model, num_experts=cfg.num_experts)
        self.experts = nn.ModuleList([
            GeneralReasoningExpert(d_model=cfg.d_model, expert_id=0),
            PersonalAISystemExpert(d_model=cfg.d_model, expert_id=1),
        ])

        # 4. Final Normalization & Output Generation Head
        self.final_norm = CustomRMSNorm(cfg.d_model)
        self.output_projection = OutputProjectionLayer(
            d_model=cfg.d_model,
            output_dim=cfg.vocab_size,
        )

    @property
    def backend_type(self) -> BackendType:
        return BackendType.PYTORCH

    @property
    def parameter_count(self) -> int:
        """Calculate total number of trainable parameters dynamically."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
        context_hints: Optional[Dict[str, Any]] = None,
        return_hidden_states: bool = False,
    ) -> ModelOutput:
        """
        Execute full forward computation pass.
        Args:
            input_ids: LongTensor of shape (batch_size, seq_len)
            attention_mask: Optional mask
            context_hints: Metadata dictionary (e.g. {'operating_mode': 'personal'})
            return_hidden_states: Whether to collect intermediate layer representations
        Returns:
            ModelOutput dataclass
        """
        if input_ids.dim() != 2:
            raise ShapeMismatchError(
                f"Expected 2D input_ids tensor (batch, seq_len), got shape {tuple(input_ids.shape)}"
            )

        seq_len = input_ids.shape[1]
        if seq_len > self.config.max_seq_len:
            raise ArchitectureError(
                f"Input sequence length ({seq_len}) exceeds configured maximum ({self.config.max_seq_len})"
            )

        # 1. Input Processing
        h = self.input_projection(input_ids)

        hidden_states: List[torch.Tensor] = [h] if return_hidden_states else []
        attentions: List[torch.Tensor] = []

        # 2. Sequential Hierarchical Processing Blocks
        for layer in self.layers:
            h, attn_meta = layer(h, attention_mask=attention_mask)
            if return_hidden_states:
                hidden_states.append(h)
            if attn_meta is not None:
                attentions.append(attn_meta)

        # 3. Dynamic Neural Routing & Specialized Expert Execution
        routing_decision = self.router.route(h, context_hints=context_hints)
        expert_id = routing_decision.selected_expert_ids[0]
        # Route through selected domain expert
        if expert_id < len(self.experts):
            h = h + self.experts[expert_id](h)

        # 4. Final Normalization & Output Logits
        h_normed = self.final_norm(h)
        logits = self.output_projection(h_normed)

        return ModelOutput(
            logits=logits,
            hidden_states=hidden_states if return_hidden_states else None,
            attentions=attentions if attentions else None,
            metadata={
                "parameter_count": self.parameter_count,
                "routing_decision": routing_decision.__dict__,
            },
        )
