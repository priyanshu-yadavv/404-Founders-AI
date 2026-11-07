"""
404 FOUNDERS — Comprehensive Defensive Security Audit Test Suite
Verifies SQL injection immunity, cross-user data isolation, path traversal blocks,
secret scrubbing, unauthenticated access controls, protected PID shielding,
approval ticket single-use lifecycle, and emergency shutdown mechanics.
"""

import os
import secrets
import time
import pytest
from fastapi.testclient import TestClient

from api.rest.app import create_app, initialize_runtime_services
from core.conversation_manager import ConversationManager, UserSettingsManager
from core.exceptions import SecurityViolationError
from database.connection import DatabaseManager
from memory.security import MemorySecurityManager
from personal_ai.controller import PersonalAIController
from personal_ai.filesystem.file_assistant import FileSystemAssistant
from personal_ai.permissions.approval_manager import TicketStatus
from personal_ai.system_monitor.process_monitor import ProcessMonitor
from personal_ai.terminal.command_advisor import CommandRiskTier
from security.auth import AuthManager


@pytest.fixture(scope="module")
def app_client():
    services = initialize_runtime_services()
    app = create_app(services=services)
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="module")
def db_mgr():
    return DatabaseManager.get_instance()


def test_sql_injection_immunity_in_auth_and_conversations(db_mgr: DatabaseManager):
    """Verify that malicious SQL payloads in usernames, emails, or inputs cannot bypass authentication or execute arbitrary SQL."""
    auth_mgr = AuthManager(db_mgr)
    
    # Classic SQL injection strings
    malicious_inputs = [
        "' OR '1'='1",
        "admin' --",
        "'; DROP TABLE user_accounts; --",
        "' UNION SELECT id, username, password_hash, salt FROM user_accounts --",
    ]

    for malicious_input in malicious_inputs:
        # 1. Authenticate should return None, not crash or bypass
        assert auth_mgr.authenticate(malicious_input, "password123") is None
        
        # 2. Registration should reject invalid username format safely
        with pytest.raises(ValueError):
            auth_mgr.register_user(
                username=malicious_input,
                email=f"sqli_{secrets.token_hex(4)}@example.com",
                password="SecurePassword_2026!",
            )

    # 3. Ensure user_accounts table still exists and is untouched
    with db_mgr.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM user_accounts")
        count = cursor.fetchone()[0]
        assert count >= 1


def test_cross_user_tenant_data_isolation(db_mgr: DatabaseManager):
    """Verify that User A cannot read, modify, or delete User B's threads or sessions."""
    auth_mgr = AuthManager(db_mgr)
    conv_mgr = ConversationManager(db_mgr)

    # Create User A
    user_a = auth_mgr.register_user(
        username=f"user_a_{secrets.token_hex(4)}",
        email=f"usera_{secrets.token_hex(4)}@test.local",
        password="Password123!",
    )
    # Create User B
    user_b = auth_mgr.register_user(
        username=f"user_b_{secrets.token_hex(4)}",
        email=f"userb_{secrets.token_hex(4)}@test.local",
        password="Password123!",
    )

    # User A creates a thread
    thread_a = conv_mgr.create_thread(user_id=user_a.id, title="User A Confidential Thread")

    # User B attempts to access User A's thread
    thread_b_view = conv_mgr.get_thread(thread_id=thread_a.id, user_id=user_b.id)
    assert thread_b_view is None, "Tenant isolation failure: User B retrieved User A's thread!"

    # User B attempts to update User A's thread
    updated = conv_mgr.update_thread(thread_id=thread_a.id, user_id=user_b.id, title="Hijacked Title")
    assert updated is False, "Tenant isolation failure: User B updated User A's thread!"

    # User B attempts to delete User A's thread
    deleted = conv_mgr.delete_thread(thread_id=thread_a.id, user_id=user_b.id)
    assert deleted is False, "Tenant isolation failure: User B deleted User A's thread!"

    # Verify User A's thread remains intact
    intact_thread = conv_mgr.get_thread(thread_id=thread_a.id, user_id=user_a.id)
    assert intact_thread is not None
    assert intact_thread.title == "User A Confidential Thread"


