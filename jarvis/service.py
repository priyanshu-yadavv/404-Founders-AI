"""
404 FOUNDERS — Unified JARVIS Service Orchestrator
Coordinates wake-word detection, voice biometrics, speech processing,
conversational memory, proactive assistance, and SQLite database persistence.
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import uuid

from database.connection import DatabaseManager
from jarvis.conversation_engine import JarvisConversationEngine
from jarvis.models import (
    JarvisState,
    ProactiveAlert,
    SpeakerVerificationOutcome,
    SpeakerVerificationVerdict,
    VoiceProfileData,
    VoiceSampleQuality,
    WakeWordResult,
)
from jarvis.proactive import ProactiveAssistanceEngine, ProactiveConfig
from jarvis.speech_recognition import JarvisSTTEngine
from jarvis.speech_synthesis import JarvisSpeechOutput, JarvisTTSEngine
from jarvis.tool_bridge import JarvisToolBridge
from jarvis.voice_biometrics import VoiceBiometricsEngine
from jarvis.wake_word import WakeWordDetector
from personal_ai.controller import PersonalAIController


class JarvisService:
    """
    Central JARVIS Service.
    Singleton orchestrator managing voice sessions, persistent biometrics in SQLite,
    proactive background alerts, and conversational tool execution.
    """

    _instance: Optional["JarvisService"] = None

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        personal_ai_controller: Optional[PersonalAIController] = None,
    ) -> None:
        self.db = db_manager or DatabaseManager.get_instance()
        self.pai_controller = personal_ai_controller or PersonalAIController()

        self.wake_detector = WakeWordDetector()
        self.biometrics = VoiceBiometricsEngine()
        self.stt = JarvisSTTEngine()
        self.tts = JarvisTTSEngine()
        self.tool_bridge = JarvisToolBridge(controller=self.pai_controller)
        self.conversation_engine = JarvisConversationEngine(
            wake_detector=self.wake_detector,
            biometrics_engine=self.biometrics,
            stt_engine=self.stt,
            tts_engine=self.tts,
            tool_bridge=self.tool_bridge,
        )
        self.proactive_engine = ProactiveAssistanceEngine(
            system_info_provider=self.pai_controller.system_info,
        )

        # Temporary enrollment sample buffer: user_id -> list of raw audio bytes
        self._enrollment_buffers: Dict[str, List[bytes]] = {}

        # Load enrolled voice profiles from database into biometrics cache
        self._load_profiles_from_database()

    @classmethod
    def get_instance(
        cls,
        db_manager: Optional[DatabaseManager] = None,
        personal_ai_controller: Optional[PersonalAIController] = None,
    ) -> "JarvisService":
        if cls._instance is None:
            cls._instance = cls(db_manager=db_manager, personal_ai_controller=personal_ai_controller)
        return cls._instance

    def _load_profiles_from_database(self) -> None:
        """Load and decrypt active speaker biometric profiles from SQLite database."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    SELECT user_id, profile_name, sample_count, f0_mean_hz, f0_std_hz,
                           spectral_centroid_hz, encrypted_embedding_blob, encryption_salt,
                           verification_threshold, anti_spoofing_enabled, enrolled_at
                    FROM voice_profiles
                    WHERE is_active = 1
                    """
                )
                rows = cursor.fetchall()
                for r in rows:
                    (u_id, p_name, s_count, f0_m, f0_s, spec_c, enc_blob, nonce_b64, thresh, anti_spoof, enrolled_at) = r
                    try:
                        meta, emb = self.biometrics.decrypt_profile(enc_blob, nonce_b64)
                        self.biometrics._enrolled_cache[u_id] = (meta, emb)
                    except Exception:
                        continue
            except Exception:
                # Table might not exist yet if migration pending
                pass

    def add_enrollment_sample(self, user_id: str, audio_bytes: bytes) -> VoiceSampleQuality:
        """Validate sample quality and add to user's enrollment buffer."""
        waveform, meta = self.biometrics.audio_processor.read_audio_bytes(audio_bytes)
        quality = self.biometrics.validate_sample_quality(waveform, meta.sample_rate)
        if quality.is_acceptable:
            if user_id not in self._enrollment_buffers:
                self._enrollment_buffers[user_id] = []
            self._enrollment_buffers[user_id].append(audio_bytes)
        return quality

    def get_enrollment_sample_count(self, user_id: str) -> int:
        """Return number of buffered valid enrollment samples for user."""
        return len(self._enrollment_buffers.get(user_id, []))

    def finalize_enrollment(
        self,
        user_id: str,
        profile_name: str = "Primary Voice",
        verification_threshold: float = 0.75,
        anti_spoofing: bool = True,
    ) -> VoiceProfileData:
        """Finalize buffered samples into an encrypted voice biometric profile."""
        samples = self._enrollment_buffers.get(user_id, [])
        if len(samples) < 3:
            raise ValueError(f"At least 3 valid samples required for enrollment, got {len(samples)}")
        profile = self.enroll_voice_profile(
            user_id=user_id,
            profile_name=profile_name,
            audio_samples=samples,
        )
        profile.verification_threshold = verification_threshold
        profile.anti_spoofing_enabled = anti_spoofing
        self._enrollment_buffers.pop(user_id, None)
        return profile

    def enroll_voice_profile(
        self,
        user_id: str,
        profile_name: str,
        audio_samples: List[bytes],
    ) -> VoiceProfileData:
        """
        Enroll a speaker's voice using 3+ samples, encrypt profile, and store in database.
        """
        profile_data, ciphertext, nonce_b64 = self.biometrics.enroll_speaker(
            user_id=user_id,
            profile_name=profile_name,
            audio_samples=audio_samples,
        )

        # Persist to database
        now_iso = datetime.now(timezone.utc).isoformat()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR IGNORE INTO user_accounts (id, username, email, password_hash, salt, display_name, role, created_at, updated_at)
                VALUES (?, ?, ?, 'insecure_placeholder', 'salt', ?, 'USER', ?, ?)
                """,
                (user_id, f"user_{user_id}", f"{user_id}@local", user_id, now_iso, now_iso),
            )
            # Deactivate previous profiles for this user
            cursor.execute("UPDATE voice_profiles SET is_active = 0 WHERE user_id = ?", (user_id,))
            cursor.execute(
                """
                INSERT INTO voice_profiles (
                    id, user_id, profile_name, is_active, sample_count,
                    f0_mean_hz, f0_std_hz, spectral_centroid_hz,
                    encrypted_embedding_blob, encryption_salt,
                    verification_threshold, anti_spoofing_enabled,
                    enrolled_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    is_active = 1,
                    encrypted_embedding_blob = excluded.encrypted_embedding_blob,
                    encryption_salt = excluded.encryption_salt,
                    updated_at = excluded.updated_at
                """,
                (
                    profile_data.profile_id,
                    user_id,
                    profile_name,
                    1,
                    profile_data.sample_count,
                    profile_data.f0_mean_hz,
                    profile_data.f0_std_hz,
                    profile_data.spectral_centroid_hz,
                    ciphertext,
                    nonce_b64,
                    profile_data.verification_threshold,
                    1 if profile_data.anti_spoofing_enabled else 0,
                    profile_data.enrolled_at,
                    now_iso,
                ),
            )
            # Log audit event
            cursor.execute(
                """
                INSERT INTO voice_audit_log (id, user_id, event_type, outcome, details, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    f"vaud_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}",
                    user_id,
                    "VOICE_ENROLLMENT",
                    "SUCCESS",
                    f"Enrolled profile '{profile_name}' with {len(audio_samples)} verified samples.",
                    now_iso,
                ),
            )

        return profile_data

    def verify_voice(
        self,
        user_id: str,
        audio_bytes: bytes,
        sample_rate: int = 16000,
    ) -> SpeakerVerificationVerdict:
        """Verify speaker against enrolled profile and record audit entry."""
        verdict = self.biometrics.verify_speaker_turn(user_id, audio_bytes, sample_rate=sample_rate)

        # Record audit log
        now_iso = datetime.now(timezone.utc).isoformat()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    INSERT INTO voice_audit_log (id, user_id, event_type, outcome, details, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"vaud_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}",
                        user_id,
                        "SPEAKER_VERIFICATION",
                        verdict.outcome.value,
                        f"Similarity: {verdict.similarity_score:.2f}, Liveness: {verdict.liveness_score:.2f}",
                        now_iso,
                    ),
                )
            except Exception:
                pass

        return verdict

    verify_speaker_voice = verify_voice

    def get_voice_profile(self, user_id: str) -> Optional[VoiceProfileData]:
        """Fetch current enrolled profile metadata for user."""
        cached = self.biometrics._enrolled_cache.get(user_id)
        if cached:
            return cached[0]

        # Check DB
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    SELECT id, user_id, profile_name, sample_count, f0_mean_hz, f0_std_hz,
                           spectral_centroid_hz, verification_threshold, anti_spoofing_enabled,
                           enrolled_at, is_active
                    FROM voice_profiles
                    WHERE user_id = ? AND is_active = 1
                    ORDER BY enrolled_at DESC LIMIT 1
                    """,
                    (user_id,),
                )
                row = cursor.fetchone()
                if row:
                    return VoiceProfileData(
                        profile_id=row[0],
                        user_id=row[1],
                        profile_name=row[2],
                        sample_count=row[3],
                        f0_mean_hz=row[4],
                        f0_std_hz=row[5],
                        spectral_centroid_hz=row[6],
                        embedding_dim=32,
                        verification_threshold=row[7],
                        anti_spoofing_enabled=bool(row[8]),
                        enrolled_at=row[9],
                        is_active=bool(row[10]),
                    )
            except Exception:
                pass

        return None

    def revoke_voice_profile(self, user_id: str) -> bool:
        """Revoke user's enrolled voice profile and delete from DB."""
        self.biometrics.revoke_profile(user_id)
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "UPDATE voice_profiles SET is_active = 0 WHERE user_id = ?",
                    (user_id,),
                )
                cursor.execute(
                    """
                    INSERT INTO voice_audit_log (id, user_id, event_type, outcome, details, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"vaud_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}",
                        user_id,
                        "VOICE_REVOCATION",
                        "SUCCESS",
                        "User voice biometric profile permanently revoked and deactivated.",
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
                return True
            except Exception:
                return False

    def process_voice_turn(
        self,
        user_id: str,
        audio_bytes: bytes,
        session_id: Optional[str] = None,
        transcript_hint: Optional[str] = None,
        skip_wake_word_check: bool = False,
    ) -> Dict[str, Any]:
        """Execute conversational voice turn."""
        return self.conversation_engine.process_voice_turn(
            user_id=user_id,
            audio_bytes=audio_bytes,
            session_id=session_id,
            transcript_hint=transcript_hint,
            skip_wake_word_check=skip_wake_word_check,
        )

    def process_text_turn(
        self,
        user_id: str,
        query: str,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute conversational text turn."""
        return self.conversation_engine.process_text_turn(
            user_id=user_id,
            query=query,
            session_id=session_id,
        )

    def interrupt(self, session_id: str) -> JarvisState:
        """Trigger barge-in interrupt."""
        return self.conversation_engine.handle_barge_in_interrupt(session_id)

    def get_proactive_alerts(self) -> List[ProactiveAlert]:
        """Fetch active proactive system health alerts."""
        return self.proactive_engine.inspect_vitals_and_generate_alerts()
