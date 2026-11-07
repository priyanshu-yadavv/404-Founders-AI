"""
404 FOUNDERS — Permission & Approval Manager
Enforces explicit approval workflows, one-time ticket authorization,
permission expiration, risk tier validation, and least-privilege security controls.
STRICT INVARIANTS:
1. Read-only default mode.
2. The language model is NEVER the authority granting sensitive action approvals.
3. Every non-read-only action requires a specific, non-reusable, expiring approval ticket.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid

from core.exceptions import PermissionDeniedError, SecurityViolationError
from personal_ai.terminal.command_advisor import CommandRiskTier


class TicketStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CONSUMED = "CONSUMED"
    REVOKED = "REVOKED"


@dataclass
class ApprovalTicket:
    """An explicit authorization ticket for a sensitive tool operation."""
    ticket_id: str
    tool_name: str
    action_summary: str
    risk_tier: CommandRiskTier
    parameters: Dict[str, Any]
    created_at: str
    expires_at: str
    status: TicketStatus
    decision_reason: Optional[str] = None
    decided_by: Optional[str] = None


class ApprovalManager:
    """
    Approval Manager enforcing explicit human-in-the-loop authorization gates.
    Maintains ephemeral tickets, checks expiration, and guarantees single-use consumption.
    """

    DEFAULT_EXPIRATION_MINUTES = 5

    def __init__(self, expiration_minutes: int = DEFAULT_EXPIRATION_MINUTES) -> None:
        self.expiration_minutes = expiration_minutes
        self._tickets: Dict[str, ApprovalTicket] = {}

    def create_ticket(
        self,
        tool_name: str,
        action_summary: str,
        risk_tier: CommandRiskTier,
        parameters: Optional[Dict[str, Any]] = None,
        ttl_seconds: Optional[int] = None,
    ) -> ApprovalTicket:
        """Create a new pending approval ticket for an action requiring authorization."""
        t_id = f"TICK-{uuid.uuid4().hex[:12].upper()}"
        now_dt = datetime.now(timezone.utc)
        if ttl_seconds is not None:
            exp_dt = now_dt + timedelta(seconds=ttl_seconds)
        else:
            exp_dt = now_dt + timedelta(minutes=self.expiration_minutes)

        ticket = ApprovalTicket(
            ticket_id=t_id,
            tool_name=tool_name,
            action_summary=action_summary,
            risk_tier=risk_tier,
            parameters=parameters or {},
            created_at=now_dt.isoformat(),
            expires_at=exp_dt.isoformat(),
            status=TicketStatus.PENDING,
            decision_reason=None,
            decided_by=None,
        )
        self._tickets[t_id] = ticket
        return ticket

    issue_ticket = create_ticket

    def get_ticket(self, ticket_id: str) -> Optional[ApprovalTicket]:
        """Retrieve ticket state and update expired status if deadline has passed."""
        ticket = self._tickets.get(ticket_id)
        if not ticket:
            return None

        # Check expiration
        now_dt = datetime.now(timezone.utc)
        exp_dt = datetime.fromisoformat(ticket.expires_at)
        if ticket.status == TicketStatus.PENDING and now_dt > exp_dt:
            ticket.status = TicketStatus.EXPIRED

        return ticket

    def list_pending_tickets(self) -> List[ApprovalTicket]:
        """List active pending approval tickets that have not expired."""
        now_dt = datetime.now(timezone.utc)
        pending: List[ApprovalTicket] = []

        for t in self._tickets.values():
            exp_dt = datetime.fromisoformat(t.expires_at)
            if t.status == TicketStatus.PENDING:
                if now_dt > exp_dt:
                    t.status = TicketStatus.EXPIRED
                else:
                    pending.append(t)

        return sorted(pending, key=lambda t: t.created_at, reverse=True)

    def decide_ticket(
        self,
        ticket_id: str,
        approved: bool,
        decided_by: str = "human_operator",
        reason: str = "",
    ) -> ApprovalTicket:
        """Record explicit human approval or rejection decision."""
        ticket = self.get_ticket(ticket_id)
        if not ticket:
            raise KeyError(f"Approval ticket '{ticket_id}' not found.")

        if ticket.status == TicketStatus.EXPIRED:
            raise SecurityViolationError(
                f"Ticket '{ticket_id}' has expired. Expired tickets cannot be decided.",
                required_tier="protected",
                active_tier="expired_ticket",
            )

        if ticket.status != TicketStatus.PENDING:
            raise ValueError(f"Cannot decide ticket in state '{ticket.status.value}'.")

        ticket.status = TicketStatus.APPROVED if approved else TicketStatus.REJECTED
        ticket.decided_by = decided_by
        ticket.decision_reason = reason
        return ticket

    def consume_ticket(self, ticket_id: str, tool_name: Optional[str] = None) -> ApprovalTicket:
        """
        Validate and consume an approved ticket before tool execution.
        Guarantees single-use: transitions ticket to CONSUMED.
        """
        ticket = self.get_ticket(ticket_id)
        if not ticket:
            raise SecurityViolationError(
                f"Execution blocked: invalid or missing approval ticket '{ticket_id}'.",
                required_tier="protected",
                active_tier="unauthorized",
            )

        if tool_name is not None and ticket.tool_name != tool_name:
            raise SecurityViolationError(
                f"Ticket mismatch: ticket '{ticket_id}' was authorized for '{ticket.tool_name}', not '{tool_name}'.",
                required_tier="protected",
                active_tier="mismatched_ticket",
            )

        if ticket.status != TicketStatus.APPROVED:
            raise SecurityViolationError(
                f"Execution blocked: Ticket '{ticket_id}' has status {ticket.status.value}, expected APPROVED.",
                required_tier="protected",
                active_tier=ticket.status.value.lower(),
            )

        # Single-use: transition to CONSUMED
        ticket.status = TicketStatus.CONSUMED
        return ticket

    get_pending_tickets = list_pending_tickets
    record_decision = decide_ticket

    def revoke_all_pending(self, reason: str = "Emergency stop triggered") -> int:
        """Revoke all pending tickets immediately during emergency shutdown."""
        count = 0
        for t in self._tickets.values():
            if t.status == TicketStatus.PENDING:
                t.status = TicketStatus.REVOKED
                t.decision_reason = reason
                count += 1
        return count
