"""
404 FOUNDERS — WebSocket Streaming Gateway Tests
Verifies real-time bidirectional communication over /ws/v1/stream and /ws/v1/chat.
"""

import pytest
from fastapi.testclient import TestClient
from api.rest.app import create_app, initialize_runtime_services


@pytest.fixture(scope="module")
def client():
    services = initialize_runtime_services()
    app = create_app(services=services)
    with TestClient(app) as test_client:
        yield test_client


def test_websocket_ping_and_telemetry(client: TestClient):
    with client.websocket_connect("/ws/v1/stream") as websocket:
        # Connected event
        init_msg = websocket.receive_json()
        assert init_msg["type"] == "connected"
        assert init_msg["service"] == "404_FOUNDERS_STREAM_GATEWAY"

        # Ping
        websocket.send_json({"action": "ping"})
        pong_msg = websocket.receive_json()
        assert pong_msg["type"] == "pong"

        # Telemetry
        websocket.send_json({"action": "telemetry"})
        telem_msg = websocket.receive_json()
        assert telem_msg["type"] == "telemetry"
        assert "uptime_seconds" in telem_msg


def test_websocket_chat_streaming(client: TestClient):
    with client.websocket_connect("/ws/v1/chat") as websocket:
        # Connected event
        init_msg = websocket.receive_json()
        assert init_msg["type"] == "connected"

        # Send chat message
        websocket.send_json({
            "action": "chat",
            "query": "Initialize system verification",
            "user_id": "operator",
        })

        # Collect events until done
        events = []
        for _ in range(30):
            msg = websocket.receive_json()
            events.append(msg)
            if msg.get("type") in ("done", "error"):
                break

        types = [e.get("type") for e in events]
        assert "status" in types
        assert "done" in types
        # Check that we received at least one token chunk or status
        assert any(e.get("type") == "token" for e in events) or any(e.get("type") == "status" for e in events)
