# 404 FOUNDERS — Memory Privacy, Security & Secret Sanitization
**Document ID:** DOC-MEM-004  
**Phase:** 09 — Advanced Memory & Learning Architecture  
**Status:** Approved  
**Author:** 404 FOUNDERS Cybersecurity & Privacy Engineering Group  
**Tagline:** Intelligence Without Boundaries.

---

## 1. Executive Summary

This manual specifies the security policies, tenant isolation barriers, automated credential redaction rules, and audit trails governing the **404 FOUNDERS Advanced Multi-Layer Memory System**.

The primary security objective is to ensure that confidential credentials, private cryptographic keys, authentication tokens, and sensitive client assertions are never stored in plain text, never leaked across tenant boundaries, and never executed as executable instructions.

---

## 2. Zero-Credential Invariant & Secret Scrubbing Pipeline

### 2.1 The Invariant
**Never store passwords, API keys, private keys, or session tokens in durable memory stores.**

All incoming conversational turns, working tasks, long-term records, knowledge propositions, and feedback submissions must pass synchronously through the `MemorySecurityManager.scrub_secrets()` sanitization pipeline prior to executing database write operations.

### 2.2 Redaction Patterns
The sanitization engine applies regex heuristics matching high-entropy credential patterns and standard secret token prefixes:

| Category | Detection Heuristic Pattern | Standard Replacement Token |
| :--- | :--- | :--- |
| **Private Keys** | `-----BEGIN (RSA\|EC\|DSA\|OPENSSH\|PGP) PRIVATE KEY-----[\s\S]+?-----END ...` | `[REDACTED_PRIVATE_KEY]` |
| **API Tokens** | `\b(?:sk-[a-zA-Z0-9]{20,}\|ghp_[a-zA-Z0-9]{36}\|gho_[a-zA-Z0-9]{36}\|glpat-[a-zA-Z0-9\-_]{20,})\b` | `[REDACTED_API_TOKEN]` |
| **AWS Access Keys** | `\bAKIA[0-9A-Z]{16}\b` | `[REDACTED_AWS_ACCESS_KEY]` |
| **Bearer JWTs** | `\bBearer\s+[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+\b` | `[REDACTED_BEARER_JWT]` |
| **Password Assignments** | `(?i)\b(?:password\|passwd\|secret\|api_key\|access_token\|private_key)\s*[:=]\s*['\"][^'\"]{4,}['\"]` | `[REDACTED_CREDENTIAL]` |
| **Connection URIs** | `[a-zA-Z0-9+.\-]+://[^:\s]+:[^@\s]+@[^\s]+` | `[REDACTED_CONNECTION_URI_CREDENTIALS]` |

When a secret is scrubbed, the detected category is logged in the record's metadata (`scrubbed_secrets`), allowing audit review without preserving the credential plaintext.

---

## 3. Strict Cross-User Tenant Isolation

1. **Mandatory Tenant Keys:** Every table in the database schema incorporates a non-nullable `user_id` or `session_id` tenant identifier.
2. **Access Control Enforcement:** `MemorySecurityManager.validate_user_access(requested_user_id, record_user_id)` validates tenant ownership prior to reading, modifying, or deleting memory records.
3. **Violation Handling:** Attempting to query records belonging to a different user raises `SecurityViolationError` (`HTTP 403 Forbidden`).
4. **Local Data Sovereignty:** In Personal AI Mode, all memory records remain strictly on the local host machine within the local SQLite database; no external cloud synchronizations occur without explicit cryptographic pairing.

---

## 4. Stored Memory Non-Execution Invariant

**Retrieved memory text is strictly data, never code or system commands.**

Retrieved memories and knowledge triples are formatted as string context blocks within prompting templates. The inference engine and API routes strictly forbid piping retrieved memory contents into shell execution environments (`subprocess.run`, `eval()`, `exec()`, or dynamic scripting interpreters).

---

## 5. Anti-Fabrication Guarantees (Episodic Memory)

To prevent deceptive synthetic memory claims:
- Past interactions exist only if authenticated in the immutable `episodic_events` table.
- If a user inquires whether a task, conversation, or experiment occurred, and no matching entry exists in the episodic table, the system is strictly forbidden from claiming that the event took place.
- The `verify_past_occurrence()` method returns an explicit non-occurrence verdict (`recorded: False`) with verifiable evidence citations.

---

## 6. Immutable Security & Memory Audit Ledger

All lifecycle operations on memory records are recorded in the `memory_audit_logs` table:

```sql
CREATE TABLE IF NOT EXISTS memory_audit_logs (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    session_id TEXT,
    action TEXT NOT NULL,
    memory_id TEXT,
    timestamp TEXT NOT NULL,
    details_json TEXT
);
```

### Audited Operations:
- `CREATE`: New short-term turn or long-term record saved.
- `UPDATE`: Record updated and new version incremented.
- `DELETE`: Record archived or removed.
- `CONSOLIDATE`: Automatic aging summarization or duplicate resolution.
- `CONFLICT_FLAGGED`: Contradiction detected during consolidation pass.
- `RECORD_EPISODE`: Event registered in episodic history.
- `MODEL_APPROVAL_GATE`: Governance decision recorded for continual learning job.
- `MODEL_DEPLOYED`: Model rollout transition executed.
