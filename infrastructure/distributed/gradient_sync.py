"""
404 FOUNDERS — Distributed Gradient Synchronization
Manages gradient bucket sizing, backward-pass overlap, and communication scheduling.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict


@dataclass
class GradientSyncPolicy:
    """Policy governing distributed gradient synchronization and communication overlap."""

    bucket_cap_mb: float = 25.0
    gradient_clipping_norm: float = 1.0
    overlap_backward_communication: bool = True
    gradient_accumulation_steps: int = 1
    allreduce_precision: str = "bfloat16"  # Reduces collective network volume by 50% vs FP32

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class GradientSyncManager:
    """Manages gradient reduction policies to maximize compute/communication overlap."""

    @classmethod
    def get_optimized_policy(
        cls,
        total_gpus: int,
        is_multinode: bool,
    ) -> GradientSyncPolicy:
        """Derive optimal gradient synchronization settings.

        On multi-node clusters with InfiniBand, larger buckets (25-50 MB) amortize packet headers.
        On single-node PCIe, smaller buckets (10-25 MB) reduce peak memory spikes.
        """
        bucket_size = 50.0 if is_multinode else 25.0
        return GradientSyncPolicy(
            bucket_cap_mb=bucket_size,
            gradient_clipping_norm=1.0,
            overlap_backward_communication=True,
            gradient_accumulation_steps=4 if is_multinode else 1,
            allreduce_precision="bfloat16",
        )
