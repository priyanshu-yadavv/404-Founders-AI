"""
404 FOUNDERS — Database Schema & Migration Engine
Defines normalized, versioned relational schemas for the multi-layer memory system,
episodic logs, working tasks, user preferences, feedback, and audit trails.
"""

from dataclasses import dataclass
import json
import sqlite3
from typing import Any, Dict, List, Optional, Tuple


MIGRATIONS: List[Tuple[int, str, str]] = [
    (
        1,
        "Initial Multi-Layer Memory & Controlled Learning Schema",
        """
        -- Schema migrations table
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL,
            description TEXT NOT NULL
        );

        -- Multi-layer structured memory records
        CREATE TABLE IF NOT EXISTS memory_records (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            session_id TEXT,
            memory_layer TEXT NOT NULL,
            content TEXT NOT NULL,
            summary TEXT,
            importance REAL DEFAULT 0.5,
            confidence REAL DEFAULT 1.0,
            is_confirmed_by_user INTEGER DEFAULT 0,
            version INTEGER DEFAULT 1,
            parent_version_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            expires_at TEXT,
            status TEXT DEFAULT 'ACTIVE',
            metadata_json TEXT
        );

        -- Cross-memory entity and causal relationships
        CREATE TABLE IF NOT EXISTS memory_relationships (
            id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            relation_type TEXT NOT NULL,
            confidence REAL DEFAULT 1.0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (source_id) REFERENCES memory_records(id) ON DELETE CASCADE,
            FOREIGN KEY (target_id) REFERENCES memory_records(id) ON DELETE CASCADE
        );

        -- Episodic event trajectory logs
        CREATE TABLE IF NOT EXISTS episodic_events (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            session_id TEXT,
            task_id TEXT,
            event_description TEXT NOT NULL,
            context_summary TEXT,
            outcome TEXT,
            related_memory_ids_json TEXT,
            user_feedback TEXT,
            timestamp TEXT NOT NULL
        );

        -- Session & task-isolated working memory
        CREATE TABLE IF NOT EXISTS working_memory_tasks (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            task_id TEXT NOT NULL,
            task_name TEXT NOT NULL,
            active_objectives_json TEXT,
            intermediate_results_json TEXT,
            dependencies_json TEXT,
            pending_actions_json TEXT,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(session_id, task_id)
        );

        -- Inspectable and editable user preferences
        CREATE TABLE IF NOT EXISTS user_preferences (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            preference_key TEXT NOT NULL,
            preference_val TEXT NOT NULL,
            is_explicit INTEGER DEFAULT 1,
            updated_at TEXT NOT NULL,
            UNIQUE(user_id, preference_key)
        );

        -- Offline continual learning user feedback records
        CREATE TABLE IF NOT EXISTS feedback_records (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            response_id TEXT,
            task_id TEXT,
            feedback_type TEXT NOT NULL,
            rating INTEGER,
            suggested_correction TEXT,
            category TEXT,
            comment TEXT,
            status TEXT DEFAULT 'RECORDED',
            created_at TEXT NOT NULL
        );

        -- Append-only security and memory audit logs
        CREATE TABLE IF NOT EXISTS memory_audit_logs (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            session_id TEXT,
            action TEXT NOT NULL,
            memory_id TEXT,
            timestamp TEXT NOT NULL,
            details_json TEXT
        );

        -- Performance Indexes
        CREATE INDEX IF NOT EXISTS idx_mem_user_layer ON memory_records(user_id, memory_layer, status);
        CREATE INDEX IF NOT EXISTS idx_mem_expires ON memory_records(expires_at);
        CREATE INDEX IF NOT EXISTS idx_episodic_user_ts ON episodic_events(user_id, timestamp);
        CREATE INDEX IF NOT EXISTS idx_working_session_task ON working_memory_tasks(session_id, task_id);
        CREATE INDEX IF NOT EXISTS idx_pref_user ON user_preferences(user_id);
        CREATE INDEX IF NOT EXISTS idx_feedback_user_status ON feedback_records(user_id, status);
        CREATE INDEX IF NOT EXISTS idx_audit_user_action ON memory_audit_logs(user_id, action, timestamp);
        """
    )
]


def apply_migrations(conn: sqlite3.Connection) -> int:
    """Execute all unapplied schema migrations in sequence."""
    cursor = conn.cursor()
    # Check current migration level
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT, description TEXT)"
    )
    cursor.execute("SELECT version FROM schema_migrations")
    applied_versions = {row[0] for row in cursor.fetchall()}

    applied_count = 0
    for version, desc, sql in MIGRATIONS:
        if version not in applied_versions:
            cursor.executescript(sql)
            from datetime import datetime, timezone
            cursor.execute(
                "INSERT INTO schema_migrations (version, applied_at, description) VALUES (?, ?, ?)",
                (version, datetime.now(timezone.utc).isoformat(), desc),
            )
            applied_count += 1

    conn.commit()
    return applied_count
