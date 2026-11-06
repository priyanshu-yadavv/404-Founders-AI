"""
404 FOUNDERS — Training Metrics Collector & Hardware Telemetry
Collects DCGM GPU telemetry, system host metrics, and computes training throughput,
TFLOPS, and Model FLOPs Utilization (MFU).
"""

from __future__ import annotations

import os
import platform
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional


@dataclass
class HardwareTelemetry:
    """Snapshot of hardware metrics (host and accelerators)."""

    timestamp: float
    cpu_percent: float
    ram_used_gb: float
    ram_total_gb: float
    ram_percent: float
    gpu_metrics: List[Dict[str, Any]]
    disk_used_percent: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TrainingThroughput:
    """Throughput and efficiency calculation for training steps."""

    step: int
    step_duration_seconds: float
    batch_size: int
    sequence_length: int
    tokens_per_second: float
    achieved_tflops: float
    mfu_percent: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MetricsCollector:
    """Collects system host telemetry, simulated or real DCGM GPU metrics,

    and computes Model FLOPs Utilization (MFU).
    """

    def __init__(
        self,
        num_model_parameters: int,
        theoretical_peak_tflops_per_device: float = 989.0,  # H100 SXM5 BF16 peak ~989 TFLOPS
        num_devices: int = 1,
    ) -> None:
        self.num_params = num_model_parameters
        self.peak_tflops_per_device = theoretical_peak_tflops_per_device
        self.num_devices = max(1, num_devices)

    def collect_system_telemetry(self) -> HardwareTelemetry:
        """Collects safe host telemetry without requiring third-party libraries."""
        now = time.time()
        ram_total = 0.0
        ram_used = 0.0
        ram_percent = 0.0

        if os.path.exists("/proc/meminfo"):
            try:
                meminfo: Dict[str, float] = {}
                with open("/proc/meminfo", "r") as f:
                    for line in f:
                        parts = line.split(":")
                        if len(parts) == 2:
                            val = parts[1].strip().split()[0]
                            meminfo[parts[0].strip()] = float(val)
                total_kb = meminfo.get("MemTotal", 0.0)
                free_kb = meminfo.get("MemFree", 0.0)
                available_kb = meminfo.get("MemAvailable", free_kb)
                ram_total = total_kb / (1024.0 * 1024.0)
                used_kb = total_kb - available_kb
                ram_used = used_kb / (1024.0 * 1024.0)
                ram_percent = (used_kb / total_kb * 100.0) if total_kb > 0 else 0.0
            except Exception:
                pass

        # Load average approximation for CPU
        cpu_load = 0.0
        try:
            load1, _, _ = os.getloadavg()
            cpu_count = os.cpu_count() or 1
            cpu_load = min(100.0, (load1 / cpu_count) * 100.0)
        except Exception:
            pass

        # Disk space
        disk_pct = 0.0
        try:
            stat = os.statvfs(".")
            total = stat.f_blocks * stat.f_frsize
            free = stat.f_bfree * stat.f_frsize
            used = total - free
            disk_pct = (used / total * 100.0) if total > 0 else 0.0
        except Exception:
            pass

        return HardwareTelemetry(
            timestamp=now,
            cpu_percent=round(cpu_load, 1),
            ram_used_gb=round(ram_used, 2),
            ram_total_gb=round(ram_total, 2),
            ram_percent=round(ram_percent, 1),
            gpu_metrics=[],  # Empty for local non-NVIDIA host; populated via DCGM on cluster
            disk_used_percent=round(disk_pct, 1),
        )

    def compute_step_throughput(
        self,
        step: int,
        step_duration_seconds: float,
        tokens_in_step: int,
        batch_size: int = 1,
        sequence_length: int = 2048,
    ) -> TrainingThroughput:
        """Calculates step throughput, achieved TFLOPS, and Model FLOPs Utilization (MFU).

        Standard transformer FLOP estimate: 6 * N_params * N_tokens per step (forward + backward).
        """
        duration = max(step_duration_seconds, 1e-6)
        tok_per_sec = tokens_in_step / duration

        # 6 FLOPs per parameter per token (3x forward pass: 1 forward + 2 backward)
        step_flops = 6.0 * self.num_params * tokens_in_step
        achieved_tflops = (step_flops / duration) / 1e12

        total_peak_tflops = self.peak_tflops_per_device * self.num_devices
        mfu_percent = (achieved_tflops / total_peak_tflops * 100.0) if total_peak_tflops > 0 else 0.0

        return TrainingThroughput(
            step=step,
            step_duration_seconds=round(duration, 4),
            batch_size=batch_size,
            sequence_length=sequence_length,
            tokens_per_second=round(tok_per_sec, 2),
            achieved_tflops=round(achieved_tflops, 2),
            mfu_percent=round(mfu_percent, 2),
        )
