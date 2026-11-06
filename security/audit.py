"""
404 FOUNDERS — Security Audit Logger
Maintains an immutable, append-only ledger of all agent tool invocations,
permission evaluations, and system actions.
"""

import json
import os
import time
from typing import Any, Dict, Optional


class SecurityAuditLogger:
    """Writes structured audit events to a dedicated security log."""

    def __init__(self, log_path: str = "logs/security_audit.log", enabled: bool = True) -> None:
        self.log_path = log_path
        self.enabled = enabled
        if self.enabled:
            os.makedirs(os.path.dirname(self.log_path) or ".", exist_ok=True)

    def log_event(
        self,
        event_type: str,
        tool_name: str,
        tier: str,
        user_confirmed: bool,
        success: bool,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Record a structured security event entry."""
        record: Dict[str, Any] = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "epoch_ns": time.time_ns(),
            "event_type": event_type,
            "tool_name": tool_name,
            "required_tier": tier,
            "user_confirmed": user_confirmed,
            "success": success,
            "details": details or {},
        }

        if self.enabled:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")

        return record
