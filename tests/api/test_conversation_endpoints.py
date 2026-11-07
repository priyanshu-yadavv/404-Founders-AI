"""
404 FOUNDERS — Unit and Integration Tests for Conversation, Settings & Activity APIs
Verifies threads CRUD, messages trajectory, user settings, SSE streaming, and activity logs.
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


def test_conversation_thread_lifecycle(client: TestClient):
    # 1. Create thread
    create_resp = client.post(
        "/api/v1/conversations",
        json={"title": "Architecture Design Review", "mode": "GENERAL"},
    )
    assert create_resp.status_code == 200, create_resp.text
    thread = create_resp.json()
    assert thread["title"] == "Architecture Design Review"
    assert thread["mode"] == "GENERAL"
    thread_id = thread["id"]

    # 2. List threads
    list_resp = client.get("/api/v1/conversations")
    assert list_resp.status_code == 200
    threads = list_resp.json()
    assert any(t["id"] == thread_id for t in threads)

    # 3. Get specific thread
    get_resp = client.get(f"/api/v1/conversations/{thread_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == thread_id

    # 4. Patch thread
    patch_resp = client.patch(
        f"/api/v1/conversations/{thread_id}",
        json={"title": "Updated Architecture Review", "mode": "CODING"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["title"] == "Updated Architecture Review"
    assert patch_resp.json()["mode"] == "CODING"

    # 5. Send message and receive response
    msg_resp = client.post(
        f"/api/v1/conversations/{thread_id}/messages",
        json={"content": "Analyze system requirements for high throughput"},
    )
    assert msg_resp.status_code == 200, msg_resp.text
    msg_data = msg_resp.json()
    assert msg_data["conversation_id"] == thread_id
    assert msg_data["sender"] == "assistant"
    assert len(msg_data["content"]) > 0

    # 6. List messages
    msgs_list_resp = client.get(f"/api/v1/conversations/{thread_id}/messages")
    assert msgs_list_resp.status_code == 200
    msgs = msgs_list_resp.json()
    assert len(msgs) >= 2  # user message and assistant message
    assert msgs[0]["sender"] == "user"
    assert msgs[1]["sender"] == "assistant"

    # 7. Delete thread
    del_resp = client.delete(f"/api/v1/conversations/{thread_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["deleted"] is True


def test_user_settings_endpoints(client: TestClient):
    # 1. Get settings
    get_resp = client.get("/api/v1/settings")
    assert get_resp.status_code == 200
    settings = get_resp.json()
    assert "theme_preference" in settings
    assert "language" in settings

    # 2. Update settings
    put_resp = client.put(
        "/api/v1/settings",
        json={"theme_preference": "dark", "language": "en", "voice_enabled": True},
    )
    assert put_resp.status_code == 200
    updated = put_resp.json()
    assert updated["theme_preference"] == "dark"
    assert updated["voice_enabled"] is True


def test_activity_history_endpoints(client: TestClient):
    hist_resp = client.get("/api/v1/activity/history")
    assert hist_resp.status_code == 200
    data = hist_resp.json()
    assert "total_count" in data
    assert "entries" in data
    assert isinstance(data["entries"], list)


def test_sse_streaming_endpoint(client: TestClient):
    stream_resp = client.post(
        "/api/v1/chat/stream",
        json={"query": "Hello 404 FOUNDERS", "mode": "GENERAL"},
    )
    assert stream_resp.status_code == 200
    assert "text/event-stream" in stream_resp.headers.get("content-type", "")
    content = stream_resp.text
    assert "event: status" in content or "event: token" in content
    assert "event: done" in content
