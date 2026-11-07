"""
404 FOUNDERS — Personal AI Audit Logging Subsystem
Records immutable audit trails for tool invocations, approval decisions,
command proposals, and emergency shutdown events.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import sqlite3
from typing import Any, Dict, List, Optional
import uuid

from database.connection import DatabaseManager
from memory.security import MemorySecurityManager


@dataclass
class AgentAuditEvent:
    """A single immutable audit ledger entry."""
    event_id: str
    user_id: str
    session_id: Optional[str]
    action: str
    tool_or_target: Optional[str]
    timestamp: str
    details: Dict[str, Any]

    @property
    def tool_name(self) -> str:
        return self.tool_or_target or self.action

    @property
    def action_description(self) -> str:
        return self.action

    @property
    def risk_tier(self) -> str:
        return self.details.get("risk_tier", "READ_ONLY")

    @property
    def success(self) -> bool:
        return self.details.get("success", True)

    @property
    def ticket_id(self) -> Optional[str]:
        return self.details.get("ticket_id")


class AgentAuditSystem:
    """Audit Logging System for Personal AI operations."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None) -> None:
        self.db = db_manager or DatabaseManager.get_instance()

    def log_event(
        self,
        user_id: str,
        action: str,
        session_id: Optional[str] = None,
        tool_or_target: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Write an immutable audit log record to database."""
        event_id = f"AUD-{uuid.uuid4().hex[:12].upper()}"
        now = datetime.now(timezone.utc).isoformat()
        clean_details = details or {}

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO memory_audit_logs (
                    id, user_id, session_id, action, memory_id, timestamp, details_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    user_id,
                    session_id,
                    action,
                    tool_or_target,
                    now,
                    json.dumps(clean_details),
                ),
            )
        return event_id

    def get_recent_events(
        self,
        user_id: str,
        limit: int = 50,
        action_filter: Optional[str] = None,
    ) -> List[AgentAuditEvent]:
        """Fetch audit log history in reverse chronological order."""
        sql = "SELECT id, user_id, session_id, action, memory_id, timestamp, details_json FROM memory_audit_logs WHERE user_id = ?"
        params: List[Any] = [user_id]

        if action_filter:
            sql += " AND action = ?"
            params.append(action_filter)

        sql += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()

        events: List[AgentAuditEvent] = []
        for r in rows:
            events.append(
                AgentAuditEvent(
                    event_id=r["id"],
                    user_id=r["user_id"],
                    session_id=r["session_id"],
                    action=r["action"],
                    tool_or_target=r["memory_id"],
                    timestamp=r["timestamp"],
                    details=json.loads(r["details_json"] or "{}"),
                )
            )
        return events

    def record_action(
        self,
        user_id: str,
        tool_name: str,
        risk_tier: str = "READ_ONLY",
        action_description: str = "",
        success: bool = True,
        ticket_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> AgentAuditEvent:
        """Helper to record an action and return an AgentAuditEvent."""
        payload = dict(details or {})
        payload.update({"risk_tier": risk_tier, "success": success, "ticket_id": ticket_id})
        event_id = self.log_event(
            user_id=user_id,
            action=action_description or tool_name,
            session_id=session_id,
            tool_or_target=tool_name,
            details=payload,
        )
        return AgentAuditEvent(
            event_id=event_id,
            user_id=user_id,
            session_id=session_id,
            action=action_description or tool_name,
            tool_or_target=tool_name,
            timestamp=datetime.now(timezone.utc).isoformat(),
            details=payload,
        )

    def get_recent_logs(self, limit: int = 50) -> List[AgentAuditEvent]:
        """Fetch audit log history in reverse chronological order."""
        sql = "SELECT id, user_id, session_id, action, memory_id, timestamp, details_json FROM memory_audit_logs ORDER BY timestamp DESC LIMIT ?"
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (limit,))
            rows = cursor.fetchall()

        events: List[AgentAuditEvent] = []
        for r in rows:
            events.append(
                AgentAuditEvent(
                    event_id=r["id"],
                    user_id=r["user_id"],
                    session_id=r["session_id"],
                    action=r["action"],
                    tool_or_target=r["memory_id"],
                    timestamp=r["timestamp"],
                    details=json.loads(r["details_json"] or "{}"),
                )
            )
        return events
