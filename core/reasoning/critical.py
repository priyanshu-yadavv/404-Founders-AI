"""
404 FOUNDERS — Critical Thinking Engine
Provides formal fallacy detection, cognitive bias identification,
evidence quality evaluation, and alternative interpretation synthesis.
"""

from dataclasses import dataclass, field
import re
from typing import Any, Dict, List, Optional


@dataclass
class FallacyDetection:
    """Represents an identified formal or informal logical fallacy."""
    fallacy_type: str
    target_statement: str
    explanation: str
    counter_argument: str


@dataclass
class BiasDetection:
    """Represents a detected cognitive bias in an argument or premise."""
    bias_name: str
    manifestation: str
    mitigation_strategy: str


@dataclass
class EvidenceEvaluation:
    """Assessment of evidence quality, rigor, and premise support."""
    sample_adequacy: str  # "SUFFICIENT", "ANECDOTAL", "UNSPECIFIED"
    correlation_vs_causation_risk: bool
    empirical_support_score: float  # 0.0 to 1.0
    evaluation_notes: List[str]


@dataclass
class CriticalThinkingResult:
    """Comprehensive analysis report from critical thinking evaluation."""
    argument_analyzed: str
    fallacies_detected: List[FallacyDetection]
    biases_detected: List[BiasDetection]
    evidence_evaluation: EvidenceEvaluation
    alternative_interpretations: List[str]
    soundness_rating: str  # "SOUND", "QUESTIONABLE", "FALLACIOUS"
    summary: str


