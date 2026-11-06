"""
404 FOUNDERS — Distributed Parallelism Configuration
Designs and validates 4D Parallelism topologies (Data, Tensor, Pipeline, Sequence Parallelism)
and ZeRO / Fully Sharded Data Parallel (FSDP) shard layouts.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional


@dataclass
class ParallelismConfig:
    """4D Parallelism distribution topology specification.

    Constraint: dp_degree * tp_degree * pp_degree * sp_degree == total_gpus
    """

    total_gpus: int
    data_parallel_size: int = 1
    tensor_parallel_size: int = 1
    pipeline_parallel_size: int = 1
    sequence_parallel_size: int = 1
    fsdp_sharding_strategy: str = "FULL_SHARD"  # NO_SHARD, SHARD_GRAD_OP, FULL_SHARD (ZeRO-3)
    mixed_precision: str = "bfloat16"           # bfloat16, fp16, fp32
    gradient_accumulation_steps: int = 1

    def __post_init__(self) -> None:
        computed = (
            self.data_parallel_size
            * self.tensor_parallel_size
            * self.pipeline_parallel_size
            * self.sequence_parallel_size
        )
        if computed != self.total_gpus:
            raise ValueError(
                f"Invalid 4D Parallelism grid: DP({self.data_parallel_size}) * "
                f"TP({self.tensor_parallel_size}) * PP({self.pipeline_parallel_size}) * "
                f"SP({self.sequence_parallel_size}) = {computed} != Total GPUs ({self.total_gpus})"
            )
        if self.fsdp_sharding_strategy not in ("NO_SHARD", "SHARD_GRAD_OP", "FULL_SHARD"):
            raise ValueError(f"Unknown FSDP strategy: {self.fsdp_sharding_strategy}")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ParallelismEngine:
    """Constructs optimal distributed parallelism configurations based on model parameters and cluster size."""

    @classmethod
    def recommend_topology(
        cls,
        parameter_count: int,
        total_gpus: int,
        context_length: int = 4096,
    ) -> ParallelismConfig:
        """Derive recommended 4D parallelism dimensions for a given model scale and GPU count.

        Rules of Thumb:
        - TP (Tensor Parallelism): Kept intra-node (<=8) to stay within high-bandwidth NVLink.
        - PP (Pipeline Parallelism): Used when model weights exceed single-node aggregated VRAM.
        - SP (Sequence Parallelism): Enabled for extreme context lengths (>=32,768).
        - DP / FSDP (Data Parallelism): Scales across remaining cluster nodes.
        """
        # Small / Single GPU
        if total_gpus <= 1:
            return ParallelismConfig(total_gpus=1, data_parallel_size=1)

        # Micro-to-Medium (<2B params) across multi-GPU
        if parameter_count < 2_000_000_000:
            # Pure FSDP (Full Shard) or DDP
            return ParallelismConfig(
                total_gpus=total_gpus,
                data_parallel_size=total_gpus,
                tensor_parallel_size=1,
                pipeline_parallel_size=1,
                sequence_parallel_size=1,
                fsdp_sharding_strategy="FULL_SHARD",
            )

        # Medium-to-Large (2B to 14B params)
        if parameter_count <= 14_000_000_000:
            # Intra-node TP (2 or 4) + FSDP
            tp = 2 if total_gpus >= 8 else 1
            dp = total_gpus // tp
            return ParallelismConfig(
                total_gpus=total_gpus,
                data_parallel_size=dp,
                tensor_parallel_size=tp,
                pipeline_parallel_size=1,
                sequence_parallel_size=1,
                fsdp_sharding_strategy="FULL_SHARD",
            )

        # Large-Scale Pretraining (>14B params on 64 GPUs)
        # TP=4 (intra-node NVLink), PP=2 (inter-node), DP=8 (distributed across nodes)
        tp = 4
        pp = 2
        dp = total_gpus // (tp * pp)
        return ParallelismConfig(
            total_gpus=total_gpus,
            data_parallel_size=dp,
            tensor_parallel_size=tp,
            pipeline_parallel_size=pp,
            sequence_parallel_size=1,
            fsdp_sharding_strategy="FULL_SHARD",
            gradient_accumulation_steps=4,
        )
