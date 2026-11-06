"""
404 FOUNDERS — Security & Permission System
Defines granular permission tiers and role-based execution constraints.
"""

from enum import IntEnum
from typing import Dict


class PermissionTier(IntEnum):
    """
    Hierarchical permission levels governing personal AI tool actions.
    Execution is strictly evaluated against the active runtime tier.
    """
    READ_ONLY = 1    # Non-destructive queries (e.g. read files, inspect cpu, view system status)
    PROTECTED = 2    # Write operations to user workspace or project directories
    PRIVILEGED = 3   # System modifications, network connections, process control
    DANGEROUS = 4    # Destructive operations (partition changes, file deletion, root commands)


TIER_NAMES: Dict[str, PermissionTier] = {
    "read_only": PermissionTier.READ_ONLY,
    "protected": PermissionTier.PROTECTED,
    "privileged": PermissionTier.PRIVILEGED,
    "dangerous": PermissionTier.DANGEROUS,
}


def parse_tier(name: str) -> PermissionTier:
    """Parse string representation into PermissionTier enum."""
    cleaned = name.strip().lower()
    if cleaned not in TIER_NAMES:
        raise ValueError(f"Invalid permission tier: '{name}'. Must be one of: {list(TIER_NAMES.keys())}")
    return TIER_NAMES[cleaned]