class CriticalThinkingEngine:
    """
    Critical thinking engine.
    Scrutinizes textual arguments for rhetorical fallacies, cognitive biases,
    unsupported causal leaps, and formulates alternative explanatory models.
    """

    FALLACY_SIGNATURES = [
        ("AD_HOMINEM", re.compile(r"\b(idiot|fool|corrupt|liar|hypocrite|ignorant|stupid)\b", re.IGNORECASE),
         "Attacks the character or motive of the speaker rather than addressing the substance of the argument.",
         "Focus refutation strictly on empirical claims and logical premises."),
        ("FALSE_DILEMMA", re.compile(r"\b(either\s+.+?\s+or\s+|if you('re| are) not with us you('re| are) against us)\b", re.IGNORECASE),
         "Presents two extreme alternatives while arbitrarily ignoring intermediate options or nuanced solutions.",
         "Identify viable middle-ground alternatives and multi-faceted trade-offs."),
        ("SLIPPERY_SLOPE", re.compile(r"\b(if we (allow|do)\s+.+?\s+it will inevitably lead to|will result in total disaster)\b", re.IGNORECASE),
         "Asserts that a relatively small initial step inevitably leads to an extreme catastrophe without demonstrating causal links.",
         "Demonstrate independent decision checkpoints preventing the extreme outcome."),
        ("APPEAL_TO_AUTHORITY", re.compile(r"\b(because\s+.+?\s+said so|celebrity\s+.+?\s+agrees|experts all know that without proof)\b", re.IGNORECASE),
         "Relies solely on an authoritative figure's assertion rather than verifiable evidence or sound methodology.",
         "Demand primary source empirical data and methodology reviews."),
        ("POST_HOC", re.compile(r"\b(after this, therefore because of this|happened after\s+.+?\s+so it caused)\b", re.IGNORECASE),
         "Assumes temporal succession implies direct causal relationship (Post hoc ergo propter hoc).",
         "Differentiate temporal correlation from controlled mechanistic causality."),
        ("BANDWAGON", re.compile(r"\b(everyone knows|everybody believes|most people think|popular consensus proves)\b", re.IGNORECASE),
         "Argues that a proposition is true simply because a substantial population believes it (Argumentum ad populum).",
         "Truth value is independent of popularity; verify through empirical demonstration."),
    ]

    BIAS_SIGNATURES = [
        ("CONFIRMATION_BIAS", re.compile(r"\b(only\s+(\w+\s+)?evidence\s+that\s+supports|ignore\s+any\s+dissenting|confirms\s+what\s+i\s+already\s+knew)\b", re.IGNORECASE),
         "Selecting only confirmatory evidence while discarding contradictory findings.",
         "Actively seek falsifying evidence and counter-examples."),
        ("ANCHORING_BIAS", re.compile(r"\b(the initial number was|first impression was that)\b", re.IGNORECASE),
         "Over-relying on the first piece of information encountered when making subsequent decisions.",
         "Recalculate estimates independently from zero-base assumptions."),
        ("SUNK_COST_FALLACY", re.compile(r"\b(we have already spent too much to stop|invested too much to turn back)\b", re.IGNORECASE),
         "Continuing a venture due to previously invested non-recoverable resources rather than future value.",
         "Evaluate future marginal costs versus future marginal benefits exclusively."),
    ]

    def detect_fallacies(self, argument: str) -> List[FallacyDetection]:
        """Scan argument for known rhetorical and logical fallacies."""
        detections: List[FallacyDetection] = []
        for name, pattern, explanation, counter in self.FALLACY_SIGNATURES:
            m = pattern.search(argument)
            if m:
                detections.append(FallacyDetection(
                    fallacy_type=name,
                    target_statement=m.group(0),
                    explanation=explanation,
                    counter_argument=counter,
                ))
        return detections

    def detect_biases(self, argument: str) -> List[BiasDetection]:
        """Detect cognitive biases in phrasing and stated reasoning."""
        biases: List[BiasDetection] = []
        for name, pattern, manifestation, mitigation in self.BIAS_SIGNATURES:
            m = pattern.search(argument)
            if m:
                biases.append(BiasDetection(
                    bias_name=name,
                    manifestation=f"Triggered by phrase '{m.group(0)}': {manifestation}",
                    mitigation_strategy=mitigation,
                ))
        return biases

    def evaluate_evidence(self, argument: str) -> EvidenceEvaluation:
        """Evaluate evidence strength, detecting anecdotal claims and ungrounded causal leaps."""
        notes: List[str] = []
        anecdotal_markers = [r"\bin my experience\b", r"\ba friend told me\b", r"\bi saw once\b", r"\bone time\b"]
        is_anecdotal = any(re.search(m, argument, re.IGNORECASE) for m in anecdotal_markers)

        causal_markers = [r"\bcauses\b", r"\bleads directly to\b", r"\bis responsible for\b"]
        claims_causation = any(re.search(m, argument, re.IGNORECASE) for m in causal_markers)

        has_data = bool(re.search(r"\b\d+(\.\d+)?%\b|\b\d+\s+(samples|participants|trials|studies)\b", argument, re.IGNORECASE))

        if is_anecdotal:
            sample_status = "ANECDOTAL"
            notes.append("Argument relies on singular anecdotal accounts rather than systematic sampling.")
            empirical_score = 0.3
        elif has_data:
            sample_status = "SUFFICIENT"
            notes.append("Quantitative figures or empirical sample sizes referenced.")
            empirical_score = 0.85
        else:
            sample_status = "UNSPECIFIED"
            notes.append("Empirical sample size and statistical methodology not specified.")
            empirical_score = 0.5

        if claims_causation and not has_data:
            notes.append("Strong causal claims made without rigorous control group data.")
            empirical_score = max(0.2, empirical_score - 0.25)

        return EvidenceEvaluation(
            sample_adequacy=sample_status,
            correlation_vs_causation_risk=claims_causation and not has_data,
            empirical_support_score=round(empirical_score, 2),
            evaluation_notes=notes,
        )

    def generate_alternative_interpretations(self, argument: str) -> List[str]:
        """Synthesize alternative explanatory models and counter-perspectives."""
        alternatives = [
            "Confounding variable hypothesis: An unmeasured third factor could be driving observed correlations.",
            "Reverse causality possibility: The presumed dependent effect might actually precede or influence the cause.",
            "Random stochastic variation: Observed outcomes may fall within normal statistical variance without systematic intervention.",
        ]
        return alternatives

    def analyze(self, argument: str) -> CriticalThinkingResult:
        """Execute full critical thinking examination on an input argument."""
        if not argument.strip():
            raise ValueError("Argument string cannot be empty.")

        fallacies = self.detect_fallacies(argument)
        biases = self.detect_biases(argument)
        evidence = self.evaluate_evidence(argument)
        alternatives = self.generate_alternative_interpretations(argument)

        if fallacies:
            soundness = "FALLACIOUS"
        elif biases or evidence.empirical_support_score < 0.5:
            soundness = "QUESTIONABLE"
        else:
            soundness = "SOUND"

        summary = (
            f"Critical analysis determined argument soundness as {soundness}. "
            f"Detected {len(fallacies)} fallacy marker(s) and {len(biases)} cognitive bias indicator(s). "
            f"Empirical support score evaluated at {evidence.empirical_support_score}."
        )

        return CriticalThinkingResult(
            argument_analyzed=argument,
            fallacies_detected=fallacies,
            biases_detected=biases,
            evidence_evaluation=evidence,
            alternative_interpretations=alternatives,
            soundness_rating=soundness,
            summary=summary,
        )
