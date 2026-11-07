"""
404 FOUNDERS — Short-Term Conversational Memory
Maintains isolated, bounded multi-turn conversational context with token window limits,
automatic context summarization, and strict multi-user tenant separation.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import sqlite3
from typing import Any, Dict, List, Optional
import uuid

from database.connection import DatabaseManager
from memory.security import MemorySecurityManager


@dataclass
class ChatMessage:
    """A single conversational message turn."""
    message_id: str
    user_id: str
    session_id: str
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: str
    token_count_estimate: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class ShortTermMemory:
    """
    Short-Term Conversational Memory.
    Provides session-isolated message caching, token-budget enforcement,
    and automatic aging summarization.
    """

    MAX_SESSION_MESSAGES = 50
    TOKEN_CEILING_FOR_SUMMARIZATION = 3000

    def __init__(self, db_manager: Optional[DatabaseManager] = None) -> None:
        self.db = db_manager or DatabaseManager.get_instance()

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Rough subword token estimation (approx 4 chars per token)."""
        return max(1, len(text) // 4)

    def add_message(
        self,
        user_id: str,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ChatMessage:
        """Add a new conversational turn to short-term memory after secret scrubbing."""
        sanitized_content, detected_secrets = MemorySecurityManager.scrub_secrets(content)
        msg_id = f"msg_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        token_count = self._estimate_tokens(sanitized_content)

        meta = metadata or {}
        if detected_secrets:
            meta["scrubbed_secrets"] = detected_secrets

        record_id = f"rec_{uuid.uuid4().hex[:12]}"
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO memory_records (
                    id, user_id, session_id, memory_layer, content, summary,
                    importance, confidence, is_confirmed_by_user, version,
                    created_at, updated_at, status, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    user_id,
                    session_id,
                    "SHORT_TERM",
                    sanitized_content,
                    sanitized_content[:100],
                    0.5,
                    1.0,
                    1,
                    1,
                    now,
                    now,
                    "ACTIVE",
                    json.dumps({"role": role, "message_id": msg_id, **meta}),
                ),
            )
            MemorySecurityManager.log_audit_event(
                conn, user_id=user_id, action="CREATE", session_id=session_id, memory_id=record_id
            )

        msg = ChatMessage(
            message_id=msg_id,
            user_id=user_id,
            session_id=session_id,
            role=role,
            content=sanitized_content,
            timestamp=now,
            token_count_estimate=token_count,
            metadata=meta,
        )

        # Check and summarize if session approaches token ceiling
        self._check_and_summarize_session(user_id, session_id)
        return msg

    def get_history(
        self,
        user_id: str,
        session_id: str,
        limit: int = 20,
    ) -> List[ChatMessage]:
        """Retrieve recent conversational messages for an isolated user session."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, user_id, session_id, content, created_at, metadata_json
                FROM memory_records
                WHERE user_id = ? AND session_id = ? AND memory_layer = 'SHORT_TERM' AND status = 'ACTIVE'
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (user_id, session_id, limit),
            )
            rows = cursor.fetchall()

        messages: List[ChatMessage] = []
        for r in rows:
            meta = json.loads(r["metadata_json"] or "{}")
            role = meta.get("role", "user")
            msg_id = meta.get("message_id", r["id"])
            messages.append(
                ChatMessage(
                    message_id=msg_id,
                    user_id=r["user_id"],
                    session_id=r["session_id"],
                    role=role,
                    content=r["content"],
                    timestamp=r["created_at"],
                    token_count_estimate=self._estimate_tokens(r["content"]),
                    metadata=meta,
                )
            )
        return messages

    def get_session_token_count(self, user_id: str, session_id: str) -> int:
        """Calculate total estimated token volume in current session history."""
        msgs = self.get_history(user_id, session_id, limit=100)
        return sum(m.token_count_estimate for m in msgs)

    def _check_and_summarize_session(self, user_id: str, session_id: str) -> Optional[str]:
        """Condense oldest turns into a summary milestone if token ceiling is breached."""
        msgs = self.get_history(user_id, session_id, limit=100)
        total_tokens = sum(m.token_count_estimate for m in msgs)

        if total_tokens <= self.TOKEN_CEILING_FOR_SUMMARIZATION and len(msgs) <= self.MAX_SESSION_MESSAGES:
            return None

        # Archive oldest 50% messages and generate summary text
        num_to_archive = max(2, len(msgs) // 2)
        oldest_msgs = msgs[:num_to_archive]

        summary_snippets = [f"{m.role.capitalize()}: {m.content[:80]}" for m in oldest_msgs]
        condensed_summary = f"[Conversation Context Summary]: " + " | ".join(summary_snippets)

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            # Mark archived messages
            for m in oldest_msgs:
                cursor.execute(
                    """
                    UPDATE memory_records
                    SET status = 'ARCHIVED', updated_at = ?
                    WHERE user_id = ? AND session_id = ? AND content = ? AND memory_layer = 'SHORT_TERM'
                    """,
                    (datetime.now(timezone.utc).isoformat(), user_id, session_id, m.content),
                )

            # Insert consolidated summary record
            now = datetime.now(timezone.utc).isoformat()
            cursor.execute(
                """
                INSERT INTO memory_records (
                    id, user_id, session_id, memory_layer, content, summary,
                    importance, confidence, is_confirmed_by_user, version,
                    created_at, updated_at, status, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"sum_{uuid.uuid4().hex[:12]}",
                    user_id,
                    session_id,
                    "SHORT_TERM",
                    condensed_summary,
                    condensed_summary[:100],
                    0.8,
                    1.0,
                    1,
                    1,
                    now,
                    now,
                    "ACTIVE",
                    json.dumps({"role": "system", "is_summary": True}),
                ),
            )
            MemorySecurityManager.log_audit_event(
                conn, user_id=user_id, action="CONSOLIDATE", session_id=session_id
            )

        return condensed_summary

    def clear_session(self, user_id: str, session_id: str) -> int:
        """Explicitly clear short-term memory for a given session."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE memory_records
                SET status = 'DELETED', updated_at = ?
                WHERE user_id = ? AND session_id = ? AND memory_layer = 'SHORT_TERM' AND status != 'DELETED'
                """,
                (datetime.now(timezone.utc).isoformat(), user_id, session_id),
            )
            affected = cursor.rowcount
            MemorySecurityManager.log_audit_event(
                conn, user_id=user_id, action="CLEAR", session_id=session_id, details={"records_cleared": affected}
            )
        return affected
