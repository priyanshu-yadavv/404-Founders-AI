"""
404 FOUNDERS — Agent Permission Validator
Enforces policy compliance and active permission tier checks before any tool executes.
"""

from typing import Any, Dict, Optional

from core.exceptions import PermissionDeniedError
from security.audit import SecurityAuditLogger
from security.permissions import PermissionTier, parse_tier


class PermissionValidator:
    """Validates execution privileges against active system policy."""

    def __init__(
        self,
        active_tier: str = "read_only",
        require_confirmation: bool = True,
        audit_logger: Optional[SecurityAuditLogger] = None,
    ) -> None:
        self.active_tier: PermissionTier = parse_tier(active_tier)
        self.require_confirmation = require_confirmation
        self.audit_logger = audit_logger or SecurityAuditLogger(enabled=False)

    def set_active_tier(self, tier_name: str) -> None:
        """Update active runtime permission tier."""
        self.active_tier = parse_tier(tier_name)

    def validate(
        self,
        tool_name: str,
        required_tier_str: str,
        user_confirmed: bool = False,
        call_params: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Validate whether the tool can be safely executed.
        Raises PermissionDeniedError on failure.
        """
        req_tier = parse_tier(required_tier_str)

        # 1. Tier boundary check: active tier must be >= required tier
        if self.active_tier < req_tier:
            self.audit_logger.log_event(
                event_type="ACCESS_DENIED",
                tool_name=tool_name,
                tier=required_tier_str,
                user_confirmed=user_confirmed,
                success=False,
                details={"reason": "Active tier insufficient", "params": call_params or {}},
            )
            raise PermissionDeniedError(
                tool_name=tool_name,
                required_tier=required_tier_str,
                active_tier=self.active_tier.name.lower(),
            )

        # 2. User confirmation check for protected or higher tiers
        if req_tier >= PermissionTier.PROTECTED and self.require_confirmation and not user_confirmed:
            self.audit_logger.log_event(
                event_type="CONFIRMATION_REQUIRED",
                tool_name=tool_name,
                tier=required_tier_str,
                user_confirmed=False,
                success=False,
                details={"reason": "User confirmation missing", "params": call_params or {}},
            )
            raise PermissionDeniedError(
                tool_name=tool_name,
                required_tier=f"{required_tier_str} (requires user confirmation)",
                active_tier=self.active_tier.name.lower(),
            )

        # 3. Successful validation audit
        self.audit_logger.log_event(
            event_type="ACCESS_GRANTED",
            tool_name=tool_name,
            tier=required_tier_str,
            user_confirmed=user_confirmed,
            success=True,
            details=call_params or {},
        )
        return True
