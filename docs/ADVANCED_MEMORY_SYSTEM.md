# 404 FOUNDERS — Advanced Multi-Layer Memory Architecture
**Document ID:** DOC-MEM-001  
**Phase:** 09 — Advanced Memory & Learning Architecture  
**Status:** Approved  
**Author:** 404 FOUNDERS Core Architecture Group  
**Tagline:** Intelligence Without Boundaries.

---

## 1. Executive Summary & Architectural Overview

The **404 FOUNDERS Advanced Multi-Layer Memory Architecture** provides an integrated, secure, multi-tier cognitive storage system designed to support both General Intelligence Mode and Personal AI Mode. Operating strictly from random initialization with zero pretrained foundation weights, the system bridges ephemeral in-context computation with durable, auditable, tenant-isolated persistent memory.

The memory hierarchy is organized into eight specialized layers:
1. **Short-Term Memory:** Session-isolated conversational context with token window limits, rolling turns, and automatic aging summarization milestones.
2. **Working Memory:** Temporary task- and session-bound scratchpad storing active objectives, intermediate computation results, dependency graphs, and pending action queues with restart recovery.
3. **Long-Term Memory:** Durable relational store for user-explicit declarations, project context, and persistent references featuring SHA-256 deduplication and version ancestry tracking.
4. **Episodic Memory:** Structured history log of events, task executions, and user interactions with **zero past-event fabrication**.
5. **Semantic & Knowledge Memory:** Propositional graph statements $(Subject \xrightarrow{Predicate} Object)$ maintaining strict epistemic boundaries between verified facts (`VERIFIED_FACT`), unverified claims (`UNVERIFIED_CLAIM`), and user assertions (`USER_STATED`).
6. **User Preference Memory:** Inspectable and editable user preferences dictating formatting style, response verbosity, technical depth, and preferred programming environments.
7. **Contextual Memory Engine:** Dynamic token-budget bounded context synthesis assembling working tasks, history, retrieved knowledge, and personalization directives into unified prompts.
8. **Memory Retrieval & Consolidation:** Hybrid BM25 lexical search combined with exponential recency decay and automated duplicate/conflict resolution.

---

## 2. Multi-Layer Memory Taxonomy

```
+---------------------------------------------------------------------------------+
|                         404 FOUNDERS CONTEXT SYNTHESIS                          |
+---------------------------------------------------------------------------------+
          |                                      |                               |
          v                                      v                               v
+-----------------------+              +-------------------+           +-------------------+
|  Short-Term Context   |              |  Working Memory   |           |  Personalization  |
| - Rolling Turn Window |              | - Active Goals    |           | - Style Directives|
| - Auto-Summarization  |              | - Intermediates   |           | - Tech Depth      |
| - Token Ceilings      |              | - Crash Recovery  |           | - Code Prefs      |
+-----------------------+              +-------------------+           +-------------------+
          |                                      |                               |
          +--------------------------------------+-------------------------------+
                                                 |
                                                 v
                       +-----------------------------------+
                       |    Hybrid Memory Retrieval Engine |
                       |    - BM25 Lexical Term Match      |
                       |    - Exp Recency Decay e^(-λ·Δt)  |
                       |    - Importance & Confidence      |
                       |    - Deterministic Fallback       |
                       +-----------------------------------+
                                                 |
                         +-----------------------+-----------------------+
                         |                                               |
                         v                                               v
        +---------------------------------+             +---------------------------------+
        |      Long-Term Storage          |             |      Episodic & Knowledge       |
        | - SHA-256 Deduplication         |             | - Proposition Triples (S-P-O)   |
        | - Immutable Version Ancestry    |             | - Claim Type Differentiation    |
        | - User-Controlled CRUD          |             | - Zero Past Fabrication Guard   |
        +---------------------------------+             +---------------------------------+
                         |                                               |
                         +-----------------------+-----------------------+
                                                 |
                                                 v
                               +-----------------------------------+
                               |     Local SQLite Engine (WAL)     |
                               |  - Foreign Key Constraints        |
                               |  - 7 Performance Indexes          |
                               |  - Append-Only Audit Logging      |
                               +-----------------------------------+
```

---

## 3. Layer Specifications

