"""
404 FOUNDERS — Phase 13 JARVIS-Style Conversational Assistant Subsystem
Tagline: Intelligence Without Boundaries.
"""

from jarvis.conversation_engine import ConversationSession, JarvisConversationEngine
from jarvis.models import (
    ConversationTurn,
    JarvisState,
    ProactiveAlert,
    SpeakerVerificationOutcome,
    SpeakerVerificationVerdict,
    VoiceProfileData,
    VoiceSampleQuality,
    WakeWordResult,
)
from jarvis.proactive import ProactiveAssistanceEngine, ProactiveConfig
from jarvis.service import JarvisService
from jarvis.speech_recognition import JarvisSTTEngine, JarvisTranscriptionResult
from jarvis.speech_synthesis import JarvisSpeechOutput, JarvisTTSEngine
from jarvis.tool_bridge import JarvisToolBridge, ToolExecutionResult
from jarvis.voice_biometrics import VoiceBiometricsEngine
from jarvis.wake_word import WakeWordDetector

__all__ = [
    "ConversationSession",
    "ConversationTurn",
    "JarvisConversationEngine",
    "JarvisService",
    "JarvisSpeechOutput",
    "JarvisState",
    "JarvisSTTEngine",
    "JarvisToolBridge",
    "JarvisTranscriptionResult",
    "JarvisTTSEngine",
    "ProactiveAlert",
    "ProactiveAssistanceEngine",
    "ProactiveConfig",
    "SpeakerVerificationOutcome",
    "SpeakerVerificationVerdict",
    "ToolExecutionResult",
    "VoiceBiometricsEngine",
    "VoiceProfileData",
    "VoiceSampleQuality",
    "WakeWordDetector",
    "WakeWordResult",
]
