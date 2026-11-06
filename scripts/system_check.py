#!/usr/bin/env python3
"""
404 FOUNDERS — System Check CLI
Performs read-only host system hardware inspection, evaluates memory and thread budgets,
and detects virtualization and NUMA topology.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure workspace root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from infrastructure.local import LocalHardwareInspector, LocalRuntimeManager


def main() -> int:
    print("=" * 65)
    print(" 404 FOUNDERS — Host System Hardware & Runtime Audit")
    print("=" * 65)

    inspector = LocalHardwareInspector()
    profile = inspector.get_profile()

    print(f"\n[CPU Telemetry]")
    print(f"  Model            : {profile.cpu_model}")
    print(f"  Cores / Threads  : {profile.physical_cores} physical cores / {profile.logical_threads} threads")
    print(f"  AVX / AVX2       : {'Yes' if profile.has_avx else 'No'} / {'Yes' if profile.has_avx2 else 'No'}")
    print(f"  FMA3 / AVX-512   : {'Yes' if profile.has_fma3 else 'No'} / {'Yes' if profile.has_avx512 else 'No'}")

    print(f"\n[Memory & Swap]")
    print(f"  Total RAM        : {profile.total_ram_gb} GB")
    print(f"  Available RAM    : {profile.available_ram_gb} GB")
    swap_gb = round(profile.swap_total_bytes / (1024**3), 2)
    print(f"  Total Swap       : {swap_gb} GB")
    if profile.swap_total_bytes == 0:
        print("  Notice           : Swapless environment detected. Conservative RAM budgeting enforced.")

    print(f"\n[Graphics & Accelerators]")
    print(f"  GPU Model        : {profile.gpu_model}")
    print(f"  Dedicated VRAM   : {round(profile.vram_bytes / (1024**3), 2)} GB")
    print(f"  NVIDIA Dedicated : {'Yes' if profile.has_nvidia_gpu else 'No'}")
    print(f"  CUDA Available   : {'Yes' if profile.cuda_runtime_available else 'No'}")

    print(f"\n[Primary Storage & Virtualization]")
    print(f"  Root Free Space  : {profile.root_free_gb} GB / {round(profile.root_total_bytes / (1024**3), 2)} GB")
    print(f"  Hardware KVM     : {'Supported (/dev/kvm present)' if profile.has_kvm else 'Not available'}")

    runtime_mgr = LocalRuntimeManager(profile)
    budget = runtime_mgr.budget
    print(f"\n[Runtime Execution Budget]")
    print(f"  Safe RAM Limit   : {budget.max_ram_gb} GB (60% available RAM ceiling)")
    print(f"  Max CPU Workers  : {budget.cpu_thread_limit} threads")
    print(f"  Execution Mode   : {budget.execution_mode}")
    print(f"  OOM Guard Active : {budget.enforce_oom_guard}")
    print("=" * 65)

    return 0


if __name__ == "__main__":
    sys.exit(main())
