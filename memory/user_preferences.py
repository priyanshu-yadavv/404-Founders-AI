"""
404 FOUNDERS — User Preference Memory Subsystem
Provides inspectable, editable, and auditable storage for user-specific preferences,
formatting styles, explanation depths, and developer environment settings.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import sqlite3
from typing import Any, Dict, List, Optional
import uuid

from database.connection import DatabaseManager
from memory.security import MemorySecurityManager


@dataclass
class UserPreference:
    """A user preference setting."""
    preference_id: str
    user_id: str
    preference_key: str
    preference_val: str
    is_explicit: bool
    updated_at: str


class UserPreferenceMemory:
    """
    User Preference Memory Engine.
    Enforces privacy, explicit user inspection, and transparent override capabilities.
    """

    DEFAULT_PREFERENCES: Dict[str, str] = {
        "communication_style": "balanced",     # "concise", "detailed", "balanced", "academic"
        "response_length": "medium",            # "short", "medium", "comprehensive"
        "technical_depth": "intermediate",      # "beginner", "intermediate", "expert"
        "code_preference": "python",            # preferred language or framework
        "explanation_mode": "step_by_step",     # "step_by_step", "direct_summary"
    }

    def __init__(self, db_manager: Optional[DatabaseManager] = None) -> None:
        self.db = db_manager or DatabaseManager.get_instance()

    def set_preference(
        self,
        user_id: str,
        preference_key: str,
        preference_val: str,
        is_explicit: bool = True,
    ) -> UserPreference:
        """Set or update a user preference after secret scrubbing."""
        clean_key, _ = MemorySecurityManager.scrub_secrets(preference_key.strip().lower())
        clean_val, _ = MemorySecurityManager.scrub_secrets(str(preference_val).strip())

        pref_id = f"pref_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO user_preferences (
                    id, user_id, preference_key, preference_val, is_explicit, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, preference_key) DO UPDATE SET
                    preference_val = excluded.preference_val,
                    is_explicit = excluded.is_explicit,
                    updated_at = excluded.updated_at
                """,
                (pref_id, user_id, clean_key, clean_val, 1 if is_explicit else 0, now),
            )
            MemorySecurityManager.log_audit_event(
                conn, user_id=user_id, action="SET_PREFERENCE",
                details={"key": clean_key, "is_explicit": is_explicit}
            )

        return UserPreference(
            preference_id=pref_id,
            user_id=user_id,
            preference_key=clean_key,
            preference_val=clean_val,
            is_explicit=is_explicit,
            updated_at=now,
        )

    def get_preference(
        self,
        user_id: str,
        preference_key: str,
        default: Optional[str] = None,
    ) -> str:
        """Get a single preference value with fallback to default settings."""
        clean_key = preference_key.strip().lower()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT preference_val FROM user_preferences WHERE user_id = ? AND preference_key = ?",
                (user_id, clean_key),
            )
            row = cursor.fetchone()
            if row:
                return row["preference_val"]

        if default is not None:
            return default
        return self.DEFAULT_PREFERENCES.get(clean_key, "")

    def get_all_preferences(self, user_id: str) -> Dict[str, str]:
        """Retrieve all preferences for a user merged with system defaults."""
        prefs = dict(self.DEFAULT_PREFERENCES)
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT preference_key, preference_val FROM user_preferences WHERE user_id = ?",
                (user_id,),
            )
            for row in cursor.fetchall():
                prefs[row["preference_key"]] = row["preference_val"]
        return prefs

    def list_preference_records(self, user_id: str) -> List[UserPreference]:
        """List raw stored preference objects for transparent user inspection."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, user_id, preference_key, preference_val, is_explicit, updated_at
                FROM user_preferences
                WHERE user_id = ?
                ORDER BY preference_key ASC
                """,
                (user_id,),
            )
            rows = cursor.fetchall()
            return [
                UserPreference(
                    preference_id=r["id"],
                    user_id=r["user_id"],
                    preference_key=r["preference_key"],
                    preference_val=r["preference_val"],
                    is_explicit=bool(r["is_explicit"]),
                    updated_at=r["updated_at"],
                )
                for r in rows
            ]

    def delete_preference(self, user_id: str, preference_key: str) -> bool:
        """Delete a user preference override, restoring default behavior."""
        clean_key = preference_key.strip().lower()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM user_preferences WHERE user_id = ? AND preference_key = ?",
                (user_id, clean_key),
            )
            deleted = cursor.rowcount > 0
            if deleted:
                MemorySecurityManager.log_audit_event(
                    conn, user_id=user_id, action="DELETE_PREFERENCE", details={"key": clean_key}
                )
            return deleted

    def clear_preferences(self, user_id: str) -> int:
        """Clear all preference records for a given user."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_preferences WHERE user_id = ?", (user_id,))
            cleared = cursor.rowcount
            MemorySecurityManager.log_audit_event(
                conn, user_id=user_id, action="CLEAR_PREFERENCES", details={"cleared_count": cleared}
            )
            return cleared
