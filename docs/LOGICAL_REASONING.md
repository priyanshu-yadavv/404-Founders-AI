# 404 FOUNDERS — Logical Reasoning Engine Specification

**Tagline:** Intelligence Without Boundaries.  
**Module:** `core.reasoning.logical` (`LogicalReasoningEngine`)  
**Phase:** Phase 07 — Intelligence Modules  
**Status:** Implemented & Verified  

---

## 1. Architectural Scope & Objectives

The Logical Reasoning Engine provides deterministic and rule-augmented formal analysis for structured problem decomposition, unstated assumption extraction, mutual exclusion contradiction detection, deductive validity evaluation, and epistemic uncertainty quantification.

The engine explicitly refrains from emitting ungrounded internal chain-of-thought strings. Instead, it surfaces structured, auditable reasoning steps with designated inference rules (Modus Ponens, Conjunction, Syllogisms), identified boundary assumptions, and quantified uncertainty metrics.

---

## 2. Core Capabilities

### 2.1 Problem Decomposition
Decomposes compound sentences and multi-stage objectives into sequential, actionable sub-problems using logical conjunctions, sequence operators, and structural boundary delimiters.

### 2.2 Unstated Assumption Extraction
Identifies presuppositions and conditional premises using lexical trigger patterns (`assuming`, `presupposing`, `if we take for granted that`). In the absence of explicit markers, establishes standard physical and operational domain boundary constraints.

### 2.3 Contradiction Detection
Scans pairs of premises for shared subject matter exhibiting opposing polarities (e.g. `enabled` vs `disabled`, `always` vs `never`, `increases` vs `decreases`). Flagged contradictions are assigned a severity rating (`CRITICAL`, `MODERATE`, `POTENTIAL`).

### 2.4 Deductive Inference
Applies formal deductive patterns:
- **Premise Introduction:** Grounding base assertions.
- **Modus Ponens:** Given $P \to Q$ and $P$, deduces $Q$.
- **Hypothesis Verification:** Validates target conclusions against premise support graphs.

### 2.5 Candidate Solution Comparison
Evaluates alternative approaches against active boundary constraints. Calculates a normalized feasibility score in $[0.0, 1.0]$ penalized by constraint violations.

### 2.6 Epistemic Uncertainty Quantification
Quantifies systemic uncertainty from 0.0 (certain) to 1.0 (unresolved):
$$\text{Uncertainty} = \text{Base} + 0.45 \cdot \text{ContradictionPenalty} + 0.25 \cdot \text{AssumptionPenalty} + 0.25 \cdot (1 - \text{AvgConfidence})$$

---

## 3. Data Contracts & Schema

```python
@dataclass
class LogicalPremise:
    id: str
    text: str
    certainty: float = 1.0
    is_assumption: bool = False

@dataclass
class LogicalStep:
    step_number: int
    statement: str
    supported_by_premises: List[str]
    inference_rule: str
    confidence: float

@dataclass
class Contradiction:
    statement_a: str
    statement_b: str
    explanation: str
    severity: str

@dataclass
class LogicalReasoningResult:
    problem: str
    decomposed_steps: List[str]
    assumptions: List[str]
    premises: List[LogicalPremise]
    deductive_steps: List[LogicalStep]
    contradictions: List[Contradiction]
    candidate_solutions: List[CandidateSolution]
    conclusion: str
    epistemic_uncertainty: float
    summary: str
```

---

## 4. Verification & Testing

Validated in `tests/intelligence/test_logical_reasoning.py`:
- Decomposition of compound queries.
- Assumption identification across explicit and implicit prompts.
- Critical contradiction detection on mutually exclusive states.
- Modus Ponens step deduction.
- Trade-off evaluation and constraint satisfaction ranking.
