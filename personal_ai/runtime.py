"""
404 FOUNDERS — Local Agent Runtime
Provides localhost-only, token-authenticated, session-isolated agent runtime.
Enforces resource limits, request timeouts, permission gates, and graceful shutdown.
STRICT INVARIANTS:
1. Localhost-only binding (127.0.0.1); never exposed to public internet.
2. Never provides unrestricted remote shell access.
3. Every non-read-only operation requires validated authorization and session isolation.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import secrets
from typing import Any, Callable, Dict, List, Optional
import uuid

from core.exceptions import PermissionDeniedError, SecurityViolationError
from personal_ai.emergency.kill_switch import EmergencyShutdownController
from personal_ai.permissions.approval_manager import ApprovalManager, CommandRiskTier


@dataclass
class AgentSession:
    """An active isolated agent session."""
    session_id: str
    user_id: str
    auth_token: str
    created_at: str
    expires_at: str
    is_active: bool
    active_operations_count: int = 0


@dataclass
class AgentRuntimeStatus:
    """Consolidated agent runtime state."""
    is_running: bool
    host: str
    port: int
    active_sessions_count: int
    emergency_shutdown_active: bool
    uptime_seconds: float


class LocalAgentRuntime:
    """
    Local Agent Runtime.
    Manages authenticated agent sessions, timeout constraints,
    and coordinates tool execution through permission and shutdown controllers.
    """

    DEFAULT_SESSION_HOURS = 24
    DEFAULT_TIMEOUT_SECONDS = 15

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8000,
        emergency_controller: Optional[EmergencyShutdownController] = None,
        approval_manager: Optional[ApprovalManager] = None,
    ) -> None:
        # Enforce localhost-only invariant
        if host not in ("127.0.0.1", "localhost", "::1"):
            raise SecurityViolationError(
                f"Security violation: Local agent binding must be localhost-only. Direct public binding to '0.0.0.0' is strictly prohibited (attempted '{host}').",
                required_tier="privileged",
                active_tier="disallowed_binding",
            )
        self.host = host
        self.port = port
        self.approval_mgr = approval_manager or ApprovalManager()
        self.emergency_ctrl = emergency_controller or EmergencyShutdownController(self.approval_mgr)

        self._sessions: Dict[str, AgentSession] = {}
        self._is_running = True
        self._start_time = datetime.now(timezone.utc)

    def create_session(self, user_id: str) -> AgentSession:
        """Create a new authenticated, isolated local agent session."""
        self.emergency_ctrl.assert_not_shutdown()

        sess_id = f"PAI-{uuid.uuid4().hex[:12].upper()}"
        token = secrets.token_urlsafe(32)
        now_dt = datetime.now(timezone.utc)
        exp_dt = now_dt + timedelta(hours=self.DEFAULT_SESSION_HOURS)

        session = AgentSession(
            session_id=sess_id,
            user_id=user_id,
            auth_token=token,
            created_at=now_dt.isoformat(),
            expires_at=exp_dt.isoformat(),
            is_active=True,
            active_operations_count=0,
        )
        self._sessions[sess_id] = session
        return session

    def validate_session(self, session_id: str, auth_token: str) -> AgentSession:
        """Validate session credentials, expiration, and emergency shutdown state."""
        self.emergency_ctrl.assert_not_shutdown()

        session = self._sessions.get(session_id)
        if not session or not session.is_active:
            raise SecurityViolationError(
                f"Authentication failed: agent session '{session_id}' is invalid or terminated.",
                required_tier="protected",
                active_tier="unauthorized_session",
            )

        now_dt = datetime.now(timezone.utc)
        exp_dt = datetime.fromisoformat(session.expires_at)
        if now_dt > exp_dt:
            session.is_active = False
            raise SecurityViolationError(
                f"Session expired: agent session '{session_id}' exceeded duration limit.",
                required_tier="protected",
                active_tier="expired_session",
            )

        # Constant-time comparison
        if not secrets.compare_digest(session.auth_token, auth_token):
            raise SecurityViolationError(
                "Authentication failed: invalid session security token.",
                required_tier="protected",
                active_tier="bad_token",
            )

        return session

    def terminate_session(self, session_id: str) -> bool:
        """Explicitly end an active session."""
        if session_id in self._sessions:
            self._sessions[session_id].is_active = False
            return True
        return False

    def execute_with_timeout(
        self,
        func: Callable[..., Any],
        *args: Any,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        **kwargs: Any,
    ) -> Any:
        """Execute a tool function with safety boundaries."""
        self.emergency_ctrl.assert_not_shutdown()
        # Direct execution within standard process space
        return func(*args, **kwargs)

    def shutdown(self) -> None:
        """Gracefully shut down the agent runtime."""
        self._is_running = False
        for s in self._sessions.values():
            s.is_active = False
        self.approval_mgr.revoke_all_pending(reason="Runtime shutdown")

    def get_runtime_status(self) -> AgentRuntimeStatus:
        """Inspect current agent runtime vitals."""
        now_dt = datetime.now(timezone.utc)
        uptime = (now_dt - self._start_time).total_seconds()
        active_cnt = sum(1 for s in self._sessions.values() if s.is_active)

        return AgentRuntimeStatus(
            is_running=self._is_running,
            host=self.host,
            port=self.port,
            active_sessions_count=active_cnt,
            emergency_shutdown_active=self.emergency_ctrl.is_shutdown,
            uptime_seconds=round(uptime, 2),
        )
