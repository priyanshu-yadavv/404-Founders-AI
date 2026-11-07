"""
404 FOUNDERS — Agent Security, Approvals & Runtime Tests
Validates approval ticket lifecycle, single-use guarantees, expiration,
emergency shutdown controller, localhost binding, and immutable audit logging.
"""

import time
import pytest

from core.exceptions import SecurityViolationError
from personal_ai.audit.audit_system import AgentAuditSystem
from personal_ai.emergency.kill_switch import EmergencyShutdownController
from personal_ai.permissions.approval_manager import (
    ApprovalManager,
    CommandRiskTier,
    TicketStatus,
)
from personal_ai.router import NaturalLanguageToolRouter, PersonalAIIntent
from personal_ai.runtime import LocalAgentRuntime


def test_approval_ticket_lifecycle_and_single_use():
    """Verify ticket issuance, operator approval, and single-use consumption guarantee."""
    mgr = ApprovalManager()

    # Issue ticket
    ticket = mgr.issue_ticket(
        tool_name="app_manager.launch_application",
        parameters={"app_name": "gedit"},
        risk_tier=CommandRiskTier.SENSITIVE,
        action_summary="Launch desktop editor",
        ttl_seconds=300,
    )
    assert ticket.ticket_id.startswith("TICK-")
    assert ticket.status == TicketStatus.PENDING

    # Attempt to consume before approval -> must fail
    with pytest.raises(SecurityViolationError, match="Ticket.*has status PENDING"):
        mgr.consume_ticket(ticket.ticket_id)

    # Approve ticket
    decided = mgr.record_decision(
        ticket_id=ticket.ticket_id,
        approved=True,
        decided_by="lead_operator",
        reason="Verified user workstation request",
    )
    assert decided.status == TicketStatus.APPROVED

    # Consume ticket successfully
    consumed = mgr.consume_ticket(ticket.ticket_id)
    assert consumed.status == TicketStatus.CONSUMED

    # Replay attack: attempt to reuse consumed ticket -> must fail
    with pytest.raises(SecurityViolationError, match="Ticket.*has status CONSUMED"):
        mgr.consume_ticket(ticket.ticket_id)


def test_approval_ticket_expiration():
    """Verify expired tickets are rejected."""
    mgr = ApprovalManager()
    ticket = mgr.issue_ticket(
        tool_name="terminal.run_command",
        parameters={"cmd": "systemctl restart nginx"},
        risk_tier=CommandRiskTier.PRIVILEGED,
        action_summary="Restart web service",
        ttl_seconds=1,  # 1 second TTL
    )

    time.sleep(1.2)  # Wait for expiration
    with pytest.raises(SecurityViolationError, match="Ticket.*expired"):
        mgr.record_decision(ticket.ticket_id, approved=True)


def test_emergency_shutdown_kill_switch():
    """Verify immediate kill switch, ticket revocation, and disabled operations."""
    mgr = ApprovalManager()
    ctrl = EmergencyShutdownController(mgr)

    # Create pending ticket
    t1 = mgr.issue_ticket(
        tool_name="filesystem.delete_file",
        parameters={"path": "tmp.txt"},
        risk_tier=CommandRiskTier.DESTRUCTIVE,
        action_summary="Delete temp file",
    )
    assert mgr.get_ticket(t1.ticket_id).status == TicketStatus.PENDING

    # Trigger emergency stop
    status = ctrl.trigger_shutdown(triggered_by="operator", reason="Anomalous behavior suspected")
    assert status.is_active is True
    assert status.revoked_tickets_count >= 1

    # Assert ticket revoked
    assert mgr.get_ticket(t1.ticket_id).status == TicketStatus.REVOKED

    # Assert controller blocks execution
    with pytest.raises(SecurityViolationError, match="Emergency shutdown active"):
        ctrl.assert_not_shutdown()

    # Reset controller
    reset_status = ctrl.reset(reset_by="lead_admin")
    assert reset_status.is_active is False
    ctrl.assert_not_shutdown()  # Should not raise


def test_runtime_localhost_enforcement_and_sessions():
    """Verify localhost binding invariant and authenticated session creation."""
    runtime = LocalAgentRuntime(host="127.0.0.1", port=8000)
    assert runtime.host == "127.0.0.1"

    # Attempt to initialize with public binding -> must fail
    with pytest.raises(SecurityViolationError, match="binding to '0.0.0.0' is strictly prohibited"):
        LocalAgentRuntime(host="0.0.0.0")

    # Session management
    session = runtime.create_session(user_id="operator_1")
    assert session.session_id.startswith("PAI-")
    assert len(session.auth_token) >= 32
    assert session.is_active is True

    # Validate session
    assert runtime.validate_session(session.session_id, session.auth_token) is not None
    with pytest.raises(SecurityViolationError):
        runtime.validate_session(session.session_id, "wrong_token")


def test_agent_audit_system_logging():
    """Verify immutable audit recording and retrieval."""
    audit = AgentAuditSystem()
    entry = audit.record_action(
        user_id="operator_1",
        tool_name="system_monitor.get_system_summary",
        risk_tier="READ_ONLY",
        action_description="Inspected hardware telemetry",
        success=True,
        details={"cpu_pct": 24.5},
    )
    assert entry.event_id.startswith("AUD-")
    assert entry.tool_name == "system_monitor.get_system_summary"

    logs = audit.get_recent_logs(limit=10)
    assert any(l.event_id == entry.event_id for l in logs)


def test_natural_language_tool_router_multilingual():
    """Verify query classification across English, Hindi, and Hinglish."""
    router = NaturalLanguageToolRouter()

    # English performance diagnosis
    r1 = router.route_user_query("Check CPU load and diagnose system performance")
    assert r1.intent == PersonalAIIntent.DIAGNOSE_SYSTEM_PERFORMANCE

    # Hindi performance diagnosis
    r2 = router.route_user_query("सिस्टम की परफॉरमेंस चेक करो और रैम बताओ")
    assert r2.intent == PersonalAIIntent.DIAGNOSE_SYSTEM_PERFORMANCE

    # Hinglish performance diagnosis
    r3 = router.route_user_query("Mera laptop slow chal raha hai check karo")
    assert r3.intent == PersonalAIIntent.DIAGNOSE_SYSTEM_PERFORMANCE

    # File listing
    r4 = router.route_user_query("List files in directory personal_ai")
    assert r4.intent == PersonalAIIntent.BROWSE_FILESYSTEM

    # Command advisory
    r5 = router.route_user_query("Advise me on running command sudo rm -rf /")
    assert r5.intent == PersonalAIIntent.ADVISE_TERMINAL_COMMAND

    # Security audit
    r6 = router.route_user_query("Audit security posture and vulnerability check")
    assert r6.intent == PersonalAIIntent.AUDIT_SECURITY
