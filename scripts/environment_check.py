#!/usr/bin/env python3
"""
404 FOUNDERS — Environment & Toolchain Audit CLI
Audits Python, compilers (GCC, G++, Rust, Clang), build tools (CMake, Git),
and machine learning runtime environments (PyTorch, JAX).
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from pathlib import Path


def get_cmd_version(cmd: str, args: list[str]) -> str:
    path = shutil.which(cmd)
    if not path:
        return "Not installed"
    try:
        res = subprocess.run([path] + args, capture_output=True, text=True, timeout=3)
        if res.returncode == 0:
            lines = res.stdout.strip().splitlines()
            return lines[0] if lines else "Installed"
        return "Installed (version query failed)"
    except Exception:
        return "Error querying"


def main() -> int:
    print("=" * 65)
    print(" 404 FOUNDERS — Software Environment & Toolchain Audit")
    print("=" * 65)

    print(f"\n[Python & Runtime]")
    print(f"  Python Version   : {platform.python_version()} ({sys.executable})")
    print(f"  In Virtualenv    : {'Yes' if sys.prefix != sys.base_prefix else 'No'}")
    print(f"  Virtualenv Path  : {sys.prefix}")

    # PyTorch
    try:
        import torch

        print(f"  PyTorch          : {torch.__version__} (Device: {'CUDA' if torch.cuda.is_available() else 'CPU'})")
    except ImportError:
        print(f"  PyTorch          : Not installed")

    # JAX
    try:
        import jax

        print(f"  JAX              : {jax.__version__} (Devices: {jax.devices()})")
    except ImportError:
        print(f"  JAX              : Not installed (Targeted for cloud cluster / Phase 06)")

    print(f"\n[Compilers & Build Systems]")
    print(f"  GCC              : {get_cmd_version('gcc', ['--version'])}")
    print(f"  G++              : {get_cmd_version('g++', ['--version'])}")
    print(f"  Clang            : {get_cmd_version('clang', ['--version'])}")
    print(f"  Rust / Cargo     : {get_cmd_version('cargo', ['--version'])}")
    print(f"  CMake            : {get_cmd_version('cmake', ['--version'])}")

    print(f"\n[DevOps, Container & Version Control]")
    print(f"  Git              : {get_cmd_version('git', ['--version'])}")
    print(f"  GitHub CLI (gh)  : {get_cmd_version('gh', ['--version'])}")
    print(f"  Docker           : {get_cmd_version('docker', ['--version'])}")
    print(f"  Node.js / npm    : {get_cmd_version('node', ['--version'])} / {get_cmd_version('npm', ['--version'])}")

    print(f"\n[Accelerators & CUDA Toolchain]")
    print(f"  NVCC Compiler    : {get_cmd_version('nvcc', ['--version'])}")
    print("=" * 65)

    return 0


if __name__ == "__main__":
    sys.exit(main())
