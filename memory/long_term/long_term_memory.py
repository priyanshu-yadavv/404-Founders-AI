"""
404 FOUNDERS — Long-Term Memory Subsystem
Provides persistent, versioned storage for explicitly saved user information,
project context, and long-term references with provenance tracking and duplicate detection.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import sqlite3
from typing import Any, Dict, List, Optional
import uuid

from database.connection import DatabaseManager
from memory.security import MemorySecurityManager


@dataclass
class LongTermRecord:
    """A persistent long-term memory record."""
    record_id: str
    user_id: str
    content: str
    summary: str
    importance: float
    confidence: float
    is_confirmed_by_user: bool
    version: int
    parent_version_id: Optional[str]
    source_type: str
    tags: List[str]
    created_at: str
    updated_at: str
    status: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class LongTermMemory:
    """
    Long-Term Persistent Memory Engine.
    Manages immutable versions, duplicate detection, and user-authorized updates.
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None) -> None:
        self.db = db_manager or DatabaseManager.get_instance()

    @staticmethod
    def _content_hash(text: str) -> str:
        """Compute deterministic SHA-256 hash of normalized text."""
        return hashlib.sha256(text.strip().lower().encode("utf-8")).hexdigest()

    def save_record(
        self,
        user_id: str,
        content: str,
        summary: Optional[str] = None,
        importance: float = 0.5,
        confidence: float = 1.0,
        is_confirmed_by_user: bool = False,
        source_type: str = "user_explicit",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LongTermRecord:
        """Save a new long-term record with secret scrubbing and duplicate check."""
        sanitized_content, detected_secrets = MemorySecurityManager.scrub_secrets(content)
        tag_list = tags or []
        meta = metadata or {}
        if detected_secrets:
            meta["scrubbed_secrets"] = detected_secrets

        c_hash = self._content_hash(sanitized_content)
        meta["content_hash"] = c_hash
        meta["source_type"] = source_type
        meta["tags"] = tag_list

        # Check for duplicate active record
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, user_id, content, summary, importance, confidence,
                       is_confirmed_by_user, version, parent_version_id,
                       created_at, updated_at, status, metadata_json
                FROM memory_records
                WHERE user_id = ? AND memory_layer = 'LONG_TERM' AND status = 'ACTIVE'
                """,
                (user_id,),
            )
            for row in cursor.fetchall():
                r_meta = json.loads(row["metadata_json"] or "{}")
                if r_meta.get("content_hash") == c_hash:
                    # Duplicate found: return existing record without duplicate insertion
                    return self._row_to_record(row)

            # Insert new record
            record_id = f"ltm_{uuid.uuid4().hex[:12]}"
            now = datetime.now(timezone.utc).isoformat()
            summ = summary or (sanitized_content[:120] + "..." if len(sanitized_content) > 120 else sanitized_content)

            cursor.execute(
                """
                INSERT INTO memory_records (
                    id, user_id, session_id, memory_layer, content, summary,
                    importance, confidence, is_confirmed_by_user, version,
                    parent_version_id, created_at, updated_at, status, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    user_id,
                    None,
                    "LONG_TERM",
                    sanitized_content,
                    summ,
                    importance,
                    confidence,
                    1 if is_confirmed_by_user else 0,
                    1,
                    None,
                    now,
                    now,
                    "ACTIVE",
                    json.dumps(meta),
                ),
            )
            MemorySecurityManager.log_audit_event(
                conn, user_id=user_id, action="CREATE", memory_id=record_id, details={"source_type": source_type}
            )

        return LongTermRecord(
            record_id=record_id,
            user_id=user_id,
            content=sanitized_content,
            summary=summ,
            importance=importance,
            confidence=confidence,
            is_confirmed_by_user=is_confirmed_by_user,
            version=1,
            parent_version_id=None,
            source_type=source_type,
            tags=tag_list,
            created_at=now,
            updated_at=now,
            status="ACTIVE",
            metadata=meta,
        )

    def update_record(
        self,
        user_id: str,
        record_id: str,
        new_content: Optional[str] = None,
        new_summary: Optional[str] = None,
        importance: Optional[float] = None,
        confidence: Optional[float] = None,
        is_confirmed_by_user: Optional[bool] = None,
        tags: Optional[List[str]] = None,
    ) -> LongTermRecord:
        """Update a record by creating an incremented version and archiving the prior version."""
        prior = self.get_record(user_id, record_id)
        if not prior:
            raise KeyError(f"Long-term memory record not found: {record_id}")

        content_to_use = prior.content
        if new_content is not None:
            content_to_use, _ = MemorySecurityManager.scrub_secrets(new_content)

        summary_to_use = new_summary if new_summary is not None else prior.summary
        imp_to_use = importance if importance is not None else prior.importance
        conf_to_use = confidence if confidence is not None else prior.confidence
        confirmed_to_use = is_confirmed_by_user if is_confirmed_by_user is not None else prior.is_confirmed_by_user
        tags_to_use = tags if tags is not None else prior.tags

        new_version_id = f"ltm_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        meta = dict(prior.metadata)
        meta["tags"] = tags_to_use
        meta["content_hash"] = self._content_hash(content_to_use)

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            # Archive previous record
            cursor.execute(
                "UPDATE memory_records SET status = 'ARCHIVED', updated_at = ? WHERE id = ? AND user_id = ?",
                (now, record_id, user_id),
            )
            # Insert updated record with incremented version
            cursor.execute(
                """
                INSERT INTO memory_records (
                    id, user_id, session_id, memory_layer, content, summary,
                    importance, confidence, is_confirmed_by_user, version,
                    parent_version_id, created_at, updated_at, status, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_version_id,
                    user_id,
                    None,
                    "LONG_TERM",
                    content_to_use,
                    summary_to_use,
                    imp_to_use,
                    conf_to_use,
                    1 if confirmed_to_use else 0,
                    prior.version + 1,
                    record_id,
                    prior.created_at,
                    now,
                    "ACTIVE",
                    json.dumps(meta),
                ),
            )
            MemorySecurityManager.log_audit_event(
                conn, user_id=user_id, action="UPDATE", memory_id=new_version_id, details={"prev_id": record_id}
            )

        return LongTermRecord(
            record_id=new_version_id,
            user_id=user_id,
            content=content_to_use,
            summary=summary_to_use,
            importance=imp_to_use,
            confidence=conf_to_use,
            is_confirmed_by_user=confirmed_to_use,
            version=prior.version + 1,
            parent_version_id=record_id,
            source_type=prior.source_type,
            tags=tags_to_use,
            created_at=prior.created_at,
            updated_at=now,
            status="ACTIVE",
            metadata=meta,
        )

    def get_record(self, user_id: str, record_id: str) -> Optional[LongTermRecord]:
        """Fetch a specific long-term memory record by ID with strict user validation."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, user_id, content, summary, importance, confidence,
                       is_confirmed_by_user, version, parent_version_id,
                       created_at, updated_at, status, metadata_json
                FROM memory_records
                WHERE id = ? AND user_id = ? AND memory_layer = 'LONG_TERM'
                """,
                (record_id, user_id),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_record(row)

    def delete_record(self, user_id: str, record_id: str, hard_delete: bool = False) -> bool:
        """Soft-delete (or hard-delete) a memory record."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if hard_delete:
                cursor.execute(
                    "DELETE FROM memory_records WHERE id = ? AND user_id = ? AND memory_layer = 'LONG_TERM'",
                    (record_id, user_id),
                )
            else:
                cursor.execute(
                    """
                    UPDATE memory_records
                    SET status = 'DELETED', updated_at = ?
                    WHERE id = ? AND user_id = ? AND memory_layer = 'LONG_TERM'
                    """,
                    (datetime.now(timezone.utc).isoformat(), record_id, user_id),
                )
            affected = cursor.rowcount > 0
            if affected:
                MemorySecurityManager.log_audit_event(
                    conn, user_id=user_id, action="DELETE", memory_id=record_id, details={"hard_delete": hard_delete}
                )
            return affected

    def list_records(self, user_id: str, limit: int = 50, include_archived: bool = False) -> List[LongTermRecord]:
        """List active long-term records for a user."""
        status_filter = "('ACTIVE', 'ARCHIVED')" if include_archived else "('ACTIVE')"
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"""
                SELECT id, user_id, content, summary, importance, confidence,
                       is_confirmed_by_user, version, parent_version_id,
                       created_at, updated_at, status, metadata_json
                FROM memory_records
                WHERE user_id = ? AND memory_layer = 'LONG_TERM' AND status IN {status_filter}
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            )
            rows = cursor.fetchall()
            return [self._row_to_record(r) for r in rows]

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> LongTermRecord:
        meta = json.loads(row["metadata_json"] or "{}")
        tags = meta.get("tags", [])
        source = meta.get("source_type", "user_explicit")
        return LongTermRecord(
            record_id=row["id"],
            user_id=row["user_id"],
            content=row["content"],
            summary=row["summary"] or "",
            importance=float(row["importance"]),
            confidence=float(row["confidence"]),
            is_confirmed_by_user=bool(row["is_confirmed_by_user"]),
            version=int(row["version"]),
            parent_version_id=row["parent_version_id"],
            source_type=source,
            tags=tags,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            status=row["status"],
            metadata=meta,
        )
