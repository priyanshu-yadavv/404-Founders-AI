"""
404 FOUNDERS — Neural Architecture/Fusion
Multi-stage cross-attention, early concatenation, and late gating mechanisms for multimodal fusion.
"""

from neural_architecture.fusion.multimodal_fusion import (
    CrossModalAttentionFusion,
    EarlyFusionLayer,
    FusionOutput,
    LateFusionAggregator,
    ModalityType,
    MultimodalFusionEngine,
    MultimodalInput,
)

__all__ = [
    "ModalityType",
    "MultimodalInput",
    "FusionOutput",
    "EarlyFusionLayer",
    "CrossModalAttentionFusion",
    "LateFusionAggregator",
    "MultimodalFusionEngine",
]
