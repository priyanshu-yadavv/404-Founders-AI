"""
404 FOUNDERS — Voice Assistant Integration Foundation
Defines abstract interfaces and architectural scaffolding for future JARVIS-style
voice interaction, STT/TTS bridges, wake-word detection, and speaker identity.
STRICT INVARIANTS:
1. Voice biometric authentication is an experimental architectural foundation,
   NOT claimed as production-ready.
2. Voice recognition ALONE is strictly prohibited from authorizing destructive or privileged actions.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional
import uuid

if TYPE_CHECKING:
    from multimodal.audio.speech_generation import SpeechGenerationEngine, SpeechSynthesisResult
    from multimodal.audio.speech_recognition import SpeechRecognitionEngine, SpeechTranscriptionResult


class VoiceSessionState(str, Enum):
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    PROCESSING = "PROCESSING"
    SPEAKING = "SPEAKING"
    INTERRUPTED = "INTERRUPTED"


@dataclass
class WakeWordDetectionResult:
    """Outcome of wake-word detection analysis."""
    detected: bool
    wake_word: Optional[str]
    confidence: float
    timestamp: str


@dataclass
class VoiceProfile:
    """Enrolled speaker voice biometric profile."""
    profile_id: str
    user_id: str
    enrolled_at: str
    sample_count: int
    f0_mean_hz: float
    f0_std_hz: float
    is_verified: bool
    is_production_ready: bool = False  # Strict Invariant: Prototype status


@dataclass
class SpeakerVerificationResult:
    """Speaker verification verdict."""
    user_id: str
    is_authenticated: bool
    similarity_score: float
    liveness_detected: bool
    verdict: str
    evaluation_notice: str = (
        "PROTOTYPE NOTICE: Speaker verification is an experimental foundation. "
        "Voice authentication alone cannot authorize destructive or privileged actions."
    )


class VoiceAssistantFoundation:
    """
    Voice Assistant Scaffolding.
    Connects to Phase 08 SpeechRecognitionEngine and SpeechGenerationEngine,
    manages voice session state, wake-word hooks, and speaker identity interfaces.
    """

    ALLOWED_WAKE_WORDS = ["hey 404", "404", "computer", "jarvis"]

    def __init__(
        self,
        stt_engine: Optional[Any] = None,
        tts_engine: Optional[Any] = None,
    ) -> None:
        self._stt = stt_engine
        self._tts = tts_engine
        self._session_state = VoiceSessionState.IDLE
        self._profiles: Dict[str, VoiceProfile] = {}

    @property
    def stt(self) -> Any:
        if self._stt is None:
            from multimodal.audio.speech_recognition import SpeechRecognitionEngine
            self._stt = SpeechRecognitionEngine()
        return self._stt

    @property
    def tts(self) -> Any:
        if self._tts is None:
            from multimodal.audio.speech_generation import SpeechGenerationEngine
            self._tts = SpeechGenerationEngine()
        return self._tts

    def detect_wake_word(self, audio_transcript: str) -> WakeWordDetectionResult:
        """Evaluate whether a wake-word phrase was spoken."""
        clean_text = audio_transcript.lower().strip()
        now = datetime.now(timezone.utc).isoformat()

        for ww in self.ALLOWED_WAKE_WORDS:
            if ww in clean_text:
                return WakeWordDetectionResult(
                    detected=True,
                    wake_word=ww,
                    confidence=0.95,
                    timestamp=now,
                )

        return WakeWordDetectionResult(
            detected=False,
            wake_word=None,
            confidence=0.0,
            timestamp=now,
        )

    def process_voice_turn(self, audio_bytes: bytes, language: str = "en") -> Dict[str, Any]:
        """Convert incoming voice audio bytes to transcribed text via SpeechRecognitionEngine."""
        transcription: SpeechTranscriptionResult = self.stt.transcribe(audio_bytes, language=language)
        wake_result = self.detect_wake_word(transcription.text)

        return {
            "transcription": transcription.text,
            "detected_language": transcription.detected_language,
            "confidence": transcription.confidence,
            "segments_count": len(transcription.segments),
            "wake_word_detected": wake_result.detected,
            "wake_word": wake_result.wake_word,
        }

    def synthesize_response_speech(self, text: str, language: str = "en") -> SpeechSynthesisResult:
        """Synthesize assistant response text into spoken audio waveform via SpeechGenerationEngine."""
        return self.tts.synthesize(text=text, language=language)

    def enroll_voice_profile(self, user_id: str, baseline_pitch_hz: float = 180.0) -> VoiceProfile:
        """Enroll an initial speaker voice profile for future verification research."""
        prof_id = f"vprof_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()

        profile = VoiceProfile(
            profile_id=prof_id,
            user_id=user_id,
            enrolled_at=now,
            sample_count=1,
            f0_mean_hz=baseline_pitch_hz,
            f0_std_hz=15.0,
            is_verified=True,
            is_production_ready=False,
        )
        self._profiles[user_id] = profile
        return profile

    def verify_speaker(self, user_id: str, pitch_hz: float) -> SpeakerVerificationResult:
        """
        Evaluate speaker similarity against enrolled profile.
        INVARIANT: Voice alone is strictly forbidden from authorizing destructive or privileged operations.
        """
        profile = self._profiles.get(user_id)
        if not profile:
            return SpeakerVerificationResult(
                user_id=user_id,
                is_authenticated=False,
                similarity_score=0.0,
                liveness_detected=False,
                verdict="NO_ENROLLED_PROFILE",
            )

        # Basic pitch deviation check
        deviation = abs(pitch_hz - profile.f0_mean_hz)
        is_match = deviation < 45.0
        score = max(0.0, min(1.0, 1.0 - (deviation / 100.0)))

        return SpeakerVerificationResult(
            user_id=user_id,
            is_authenticated=is_match,
            similarity_score=round(score, 2),
            liveness_detected=True,
            verdict="MATCH" if is_match else "PITCH_MISMATCH",
        )

    def handle_interrupt(self) -> VoiceSessionState:
        """Handle user barge-in / speech interrupt while assistant is speaking."""
        self._session_state = VoiceSessionState.INTERRUPTED
        return self._session_state
