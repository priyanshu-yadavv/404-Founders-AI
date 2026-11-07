"""
404 FOUNDERS — Natural-Language Tool Routing Engine
Parses multi-lingual user intents (English, Hindi, Hinglish), identifies target operations,
and dispatches requests to authorized Personal AI subsystem tools.
STRICT INVARIANT: Never claims an action succeeded unless the underlying tool confirms success.
"""

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Any, Dict, List, Optional


class PersonalAIIntent(str, Enum):
    DIAGNOSE_SYSTEM_PERFORMANCE = "DIAGNOSE_SYSTEM_PERFORMANCE"
    INSPECT_HARDWARE = "INSPECT_HARDWARE"
    MONITOR_PROCESSES = "MONITOR_PROCESSES"
    BROWSE_FILESYSTEM = "BROWSE_FILESYSTEM"
    LAUNCH_APPLICATION = "LAUNCH_APPLICATION"
    ADVISE_TERMINAL_COMMAND = "ADVISE_TERMINAL_COMMAND"
    DIAGNOSE_NETWORK = "DIAGNOSE_NETWORK"
    ANALYZE_PROJECT_CODE = "ANALYZE_PROJECT_CODE"
    AUDIT_SECURITY = "AUDIT_SECURITY"
    GENERAL_ASSISTANCE = "GENERAL_ASSISTANCE"


@dataclass
class RoutedIntentResult:
    """Parsed intent and tool execution routing parameters."""
    intent: PersonalAIIntent
    confidence: float
    detected_entities: Dict[str, Any]
    requires_approval: bool
    recommended_tool: str
    explanation: str


