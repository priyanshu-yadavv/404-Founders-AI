"""
404 FOUNDERS — Foundation Model & Pretraining Configuration
Provides type-safe, auditable configurations for model architecture, optimization,
and distributed pretraining across experimental, local CPU, and cluster profiles.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, Optional
import json
import yaml

from core.intelligence.neural_core import NeuralCoreConfig


class PrecisionType(str, Enum):
    """Supported computational precision modes."""
    FP32 = "fp32"
    BF16 = "bf16"
    FP16 = "fp16"


class InitStrategy(str, Enum):
    """Supported parameter initialization strategies."""
    SCALED_GAUSSIAN = "scaled_gaussian"
    XAVIER_UNIFORM = "xavier_uniform"
    KAIMING_NORMAL = "kaiming_normal"


@dataclass
class FoundationModelConfig:
    """
    Architectural configuration for the 404 FOUNDERS foundation model.
    Defines structural layer dimensions, attention topology, and context limits.
    """

    # Model dimensions
    vocab_size: int = 512
    d_model: int = 128
    n_layers: int = 2
    n_heads: int = 4
    intermediate_dim: Optional[int] = None
    max_seq_len: int = 256

    # Attention topology
    use_fusion_attention: bool = True
    window_size: int = 64
    chunk_size: int = 16
    num_experts: int = 2

    # Regularization & Initialization
    dropout: float = 0.0
    init_strategy: str = InitStrategy.SCALED_GAUSSIAN.value
    init_std: float = 0.02
    scale_residual_init: bool = True
    norm_eps: float = 1e-6
    random_seed: int = 404

    def __post_init__(self) -> None:
        if self.vocab_size <= 0:
            raise ValueError(f"vocab_size must be positive, got {self.vocab_size}")
        if self.d_model <= 0 or self.d_model % self.n_heads != 0:
            raise ValueError(
                f"d_model ({self.d_model}) must be positive and divisible by n_heads ({self.n_heads})"
            )
        if self.n_layers <= 0:
            raise ValueError(f"n_layers must be positive, got {self.n_layers}")
        if self.max_seq_len <= 0:
            raise ValueError(f"max_seq_len must be positive, got {self.max_seq_len}")
        if not (0.0 <= self.dropout < 1.0):
            raise ValueError(f"dropout must be in [0.0, 1.0), got {self.dropout}")

    def to_neural_core_config(self) -> NeuralCoreConfig:
        """Translate into NeuralCoreConfig expected by NeuralCore engine."""
        return NeuralCoreConfig(
            d_model=self.d_model,
            n_layers=self.n_layers,
            n_heads=self.n_heads,
            vocab_size=self.vocab_size,
            max_seq_len=self.max_seq_len,
            use_fusion_attention=self.use_fusion_attention,
            window_size=self.window_size,
            chunk_size=self.chunk_size,
            intermediate_dim=self.intermediate_dim,
            dropout=self.dropout,
            random_seed=self.random_seed,
            num_experts=self.num_experts,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> FoundationModelConfig:
        """Instantiate configuration from dictionary."""
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


@dataclass
class PretrainingConfig:
    """
    Optimization, hardware execution, and checkpointing configuration for pretraining.
    """

    # Batching & accumulation
    batch_size: int = 4
    gradient_accumulation_steps: int = 1

    # Optimizer (AdamW) hyperparameters
    learning_rate: float = 3e-4
    min_learning_rate: float = 3e-5
    weight_decay: float = 0.01
    beta1: float = 0.9
    beta2: float = 0.95
    eps: float = 1e-8
    max_grad_norm: float = 1.0

    # Learning rate schedule
    warmup_steps: int = 20
    max_steps: int = 100

    # Execution & Precision
    precision: str = PrecisionType.FP32.value
    device: str = "cpu"
    seed: int = 404

    # Intervals (in training steps)
    log_interval: int = 5
    eval_interval: int = 20
    save_interval: int = 50

    # Paths & Special Tokens
    checkpoint_dir: str = "checkpoints"
    output_dir: str = "training_runs"
    ignore_index: int = 0  # <pad> token ID

    def __post_init__(self) -> None:
        if self.batch_size <= 0:
            raise ValueError(f"batch_size must be positive, got {self.batch_size}")
        if self.gradient_accumulation_steps <= 0:
            raise ValueError(
                f"gradient_accumulation_steps must be positive, got {self.gradient_accumulation_steps}"
            )
        if self.learning_rate <= 0:
            raise ValueError(f"learning_rate must be positive, got {self.learning_rate}")
        if self.max_steps <= 0:
            raise ValueError(f"max_steps must be positive, got {self.max_steps}")

    @property
    def effective_batch_size(self) -> int:
        """Global effective batch size per optimizer step."""
        return self.batch_size * self.gradient_accumulation_steps

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PretrainingConfig:
        """Instantiate configuration from dictionary."""
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


# -----------------------------------------------------------------------------
# Standard Approved Preset Profiles
# -----------------------------------------------------------------------------

# 1. Experimental Tiny Profile: Ultra-lightweight for fast CPU smoke tests (<200k params)
EXPERIMENTAL_TINY_CONFIG = FoundationModelConfig(
    vocab_size=512,
    d_model=64,
    n_layers=2,
    n_heads=2,
    intermediate_dim=128,
    max_seq_len=64,
    window_size=16,
    chunk_size=8,
    use_fusion_attention=False,
    num_experts=2,
    dropout=0.0,
    random_seed=404,
)

# 2. Local Workstation Profile: Sized strictly for Dell Latitude 5400 CPU (~633k params)
EXPERIMENTAL_LOCAL_CPU_CONFIG = FoundationModelConfig(
    vocab_size=512,
    d_model=128,
    n_layers=2,
    n_heads=4,
    intermediate_dim=256,
    max_seq_len=128,
    window_size=32,
    chunk_size=16,
    use_fusion_attention=True,
    num_experts=2,
    dropout=0.0,
    random_seed=404,
)

# 3. Research Pilot Profile: Single-GPU pilot testing (~25M params, Tier A/B)
RESEARCH_PILOT_CONFIG = FoundationModelConfig(
    vocab_size=4096,
    d_model=512,
    n_layers=8,
    n_heads=8,
    intermediate_dim=1536,
    max_seq_len=512,
    window_size=128,
    chunk_size=32,
    use_fusion_attention=True,
    num_experts=4,
    dropout=0.1,
    random_seed=404,
)

# 4. Production Cluster Profile: Target foundation spec (~1.2B params, Tier C Supercluster)
PRODUCTION_CLUSTER_SPEC = FoundationModelConfig(
    vocab_size=32000,
    d_model=2048,
    n_layers=24,
    n_heads=16,
    intermediate_dim=5632,
    max_seq_len=2048,
    window_size=256,
    chunk_size=64,
    use_fusion_attention=True,
    num_experts=8,
    dropout=0.0,
    random_seed=404,
)
