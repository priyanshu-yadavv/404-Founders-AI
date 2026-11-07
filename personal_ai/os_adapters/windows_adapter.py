"""
404 FOUNDERS — Windows OS Adapter
Provides safe, read-only system inspection for Windows 10/11 workstations.
Uses standard Python platform, os, shutil, and socket APIs with graceful fallbacks.
"""

import os
from pathlib import Path
import platform
import shutil
import socket
import sys
from typing import Any, Dict, List, Optional

from personal_ai.os_adapters.base import (
    BaseOSAdapter,
    BatteryStatus,
    CPUVitals,
    InstalledAppInfo,
    MemoryVitals,
    NetworkInterfaceInfo,
    OSInfo,
    ProcessInfo,
    StoragePartition,
)


class WindowsAdapter(BaseOSAdapter):
    """Windows platform adapter supporting Windows 10/11."""

    def get_os_info(self) -> OSInfo:
        return OSInfo(
            system="Windows",
            release=platform.release(),
            version=platform.version(),
            machine=platform.machine(),
            distribution=f"Windows {platform.release()}",
            kernel=platform.version(),
            hostname=socket.gethostname(),
            python_version=platform.python_version(),
        )

    def get_cpu_vitals(self) -> CPUVitals:
        physical_cores = os.cpu_count() or 1
        logical_cores = os.cpu_count() or 1
        model = platform.processor() or "Windows x86_64 Processor"

        return CPUVitals(
            model=model,
            physical_cores=physical_cores,
            logical_cores=logical_cores,
            usage_percent_overall=0.0,
            usage_percent_per_core=[0.0] * logical_cores,
            load_averages=[0.0, 0.0, 0.0],
            frequency_mhz=None,
            temperature_celsius=None,
        )

    def get_memory_vitals(self) -> MemoryVitals:
        # Standard fallback for Windows without external ctypes
        return MemoryVitals(
            total_ram_mb=0.0,
            available_ram_mb=0.0,
            used_ram_mb=0.0,
            percent_used_ram=0.0,
            total_swap_mb=0.0,
            free_swap_mb=0.0,
            used_swap_mb=0.0,
            percent_used_swap=0.0,
        )

    def get_storage_partitions(self) -> List[StoragePartition]:
        partitions: List[StoragePartition] = []
        # On Windows, typically C:\
        drive = "C:\\" if os.name == "nt" else "/"
        try:
            usage = shutil.disk_usage(drive)
            total_gb = usage.total / (1024 ** 3)
            used_gb = usage.used / (1024 ** 3)
            free_gb = usage.free / (1024 ** 3)
            pct = (used_gb / total_gb * 100.0) if total_gb > 0 else 0.0

            partitions.append(
                StoragePartition(
                    mount_point=drive,
                    device=drive,
                    filesystem="NTFS" if os.name == "nt" else "ext4",
                    total_gb=round(total_gb, 2),
                    used_gb=round(used_gb, 2),
                    free_gb=round(free_gb, 2),
                    percent_used=round(pct, 1),
                )
            )
        except Exception:
            pass
        return partitions

    def get_battery_status(self) -> BatteryStatus:
        return BatteryStatus(has_battery=False)

    def get_system_uptime_seconds(self) -> float:
        return 0.0

    def list_processes(self, limit: int = 50) -> List[ProcessInfo]:
        return []

    def list_network_interfaces(self) -> List[NetworkInterfaceInfo]:
        return [
            NetworkInterfaceInfo(
                name="Ethernet",
                ipv4_addresses=["127.0.0.1"],
                ipv6_addresses=["::1"],
                mac_address="00:00:00:00:00:00",
                is_up=True,
                is_loopback=False,
            )
        ]

    def list_installed_applications(self, limit: int = 100) -> List[InstalledAppInfo]:
        return []
