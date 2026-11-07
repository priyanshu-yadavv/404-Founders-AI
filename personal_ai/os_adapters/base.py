"""
404 FOUNDERS — OS Adapter Base Interface
Defines platform-agnostic contracts for local hardware, system introspection,
process inspection, and application discovery across Linux (Kali/Debian/Ubuntu) and Windows.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class OSInfo:
    """Operating system and platform identification."""
    system: str  # "Linux", "Windows", "Darwin"
    release: str
    version: str
    machine: str  # "x86_64", "AMD64", "arm64"
    distribution: str  # e.g., "Kali GNU/Linux", "Ubuntu", "Windows 11"
    kernel: str
    hostname: str
    python_version: str

    @property
    def os_name(self) -> str:
        return self.system

    @property
    def architecture(self) -> str:
        return self.machine

    @property
    def kernel_version(self) -> str:
        return self.kernel


@dataclass
class CPUVitals:
    """CPU hardware and load vitals."""
    model: str
    physical_cores: int
    logical_cores: int
    usage_percent_overall: float
    usage_percent_per_core: List[float]
    load_averages: List[float]  # 1m, 5m, 15m
    frequency_mhz: Optional[float] = None
    temperature_celsius: Optional[float] = None

    @property
    def usage_per_core(self) -> List[float]:
        return self.usage_percent_per_core



@dataclass
class MemoryVitals:
    """RAM and swap memory vitals in megabytes."""
    total_ram_mb: float
    available_ram_mb: float
    used_ram_mb: float
    percent_used_ram: float
    total_swap_mb: float
    free_swap_mb: float
    used_swap_mb: float
    percent_used_swap: float


@dataclass
class StoragePartition:
    """Filesystem partition metrics."""
    mount_point: str
    device: str
    filesystem: str
    total_gb: float
    used_gb: float
    free_gb: float
    percent_used: float


@dataclass
class BatteryStatus:
    """Host device battery metrics."""
    has_battery: bool
    percent: Optional[float] = None
    power_plugged: Optional[bool] = None
    charging_status: Optional[str] = None  # "Charging", "Discharging", "Full", "Unknown"


@dataclass
class ProcessInfo:
    """Running operating system process representation."""
    pid: int
    name: str
    cpu_percent: float
    memory_mb: float
    status: str
    user: str
    command_line: str
    is_protected: bool = False  # True for core system daemons


@dataclass
class NetworkInterfaceInfo:
    """Host network interface details."""
    name: str
    ipv4_addresses: List[str]
    ipv6_addresses: List[str]
    mac_address: str
    is_up: bool
    is_loopback: bool


@dataclass
class InstalledAppInfo:
    """Discovered local desktop application."""
    name: str
    executable: str
    category: str
    desktop_file_path: Optional[str] = None
    version: Optional[str] = None


class BaseOSAdapter(ABC):
    """Abstract base class for operating system specific system adapters."""

    @abstractmethod
    def get_os_info(self) -> OSInfo:
        """Inspect and return operating system identity."""
        pass

    @abstractmethod
    def get_cpu_vitals(self) -> CPUVitals:
        """Inspect and return CPU usage and temperature vitals."""
        pass

    @abstractmethod
    def get_memory_vitals(self) -> MemoryVitals:
        """Inspect and return RAM and swap consumption."""
        pass

    @abstractmethod
    def get_storage_partitions(self) -> List[StoragePartition]:
        """Inspect and return mounted storage partitions."""
        pass

    @abstractmethod
    def get_battery_status(self) -> BatteryStatus:
        """Inspect and return battery telemetry where supported."""
        pass

    @abstractmethod
    def get_system_uptime_seconds(self) -> float:
        """Inspect and return system uptime in seconds."""
        pass

    @abstractmethod
    def list_processes(self, limit: int = 50) -> List[ProcessInfo]:
        """Inspect and return running processes sorted by resource consumption."""
        pass

    @abstractmethod
    def list_network_interfaces(self) -> List[NetworkInterfaceInfo]:
        """Inspect and return local network interfaces."""
        pass

    @abstractmethod
    def list_installed_applications(self, limit: int = 100) -> List[InstalledAppInfo]:
        """Discover installed applications on the system."""
        pass
