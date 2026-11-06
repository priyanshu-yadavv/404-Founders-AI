"""
404 FOUNDERS — Hybrid Workload Router
Determines optimal placement (Local Workstation vs Cloud Single-Node vs GPU Supercluster)
based on parameter scale, dataset volume, and memory requirements.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from infrastructure.local.runtime import (
    EXEC_MODE_LOCAL_CPU,
    EXEC_MODE_REMOTE_CLUSTER,
    LocalRuntimeManager,
)


TARGET_LOCAL_CPU = "local_workstation_cpu"
TARGET_CLOUD_DEV_NODE = "cloud_tier_a_dev_node"
TARGET_CLOUD_RESEARCH_NODE = "cloud_tier_b_research_node"
TARGET_GPU_SUPERCLUSTER = "cloud_tier_c_gpu_supercluster"


@dataclass
class PlacementDecision:
    """Outcome of workload placement routing analysis."""

    target: str
    reason: str
    estimated_ram_required_gb: float
    recommended_gpu_count: int
    estimated_cost_usd_per_hour: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target": self.target,
            "reason": self.reason,
            "estimated_ram_required_gb": self.estimated_ram_required_gb,
            "recommended_gpu_count": self.recommended_gpu_count,
            "estimated_cost_usd_per_hour": self.estimated_cost_usd_per_hour,
        }


class HybridWorkloadRouter:
    """Routes compute workloads to local CPU, cloud nodes, or training superclusters."""

    # Parameter thresholds
    MAX_LOCAL_PARAMS = 50_000_000        # 50M parameter micro-models on CPU
    MAX_DEV_NODE_PARAMS = 1_500_000_000  # 1.5B on single RTX 4090 / L40S
    MAX_RESEARCH_NODE_PARAMS = 14_000_000_000  # 14B on 8x H100 640GB

    def __init__(self, runtime_manager: Optional[LocalRuntimeManager] = None) -> None:
        self.runtime_manager = runtime_manager or LocalRuntimeManager()

    def route_training_job(
        self,
        parameter_count: int,
        dataset_tokens_count: int,
        batch_size: int = 1,
        precision: str = "bfloat16",
    ) -> PlacementDecision:
        """Analyze model training requirements and select optimal execution target.

        Args:
            parameter_count: Total trainable parameter count.
            dataset_tokens_count: Number of tokens to train over.
            batch_size: Micro-batch size per device.
            precision: Numerical precision ('fp32', 'fp16', 'bfloat16').

        Returns:
            PlacementDecision containing recommended execution target and rationale.
        """
        # Bytes per parameter: bfloat16 = 2 bytes, fp32 = 4 bytes
        bytes_per_param = 2 if precision in ("fp16", "bfloat16") else 4
        # Model weights + Adam optimizer states (8 bytes/param) + gradients (2 bytes/param) = ~16 bytes/param
        training_state_bytes = parameter_count * 16
        training_state_gb = training_state_bytes / (1024**3)

        # 1. Small experiments (<50M parameters) can run locally on CPU within safe memory budget
        if parameter_count <= self.MAX_LOCAL_PARAMS and training_state_gb <= self.runtime_manager.budget.max_ram_gb:
            return PlacementDecision(
                target=TARGET_LOCAL_CPU,
                reason=(
                    f"Model scale ({parameter_count:,} params, {training_state_gb:.2f} GB) "
                    f"fits within local workstation CPU budget ({self.runtime_manager.budget.max_ram_gb:.2f} GB)."
                ),
                estimated_ram_required_gb=round(training_state_gb, 2),
                recommended_gpu_count=0,
                estimated_cost_usd_per_hour=0.0,
            )

        # 2. Medium experiments (50M to 1.5B) require Tier A Cloud Development Node (1x-2x RTX 4090 / L40S)
        if parameter_count <= self.MAX_DEV_NODE_PARAMS:
            return PlacementDecision(
                target=TARGET_CLOUD_DEV_NODE,
                reason=(
                    f"Model scale ({parameter_count:,} params, {training_state_gb:.2f} GB) "
                    "exceeds local CPU headroom but fits on Tier A Cloud Dev Node (1x-2x GPU with 24-48GB VRAM)."
                ),
                estimated_ram_required_gb=round(training_state_gb, 2),
                recommended_gpu_count=1,
                estimated_cost_usd_per_hour=0.50,
            )

        # 3. Multi-GPU Research (1.5B to 14B) requires Tier B 8x H100 Node
        if parameter_count <= self.MAX_RESEARCH_NODE_PARAMS:
            return PlacementDecision(
                target=TARGET_CLOUD_RESEARCH_NODE,
                reason=(
                    f"Model scale ({parameter_count:,} params, {training_state_gb:.2f} GB) "
                    "requires multi-GPU research node (8x H100 80GB SXM5 with NVLink 4)."
                ),
                estimated_ram_required_gb=round(training_state_gb, 2),
                recommended_gpu_count=8,
                estimated_cost_usd_per_hour=24.00,
            )

        # 4. Large-scale Pretraining (>14B) requires Tier C Multi-Node Supercluster (32x to 64x H100/H200)
        return PlacementDecision(
            target=TARGET_GPU_SUPERCLUSTER,
            reason=(
                f"Foundation pretraining scale ({parameter_count:,} params, {dataset_tokens_count:,} tokens) "
                "requires Tier C distributed supercluster with InfiniBand NDR interconnect and 4D Parallelism."
            ),
            estimated_ram_required_gb=round(training_state_gb, 2),
            recommended_gpu_count=64,
            estimated_cost_usd_per_hour=192.00,
        )
