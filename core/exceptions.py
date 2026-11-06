"""
404 FOUNDERS — Exception Hierarchy
Provides a unified, structured error taxonomy across all subsystems.
"""

from typing import Any, Dict, Optional


class FoundersBaseException(Exception):
    """Base exception for all 404 FOUNDERS errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "GENERIC_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """Serialize exception to a structured dictionary."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
        }


# Configuration & Initialization Errors
class ConfigurationError(FoundersBaseException):
    """Raised when configuration values are missing, malformed, or invalid."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, error_code="CONFIGURATION_ERROR", details=details)


# Neural Architecture & Backend Errors
class ArchitectureError(FoundersBaseException):
    """Base exception for neural network architecture violations."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, error_code="ARCHITECTURE_ERROR", details=details)


class BackendNotAvailableError(ArchitectureError):
    """Raised when requested compute backend (PyTorch/JAX/CUDA) is not installed."""

    def __init__(self, backend_name: str, details: Optional[Dict[str, Any]] = None) -> None:
        message = f"Compute backend '{backend_name}' is not installed or available in this environment."
        super().__init__(message, details=details)
        self.error_code = "BACKEND_NOT_AVAILABLE"


class ShapeMismatchError(ArchitectureError):
    """Raised when tensor shapes violate layer dimensional constraints."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, details=details)
        self.error_code = "SHAPE_MISMATCH"


# Memory Subsystem Errors
class MemorySubsystemError(FoundersBaseException):
    """Base exception for memory indexing, consolidation, and retrieval errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, error_code="MEMORY_ERROR", details=details)


class ContextWindowExceededError(MemorySubsystemError):
    """Raised when token sequence exceeds active memory window capacity."""

    def __init__(self, current_tokens: int, max_tokens: int) -> None:
        message = f"Token count ({current_tokens}) exceeds maximum memory capacity ({max_tokens})."
        super().__init__(message, details={"current_tokens": current_tokens, "max_tokens": max_tokens})
        self.error_code = "CONTEXT_WINDOW_EXCEEDED"


# Security & Permission Errors
class SecurityViolationError(FoundersBaseException):
    """Base exception for unauthorized operations, permission failures, or sandbox breaches."""

    def __init__(
        self,
        message: str,
        required_tier: str = "privileged",
        active_tier: str = "read_only",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        det = details or {}
        det.update({"required_tier": required_tier, "active_tier": active_tier})
        super().__init__(message, error_code="SECURITY_VIOLATION", details=det)


class PermissionDeniedError(SecurityViolationError):
    """Raised when an agent tool is invoked without required user or policy authorization."""

    def __init__(self, tool_name: str, required_tier: str, active_tier: str) -> None:
        message = f"Execution of tool '{tool_name}' denied. Required tier: '{required_tier}', active tier: '{active_tier}'."
        super().__init__(message, required_tier=required_tier, active_tier=active_tier)
        self.error_code = "PERMISSION_DENIED"


class PromptInjectionDetectedError(SecurityViolationError):
    """Raised when input sanitization filters detect hostile prompt injection patterns."""

    def __init__(self, pattern: str) -> None:
        message = f"Hostile prompt injection signature detected: {pattern}"
        super().__init__(message, details={"detected_pattern": pattern})
        self.error_code = "PROMPT_INJECTION_DETECTED"


# Personal AI & Agent Tool Errors
class ToolExecutionError(FoundersBaseException):
    """Raised when an internal agent tool fails during execution."""

    def __init__(self, tool_name: str, reason: str, details: Optional[Dict[str, Any]] = None) -> None:
        message = f"Tool '{tool_name}' failed during execution: {reason}"
        super().__init__(message, error_code="TOOL_EXECUTION_ERROR", details=details)


class SystemResourceExhaustedError(FoundersBaseException):
    """Raised when local memory or disk constraints are reached."""

    def __init__(self, resource: str, current: str, limit: str) -> None:
        message = f"Resource limit reached for '{resource}'. Current: {current}, Limit: {limit}."
        super().__init__(
            message,
            error_code="RESOURCE_EXHAUSTED",
            details={"resource": resource, "current": current, "limit": limit},
        )
