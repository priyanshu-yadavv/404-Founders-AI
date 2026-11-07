# 404 FOUNDERS — Production Deployment Guide
**Document ID:** `DOC-DEP-001`  
**Brand:** 404 FOUNDERS  
**Tagline:** *Intelligence Without Boundaries.*  
**Phase:** 11 — API, Frontend & Deployment  

---

## 1. Architecture Overview

The 404 FOUNDERS deployment topology is designed for high reliability, minimal resource footprint, and zero unauthorized public exposure. The containerized stack consists of three coordinated micro-services:

```
[ Client Browser / Desktop ]
             │
             ▼ Port 80 (HTTP)
   ┌───────────────────┐
   │    Nginx Proxy    │ (Reverse Proxy, SSL termination, WebSocket upgrade)
   └─────────┬─────────┘
             ├──────────────────────────┐
             ▼                          ▼
   ┌───────────────────┐      ┌───────────────────┐
   │ Frontend Service  │      │  Backend Service  │
   │ (Node.js Alpine)  │      │ (FastAPI, PyTorch)│
   │    Port 5173      │      │  Port 8000/50051  │
   └───────────────────┘      └─────────┬─────────┘
                                        ▼
                              ┌───────────────────┐
                              │  SQLite Database  │
                              │ (data/memory.db)  │
                              └───────────────────┘
```

---

## 2. Container Images

### 2.1 Backend (`Dockerfile.backend`)
- **Base Image:** `python:3.11-slim`
- **Security:** Non-root execution under unprivileged system user `founders` (`uid=1001`, `gid=1001`).
- **Optimization:** Multi-stage caching; PyTorch CPU installed with zero-CUDA bloat.
- **Ports:** `8000` (FastAPI REST/WS) and `50051` (gRPC cluster service).
- **Healthcheck:** Automatic polling on `http://127.0.0.1:8000/health`.

### 2.2 Frontend (`Dockerfile.frontend`)
- **Base Image:** `node:20-alpine`
- **Security:** Runs under default non-root user `node`.
- **Runtime:** Lightweight, zero-dependency Node.js HTTP static server (`server.js`).
- **Port:** `5173`.
- **Healthcheck:** `wget --spider -q http://localhost:5173/`.

### 2.3 Reverse Proxy (`nginx/nginx.conf`)
- Buffers client connections and manages WebSocket upgrade headers (`Upgrade: websocket`).
- Proxies `/api/`, `/health`, `/docs` to backend on port 8000.
- Proxies all UI requests to frontend on port 5173.

---

## 3. Pre-Flight Verification & Launch Commands

### 3.1 Automated Pre-Flight Check
Run the pre-flight verification script before container builds:
```bash
python3 scripts/deploy_check.py
```
This inspects:
1. Python environment and runtime version.
2. PyTorch installation and CPU tensor execution.
3. SQLite database connectivity and migration level.
4. Tokenizer vocab size and Neural Core parameter counts.
5. Frontend UI asset integrity.
6. Deployment configuration existence and syntax.

### 3.2 Local Development Launch
```bash
docker compose up -d --build
```
Access at `http://localhost:5173` (Frontend) and `http://localhost:8000/docs` (Backend).

### 3.3 Production Deployment Launch
```bash
./scripts/run_production.sh
```
Or directly with Compose:
```bash
docker compose -f docker-compose.prod.yml up -d --build
```
Access unified interface at `http://localhost` (proxied through Nginx).

---

## 4. Resource Guardrails & Failure Modes

| Service | CPU Limit | Memory Limit | Restart Policy | Failure Behavior |
|---|---|---|---|---|
| `backend` | 4.0 Cores | 8,192 MB | `always` | OOM-Guard aborts excessive generation requests before container memory exhaustion. |
| `frontend` | 1.0 Cores | 512 MB | `always` | Instant restart on Node process failure. |
| `proxy` | 1.0 Cores | 256 MB | `always` | Independent Nginx reverse proxy with healthcheck dependency tracking. |
