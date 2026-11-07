# 404 FOUNDERS — Local Setup, Operations & Deployment Guide
**Document ID:** `DOC-OPS-001`  
**Phase:** Phase 12 — Testing, Optimization & Release  
**Status:** COMPLETE & VERIFIED  
**Date:** November 2026  
**Brand:** 404 FOUNDERS  
**Tagline:** Intelligence Without Boundaries.

---

## 1. System Requirements & Prerequisites

Before setting up 404 FOUNDERS locally, ensure your host machine satisfies the following hardware and software requirements:

| Component | Minimum Requirement | Recommended Specification |
| :--- | :--- | :--- |
| **Operating System** | Linux (Ubuntu 22.04+, Debian 12+), macOS 13+, Windows 11 WSL2 | Linux x86_64 or aarch64 |
| **Python** | Python 3.10 to 3.14 | Python 3.14.x |
| **Node.js & npm** | Node.js 18.x LTS, npm 9.x | Node.js 20.x LTS |
| **RAM** | 4 GB | 8 GB or higher |
| **Storage** | 2 GB free space | SSD storage with WAL support |
| **GPU (Optional)** | CPU execution supported natively | NVIDIA GPU with CUDA 12+ (for pretraining) |

---

## 2. Quick-Start Local Installation

### Step 1: Clone Repository & Enter Directory
```bash
git clone https://github.com/priyanshu-yadavv/404-Founders-AI.git
cd "404 Founders AI"
```

### Step 2: Set Up Python Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> [!NOTE]
> If your system Python packages reside in `.venv/lib/python3.14/site-packages`, you can export your `PYTHONPATH` or prefix commands:
> ```bash
> export PYTHONPATH="./.venv/lib/python3.14/site-packages:."
> ```

### Step 3: Install Frontend Dependencies
```bash
cd frontend
npm install
cd ..
```

---

## 3. Pre-Flight Verification & Health Check

Execute the comprehensive deployment pre-flight validator to verify Python, PyTorch, SQLite schema, Neural Core, and frontend assets:

```bash
python3 scripts/deploy_check.py
```

Expected output:
```
======================================================================
 404 FOUNDERS — PRE-FLIGHT DEPLOYMENT VERIFICATION REPORT
 Tagline: Intelligence Without Boundaries.
======================================================================
[✓] PYTHON: PASS
[✓] TORCH_RUNTIME: PASS
[✓] DATABASE: PASS
[✓] NEURAL_CORE: PASS
[✓] FRONTEND_ASSETS: PASS
[✓] DEPLOYMENT_CONFIGS: PASS
----------------------------------------------------------------------
Verification completed in 1.303s. Verdict: DEPLOYMENT READY
======================================================================
```

---

## 4. Launching Backend & Frontend Services

### Option A: Standard Two-Process Local Launch

**Terminal 1 — FastAPI Backend (Port 8000):**
```bash
PYTHONPATH="./.venv/lib/python3.14/site-packages:." python3 scripts/run_backend.py
```
- Interactive Swagger UI: `http://localhost:8000/docs`
- Redoc API Documentation: `http://localhost:8000/redoc`
- System Health Check: `http://localhost:8000/health`

**Terminal 2 — Warm Neutral Frontend (Port 3000):**
```bash
cd frontend
npm start
```
- Browser Interface: `http://localhost:3000`

---

## 5. Verification, Benchmarking & Backup Commands

### 5.1 Run Complete Automated Test Suite (330 Tests)
```bash
PYTHONPATH="./.venv/lib/python3.14/site-packages:." pytest tests/ -v
```

### 5.2 Run Defensive Security Audit Suite
```bash
PYTHONPATH="./.venv/lib/python3.14/site-packages:." pytest tests/security/test_security_audit.py -v
```

### 5.3 Run Performance Benchmarks
Measures API response times, neural forward passes, CPU generation throughput, and database queries:
```bash
PYTHONPATH="./.venv/lib/python3.14/site-packages:." python3 scripts/benchmark_performance.py
```
*Results are exported to `benchmarks/performance_results.json`.*

### 5.4 Run AI Quality & Multi-Domain Evaluation
Evaluates all 10 intelligence domains with deterministic scoring and baseline reporting:
```bash
PYTHONPATH="./.venv/lib/python3.14/site-packages:." python3 scripts/evaluate_ai_quality.py
```
*Results are exported to `benchmarks/ai_quality_report.json`.*

### 5.5 Perform Live Atomic Database Backup
Backs up SQLite database in WAL mode using `sqlite3.Connection.backup` with integrity verification:
```bash
python3 scripts/backup_database.py
```
*Backups are saved and verified in `backups/memory_backup_<timestamp>.db`.*

---

## 6. Troubleshooting Common Issues

### Issue 1: Port Already in Use (Port 8000 or Port 3000)
- **Symptom:** `OSError: [Errno 98] Address already in use`
- **Solution:**
  ```bash
  # Check which process is occupying the port
  lsof -i :8000
  lsof -i :3000
  # Terminate stale development process
  kill -9 <PID>
  ```

### Issue 2: ModuleNotFoundError for PyTorch or FastAPI
- **Symptom:** `ModuleNotFoundError: No module named 'torch'`
- **Solution:** Ensure `PYTHONPATH` includes the virtual environment site-packages:
  ```bash
  export PYTHONPATH="./.venv/lib/python3.14/site-packages:."
  ```

### Issue 3: Database Locked or Schema Migration Failure
- **Symptom:** `sqlite3.OperationalError: database is locked`
- **Solution:** SQLite is configured with WAL mode and a 5000 ms busy timeout. If an unclosed process holds a transaction:
  ```bash
  # Verify database integrity
  python3 scripts/backup_database.py
  ```

### Issue 4: CORS Errors Between Frontend and Backend
- **Symptom:** Browser console reports `Access-Control-Allow-Origin` blocked
- **Solution:** The frontend uses a reverse proxy in `frontend/server.js` forwarding `/api/*` to `http://127.0.0.1:8000`. Access the app through `http://localhost:3000` rather than opening `index.html` as a `file://` URL.
