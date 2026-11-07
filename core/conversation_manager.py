"""
404 FOUNDERS — Conversation, Activity, and Application Settings Manager
Coordinates durable multi-turn conversation threads, message histories,
user UI/theme settings, and unified activity event logging.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import json
import secrets
from typing import Any, Dict, List, Optional

from database.connection import DatabaseManager


@dataclass
class ConversationThread:
    """Multi-turn conversation thread."""
    id: str
    user_id: str
    title: str
    mode: str
    created_at: str
    updated_at: str
    metadata: Dict[str, Any]


@dataclass
class ConversationMessage:
    """Individual message within a conversation thread."""
    id: str
    conversation_id: str
    sender: str  # "user" or "assistant"
    content: str
    message_type: str  # "TEXT", "CODE", "MULTIMODAL", "SYSTEM"
    metadata: Dict[str, Any]
    created_at: str


@dataclass
class UserSettings:
    """User appearance, voice, and application preferences."""
    user_id: str
    theme_preference: str  # "light", "dark", "system"
    language: str
    voice_enabled: bool
    tts_autoplay: bool
    memory_retention_days: int
    custom_endpoint_url: Optional[str]
    updated_at: str


@dataclass
class ActivityLogEntry:
    """Audit and operational event in the activity history."""
    id: str
    user_id: str
    category: str  # "INTELLIGENCE", "PERSONAL_AI", "CODING", "SECURITY", "LEARNING", "AUTH"
    action: str
    status: str  # "SUCCESS", "PENDING", "FAILED", "BLOCKED"
    detail: Optional[str]
    created_at: str


class ConversationManager:
    """Manages persistent conversation threads and message trajectories."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None) -> None:
        self.db = db_manager or DatabaseManager.get_instance()

    def _resolve_user_id(self, user_id: str) -> str:
        """Resolve user_id (whether UUID or username) to a valid user_accounts.id."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM user_accounts WHERE id = ? OR username = ?", (user_id, user_id.lower()))
            row = cursor.fetchone()
            if row:
                return row[0]
            # Ensure an account entry exists for the user_id to satisfy foreign key
            u_id = f"USR-{secrets.token_hex(8)}"
            now_iso = datetime.now(timezone.utc).isoformat()
            cursor.execute(
                """
                INSERT OR IGNORE INTO user_accounts 
                (id, username, email, password_hash, salt, display_name, role, is_active, created_at, updated_at)
                VALUES (?, ?, ?, '', '', ?, 'USER', 1, ?, ?)
                """,
                (u_id, user_id.lower(), f"{user_id.lower()}@404founders.local", user_id, now_iso, now_iso),
            )
            cursor.execute("SELECT id FROM user_accounts WHERE username = ?", (user_id.lower(),))
            row = cursor.fetchone()
            return row[0] if row else user_id

    def create_thread(
        self,
        user_id: str,
        title: str = "New Conversation",
        mode: str = "GENERAL",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ConversationThread:
        """Create a new conversation thread for a user."""
        resolved_uid = self._resolve_user_id(user_id)
        thread_id = f"THRD-{secrets.token_hex(8)}"
        now_iso = datetime.now(timezone.utc).isoformat()
        meta_json = json.dumps(metadata or {})

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO conversation_threads
                (id, user_id, title, mode, created_at, updated_at, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (thread_id, resolved_uid, title.strip(), mode.upper(), now_iso, now_iso, meta_json),
            )

        return ConversationThread(
            id=thread_id,
            user_id=resolved_uid,
            title=title.strip(),
            mode=mode.upper(),
            created_at=now_iso,
            updated_at=now_iso,
            metadata=metadata or {},
        )

    def list_threads(self, user_id: str, limit: int = 50, offset: int = 0) -> List[ConversationThread]:
        """Fetch all conversation threads for a user ordered by last update."""
        resolved_uid = self._resolve_user_id(user_id)
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, user_id, title, mode, created_at, updated_at, metadata_json
                FROM conversation_threads
                WHERE user_id = ?
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
                """,
                (resolved_uid, limit, offset),
            )
            rows = cursor.fetchall()
            return [
                ConversationThread(
                    id=r[0],
                    user_id=r[1],
                    title=r[2],
                    mode=r[3],
                    created_at=r[4],
                    updated_at=r[5],
                    metadata=json.loads(r[6] or "{}"),
                )
                for r in rows
            ]

    def get_thread(self, thread_id: str, user_id: str) -> Optional[ConversationThread]:
        """Fetch a specific thread ensuring tenant boundary isolation."""
        resolved_uid = self._resolve_user_id(user_id)
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, user_id, title, mode, created_at, updated_at, metadata_json
                FROM conversation_threads
                WHERE id = ? AND user_id = ?
                """,
                (thread_id, resolved_uid),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return ConversationThread(
                id=row[0],
                user_id=row[1],
                title=row[2],
                mode=row[3],
                created_at=row[4],
                updated_at=row[5],
                metadata=json.loads(row[6] or "{}"),
            )

    def add_message(
        self,
        conversation_id: str,
        sender: str,
        content: str,
        message_type: str = "TEXT",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ConversationMessage:
        """Append a message to a thread and update thread timestamp."""
        msg_id = f"MSG-{secrets.token_hex(8)}"
        now_iso = datetime.now(timezone.utc).isoformat()
        meta_json = json.dumps(metadata or {})

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO conversation_messages
                (id, conversation_id, sender, content, message_type, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (msg_id, conversation_id, sender.lower(), content, message_type.upper(), meta_json, now_iso),
            )
            cursor.execute(
                "UPDATE conversation_threads SET updated_at = ? WHERE id = ?",
                (now_iso, conversation_id),
            )

        return ConversationMessage(
            id=msg_id,
            conversation_id=conversation_id,
            sender=sender.lower(),
            content=content,
            message_type=message_type.upper(),
            metadata=metadata or {},
            created_at=now_iso,
        )

    def list_messages(self, conversation_id: str, limit: int = 100, offset: int = 0) -> List[ConversationMessage]:
        """Fetch chronologically ordered messages in a thread."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, conversation_id, sender, content, message_type, metadata_json, created_at
                FROM conversation_messages
                WHERE conversation_id = ?
                ORDER BY created_at ASC
                LIMIT ? OFFSET ?
                """,
                (conversation_id, limit, offset),
            )
            rows = cursor.fetchall()
            return [
                ConversationMessage(
                    id=r[0],
                    conversation_id=r[1],
                    sender=r[2],
                    content=r[3],
                    message_type=r[4],
                    metadata=json.loads(r[5] or "{}"),
                    created_at=r[6],
                )
                for r in rows
            ]

    def update_thread(
        self,
        thread_id: str,
        user_id: str,
        title: Optional[str] = None,
        mode: Optional[str] = None,
    ) -> bool:
        """Update thread metadata."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if title is not None and mode is not None:
                cursor.execute(
                    "UPDATE conversation_threads SET title = ?, mode = ?, updated_at = ? WHERE id = ? AND user_id = ?",
                    (title.strip(), mode.upper(), now_iso, thread_id, user_id),
                )
            elif title is not None:
                cursor.execute(
                    "UPDATE conversation_threads SET title = ?, updated_at = ? WHERE id = ? AND user_id = ?",
                    (title.strip(), now_iso, thread_id, user_id),
                )
            elif mode is not None:
                cursor.execute(
                    "UPDATE conversation_threads SET mode = ?, updated_at = ? WHERE id = ? AND user_id = ?",
                    (mode.upper(), now_iso, thread_id, user_id),
                )
            return cursor.rowcount > 0

    def delete_thread(self, thread_id: str, user_id: str) -> bool:
        """Delete thread and its associated messages."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM conversation_messages WHERE conversation_id = ?", (thread_id,))
            cursor.execute("DELETE FROM conversation_threads WHERE id = ? AND user_id = ?", (thread_id, user_id))
            return cursor.rowcount > 0


class UserSettingsManager:
    """Manages application settings, themes, and personal AI configuration."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None) -> None:
        self.db = db_manager or DatabaseManager.get_instance()

    def _resolve_user_id(self, user_id: str) -> str:
        """Resolve user_id (whether UUID or username) to a valid user_accounts.id."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM user_accounts WHERE id = ? OR username = ?", (user_id, user_id.lower()))
            row = cursor.fetchone()
            if row:
                return row[0]
            u_id = f"USR-{secrets.token_hex(8)}"
            now_iso = datetime.now(timezone.utc).isoformat()
            cursor.execute(
                """
                INSERT OR IGNORE INTO user_accounts 
                (id, username, email, password_hash, salt, display_name, role, is_active, created_at, updated_at)
                VALUES (?, ?, ?, '', '', ?, 'USER', 1, ?, ?)
                """,
                (u_id, user_id.lower(), f"{user_id.lower()}@404founders.local", user_id, now_iso, now_iso),
            )
            cursor.execute("SELECT id FROM user_accounts WHERE username = ?", (user_id.lower(),))
            row = cursor.fetchone()
            return row[0] if row else user_id

    def get_settings(self, user_id: str) -> UserSettings:
        """Retrieve settings for user, creating defaults if not yet present."""
        resolved_uid = self._resolve_user_id(user_id)
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT theme_preference, language, voice_enabled, tts_autoplay, memory_retention_days, custom_endpoint_url, updated_at
                FROM user_application_settings
                WHERE user_id = ?
                """,
                (resolved_uid,),
            )
            row = cursor.fetchone()
            if not row:
                now_iso = datetime.now(timezone.utc).isoformat()
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO user_application_settings
                    (user_id, theme_preference, language, voice_enabled, tts_autoplay, memory_retention_days, updated_at)
                    VALUES (?, 'system', 'en', 0, 0, 365, ?)
                    """,
                    (resolved_uid, now_iso),
                )
                return UserSettings(
                    user_id=resolved_uid,
                    theme_preference="system",
                    language="en",
                    voice_enabled=False,
                    tts_autoplay=False,
                    memory_retention_days=365,
                    custom_endpoint_url=None,
                    updated_at=now_iso,
                )

            return UserSettings(
                user_id=resolved_uid,
                theme_preference=row[0] or "system",
                language=row[1] or "en",
                voice_enabled=bool(row[2]),
                tts_autoplay=bool(row[3]),
                memory_retention_days=row[4] or 365,
                custom_endpoint_url=row[5],
                updated_at=row[6],
            )

    def update_settings(
        self,
        user_id: str,
        theme_preference: Optional[str] = None,
        language: Optional[str] = None,
        voice_enabled: Optional[bool] = None,
        tts_autoplay: Optional[bool] = None,
        memory_retention_days: Optional[int] = None,
        custom_endpoint_url: Optional[str] = None,
    ) -> UserSettings:
        """Update one or more settings fields."""
        resolved_uid = self._resolve_user_id(user_id)
        curr = self.get_settings(resolved_uid)
        new_theme = theme_preference if theme_preference is not None else curr.theme_preference
        new_lang = language if language is not None else curr.language
        new_voice = voice_enabled if voice_enabled is not None else curr.voice_enabled
        new_tts = tts_autoplay if tts_autoplay is not None else curr.tts_autoplay
        new_ret = memory_retention_days if memory_retention_days is not None else curr.memory_retention_days
        new_ep = custom_endpoint_url if custom_endpoint_url is not None else curr.custom_endpoint_url
        now_iso = datetime.now(timezone.utc).isoformat()

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO user_application_settings
                (user_id, theme_preference, language, voice_enabled, tts_autoplay, memory_retention_days, custom_endpoint_url, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    theme_preference = excluded.theme_preference,
                    language = excluded.language,
                    voice_enabled = excluded.voice_enabled,
                    tts_autoplay = excluded.tts_autoplay,
                    memory_retention_days = excluded.memory_retention_days,
                    custom_endpoint_url = excluded.custom_endpoint_url,
                    updated_at = excluded.updated_at
                """,
                (resolved_uid, new_theme, new_lang, int(new_voice), int(new_tts), new_ret, new_ep, now_iso),
            )

        return UserSettings(
            user_id=resolved_uid,
            theme_preference=new_theme,
            language=new_lang,
            voice_enabled=new_voice,
            tts_autoplay=new_tts,
            memory_retention_days=new_ret,
            custom_endpoint_url=new_ep,
            updated_at=now_iso,
        )


