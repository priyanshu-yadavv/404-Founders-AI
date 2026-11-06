"""
404 FOUNDERS — Local Hardware & Workstation Runtime Tests
Validates safe host hardware inspection, swapless memory budgeting, and CPU worker limits.
"""

from __future__ import annotations

import os
import pytest

from infrastructure.local import (
    LocalHardwareInspector,
    LocalHardwareProfile,
    LocalRuntimeManager,
)


def test_local_hardware_inspector_profile() -> None:
    """Verify inspector accurately reads host CPU, RAM, and storage telemetry."""
    profile = LocalHardwareInspector.get_profile()

    assert isinstance(profile, LocalHardwareProfile)
    assert len(profile.cpu_model) > 0
    assert profile.physical_cores >= 1
    assert profile.logical_threads >= profile.physical_cores
    assert profile.total_ram_bytes > 0
    assert profile.available_ram_bytes > 0
    assert profile.total_ram_gb > 0
    assert profile.available_ram_gb <= profile.total_ram_gb
    assert profile.root_total_bytes > 0
    assert profile.root_free_bytes <= profile.root_total_bytes


def test_runtime_budget_calculation_on_swapless_system() -> None:
    """Verify runtime manager enforces safe memory margin (60% ceiling)."""
    # Create mock profile with 16GB RAM and 0B swap
    mock_profile = LocalHardwareProfile(
        cpu_model="Mock Intel i5",
        physical_cores=4,
        logical_threads=8,
        has_avx=True,
        has_avx2=True,
        has_fma3=True,
        has_avx512=False,
        total_ram_bytes=16 * 1024**3,
        available_ram_bytes=10 * 1024**3,
        swap_total_bytes=0,
        has_nvidia_gpu=False,
        gpu_model="Intel UHD 620 UMA",
        vram_bytes=0,
    )

    manager = LocalRuntimeManager(mock_profile)
    budget = manager.budget

    # Expected: 60% of 10GB = 6GB
    expected_limit = int(10 * 1024**3 * 0.60)
    assert budget.max_ram_bytes == expected_limit
    assert budget.cpu_thread_limit <= mock_profile.physical_cores
    assert budget.execution_mode == "local_cpu"
    assert budget.enforce_oom_guard is True


def test_runtime_manager_validation_checks() -> None:
    """Verify manager validates request against allocated budget."""
    mock_profile = LocalHardwareProfile(
        cpu_model="Mock CPU",
        physical_cores=2,
        logical_threads=4,
        has_avx=True,
        has_avx2=True,
        has_fma3=True,
        has_avx512=False,
        total_ram_bytes=8 * 1024**3,
        available_ram_bytes=4 * 1024**3,
        swap_total_bytes=0,
        has_nvidia_gpu=False,
        gpu_model="UMA",
        vram_bytes=0,
    )
    manager = LocalRuntimeManager(mock_profile)

    # 1GB request should pass
    assert manager.check_memory_headroom(1 * 1024**3) is True

    # 10GB request exceeds safe limit (~2.4GB)
    assert manager.check_memory_headroom(10 * 1024**3) is False
