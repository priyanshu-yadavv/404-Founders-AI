# 404 FOUNDERS — Development Standards & Engineering Guidelines

**Document ID:** `DOC-STANDARDS-001`  
**Status:** Engineering Governance Baseline (Phase 02 Baseline)  
**Authors:** Chief Software Architect & Principal AI Systems Engineer  

---

## 1. Programming Languages & Polyglot Strategy

404 FOUNDERS leverages a targeted polyglot architecture with strict boundaries:

| Language | Primary Domain | Usage Boundaries |
|---|---|---|
| **Python (3.11+)** | Primary Orchestration & ML Core | All architecture logic, agent planning, data pipelines, API services |
| **Rust** | Performance & Tokenizer Engine | Custom BPE tokenizer (`tokenizers-rs`), high-throughput file parsers |
| **C++ (C++20)** | Native Inference & OS Shims | Low-level hardware bindings, CPU AVX2 quantized kernels, memory buffers |
| **CUDA (C++/PTX)** | GPU Acceleration Kernels | Custom attention kernels (MMA/FlashAttention), fused SwiGLU / RMSNorm |
| **TypeScript (v5+)**| Frontend & Client User Interfaces | React/Next.js client interface, desktop Tauri frontend |
| **SQL** | Structured Persistence | SQLite metadata schemas, DuckDB columnar analytical queries |

**Engineering Rule:** Python is the primary orchestration language. C++, CUDA, and Rust are reserved strictly for components that genuinely require low-level memory layout control or raw hardware vectorization.

---

## 2. Framework Isolation Policy: PyTorch vs. JAX

To avoid catastrophic memory fragmentation and cross-framework conversion overhead:
1. **Zero Dynamic Interoperability:** PyTorch tensors and JAX arrays must **never** be passed across subsystem boundaries during a single execution run.
2. **Abstract Interface Boundary:** All models conform to `neural_architecture/interfaces.py` (`NeuralModuleInterface` and `ModelBackendEngine`). The active backend is selected at boot time via `FOUNDERS_COMPUTE_BACKEND`.
3. **Hardware Alignment:** PyTorch is the primary backend for multi-GPU Slurm cluster training; JAX is used for functional research and mathematical verification.

---

## 3. Code Formatting, Linting & Type-Checking

All Python source code must comply with the following automated standards:

### 3.1 Code Style & Linting
- **Formatter:** `black` and `ruff` with a target line length of **100 characters**.
- **Import Sorting:** `isort` configured with multi-line output mode 3 (vertical hanging indent).
- **Linter:** `ruff` enforcing flake8, bugbear, comprehension, and pyupgrade rules:
  ```bash
  ruff check .
  ```

### 3.2 Strict Static Type Checking
- **Type Checker:** `mypy` operating with strict mode enabled:
  ```bash
  mypy core/ neural_architecture/ security/ agent/ configs/ tests/
  ```
- **Rules:**
  - All public function arguments and return types must be explicitly annotated.
  - Avoid untyped `Any` where concrete generic types can be specified.
  - Use `from typing import Optional, Dict, List, Tuple, Any, Callable`.

---

## 4. Structured Logging Standards

- **Zero Print Statements:** Standard `print()` statements are prohibited in production modules.
- **Logger Retrieval:** Modules must obtain a structured logger via `core/logging.py`:
  ```python
  from core.logging import setup_logger
  logger = setup_logger("founders404.module_name")
  ```
- **Structured Fields:** Use trace IDs and dictionary payloads to facilitate machine ingestion:
  ```python
  logger.info("Executed tool successfully", extra={"extra_data": {"tool": "sys_mon", "duration_ms": 14}})
  ```

---

## 5. Exception Handling Standards

- **Unified Hierarchy:** All custom exceptions must inherit from `FoundersBaseException` defined in `core/exceptions.py`.
- **Structured Taxonomy:**
  - `ConfigurationError`: Missing or invalid configuration parameters.
  - `ArchitectureError`: Neural network shape mismatches or backend incompatibilities.
  - `MemorySubsystemError`: Context overflow or retrieval index failures.
  - `SecurityViolationError`: Unauthorized operations, permission failures, or prompt injection.
  - `ToolExecutionError`: Agent tool runtime failures.
- **No Bare Excepts:** Catching bare `except:` or silencing exceptions without logging is strictly forbidden.

---

## 6. Configuration & Environment Variables

- **Centralized Config:** Configuration must be loaded via `core/config.py` (`SystemConfig.from_env()` or `SystemConfig.from_file()`).
- **No Hardcoded Values:** Port numbers, URLs, directory paths, and thresholds must never be hardcoded in module source files.
- **Environment Prefixes:** All environment variables use the `FOUNDERS_` prefix (e.g. `FOUNDERS_ENV`, `FOUNDERS_COMPUTE_BACKEND`).
- **Secret Protection:** `.env` files must remain strictly in `.gitignore`. Use `.env.example` as the canonical schema template.

---

## 7. Testing Standards & Integrity

- **Directory Layout:** Tests are organized in `tests/`:
  - `tests/unit/`: Module-level logic, configuration, exceptions, logging.
  - `tests/integration/`: Cross-subsystem workflows and data pipelines.
  - `tests/security/`: Permission checks, prompt injection scanners, audit logs.
  - `tests/architecture/`: Repository consistency, import integrity, and structure checks.
- **Integrity Rule:** **Never create fake tests that claim AI model functionality works when it is not yet implemented.** Tests must strictly validate existing, implemented code.
- **Execution:** Tests must pass cleanly with:
  ```bash
  pytest
  ```

---

## 8. Git Workflow & Governance

1. **Single Unified Repository:** All work lives within `404-FOUNDERS` on branch `main`.
2. **Phase-Wise Commits:** Commit messages follow `phase-XX: <description>` (e.g. `phase-02: establish project architecture and workspace`).
3. **Documentation Updates:** Every phase commit must update `PHASE_STATUS.md`, `DEVELOPMENT_LOG.md`, `CHANGELOG.md`, and `README.md`.
4. **Approval Gate:** Never push to the remote repository without explicit user review and confirmation.
