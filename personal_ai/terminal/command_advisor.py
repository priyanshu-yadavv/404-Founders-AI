"""
404 FOUNDERS — Safe Terminal Command Advisor
Understands user intents, formulates verified shell commands, explains operations and risks,
classifies risk tiers, and enforces human approval gates before execution.
STRICT INVARIANTS:
1. Never provides an unrestricted shell execution tool to language models.
2. Zero automatic execution of generated shell commands.
3. Classifies commands into READ_ONLY, LOW_RISK, SENSITIVE, DESTRUCTIVE, PRIVILEGED.
4. Enforces strict blocklists against fork bombs, raw disk writes, and remote piping.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import re
import shlex
from typing import Any, Dict, List, Optional, Tuple

from core.exceptions import SecurityViolationError


class CommandRiskTier(str, Enum):
    """Categorization of command operational and security risk."""
    READ_ONLY = "READ_ONLY"        # Non-modifying queries (ls, cat, df, free, uptime, git status)
    LOW_RISK = "LOW_RISK"          # Benign workspace creations (mkdir, touch, pwd, git diff)
    SENSITIVE = "SENSITIVE"        # Modifications to workspace files, git checkout, package installs
    DESTRUCTIVE = "DESTRUCTIVE"    # Deletion of files, directories, git reset --hard, rm
    PRIVILEGED = "PRIVILEGED"      # sudo, systemctl, chmod, chown, useradd, iptables, fdisk


@dataclass
class CommandAdvisoryReport:
    """Comprehensive analysis report for a proposed command."""
    user_intent: str
    proposed_command: str
    command_tokens: List[str]
    binary_name: str
    explanation: str
    potential_risks: List[str]
    risk_tier: CommandRiskTier
    requires_approval: bool
    is_blocked: bool
    block_reason: Optional[str] = None


# Dangerous command patterns that are permanently blocked regardless of approval
BLOCKED_PATTERNS = [
    (r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:", "Fork bomb attempt detected"),
    (r">\s*/dev/(?:sd[a-z]|nvme[0-9]n[0-9]|hd[a-z])", "Direct raw block device write attempted"),
    (r"(?:curl|wget)\s+[^\n|]+\|\s*(?:bash|sh|zsh|python|perl)", "Piping untrusted remote network script into interpreter"),
    (r"rm\s+-[rRfF]*\s+/(?:\s|$|\*)", "Root directory recursive deletion attempted"),
    (r"mkfs(?:\.[a-z0-9]+)?\s+", "Filesystem creation/formatting attempted"),
    (r"dd\s+if=[^\s]+\s+of=/dev/", "Raw disk block overwrite attempted"),
    (r"chmod\s+-[rRfF]*\s+777\s+/", "Universal world-writable permissions on system root"),
]

# Command binaries categorized by default risk
READ_ONLY_BINARIES = {
    "ls", "dir", "cat", "more", "less", "head", "tail", "grep", "find",
    "df", "du", "free", "uptime", "uname", "whoami", "id", "pwd", "date",
    "ps", "top", "htop", "ss", "netstat", "ip", "ifconfig", "ping", "traceroute",
    "git", "python", "python3", "pytest", "env", "echo"
}

LOW_RISK_BINARIES = {
    "mkdir", "touch", "cp", "tree", "wc", "sort", "uniq", "diff", "stat"
}

SENSITIVE_BINARIES = {
    "mv", "sed", "awk", "tar", "zip", "unzip", "gzip", "pip", "npm", "cargo"
}

DESTRUCTIVE_BINARIES = {
    "rm", "rmdir", "shred", "truncate", "kill", "killall", "pkill"
}

PRIVILEGED_BINARIES = {
    "sudo", "su", "systemctl", "service", "chmod", "chown", "chgrp",
    "useradd", "usermod", "userdel", "groupadd", "passwd", "iptables",
    "ufw", "nft", "mount", "umount", "fdisk", "parted", "reboot", "shutdown",
    "poweroff", "insmod", "rmmod", "modprobe"
}


class TerminalCommandAdvisor:
    """Safe command-advisory system advising human operators without auto-execution."""

    def advise(self, user_intent: str, proposed_command: str) -> CommandAdvisoryReport:
        """
        Analyze a proposed command, generate an explanation, assess risks,
        and assign a strict risk tier requiring approval for anything beyond READ_ONLY.
        """
        cmd_clean = proposed_command.strip()
        if not cmd_clean:
            raise ValueError("Proposed command cannot be empty.")

        # 1. Check against permanent blocklist
        for pattern, reason in BLOCKED_PATTERNS:
            if re.search(pattern, cmd_clean):
                return CommandAdvisoryReport(
                    user_intent=user_intent,
                    proposed_command=cmd_clean,
                    command_tokens=[],
                    binary_name="",
                    explanation="This command is classified as inherently hazardous and has been blocked by policy.",
                    potential_risks=[reason],
                    risk_tier=CommandRiskTier.PRIVILEGED,
                    requires_approval=True,
                    is_blocked=True,
                    block_reason=reason,
                )

        # 2. Tokenize command safely
        try:
            tokens = shlex.split(cmd_clean)
        except Exception:
            tokens = cmd_clean.split()

        binary = Path(tokens[0]).name.lower() if tokens else ""

        # 3. Classify risk tier
        risk_tier, risks = self._classify_risk(cmd_clean, tokens, binary)

        # 4. Generate structured explanation
        explanation = self._explain_command(binary, tokens)

        # 5. Invariant: READ_ONLY does not require explicit ticket approval; all other tiers DO
        requires_approval = risk_tier != CommandRiskTier.READ_ONLY

        return CommandAdvisoryReport(
            user_intent=user_intent,
            proposed_command=cmd_clean,
            command_tokens=tokens,
            binary_name=binary,
            explanation=explanation,
            potential_risks=risks,
            risk_tier=risk_tier,
            requires_approval=requires_approval,
            is_blocked=False,
            block_reason=None,
        )

    def analyze_command(self, proposed_command: str, user_intent: str = "") -> CommandAdvisoryReport:
        """Alias accepting proposed_command first."""
        return self.advise(user_intent=user_intent or "Inspect command safety", proposed_command=proposed_command)

    def _classify_risk(self, full_cmd: str, tokens: List[str], binary: str) -> Tuple[CommandRiskTier, List[str]]:
        risks: List[str] = []

        # Privileged check
        if binary in PRIVILEGED_BINARIES or "sudo " in full_cmd:
            risks.append("Elevated administrative/root privileges required; modifies system configuration.")
            return CommandRiskTier.PRIVILEGED, risks

        # Destructive check
        if binary in DESTRUCTIVE_BINARIES or "rm " in full_cmd or "git reset --hard" in full_cmd:
            risks.append("Permanently deletes files, directories, or repository states; irreversible action.")
            return CommandRiskTier.DESTRUCTIVE, risks

        # Sensitive check
        if binary in SENSITIVE_BINARIES or (binary == "git" and any(t in tokens for t in ["checkout", "commit", "push", "merge", "rebase"])):
            risks.append("Alters workspace files, dependencies, or git branch working tree.")
            return CommandRiskTier.SENSITIVE, risks

        # Low risk check
        if binary in LOW_RISK_BINARIES:
            risks.append("Creates local files or directories; non-destructive write.")
            return CommandRiskTier.LOW_RISK, risks

        # Read only check
        if binary in READ_ONLY_BINARIES:
            # Special check for git commands that mutate vs read
            if binary == "git" and any(t in tokens for t in ["status", "diff", "log", "branch", "show"]):
                return CommandRiskTier.READ_ONLY, ["Safe non-destructive repository read query."]
            elif binary == "git":
                risks.append("Git command modifies repository state.")
                return CommandRiskTier.SENSITIVE, risks
            return CommandRiskTier.READ_ONLY, ["Safe read-only operational query."]

        # Default fallback: unknown binary defaults to SENSITIVE with warning
        risks.append(f"Unrecognized binary '{binary}'; defaulting to sensitive with mandatory approval.")
        return CommandRiskTier.SENSITIVE, risks

    def _explain_command(self, binary: str, tokens: List[str]) -> str:
        """Formulate a clear natural-language explanation of what the command does."""
        if binary == "ls":
            target = tokens[1] if len(tokens) > 1 and not tokens[1].startswith("-") else "the current directory"
            return f"Lists file names, sizes, and attributes in {target}."
        elif binary == "cat":
            target = tokens[1] if len(tokens) > 1 else "the file"
            return f"Reads and outputs the contents of {target}."
        elif binary == "df":
            return "Displays available disk space across mounted filesystems."
        elif binary == "free":
            return "Displays total, used, and available physical RAM and swap memory."
        elif binary == "uptime":
            return "Reports how long the system has been continuously running and current load averages."
        elif binary == "git":
            subcmd = tokens[1] if len(tokens) > 1 else ""
            if subcmd == "status":
                return "Inspects modified files and uncommitted changes in the git repository."
            elif subcmd == "diff":
                return "Displays line-by-line differences between modified files and the latest commit."
            elif subcmd == "log":
                return "Displays recent commit history in reverse chronological order."
            return f"Executes git version control operation '{subcmd}'."
        elif binary == "mkdir":
            folder = tokens[1] if len(tokens) > 1 else "folder"
            return f"Creates a new directory named '{folder}'."
        elif binary == "rm":
            return "Deletes specified files or directories from disk permanently."
        elif binary in ("sudo", "su"):
            return "Executes an operation with superuser (root) administrative privileges."
        else:
            return f"Invokes system utility '{binary}' with arguments: {' '.join(tokens[1:])}."
