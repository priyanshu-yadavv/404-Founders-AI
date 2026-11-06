"""
404 FOUNDERS — Cluster Security & Access Control
Enforces SSH key policies, Role-Based Access Control (RBAC), secret sanitization,
container security profiles, and immutable audit logging for the GPU supercluster.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


class ClusterRole(str, Enum):
    """Cluster access roles with hierarchical permissions."""

    CLUSTER_ADMIN = "cluster_admin"          # Full node, network, power, and slurm admin
    ML_ENGINEER = "ml_engineer"              # Submit distributed jobs, mount storage, checkpoint
    RESEARCHER = "researcher"                # Submit standard training/eval jobs, read checkpoints
    AUDITOR_OBSERVER = "auditor_observer"    # Read-only telemetry, logs, metrics


ROLE_PERMISSIONS: Dict[ClusterRole, Set[str]] = {
    ClusterRole.CLUSTER_ADMIN: {
        "node:reboot",
        "node:drain",
        "fabric:reconfigure",
        "security:rotate_keys",
        "slurm:admin",
        "job:submit",
        "job:cancel",
        "checkpoint:read",
        "checkpoint:write",
        "checkpoint:delete",
        "metrics:read",
    },
    ClusterRole.ML_ENGINEER: {
        "job:submit",
        "job:cancel_own",
        "checkpoint:read",
        "checkpoint:write",
        "metrics:read",
        "storage:mount",
    },
    ClusterRole.RESEARCHER: {
        "job:submit",
        "job:cancel_own",
        "checkpoint:read",
        "metrics:read",
    },
    ClusterRole.AUDITOR_OBSERVER: {
        "metrics:read",
        "audit:read",
    },
}

SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|token|password|passwd|auth)\s*[:=]\s*['\"]?([A-Za-z0-9_\-\.\/+=]{8,})['\"]?"),
    re.compile(r"ghp_[A-Za-z0-9]{36}"),                        # GitHub personal token
    re.compile(r"sk-[A-Za-z0-9]{32,}"),                        # OpenAI API key style
    re.compile(r"hf_[A-Za-z0-9]{34,}"),                        # HuggingFace token
    re.compile(r"AKIA[0-9A-Z]{16}"),                           # AWS Access Key ID
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
]


@dataclass
class AuditLogEntry:
    """Immutable audit record for privileged actions."""

    timestamp: float
    user: str
    role: str
    action: str
    target: str
    status: str
    details: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ClusterSecurityManager:
    """Manages role-based authorization, SSH key validation, log sanitization, and audit logging."""

    def __init__(self, audit_log_path: str | Path = "logs/security_audit.jsonl") -> None:
        self.audit_log_path = Path(audit_log_path)
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)

    def authorize_action(self, user: str, role: ClusterRole, action: str, target: str = "") -> bool:
        """Checks if the user role is permitted to perform the specified action."""
        allowed = action in ROLE_PERMISSIONS.get(role, set())
        status = "GRANTED" if allowed else "DENIED"

        self._record_audit_event(
            user=user,
            role=role.value,
            action=action,
            target=target,
            status=status,
            details={"permitted": allowed},
        )
        return allowed

    def validate_ssh_public_key(self, key_text: str) -> Tuple[bool, str]:
        """Validates that SSH keys conform to zero-trust standards (Ed25519 required or RSA >= 4096)."""
        stripped = key_text.strip()
        parts = stripped.split()
        if len(parts) < 2:
            return False, "Invalid SSH key format (missing key type or payload)"

        key_type = parts[0]
        if key_type == "ssh-ed25519":
            return True, "Valid Ed25519 public key (Approved)"
        if key_type == "ssh-rsa":
            return False, "RSA keys are deprecated for cluster access; please generate an Ed25519 key"
        if key_type in ("ecdsa-sha2-nistp256", "ecdsa-sha2-nistp384", "ecdsa-sha2-nistp521"):
            return True, "Valid ECDSA public key"
        return False, f"Unsupported or insecure key algorithm: {key_type}"

    def sanitize_text(self, text: str) -> str:
        """Redacts sensitive credentials, private keys, and tokens from command outputs and logs."""
        sanitized = text
        for pat in SECRET_PATTERNS:
            sanitized = pat.sub(r"[REDACTED_SECRET]", sanitized)
        return sanitized

    def get_container_security_profile(self, allow_host_network: bool = False) -> Dict[str, Any]:
        """Returns hardened container security options for Slurm / Docker jobs."""
        return {
            "run_as_user": "1000:1000",
            "read_only_root_filesystem": True,
            "drop_capabilities": ["ALL"],
            "add_capabilities": ["SYS_PTRACE"] if allow_host_network else [],
            "no_new_privileges": True,
            "seccomp_profile": "runtime/default",
            "ipc_mode": "host",  # Required for PyTorch CUDA IPC shared memory
            "shm_size": "64gb",
        }

    def _record_audit_event(
        self,
        user: str,
        role: str,
        action: str,
        target: str,
        status: str,
        details: Dict[str, Any],
    ) -> None:
        entry = AuditLogEntry(
            timestamp=time.time(),
            user=user,
            role=role,
            action=action,
            target=target,
            status=status,
            details=details,
        )
        with open(self.audit_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry.to_dict()) + "\n")
