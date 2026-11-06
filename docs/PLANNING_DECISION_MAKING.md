# 404 FOUNDERS — Planning & Decision-Making Engine Specification

**Tagline:** Intelligence Without Boundaries.  
**Module:** `agent.planner.planning_engine` (`PlanningDecisionEngine`)  
**Phase:** Phase 07 — Intelligence Modules  
**Status:** Implemented & Verified  

---

## 1. Architectural Scope & Objectives

The Planning and Decision-Making Engine decomposes high-level goals into directed acyclic graph (DAG) execution workflows, performs topological dependency sorting, evaluates alternative strategies, classifies risk tiers, and enforces mandatory human approval checkpoints.

---

## 2. Risk Classification & Human Approval Gating

### 2.1 Permission Tier Alignment
Subtasks are classified according to the core `PermissionTier` policy:
1. **READ_ONLY:** Non-destructive queries, environment inspection. Zero confirmation needed.
2. **PROTECTED:** Workspace modifications, code authoring, test execution.
3. **PRIVILEGED:** System configuration changes, network access, service restarts. Requires operator approval.
4. **DANGEROUS:** File deletion, disk partition modifications, irreversible database schema drops. Mandatory operator approval required.

### 2.2 Approval Gate Invariant
Any task that is classified as `PRIVILEGED` or `DANGEROUS`, or contains irreversible keywords (`delete`, `drop`, `truncate`, `format`, `wipe`, `reboot`), **cannot transition to `READY` or execute until explicit operator authorization is granted** via `grant_approval()`.

---

## 3. Dependency Sequencing & Cycle Detection

The engine executes Kahn's Algorithm for topological sorting:
- Evaluates in-degree counts for each subtask based on prerequisite dependencies.
- Dispatches tasks with `in_degree == 0` first.
- Identifies circular dependencies (`has_cycles: True`), alerting operators before execution.

---

## 4. Alternative Approach Analysis

Synthesizes multiple operational strategies for each objective:
- **Incremental Conservative Rollout:** Step-by-step with manual validation checkpoints between stages (lowest catastrophic risk).
- **Parallel Optimized Batching:** Concurrent execution of all independent non-dependent steps (fastest turnaround, moderate risk).
