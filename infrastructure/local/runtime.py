"""
404 FOUNDERS — Local Workstation Runtime Manager
Budgets system resources (RAM, CPU threads) to prevent kernel OOM panics on swapless systems
and manages execution modes (Local CPU, Mock GPU, Remote Cluster).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, Optional

from infrastructure.local.hardware import LocalHardwareInspector, LocalHardwareProfile


# Execution Mode Constants
EXEC_MODE_LOCAL_CPU = "local_cpu"
EXEC_MODE_MOCK_GPU = "mock_gpu"
EXEC_MODE_REMOTE_CLUSTER = "remote_cluster"


@dataclass
class RuntimeBudget:
    """Resource constraints for local workstation process execution."""

    max_ram_bytes: int
    cpu_thread_limit: int
    execution_mode: str = EXEC_MODE_LOCAL_CPU
    enforce_oom_guard: bool = True

    @property
    def max_ram_gb(self) -> float:
        return round(self.max_ram_bytes / (1024**3), 2)


class LocalRuntimeManager:
    """Manages workstation execution limits and guards against memory exhaustion."""

    DEFAULT_MAX_RAM_FRACTION = 0.60  # Safe cap: 60% of available RAM

    def __init__(self, profile: Optional[LocalHardwareProfile] = None) -> None:
        self.profile = profile or LocalHardwareInspector.get_profile()
        self.budget = self._calculate_safe_budget()

    def _calculate_safe_budget(self) -> RuntimeBudget:
        """Derive safe resource limits based on physical host telemetry."""
        # On swapless systems (like Dell Latitude 5400 with 0B swap), limit process to 60% of free RAM
        avail = self.profile.available_ram_bytes
        max_bytes = int(avail * self.DEFAULT_MAX_RAM_FRACTION)

        # Thread limit: match physical cores to prevent hyperthread contention on compute kernels
        threads = max(1, self.profile.physical_cores)

        mode = EXEC_MODE_LOCAL_CPU
        if self.profile.has_nvidia_gpu and self.profile.cuda_runtime_available:
            mode = EXEC_MODE_MOCK_GPU

        return RuntimeBudget(
            max_ram_bytes=max_bytes,
            cpu_thread_limit=threads,
            execution_mode=mode,
            enforce_oom_guard=True,
        )

    def apply_thread_limits(self) -> None:
        """Apply CPU thread limits to PyTorch, OpenMP, and MKL runtimes."""
        threads = self.budget.cpu_thread_limit
        os.environ["OMP_NUM_THREADS"] = str(threads)
        os.environ["MKL_NUM_THREADS"] = str(threads)
        os.environ["OPENBLAS_NUM_THREADS"] = str(threads)

        try:
            import torch
            torch.set_num_threads(threads)
        except Exception:
            pass

    def check_memory_headroom(self, required_bytes: int) -> bool:
        """Check if requested memory allocation fits within safe budget."""
        return required_bytes <= self.budget.max_ram_bytes

    def get_runtime_status(self) -> Dict[str, Any]:
        """Return comprehensive runtime budget and host execution state."""
        return {
            "execution_mode": self.budget.execution_mode,
            "max_ram_budget_bytes": self.budget.max_ram_bytes,
            "max_ram_budget_gb": self.budget.max_ram_gb,
            "cpu_thread_limit": self.budget.cpu_thread_limit,
            "host_available_ram_gb": self.profile.available_ram_gb,
            "host_swap_bytes": self.profile.swap_total_bytes,
            "has_discrete_gpu": self.profile.has_nvidia_gpu,
            "gpu_model": self.profile.gpu_model,
        }
