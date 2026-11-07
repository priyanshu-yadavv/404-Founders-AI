"""
404 FOUNDERS — OS Adapters & System Telemetry Unit Tests
Validates zero-fabrication system vitals, hardware metrics, process monitoring,
and system process protection guards.
"""

from personal_ai.os_adapters import get_os_adapter
from personal_ai.os_adapters.base import (
    BaseOSAdapter,
    CPUVitals,
    MemoryVitals,
    OSInfo,
    ProcessInfo,
)
from personal_ai.system_monitor.process_monitor import ProcessMonitor
from personal_ai.system_monitor.system_info import SystemInfoProvider


def test_os_adapter_detection():
    """Verify host OS detection returns a functional adapter."""
    adapter = get_os_adapter()
    assert isinstance(adapter, BaseOSAdapter)

    os_info = adapter.get_os_info()
    assert isinstance(os_info, OSInfo)
    assert os_info.os_name in ["Linux", "Windows"]
    assert len(os_info.architecture) > 0
    assert len(os_info.kernel_version) > 0


def test_cpu_vitals_telemetry():
    """Verify real CPU telemetry without fabrication."""
    adapter = get_os_adapter()
    cpu = adapter.get_cpu_vitals()
    assert isinstance(cpu, CPUVitals)
    assert cpu.logical_cores >= 1
    assert cpu.physical_cores >= 1
    assert 0.0 <= cpu.usage_percent_overall <= 100.0
    assert len(cpu.usage_per_core) == cpu.logical_cores
    assert cpu.frequency_mhz >= 0.0


def test_memory_vitals_telemetry():
    """Verify real RAM telemetry without fabrication."""
    adapter = get_os_adapter()
    mem = adapter.get_memory_vitals()
    assert isinstance(mem, MemoryVitals)
    assert mem.total_ram_mb > 0
    assert mem.available_ram_mb >= 0
    assert mem.used_ram_mb >= 0
    assert 0.0 <= mem.percent_used_ram <= 100.0
    assert mem.total_swap_mb >= 0


def test_system_info_provider_summary():
    """Verify top-level SystemInfoProvider aggregate report."""
    provider = SystemInfoProvider()
    summary = provider.get_system_summary()
    assert summary.os_name in ["Linux", "Windows"]
    assert summary.cpu.logical_cores >= 1
    assert summary.memory.total_ram_mb > 0
    assert summary.uptime_hours >= 0.0

    telemetry = provider.get_hardware_telemetry()
    assert "cpu_model" in telemetry
    assert "ram_used_pct" in telemetry
    assert "uptime_hours" in telemetry


def test_process_monitor_listing_and_protection():
    """Verify process monitoring and system process protection guards."""
    monitor = ProcessMonitor()
    processes = monitor.list_processes(limit=100)
    assert len(processes) > 0

    # Ensure system processes are marked as protected
    protected_procs = [p for p in processes if p.is_protected]
    assert len(protected_procs) > 0

    # Test protection guard directly
    for p in protected_procs:
        assert monitor.is_process_protected(p.pid) is True
        guard = monitor.check_termination_permission(p.pid)
        assert guard["permitted"] is False
        assert "Protected system process" in guard["reason"]


def test_process_monitor_consumers_and_anomalies():
    """Verify resource consumption ranking and anomaly detection."""
    monitor = ProcessMonitor()
    top = monitor.get_top_resource_consumers(top_n=5)
    assert "top_memory" in top
    assert "top_cpu" in top
    assert len(top["top_memory"]) <= 5

    anomalies = monitor.detect_anomalies(cpu_threshold_pct=99.0, mem_threshold_mb=100000.0)
    assert isinstance(anomalies, list)