class NaturalLanguageToolRouter:
    """Intent classifier and tool dispatcher for Personal AI operations."""

    def route_user_query(self, query: str) -> RoutedIntentResult:
        """Classify user query and route to target Personal AI subsystem tool."""
        q = query.strip().lower()

        # 1. System Slow / Performance Diagnostic (English, Hindi, Hinglish)
        # e.g., "laptop slow kyun hai", "why is my pc slow", "system lag", "high cpu", "सिस्टम की परफॉरमेंस"
        if any(w in q for w in [
            "slow", "lag", "hang", "dheema", "kyun hai", "heavy", "stuck", "performance", "diagnose", "health",
            "परफॉरमेंस", "धीमा", "हैंग", "रैम", "सीपीयू"
        ]) and any(w in q for w in [
            "laptop", "pc", "system", "computer", "machine", "सिस्टम", "कंप्यूटर", "लैपटॉप"
        ]):
            return RoutedIntentResult(
                intent=PersonalAIIntent.DIAGNOSE_SYSTEM_PERFORMANCE,
                confidence=0.95,
                detected_entities={"target": "system_performance"},
                requires_approval=False,
                recommended_tool="system_info_provider.get_system_summary",
                explanation="Detected system performance diagnostic intent. Inspecting CPU, RAM, and disk utilization.",
            )

        # 2. Hardware / Specs Inspection
        # e.g., "show hardware", "cpu usage", "ram info", "kitna ram hai", "battery status"
        if any(w in q for w in ["hardware", "cpu", "ram", "memory", "battery", "storage", "disk", "specs", "temperature"]):
            return RoutedIntentResult(
                intent=PersonalAIIntent.INSPECT_HARDWARE,
                confidence=0.90,
                detected_entities={"target": "hardware_vitals"},
                requires_approval=False,
                recommended_tool="system_info_provider.get_hardware_telemetry",
                explanation="Detected hardware telemetry inspection intent. Querying non-destructive sensor metrics.",
            )

        # 3. Process Monitoring / High Consumers
        # e.g., "running processes", "kya chal raha hai", "top processes", "kill process", "task manager"
        if any(w in q for w in ["process", "processes", "task", "pid", "kya chal raha"]):
            return RoutedIntentResult(
                intent=PersonalAIIntent.MONITOR_PROCESSES,
                confidence=0.88,
                detected_entities={"target": "processes"},
                requires_approval=False,
                recommended_tool="process_monitor.list_processes",
                explanation="Detected process inspection intent. Listing active operating system processes.",
            )

        # 4. Application Launch
        # e.g., "vs code open karo", "launch firefox", "start browser", "open terminal", "kholo"
        if any(w in q for w in ["open", "launch", "start", "kholo", "chalao"]) and any(w in q for w in ["code", "vscode", "vs code", "firefox", "browser", "chrome", "terminal", "app"]):
            # Extract application name candidate
            app_match = re.search(r"(?:open|launch|start|kholo|chalao)\s+([a-zA-Z0-9_\-\s]+)", q)
            app_name = app_match.group(1).strip() if app_match else "application"
            app_name = re.sub(r"\b(?:app|application|karo)\b", "", app_name).strip() or "app"

            return RoutedIntentResult(
                intent=PersonalAIIntent.LAUNCH_APPLICATION,
                confidence=0.92,
                detected_entities={"app_name": app_name},
                requires_approval=True,
                recommended_tool="application_manager.launch_app",
                explanation=f"Detected application launch request for '{app_name}'. Prepared approved launch adapter.",
            )

        # 5. Project Coding / Error Analysis
        # e.g., "project mein error find karo", "find errors in my code", "git status", "review diff", "run tests"
        if any(w in q for w in ["project", "code", "error", "bug", "git", "diff", "test", "tests", "syntax"]):
            return RoutedIntentResult(
                intent=PersonalAIIntent.ANALYZE_PROJECT_CODE,
                confidence=0.91,
                detected_entities={"target": "repository"},
                requires_approval=False,
                recommended_tool="repository_assistant.get_repo_summary",
                explanation="Detected coding and repository intelligence intent. Inspecting authorized workspace structure.",
            )

        # 6. Network Diagnostics
        # e.g., "check internet", "ping host", "dns test", "network status", "ip address"
        if any(w in q for w in ["network", "internet", "ping", "dns", "ip", "connection", "wifi"]):
            return RoutedIntentResult(
                intent=PersonalAIIntent.DIAGNOSE_NETWORK,
                confidence=0.89,
                detected_entities={"target": "network_diagnostics"},
                requires_approval=False,
                recommended_tool="network_diagnostics.run_full_diagnostics",
                explanation="Detected defensive network diagnostic intent. Checking interfaces, DNS, and latency.",
            )

        # 7. Cybersecurity / Port Audit
        # e.g., "security audit", "open ports", "firewall", "vulnerability check", "auth logs"
        if any(w in q for w in ["security", "port", "ports", "firewall", "vulnerability", "audit", "threat", "log"]):
            return RoutedIntentResult(
                intent=PersonalAIIntent.AUDIT_SECURITY,
                confidence=0.90,
                detected_entities={"target": "security_audit"},
                requires_approval=False,
                recommended_tool="defensive_security.run_posture_audit",
                explanation="Detected defensive security inspection intent. Analyzing open listening ports and security logs.",
            )

        # 8. File System Exploration
        # e.g., "list files", "search file", "find document", "directory contents"
        if any(w in q for w in ["file", "files", "directory", "folder", "documents", "path"]):
            return RoutedIntentResult(
                intent=PersonalAIIntent.BROWSE_FILESYSTEM,
                confidence=0.85,
                detected_entities={"target": "filesystem"},
                requires_approval=False,
                recommended_tool="file_assistant.list_directory",
                explanation="Detected file system exploration intent. Inspecting authorized directory contents.",
            )

        # 9. Terminal Command Advisory
        # e.g., "advise me on command", "is this command safe", "explain command"
        if any(w in q for w in ["advise", "command", "shell", "terminal", "bash"]):
            return RoutedIntentResult(
                intent=PersonalAIIntent.ADVISE_TERMINAL_COMMAND,
                confidence=0.92,
                detected_entities={"target": "terminal_command"},
                requires_approval=False,
                recommended_tool="terminal_command_advisor.advise",
                explanation="Detected terminal command advisory intent. Evaluating command safety and potential risks.",
            )

        # Default: General Assistance / Terminal Advisory
        return RoutedIntentResult(
            intent=PersonalAIIntent.GENERAL_ASSISTANCE,
            confidence=0.70,
            detected_entities={},
            requires_approval=False,
            recommended_tool="terminal_command_advisor.advise",
            explanation="General personal AI query. Ready to provide guidance and safe command advisory.",
        )
