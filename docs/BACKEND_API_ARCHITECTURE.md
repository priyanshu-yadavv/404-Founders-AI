# 404 FOUNDERS — Backend API Architecture Specification
**Document ID:** `DOC-API-002`  
**Brand:** 404 FOUNDERS  
**Tagline:** *Intelligence Without Boundaries.*  
**Phase:** 11 — API, Frontend & Deployment  

---

## 1. Executive Summary

The 404 FOUNDERS backend architecture provides a production-grade, hardened microservice and gateway layer unifying foundation neural inference, multi-layer memory, Personal AI agent actions, multimodal processing, and cluster telemetry.

It exposes three distinct networking protocols:
1. **REST APIs:** Full OpenAPI 3.1.0 JSON-RPC and REST endpoints with strict Pydantic validation.
2. **WebSocket Gateway:** Low-latency bidirectional event and token chunk streaming (`/ws/v1/stream`, `/ws/v1/chat`).
3. **gRPC Microservice:** High-throughput internal cluster RPC contracts (`founders_service.proto`).

---

## 2. API Endpoints Catalog

### 2.1 Authentication & Session Management
- `POST /api/v1/auth/register` — Registers new user with PBKDF2-HMAC-SHA256 password hashing (100,000 iterations, 16-byte random salt).
- `POST /api/v1/auth/login` — Authenticates credentials and returns a secure bearer session token (`404SESS-...`).
- `POST /api/v1/auth/logout` — Revokes active session token.
- `GET /api/v1/auth/me` — Inspects authenticated user profile.
- `GET /api/v1/auth/sessions` — Lists all active sessions for current user.
- `DELETE /api/v1/auth/sessions/{id}` — Revokes target session.

### 2.2 Conversations & Trajectories
- `POST /api/v1/conversations` — Creates durable conversation thread.
- `GET /api/v1/conversations` — Lists user's conversation threads.
- `GET /api/v1/conversations/{id}` — Fetches specific thread metadata.
- `PATCH /api/v1/conversations/{id}` — Updates thread title or operational mode.
- `DELETE /api/v1/conversations/{id}` — Deletes thread and cascade deletes messages.
- `GET /api/v1/conversations/{id}/messages` — Lists ordered messages in thread.
- `POST /api/v1/conversations/{id}/messages` — Appends user query, executes neural inference or central router dispatch, logs activity, and returns assistant message.

### 2.3 Streaming Gateways
- `POST /api/v1/chat/stream` — Progressive token streaming via Server-Sent Events (SSE).
- `WS /ws/v1/stream` — Bidirectional WebSocket gateway for ping, telemetry, and actions.
- `WS /ws/v1/chat` — Live bidirectional chat session with progressive token chunk emissions.

### 2.4 User Settings & Activity Ledger
- `GET /api/v1/settings` — Retrieves user appearance, language, voice, and memory retention preferences.
- `PUT /api/v1/settings` — Updates user application settings.
- `GET /api/v1/activity/history` — Lists unified activity history across all subsystems with optional category filtering.

### 2.5 Health & Status
- `GET /health` & `GET /api/v1/health` — Host health, parameter counts, and compute backend status.
- `GET /api/v1/telemetry` — Live CPU vitals, physical memory usage, and memory budget protection.

---

## 3. Database Schema Migration 2

Implemented in `database/schema.py`:
- `user_accounts`: Durable identity table storing PBKDF2 password hashes, cryptographic salts, and roles.
- `user_sessions`: Active session tokens stored as SHA-256 hashes for defense-in-depth.
- `conversation_threads`: Multi-turn thread metadata with foreign keys to `user_accounts`.
- `conversation_messages`: Chronological message records with JSON metadata.
- `user_application_settings`: Per-user themes, language, voice, and retention windows.
- `activity_log_entries`: Immutable unified audit log entries.
