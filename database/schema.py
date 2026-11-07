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
    ),
    (
        2,
        "User Authentication, Sessions, Conversations, Settings and Activity Logging Schema",
        """
        -- User accounts for secure local authentication
        CREATE TABLE IF NOT EXISTS user_accounts (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            display_name TEXT,
            role TEXT DEFAULT 'USER',
            is_active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_login_at TEXT
        );

        -- Active user authenticated sessions
        CREATE TABLE IF NOT EXISTS user_sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            token_hash TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            is_revoked INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES user_accounts(id) ON DELETE CASCADE
        );

        -- Multi-turn conversation threads
        CREATE TABLE IF NOT EXISTS conversation_threads (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            mode TEXT DEFAULT 'GENERAL',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            metadata_json TEXT,
            FOREIGN KEY (user_id) REFERENCES user_accounts(id) ON DELETE CASCADE
        );

        -- Conversation messages
        CREATE TABLE IF NOT EXISTS conversation_messages (
            id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            sender TEXT NOT NULL,
            content TEXT NOT NULL,
            message_type TEXT DEFAULT 'TEXT',
            metadata_json TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (conversation_id) REFERENCES conversation_threads(id) ON DELETE CASCADE
        );

        -- User application settings and preferences
        CREATE TABLE IF NOT EXISTS user_application_settings (
            user_id TEXT PRIMARY KEY,
            theme_preference TEXT DEFAULT 'system',
            language TEXT DEFAULT 'en',
            voice_enabled INTEGER DEFAULT 0,
            tts_autoplay INTEGER DEFAULT 0,
            memory_retention_days INTEGER DEFAULT 365,
            custom_endpoint_url TEXT,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES user_accounts(id) ON DELETE CASCADE
        );

        -- Unified task and activity history log
        CREATE TABLE IF NOT EXISTS activity_log_entries (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            category TEXT NOT NULL,
            action TEXT NOT NULL,
            status TEXT NOT NULL,
            detail TEXT,
            created_at TEXT NOT NULL
        );

        -- Indexes for high-throughput queries
        CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(token_hash);
        CREATE INDEX IF NOT EXISTS idx_sessions_user_active ON user_sessions(user_id, is_revoked, expires_at);
        CREATE INDEX IF NOT EXISTS idx_threads_user ON conversation_threads(user_id, updated_at);
        CREATE INDEX IF NOT EXISTS idx_messages_conversation ON conversation_messages(conversation_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_activity_user_cat ON activity_log_entries(user_id, category, created_at);
        """
    ),
    (
        3,
        "Phase 13 Voice Biometrics, Profiles, Sessions & Proactive Settings Schema",
        """
        -- Registered voice biometric profiles (encrypted embedding storage)
        CREATE TABLE IF NOT EXISTS voice_profiles (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            profile_name TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            sample_count INTEGER DEFAULT 3,
            f0_mean_hz REAL,
            f0_std_hz REAL,
            spectral_centroid_hz REAL,
            encrypted_embedding_blob BLOB NOT NULL,
            encryption_salt TEXT NOT NULL,
            verification_threshold REAL DEFAULT 0.72,
            anti_spoofing_enabled INTEGER DEFAULT 1,
            enrolled_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES user_accounts(id) ON DELETE CASCADE
        );

        -- Active voice session state machine
        CREATE TABLE IF NOT EXISTS voice_sessions (
            session_id TEXT PRIMARY KEY,
            user_id TEXT,
            state TEXT DEFAULT 'STANDBY',
            wake_word_detected TEXT,
            verification_outcome TEXT,
            confidence REAL,
            liveness_score REAL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        -- Voice security and authentication audit ledger
        CREATE TABLE IF NOT EXISTS voice_audit_log (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            outcome TEXT NOT NULL,
            details TEXT,
            timestamp TEXT NOT NULL
        );

        -- Proactive assistance configuration
        CREATE TABLE IF NOT EXISTS proactive_settings (
            user_id TEXT PRIMARY KEY,
            enabled INTEGER DEFAULT 1,
            quiet_hours_enabled INTEGER DEFAULT 1,
            quiet_hours_start TEXT DEFAULT '22:00',
            quiet_hours_end TEXT DEFAULT '08:00',
            ram_threshold_pct REAL DEFAULT 85.0,
            cpu_threshold_pct REAL DEFAULT 80.0,
            disk_threshold_gb REAL DEFAULT 10.0,
            battery_low_threshold_pct REAL DEFAULT 20.0,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES user_accounts(id) ON DELETE CASCADE
        );

        -- Indexes for voice biometrics and audits
        CREATE INDEX IF NOT EXISTS idx_voice_profiles_user ON voice_profiles(user_id, is_active);
        CREATE INDEX IF NOT EXISTS idx_voice_audit_user ON voice_audit_log(user_id, timestamp);
        """
    ),
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
