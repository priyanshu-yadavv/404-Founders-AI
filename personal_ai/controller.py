"""
404 FOUNDERS — Personal AI Controller
Top-level coordinator orchestrating the Local Agent Runtime, OS inspection,
system intelligence, process monitoring, file assistant, terminal command advisor,
network diagnostics, coding repository assistant, defensive cybersecurity,
approval workflow, and voice integration foundation.
STRICT INVARIANT: Integrates with the existing intelligence router and memory layers
without creating competing architectures or unrestricted execution paths.
"""

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from personal_ai.apps.app_manager import ApplicationManager
from personal_ai.audit.audit_system import AgentAuditSystem
from personal_ai.coding_assistant.repo_assistant import RepositoryAssistant
from personal_ai.cybersecurity.defense_assistant import DefensiveSecurityAssistant
from personal_ai.emergency.kill_switch import EmergencyShutdownController
from personal_ai.filesystem.file_assistant import FileSystemAssistant
from personal_ai.memory_bridge import PersonalAIMemoryBridge
from personal_ai.network_analysis.network_diagnostics import NetworkDiagnosticsModule
from personal_ai.os_adapters import get_os_adapter
from personal_ai.permissions.approval_manager import ApprovalManager, CommandRiskTier
from personal_ai.router import NaturalLanguageToolRouter, PersonalAIIntent, RoutedIntentResult
from personal_ai.runtime import LocalAgentRuntime
from personal_ai.system_monitor.process_monitor import ProcessMonitor
from personal_ai.system_monitor.system_info import SystemInfoProvider
from personal_ai.terminal.command_advisor import TerminalCommandAdvisor
from personal_ai.voice.voice_interface import VoiceAssistantFoundation


@dataclass
class AgentInteractionResponse:
    """Outcome of a natural-language personal AI interaction."""
    user_query: str
    intent: str
    assistant_response: str
    action_taken: str
    data_payload: Dict[str, Any]
    requires_approval: bool
    pending_ticket_id: Optional[str] = None


