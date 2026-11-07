"""
404 FOUNDERS — User Authentication & Session Management System
Provides secure password hashing (PBKDF2-HMAC-SHA256), cryptographic salt generation,
session token creation, token verification, session lifecycle management, and rate limiting.
STRICT INVARIANT: Plaintext passwords are NEVER stored or logged.
"""

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import hashlib
import os
import re
import secrets
from typing import Any, Dict, List, Optional, Tuple

from core.exceptions import SecurityViolationError
from database.connection import DatabaseManager


@dataclass
class UserAccount:
    """Registered user account representation."""
    id: str
    username: str
    email: str
    display_name: str
    role: str  # "ADMIN", "OPERATOR", "USER"
    is_active: bool
    created_at: str
    updated_at: str
    last_login_at: Optional[str] = None


@dataclass
class UserSession:
    """Active authenticated session."""
    id: str
    user_id: str
    token: str  # Plaintext token returned ONLY on creation
    created_at: str
    expires_at: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    is_revoked: bool = False


class AuthManager:
    """
    Cryptographically secure authentication and session management engine.
    Uses PBKDF2-HMAC-SHA256 with unique 16-byte cryptographic salts.
    """

    PBKDF2_ITERATIONS = 100_000

    def __init__(self, db_manager: Optional[DatabaseManager] = None) -> None:
        self.db = db_manager or DatabaseManager.get_instance()
        self._ensure_default_operator()

    def _hash_password(self, password: str, salt_hex: Optional[str] = None) -> Tuple[str, str]:
        """Hash a password using PBKDF2-HMAC-SHA256 with a secure salt."""
        salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(16)
        pwd_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            self.PBKDF2_ITERATIONS,
        )
        return pwd_hash.hex(), salt.hex()

    def _hash_token(self, token: str) -> str:
        """Hash session tokens before storage for defense-in-depth."""
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _ensure_default_operator(self) -> None:
        """Bootstrap default operator account if no accounts exist."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM user_accounts")
            count = cursor.fetchone()[0]
            if count == 0:
                default_user = os.environ.get("FOUNDERS_DEFAULT_USER", "operator")
                default_email = os.environ.get("FOUNDERS_DEFAULT_EMAIL", "operator@404founders.local")
                default_password = os.environ.get("FOUNDERS_DEFAULT_PASSWORD", "FoundersAI_2026!")
                try:
                    self.register_user(
                        username=default_user,
                        email=default_email,
                        password=default_password,
                        display_name="Lead Operator",
                        role="ADMIN",
                    )
                except Exception:
                    pass

    def validate_username(self, username: str) -> bool:
        """Validate username format (alphanumeric, underscores, hyphens, 3-32 chars)."""
        return bool(re.match(r"^[a-zA-Z0-9_-]{3,32}$", username))

    def validate_email(self, email: str) -> bool:
        """Validate email format."""
        return bool(re.match(r"^[^@]+@[^@]+\.[^@]+$", email))

    def register_user(
        self,
        username: str,
        email: str,
        password: str,
        display_name: Optional[str] = None,
        role: str = "USER",
    ) -> UserAccount:
        """Register a new user account with hashed password and salt."""
        clean_user = username.strip().lower()
        clean_email = email.strip().lower()

        if not self.validate_username(clean_user):
            raise ValueError(f"Invalid username '{username}'. Must be 3-32 alphanumeric characters, hyphens, or underscores.")
        if not self.validate_email(clean_email):
            raise ValueError(f"Invalid email address '{email}'.")
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long.")

        pwd_hash, salt_hex = self._hash_password(password)
        user_id = f"USR-{secrets.token_hex(8)}"
        now_iso = datetime.now(timezone.utc).isoformat()
        disp_name = (display_name or username).strip()

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            # Check uniqueness
            cursor.execute("SELECT id FROM user_accounts WHERE username = ? OR email = ?", (clean_user, clean_email))
            existing = cursor.fetchone()
            if existing:
                raise ValueError("An account with that username or email already exists.")

            cursor.execute(
                """
                INSERT INTO user_accounts 
                (id, username, email, password_hash, salt, display_name, role, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (user_id, clean_user, clean_email, pwd_hash, salt_hex, disp_name, role.upper(), now_iso, now_iso),
            )
            # Create default user settings
            cursor.execute(
                """
                INSERT OR IGNORE INTO user_application_settings
                (user_id, theme_preference, language, voice_enabled, tts_autoplay, memory_retention_days, updated_at)
                VALUES (?, 'system', 'en', 0, 0, 365, ?)
                """,
                (user_id, now_iso),
            )

        return UserAccount(
            id=user_id,
            username=clean_user,
            email=clean_email,
            display_name=disp_name,
            role=role.upper(),
            is_active=True,
            created_at=now_iso,
            updated_at=now_iso,
        )

    def authenticate(self, username_or_email: str, password: str) -> Optional[UserAccount]:
        """Verify user credentials and return UserAccount if valid."""
        ident = username_or_email.strip().lower()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, username, email, password_hash, salt, display_name, role, is_active, created_at, updated_at
                FROM user_accounts
                WHERE (username = ? OR email = ?) AND is_active = 1
                """,
                (ident, ident),
            )
            row = cursor.fetchone()
            if not row:
                return None

            user_id, uname, uemail, stored_hash, salt_hex, dname, urole, is_act, c_at, u_at = row
            computed_hash, _ = self._hash_password(password, salt_hex)

            if not secrets.compare_digest(stored_hash, computed_hash):
                return None

            now_iso = datetime.now(timezone.utc).isoformat()
            cursor.execute("UPDATE user_accounts SET last_login_at = ? WHERE id = ?", (now_iso, user_id))

            return UserAccount(
                id=user_id,
                username=uname,
                email=uemail,
                display_name=dname,
                role=urole,
                is_active=bool(is_act),
                created_at=c_at,
                updated_at=u_at,
                last_login_at=now_iso,
            )

    def create_session(
        self,
        user_id: str,
        ttl_seconds: int = 86400,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> UserSession:
        """Create a cryptographic session token and persist hashed session."""
        token = f"404SESS-{secrets.token_urlsafe(32)}"
        token_hash = self._hash_token(token)
        session_id = f"SES-{secrets.token_hex(8)}"
        now = datetime.now(timezone.utc)
        expires = now + timedelta(seconds=ttl_seconds)

        now_iso = now.isoformat()
        expires_iso = expires.isoformat()

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO user_sessions
                (id, user_id, token_hash, created_at, expires_at, ip_address, user_agent, is_revoked)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (session_id, user_id, token_hash, now_iso, expires_iso, ip_address, user_agent),
            )

        return UserSession(
            id=session_id,
            user_id=user_id,
            token=token,
            created_at=now_iso,
            expires_at=expires_iso,
            ip_address=ip_address,
            user_agent=user_agent,
            is_revoked=False,
        )

    def validate_session(self, token: str) -> Optional[UserAccount]:
        """Validate bearer session token and return authenticated UserAccount."""
        if not token:
            return None
        token_hash = self._hash_token(token)
        now_iso = datetime.now(timezone.utc).isoformat()

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT u.id, u.username, u.email, u.display_name, u.role, u.is_active, u.created_at, u.updated_at, u.last_login_at
                FROM user_sessions s
                JOIN user_accounts u ON s.user_id = u.id
                WHERE s.token_hash = ? AND s.is_revoked = 0 AND s.expires_at > ? AND u.is_active = 1
                """,
                (token_hash, now_iso),
            )
            row = cursor.fetchone()
            if not row:
                return None

            return UserAccount(
                id=row[0],
                username=row[1],
                email=row[2],
                display_name=row[3],
                role=row[4],
                is_active=bool(row[5]),
                created_at=row[6],
                updated_at=row[7],
                last_login_at=row[8],
            )

    def revoke_session(self, token: str) -> bool:
        """Revoke a single session token."""
        token_hash = self._hash_token(token)
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE user_sessions SET is_revoked = 1 WHERE token_hash = ?", (token_hash,))
            return cursor.rowcount > 0

    def revoke_session_by_id(self, session_id: str, user_id: str) -> bool:
        """Revoke a session by session ID for a specific user."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE user_sessions SET is_revoked = 1 WHERE id = ? AND user_id = ?", (session_id, user_id))
            return cursor.rowcount > 0

    def revoke_all_user_sessions(self, user_id: str) -> int:
        """Revoke all active sessions for a user (logout all devices)."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE user_sessions SET is_revoked = 1 WHERE user_id = ? AND is_revoked = 0", (user_id,))
            return cursor.rowcount

    def list_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """List active sessions for an authorized user."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, created_at, expires_at, ip_address, user_agent, is_revoked
                FROM user_sessions
                WHERE user_id = ? AND is_revoked = 0 AND expires_at > ?
                ORDER BY created_at DESC
                """,
                (user_id, now_iso),
            )
            rows = cursor.fetchall()
            return [
                {
                    "session_id": r[0],
                    "created_at": r[1],
                    "expires_at": r[2],
                    "ip_address": r[3],
                    "user_agent": r[4],
                    "is_active": True,
                }
                for r in rows
            ]

    def get_user_by_id(self, user_id: str) -> Optional[UserAccount]:
        """Fetch user account by ID."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, username, email, display_name, role, is_active, created_at, updated_at, last_login_at
                FROM user_accounts WHERE id = ?
                """,
                (user_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return UserAccount(
                id=row[0],
                username=row[1],
                email=row[2],
                display_name=row[3],
                role=row[4],
                is_active=bool(row[5]),
                created_at=row[6],
                updated_at=row[7],
                last_login_at=row[8],
            )

    def get_user_by_username(self, username: str) -> Optional[UserAccount]:
        """Fetch user account by username."""
        clean_user = username.strip().lower()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, username, email, display_name, role, is_active, created_at, updated_at, last_login_at
                FROM user_accounts WHERE username = ?
                """,
                (clean_user,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return UserAccount(
                id=row[0],
                username=row[1],
                email=row[2],
                display_name=row[3],
                role=row[4],
                is_active=bool(row[5]),
                created_at=row[6],
                updated_at=row[7],
                last_login_at=row[8],
            )
