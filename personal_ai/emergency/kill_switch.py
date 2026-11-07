"""
404 FOUNDERS — Emergency Shutdown Controller (Kill Switch)
Provides an immediate, fail-safe kill switch mechanism revoking all active
approval tickets, aborting pending operations, and placing the agent into a disabled state.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from core.exceptions import SecurityViolationError
from personal_ai.permissions.approval_manager import ApprovalManager


@dataclass
class EmergencyShutdownState:
    """Current emergency shutdown status."""
    is_active: bool
    triggered_at: Optional[str]
    triggered_by: Optional[str]
    reason: Optional[str]
    revoked_tickets_count: int


class EmergencyShutdownController:
    """
    Emergency Shutdown Controller.
    Instantly disables agent operations, revokes tickets, and prevents further tool executions.
    """

    def __init__(self, approval_manager: Optional[ApprovalManager] = None) -> None:
        self.approval_manager = approval_manager or ApprovalManager()
        self._is_shutdown = False
        self._triggered_at: Optional[str] = None
        self._triggered_by: Optional[str] = None
        self._reason: Optional[str] = None
        self._revoked_count = 0

    @property
    def is_shutdown(self) -> bool:
        return self._is_shutdown

    def trigger_emergency_shutdown(
        self,
        triggered_by: str = "human_operator",
        reason: str = "Immediate manual emergency shutdown initiated.",
    ) -> EmergencyShutdownState:
        """Trigger hard emergency stop revoking all tickets and disabling agent tools."""
        now = datetime.now(timezone.utc).isoformat()
        self._is_shutdown = True
        self._triggered_at = now
        self._triggered_by = triggered_by
        self._reason = reason

        # Revoke all pending tickets
        self._revoked_count = self.approval_manager.revoke_all_pending(reason=f"Emergency shutdown: {reason}")

        return EmergencyShutdownState(
            is_active=True,
            triggered_at=now,
            triggered_by=triggered_by,
            reason=reason,
            revoked_tickets_count=self._revoked_count,
        )

    def assert_not_shutdown(self) -> None:
        """Enforce shutdown boundary: raises SecurityViolationError if agent is shut down."""
        if self._is_shutdown:
            raise SecurityViolationError(
                f"Agent operations disabled: Emergency shutdown active since {self._triggered_at}. "
                f"Reason: '{self._reason}'. Manual operator reset required.",
                required_tier="privileged",
                active_tier="emergency_shutdown",
            )

    def reset_shutdown(self, authorized_by: str = "human_operator") -> EmergencyShutdownState:
        """Explicitly reset and re-enable the personal AI agent."""
        self._is_shutdown = False
        self._triggered_at = None
        self._triggered_by = None
        self._reason = None
        self._revoked_count = 0

        return EmergencyShutdownState(
            is_active=False,
            triggered_at=None,
            triggered_by=None,
            reason=None,
            revoked_tickets_count=0,
        )

    def get_status(self) -> EmergencyShutdownState:
        return EmergencyShutdownState(
            is_active=self._is_shutdown,
            triggered_at=self._triggered_at,
            triggered_by=self._triggered_by,
            reason=self._reason,
            revoked_tickets_count=self._revoked_count,
        )

    def trigger_shutdown(
        self,
        triggered_by: str = "human_operator",
        reason: str = "Immediate manual emergency shutdown initiated.",
    ) -> EmergencyShutdownState:
        """Alias for trigger_emergency_shutdown."""
        return self.trigger_emergency_shutdown(triggered_by=triggered_by, reason=reason)

    def reset(self, reset_by: str = "human_operator") -> EmergencyShutdownState:
        """Alias for reset_shutdown."""
        return self.reset_shutdown(authorized_by=reset_by)