### 3.1 Short-Term Memory (`ShortTermMemory`)
- **Scope:** Session-isolated conversational turns.
- **Token Budget:** Enforces a configurable ceiling (`TOKEN_CEILING_FOR_SUMMARIZATION = 3000 tokens`).
- **Automatic Context Aging:** When turns approach token limits, the oldest 50% turns are consolidated into an active context summary milestone (`[Conversation Context Summary]: ...`), preventing context overflow and preserving earlier prompt intents.
- **Safety:** Content passes through `MemorySecurityManager.scrub_secrets()` before persistence.

### 3.2 Working Memory (`WorkingMemory`)
- **Scope:** Session- and task-isolated scratchpad.
- **Schema:** `working_memory_tasks` keyed by `(session_id, task_id)`.
- **Properties:**
  - `active_objectives`: String list of tasks to execute.
  - `intermediate_results`: JSON dictionary of intermediate calculation tensors or step outputs.
  - `dependencies`: Prerequisite tasks.
  - `pending_actions`: Uncommitted operations.
- **Crash Recovery:** Tasks survive backend restarts and resume seamlessly with existing checkpoints.

### 3.3 Long-Term Memory (`LongTermMemory`)
- **Scope:** Cross-session persistent knowledge explicitly authorized by the user.
- **Deduplication:** Computes normalized SHA-256 content hashes. Duplicate saves return existing record references without inflating storage.
- **Versioning:** Updates archive prior versions (`status='ARCHIVED'`) and create new active versions linked via `parent_version_id`.
- **Tenant Isolation:** Enforces strict user ID checks with zero cross-tenant leakage.

### 3.4 Episodic Memory (`EpisodicMemory`)
- **Scope:** Historical event trajectories and user interaction milestones.
- **Zero Past-Event Fabrication Guarantee:** The system strictly prohibits hallucinating past conversations, executed scripts, or user preferences. If an event cannot be located via lexical or similarity lookup in `episodic_events`, `verify_past_occurrence()` explicitly returns `recorded: False` with status `"No historical record matches query. Event did not occur in system logs."`

### 3.5 Semantic & Knowledge Memory (`KnowledgeMemory`)
- **Scope:** Structured entities and relational knowledge triples.
- **Epistemic Classification (`ClaimType`):**
  - `VERIFIED_FACT`: Objective, externally validated truths.
  - `UNVERIFIED_CLAIM`: Hypotheses or assertions lacking external corroboration.
  - `USER_STATED`: Declarations provided by the user.
- **Relationship Graph:** Manages directed links (`memory_relationships`) such as `CAUSES`, `DEPENDS_ON`, `PART_OF`, `CONTRADICTS`.

### 3.6 User Preference Memory (`UserPreferenceMemory`)
- **Scope:** Inspectable, editable preferences dictating generation behavior.
- **Standard Properties:**
  - `communication_style`: `"balanced"`, `"concise"`, `"detailed"`, `"academic"`.
  - `response_length`: `"short"`, `"medium"`, `"comprehensive"`.
  - `technical_depth`: `"beginner"`, `"intermediate"`, `"expert"`.
  - `code_preference`: `"python"`, `"rust"`, `"typescript"`, `"cpp"`.
  - `explanation_mode`: `"step_by_step"`, `"direct_summary"`.
- **Overrides:** Users can inspect, set, or delete any preference, immediately restoring deterministic system defaults.

---

## 4. Database Schema & Concurrency Safety

All memory layers persist to an embedded SQLite database using standard library `sqlite3` without external runtime dependencies:
- **Write-Ahead Logging (WAL):** Enabled via `PRAGMA journal_mode = WAL` to ensure concurrent reads and non-blocking writes.
- **Foreign Key Enforcement:** `PRAGMA foreign_keys = ON` guarantees referential integrity on cascading deletions.
- **Migrations:** Managed through a versioned `schema_migrations` table applying DDL statements atomically.
- **Indexes:** 7 targeted multi-column indexes (`idx_mem_user_layer`, `idx_mem_expires`, `idx_episodic_user_ts`, `idx_working_session_task`, `idx_pref_user`, `idx_feedback_user_status`, `idx_audit_user_action`) ensure fast lookup times even under extensive record volumes.

---

## 5. Architectural Invariants

1. **Zero Pretrained Weights:** All components operate from random initialization and custom algorithms.
2. **Deterministic Fallbacks:** When search queries are empty or lexical matches are zero, memory retrieval falls back to deterministic recency and importance ordering.
3. **Tenant Boundary Protection:** Any attempt to query or mutate another user's memory records raises `SecurityViolationError`.
4. **Append-Only Audit Ledger:** All creations, updates, consolidations, and deletions are permanently recorded in `memory_audit_logs`.
