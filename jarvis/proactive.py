"""
404 FOUNDERS — Proactive Assistance & System Monitoring Engine
Monitors host hardware vitals in the background, checks threshold boundaries
(RAM, CPU, disk, battery), enforces user-configured quiet hours,
and emits non-intrusive proactive advisory alerts.

STRICT INVARIANTS:
1. Zero fabrication: Alerts trigger ONLY on real operating system telemetry.
2. Quiet hours and user enablement settings are strictly respected.
3. NEVER activates the microphone or runs unauthorized background actions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time as dtime, timezone
from typing import Any, Dict, List, Optional
import uuid

from jarvis.models import ProactiveAlert
from personal_ai.system_monitor.system_info import SystemInfoProvider


@dataclass
class ProactiveConfig:
    """User-controlled configuration for proactive notifications."""
    enabled: bool = True
    quiet_hours_enabled: bool = True
    quiet_hours_start: str = "22:00"  # HH:MM
    quiet_hours_end: str = "08:00"    # HH:MM
    ram_threshold_pct: float = 85.0
    cpu_threshold_pct: float = 85.0
    disk_threshold_gb: float = 10.0
    battery_low_threshold_pct: float = 20.0
    min_alert_interval_seconds: int = 300  # 5 minutes throttling per category

    @property
    def battery_threshold_pct(self) -> float:
        return self.battery_low_threshold_pct

    @battery_threshold_pct.setter
    def battery_threshold_pct(self, val: float) -> None:
        self.battery_low_threshold_pct = val


class ProactiveAssistanceEngine:
    """
    Proactive Assistance Engine.
    Inspects real host system vitals without polling microphone audio.
    Generates structured ProactiveAlert events when metrics exceed safe thresholds.
    """

    def __init__(
        self,
        system_info_provider: Optional[SystemInfoProvider] = None,
        config: Optional[ProactiveConfig] = None,
    ) -> None:
        self.sys_info = system_info_provider or SystemInfoProvider()
        self.config = config or ProactiveConfig()
        self._last_alert_times: Dict[str, float] = {}
        self._active_alerts: List[ProactiveAlert] = []

    def is_in_quiet_hours(self, current_dt: Optional[datetime] = None) -> bool:
        """Check if current time falls within configured quiet hours."""
        if not self.config.quiet_hours_enabled:
            return False

        now = (current_dt or datetime.now()).time()
        try:
            start_parts = [int(p) for p in self.config.quiet_hours_start.split(":")]
            end_parts = [int(p) for p in self.config.quiet_hours_end.split(":")]
            start_t = dtime(start_parts[0], start_parts[1])
            end_t = dtime(end_parts[0], end_parts[1])

            if start_t <= end_t:
                return start_t <= now <= end_t
            else:  # Overnight span (e.g. 22:00 to 08:00)
                return now >= start_t or now <= end_t
        except Exception:
            return False

    is_quiet_hours = is_in_quiet_hours

    def inspect_vitals_and_generate_alerts(self) -> List[ProactiveAlert]:
        """
        Evaluate real hardware telemetry against thresholds.
        Suppresses alerts during quiet hours or when throttled by min_alert_interval.
        """
        if not self.config.enabled:
            return []

        if self.is_in_quiet_hours():
            return []

        import time
        now_epoch = time.time()
        now_iso = datetime.now(timezone.utc).isoformat()
        new_alerts: List[ProactiveAlert] = []

        try:
            summary = self.sys_info.get_system_summary()
            telemetry = self.sys_info.get_hardware_telemetry()
        except Exception:
            return []

        # 1. High Memory Check
        ram_pct = summary.memory.percent_used_ram
        if ram_pct >= self.config.ram_threshold_pct:
            if self._should_emit("MEMORY_HIGH", now_epoch):
                alert = ProactiveAlert(
                    alert_id=f"alt_{uuid.uuid4().hex[:8]}",
                    category="MEMORY_HIGH",
                    severity="HIGH" if ram_pct >= 92.0 else "MEDIUM",
                    title="Elevated RAM Utilization",
                    message=f"System RAM is at {ram_pct:.1f}% ({summary.memory.used_ram_mb:.0f} MB / {summary.memory.total_ram_mb:.0f} MB). You can ask JARVIS to review top processes.",
                    timestamp=now_iso,
                    suggested_action="Review top memory-consuming processes or close unused applications.",
                )
                new_alerts.append(alert)
                self._record_emitted("MEMORY_HIGH", now_epoch)

        # 2. High CPU Load Check
        cpu_pct = summary.cpu.usage_percent_overall
        if cpu_pct >= self.config.cpu_threshold_pct:
            if self._should_emit("CPU_HIGH", now_epoch):
                alert = ProactiveAlert(
                    alert_id=f"alt_{uuid.uuid4().hex[:8]}",
                    category="CPU_HIGH",
                    severity="HIGH" if cpu_pct >= 95.0 else "MEDIUM",
                    title="High CPU Activity",
                    message=f"CPU load is elevated at {cpu_pct:.1f}%. Ongoing tasks or builds may be consuming compute resources.",
                    timestamp=now_iso,
                    suggested_action="Check active compilation or model processes.",
                )
                new_alerts.append(alert)
                self._record_emitted("CPU_HIGH", now_epoch)

        # 3. Low Battery Check
        battery_pct = telemetry.get("battery_percent")
        if battery_pct is not None and battery_pct <= self.config.battery_low_threshold_pct:
            if self._should_emit("BATTERY_LOW", now_epoch):
                alert = ProactiveAlert(
                    alert_id=f"alt_{uuid.uuid4().hex[:8]}",
                    category="BATTERY_LOW",
                    severity="HIGH" if battery_pct <= 10.0 else "MEDIUM",
                    title="Low Battery Warning",
                    message=f"Battery level has dropped to {battery_pct}%. Consider connecting the power adapter.",
                    timestamp=now_iso,
                    suggested_action="Connect to AC power.",
                )
                new_alerts.append(alert)
                self._record_emitted("BATTERY_LOW", now_epoch)

        # 4. Low Disk Space Check
        disk_free_gb = min((p.free_gb for p in summary.storage), default=50.0)
        if disk_free_gb <= self.config.disk_threshold_gb:
            if self._should_emit("DISK_LOW", now_epoch):
                alert = ProactiveAlert(
                    alert_id=f"alt_{uuid.uuid4().hex[:8]}",
                    category="DISK_LOW",
                    severity="HIGH",
                    title="Low Disk Storage",
                    message=f"Available disk space is down to {disk_free_gb:.1f} GB. Clean up temporary files or old checkpoints.",
                    timestamp=now_iso,
                    suggested_action="Inspect storage or prune cached checkpoints.",
                )
                new_alerts.append(alert)
                self._record_emitted("DISK_LOW", now_epoch)

        self._active_alerts.extend(new_alerts)
        return new_alerts

    def get_active_alerts(self) -> List[ProactiveAlert]:
        """Return all active undismissed alerts."""
        return [a for a in self._active_alerts if not a.is_dismissed]

    def dismiss_alert(self, alert_id: str) -> bool:
        """Dismiss an alert by ID."""
        for a in self._active_alerts:
            if a.alert_id == alert_id:
                a.is_dismissed = True
                return True
        return False

    def _should_emit(self, category: str, now_epoch: float) -> bool:
        last = self._last_alert_times.get(category, 0.0)
        return (now_epoch - last) >= self.config.min_alert_interval_seconds

    def _record_emitted(self, category: str, now_epoch: float) -> None:
        self._last_alert_times[category] = now_epoch
