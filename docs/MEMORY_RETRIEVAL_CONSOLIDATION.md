# 404 FOUNDERS — Memory Retrieval & Consolidation Engine
**Document ID:** DOC-MEM-002  
**Phase:** 09 — Advanced Memory & Learning Architecture  
**Status:** Approved  
**Author:** 404 FOUNDERS Retrieval & Cognitive Systems Group  
**Tagline:** Intelligence Without Boundaries.

---

## 1. Executive Summary

This specification defines the mathematical and algorithmic architecture of the **404 FOUNDERS Hybrid Memory Retrieval Engine** and the **Memory Consolidation & Conflict Detection Subsystem**.

The retrieval engine provides multi-dimensional ranking across lexical overlap, semantic metadata, importance weighting, confidence scores, and exponential temporal recency decay. The consolidation engine executes automated background maintenance passes to merge near-duplicate memories and detect explicit semantic contradictions without silent data overwrites.

---

## 2. Hybrid Retrieval Mathematical Formulation

The hybrid relevance score $S(d, q)$ for a memory document record $d$ given an input query $q$ is defined as:

$$S(d, q) = w_{lex} \cdot S_{lex}(d, q) + w_{imp} \cdot \text{Importance}(d) + w_{conf} \cdot \text{Confidence}(d) + w_{rec} \cdot S_{rec}(d)$$

Where:
- $w_{lex} = 0.50$: Weighting assigned to BM25-style lexical term matching.
- $w_{imp} = 0.20$: Weighting assigned to author/system importance $(0.0 \le \text{Importance} \le 1.0)$.
- $w_{conf} = 0.15$: Weighting assigned to epistemic confidence $(0.0 \le \text{Confidence} \le 1.0)$.
- $w_{rec} = 0.15$: Weighting assigned to exponential recency decay.

$$\sum_{i} w_i = 0.50 + 0.20 + 0.15 + 0.15 = 1.00$$

### 2.1 Lexical Scoring Function $S_{lex}(d, q)$
Text normalization tokenizes the query into lowercase terms $q = \{t_1, t_2, \dots, t_k\}$, removing common English stopwords. The score computes sub-linear term frequency saturation over the document content, summary, tags, and relational predicates:

$$S_{lex}(d, q) = \frac{\sum_{t \in q} \ln(1 + \text{TF}(t, d))}{\max(1.0, |q| \cdot \ln(1 + 3))}$$

The resulting $S_{lex}(d, q)$ is clamped to the range $[0.0, 1.0]$.

### 2.2 Exponential Recency Decay $S_{rec}(d)$
To ensure recent user interactions and updated facts are prioritized while older deprecated facts gracefully decay in relevance, recency is formulated as an exponential decay over elapsed time:

$$S_{rec}(d) = \exp\left(-\lambda \cdot \Delta t_{hours}\right)$$

Where:
- $\Delta t_{hours} = \frac{T_{now} - T_{updated}}{3600 \text{ seconds}}$
- $\lambda = 0.005 \text{ hour}^{-1}$ (gentle decay half-life of approximately 138 hours / 5.7 days).

### 2.3 Deterministic Fallback Strategy
When a query contains no search tokens (e.g., initial session startup or ambient background context retrieval), the lexical component is omitted, and records are ranked deterministically by recency and importance:

$$S_{fallback}(d) = 0.50 \cdot S_{rec}(d) + 0.30 \cdot \text{Importance}(d) + 0.20 \cdot \text{Confidence}(d)$$

---

## 3. Memory Consolidation & Conflict Detection Engine

The **Memory Consolidation Engine** (`MemoryConsolidationEngine`) operates periodic maintenance passes over active memory records.

```
+-------------------------------------------------------------------------------+
|                      MEMORY CONSOLIDATION PIPELINE                            |
+-------------------------------------------------------------------------------+
                                       |
                                       v
                    +-------------------------------------+
                    |   Fetch Active Records (LTM, KM)    |
                    +-------------------------------------+
                                       |
                                       v
                    +-------------------------------------+
                    |   Pairwise Sequence & Entity Check  |
                    +-------------------------------------+
                                       |
             +-------------------------+-------------------------+
             |                                                   |
             v                                                   v
   [Similarity >= 0.88]                               [Contradiction Detected]
             |                                                   |
             v                                                   v
+-----------------------------+                     +-----------------------------+
|    Duplicate Resolution     |                     |    Conflict Flagging        |
| - Archive older record      |                     | - Mark status to            |
| - Keep newer active record  |                     |   'CONFLICT_DETECTED'       |
| - Insert 'DUPLICATE_OF'     |                     | - NEVER silently overwrite! |
|   relationship link         |                     | - Insert 'CONTRADICTS' link |
+-----------------------------+                     +-----------------------------+
             |                                                   |
             +-------------------------+-------------------------+
                                       |
                                       v
                    +-------------------------------------+
                    |     Consolidation Summary Report    |
                    |     & Security Audit Event Log      |
                    +-------------------------------------+
```

### 3.1 Deduplication Algorithm
1. Computes character-level sequence matcher ratio $R = \text{SequenceMatcher}(content_a, content_b)$.
2. If $R \ge 0.88$:
   - The older record (lower `updated_at`) is transitioned to `status = 'ARCHIVED'`.
   - The newer record remains `status = 'ACTIVE'`.
   - A relational link `(older_id) -[DUPLICATE_OF]-> (newer_id)` is recorded with confidence 1.0.

### 3.2 Conflict Detection Rules & Non-Overwriting Invariant
**Strict Invariant:** The system must NEVER silently delete or overwrite user statements when contradictions occur.

1. **Knowledge Graph Contradictions:**
   When two active records assert the same Subject and Predicate but different Object values:
   $$\text{Subject}(a) = \text{Subject}(b) \land \text{Predicate}(a) = \text{Predicate}(b) \land \text{Object}(a) \neq \text{Object}(b)$$
   Both records are immediately flagged with `status = 'CONFLICT_DETECTED'`.
2. **Preference Contradictions:**
   When two active records express mutually exclusive user preferences on common tags (e.g., "prefer Rust" vs "prefer Python"), both records are flagged.
3. **Auditing & Relationship:**
   A directed `CONTRADICTS` link is persisted in `memory_relationships`, and an audit event (`CONFLICT_FLAGGED`) is recorded. The system prompts the user or surfaces the conflict in the frontend rather than outputting deceptive assertions.

---

## 4. Performance & Query Isolation Guarantees

- All retrieval and consolidation queries filter strictly by `user_id`.
- Composite indexing on `(user_id, memory_layer, status)` guarantees $O(\log N)$ scan times.
- Context assembly enforces strict token ceilings, dynamically trimming conversational history when total synthesized tokens exceed prompt limits.