class ActivityLogManager:
    """Manages activity and audit logs for task and history views."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None) -> None:
        self.db = db_manager or DatabaseManager.get_instance()

    def log_activity(
        self,
        user_id: str,
        category: str,
        action: str,
        status: str = "SUCCESS",
        detail: Optional[str] = None,
    ) -> ActivityLogEntry:
        """Record an activity event."""
        event_id = f"ACT-{secrets.token_hex(8)}"
        now_iso = datetime.now(timezone.utc).isoformat()

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO activity_log_entries
                (id, user_id, category, action, status, detail, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (event_id, user_id, category.upper(), action, status.upper(), detail, now_iso),
            )

        return ActivityLogEntry(
            id=event_id,
            user_id=user_id,
            category=category.upper(),
            action=action,
            status=status.upper(),
            detail=detail,
            created_at=now_iso,
        )

    def list_activity(
        self,
        user_id: str,
        category: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ActivityLogEntry]:
        """Fetch activity logs for a user, optionally filtered by category."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if category:
                cursor.execute(
                    """
                    SELECT id, user_id, category, action, status, detail, created_at
                    FROM activity_log_entries
                    WHERE user_id = ? AND category = ?
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (user_id, category.upper(), limit, offset),
                )
            else:
                cursor.execute(
                    """
                    SELECT id, user_id, category, action, status, detail, created_at
                    FROM activity_log_entries
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (user_id, limit, offset),
                )
            rows = cursor.fetchall()
            return [
                ActivityLogEntry(
                    id=r[0],
                    user_id=r[1],
                    category=r[2],
                    action=r[3],
                    status=r[4],
                    detail=r[5],
                    created_at=r[6],
                )
                for r in rows
            ]
