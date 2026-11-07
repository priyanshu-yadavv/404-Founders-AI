# 404 FOUNDERS — Security Architecture & Guidelines
**Document ID:** `DOC-SEC-002`  
**Brand:** 404 FOUNDERS  
**Tagline:** *Intelligence Without Boundaries.*  
**Phase:** 11 — API, Frontend & Deployment  

---

## 1. Authentication & Cryptography Invariants

### 1.1 Password Storage
- **Algorithm:** PBKDF2 with HMAC-SHA256 (`PBKDF2-HMAC-SHA256`).
- **Work Factor:** 100,000 iterations.
- **Salt Generation:** Unique 16-byte cryptographically secure random salt generated via `secrets.token_bytes(16)` per account.
- **Comparison:** Constant-time verification using `secrets.compare_digest` to eliminate timing side-channel attacks.
- **Strict Invariant:** Plaintext passwords are NEVER stored, printed in logs, or returned in API responses.

### 1.2 Session Token Lifecycle
- **Token Generation:** 32-byte cryptographic entropy tokens prefixed with `404SESS-...`.
- **Hashed Storage:** Tokens are hashed using SHA-256 before storage in SQLite `user_sessions(token_hash)`. Even in the event of database exfiltration, plaintext session tokens cannot be recovered.
- **Expiration:** Default TTL of 86,400 seconds (24 hours).
- **Revocation:** Explicit single-session revocation (`DELETE /api/v1/auth/sessions/{id}`) and global user session revocation (`POST /api/v1/auth/logout`).

---

## 2. API & Network Hardening

### 2.1 CORS Security
- Allowed origins are restricted by default to explicit localhost endpoints (`http://localhost:5173`, `http://127.0.0.1:5173`, `http://localhost:3000`, `http://127.0.0.1:3000`, `http://localhost:8000`, `http://127.0.0.1:8000`).
- Configurable via `FOUNDERS_ALLOWED_ORIGINS` in `.env.production`. Wildcard `*` origins are blocked when credentials are enabled.

### 2.2 Shell Command & Path Sanitization
- All Personal AI system actions pass through `security.sanitization.validate_shell_command` before human approval tickets are issued.
- Arbitrary code execution, shell piping, and forbidden paths (`/etc/shadow`, `/root`, `~/.ssh`) are blocked at the boundary.
- Filesystem inspection is strictly confined to the repository root directory with parent traversal (`..`) blocked.

### 2.3 Container Isolation
- Docker containers run as unprivileged users (`founders` UID 1001 on backend, `node` on frontend).
- Root filesystem is read-only where appropriate with write mounts strictly limited to `/app/data` and `/app/logs`.
- Nginx proxy strips internal headers and enforces `X-Frame-Options: SAMEORIGIN` and `X-Content-Type-Options: nosniff`.
