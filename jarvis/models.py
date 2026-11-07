"""
404 FOUNDERS — JARVIS-Style Conversational Assistant Models
Defines core enumeration types, data transfer objects, state representations,
and verification schemas for voice-first interactions, voice biometrics, and tool-calling.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class JarvisState(str, Enum):
    """Lifecycle state machine for the JARVIS conversational assistant."""
    STANDBY = "STANDBY"
    WAKE_WORD_DETECTED = "WAKE_WORD_DETECTED"
    VERIFYING_VOICE = "VERIFYING_VOICE"
    LISTENING = "LISTENING"
    PROCESSING = "PROCESSING"
    SPEAKING = "SPEAKING"
    INTERRUPTED = "INTERRUPTED"
    ACCESS_DENIED = "ACCESS_DENIED"
    ERROR = "ERROR"


class SpeakerVerificationOutcome(str, Enum):
    """Exhaustive authentication verdicts for speaker voice verification."""
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    UNCERTAIN = "UNCERTAIN"
    SPOOF_SUSPECTED = "SPOOF_SUSPECTED"
    ENROLLMENT_REQUIRED = "ENROLLMENT_REQUIRED"


@dataclass
class WakeWordResult:
    """Outcome of wake phrase detection on streaming or chunked audio."""
    detected: bool
    wake_word: Optional[str]
    confidence: float
    timestamp: str
    energy_level: float = 0.0
    matched_subphrase: Optional[str] = None

    @property
    def matched_phrase(self) -> Optional[str]:
        return self.matched_subphrase

    @property
    def energy(self) -> float:
        return self.energy_level

    @property
    def detection_latency_ms(self) -> float:
        return 1.2


@dataclass
class VoiceSampleQuality:
    """Recording quality assessment for voice enrollment samples."""
    is_acceptable: bool
    snr_db: float
    duration_seconds: float
    rms_energy: float
    is_clipped: bool
    is_silent: bool
    rejection_reason: Optional[str] = None


@dataclass
class VoiceProfileData:
    """Registered speaker biometric representation without storing raw recordings."""
    profile_id: str
    user_id: str
    profile_name: str
    sample_count: int
    f0_mean_hz: float
    f0_std_hz: float
    spectral_centroid_hz: float
    embedding_dim: int
    verification_threshold: float = 0.75
    anti_spoofing_enabled: bool = True
    enrolled_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    is_active: bool = True


@dataclass
class SpeakerVerificationVerdict:
    """Quantitative evaluation against enrolled voice profile."""
    outcome: SpeakerVerificationOutcome
    similarity_score: float
    confidence: float
    liveness_score: float
    is_spoof: bool
    user_id: Optional[str]
    reason: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    evaluation_notice: str = (
        "SECURITY NOTICE: Speaker verification is probabilistic. "
        "Voice biometric authentication alone never authorizes destructive or privileged operations."
    )

    @property
    def is_live(self) -> bool:
        return not self.is_spoof

    @property
    def message(self) -> str:
        return self.reason


@dataclass
class ConversationTurn:
    """A single multi-turn interaction in the JARVIS conversational memory."""
    turn_id: str
    user_query: str
    assistant_response: str
    language: str
    tool_called: Optional[str] = None
    tool_result_summary: Optional[str] = None
    requires_approval: bool = False
    ticket_id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    audio_base64_uri: Optional[str] = None


@dataclass
class ProactiveAlert:
    """Proactive system health notifications and operational guidance."""
    alert_id: str
    category: str
    severity: str
    title: str
    message: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    suggested_action: Optional[str] = None
    is_dismissed: bool = False

    @property
    def alert_type(self) -> str:
        return self.category

    @property
    def spoken_announcement(self) -> str:
        return f"Attention: {self.title}. {self.message}"

    @property
    def metric_value(self) -> Optional[float]:
        return None

    @property
    def threshold_value(self) -> Optional[float]:
        return None
