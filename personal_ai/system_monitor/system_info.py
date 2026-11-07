"""
404 FOUNDERS — System Information & Hardware Monitoring Provider
Provides read-only, non-destructive inspection of operating system, CPU,
memory, storage, battery, and sensor vitals. Zero false or fabricated metrics.
"""

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from personal_ai.os_adapters import (
    BaseOSAdapter,
    BatteryStatus,
    CPUVitals,
    MemoryVitals,
    OSInfo,
    StoragePartition,
    get_os_adapter,
)


@dataclass
class SystemSummary:
    """Consolidated host system telemetry."""
    os: OSInfo
    cpu: CPUVitals
    memory: MemoryVitals
    storage: List[StoragePartition]
    battery: BatteryStatus
    uptime_seconds: float
    has_battery: bool

    @property
    def os_name(self) -> str:
        return self.os.system

    @property
    def os_version(self) -> str:
        return self.os.version or self.os.release

    @property
    def architecture(self) -> str:
        return self.os.machine

    @property
    def hostname(self) -> str:
        return self.os.hostname

    @property
    def kernel_version(self) -> str:
        return self.os.kernel

    @property
    def uptime_hours(self) -> float:
        return round(self.uptime_seconds / 3600.0, 2)

    @property
    def battery_percent(self) -> Optional[float]:
        return self.battery.percent if self.has_battery else None



class SystemInfoProvider:
    """Read-only system information provider using host OS adapters."""

    def __init__(self, adapter: Optional[BaseOSAdapter] = None) -> None:
        self.adapter = adapter or get_os_adapter()

    def get_system_summary(self) -> SystemSummary:
        """Fetch complete system health snapshot."""
        os_info = self.adapter.get_os_info()
        cpu = self.adapter.get_cpu_vitals()
        mem = self.adapter.get_memory_vitals()
        storage = self.adapter.get_storage_partitions()
        battery = self.adapter.get_battery_status()
        uptime = self.adapter.get_system_uptime_seconds()

        return SystemSummary(
            os=os_info,
            cpu=cpu,
            memory=mem,
            storage=storage,
            battery=battery,
            uptime_seconds=uptime,
            has_battery=battery.has_battery,
        )

    def get_hardware_telemetry(self) -> Dict[str, Any]:
        """Fetch structured hardware vitals for monitoring dashboards."""
        cpu = self.adapter.get_cpu_vitals()
        mem = self.adapter.get_memory_vitals()
        storage = self.adapter.get_storage_partitions()
        battery = self.adapter.get_battery_status()

        return {
            "cpu_model": cpu.model,
            "physical_cores": cpu.physical_cores,
            "logical_cores": cpu.logical_cores,
            "cpu_usage_pct": cpu.usage_percent_overall,
            "load_averages": cpu.load_averages,
            "temperature_celsius": cpu.temperature_celsius,
            "total_ram_mb": mem.total_ram_mb,
            "available_ram_mb": mem.available_ram_mb,
            "used_ram_mb": mem.used_ram_mb,
            "ram_used_pct": mem.percent_used_ram,
            "total_swap_mb": mem.total_swap_mb,
            "swap_used_pct": mem.percent_used_swap,
            "partitions": [asdict(p) for p in storage],
            "battery_percent": battery.percent,
            "battery_charging": battery.power_plugged,
            "uptime_hours": round(self.adapter.get_system_uptime_seconds() / 3600.0, 2),
        }
