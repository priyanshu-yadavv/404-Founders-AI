"""
404 FOUNDERS — OS Adapters Subsystem
Detects host operating system and provides platform-specific implementations
for Linux (Kali, Debian, Ubuntu) and Windows 10/11.
"""

import platform
from typing import Optional

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
from personal_ai.os_adapters.linux_adapter import LinuxAdapter
from personal_ai.os_adapters.windows_adapter import WindowsAdapter


def get_os_adapter() -> BaseOSAdapter:
    """Factory detecting current host platform and returning the specialized OS adapter."""
    sys_name = platform.system()
    if sys_name == "Windows":
        return WindowsAdapter()
    return LinuxAdapter()


__all__ = [
    "BaseOSAdapter",
    "BatteryStatus",
    "CPUVitals",
    "InstalledAppInfo",
    "LinuxAdapter",
    "MemoryVitals",
    "NetworkInterfaceInfo",
    "OSInfo",
    "ProcessInfo",
    "StoragePartition",
    "WindowsAdapter",
    "get_os_adapter",
]
