"""
404 FOUNDERS — WebSocket Streaming Handler
Provides real-time bidirectional communication, token streaming,
processing status notifications, and agent telemetry feeds.
"""

import asyncio
from datetime import datetime, timezone
import json
import time
from typing import Any, Dict, List, Optional, Set

from fastapi import WebSocket, WebSocketDisconnect
from core.intelligence.central_router import CentralIntelligenceRouter
from core.intelligence.neural_core import NeuralCore
from neural_architecture.inference import InferenceEngine
from personal_ai.controller import PersonalAIController
from tokenizer import CustomBPETokenizer


class WebSocketConnectionManager:
    """Manages active WebSocket client connections and broadcasts."""

    def __init__(self) -> None:
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new client connection."""
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        """Deregister a disconnected client."""
        self.active_connections.discard(websocket)

    async def send_json(self, websocket: WebSocket, data: Dict[str, Any]) -> None:
        """Send a JSON payload to a specific client."""
        await websocket.send_text(json.dumps(data))

    async def broadcast_json(self, data: Dict[str, Any]) -> None:
        """Broadcast a message to all active clients."""
        dead_connections: List[WebSocket] = []
        payload = json.dumps(data)
        for conn in self.active_connections:
            try:
                await conn.send_text(payload)
            except Exception:
                dead_connections.append(conn)

        for conn in dead_connections:
            self.disconnect(conn)


ws_manager = WebSocketConnectionManager()


async def handle_websocket_session(
    websocket: WebSocket,
    services: Dict[str, Any],
) -> None:
    """
    Main WebSocket communication loop:
    Parses client actions, generates progressive status updates,
    streams tokens, and emits completion receipts.
    """
    await ws_manager.connect(websocket)

    try:
        # Send initial connection handshake
        await ws_manager.send_json(
            websocket,
            {
                "type": "connected",
                "service": "404_FOUNDERS_STREAM_GATEWAY",
                "message": "Connected to 404 FOUNDERS WebSocket Gateway",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "supported_actions": ["chat", "personal_ai", "telemetry", "ping"],
            },
        )

        while True:
            raw_text = await websocket.receive_text()
            try:
                msg = json.loads(raw_text)
            except json.JSONDecodeError:
                await ws_manager.send_json(
                    websocket,
                    {"type": "error", "message": "Invalid JSON payload received"},
                )
                continue

            action = msg.get("action", "chat")

            if action == "ping":
                await ws_manager.send_json(
                    websocket,
                    {"type": "pong", "timestamp": time.time()},
                )

            elif action == "telemetry":
                pai: Optional[PersonalAIController] = services.get("personal_ai_controller")
                telemetry_data = {}
                if pai:
                    telemetry_data = pai.system_info.get_hardware_telemetry()
                else:
                    telemetry_data = {"status": "operational"}
                start_time = services.get("start_time", time.time())
                uptime = time.time() - start_time
                await ws_manager.send_json(
                    websocket,
                    {
                        "type": "telemetry",
                        "data": telemetry_data,
                        "uptime_seconds": uptime,
                        "timestamp": time.time(),
                    },
                )

            elif action == "personal_ai":
                query = msg.get("query", "")
                user_id = msg.get("user_id", "operator")
                session_id = msg.get("session_id")
                pai: Optional[PersonalAIController] = services.get("personal_ai_controller")

                if not pai:
                    await ws_manager.send_json(
                        websocket,
                        {"type": "error", "message": "Personal AI controller not initialized"},
                    )
                    continue

                await ws_manager.send_json(
                    websocket,
                    {
                        "type": "status",
                        "stage": "INSPECTING",
                        "detail": f"Routing local query '{query[:40]}'...",
                    },
                )
                await asyncio.sleep(0.05)

                try:
                    res = pai.process_request(user_id=user_id, query=query, session_id=session_id)
                    await ws_manager.send_json(
                        websocket,
                        {
                            "type": "done",
                            "action": "personal_ai",
                            "intent": res.intent,
                            "response": res.assistant_response,
                            "action_taken": res.action_taken,
                            "data_payload": res.data_payload,
                            "requires_approval": res.requires_approval,
                            "pending_ticket_id": res.pending_ticket_id,
                        },
                    )
                except Exception as e:
                    await ws_manager.send_json(
                        websocket,
                        {"type": "error", "message": str(e)},
                    )

            elif action == "chat":
                query = msg.get("query", "").strip()
                if not query:
                    await ws_manager.send_json(
                        websocket,
                        {"type": "error", "message": "Query cannot be empty"},
                    )
                    continue

                try:
                    router: Optional[CentralIntelligenceRouter] = services.get("central_router")
                    inference: Optional[InferenceEngine] = services.get("inference_engine")
                    tokenizer: Optional[CustomBPETokenizer] = services.get("tokenizer")

                    # Step 1: Emit status
                    await ws_manager.send_json(
                        websocket,
                        {
                            "type": "status",
                            "stage": "ANALYZING",
                            "detail": "Analyzing intent with Central Intelligence Router...",
                        },
                    )
                    await asyncio.sleep(0.01)

                    # Step 2: Route request
                    routed_module = "neural_core"
                    if router:
                        plan = router.classify_intent(query)
                        routed_module = plan.primary_engine

                    await ws_manager.send_json(
                        websocket,
                        {
                            "type": "status",
                            "stage": "PROCESSING",
                            "detail": f"Synthesizing response via module: {routed_module}",
                        },
                    )
                    await asyncio.sleep(0.01)

                    # Step 3: Stream tokens
                    if router:
                        dispatch_res = router.dispatch(query=query)
                        res_text = dispatch_res.combined_summary
                        words = res_text.split(" ")
                        for w in words:
                            piece = w + " "
                            await ws_manager.send_json(
                                websocket,
                                {"type": "token", "content": piece},
                            )
                            await asyncio.sleep(0.01)

                        await ws_manager.send_json(
                            websocket,
                            {
                                "type": "done",
                                "action": "chat",
                                "full_response": res_text,
                                "module": routed_module,
                                "tokens_generated": len(words),
                            },
                        )
                    elif tokenizer and inference:
                        encoded = tokenizer.encode(query)
                        raw_ids = getattr(encoded, "ids", None) or (encoded if isinstance(encoded, list) else [1, 2, 3])
                        token_ids = list(raw_ids)[:32]
                        if not token_ids:
                            token_ids = [1]

                        new_tokens = inference.generate_greedy_tokens(token_ids, max_new_tokens=8)
                        generated_slice = new_tokens[len(token_ids):] if len(new_tokens) > len(token_ids) else new_tokens
                        streamed_words = []

                        for tok in generated_slice:
                            piece = tokenizer.decode([tok]) if hasattr(tokenizer, "decode") else f" tok_{tok}"
                            streamed_words.append(piece)
                            await ws_manager.send_json(
                                websocket,
                                {"type": "token", "content": piece},
                            )
                            await asyncio.sleep(0.01)

                        full_text = "".join(streamed_words)
                        await ws_manager.send_json(
                            websocket,
                            {
                                "type": "done",
                                "action": "chat",
                                "full_response": full_text,
                                "module": routed_module,
                                "tokens_generated": len(generated_slice),
                            },
                        )
                    else:
                        # Fallback token streaming
                        fallback_response = f"404 FOUNDERS Intelligence ({routed_module}): Processed '{query}'."
                        words = fallback_response.split(" ")
                        for w in words:
                            await ws_manager.send_json(
                                websocket,
                                {"type": "token", "content": w + " "},
                            )
                            await asyncio.sleep(0.01)

                        await ws_manager.send_json(
                            websocket,
                            {
                                "type": "done",
                                "action": "chat",
                                "full_response": fallback_response,
                                "module": routed_module,
                            },
                        )
                except Exception as exc:
                    await ws_manager.send_json(
                        websocket,
                        {"type": "error", "message": str(exc)},
                    )

            else:
                await ws_manager.send_json(
                    websocket,
                    {"type": "error", "message": f"Unsupported action: '{action}'"},
                )

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        ws_manager.disconnect(websocket)
