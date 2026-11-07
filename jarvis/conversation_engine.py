"""
404 FOUNDERS — Real-Time JARVIS Conversation Engine
Orchestrates the complete voice-first interaction pipeline:
Microphone / Text → Wake-Word Detection → Speaker Verification ("Only My Voice")
→ Speech Recognition → Conversational Memory → Tool Bridge → Natural Response Generation
→ Speech Synthesis → Spoken Audio Delivery.

Maintains multi-turn context, follow-up tracking, barge-in interruption,
and natural conversational phrasing across English, Hindi, and Hinglish.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional, Tuple, Union
import uuid

from jarvis.models import (
    ConversationTurn,
    JarvisState,
    SpeakerVerificationOutcome,
    SpeakerVerificationVerdict,
    WakeWordResult,
)
from jarvis.speech_recognition import JarvisSTTEngine, JarvisTranscriptionResult
from jarvis.speech_synthesis import JarvisSpeechOutput, JarvisTTSEngine
from jarvis.tool_bridge import JarvisToolBridge, ToolExecutionResult
from jarvis.voice_biometrics import VoiceBiometricsEngine
from jarvis.wake_word import WakeWordDetector


@dataclass
class ConversationSession:
    """Active conversational session state and episodic turn memory."""
    session_id: str
    user_id: str
    state: JarvisState = JarvisState.STANDBY
    is_authenticated: bool = False
    language_preference: str = "auto"
    history: List[ConversationTurn] = field(default_factory=list)
    last_interaction_time: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    active_topic: Optional[str] = None
    last_tool_payload: Optional[Dict[str, Any]] = None

    @property
    def speaker_verified(self) -> bool:
        return self.is_authenticated

    @property
    def created_at(self) -> str:
        return self.last_interaction_time

    @property
    def turns(self) -> List[ConversationTurn]:
        return self.history


class JarvisConversationEngine:
    """
    Central JARVIS Conversational Assistant Engine.
    Executes real-time natural language dialogue, enforces biometric voice security,
    dispatches tools via JarvisToolBridge, and generates spoken speech outputs.
    """

    MAX_HISTORY_TURNS = 20

    def __init__(
        self,
        wake_detector: Optional[WakeWordDetector] = None,
        biometrics_engine: Optional[VoiceBiometricsEngine] = None,
        stt_engine: Optional[JarvisSTTEngine] = None,
        tts_engine: Optional[JarvisTTSEngine] = None,
        tool_bridge: Optional[JarvisToolBridge] = None,
    ) -> None:
        self.wake_detector = wake_detector or WakeWordDetector()
        self.biometrics = biometrics_engine or VoiceBiometricsEngine()
        self.stt = stt_engine or JarvisSTTEngine()
        self.tts = tts_engine or JarvisTTSEngine()
        self.tools = tool_bridge or JarvisToolBridge()

        # Active sessions cache: session_id -> ConversationSession
        self._sessions: Dict[str, ConversationSession] = {}

    def get_or_create_session(self, user_id: str, session_id: Optional[str] = None) -> ConversationSession:
        """Fetch active session or initialize a fresh standby session."""
        s_id = session_id or f"jsess_{uuid.uuid4().hex[:12]}"
        if s_id not in self._sessions:
            self._sessions[s_id] = ConversationSession(
                session_id=s_id,
                user_id=user_id,
                state=JarvisState.STANDBY,
                is_authenticated=False,
            )
        return self._sessions[s_id]

    def create_session(self, user_id: str, language_hint: str = "en", session_id: Optional[str] = None) -> ConversationSession:
        sess = self.get_or_create_session(user_id=user_id, session_id=session_id)
        sess.language_preference = language_hint
        return sess

    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        return self._sessions.get(session_id)

    def update_state(self, session_id: str, state: JarvisState) -> None:
        sess = self._sessions.get(session_id)
        if sess:
            sess.state = state

    def handle_barge_in_interrupt(self, session_id: str) -> JarvisState:
        """Handle user barge-in / speech interrupt while assistant is speaking."""
        self.tts.interrupt()
        session = self.get_or_create_session("USR-operator", session_id=session_id)
        session.state = JarvisState.INTERRUPTED
        return session.state

    def process_voice_turn(
        self,
        user_id: str,
        audio_bytes: bytes,
        session_id: Optional[str] = None,
        transcript_hint: Optional[str] = None,
        skip_wake_word_check: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute end-to-end voice turn:
        1. Wake-word detection (if in STANDBY)
        2. Speaker verification ("Only My Voice")
        3. Speech-to-Text transcription
        4. Conversational understanding & tool dispatch
        5. Natural response generation (English / Hindi / Hinglish)
        6. TTS synthesis & base64 audio return
        """
        session = self.get_or_create_session(user_id, session_id)
        now_iso = datetime.now(timezone.utc).isoformat()
        session.last_interaction_time = now_iso

        # Step 1: Wake-Word Gate (if session is not already active/listening)
        if not skip_wake_word_check and session.state == JarvisState.STANDBY:
            # Check transcript hint or raw audio
            wake_result: WakeWordResult = self.wake_detector.detect_from_transcript(transcript_hint or "")
            if not wake_result.detected:
                return {
                    "session_id": session.session_id,
                    "state": JarvisState.STANDBY.value,
                    "wake_word_detected": False,
                    "message": "Standing by. Speak 'Hey Founders' to activate.",
                }
            session.state = JarvisState.WAKE_WORD_DETECTED

        # Step 2: Speaker Verification Gate ("Only My Voice")
        session.state = JarvisState.VERIFYING_VOICE
        verdict: SpeakerVerificationVerdict = self.biometrics.verify_speaker_turn(user_id, audio_bytes)

        if verdict.outcome not in (SpeakerVerificationOutcome.VERIFIED,):
            session.state = JarvisState.ACCESS_DENIED
            session.is_authenticated = False

            # Conversational explanation of rejection
            if verdict.outcome == SpeakerVerificationOutcome.ENROLLMENT_REQUIRED:
                reply = "Voice authentication requires initial voice profile enrollment. Please complete enrollment first."
            elif verdict.outcome == SpeakerVerificationOutcome.SPOOF_SUSPECTED:
                reply = "Voice authentication rejected: acoustic liveness check failed (possible recording or synthetic audio)."
            else:
                reply = "Voice verification could not confirm your identity. Access to personal AI tools is restricted."

            tts_out = self.tts.synthesize_response(reply, language="en")
            return {
                "session_id": session.session_id,
                "state": session.state.value,
                "is_authenticated": False,
                "verification": {
                    "outcome": verdict.outcome.value,
                    "similarity": verdict.similarity_score,
                    "liveness": verdict.liveness_score,
                    "reason": verdict.reason,
                },
                "assistant_response": reply,
                "audio_base64_uri": tts_out.audio_base64_uri,
            }

        # Verification Succeeded
        session.is_authenticated = True
        session.state = JarvisState.LISTENING

        # Step 3: Speech-to-Text Transcription
        transcription: JarvisTranscriptionResult = self.stt.transcribe_audio_bytes(
            audio_bytes,
            context_transcription_hint=transcript_hint,
        )
        user_query = transcription.text.strip()
        detected_lang = transcription.detected_language

        if not user_query:
            session.state = JarvisState.STANDBY
            return {
                "session_id": session.session_id,
                "state": session.state.value,
                "is_authenticated": True,
                "message": "Voice verified, but no spoken command was detected.",
            }

        # Step 4: Conversational Intent, Multi-Turn Context & Tool Calling
        session.state = JarvisState.PROCESSING
        return self._execute_conversational_step(session, user_query, detected_lang)

    def process_text_turn(
        self,
        user_id: str,
        query: str,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process authenticated conversational turn from text input.
        """
        session = self.get_or_create_session(user_id, session_id)
        session.is_authenticated = True
        session.state = JarvisState.PROCESSING
        lang = self.stt.identify_language(query)
        return self._execute_conversational_step(session, query, lang)

    def _execute_conversational_step(
        self,
        session: ConversationSession,
        user_query: str,
        language: str,
    ) -> Dict[str, Any]:
        """Coordinate multi-turn dialogue, tool execution, and voice output synthesis."""
        now_iso = datetime.now(timezone.utc).isoformat()
        clean_q = self._strip_wake_words(user_query)

        # Multi-turn context resolution (follow-up handling)
        resolved_query = self._resolve_follow_up(clean_q, session)

        # Tool execution via JarvisToolBridge
        tool_res: ToolExecutionResult = self.tools.map_and_execute_tool(
            user_id=session.user_id,
            query=resolved_query,
            session_id=session.session_id,
        )

        session.last_tool_payload = tool_res.raw_payload
        session.active_topic = tool_res.intent.value

        # Select conversational phrasing based on detected language
        if language in ("hi", "hinglish"):
            response_text = tool_res.conversational_explanation_hi
        else:
            response_text = tool_res.conversational_explanation_en

        # Synthesize speech
        session.state = JarvisState.SPEAKING
        tts_out: JarvisSpeechOutput = self.tts.synthesize_response(
            text=response_text,
            language="hi" if language == "hi" else "en",
        )

        # Record conversation turn in memory
        turn = ConversationTurn(
            turn_id=f"turn_{uuid.uuid4().hex[:8]}",
            user_query=user_query,
            assistant_response=response_text,
            language=language,
            tool_called=tool_res.tool_name,
            tool_result_summary=tool_res.output_summary,
            requires_approval=tool_res.requires_approval,
            ticket_id=tool_res.ticket_id,
            timestamp=now_iso,
            audio_base64_uri=tts_out.audio_base64_uri,
        )

        session.history.append(turn)
        if len(session.history) > self.MAX_HISTORY_TURNS:
            session.history.pop(0)

        session.state = JarvisState.STANDBY

        return {
            "session_id": session.session_id,
            "turn_id": turn.turn_id,
            "state": session.state.value,
            "is_authenticated": session.is_authenticated,
            "user_query": user_query,
            "detected_language": language,
            "assistant_response": response_text,
            "assistant_reply": response_text,
            "transcript": user_query,
            "tool_called": tool_res.tool_name,
            "tool_status": "APPROVAL_REQUIRED" if tool_res.requires_approval else ("SUCCESS" if tool_res.success else "FAILED"),
            "tool_result": tool_res.raw_payload,
            "requires_ticket": tool_res.requires_approval,
            "required_permission": tool_res.risk_tier,
            "ticket_request_id": tool_res.ticket_id,
            "audio_base64": tts_out.audio_base64,
            "tool_execution": {
                "tool_name": tool_res.tool_name,
                "intent": tool_res.intent.value,
                "risk_tier": tool_res.risk_tier,
                "requires_approval": tool_res.requires_approval,
                "ticket_id": tool_res.ticket_id,
                "success": tool_res.success,
            },
            "audio": {
                "base64_uri": tts_out.audio_base64_uri,
                "duration_seconds": tts_out.duration_seconds,
                "voice_id": tts_out.voice_id,
            },
            "timestamp": now_iso,
        }

    def _strip_wake_words(self, query: str) -> str:
        """Remove leading wake phrases like 'Hey Founders', 'Founders', 'Computer'."""
        q = query.strip()
        for ww in self.wake_detector.wake_words:
            pattern = r"^(?:hey\s+)?" + re.escape(ww) + r"[,:\s]*"
            q = re.sub(pattern, "", q, flags=re.IGNORECASE).strip()
        return q if q else query.strip()

    def _resolve_follow_up(self, query: str, session: ConversationSession) -> str:
        """Resolve conversational anaphora and follow-up references."""
        q_lower = query.lower()
        if not session.history:
            return query

        last_turn = session.history[-1]

        # Follow-up: "Inme se..." or "Which process..."
        if any(w in q_lower for w in ["inme se", "which of these", "tell me more", "aur batao", "explain this"]):
            if session.active_topic == "DIAGNOSE_SYSTEM_PERFORMANCE":
                return "show top memory consuming processes details"
            elif session.active_topic == "INSPECT_HARDWARE":
                return "show detailed cpu and ram telemetry"

        return query
