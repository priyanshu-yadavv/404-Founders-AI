"""
404 FOUNDERS — Training Configurations Package
"""

from training.configs.model_config import (
    EXPERIMENTAL_LOCAL_CPU_CONFIG,
    EXPERIMENTAL_TINY_CONFIG,
    PRODUCTION_CLUSTER_SPEC,
    RESEARCH_PILOT_CONFIG,
    FoundationModelConfig,
    InitStrategy,
    PrecisionType,
    PretrainingConfig,
)

__all__ = [
    "FoundationModelConfig",
    "PretrainingConfig",
    "PrecisionType",
    "InitStrategy",
    "EXPERIMENTAL_TINY_CONFIG",
    "EXPERIMENTAL_LOCAL_CPU_CONFIG",
    "RESEARCH_PILOT_CONFIG",
    "PRODUCTION_CLUSTER_SPEC",
]
