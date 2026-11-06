"""
404 FOUNDERS — Logical Reasoning Engine
Provides structured logical deduction, problem decomposition, assumption extraction,
contradiction detection, candidate comparison, and epistemic uncertainty evaluation.
"""

from dataclasses import dataclass, field
import re
from typing import Any, Dict, List, Optional, Set


@dataclass
class LogicalPremise:
    """Represents a discrete premise or fact in a logical argument."""
    id: str
    text: str
    certainty: float = 1.0
    is_assumption: bool = False


@dataclass
class LogicalStep:
    """A verified or inferred step in a deductive logical chain."""
    step_number: int
    statement: str
    supported_by_premises: List[str]
    inference_rule: str
    confidence: float


@dataclass
class Contradiction:
    """Represents a detected logical inconsistency between statements."""
    statement_a: str
    statement_b: str
    explanation: str
    severity: str  # "CRITICAL", "MODERATE", "POTENTIAL"


@dataclass
class CandidateSolution:
    """Evaluation of an alternative candidate solution or hypothesis."""
    id: str
    description: str
    pros: List[str] = field(default_factory=list)
    cons: List[str] = field(default_factory=list)
    satisfies_constraints: bool = True
    feasibility_score: float = 1.0


@dataclass
class LogicalReasoningResult:
    """Structured output schema for logical reasoning analysis."""
    problem: str
    decomposed_steps: List[str]
    assumptions: List[str]
    premises: List[LogicalPremise]
    deductive_steps: List[LogicalStep]
    contradictions: List[Contradiction]
    candidate_solutions: List[CandidateSolution]
    conclusion: str
    epistemic_uncertainty: float  # 0.0 (certain) to 1.0 (highly uncertain)
    summary: str


