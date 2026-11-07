#!/usr/bin/env bash
# =============================================================================
# 404 FOUNDERS — Production Startup Script
# Validates pre-flight conditions and orchestrates containerized deployment
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "======================================================================"
echo " 404 FOUNDERS — Starting Production Orchestration"
echo " Tagline: Intelligence Without Boundaries."
echo "======================================================================"

# 1. Run automated pre-flight checks
echo "[1/4] Running pre-flight verification checks..."
if command -v python3 >/dev/null 2>&1; then
    python3 "$SCRIPT_DIR/deploy_check.py"
else
    echo "[!] python3 not found locally; skipping host pre-flight check."
fi

# 2. Check for Docker and Docker Compose
echo "[2/4] Checking Docker runtime prerequisites..."
if ! command -v docker >/dev/null 2>&1; then
    echo "[ERROR] Docker is not installed or not in PATH."
    echo "Install Docker Engine from https://docs.docker.com/engine/install/"
    exit 1
fi

COMPOSE_CMD=""
if docker compose version >/dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE_CMD="docker-compose"
else
    echo "[ERROR] Neither 'docker compose' nor 'docker-compose' was found."
    exit 1
fi
echo "Using: $COMPOSE_CMD"

# 3. Environment configuration template check
echo "[3/4] Checking environment configuration..."
if [ ! -f ".env.production" ]; then
    echo "[INFO] .env.production not found. Initializing from .env.production.example..."
    cp .env.production.example .env.production
    echo "[IMPORTANT] Default credentials generated in .env.production. Review before external exposure."
fi

# 4. Launch Production Containers
echo "[4/4] Launching production cluster with Nginx proxy and resource limits..."
$COMPOSE_CMD -f docker-compose.prod.yml up -d --build

echo ""
echo "======================================================================"
echo " ✓ 404 FOUNDERS Production Deployment Successfully Initiated"
echo "======================================================================"
echo "  Web Interface   : http://localhost (via Nginx proxy)"
echo "  Backend API     : http://localhost/api/v1"
echo "  Health Endpoint : http://localhost/health"
echo "  API Docs        : http://localhost/docs"
echo "======================================================================"
