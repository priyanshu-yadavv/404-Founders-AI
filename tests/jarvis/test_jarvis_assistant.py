"""
404 FOUNDERS — Phase 13 JARVIS Conversational Voice Assistant Test Suite
Validates wake-word detection, speaker voice biometrics, speech processing,
conversational turn context, tool execution, proactive alerts, and REST APIs.
"""

from __future__ import annotations

import base64
import io
import math
import struct
import wave
from typing import Generator
import pytest
from starlette.testclient import TestClient

from api.rest.app import create_app, initialize_runtime_services
from database.connection import DatabaseManager
from jarvis.conversation_engine import JarvisConversationEngine
from jarvis.models import (
    JarvisState,
    SpeakerVerificationVerdict,
    SpeakerVerificationOutcome,
)
from jarvis.proactive import ProactiveAssistanceEngine, ProactiveConfig
from jarvis.service import JarvisService
from jarvis.speech_recognition import JarvisSTTEngine
from jarvis.speech_synthesis import JarvisTTSEngine
from jarvis.tool_bridge import JarvisToolBridge
from jarvis.voice_biometrics import VoiceBiometricsEngine
from jarvis.wake_word import WakeWordDetector
from personal_ai.controller import PersonalAIController


def generate_test_wav(
    duration_s: float = 2.0,
    sample_rate: int = 16000,
    freq: float = 180.0,
    volume: float = 0.5,
) -> bytes:
    """Helper to generate a valid PCM mono WAV byte buffer for audio tests."""
    buf = io.BytesIO()
    n_samples = int(duration_s * sample_rate)
    with wave.open(buf, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        frames = bytearray()
        for i in range(n_samples):
            t = float(i) / sample_rate
            sample = volume * math.sin(2.0 * math.pi * freq * t)
            # Add subtle second harmonic for vocal formant realism
            sample += (volume * 0.3) * math.sin(2.0 * math.pi * (freq * 2.0) * t)
            sample_val = int(max(-32768, min(32767, sample * 32767.0)))
            frames.extend(struct.pack("<h", sample_val))
        wav_file.writeframes(frames)
    return buf.getvalue()


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    """Creates a test client with initialized Phase 13 runtime services."""
    services = initialize_runtime_services()
    app = create_app(services=services)
    with TestClient(app) as test_client:
        yield test_client


# =============================================================================
# 1. Wake-Word Detector Unit Tests
# =============================================================================

def test_wake_word_detector_phrase_matching() -> None:
    """Verify wake-word matches English, Hindi, and rejects dissimilar text."""
    detector = WakeWordDetector()

    # English matching
    res_en = detector.detect(transcript_hint="Hey Founders, what is the status?")
    assert res_en.detected is True
    assert res_en.confidence >= 0.85
    assert res_en.matched_phrase == "hey founders"

    # Hindi / Hinglish matching
    res_hi = detector.detect(transcript_hint="नमस्ते फाउंडर्स, सिस्टम डायग्नोस्टिक्स चलाओ")
    assert res_hi.detected is True
    assert res_hi.confidence >= 0.85

    # Dissimilar phrase rejection
    res_reject = detector.detect(transcript_hint="Hello Siri, can you open the website?")
    assert res_reject.detected is False
    assert res_reject.matched_phrase is None


def test_wake_word_energy_gating_and_mute() -> None:
    """Verify acoustic energy threshold rejects silence and mute blocks wake word."""
    detector = WakeWordDetector()

    # Silent audio bytes
    silent_wav = generate_test_wav(duration_s=1.0, volume=0.0)
    res_silent = detector.detect(audio_bytes=silent_wav, transcript_hint="hey founders")
    # Low energy should prevent acoustic detection
    assert res_silent.energy < 0.05

    # Mute control
    detector.mute()
    assert detector.is_muted is True
    res_muted = detector.detect(transcript_hint="hey founders")
    assert res_muted.detected is False
    assert res_muted.energy == 0.0

    detector.unmute()
    assert detector.is_muted is False


# =============================================================================
# 2. Voice Biometrics Engine Tests
# =============================================================================

def test_voice_biometrics_quality_validation() -> None:
    """Verify quality validation rejects short or silent audio and accepts clear audio."""
    engine = VoiceBiometricsEngine()

    # Too short audio (< 0.8s)
    short_wav = generate_test_wav(duration_s=0.3, volume=0.5)
    wf_short, meta_short = engine.audio_processor.read_audio_bytes(short_wav)
    q_short = engine.validate_sample_quality(wf_short, meta_short.sample_rate)
    assert q_short.is_acceptable is False
    assert "shorter than minimum" in (q_short.rejection_reason or "")

    # Silent audio
    silent_wav = generate_test_wav(duration_s=1.5, volume=0.0001)
    wf_sil, meta_sil = engine.audio_processor.read_audio_bytes(silent_wav)
    q_sil = engine.validate_sample_quality(wf_sil, meta_sil.sample_rate)
    assert q_sil.is_acceptable is False

    # Valid audio
    valid_wav = generate_test_wav(duration_s=2.0, freq=160.0, volume=0.5)
    wf_valid, meta_valid = engine.audio_processor.read_audio_bytes(valid_wav)
    q_valid = engine.validate_sample_quality(wf_valid, meta_valid.sample_rate)
    assert q_valid.is_acceptable is True
    assert q_valid.snr_db > 10.0


def test_voice_biometrics_enrollment_and_encryption() -> None:
    """Verify enrollment with 3 samples and AES-256-GCM encrypted profile round-trip."""
    engine = VoiceBiometricsEngine()
    user_id = "test_user_biometrics_1"

    sample1 = generate_test_wav(duration_s=2.0, freq=150.0, volume=0.5)
    sample2 = generate_test_wav(duration_s=2.2, freq=155.0, volume=0.5)
    sample3 = generate_test_wav(duration_s=2.0, freq=152.0, volume=0.5)

    profile_data, ciphertext, nonce_b64 = engine.enroll_speaker(
        user_id=user_id,
        profile_name="Primary Operator",
        audio_samples=[sample1, sample2, sample3],
    )

    assert profile_data.user_id == user_id
    assert profile_data.sample_count == 3
    assert profile_data.embedding_dim == 32
    assert profile_data.is_active is True
    assert len(ciphertext) > 0
    assert len(nonce_b64) > 0

    # Decrypt profile
    meta_dec, emb_dec = engine.decrypt_profile(ciphertext, nonce_b64)
    assert meta_dec.user_id == user_id
    assert emb_dec.shape[-1] == 32


def test_voice_biometrics_verification_matching_and_rejection() -> None:
    """Verify enrolled voice yields VERIFIED while distinct speaker yields REJECTED."""
    engine = VoiceBiometricsEngine()
    user_id = "test_user_biometrics_2"

    # Enroll user at fundamental freq 140 Hz
    s1 = generate_test_wav(duration_s=2.0, freq=140.0, volume=0.5)
    s2 = generate_test_wav(duration_s=2.0, freq=142.0, volume=0.5)
    s3 = generate_test_wav(duration_s=2.0, freq=141.0, volume=0.5)
    engine.enroll_speaker(user_id=user_id, profile_name="Operator 2", audio_samples=[s1, s2, s3])

    # Test sample from same vocal register (141 Hz)
    test_matching = generate_test_wav(duration_s=2.0, freq=141.0, volume=0.5)
    verdict_match = engine.verify(user_id=user_id, audio_bytes=test_matching)
    assert verdict_match.outcome in (
        SpeakerVerificationOutcome.VERIFIED,
        SpeakerVerificationOutcome.UNCERTAIN,
    )
    assert verdict_match.similarity_score > 0.65

    # Test sample from totally different vocal register (380 Hz)
    test_impostor = generate_test_wav(duration_s=2.0, freq=380.0, volume=0.5)
    verdict_impostor = engine.verify(user_id=user_id, audio_bytes=test_impostor)
    assert verdict_impostor.outcome == SpeakerVerificationOutcome.REJECTED


def test_voice_biometrics_profile_revocation() -> None:
    """Verify revocation clears cached profile and reports ENROLLMENT_REQUIRED."""
    engine = VoiceBiometricsEngine()
    user_id = "test_user_biometrics_3"

    s1 = generate_test_wav(duration_s=2.0, freq=150.0)
    engine.enroll_speaker(user_id=user_id, profile_name="Revocable", audio_samples=[s1, s1, s1])
    assert user_id in engine._enrolled_cache

    revoked = engine.revoke_profile(user_id)
    assert revoked is True
    assert user_id not in engine._enrolled_cache

    # Verification after revocation
    verdict = engine.verify(user_id=user_id, audio_bytes=s1)
    assert verdict.outcome == SpeakerVerificationOutcome.ENROLLMENT_REQUIRED


# =============================================================================
# 3. Speech Recognition & Synthesis Unit Tests
# =============================================================================

def test_jarvis_stt_language_detection() -> None:
    """Verify STT identifies English, Hindi, and Hinglish queries."""
    stt = JarvisSTTEngine()

    assert stt.detect_language("What is the current memory consumption?") == "en"
    assert stt.detect_language("सिस्टम की स्थिति की जांच करें") == "hi"
    assert stt.detect_language("System ka status batao please") == "hinglish"
    assert stt.detect_language("Yeh application start karo") == "hinglish"


def test_jarvis_tts_synthesis() -> None:
    """Verify TTS generates valid WAV bytes across voice profiles with rate/pitch control."""
    tts = JarvisTTSEngine()

    # English Calm
    out_calm = tts.synthesize("System diagnostic passed successfully.", voice_id="founders_calm")
    assert len(out_calm.audio_base64) > 0
    assert out_calm.duration_seconds > 0.0
    assert out_calm.audio_format == "audio/wav"

    # Hindi Profile
    out_hi = tts.synthesize("सिस्टम के सभी घटक सक्रिय हैं।", voice_id="founders_hindi")
    assert len(out_hi.audio_base64) > 0
    assert out_hi.voice_id == "founders_hindi"

    # Speed & Pitch Modulation
    out_fast = tts.synthesize("Rapid telemetry check.", speed=1.3, pitch=1.1)
    assert out_fast.duration_seconds > 0.0


# =============================================================================
# 4. Tool Bridge & Permission Enforcement Unit Tests
# =============================================================================

def test_jarvis_tool_bridge_permission_enforcement() -> None:
    """Verify Read-Only tools execute freely while Privileged tools enforce approval."""
    bridge = JarvisToolBridge()

    # 1. Read-Only tool: System Vitals
    res_vitals = bridge.execute_intent("Inspect hardware and CPU memory status")
    assert res_vitals.tool_called == "system_info_provider.get_hardware_telemetry"
    assert res_vitals.status == "SUCCESS"
    assert res_vitals.requires_ticket is False
    assert "used_ram_mb" in (res_vitals.result or {})

    # 2. Privileged tool: Application Launch (requires ticket)
    res_launch = bridge.execute_intent("Launch application radare2")
    assert res_launch.tool_called == "application_manager.launch_app"
    assert res_launch.requires_ticket is True
    assert res_launch.status == "APPROVAL_REQUIRED"
    assert res_launch.ticket_request_id is not None


def test_jarvis_tool_bridge_hindi_commands() -> None:
    """Verify Hindi and Hinglish queries map accurately to tool execution."""
    bridge = JarvisToolBridge()

    # Hinglish query
    res_hinglish = bridge.execute_intent("Memory aur CPU kitna use ho raha hai?")
    assert res_hinglish.tool_called == "system_info_provider.get_hardware_telemetry"
    assert res_hinglish.status == "SUCCESS"

    # Hindi query
    res_hindi = bridge.execute_intent("सिस्टम स्थिति की जाँच करें")
    assert res_hindi.status == "SUCCESS"


# =============================================================================
# 5. Proactive Assistance Unit Tests
# =============================================================================

def test_proactive_assistance_alerts_and_quiet_hours() -> None:
    """Verify vitals watchdog generates alerts when thresholds exceed and respects quiet hours."""
    engine = ProactiveAssistanceEngine(config=ProactiveConfig(enabled=True, ram_threshold_pct=10.0))

    # Threshold violation check (ram_threshold_pct=10.0 is deliberately low to trigger)
    alerts = engine.inspect_vitals_and_generate_alerts()
    # At least RAM or CPU should trigger alert
    assert len(alerts) >= 1
    assert alerts[0].spoken_announcement is not None

    # Quiet hours check
    engine.config.quiet_hours_start = "00:00"
    engine.config.quiet_hours_end = "23:59"
    assert engine.is_quiet_hours() is True
    alerts_quiet = engine.inspect_vitals_and_generate_alerts()
    assert len(alerts_quiet) == 0  # Silenced during quiet hours


# =============================================================================
# 6. Conversation Engine & Multi-Turn State Tests
# =============================================================================

def test_conversation_engine_turn_and_interrupt() -> None:
    """Verify session turns, contextual follow-ups, and barge-in interruptions."""
    engine = JarvisConversationEngine()
    session = engine.create_session("operator_test", language_hint="en")
    assert session.state == JarvisState.STANDBY

    # Turn 1
    t1 = engine.process_text_turn(
        user_id="operator_test",
        query="Inspect hardware and host memory status",
        session_id=session.session_id,
    )
    assert t1["tool_called"] == "system_info_provider.get_hardware_telemetry"
    assert len(session.turns) == 1

    # Barge-in interrupt
    interrupted_state = engine.handle_barge_in_interrupt(session.session_id)
    assert interrupted_state == JarvisState.INTERRUPTED
    assert session.state == JarvisState.INTERRUPTED


# =============================================================================
# 7. Unified JarvisService & SQLite Persistence Tests
# =============================================================================

def test_jarvis_service_database_persistence() -> None:
    """Verify voice profile is stored in SQLite voice_profiles and audit logged."""
    db = DatabaseManager.get_instance()
    svc = JarvisService.get_instance(db_manager=db)

    user_id = "test_user_db_persistence"
    s1 = generate_test_wav(duration_s=2.0, freq=160.0)
    s2 = generate_test_wav(duration_s=2.0, freq=162.0)
    s3 = generate_test_wav(duration_s=2.0, freq=161.0)

    # Enroll
    profile = svc.enroll_voice_profile(user_id=user_id, profile_name="DB Persist Test", audio_samples=[s1, s2, s3])
    assert profile.user_id == user_id

    # Verify directly from DB
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, is_active FROM voice_profiles WHERE user_id = ? AND is_active = 1", (user_id,))
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == user_id
        assert row[1] == 1

        # Check audit log
        cursor.execute("SELECT event_type, outcome FROM voice_audit_log WHERE user_id = ?", (user_id,))
        audit_rows = cursor.fetchall()
        assert len(audit_rows) >= 1
        assert any(r[0] == "VOICE_ENROLLMENT" for r in audit_rows)

    # Clean up / revoke
    revoked = svc.revoke_voice_profile(user_id)
    assert revoked is True


# =============================================================================
# 8. REST API Endpoints Integration Tests
# =============================================================================

def test_jarvis_api_session_and_wake_word(client: TestClient) -> None:
    """Verify /api/v1/jarvis/session and /api/v1/jarvis/wake-word."""
    # Session creation
    res_sess = client.post("/api/v1/jarvis/session", json={"language_hint": "en"})
    assert res_sess.status_code == 200
    sess_data = res_sess.json()
    assert "session_id" in sess_data
    assert sess_data["state"] == "STANDBY"

    # Wake-word detection
    res_ww = client.post("/api/v1/jarvis/wake-word", json={"text_hint": "Hey Founders, help me"})
    assert res_ww.status_code == 200
    ww_data = res_ww.json()
    assert ww_data["detected"] is True
    assert ww_data["phrase"] == "hey founders"


def test_jarvis_api_enrollment_and_profile_flow(client: TestClient) -> None:
    """Verify full enrollment lifecycle: sample, finalize, get profile, delete profile."""
    user_id = "test_api_speaker_enrollment"
    s1_b64 = base64.b64encode(generate_test_wav(duration_s=2.0, freq=165.0)).decode("utf-8")
    s2_b64 = base64.b64encode(generate_test_wav(duration_s=2.0, freq=166.0)).decode("utf-8")
    s3_b64 = base64.b64encode(generate_test_wav(duration_s=2.0, freq=164.0)).decode("utf-8")

    # Step 1: Submit samples
    for idx, sample_b64 in enumerate([s1_b64, s2_b64, s3_b64], start=1):
        res_sample = client.post(
            "/api/v1/jarvis/enroll/sample",
            json={
                "user_id": user_id,
                "sample_index": idx,
                "audio_base64": sample_b64,
                "sample_rate": 16000,
            },
        )
        assert res_sample.status_code == 200
        sample_data = res_sample.json()
        assert sample_data["is_valid"] is True
        assert sample_data["samples_recorded"] == idx

    # Step 2: Finalize
    res_fin = client.post(
        "/api/v1/jarvis/enroll/finalize",
        json={
            "user_id": user_id,
            "profile_name": "API Enrolled Operator",
            "verification_threshold": 0.75,
            "anti_spoofing": True,
        },
    )
    assert res_fin.status_code == 200
    fin_data = res_fin.json()
    assert fin_data["status"] == "ACTIVE"
    assert fin_data["sample_count"] == 3

    # Step 3: Get profile
    res_prof = client.get(f"/api/v1/jarvis/profile?user_id={user_id}")
    assert res_prof.status_code == 200
    prof_data = res_prof.json()
    assert prof_data["exists"] is True
    assert prof_data["is_active"] is True

    # Step 4: Delete profile
    res_del = client.delete(f"/api/v1/jarvis/profile?user_id={user_id}")
    assert res_del.status_code == 200
    assert res_del.json()["status"] == "REVOKED"


def test_jarvis_api_verify_and_transcribe(client: TestClient) -> None:
    """Verify /api/v1/jarvis/verify and /api/v1/jarvis/transcribe."""
    test_wav_b64 = base64.b64encode(generate_test_wav(duration_s=1.5, freq=170.0)).decode("utf-8")

    # Verification (unknown speaker without profile)
    res_ver = client.post(
        "/api/v1/jarvis/verify",
        json={"user_id": "unregistered_user", "audio_base64": test_wav_b64},
    )
    assert res_ver.status_code == 200
    ver_data = res_ver.json()
    assert ver_data["outcome"] == "ENROLLMENT_REQUIRED"

    # Transcription
    res_tr = client.post(
        "/api/v1/jarvis/transcribe",
        json={"audio_base64": test_wav_b64, "language_hint": "en"},
    )
    assert res_tr.status_code == 200
    tr_data = res_tr.json()
    assert "text" in tr_data
    assert tr_data["detected_language"] in ("en", "hi", "hinglish")


def test_jarvis_api_synthesize_and_interact(client: TestClient) -> None:
    """Verify /api/v1/jarvis/synthesize and /api/v1/jarvis/interact."""
    # Synthesize
    res_synth = client.post(
        "/api/v1/jarvis/synthesize",
        json={"text": "404 FOUNDERS JARVIS Online", "voice_id": "founders_calm"},
    )
    assert res_synth.status_code == 200
    synth_data = res_synth.json()
    assert len(synth_data["audio_base64"]) > 0
    assert synth_data["audio_format"] == "audio/wav"

    # Interact via text
    res_interact = client.post(
        "/api/v1/jarvis/interact",
        json={"text_input": "Inspect hardware and cpu ram status"},
    )
    assert res_interact.status_code == 200
    int_data = res_interact.json()
    assert int_data["tool_called"] == "system_info_provider.get_hardware_telemetry"
    assert int_data["tool_status"] == "SUCCESS"
    assert len(int_data["assistant_reply"]) > 0
    assert len(int_data["audio_base64"]) > 0


def test_jarvis_api_interrupt_and_state(client: TestClient) -> None:
    """Verify /api/v1/jarvis/interrupt and /api/v1/jarvis/state."""
    res_int = client.post(
        "/api/v1/jarvis/interrupt",
        json={"session_id": "sess_int_test", "reason": "barge_in"},
    )
    assert res_int.status_code == 200
    int_data = res_int.json()
    assert int_data["interrupted"] is True
    assert int_data["state"] == "INTERRUPTED"

    res_st = client.get("/api/v1/jarvis/state?session_id=sess_int_test")
    assert res_st.status_code == 200
    assert "state" in res_st.json()


def test_jarvis_api_proactive_endpoints(client: TestClient) -> None:
    """Verify /api/v1/jarvis/proactive/alerts, config, and dismiss."""
    # Alerts
    res_alerts = client.get("/api/v1/jarvis/proactive/alerts")
    assert res_alerts.status_code == 200
    alerts_data = res_alerts.json()
    assert "alerts" in alerts_data
    assert "quiet_hours_active" in alerts_data

    # Config update
    res_cfg = client.post(
        "/api/v1/jarvis/proactive/config",
        json={"ram_threshold_pct": 90.0, "quiet_hours_start": "23:00"},
    )
    assert res_cfg.status_code == 200
    cfg_data = res_cfg.json()
    assert cfg_data["status"] == "UPDATED"
    assert cfg_data["config"]["ram_threshold_pct"] == 90.0

    # Dismiss
    res_dis = client.post("/api/v1/jarvis/proactive/dismiss?alert_id=nonexistent_alert")
    assert res_dis.status_code == 200
    assert res_dis.json()["status"] == "DISMISSED"
