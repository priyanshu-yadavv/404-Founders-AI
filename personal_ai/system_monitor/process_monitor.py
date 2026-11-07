"""
404 FOUNDERS — Process Monitoring Module
Provides read-only process listing, resource consumption ranking, and anomaly detection.
STRICT INVARIANT: Read-only by default. Never terminates, modifies, or suspends
processes without explicit human approval. Protected system services can NEVER be touched.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from core.exceptions import SecurityViolationError
from personal_ai.os_adapters import BaseOSAdapter, ProcessInfo, get_os_adapter


@dataclass
class ProcessResourceAnomaly:
    """Alert for unusual or excessive resource consumption."""
    pid: int
    name: str
    anomaly_type: str  # "HIGH_CPU", "HIGH_MEMORY", "UNUSUAL_PATH"
    detail: str
    severity: str  # "LOW", "MEDIUM", "HIGH"


class ProcessMonitor:
    """Read-only process monitoring engine with safety guards for protected services."""

    def __init__(self, adapter: Optional[BaseOSAdapter] = None) -> None:
        self.adapter = adapter or get_os_adapter()

    def list_processes(self, limit: int = 50) -> List[ProcessInfo]:
        """Fetch running processes sorted by resource consumption."""
        return self.adapter.list_processes(limit=limit)

    def get_top_resource_consumers(self, top_n: int = 5) -> Dict[str, List[ProcessInfo]]:
        """Identify top memory and CPU consumers from process listing."""
        all_procs = self.adapter.list_processes(limit=100)
        sorted_by_mem = sorted(all_procs, key=lambda p: p.memory_mb, reverse=True)
        sorted_by_cpu = sorted(all_procs, key=lambda p: p.cpu_percent, reverse=True)
        return {
            "top_memory": sorted_by_mem[:top_n],
            "top_cpu": sorted_by_cpu[:top_n],
        }

    def detect_anomalies(
        self,
        mem_mb_threshold: float = 2048.0,
        cpu_threshold_pct: float = 95.0,
        mem_threshold_mb: Optional[float] = None,
    ) -> List[ProcessResourceAnomaly]:
        """Detect processes exceeding safe resource thresholds or located in suspicious paths."""
        effective_mem_limit = mem_threshold_mb if mem_threshold_mb is not None else mem_mb_threshold
        anomalies: List[ProcessResourceAnomaly] = []
        processes = self.adapter.list_processes(limit=100)

        for p in processes:
            # Memory runaway check
            if p.memory_mb > effective_mem_limit and not p.is_protected:
                anomalies.append(
                    ProcessResourceAnomaly(
                        pid=p.pid,
                        name=p.name,
                        anomaly_type="HIGH_MEMORY",
                        detail=f"Process consumes {p.memory_mb} MB (threshold: {effective_mem_limit} MB)",
                        severity="MEDIUM" if p.memory_mb < 4096 else "HIGH",
                    )
                )

            # Suspicious execution path check (e.g. running directly from /tmp or /dev/shm)
            cmd = p.command_line.lower()
            if "/tmp/" in cmd or "/dev/shm/" in cmd:
                anomalies.append(
                    ProcessResourceAnomaly(
                        pid=p.pid,
                        name=p.name,
                        anomaly_type="UNUSUAL_PATH",
                        detail=f"Process executable or argument originates from ephemeral path: {p.command_line[:60]}",
                        severity="HIGH",
                    )
                )

        return anomalies

    def validate_termination_target(self, pid: int) -> ProcessInfo:
        """
        Validate whether a process is eligible to be submitted for human approval to terminate.
        STRICT INVARIANT: Protected system processes (PID 1, init, systemd, sshd, auditd)
        can NEVER be targeted for termination.
        """
        processes = self.adapter.list_processes(limit=200)
        target = next((p for p in processes if p.pid == pid), None)
        if not target:
            raise KeyError(f"Process PID {pid} not found in running process table.")

        if target.is_protected or pid in (0, 1, 2):
            raise SecurityViolationError(
                f"Termination blocked: Process '{target.name}' (PID {pid}) is a protected system service. "
                "404 FOUNDERS strictly prohibits interfering with core system daemons.",
                required_tier="privileged",
                active_tier="blocked",
            )

        return target

    def is_process_protected(self, pid: int) -> bool:
        """Check whether a PID belongs to protected system services."""
        if pid in (0, 1, 2):
            return True
        processes = self.adapter.list_processes(limit=200)
        target = next((p for p in processes if p.pid == pid), None)
        return bool(target and target.is_protected)

    def check_termination_permission(self, pid: int) -> Dict[str, Any]:
        """Check if termination can be authorized via approval ticket."""
        if self.is_process_protected(pid):
            return {
                "permitted": False,
                "reason": f"Protected system process PID {pid} cannot be terminated under any circumstances.",
            }
        return {
            "permitted": True,
            "reason": "Process may be eligible for termination with valid operator approval ticket.",
        }
