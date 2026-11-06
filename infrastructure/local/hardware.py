"""
404 FOUNDERS — Local Hardware Inspector
Safe, read-only introspection of workstation host hardware (CPU, RAM, GPU, storage, networking).
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class LocalHardwareProfile:
    """Comprehensive hardware inventory of the local host workstation."""

    # CPU Telemetry
    cpu_model: str
    physical_cores: int
    logical_threads: int
    has_avx: bool
    has_avx2: bool
    has_fma3: bool
    has_avx512: bool

    # RAM Telemetry
    total_ram_bytes: int
    available_ram_bytes: int
    swap_total_bytes: int

    # GPU / Graphics Telemetry
    has_nvidia_gpu: bool
    gpu_model: str
    vram_bytes: int
    cuda_driver_version: Optional[str] = None
    cuda_runtime_available: bool = False

    # Storage Telemetry
    root_total_bytes: int = 0
    root_free_bytes: int = 0

    # Virtualization Telemetry
    has_kvm: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to serializable dictionary."""
        return asdict(self)

    @property
    def total_ram_gb(self) -> float:
        return round(self.total_ram_bytes / (1024**3), 2)

    @property
    def available_ram_gb(self) -> float:
        return round(self.available_ram_bytes / (1024**3), 2)

    @property
    def root_free_gb(self) -> float:
        return round(self.root_free_bytes / (1024**3), 2)


class LocalHardwareInspector:
    """Performs safe, non-destructive, read-only host hardware inspection."""

    @classmethod
    def inspect_cpu(cls) -> Dict[str, Any]:
        """Read CPU model, core counts, and vector instruction flags from /proc/cpuinfo."""
        model = "Unknown CPU"
        flags: List[str] = []
        physical_ids = set()
        core_ids = set()
        processor_count = 0

        cpuinfo_path = Path("/proc/cpuinfo")
        if cpuinfo_path.is_file():
            current_phys = 0
            for line in cpuinfo_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                if line.startswith("model name"):
                    model = line.split(":", 1)[1].strip()
                elif line.startswith("flags"):
                    flags = line.split(":", 1)[1].strip().split()
                elif line.startswith("processor"):
                    processor_count += 1
                elif line.startswith("physical id"):
                    current_phys = int(line.split(":", 1)[1].strip())
                    physical_ids.add(current_phys)
                elif line.startswith("core id"):
                    cid = int(line.split(":", 1)[1].strip())
                    core_ids.add((current_phys, cid))

        phys_cores = len(core_ids) if core_ids else (os.cpu_count() or 1) // 2
        logical_threads = processor_count or (os.cpu_count() or 1)

        flag_set = set(flags)
        return {
            "model": model,
            "physical_cores": max(1, phys_cores),
            "logical_threads": logical_threads,
            "has_avx": "avx" in flag_set,
            "has_avx2": "avx2" in flag_set,
            "has_fma3": "fma" in flag_set,
            "has_avx512": any(f.startswith("avx512") for f in flag_set),
        }

    @classmethod
    def inspect_memory(cls) -> Dict[str, int]:
        """Read system physical memory and swap statistics from /proc/meminfo."""
        mem_total = 0
        mem_avail = 0
        swap_total = 0

        meminfo_path = Path("/proc/meminfo")
        if meminfo_path.is_file():
            for line in meminfo_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                parts = line.split(":")
                if len(parts) == 2:
                    key = parts[0].strip()
                    val_str = parts[1].strip().split()[0]
                    if val_str.isdigit():
                        val_kb = int(val_str)
                        if key == "MemTotal":
                            mem_total = val_kb * 1024
                        elif key == "MemAvailable":
                            mem_avail = val_kb * 1024
                        elif key == "SwapTotal":
                            swap_total = val_kb * 1024

        return {
            "total_bytes": mem_total,
            "available_bytes": mem_avail,
            "swap_total_bytes": swap_total,
        }

    @classmethod
    def inspect_gpu(cls) -> Dict[str, Any]:
        """Detect GPU availability safely without crashing if drivers are absent."""
        has_nvidia = False
        gpu_model = "Intel Integrated Graphics (UMA)"
        vram_bytes = 0
        cuda_driver = None
        cuda_available = False

        # 1. Check for nvidia-smi binary
        nvidia_smi = shutil.which("nvidia-smi")
        if nvidia_smi:
            try:
                res = subprocess.run(
                    [nvidia_smi, "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"],
                    capture_output=True,
                    text=True,
                    timeout=3,
                )
                if res.returncode == 0 and res.stdout.strip():
                    parts = res.stdout.strip().split(",")
                    if len(parts) >= 3:
                        gpu_model = parts[0].strip()
                        vram_mb = int(parts[1].strip())
                        vram_bytes = vram_mb * 1024 * 1024
                        cuda_driver = parts[2].strip()
                        has_nvidia = True
            except Exception:
                pass

        # 2. Check PyTorch CUDA availability if torch is present
        try:
            import torch
            cuda_available = torch.cuda.is_available()
            if cuda_available and not has_nvidia:
                has_nvidia = True
                gpu_model = torch.cuda.get_device_name(0)
                vram_bytes = torch.cuda.get_device_properties(0).total_memory
        except Exception:
            pass

        return {
            "has_nvidia_gpu": has_nvidia,
            "gpu_model": gpu_model,
            "vram_bytes": vram_bytes,
            "cuda_driver_version": cuda_driver,
            "cuda_runtime_available": cuda_available,
        }

    @classmethod
    def inspect_storage(cls) -> Dict[str, int]:
        """Inspect storage space available on the primary root filesystem."""
        try:
            stat = shutil.disk_usage("/")
            return {
                "root_total_bytes": stat.total,
                "root_free_bytes": stat.free,
            }
        except Exception:
            return {"root_total_bytes": 0, "root_free_bytes": 0}

    @classmethod
    def inspect_virtualization(cls) -> bool:
        """Check if KVM hardware virtualization device is present."""
        return Path("/dev/kvm").exists()

    @classmethod
    def get_profile(cls) -> LocalHardwareProfile:
        """Construct full hardware profile using all inspectors."""
        cpu_data = cls.inspect_cpu()
        mem_data = cls.inspect_memory()
        gpu_data = cls.inspect_gpu()
        storage_data = cls.inspect_storage()
        has_kvm = cls.inspect_virtualization()

        return LocalHardwareProfile(
            cpu_model=cpu_data["model"],
            physical_cores=cpu_data["physical_cores"],
            logical_threads=cpu_data["logical_threads"],
            has_avx=cpu_data["has_avx"],
            has_avx2=cpu_data["has_avx2"],
            has_fma3=cpu_data["has_fma3"],
            has_avx512=cpu_data["has_avx512"],
            total_ram_bytes=mem_data["total_bytes"],
            available_ram_bytes=mem_data["available_bytes"],
            swap_total_bytes=mem_data["swap_total_bytes"],
            has_nvidia_gpu=gpu_data["has_nvidia_gpu"],
            gpu_model=gpu_data["gpu_model"],
            vram_bytes=gpu_data["vram_bytes"],
            cuda_driver_version=gpu_data["cuda_driver_version"],
            cuda_runtime_available=gpu_data["cuda_runtime_available"],
            root_total_bytes=storage_data["root_total_bytes"],
            root_free_bytes=storage_data["root_free_bytes"],
            has_kvm=has_kvm,
        )
