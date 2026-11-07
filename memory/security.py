"""
404 FOUNDERS — Memory Security, Privacy & Secret Sanitization
Guarantees that sensitive secrets (API keys, private keys, passwords) are scrubbed,
cross-user data leakage is prevented, and memory actions are auditable.
"""

from datetime import datetime, timezone
import json
import re
import sqlite3
from typing import Any, Dict, List, Optional, Tuple
import uuid

from core.exceptions import SecurityViolationError


# Patterns identifying high-entropy secrets and authentication credentials
SECRET_PATTERNS = [
    (r"-----BEGIN (?:RSA|EC|DSA|OPENSSH|PGP) PRIVATE KEY-----[\s\S]+?-----END (?:RSA|EC|DSA|OPENSSH|PGP) PRIVATE KEY-----", "[REDACTED_PRIVATE_KEY]"),
    (r"\b(?:sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{36}|gho_[a-zA-Z0-9]{36}|glpat-[a-zA-Z0-9\-_]{20,})\b", "[REDACTED_API_TOKEN]"),
    (r"\bAKIA[0-9A-Z]{16}\b", "[REDACTED_AWS_ACCESS_KEY]"),
    (r"\bBearer\s+[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+\b", "[REDACTED_BEARER_JWT]"),
    (r"(?i)\b(?:password|passwd|secret|api_key|access_token|private_key)\s*[:=]\s*['\"][^'\"]{4,}['\"]", "[REDACTED_CREDENTIAL]"),
    (r"[a-zA-Z0-9+.\-]+://[^:\s]+:[^@\s]+@[^\s]+", "[REDACTED_CONNECTION_URI_CREDENTIALS]"),
]


class MemorySecurityManager:
    """
    Enforces memory safety, secret redaction, and audit logging.
    """

    @staticmethod
    def scrub_secrets(text: str) -> Tuple[str, List[str]]:
        """
        Scan text and replace sensitive credential strings with standardized redaction markers.
        Returns:
            (sanitized_text, list_of_detected_categories)
        """
        if not text:
            return "", []

        cleaned = text
        detected: List[str] = []

        for pattern, replacement in SECRET_PATTERNS:
            matches = re.findall(pattern, cleaned)
            if matches:
                detected.append(replacement.strip("[]"))
                cleaned = re.sub(pattern, replacement, cleaned)

        return cleaned, detected

    @staticmethod
    def validate_user_access(requested_user_id: str, record_user_id: str) -> None:
        """Enforce strict cross-user isolation. Never leak records to another user."""
        if requested_user_id != record_user_id:
            raise SecurityViolationError(
                f"Unauthorized memory access attempt across tenant boundaries. "
                f"Requester '{requested_user_id}' cannot access records of '{record_user_id}'.",
                required_tier="privileged",
                active_tier="unauthorized",
            )

    @staticmethod
    def log_audit_event(
        conn: sqlite3.Connection,
        user_id: str,
        action: str,
        session_id: Optional[str] = None,
        memory_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Record an immutable memory audit log entry in the database."""
        event_id = f"aud_{uuid.uuid4().hex[:12]}"
        timestamp = datetime.now(timezone.utc).isoformat()
        details_json = json.dumps(details or {})

        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO memory_audit_logs (id, user_id, session_id, action, memory_id, timestamp, details_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (event_id, user_id, session_id, action, memory_id, timestamp, details_json),
        )
        return event_id
