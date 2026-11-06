"""
404 FOUNDERS — Distributed Training Interface
Provides abstract communication primitives, rank determination, and gradient
synchronization interfaces across single-node workstations and multi-node clusters.
"""

from __future__ import annotations

from typing import Any, Optional
import os
import torch
import torch.distributed as dist


class DistributedEngine:
    """
    Encapsulates PyTorch Distributed initialization and collective operations.
    Gracefully handles standalone single-process mode when distributed environment is absent.
    """

    def __init__(self) -> None:
        self.is_distributed = self._detect_distributed()
        self.rank = int(os.environ.get("RANK", 0)) if self.is_distributed else 0
        self.world_size = int(os.environ.get("WORLD_SIZE", 1)) if self.is_distributed else 1
        self.local_rank = int(os.environ.get("LOCAL_RANK", 0)) if self.is_distributed else 0

    def _detect_distributed(self) -> bool:
        """Detect whether running inside a distributed torchrun or Slurm environment."""
        return "WORLD_SIZE" in os.environ and int(os.environ.get("WORLD_SIZE", 1)) > 1

    def initialize_process_group(self, backend: Optional[str] = None) -> None:
        """
        Initialize distributed process group if running in multi-process mode.
        Uses 'nccl' on CUDA, 'gloo' on CPU.
        """
        if not self.is_distributed:
            return

        if not dist.is_initialized():
            if backend is None:
                backend = "nccl" if torch.cuda.is_available() else "gloo"
            dist.init_process_group(backend=backend)
            self.rank = dist.get_rank()
            self.world_size = dist.get_world_size()

    @property
    def is_main_process(self) -> bool:
        """True if current process is rank 0 or standalone."""
        return self.rank == 0

    def barrier(self) -> None:
        """Synchronize all processes across the cluster."""
        if self.is_distributed and dist.is_initialized():
            dist.barrier()

    def all_reduce_mean(self, tensor: torch.Tensor) -> torch.Tensor:
        """Compute all-reduce mean across all processes."""
        if self.is_distributed and dist.is_initialized():
            dist.all_reduce(tensor, op=dist.ReduceOp.SUM)
            tensor /= float(self.world_size)
        return tensor

    def broadcast(self, tensor: torch.Tensor, src: int = 0) -> torch.Tensor:
        """Broadcast tensor from src rank to all other ranks."""
        if self.is_distributed and dist.is_initialized():
            dist.broadcast(tensor, src=src)
        return tensor
