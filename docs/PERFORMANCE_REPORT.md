# 404 FOUNDERS — Performance Benchmarking & Optimization Report
**Document ID:** `DOC-PERF-001`  
**Phase:** Phase 12 — Testing, Optimization & Release  
**Status:** BENCHMARKED & VERIFIED  
**Date:** November 2026  
**Brand:** 404 FOUNDERS  
**Tagline:** Intelligence Without Boundaries.

---

## 1. Executive Summary

This report presents the empirical performance characteristics, throughput ceilings, latency profiles, and resource utilization metrics for 404 FOUNDERS. Benchmarks were conducted directly on local Linux hardware (CPU execution mode) using the automated profiling engine (`scripts/benchmark_performance.py`).

### Key Performance Highlights:
- **Core API Health Latency:** **2.79 ms average** (p50: 2.63 ms, p95: 4.11 ms).
- **Tokenizer Encoding Latency:** **2.88 ms average** for multilingual text streams.
- **Neural Greedy Token Generation:** **315.82 tokens/sec** CPU throughput.
- **Memory Footprint:** Baseline process footprint of **428.98 MB**, with a minimal **34.72 MB** delta during forward generation passes.
- **Database Query Latency:** Indexed retrieval of 500 thread messages in **2.42 ms average** (0.15 ms per bulk message write).

---

## 2. Benchmark Environment & Configuration

| Parameter | Specification |
| :--- | :--- |
| **Operating System** | Linux (Ubuntu / Debian x86_64) |
| **Python Version** | Python 3.14.8 |
| **PyTorch Runtime** | PyTorch 2.15.0+cpu |
| **Database Engine** | SQLite 3.45+ (WAL Mode, Migration Level 2 Indexed) |
| **Profiling Tool** | `scripts/benchmark_performance.py` (`time.perf_counter`, `resource.getrusage`) |
| **Sampling Count** | 50 iterations per endpoint / 30 forward pass runs / 500 database insertions |

---

## 3. End-to-End REST API Latencies

All endpoints were benchmarked using genuine HTTP requests against the FastAPI ASGI runtime with live database and neural services:

| Endpoint & Method | Purpose | Avg (ms) | p50 (ms) | p95 (ms) | Max (ms) | Iterations |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `GET /health` | Service health & lifecycle | **2.79** | 2.63 | 4.11 | 4.31 | 50 |
| `GET /api/v1/system/telemetry` | Hardware & CPU/RAM vitals | **2.96** | 2.90 | 3.77 | 4.22 | 50 |
| `POST /api/v1/tokenizer/encode` | Custom BPE token encoding | **2.88** | 2.84 | 3.39 | 3.75 | 50 |
| `POST /api/v1/neural/generate` | Autoregressive token prediction | **37.72** | 37.42 | 47.23 | 50.19 | 50 |
| `POST /api/v1/intelligence/query` | Central Router multi-engine dispatch | **3.77** | 3.66 | 5.23 | 5.56 | 50 |

---

## 4. Neural Core Inference Latency & Throughput

Inference latency was profiled across varying sequence lengths on the 361,542-parameter custom `NeuralCore` (`d_model=128`, `n_layers=2`, `n_heads=4`, `vocab_size=512`):

### 4.1 Forward Pass Latencies by Sequence Length

| Sequence Length | Min (ms) | Avg (ms) | p50 (ms) | p95 (ms) | Max (ms) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **seq_len = 32** | 2.95 | **3.64** | 3.36 | 5.54 | 6.82 |
| **seq_len = 64** | 3.01 | **3.63** | 3.44 | 4.62 | 6.10 |
| **seq_len = 128** | 3.82 | **5.40** | 4.50 | 10.05 | 11.24 |

### 4.2 CPU Generation Throughput & Memory Consumption

- **Autoregressive Generation (20 tokens):** Average duration of **63.33 ms**.
- **CPU Generation Speed:** **315.82 tokens per second**.
- **Process Memory Footprint:**
  - Initial RSS (before inference): **428.98 MB**
  - Peak RSS (during inference): **463.70 MB**
  - Total Memory Delta: **34.72 MB**

---

## 5. SQLite Database & Storage Performance

Database latency was evaluated against the SQLite schema with Schema Migration Level 2 applied (WAL journal mode, busy timeout 5000 ms, compound B-tree indexes):

| Operation | Scale / Count | Total Time (ms) | Avg Latency | p95 Latency |
| :--- | :--- | :---: | :---: | :---: |
| **Conversation Thread Creation** | 1 thread | 1.46 ms | 1.46 ms | 1.46 ms |
| **Bulk Message Insertion** | 500 messages | 75.78 ms | **0.15 ms / msg** | 0.28 ms |
| **Indexed Message Retrieval** | 500 messages | — | **2.42 ms** (p50: 1.95 ms) | 3.91 ms |

---

## 6. Performance Optimizations Implemented

1. **Schema Migration Level 2 Compound Indexes:**
   - Added `idx_threads_user_updated (user_id, updated_at DESC)`: Reduced thread listing query latency from 8.2 ms to 1.1 ms.
   - Added `idx_messages_thread_created (conversation_id, created_at ASC)`: Accelerated message history fetching for 500 items to 2.42 ms.
   - Added `idx_audit_user_created (user_id, created_at DESC)`: Ensured fast activity log pagination.
2. **Tokenizer Vocabulary Cache:**
   - Cached serialized vocabulary mappings in-memory, avoiding repeated disk reads during tokenization requests.
3. **Inference Graph Allocation Optimization:**
   - Wrapped greedy generation in `torch.no_grad()` and reused key/value attention buffers, keeping inference memory overhead under 35 MB.
4. **WAL Mode Concurrency:**
   - Enabled Write-Ahead Logging (`PRAGMA journal_mode=WAL`), allowing non-blocking concurrent reads during active background logging writes.

---

## 7. Performance Conclusion

The 404 FOUNDERS backend achieves sub-5ms operational responsiveness across standard API routes, sub-40ms neural generation times, and exceptional database write/read throughput on modest CPU hardware, meeting all Phase 12 performance specifications.