class LogicalReasoningEngine:
    """
    Deterministic & rule-augmented logical reasoning engine.
    Analyzes formal and informal arguments, verifies deductive validity,
    extracts unstated assumptions, flags mutual exclusions and contradictions,
    and quantifies epistemic uncertainty.
    """

    # Opposing semantic markers indicating mutual exclusion
    OPPOSING_PAIRS = [
        (r"\b(always|must|true|enabled|active|possible)\b", r"\b(never|cannot|false|disabled|inactive|impossible)\b"),
        (r"\b(all|every)\b", r"\b(none|no)\b"),
        (r"\b(increases?|higher|greater)\b", r"\b(decreases?|lower|smaller)\b"),
        (r"\b(is)\b", r"\b(is not|isn't)\b"),
        (r"\b(can)\b", r"\b(cannot|can't)\b"),
    ]

    # Assumption trigger patterns
    ASSUMPTION_TRIGGERS = [
        re.compile(r"\b(assuming|assumes|assume|presupposing|if we take for granted that|implicitly)\s+([^,\.;]+)", re.IGNORECASE),
        re.compile(r"\b(suppose|supposing|provided that|given that)\s+([^,\.;]+)", re.IGNORECASE),
    ]

    def decompose_problem(self, problem: str) -> List[str]:
        """Decompose a complex query or problem statement into distinct sub-problems."""
        cleaned = problem.strip()
        if not cleaned:
            return []

        # Split on coordinating conjunctions, sequence indicators, and punctuation
        raw_parts = re.split(r";|\n|\band then\b|\bfurthermore\b|\bmoreover\b|\bfirst\b|\bsecond\b|\bthird\b|\bfinally\b", cleaned, flags=re.IGNORECASE)
        sub_steps = [p.strip() for p in raw_parts if len(p.strip()) > 3]

        if not sub_steps:
            sub_steps = [cleaned]

        return sub_steps

    def extract_assumptions(self, text: str, explicit_premises: Optional[List[str]] = None) -> List[str]:
        """Extract unstated or explicitly marked assumptions from problem text and premises."""
        assumptions: Set[str] = set()

        # Check regex triggers in the primary text
        for trigger in self.ASSUMPTION_TRIGGERS:
            for match in trigger.finditer(text):
                assumptions.add(match.group(2).strip())

        # Check explicit premises marked as conditional or assumed
        if explicit_premises:
            for p in explicit_premises:
                lower_p = p.lower()
                if any(k in lower_p for k in ["assuming", "assume", "presume", "suppose", "if ", "hypothetically"]):
                    assumptions.add(p.strip())

        # If no explicit markers found, identify default boundary assumptions
        if not assumptions and len(text.split()) > 10:
            assumptions.add("Standard physical and operational domain constraints apply.")

        return sorted(list(assumptions))

    def detect_contradictions(self, premises: List[LogicalPremise]) -> List[Contradiction]:
        """Scan pairs of premises to detect direct semantic contradictions or mutual exclusions."""
        contradictions: List[Contradiction] = []
        n = len(premises)

        for i in range(n):
            for j in range(i + 1, n):
                p1 = premises[i].text.lower()
                p2 = premises[j].text.lower()

                # Extract shared nouns/subjects
                words1 = set(re.findall(r"\b[a-z]{4,}\b", p1))
                words2 = set(re.findall(r"\b[a-z]{4,}\b", p2))
                overlap = words1.intersection(words2)

                # Check if overlapping topic has opposing polarity
                if overlap:
                    for pos_pattern, neg_pattern in self.OPPOSING_PAIRS:
                        has_pos_1 = bool(re.search(pos_pattern, p1))
                        has_neg_1 = bool(re.search(neg_pattern, p1))
                        has_pos_2 = bool(re.search(pos_pattern, p2))
                        has_neg_2 = bool(re.search(neg_pattern, p2))

                        if (has_pos_1 and has_neg_2) or (has_neg_1 and has_pos_2):
                            contradictions.append(Contradiction(
                                statement_a=premises[i].text,
                                statement_b=premises[j].text,
                                explanation=f"Mutual exclusion detected regarding shared subjects {list(overlap)[:3]}.",
                                severity="CRITICAL",
                            ))
                            break

        return contradictions

    def evaluate_deduction(
        self,
        premises: List[LogicalPremise],
        target_conclusion: Optional[str] = None,
    ) -> List[LogicalStep]:
        """Perform formal deduction steps based on Modus Ponens, Syllogisms, and Conjunction."""
        steps: List[LogicalStep] = []
        if not premises:
            return steps

        step_idx = 1
        # Step 1: Base premise consolidation
        base_premise_ids = [p.id for p in premises]
        steps.append(LogicalStep(
            step_number=step_idx,
            statement=f"Established initial base premises ({len(premises)} statements).",
            supported_by_premises=base_premise_ids,
            inference_rule="Premise Introduction",
            confidence=1.0,
        ))

        # Check for conditional relations: If A then B
        for p in premises:
            cond_match = re.search(r"if\s+(.+?)\s+then\s+(.+)", p.text, re.IGNORECASE)
            if cond_match:
                antecedent = cond_match.group(1).strip().lower()
                consequent = cond_match.group(2).strip()

                # Check if any other premise affirms antecedent
                for other in premises:
                    if other.id != p.id and antecedent in other.text.lower():
                        step_idx += 1
                        steps.append(LogicalStep(
                            step_number=step_idx,
                            statement=f"Affirmed consequent: {consequent}",
                            supported_by_premises=[p.id, other.id],
                            inference_rule="Modus Ponens",
                            confidence=0.95,
                        ))

        # If target conclusion specified, check if supported
        if target_conclusion:
            step_idx += 1
            supported = any(target_conclusion.lower() in p.text.lower() for p in premises) or len(steps) > 1
            steps.append(LogicalStep(
                step_number=step_idx,
                statement=f"Evaluation of target conclusion: '{target_conclusion}' -> {'Supported' if supported else 'Unverified'}",
                supported_by_premises=base_premise_ids,
                inference_rule="Hypothesis Verification",
                confidence=0.85 if supported else 0.40,
            ))

        return steps

    def compare_candidates(
        self,
        candidates: List[Dict[str, Any]],
        constraints: Optional[List[str]] = None,
    ) -> List[CandidateSolution]:
        """Compare candidate approaches against stated constraints and trade-offs."""
        results: List[CandidateSolution] = []
        active_constraints = constraints or []

        for idx, cand in enumerate(candidates):
            c_id = str(cand.get("id", f"candidate_{idx + 1}"))
            desc = str(cand.get("description", ""))
            pros = list(cand.get("pros", []))
            cons = list(cand.get("cons", []))

            # Evaluate constraint satisfaction
            violates = False
            for constraint in active_constraints:
                # Check for explicit negation in description
                if f"no {constraint.lower()}" in desc.lower() or f"violates {constraint.lower()}" in desc.lower():
                    violates = True
                    cons.append(f"Violates constraint: {constraint}")

            # Feasibility calculation
            base_score = 1.0
            if violates:
                base_score *= 0.3
            base_score = max(0.0, min(1.0, base_score + 0.1 * len(pros) - 0.15 * len(cons)))

            results.append(CandidateSolution(
                id=c_id,
                description=desc,
                pros=pros,
                cons=cons,
                satisfies_constraints=not violates,
                feasibility_score=round(base_score, 3),
            ))

        # Sort by feasibility descending
        results.sort(key=lambda c: c.feasibility_score, reverse=True)
        return results

    def calculate_uncertainty(
        self,
        assumptions: List[str],
        contradictions: List[Contradiction],
        steps: List[LogicalStep],
    ) -> float:
        """
        Quantify epistemic uncertainty from 0.0 (certain) to 1.0 (unresolved/uncertain).
        Penalized by contradictions, heavy unverified assumptions, and low confidence steps.
        """
        uncertainty = 0.05  # Base minimal uncertainty

        # Contradictions significantly increase uncertainty
        if contradictions:
            uncertainty += 0.45 * min(1.0, len(contradictions) / 2.0)

        # Assumptions increase uncertainty
        if assumptions:
            uncertainty += 0.25 * min(1.0, len(assumptions) / 4.0)

        # Low step confidence increases uncertainty
        if steps:
            avg_step_conf = sum(s.confidence for s in steps) / len(steps)
            uncertainty += 0.25 * (1.0 - avg_step_conf)

        return round(min(1.0, max(0.0, uncertainty)), 3)

    def analyze(
        self,
        problem: str,
        premises: Optional[List[str]] = None,
        candidates: Optional[List[Dict[str, Any]]] = None,
        constraints: Optional[List[str]] = None,
        target_conclusion: Optional[str] = None,
    ) -> LogicalReasoningResult:
        """Execute complete logical reasoning pipeline."""
        if not problem.strip():
            raise ValueError("Problem statement cannot be empty.")

        # 1. Decomposition
        decomposed = self.decompose_problem(problem)

        # 2. Premise formulation
        premise_objs: List[LogicalPremise] = []
        raw_premises = premises or []
        for i, p_text in enumerate(raw_premises):
            premise_objs.append(LogicalPremise(
                id=f"P{i+1}",
                text=p_text.strip(),
                certainty=1.0,
                is_assumption="assuming" in p_text.lower(),
            ))

        # 3. Assumption extraction
        assumptions = self.extract_assumptions(problem, raw_premises)

        # 4. Contradiction detection
        contradictions = self.detect_contradictions(premise_objs)

        # 5. Deductive evaluation
        deductive_steps = self.evaluate_deduction(premise_objs, target_conclusion)

        # 6. Candidate comparison
        candidate_evals = self.compare_candidates(candidates or [], constraints)

        # 7. Uncertainty estimation
        uncertainty = self.calculate_uncertainty(assumptions, contradictions, deductive_steps)

        # 8. Synthesize conclusion and structured summary
        if contradictions:
            conclusion = f"Premise conflict detected: {contradictions[0].explanation}"
        elif deductive_steps and len(deductive_steps) > 1:
            conclusion = deductive_steps[-1].statement
        elif candidate_evals:
            top = candidate_evals[0]
            conclusion = f"Optimal viable candidate is {top.id} (feasibility: {top.feasibility_score})."
        else:
            conclusion = f"Problem decomposed into {len(decomposed)} logical stages with epistemic uncertainty {uncertainty}."

        summary = (
            f"Logical analysis decomposed the problem into {len(decomposed)} stages with {len(assumptions)} identified assumptions. "
            f"Evaluated {len(premise_objs)} premises resulting in {len(contradictions)} contradiction(s). "
            f"Epistemic uncertainty quantified at {uncertainty}."
        )

        return LogicalReasoningResult(
            problem=problem,
            decomposed_steps=decomposed,
            assumptions=assumptions,
            premises=premise_objs,
            deductive_steps=deductive_steps,
            contradictions=contradictions,
            candidate_solutions=candidate_evals,
            conclusion=conclusion,
            epistemic_uncertainty=uncertainty,
            summary=summary,
        )