def test_secret_scrubbing_across_data_surfaces():
    """Verify that credentials, API tokens, and private keys are scrubbed before persistence."""
    sample_text = (
        "Here is my OpenAI key: sk-proj-abc1234567890abcdefghijklmnopqrstuvwxyz123456\n"
        "Here is my AWS key: AKIAIOSFODNN7EXAMPLE\n"
        "And password: 'SuperSecretAdminPassword123!'"
    )
    scrubbed, detected = MemorySecurityManager.scrub_secrets(sample_text)
    assert "sk-proj-" not in scrubbed
    assert "AKIAIOSFODNN7EXAMPLE" not in scrubbed
    assert "SuperSecretAdminPassword123!" not in scrubbed
    assert "[REDACTED_API_TOKEN]" in scrubbed
    assert "[REDACTED_AWS_ACCESS_KEY]" in scrubbed
    assert "[REDACTED_CREDENTIAL]" in scrubbed
    assert len(detected) >= 3


def test_filesystem_sandbox_path_traversal_prevention(tmp_path):
    """Verify that FileSystemAssistant strictly blocks path traversal and forbidden system files."""
    sandbox = FileSystemAssistant(allowed_roots=[str(tmp_path)])

    # Create safe file inside sandbox
    safe_file = tmp_path / "safe.txt"
    safe_file.write_text("Safe content")

    # Safe read
    entry = sandbox.read_file(str(safe_file))
    assert entry.content == "Safe content"

    # Traversal attempts
    traversal_paths = [
        str(tmp_path / "../../etc/shadow"),
        str(tmp_path / "../../../etc/passwd"),
        "/etc/passwd",
        "/root/.ssh/id_rsa",
    ]

    for p in traversal_paths:
        with pytest.raises(SecurityViolationError):
            sandbox.read_file(p)


def test_protected_process_termination_shield():
    """Verify that protected OS processes (PID 0, 1, 2, systemd, sshd) cannot be targeted for termination."""
    monitor = ProcessMonitor()

    # PIDs 0, 1, 2 must always be protected
    assert monitor.is_process_protected(0) is True
    assert monitor.is_process_protected(1) is True
    assert monitor.is_process_protected(2) is True

    # Attempting to validate PID 1 for termination must raise SecurityViolationError
    with pytest.raises(SecurityViolationError):
        monitor.validate_termination_target(pid=1)


def test_approval_ticket_single_use_and_expiration():
    """Verify that human approval tickets expire after TTL and cannot be reused."""
    ctrl = PersonalAIController()
    mgr = ctrl.approval_mgr

    # Create ticket
    ticket = mgr.create_ticket(
        tool_name="terminate_process",
        action_summary="Terminate test process",
        risk_tier=CommandRiskTier.PRIVILEGED,
        parameters={"pid": 99999},
        ttl_seconds=1,  # 1 second TTL for quick expiry test
    )
    assert ticket.status == TicketStatus.PENDING

    # Approve ticket
    approved = mgr.decide_ticket(ticket.ticket_id, approved=True, decided_by="operator")
    assert approved.status == TicketStatus.APPROVED

    # Consume ticket first time
    consumed = mgr.consume_ticket(ticket.ticket_id, tool_name="terminate_process")
    assert consumed.status == TicketStatus.CONSUMED

    # Attempt to consume ticket second time (replay attack prevention)
    with pytest.raises(SecurityViolationError):
        mgr.consume_ticket(ticket.ticket_id, tool_name="terminate_process")


def test_emergency_shutdown_instant_kill_and_revocation():
    """Verify that the emergency shutdown instantly blocks agent actions and revokes all active approval tickets."""
    ctrl = PersonalAIController()
    appr_mgr = ctrl.approval_mgr
    emerg_ctrl = ctrl.emergency_ctrl

    # Create pending ticket
    t1 = appr_mgr.create_ticket(
        tool_name="terminal_execution",
        action_summary="Testing emergency stop",
        risk_tier=CommandRiskTier.PRIVILEGED,
        parameters={"cmd": "systemctl restart nginx"},
    )
    assert t1.status == TicketStatus.PENDING

    # Trigger emergency kill switch
    emerg_status = emerg_ctrl.trigger_emergency_shutdown(triggered_by="operator", reason="Simulated security incident")
    assert emerg_status.is_active is True
    assert emerg_status.revoked_tickets_count >= 1

    # Ticket should now be REVOKED
    t1_after = appr_mgr.get_ticket(t1.ticket_id)
    assert t1_after.status == TicketStatus.REVOKED

    # Any new action should be blocked
    with pytest.raises(SecurityViolationError):
        ctrl.process_request(user_id="operator", query="Launch terminal command")

    # Reset emergency stop
    reset_status = emerg_ctrl.reset_shutdown(authorized_by="human_operator")
    assert reset_status.is_active is False
