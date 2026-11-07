"""
404 FOUNDERS — User Feedback Subsystem
Captures, validates, and curates multi-dimensional user feedback
(positive/negative ratings, corrections, bug reports) for offline learning workflows.
Enforces secret scrubbing, privacy redaction, and strict data-quality gates.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
import sqlite3
from typing import Any, Dict, List, Optional
import uuid

from database.connection import DatabaseManager
from memory.security import MemorySecurityManager


class FeedbackType(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    CORRECTION = "CORRECTION"
    ERROR_REPORT = "ERROR_REPORT"


class FeedbackStatus(str, Enum):
    RECORDED = "RECORDED"
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"
    CURATED = "CURATED"
    PROCESSED = "PROCESSED"


@dataclass
class FeedbackRecord:
    """A structured feedback entry."""
    feedback_id: str
    user_id: str
    response_id: Optional[str]
    task_id: Optional[str]
    feedback_type: FeedbackType
    rating: Optional[int]  # 1 to 5 scale or -1/1
    suggested_correction: Optional[str]
    category: str
    comment: Optional[str]
    status: FeedbackStatus
    created_at: str


class FeedbackSystem:
    """
    Feedback Capture & Curation Engine.
    Stores and validates feedback without allowing direct online weight mutation.
    """

    ALLOWED_CATEGORIES = {
        "factual_accuracy",
        "code_syntax",
        "logical_reasoning",
        "hallucination",
        "formatting",
        "security",
        "tone_preference",
        "general",
    }

    def __init__(self, db_manager: Optional[DatabaseManager] = None) -> None:
        self.db = db_manager or DatabaseManager.get_instance()

    def record_feedback(
        self,
        user_id: str,
        feedback_type: FeedbackType,
        response_id: Optional[str] = None,
        task_id: Optional[str] = None,
        rating: Optional[int] = None,
        suggested_correction: Optional[str] = None,
        category: str = "general",
        comment: Optional[str] = None,
    ) -> FeedbackRecord:
        """Record user feedback after secret scrubbing."""
        clean_correction, _ = MemorySecurityManager.scrub_secrets(suggested_correction or "")
        clean_comment, _ = MemorySecurityManager.scrub_secrets(comment or "")

        cat = category.strip().lower()
        if cat not in self.ALLOWED_CATEGORIES:
            cat = "general"

        fb_type = feedback_type if isinstance(feedback_type, FeedbackType) else FeedbackType(feedback_type)
        fb_id = f"fb_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO feedback_records (
                    id, user_id, response_id, task_id, feedback_type,
                    rating, suggested_correction, category, comment, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fb_id,
                    user_id,
                    response_id,
                    task_id,
                    fb_type.value,
                    rating,
                    clean_correction if clean_correction else None,
                    cat,
                    clean_comment if clean_comment else None,
                    FeedbackStatus.RECORDED.value,
                    now,
                ),
            )
            MemorySecurityManager.log_audit_event(
                conn, user_id=user_id, action="RECORD_FEEDBACK",
                details={"feedback_id": fb_id, "type": fb_type.value, "category": cat}
            )

        return FeedbackRecord(
            feedback_id=fb_id,
            user_id=user_id,
            response_id=response_id,
            task_id=task_id,
            feedback_type=fb_type,
            rating=rating,
            suggested_correction=clean_correction if clean_correction else None,
            category=cat,
            comment=clean_comment if clean_comment else None,
            status=FeedbackStatus.RECORDED,
            created_at=now,
        )

    def validate_feedback(
        self,
        feedback_id: str,
        is_valid: bool,
        validation_notes: Optional[str] = None,
    ) -> bool:
        """Validate or reject recorded feedback for downstream training curation."""
        new_status = FeedbackStatus.VALIDATED if is_valid else FeedbackStatus.REJECTED
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE feedback_records SET status = ? WHERE id = ?",
                (new_status.value, feedback_id),
            )
            updated = cursor.rowcount > 0
            if updated:
                MemorySecurityManager.log_audit_event(
                    conn, user_id="system_validator", action="VALIDATE_FEEDBACK",
                    details={"feedback_id": feedback_id, "status": new_status.value, "notes": validation_notes}
                )
            return updated

    def curate_training_candidates(
        self,
        category: Optional[str] = None,
        limit: int = 100,
    ) -> List[FeedbackRecord]:
        """Fetch validated feedback candidates ready for offline training dataset curation."""
        query = "SELECT * FROM feedback_records WHERE status = 'VALIDATED'"
        params: List[Any] = []

        if category:
            query += " AND category = ?"
            params.append(category.lower())

        query += " ORDER BY created_at ASC LIMIT ?"
        params.append(limit)

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [self._row_to_feedback(r) for r in rows]

    def list_feedback(
        self,
        user_id: Optional[str] = None,
        status: Optional[FeedbackStatus] = None,
        limit: int = 50,
    ) -> List[FeedbackRecord]:
        """List feedback records with optional filtering."""
        query = "SELECT * FROM feedback_records WHERE 1=1"
        params: List[Any] = []

        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        if status:
            st_val = status.value if isinstance(status, FeedbackStatus) else str(status)
            query += " AND status = ?"
            params.append(st_val)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [self._row_to_feedback(r) for r in rows]

    @staticmethod
    def _row_to_feedback(row: sqlite3.Row) -> FeedbackRecord:
        return FeedbackRecord(
            feedback_id=row["id"],
            user_id=row["user_id"],
            response_id=row["response_id"],
            task_id=row["task_id"],
            feedback_type=FeedbackType(row["feedback_type"]),
            rating=row["rating"],
            suggested_correction=row["suggested_correction"],
            category=row["category"],
            comment=row["comment"],
            status=FeedbackStatus(row["status"]),
            created_at=row["created_at"],
        )
