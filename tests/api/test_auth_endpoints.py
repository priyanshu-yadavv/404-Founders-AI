"""
404 FOUNDERS — Unit and Integration Tests for Authentication & Session APIs
Verifies registration, login, profile inspection, session listing, session revocation, and logout.
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


def test_auth_register_and_login_flow(client: TestClient):
    import secrets
    uname = f"testuser_{secrets.token_hex(4)}"
    email = f"{uname}@example.com"
    pwd = "SecurePassword_2026!"

    # 1. Register
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "username": uname,
            "email": email,
            "password": pwd,
            "display_name": "Test Engineer",
        },
    )
    assert reg_resp.status_code == 200, reg_resp.text
    reg_data = reg_resp.json()
    assert "token" in reg_data
    assert reg_data["username"] == uname
    assert reg_data["email"] == email
    token = reg_data["token"]

    # 2. Get profile with Bearer token
    profile_resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert profile_resp.status_code == 200
    pdata = profile_resp.json()
    assert pdata["username"] == uname
    assert pdata["is_active"] is True

    # 3. List active sessions
    sess_resp = client.get(
        "/api/v1/auth/sessions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert sess_resp.status_code == 200
    sessions = sess_resp.json()
    assert len(sessions) >= 1

    # 4. Login separately with username
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": uname, "password": pwd},
    )
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert login_data["token"].startswith("404SESS-")

    # 5. Login with invalid password
    bad_login = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": uname, "password": "WrongPassword_2026!"},
    )
    assert bad_login.status_code == 401

    # 6. Logout
    logout_resp = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout_resp.status_code == 200
    assert logout_resp.json()["status"] == "ok"


def test_auth_validation_errors(client: TestClient):
    # Short password
    bad_pwd = client.post(
        "/api/v1/auth/register",
        json={"username": "shortpwd", "email": "sp@example.com", "password": "123"},
    )
    assert bad_pwd.status_code in (400, 422)

    # Invalid username chars
    bad_uname = client.post(
        "/api/v1/auth/register",
        json={"username": "invalid username with spaces!", "email": "valid@example.com", "password": "Password123!"},
    )
    assert bad_uname.status_code in (400, 422)
