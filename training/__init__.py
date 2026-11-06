"""
404 FOUNDERS — Training Package
Foundation model pretraining pipeline from random initialization,
including configuration, initialization auditing, forward engine, loss objectives,
optimizers, schedulers, dataloaders, checkpointing, telemetry, and preflight verification.
"""

from training.checkpoints.checkpoint_manager import (
    CheckpointCorruptedError,
    CheckpointManager,
)
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
from training.dataloaders.data_loader import (
    FoundationDataLoader,
    SyntheticDatasetGenerator,
    TokenizedSequenceDataset,
)
from training.distributed.distributed_engine import DistributedEngine
from training.engine.compute_readiness import (
    ComputeReadinessGate,
    ComputeReadinessReport,
    MemoryBreakdown,
)
from training.engine.device_manager import DeviceManager
from training.engine.forward_engine import ForwardEngine
from training.engine.orchestrator import (
    TrainingOrchestrator,
    TrainingSummary,
)
from training.experiments.experiment_tracker import (
    ExperimentManifest,
    ExperimentTracker,
)
from training.initialization.initializer import (
    InitializationReport,
    LayerParamSummary,
    ModelInitializer,
)
from training.monitoring.training_monitor import (
    StepMetrics,
    TrainingMonitor,
)
from training.objectives.loss_engine import (
    AutoregressiveLossEngine,
    LossComputationError,
    LossOutput,
)
from training.optimizers.optimization_engine import OptimizationEngine
from training.schedulers.lr_scheduler import CosineWarmupScheduler
from training.validation.preflight_verifier import (
    PreflightReport,
    PreflightStepResult,
    PreflightVerifier,
)
from training.validation.validation_engine import (
    ValidationEngine,
    ValidationMetrics,
)

__all__ = [
    # Configs
    "FoundationModelConfig",
    "PretrainingConfig",
    "PrecisionType",
    "InitStrategy",
    "EXPERIMENTAL_TINY_CONFIG",
    "EXPERIMENTAL_LOCAL_CPU_CONFIG",
    "RESEARCH_PILOT_CONFIG",
    "PRODUCTION_CLUSTER_SPEC",
    # Initialization
    "ModelInitializer",
    "InitializationReport",
    "LayerParamSummary",
    # Engines
    "DeviceManager",
    "ForwardEngine",
    "TrainingOrchestrator",
    "TrainingSummary",
    "ComputeReadinessGate",
    "ComputeReadinessReport",
    "MemoryBreakdown",
    # Objectives & Optimization
    "AutoregressiveLossEngine",
    "LossOutput",
    "LossComputationError",
    "OptimizationEngine",
    "CosineWarmupScheduler",
    # Data & Distributed
    "TokenizedSequenceDataset",
    "SyntheticDatasetGenerator",
    "FoundationDataLoader",
    "DistributedEngine",
    # Checkpointing & Telemetry
    "CheckpointManager",
    "CheckpointCorruptedError",
    "TrainingMonitor",
    "StepMetrics",
    "ExperimentTracker",
    "ExperimentManifest",
    # Validation
    "ValidationEngine",
    "ValidationMetrics",
    "PreflightVerifier",
    "PreflightReport",
    "PreflightStepResult",
]
