"""
404 FOUNDERS — Distributed Training Infrastructure
Provides 4D parallelism, gradient synchronization, and atomic sharded checkpointing.
"""

from infrastructure.distributed.checkpointing import (
    CheckpointMetadata,
    DistributedCheckpointManager,
)
from infrastructure.distributed.gradient_sync import (
    GradientSyncManager,
    GradientSyncPolicy,
)
from infrastructure.distributed.parallelism import (
    ParallelismConfig,
    ParallelismEngine,
)

__all__ = [
    "ParallelismConfig",
    "ParallelismEngine",
    "GradientSyncPolicy",
    "GradientSyncManager",
    "CheckpointMetadata",
    "DistributedCheckpointManager",
]
