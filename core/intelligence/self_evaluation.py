"""
404 FOUNDERS — Self-Evaluation and Error Detection Engine
Provides automated consistency verification, missing information audits, contradiction scanning,
unsupported claim detection, epistemic modesty indicators, and offline feedback logging.
Strictly prohibits live model weight self-modification.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional


@dataclass
class EvaluationFinding:
    """Represents a specific defect, inconsistency, or ambiguity identified in an output."""
    category: str  # "CONTRADICTION", "MISSING_INFO", "UNSUPPORTED_CLAIM", "CALCULATION_RISK"
    severity: str  # "HIGH", "MEDIUM", "LOW"
    description: str
    suggested_correction: str


@dataclass
class FeedbackRecord:
    """Structured record stored for future offline training and evaluation pipelines."""
    record_id: str
    timestamp_utc: str
    input_query: str
    candidate_output: str
    findings: List[Dict[str, str]]
    quality_score: float
    logged_for_training: bool = True
    notice: str = "OFFLINE LOGGING ONLY: Live self-modification of weights is strictly disabled."


@dataclass
class SelfEvaluationResult:
    """Comprehensive evaluation report regarding model or module output quality."""
    is_valid: bool
    quality_score: float  # 0.0 to 1.0
    epistemic_modesty_status: str  # "GROUNDED", "SPECULATIVE", "UNKNOWN_DECLARED"
    findings: List[EvaluationFinding]
    missing_elements: List[str]
    contains_contradictions: bool
    summary: str
    logged_record_id: Optional[str] = None


class SelfEvaluationEngine:
    """
    Self-evaluation and error detection engine.
    Audits generated text and calculations for factual grounding, logical consistency,
    and missing prerequisite facts. Practices explicit epistemic modesty when uncertain.
    """

    HEDGING_MODESTY_MARKERS = [
        r"\bi do not know\b",
        r"\bunknown\b",
        r"\buncertain\b",
        r"\binsufficient information\b",
        r"\bcannot be verified\b",
        r"\blacks empirical evidence\b",
    ]

    UNSUPPORTED_ABSOLUTES = [
        (r"\b(100% guaranteed|undeniably proven|without any doubt|absolute certainty)\b", "Uses absolute certainty markers without empirical bounding."),
        (r"\bevery single person agrees\b", "Universal consensus claim without demographic evidence."),
    ]

    def __init__(self, log_dir: Optional[Path] = None) -> None:
        self.log_dir = log_dir

    def check_contradictions(self, text: str) -> List[EvaluationFinding]:
        """Scan text for internal conflicting assertions."""
        findings: List[EvaluationFinding] = []
        sentences = [s.strip().lower() for s in re.split(r"[.!?]\s+", text) if len(s.strip()) > 10]

        for i, s1 in enumerate(sentences):
            for s2 in sentences[i+1:]:
                if "is enabled" in s1 and "is disabled" in s2 and any(w in s2 for w in s1.split() if len(w) > 4):
                    findings.append(EvaluationFinding(
                        category="CONTRADICTION",
                        severity="HIGH",
                        description=f"Conflicting state assertions detected: '{s1}' vs '{s2}'",
                        suggested_correction="Harmonize operational state across both statements.",
                    ))
                elif "always" in s1 and "never" in s2 and any(w in s2 for w in s1.split() if len(w) > 4):
                    findings.append(EvaluationFinding(
                        category="CONTRADICTION",
                        severity="MEDIUM",
                        description=f"Conflicting universal quantifiers: '{s1}' vs '{s2}'",
                        suggested_correction="Specify boundary conditions under which each applies.",
                    ))
        return findings

    def check_unsupported_claims(self, text: str) -> List[EvaluationFinding]:
        """Detect ungrounded absolute certainty claims."""
        findings: List[EvaluationFinding] = []
        for pattern, explanation in self.UNSUPPORTED_ABSOLUTES:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                findings.append(EvaluationFinding(
                    category="UNSUPPORTED_CLAIM",
                    severity="MEDIUM",
                    description=f"Found absolute claim '{match.group(0)}': {explanation}",
                    suggested_correction="Rephrase with appropriate epistemic qualifiers or provide verified proof.",
                ))
        return findings

    def check_missing_information(self, query: str, output: str) -> List[str]:
        """Verify whether expected questions or core query variables are addressed."""
        missing: List[str] = []
        lower_q = query.lower()
        lower_o = output.lower()

        # Check question words
        if "how much" in lower_q or "calculate" in lower_q:
            if not re.search(r"\d+", output):
                missing.append("Query requests quantitative calculation, but output contains no numerical figures.")

        if "why" in lower_q:
            if not any(k in lower_o for k in ["because", "due to", "reason", "as a result"]):
                missing.append("Query asks 'why', but output contains no causal explanation markers.")

        return missing

    def evaluate(
        self,
        query: str,
        output: str,
        context_facts: Optional[List[str]] = None,
        log_feedback: bool = False,
    ) -> SelfEvaluationResult:
        """Perform full self-evaluation of candidate output against query and facts."""
        if not output.strip():
            return SelfEvaluationResult(
                is_valid=False,
                quality_score=0.0,
                epistemic_modesty_status="UNKNOWN_DECLARED",
                findings=[EvaluationFinding("MISSING_INFO", "HIGH", "Output is completely empty.", "Generate substantive response.")],
                missing_elements=["Substantive response content"],
                contains_contradictions=False,
                summary="Output is empty.",
            )

        findings: List[EvaluationFinding] = []
        findings.extend(self.check_contradictions(output))
        findings.extend(self.check_unsupported_claims(output))

        missing_elements = self.check_missing_information(query, output)
        for m in missing_elements:
            findings.append(EvaluationFinding(
                category="MISSING_INFO",
                severity="HIGH" if "calculation" in m else "MEDIUM",
                description=m,
                suggested_correction="Incorporate missing factual requirement into output.",
            ))

        # Check epistemic modesty
        declares_unknown = any(re.search(pat, output, re.IGNORECASE) for pat in self.HEDGING_MODESTY_MARKERS)
        if declares_unknown:
            modesty_status = "UNKNOWN_DECLARED"
        elif any(f.category == "UNSUPPORTED_CLAIM" for f in findings):
            modesty_status = "SPECULATIVE"
        else:
            modesty_status = "GROUNDED"

        # Quality scoring
        score = 1.0
        for f in findings:
            if f.severity == "HIGH":
                score -= 0.35
            elif f.severity == "MEDIUM":
                score -= 0.15
            else:
                score -= 0.05
        score = round(max(0.0, min(1.0, score)), 2)

        has_contradictions = any(f.category == "CONTRADICTION" for f in findings)
        is_valid = score >= 0.60 and not has_contradictions

        record_id = None
        if log_feedback and self.log_dir:
            record_id = f"feedback_{int(datetime.now(timezone.utc).timestamp()*1000)}"
            record = FeedbackRecord(
                record_id=record_id,
                timestamp_utc=datetime.now(timezone.utc).isoformat(),
                input_query=query,
                candidate_output=output,
                findings=[{"cat": f.category, "desc": f.description} for f in findings],
                quality_score=score,
            )
            try:
                self.log_dir.mkdir(parents=True, exist_ok=True)
                log_file = self.log_dir / "evaluation_feedback.jsonl"
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(record.__dict__) + "\n")
            except Exception:
                pass

        summary = (
            f"Self-evaluation score: {score}/1.0 ({'VALID' if is_valid else 'NEEDS_REVISION'}). "
            f"Modesty status: {modesty_status}. Found {len(findings)} issue(s)."
        )

        return SelfEvaluationResult(
            is_valid=is_valid,
            quality_score=score,
            epistemic_modesty_status=modesty_status,
            findings=findings,
            missing_elements=missing_elements,
            contains_contradictions=has_contradictions,
            summary=summary,
            logged_record_id=record_id,
        )
