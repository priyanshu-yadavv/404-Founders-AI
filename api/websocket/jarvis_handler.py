"""
404 FOUNDERS — Real-Time WebSocket Handler for JARVIS Assistant
Provides bi-directional streaming for wake-word detection, live transcription,
tool-augmented conversational processing, barge-in interrupts, and audio responses.
"""

from __future__ import annotations

import asyncio
import base64
from datetime import datetime, timezone
import json
import time
from typing import Any, Dict, Optional

from fastapi import WebSocket, WebSocketDisconnect
from jarvis.models import JarvisState, SpeakerVerificationVerdict
from jarvis.service import JarvisService


async def handle_jarvis_websocket_session(
    websocket: WebSocket,
    services: Dict[str, Any],
) -> None:
    """
    Handle real-time WebSocket session for JARVIS voice assistant.
    Endpoint: /ws/v1/jarvis
    """
    await websocket.accept()

    jarvis_svc: Optional[JarvisService] = services.get("jarvis_service")
    if jarvis_svc is None:
        jarvis_svc = JarvisService.get_instance(
            db_manager=services.get("db_manager"),
            personal_ai_controller=services.get("personal_ai_controller"),
        )
        services["jarvis_service"] = jarvis_svc

    session_id = f"jarvis_ws_{int(time.time() * 1000)}"
    user_id = "USR-operator"
    current_state = JarvisState.STANDBY

    # Send initial connection handshake
    await websocket.send_text(
        json.dumps({
            "type": "connected",
            "session_id": session_id,
            "user_id": user_id,
            "state": current_state.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    )

    try:
        while True:
            raw_msg = await websocket.receive_text()
            try:
                data = json.loads(raw_msg)
            except Exception:
                await websocket.send_text(json.dumps({"type": "error", "message": "Malformed JSON payload"}))
                continue

            msg_type = data.get("type", "interact")

            # 1. Heartbeat Ping / Pong
            if msg_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong", "timestamp": time.time()}))
                continue

            # 2. Handshake / Init
            elif msg_type == "init":
                user_id = data.get("user_id", user_id)
                session_id = data.get("session_id", session_id)
                await websocket.send_text(json.dumps({
                    "type": "initialized",
                    "session_id": session_id,
                    "user_id": user_id,
                    "state": current_state.value,
                }))

            # 3. Barge-In Interrupt
            elif msg_type == "interrupt":
                current_state = jarvis_svc.interrupt(session_id)
                await websocket.send_text(json.dumps({
                    "type": "state_changed",
                    "state": current_state.value,
                    "interrupted": True,
                }))

            # 4. Wake-Word Check
            elif msg_type == "wake_word":
                audio_b64 = data.get("audio")
                text_hint = data.get("text_hint")
                sample_rate = int(data.get("sample_rate", 16000))

                audio_bytes = base64.b64decode(audio_b64) if audio_b64 else None
                detection = jarvis_svc.wake_detector.detect(
                    audio_bytes=audio_bytes,
                    sample_rate=sample_rate,
                    transcript_hint=text_hint,
                )

                if detection.detected:
                    current_state = JarvisState.LISTENING
                    jarvis_svc.conversation_engine.update_state(session_id, current_state)
                    await websocket.send_text(json.dumps({
                        "type": "wake_word_detected",
                        "confidence": detection.confidence,
                        "matched_phrase": detection.matched_phrase,
                        "state": current_state.value,
                    }))
                else:
                    await websocket.send_text(json.dumps({
                        "type": "wake_word_rejected",
                        "confidence": detection.confidence,
                        "state": current_state.value,
                    }))

            # 5. Speaker Verification
            elif msg_type == "verify":
                audio_b64 = data.get("audio")
                if not audio_b64:
                    await websocket.send_text(json.dumps({"type": "error", "message": "Missing audio data"}))
                    continue

                audio_bytes = base64.b64decode(audio_b64)
                verdict = jarvis_svc.verify_speaker_voice(user_id=user_id, audio_bytes=audio_bytes)
                await websocket.send_text(json.dumps({
                    "type": "verification_result",
                    "verdict": verdict.outcome.value,
                    "similarity": verdict.similarity_score,
                    "liveness": verdict.liveness_score,
                    "message": verdict.message,
                }))

            # 6. Conversational Turn (Audio or Text)
            elif msg_type in ("interact", "audio", "text"):
                t0 = time.time()
                query_text = data.get("query") or data.get("text")
                audio_b64 = data.get("audio") or data.get("data")
                language_hint = data.get("language_hint")

                # Transition state to PROCESSING
                current_state = JarvisState.PROCESSING
                jarvis_svc.conversation_engine.update_state(session_id, current_state)
                await websocket.send_text(json.dumps({
                    "type": "state_changed",
                    "state": current_state.value,
                }))

                turn_result = {}
                if audio_b64:
                    audio_bytes = base64.b64decode(audio_b64)
                    turn_result = jarvis_svc.process_voice_turn(
                        user_id=user_id,
                        audio_bytes=audio_bytes,
                        session_id=session_id,
                        transcript_hint=query_text,
                        skip_wake_word_check=True,
                    )
                elif query_text:
                    turn_result = jarvis_svc.process_text_turn(
                        user_id=user_id,
                        query=query_text,
                        session_id=session_id,
                    )
                else:
                    await websocket.send_text(json.dumps({"type": "error", "message": "No audio or text provided"}))
                    continue

                transcript = turn_result.get("transcript", "")
                reply = turn_result.get("assistant_reply", "")
                audio_res_b64 = turn_result.get("audio_base64")
                tool_called = turn_result.get("tool_called")
                tool_status = turn_result.get("tool_status")
                tool_result = turn_result.get("tool_result")

                # Send transcript update
                if transcript:
                    await websocket.send_text(json.dumps({
                        "type": "transcript",
                        "text": transcript,
                    }))

                # Send tool update if called
                if tool_called:
                    await websocket.send_text(json.dumps({
                        "type": "tool_executed",
                        "tool": tool_called,
                        "status": tool_status,
                        "result": tool_result,
                    }))

                # Transition state to SPEAKING
                current_state = JarvisState.SPEAKING
                jarvis_svc.conversation_engine.update_state(session_id, current_state)
                await websocket.send_text(json.dumps({
                    "type": "response",
                    "session_id": session_id,
                    "state": current_state.value,
                    "text": reply,
                    "audio": audio_res_b64,
                    "audio_format": "audio/wav" if audio_res_b64 else None,
                    "latency_ms": round((time.time() - t0) * 1000, 2),
                }))

                # After response, return to STANDBY
                current_state = JarvisState.STANDBY
                jarvis_svc.conversation_engine.update_state(session_id, current_state)
                await websocket.send_text(json.dumps({
                    "type": "state_changed",
                    "state": current_state.value,
                }))

            # 7. Proactive Alerts Check
            elif msg_type == "alerts_check":
                alerts = jarvis_svc.get_proactive_alerts()
                await websocket.send_text(json.dumps({
                    "type": "proactive_alerts",
                    "total": len(alerts),
                    "alerts": [
                        {
                            "id": a.alert_id,
                            "type": a.alert_type,
                            "severity": a.severity,
                            "title": a.title,
                            "message": a.message,
                            "metric_value": a.metric_value,
                            "threshold_value": a.threshold_value,
                            "spoken_announcement": a.spoken_announcement,
                            "timestamp": a.timestamp,
                        }
                        for a in alerts
                    ],
                }))

            else:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"Unsupported message type: '{msg_type}'",
                }))

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