class PersonalAIController:
    """Central Personal AI Controller orchestrating local computer intelligence modules."""

    def __init__(
        self,
        runtime: Optional[LocalAgentRuntime] = None,
        approval_manager: Optional[ApprovalManager] = None,
        emergency_controller: Optional[EmergencyShutdownController] = None,
        audit_system: Optional[AgentAuditSystem] = None,
        memory_bridge: Optional[PersonalAIMemoryBridge] = None,
    ) -> None:
        self.approval_mgr = approval_manager or ApprovalManager()
        self.emergency_ctrl = emergency_controller or EmergencyShutdownController(self.approval_mgr)
        self.runtime = runtime or LocalAgentRuntime(emergency_controller=self.emergency_ctrl, approval_manager=self.approval_mgr)
        self.audit = audit_system or AgentAuditSystem()
        self.memory = memory_bridge or PersonalAIMemoryBridge()

        # Local agent subsystems
        adapter = get_os_adapter()
        self.system_info = SystemInfoProvider(adapter)
        self.process_monitor = ProcessMonitor(adapter)
        self.filesystem = FileSystemAssistant()
        self.app_manager = ApplicationManager(adapter)
        self.command_advisor = TerminalCommandAdvisor()
        self.network = NetworkDiagnosticsModule(adapter)
        self.repo_assistant = RepositoryAssistant(fs_assistant=self.filesystem)
        self.security = DefensiveSecurityAssistant(proc_monitor=self.process_monitor)
        self.voice = VoiceAssistantFoundation()
        self.router = NaturalLanguageToolRouter()

    def process_request(
        self,
        user_id: str,
        query: str,
        session_id: Optional[str] = None,
    ) -> AgentInteractionResponse:
        """
        End-to-end processing of user natural-language requests:
        1. Classifies intent across English, Hindi, and Hinglish.
        2. Executes permitted read-only diagnostic or generates approval tickets for actions.
        3. Persists audit event and episodic interaction trajectory.
        """
        self.emergency_ctrl.assert_not_shutdown()

        routing: RoutedIntentResult = self.router.route_user_query(query)
        intent = routing.intent
        data_payload: Dict[str, Any] = {}
        action_taken = "ANALYSIS"
        requires_approval = False
        ticket_id: Optional[str] = None
        response_text = ""

        # 1. System Performance Diagnosis
        if intent == PersonalAIIntent.DIAGNOSE_SYSTEM_PERFORMANCE:
            summary = self.system_info.get_system_summary()
            top_mem = self.process_monitor.get_top_resource_consumers(top_n=3)
            anomalies = self.process_monitor.detect_anomalies()

            data_payload = {
                "cpu_usage_pct": summary.cpu.usage_percent_overall,
                "ram_used_mb": summary.memory.used_ram_mb,
                "ram_total_mb": summary.memory.total_ram_mb,
                "ram_percent": summary.memory.percent_used_ram,
                "top_consumers": [f"{p.name} ({p.memory_mb} MB)" for p in top_mem["top_memory"]],
                "anomalies_count": len(anomalies),
            }

            diag_findings = []
            if summary.memory.percent_used_ram > 85.0:
                diag_findings.append(f"RAM utilization is elevated at {summary.memory.percent_used_ram}%.")
            if summary.cpu.usage_percent_overall > 80.0:
                diag_findings.append(f"CPU load is elevated at {summary.cpu.usage_percent_overall}%.")
            if not diag_findings:
                diag_findings.append("Hardware vitals are within normal operational limits.")

            response_text = (
                f"System Health Analysis:\n"
                f"- CPU: {summary.cpu.usage_percent_overall}% ({summary.cpu.model})\n"
                f"- RAM: {summary.memory.used_ram_mb:.0f} MB / {summary.memory.total_ram_mb:.0f} MB ({summary.memory.percent_used_ram}%)\n"
                f"- Primary consumers: {', '.join(data_payload['top_consumers'])}\n"
                f"- Verdict: {' '.join(diag_findings)}"
            )
            action_taken = "SYSTEM_PERFORMANCE_AUDIT"

        # 2. Hardware Inspection
        elif intent == PersonalAIIntent.INSPECT_HARDWARE:
            data_payload = self.system_info.get_hardware_telemetry()
            response_text = (
                f"Hardware Vitals:\n"
                f"- Model: {data_payload['cpu_model']} ({data_payload['logical_cores']} logical threads)\n"
                f"- RAM: {data_payload['used_ram_mb']:.0f} MB used of {data_payload['total_ram_mb']:.0f} MB ({data_payload['ram_used_pct']}%)\n"
                f"- System Uptime: {data_payload['uptime_hours']} hours\n"
                f"- Battery: {data_payload['battery_percent']}%" if data_payload['battery_percent'] is not None else "Hardware Vitals inspected."
            )
            action_taken = "HARDWARE_INSPECTION"

        # 3. Process Monitoring
        elif intent == PersonalAIIntent.MONITOR_PROCESSES:
            procs = self.process_monitor.list_processes(limit=10)
            data_payload = {"processes": [asdict(p) for p in procs]}
            proc_lines = [f"PID {p.pid}: {p.name} - {p.memory_mb} MB ({p.user})" for p in procs[:5]]
            response_text = f"Top Active Processes:\n" + "\n".join(proc_lines)
            action_taken = "PROCESS_LISTING"

        # 4. Application Launch
        elif intent == PersonalAIIntent.LAUNCH_APPLICATION:
            app_name = routing.detected_entities.get("app_name", "app")
            app_info = self.app_manager.find_app(app_name)

            if app_info:
                # Create an explicit approval ticket for application launch
                ticket = self.approval_mgr.create_ticket(
                    tool_name="application_manager.launch_app",
                    action_summary=f"Launch application '{app_info.name}' ({app_info.executable})",
                    risk_tier=CommandRiskTier.LOW_RISK,
                    parameters={"app_name": app_info.name, "executable": app_info.executable},
                )
                requires_approval = True
                ticket_id = ticket.ticket_id
                data_payload = {"ticket": asdict(ticket), "app_info": asdict(app_info)}
                response_text = (
                    f"Application '{app_info.name}' is available. "
                    f"To proceed, approve pending ticket '{ticket_id}'."
                )
                action_taken = "APPLICATION_LAUNCH_TICKET_CREATED"
            else:
                response_text = f"Application '{app_name}' was not located on this system."
                action_taken = "APP_NOT_FOUND"

        # 5. Project Code Analysis
        elif intent == PersonalAIIntent.ANALYZE_PROJECT_CODE:
            repo_summary = self.repo_assistant.get_repo_summary()
            git_st = self.repo_assistant.get_git_status()
            data_payload = {"repo": asdict(repo_summary), "git_status": asdict(git_st)}
            response_text = (
                f"Repository Intelligence ({repo_summary.project_name}):\n"
                f"- Primary language: {repo_summary.primary_language} ({repo_summary.file_count} files)\n"
                f"- Branch: {git_st.branch} (Clean: {git_st.is_clean})\n"
                f"- Uncommitted files: {len(git_st.modified_files) + len(git_st.untracked_files)}"
            )
            action_taken = "REPO_INSPECTION"

        # 6. Network Diagnostics
        elif intent == PersonalAIIntent.DIAGNOSE_NETWORK:
            net_diag = self.network.run_full_diagnostics()
            data_payload = {
                "interfaces_count": len(net_diag.interfaces),
                "dns_servers": net_diag.dns_servers,
                "connected": net_diag.internet_connected,
            }
            response_text = (
                f"Network Status:\n"
                f"- Active interfaces: {len(net_diag.interfaces)}\n"
                f"- DNS servers: {', '.join(net_diag.dns_servers)}\n"
                f"- Connectivity: {'Operational' if net_diag.internet_connected else 'Disconnected'}"
            )
            action_taken = "NETWORK_DIAGNOSTICS"

        # 7. Cybersecurity Audit
        elif intent == PersonalAIIntent.AUDIT_SECURITY:
            posture = self.security.run_posture_audit()
            data_payload = {
                "open_ports_count": posture.total_open_ports,
                "exposed_ports_count": posture.exposed_external_ports,
                "risk_rating": posture.overall_risk_rating,
                "recommendations": posture.hardening_recommendations,
            }
            response_text = (
                f"Defensive Security Posture:\n"
                f"- Risk Rating: {posture.overall_risk_rating}\n"
                f"- Open Listening Ports: {posture.total_open_ports} ({posture.exposed_external_ports} externally exposed)\n"
                f"- Recommendation: {posture.hardening_recommendations[0] if posture.hardening_recommendations else 'All checks normal.'}"
            )
            action_taken = "SECURITY_POSTURE_AUDIT"

        # 8. File System Exploration
        elif intent == PersonalAIIntent.BROWSE_FILESYSTEM:
            files = self.filesystem.list_directory(".", limit=8)
            data_payload = {"files": [asdict(f) for f in files]}
            file_names = [f.name + ("/" if f.is_directory else "") for f in files]
            response_text = f"Workspace Directory:\n" + "\n".join(f"- {n}" for n in file_names)
            action_taken = "DIRECTORY_LISTING"

        # 9. General / Terminal Advisory Fallback
        else:
            advisory = self.command_advisor.advise(user_intent=query, proposed_command="uname -a")
            data_payload = {"advisory": asdict(advisory)}
            response_text = (
                f"404 FOUNDERS Personal AI Assistant online.\n"
                f"I can assist with system diagnostics, file exploration, defensive security posture audits, "
                f"and command advice. State your objective to begin."
            )
            action_taken = "GENERAL_ADVISORY"

        # Audit event
        self.audit.log_event(
            user_id=user_id,
            action=action_taken,
            session_id=session_id,
            details={"query": query, "intent": intent.value, "ticket_id": ticket_id},
        )

        # Episodic event
        self.memory.log_agent_episode(
            user_id=user_id,
            event_description=f"Personal AI handled intent '{intent.value}' for query: '{query[:80]}'",
            session_id=session_id,
            outcome=action_taken,
        )

        return AgentInteractionResponse(
            user_query=query,
            intent=intent.value,
            assistant_response=response_text,
            action_taken=action_taken,
            data_payload=data_payload,
            requires_approval=requires_approval,
            pending_ticket_id=ticket_id,
        )
