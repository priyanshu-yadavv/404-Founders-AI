"""
404 FOUNDERS — Deployment Architecture & Configuration Tests
Verifies Dockerfile syntax, Compose YAML specifications, Nginx reverse proxy routing,
and automated pre-flight deployment check execution.
"""

from pathlib import Path
import subprocess
import sys
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_dockerfile_backend_configuration():
    dockerfile = REPO_ROOT / "Dockerfile.backend"
    assert dockerfile.is_file()
    content = dockerfile.read_text()

    assert "FROM python:3.11-slim" in content
    assert "EXPOSE 8000 50051" in content
    assert "HEALTHCHECK" in content
    assert "useradd -u 1001" in content
    assert "USER founders" in content
    assert "uvicorn" in content


def test_dockerfile_frontend_configuration():
    dockerfile = REPO_ROOT / "Dockerfile.frontend"
    assert dockerfile.is_file()
    content = dockerfile.read_text()

    assert "FROM node:20-alpine" in content
    assert "EXPOSE 5173" in content
    assert "HEALTHCHECK" in content
    assert "USER node" in content
    assert 'CMD ["node", "server.js"]' in content


def test_docker_compose_development_structure():
    compose_path = REPO_ROOT / "docker-compose.yml"
    assert compose_path.is_file()
    with open(compose_path, "r") as f:
        data = yaml.safe_load(f)

    services = data.get("services", {})
    assert "backend" in services
    assert "frontend" in services

    # Backend ports & healthcheck
    backend = services["backend"]
    assert "8000:8000" in backend["ports"]
    assert "50051:50051" in backend["ports"]
    assert "healthcheck" in backend

    # Frontend depends on backend
    frontend = services["frontend"]
    assert "5173:5173" in frontend["ports"]
    assert "backend" in frontend.get("depends_on", {})


def test_docker_compose_production_structure():
    compose_path = REPO_ROOT / "docker-compose.prod.yml"
    assert compose_path.is_file()
    with open(compose_path, "r") as f:
        data = yaml.safe_load(f)

    services = data.get("services", {})
    assert "backend" in services
    assert "frontend" in services
    assert "proxy" in services

    # Resource limits on production backend
    backend = services["backend"]
    assert backend["restart"] == "always"
    limits = backend.get("deploy", {}).get("resources", {}).get("limits", {})
    assert limits.get("cpus") == "4.0"
    assert limits.get("memory") == "8192M"

    # Proxy configuration
    proxy = services["proxy"]
    assert "80:80" in proxy["ports"]
    assert proxy["restart"] == "always"


def test_nginx_proxy_configuration():
    nginx_conf = REPO_ROOT / "nginx/nginx.conf"
    assert nginx_conf.is_file()
    content = nginx_conf.read_text()

    assert "upstream backend_nodes" in content
    assert "upstream frontend_nodes" in content
    assert "location /api/" in content
    assert "location /ws/" in content
    assert "proxy_set_header Upgrade $http_upgrade" in content
    assert "location /" in content


def test_production_env_example():
    env_example = REPO_ROOT / ".env.production.example"
    assert env_example.is_file()
    content = env_example.read_text()

    required_vars = [
        "FOUNDERS_ENV=production",
        "PORT=8000",
        "FRONTEND_PORT=5173",
        "GRPC_PORT=50051",
        "FOUNDERS_ALLOWED_ORIGINS=",
        "FOUNDERS_DB_PATH=",
        "FOUNDERS_DEFAULT_USER=",
        "FOUNDERS_DEFAULT_PASSWORD=",
    ]
    for var in required_vars:
        assert var in content


def test_deploy_check_script_execution():
    script_path = REPO_ROOT / "scripts/deploy_check.py"
    res = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, res.stderr
    assert "VERIFICATION REPORT" in res.stdout
    assert "DEPLOYMENT READY" in res.stdout
