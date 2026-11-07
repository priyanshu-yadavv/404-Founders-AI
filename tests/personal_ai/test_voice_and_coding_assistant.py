"""
404 FOUNDERS — Voice Foundation & Coding / Cyber Assistant Unit Tests
Validates voice wake-word detection, speaker verification safety invariants,
repository topology inspection, and defensive cybersecurity analysis.
"""

from personal_ai.coding_assistant.repo_assistant import RepositoryAssistant
from personal_ai.cybersecurity.defense_assistant import DefensiveSecurityAssistant
from personal_ai.voice.voice_interface import (
    SpeakerVerificationResult,
    VoiceAssistantFoundation,
    VoiceProfile,
    VoiceSessionState,
)


def test_voice_wake_word_detection():
    """Verify wake word matching across supported triggers."""
    voice = VoiceAssistantFoundation()

    res1 = voice.detect_wake_word("Hey 404, what is the cpu load?")
    assert res1.detected is True
    assert res1.wake_word == "hey 404"
    assert res1.confidence > 0.8

    res2 = voice.detect_wake_word("computer check my ram")
    assert res2.detected is True
    assert res2.wake_word == "computer"

    res3 = voice.detect_wake_word("random background noise speech")
    assert res3.detected is False
    assert res3.wake_word is None


def test_voice_session_state_and_interrupt():
    """Verify voice session state transitions and interrupt handling."""
    voice = VoiceAssistantFoundation()
    assert voice._session_state == VoiceSessionState.IDLE

    # Interrupt playback
    voice._session_state = VoiceSessionState.SPEAKING
    interrupted_state = voice.handle_interrupt()
    assert interrupted_state == VoiceSessionState.INTERRUPTED
    assert voice._session_state == VoiceSessionState.INTERRUPTED


def test_speaker_verification_invariant_prototype_only():
    """
    CRITICAL SAFETY INVARIANT:
    Speaker verification is experimental and carries an explicit safety notice that
    voice authentication alone cannot authorize destructive or privileged actions.
    """
    voice = VoiceAssistantFoundation()

    # Enrolling user voice profile
    profile = voice.enroll_voice_profile(user_id="operator_test", baseline_pitch_hz=175.0)
    assert isinstance(profile, VoiceProfile)
    assert profile.is_production_ready is False  # Must remain prototype

    # Verifying speaker
    res = voice.verify_speaker(user_id="operator_test", pitch_hz=180.0)
    assert isinstance(res, SpeakerVerificationResult)
    assert res.is_authenticated is True
    assert "PROTOTYPE NOTICE" in res.evaluation_notice
    assert "cannot authorize destructive or privileged actions" in res.evaluation_notice


def test_repository_assistant_topology_and_git():
    """Verify repository analysis, topology scanning, and git inspection."""
    repo = RepositoryAssistant()
    topology = repo.analyze_project_topology()

    assert topology.is_git_repository is True
    assert topology.total_files_scanned > 0
    assert "py" in topology.file_type_counts
    assert topology.primary_language in ["Python", "Mixed"]

    git_status = repo.inspect_git_status()
    assert git_status.branch in ["main", "master", "HEAD"]

    diffs = repo.inspect_git_diff(cached=False)
    assert isinstance(diffs, str)


def test_defensive_security_assistant_posture():
    """Verify defensive port inspection and security hardening assessment."""
    sec = DefensiveSecurityAssistant()
    posture = sec.assess_security_posture()

    assert posture.open_ports_count >= 0
    assert len(posture.active_security_modules) > 0
    assert len(posture.hardening_recommendations) > 0
    assert posture.risk_level in ["LOW", "MEDIUM", "ELEVATED", "HIGH"]
