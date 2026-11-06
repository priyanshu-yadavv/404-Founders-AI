"""
404 FOUNDERS — Security Sanitization & Injection Defense
Provides heuristic and signature-based validation for commands and user prompts.
"""

import re
from typing import List, Tuple

from core.exceptions import PromptInjectionDetectedError, SecurityViolationError

# Known high-risk command patterns that must never be executed blindly
CRITICAL_COMMAND_PATTERNS = [
    r"\brm\s+-[a-zA-Z]*[rRfF][a-zA-Z]*\s+(/|/\*|\.\.)",
    r"\bmkfs\b",
    r"\bfdisk\b",
    r"\bdd\s+if=.*of=/dev/",
    r":\(\)\s*\{\s*:\|:&\s*\};:",  # Fork bomb
    r">\s*/dev/sd[a-z]",
    r"\bchmod\s+-R\s+777\s+/",
]

# Signatures for adversarial prompt injection attempts targeting system instructions
PROMPT_INJECTION_SIGNATURES = [
    r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
    r"disregard\s+(the\s+)?system\s+prompt",
    r"reveal\s+your\s+(system\s+)?instructions",
    r"you\s+are\s+now\s+in\s+developer\s+mode",
    r"override\s+all\s+safety\s+protocols",
]


def validate_shell_command(command: str) -> None:
    """Ensure shell command does not contain catastrophic destruction patterns."""
    for pattern in CRITICAL_COMMAND_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            raise SecurityViolationError(
                f"Prohibited catastrophic shell command pattern detected: {pattern}",
                required_tier="dangerous",
                active_tier="blocked",
            )


def inspect_prompt_safety(text: str) -> Tuple[bool, List[str]]:
    """Scan incoming user prompt for hostile injection indicators."""
    detected = []
    for sig in PROMPT_INJECTION_SIGNATURES:
        if re.search(sig, text, re.IGNORECASE):
            detected.append(sig)

    if detected:
        raise PromptInjectionDetectedError(f"Matches injection signatures: {detected}")

    return True, []
