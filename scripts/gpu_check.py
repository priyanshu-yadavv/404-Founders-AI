#!/usr/bin/env python3
"""
404 FOUNDERS — GPU & CUDA Compatibility Check CLI
Inspects host GPU availability, CUDA driver version, and PyTorch accelerator support.
Gracefully handles CPU-only workstations and reports cloud cluster target capabilities.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from infrastructure.gpu_cluster import ClusterCatalog


def main() -> int:
    print("=" * 65)
    print(" 404 FOUNDERS — Accelerator & CUDA Compatibility Audit")
    print("=" * 65)

    # 1. PyTorch CUDA inspection
    try:
        import torch

        torch_version = torch.__version__
        cuda_available = torch.cuda.is_available()
        cuda_version = torch.version.cuda if hasattr(torch.version, "cuda") else "None"
        device_count = torch.cuda.device_count() if cuda_available else 0
    except ImportError:
        torch_version = "Not installed"
        cuda_available = False
        cuda_version = "None"
        device_count = 0

    print(f"\n[PyTorch Runtime]")
    print(f"  PyTorch Version  : {torch_version}")
    print(f"  CUDA Built-In    : {cuda_version}")
    print(f"  CUDA Available   : {'Yes' if cuda_available else 'No'}")
    print(f"  Device Count     : {device_count}")

    # 2. Host driver / nvidia-smi
    smi = shutil.which("nvidia-smi")
    has_nvidia_driver = False
    driver_version = "Not detected"

    if smi:
        try:
            res = subprocess.run(
                [smi, "--query-gpu=driver_version", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            if res.returncode == 0:
                has_nvidia_driver = True
                driver_version = res.stdout.strip()
        except Exception:
            pass

    print(f"\n[NVIDIA Driver & System Accelerators]")
    print(f"  nvidia-smi binary: {'Present (' + smi + ')' if smi else 'Not found'}")
    print(f"  Driver Version   : {driver_version}")

    if cuda_available and device_count > 0:
        for idx in range(device_count):
            props = torch.cuda.get_device_properties(idx)
            vram_gb = props.total_memory / (1024**3)
            print(f"  GPU #{idx}          : {props.name} | VRAM: {vram_gb:.2f} GB | CC: {props.major}.{props.minor}")
    else:
        print(f"\n[Local Environment Notice]")
        print("  Status           : CPU-Only Workstation (Intel UHD 620 UMA / 0GB dedicated VRAM).")
        print("  Workflow Policy  : Local development is strictly constrained to unit testing,")
        print("                     CPU tokenizer verification, and architecture validation.")
        print("                     Foundation pretraining is targeted for Tier B & Tier C clusters.")

    # 3. Target cluster catalog summary
    print(f"\n[404 FOUNDERS — Cluster Targets]")
    tier_a = ClusterCatalog.get_tier("A")
    tier_b = ClusterCatalog.get_tier("B")
    tier_c = ClusterCatalog.get_tier("C")

    if tier_a:
        print(f"  Tier A (Dev)     : {tier_a.node_count} Node, {tier_a.total_gpus}x {tier_a.gpu_model} ({tier_a.vram_per_gpu_gb}GB) -> Interconnect: {tier_a.interconnect.technology}")
    if tier_b:
        print(f"  Tier B (Research): {tier_b.node_count} Node, {tier_b.total_gpus}x {tier_b.gpu_model} ({tier_b.vram_per_gpu_gb}GB) -> Interconnect: {tier_b.interconnect.technology}")
    if tier_c:
        print(f"  Tier C (Pretrain): {tier_c.node_count} Nodes, {tier_c.total_gpus}x {tier_c.gpu_model} ({tier_c.vram_per_gpu_gb}GB) -> Interconnect: {tier_c.interconnect.technology}")

    print("=" * 65)
    return 0


if __name__ == "__main__":
    sys.exit(main())
