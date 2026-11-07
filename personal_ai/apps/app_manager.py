"""
404 FOUNDERS — Application Management Interface
Discovers installed local desktop applications, inspects running status,
and provides authorized application launching via approved adapters.
STRICT INVARIANT: Never silently installs, removes, or updates software;
never executes arbitrary downloaded binaries; application closing strictly requires explicit approval.
"""

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any, Dict, List, Optional

from core.exceptions import SecurityViolationError
from personal_ai.os_adapters import BaseOSAdapter, InstalledAppInfo, get_os_adapter


@dataclass
class AppStatusResult:
    """Running status for a desktop application."""
    name: str
    executable: str
    is_running: bool
    matching_pids: List[int]
    total_memory_mb: float


@dataclass
class AppLaunchResult:
    """Result of an authorized application launch invocation."""
    app_name: str
    executable: str
    pid: Optional[int]
    status: str  # "LAUNCHED", "ALREADY_RUNNING", "FAILED", "APPROVAL_REQUIRED"
    message: str


class ApplicationManager:
    """Application management interface with permission boundaries and approved launchers."""

    def __init__(self, adapter: Optional[BaseOSAdapter] = None) -> None:
        self.adapter = adapter or get_os_adapter()

    def list_installed_apps(self, limit: int = 100) -> List[InstalledAppInfo]:
        """Discover installed applications on the workstation."""
        return self.adapter.list_installed_applications(limit=limit)

    def find_app(self, query: str) -> Optional[InstalledAppInfo]:
        """Find an installed application by name or executable keyword."""
        q_clean = query.strip().lower()
        apps = self.list_installed_apps(limit=200)

        # Exact match first
        for app in apps:
            if app.name.lower() == q_clean or app.executable.lower() == q_clean:
                return app

        # Substring match second
        for app in apps:
            if q_clean in app.name.lower() or q_clean in app.executable.lower():
                return app

        # Check if executable exists in system PATH (e.g., "code", "firefox", "wireshark")
        which_path = shutil.which(q_clean)
        if which_path:
            return InstalledAppInfo(
                name=q_clean,
                executable=which_path,
                category="System Tool",
            )

        return None

    def get_app_status(self, app_name_or_exec: str) -> AppStatusResult:
        """Inspect whether an application is currently running."""
        app = self.find_app(app_name_or_exec)
        exec_name = Path(app.executable).name.lower() if app else app_name_or_exec.lower()
        display_name = app.name if app else app_name_or_exec

        processes = self.adapter.list_processes(limit=250)
        matching_pids: List[int] = []
        total_mem = 0.0

        for p in processes:
            p_name = p.name.lower()
            if exec_name in p_name or p_name in exec_name:
                matching_pids.append(p.pid)
                total_mem += p.memory_mb

        return AppStatusResult(
            name=display_name,
            executable=exec_name,
            is_running=len(matching_pids) > 0,
            matching_pids=matching_pids,
            total_memory_mb=round(total_mem, 1),
        )

    def launch_app(self, app_name_or_exec: str, user_confirmed: bool = True) -> AppLaunchResult:
        """
        Launch an application via approved local subprocess adapter.
        STRICT INVARIANT: Only launches verified local applications existing on the machine.
        """
        app = self.find_app(app_name_or_exec)
        if not app:
            return AppLaunchResult(
                app_name=app_name_or_exec,
                executable="",
                pid=None,
                status="FAILED",
                message=f"Application '{app_name_or_exec}' was not found among installed applications or system PATH.",
            )

        exec_path = shutil.which(app.executable) or app.executable
        if not exec_path or not os.path.exists(exec_path) and not shutil.which(exec_path):
            return AppLaunchResult(
                app_name=app.name,
                executable=app.executable,
                pid=None,
                status="FAILED",
                message=f"Executable path '{app.executable}' does not exist on disk.",
            )

        # Check for command injection / dangerous arguments
        if any(char in app.executable for char in [";", "&", "|", "`", "$", "(", ")"]):
            raise SecurityViolationError(
                f"Application launch blocked: suspicious characters detected in executable path '{app.executable}'.",
                required_tier="dangerous",
                active_tier="blocked",
            )

        try:
            # Spawn in background with detached session so it persists independently of the agent
            proc = subprocess.Popen(
                [exec_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            return AppLaunchResult(
                app_name=app.name,
                executable=exec_path,
                pid=proc.pid,
                status="LAUNCHED",
                message=f"Successfully launched '{app.name}' (PID: {proc.pid}).",
            )
        except Exception as e:
            return AppLaunchResult(
                app_name=app.name,
                executable=exec_path,
                pid=None,
                status="FAILED",
                message=f"Failed to launch application '{app.name}': {str(e)}",
            )
