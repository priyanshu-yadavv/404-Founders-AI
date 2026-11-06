"""
404 FOUNDERS — Slurm Workload Manager Specifications
Generates production Slurm SBATCH job submission scripts for multi-node GPU superclusters
using PyTorch FSDP, Pyxis/Enroot containers, and InfiniBand fabrics.
"""

from __future__ import annotations

from typing import Dict, Optional


class SlurmSpecGenerator:
    """Generates Slurm SBATCH submission scripts for multi-node AI foundation training."""

    @classmethod
    def generate_sbatch_script(
        cls,
        job_name: str = "404_founders_pretrain",
        node_count: int = 8,
        gpus_per_node: int = 8,
        partition: str = "gpu-h100",
        time_limit: str = "48:00:00",
        container_image: str = "404-founders-training:v1.0.sqsh",
        training_script: str = "scripts/train_foundation_fsdp.py",
        master_port: int = 29500,
    ) -> str:
        """Generate a production Slurm SBATCH script for multi-node training."""
        total_gpus = node_count * gpus_per_node
        return f"""#!/bin/bash
#SBATCH --job-name={job_name}
#SBATCH --nodes={node_count}
#SBATCH --ntasks-per-node=1
#SBATCH --gpus-per-node={gpus_per_node}
#SBATCH --cpus-per-task=128
#SBATCH --partition={partition}
#SBATCH --time={time_limit}
#SBATCH --output=logs/slurm_%j.out
#SBATCH --error=logs/slurm_%j.err
#SBATCH --exclusive

# 404 FOUNDERS — Multi-Node Distributed Training Launcher
# Total Nodes: {node_count} | Total GPUs: {total_gpus}

set -eo pipefail

echo "============================================================"
echo "Job ID: $SLURM_JOB_ID | Nodes: $SLURM_JOB_NUM_NODES"
echo "Allocated Nodes: $SLURM_JOB_NODELIST"
echo "Start Time: $(date -u)"
echo "============================================================"

# Master Node IP Address Resolution
export MASTER_ADDR=$(scontrol show hostnames "$SLURM_JOB_NODELIST" | head -n 1)
export MASTER_PORT={master_port}
export WORLD_SIZE={total_gpus}

# NCCL Interconnect Environment Optimization
export NCCL_DEBUG=INFO
export NCCL_DEBUG_SUBSYS=INIT,COLL,ENV
export NCCL_IB_DISABLE=0
export NCCL_IB_HCA=mlx5_0,mlx5_1,mlx5_2,mlx5_3,mlx5_4,mlx5_5,mlx5_6,mlx5_7
export NCCL_IB_GID_INDEX=3
export NCCL_CROSS_NIC=1
export NCCL_NET_GDR_LEVEL=5
export CUDA_DEVICE_MAX_CONNECTIONS=1

echo "Master Address: $MASTER_ADDR:$MASTER_PORT"
echo "Total Distributed World Size: $WORLD_SIZE"

# Execute PyTorch Distributed Runner via Slurm srun & Pyxis Container
srun \\
    --container-image="{container_image}" \\
    --container-mounts=/shared/404-FOUNDERS:/workspace/404-FOUNDERS,/local_nvme:/tmp \\
    --container-workdir=/workspace/404-FOUNDERS \\
    torchrun \\
        --nnodes={node_count} \\
        --nproc_per_node={gpus_per_node} \\
        --rdzv_id=$SLURM_JOB_ID \\
        --rdzv_backend=c10d \\
        --rdzv_endpoint="$MASTER_ADDR:$MASTER_PORT" \\
        {training_script} \\
        --config configs/training/fsdp_config.yaml

echo "============================================================"
echo "Training Run Completed: $(date -u)"
echo "============================================================"
"""
