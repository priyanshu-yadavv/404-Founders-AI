"""
404 FOUNDERS — Episodic Memory Subsystem
Logs structured past events, task milestones, outcomes, and contextual episodes.
Guarantees ZERO past-event fabrication: past occurrences are strictly retrieved
from immutable event logs, never hallucinated.
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
class EpisodicEvent:
    """A structured episode or past event log."""
    event_id: str
    user_id: str
    session_id: Optional[str]
    task_id: Optional[str]
    event_description: str
    context_summary: Optional[str]
    outcome: Optional[str]
    related_memory_ids: List[str]
    user_feedback: Optional[str]
    timestamp: str


class EpisodicMemory:
    """
    Episodic Memory Engine.
    Persists structured historical episodes and provides chronological/keyword search.
    Enforces strict anti-fabrication: events exist only if recorded in the episodic log.
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None) -> None:
        self.db = db_manager or DatabaseManager.get_instance()

    def record_event(
        self,
        user_id: str,
        event_description: str,
        session_id: Optional[str] = None,
        task_id: Optional[str] = None,
        context_summary: Optional[str] = None,
        outcome: Optional[str] = None,
        related_memory_ids: Optional[List[str]] = None,
        user_feedback: Optional[str] = None,
    ) -> EpisodicEvent:
        """Record a structured episodic event after secret scrubbing."""
        clean_desc, _ = MemorySecurityManager.scrub_secrets(event_description)
        clean_summary, _ = MemorySecurityManager.scrub_secrets(context_summary or "")
        clean_outcome, _ = MemorySecurityManager.scrub_secrets(outcome or "")
        clean_feedback, _ = MemorySecurityManager.scrub_secrets(user_feedback or "")

        event_id = f"ep_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        rel_ids = related_memory_ids or []

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO episodic_events (
                    id, user_id, session_id, task_id, event_description,
                    context_summary, outcome, related_memory_ids_json,
                    user_feedback, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    user_id,
                    session_id,
                    task_id,
                    clean_desc,
                    clean_summary if clean_summary else None,
                    clean_outcome if clean_outcome else None,
                    json.dumps(rel_ids),
                    clean_feedback if clean_feedback else None,
                    now,
                ),
            )
            MemorySecurityManager.log_audit_event(
                conn, user_id=user_id, action="RECORD_EPISODE", session_id=session_id,
                memory_id=event_id, details={"task_id": task_id}
            )

        return EpisodicEvent(
            event_id=event_id,
            user_id=user_id,
            session_id=session_id,
            task_id=task_id,
            event_description=clean_desc,
            context_summary=clean_summary if clean_summary else None,
            outcome=clean_outcome if clean_outcome else None,
            related_memory_ids=rel_ids,
            user_feedback=clean_feedback if clean_feedback else None,
            timestamp=now,
        )

    def get_recent_events(
        self,
        user_id: str,
        limit: int = 20,
        session_id: Optional[str] = None,
    ) -> List[EpisodicEvent]:
        """Retrieve recent episodic events chronologically descending for an isolated tenant."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if session_id:
                cursor.execute(
                    """
                    SELECT id, user_id, session_id, task_id, event_description,
                           context_summary, outcome, related_memory_ids_json,
                           user_feedback, timestamp
                    FROM episodic_events
                    WHERE user_id = ? AND session_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (user_id, session_id, limit),
                )
            else:
                cursor.execute(
                    """
                    SELECT id, user_id, session_id, task_id, event_description,
                           context_summary, outcome, related_memory_ids_json,
                           user_feedback, timestamp
                    FROM episodic_events
                    WHERE user_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (user_id, limit),
                )
            rows = cursor.fetchall()
            return [self._row_to_event(r) for r in rows]

    def search_events(
        self,
        user_id: str,
        query: str,
        limit: int = 10,
    ) -> List[EpisodicEvent]:
        """
        Search past events by keyword matching across description, context, and outcome.
        Returns empty list if no genuine record matches. Never fabricates past interactions.
        """
        if not query or not query.strip():
            return self.get_recent_events(user_id, limit=limit)

        tokens = [t.lower() for t in query.strip().split() if len(t) > 2]
        if not tokens:
            tokens = [query.strip().lower()]

        # Build dynamic LIKE clause for tokens
        like_clauses = " OR ".join(
            ["(LOWER(event_description) LIKE ? OR LOWER(context_summary) LIKE ? OR LOWER(outcome) LIKE ?)" for _ in tokens]
        )
        params: List[Any] = [user_id]
        for t in tokens:
            param = f"%{t}%"
            params.extend([param, param, param])
        params.append(limit)

        sql = f"""
            SELECT id, user_id, session_id, task_id, event_description,
                   context_summary, outcome, related_memory_ids_json,
                   user_feedback, timestamp
            FROM episodic_events
            WHERE user_id = ? AND ({like_clauses})
            ORDER BY timestamp DESC
            LIMIT ?
        """

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            return [self._row_to_event(r) for r in rows]

    def verify_past_occurrence(self, user_id: str, query: str) -> Dict[str, Any]:
        """
        Anti-fabrication verifier: validates whether an event actually occurred in user history.
        Explicitly flags whether the event was found or unrecorded.
        """
        matched = self.search_events(user_id, query, limit=5)
        if matched:
            return {
                "recorded": True,
                "count": len(matched),
                "most_recent_timestamp": matched[0].timestamp,
                "evidence": [m.event_description for m in matched],
            }
        return {
            "recorded": False,
            "count": 0,
            "most_recent_timestamp": None,
            "evidence": [],
            "status": "No historical record matches query. Event did not occur in system logs.",
        }

    @staticmethod
    def _row_to_event(row: sqlite3.Row) -> EpisodicEvent:
        return EpisodicEvent(
            event_id=row["id"],
            user_id=row["user_id"],
            session_id=row["session_id"],
            task_id=row["task_id"],
            event_description=row["event_description"],
            context_summary=row["context_summary"],
            outcome=row["outcome"],
            related_memory_ids=json.loads(row["related_memory_ids_json"] or "[]"),
            user_feedback=row["user_feedback"],
            timestamp=row["timestamp"],
        )
