"""
404 FOUNDERS — Linux OS Adapter
Provides real, non-destructive system inspection for Linux distributions
including Kali Linux, Debian, and Ubuntu via /proc, /sys, and standard POSIX APIs.
"""

import glob
import os
from pathlib import Path
import platform
import re
import shutil
import socket
import sys
import time
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

PROTECTED_PROCESS_NAMES = {
    "systemd", "init", "sshd", "auditd", "kthreadd", "dbus-daemon",
    "dbus-broker", "NetworkManager", "rsyslogd", "cron", "crond",
    "polkitd", "udevd", "systemd-journald", "systemd-logind",
    "systemd-resolved", "systemd-timesyncd", "systemd-udevd", "systemd-networkd",
    "wpa_supplicant", "login", "agetty"
}


class LinuxAdapter(BaseOSAdapter):
    """Linux platform adapter reading real metrics from /proc, /sys, and POSIX calls."""

    def get_os_info(self) -> OSInfo:
        distro = "Linux"
        os_release = Path("/etc/os-release")
        if os_release.is_file():
            try:
                content = os_release.read_text(encoding="utf-8")
                name_match = re.search(r'^PRETTY_NAME=["\']?(.*?)["\']?$', content, re.M)
                if name_match:
                    distro = name_match.group(1)
            except Exception:
                pass

        return OSInfo(
            system="Linux",
            release=platform.release(),
            version=platform.version(),
            machine=platform.machine(),
            distribution=distro,
            kernel=platform.release(),
            hostname=socket.gethostname(),
            python_version=platform.python_version(),
        )

    def get_cpu_vitals(self) -> CPUVitals:
        model = "Unknown CPU"
        physical_cores = os.cpu_count() or 1
        logical_cores = os.cpu_count() or 1

        cpuinfo = Path("/proc/cpuinfo")
        if cpuinfo.is_file():
            try:
                for line in cpuinfo.read_text(encoding="utf-8").splitlines():
                    if "model name" in line:
                        model = line.split(":", 1)[1].strip()
                        break
            except Exception:
                pass

        # Load averages
        load_1, load_5, load_15 = (0.0, 0.0, 0.0)
        try:
            load_1, load_5, load_15 = os.getloadavg()
        except (AttributeError, OSError):
            pass

        # Overall usage estimate based on 1m load relative to cores
        est_usage = min(100.0, max(0.0, (load_1 / max(1, logical_cores)) * 100.0))

        # Temperature sensors from /sys/class/thermal
        temp_c: Optional[float] = None
        thermal_zones = glob.glob("/sys/class/thermal/thermal_zone*/temp")
        for tz in thermal_zones:
            try:
                val = int(Path(tz).read_text().strip())
                temp_c = val / 1000.0 if val > 1000 else float(val)
                break
            except Exception:
                continue

        # Frequency from /proc/cpuinfo or /sys/devices/system/cpu/cpu0/cpufreq
        freq_mhz: Optional[float] = None
        freq_path = Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq")
        if freq_path.is_file():
            try:
                freq_mhz = float(freq_path.read_text().strip()) / 1000.0
            except Exception:
                pass

        return CPUVitals(
            model=model,
            physical_cores=physical_cores,
            logical_cores=logical_cores,
            usage_percent_overall=round(est_usage, 1),
            usage_percent_per_core=[round(est_usage, 1)] * logical_cores,
            load_averages=[round(load_1, 2), round(load_5, 2), round(load_15, 2)],
            frequency_mhz=round(freq_mhz, 1) if freq_mhz else None,
            temperature_celsius=round(temp_c, 1) if temp_c else None,
        )

    def get_memory_vitals(self) -> MemoryVitals:
        total_kb = 0
        avail_kb = 0
        swap_total_kb = 0
        swap_free_kb = 0

        meminfo = Path("/proc/meminfo")
        if meminfo.is_file():
            try:
                for line in meminfo.read_text(encoding="utf-8").splitlines():
                    if line.startswith("MemTotal:"):
                        total_kb = int(line.split()[1])
                    elif line.startswith("MemAvailable:"):
                        avail_kb = int(line.split()[1])
                    elif line.startswith("SwapTotal:"):
                        swap_total_kb = int(line.split()[1])
                    elif line.startswith("SwapFree:"):
                        swap_free_kb = int(line.split()[1])
            except Exception:
                pass

        total_mb = total_kb / 1024.0
        avail_mb = avail_kb / 1024.0
        used_mb = max(0.0, total_mb - avail_mb)
        pct_used = (used_mb / total_mb * 100.0) if total_mb > 0 else 0.0

        swap_total_mb = swap_total_kb / 1024.0
        swap_free_mb = swap_free_kb / 1024.0
        swap_used_mb = max(0.0, swap_total_mb - swap_free_mb)
        pct_swap = (swap_used_mb / swap_total_mb * 100.0) if swap_total_mb > 0 else 0.0

        return MemoryVitals(
            total_ram_mb=round(total_mb, 1),
            available_ram_mb=round(avail_mb, 1),
            used_ram_mb=round(used_mb, 1),
            percent_used_ram=round(pct_used, 1),
            total_swap_mb=round(swap_total_mb, 1),
            free_swap_mb=round(swap_free_mb, 1),
            used_swap_mb=round(swap_used_mb, 1),
            percent_used_swap=round(pct_swap, 1),
        )

    def get_storage_partitions(self) -> List[StoragePartition]:
        partitions: List[StoragePartition] = []
        try:
            usage = shutil.disk_usage("/")
            total_gb = usage.total / (1024 ** 3)
            used_gb = usage.used / (1024 ** 3)
            free_gb = usage.free / (1024 ** 3)
            pct = (used_gb / total_gb * 100.0) if total_gb > 0 else 0.0

            partitions.append(
                StoragePartition(
                    mount_point="/",
                    device="/dev/root",
                    filesystem="ext4",
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
        power_supply_dirs = glob.glob("/sys/class/power_supply/BAT*")
        if not power_supply_dirs:
            return BatteryStatus(has_battery=False)

        bat_dir = Path(power_supply_dirs[0])
        try:
            capacity_file = bat_dir / "capacity"
            status_file = bat_dir / "status"

            pct = float(capacity_file.read_text().strip()) if capacity_file.is_file() else None
            stat = status_file.read_text().strip() if status_file.is_file() else "Unknown"
            plugged = stat in ("Charging", "Full")

            return BatteryStatus(
                has_battery=True,
                percent=pct,
                power_plugged=plugged,
                charging_status=stat,
            )
        except Exception:
            return BatteryStatus(has_battery=True, charging_status="Unknown")

    def get_system_uptime_seconds(self) -> float:
        uptime_file = Path("/proc/uptime")
        if uptime_file.is_file():
            try:
                val = float(uptime_file.read_text().split()[0])
                return round(val, 1)
            except Exception:
                pass
        return 0.0

    def list_processes(self, limit: int = 50) -> List[ProcessInfo]:
        processes: List[ProcessInfo] = []
        proc_path = Path("/proc")

        if proc_path.is_dir():
            for entry in os.listdir(proc_path):
                if not entry.isdigit():
                    continue
                pid = int(entry)
                p_dir = proc_path / entry
                try:
                    # Read process comm/name
                    comm_file = p_dir / "comm"
                    name = comm_file.read_text().strip() if comm_file.is_file() else f"proc_{pid}"

                    # Read cmdline
                    cmd_file = p_dir / "cmdline"
                    cmdline = ""
                    if cmd_file.is_file():
                        raw_cmd = cmd_file.read_bytes()
                        cmdline = " ".join(raw_cmd.decode("utf-8", errors="replace").split("\x00")).strip()
                    if not cmdline:
                        cmdline = name

                    # Read status for VmRSS memory and process relationships
                    status_file = p_dir / "status"
                    rss_kb = 0
                    state = "R"
                    uid_str = "0"
                    ppid = -1
                    if status_file.is_file():
                        for line in status_file.read_text(encoding="utf-8", errors="replace").splitlines():
                            if line.startswith("VmRSS:"):
                                parts = line.split()
                                if len(parts) > 1 and parts[1].isdigit():
                                    rss_kb = int(parts[1])
                            elif line.startswith("State:"):
                                parts = line.split()
                                if len(parts) > 1:
                                    state = parts[1]
                            elif line.startswith("Uid:"):
                                parts = line.split()
                                if len(parts) > 1:
                                    uid_str = parts[1]
                            elif line.startswith("PPid:"):
                                parts = line.split()
                                if len(parts) > 1 and parts[1].isdigit():
                                    ppid = int(parts[1])

                    # Legitimate OS metadata evaluation for protected process:
                    # 1. Core initial / scheduler PIDs
                    is_core_pid = pid in (0, 1, 2)

                    # 2. Kernel threads (spawned by kthreadd PPID 2 or named kworker/ksoftirqd/etc.)
                    is_kernel_thread = (ppid == 2) or name.startswith(("kworker", "ksoftirqd", "rcu_", "migration/", "watchdog"))

                    # 3. Known critical system daemons or systemd services
                    is_system_service = (
                        name in PROTECTED_PROCESS_NAMES
                        or name.startswith("systemd")
                    )

                    # 4. Check systemd cgroup slice if available
                    is_system_slice = False
                    cgroup_file = p_dir / "cgroup"
                    if cgroup_file.is_file():
                        try:
                            cg_content = cgroup_file.read_text(encoding="utf-8", errors="replace")
                            if "system.slice" in cg_content or "init.scope" in cg_content:
                                if uid_str.isdigit() and int(uid_str) < 1000:
                                    is_system_slice = True
                        except Exception:
                            pass

                    is_protected = bool(is_core_pid or is_kernel_thread or is_system_service or is_system_slice)

                    processes.append(
                        ProcessInfo(
                            pid=pid,
                            name=name,
                            cpu_percent=0.0,
                            memory_mb=round(rss_kb / 1024.0, 1),
                            status=state,
                            user="root" if uid_str == "0" else f"user_{uid_str}",
                            command_line=cmdline[:160],
                            is_protected=is_protected,
                        )
                    )
                except (FileNotFoundError, PermissionError, ProcessLookupError):
                    continue

        # Partition into protected system processes and user processes
        protected_list = [p for p in processes if p.is_protected]
        user_list = [p for p in processes if not p.is_protected]

        # Sort protected processes by PID (ascending) so PID 1, 2, etc. are first
        protected_list.sort(key=lambda p: p.pid)

        # Sort user processes by memory usage descending (highest memory consumers first)
        user_list.sort(key=lambda p: p.memory_mb, reverse=True)

        # Combine: always include protected processes first, then top user processes up to limit
        combined = protected_list + user_list
        return combined[:limit]

    def list_network_interfaces(self) -> List[NetworkInterfaceInfo]:
        interfaces: List[NetworkInterfaceInfo] = []
        sys_net = Path("/sys/class/net")
        if sys_net.is_dir():
            for iface in os.listdir(sys_net):
                iface_dir = sys_net / iface
                is_loop = iface == "lo"
                operstate_file = iface_dir / "operstate"
                is_up = False
                if operstate_file.is_file():
                    try:
                        is_up = operstate_file.read_text().strip() == "up"
                    except Exception:
                        pass

                mac_file = iface_dir / "address"
                mac = "00:00:00:00:00:00"
                if mac_file.is_file():
                    try:
                        mac = mac_file.read_text().strip()
                    except Exception:
                        pass

                interfaces.append(
                    NetworkInterfaceInfo(
                        name=iface,
                        ipv4_addresses=["127.0.0.1"] if is_loop else [],
                        ipv6_addresses=["::1"] if is_loop else [],
                        mac_address=mac,
                        is_up=is_up,
                        is_loopback=is_loop,
                    )
                )
        return interfaces

    def list_installed_applications(self, limit: int = 100) -> List[InstalledAppInfo]:
        apps: List[InstalledAppInfo] = []
        app_dirs = [
            Path("/usr/share/applications"),
            Path("/usr/local/share/applications"),
            Path(os.path.expanduser("~/.local/share/applications")),
        ]

        seen_names = set()

        for adir in app_dirs:
            if not adir.is_dir():
                continue
            for desktop_file in adir.glob("*.desktop"):
                try:
                    content = desktop_file.read_text(encoding="utf-8", errors="replace")
                    # Check NoDisplay
                    if "NoDisplay=true" in content:
                        continue

                    name_match = re.search(r"^Name=(.+)$", content, re.M)
                    exec_match = re.search(r"^Exec=(.+)$", content, re.M)
                    cat_match = re.search(r"^Categories=(.+)$", content, re.M)

                    if name_match and exec_match:
                        name = name_match.group(1).strip()
                        if name in seen_names:
                            continue
                        seen_names.add(name)

                        exec_cmd = exec_match.group(1).split()[0].strip()
                        cat = cat_match.group(1).strip() if cat_match else "Utility"

                        apps.append(
                            InstalledAppInfo(
                                name=name,
                                executable=exec_cmd,
                                category=cat,
                                desktop_file_path=str(desktop_file),
                            )
                        )
                        if len(apps) >= limit:
                            return apps
                except Exception:
                    continue

        return apps
