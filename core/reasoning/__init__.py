"""
404 FOUNDERS — Core/Reasoning
Symbolic, mathematical, deductive, scientific, critical, and creative reasoning engines.
"""

from core.reasoning.creative import (
    AnalogyMapping,
    ConstraintRelaxation,
    CreativeProblemResult,
    CreativeProblemSolvingEngine,
    CreativeSolutionVector,
)
from core.reasoning.critical import (
    BiasDetection,
    CriticalThinkingEngine,
    CriticalThinkingResult,
    EvidenceEvaluation,
    FallacyDetection,
)
from core.reasoning.logical import (
    CandidateSolution,
    Contradiction,
    LogicalPremise,
    LogicalReasoningEngine,
    LogicalReasoningResult,
    LogicalStep,
)
from core.reasoning.mathematical import (
    MathematicalReasoningEngine,
    MathematicalResult,
    MathStep,
    NumericalVerification,
)
from core.reasoning.scientific import (
    EvidenceComparisonResult,
    HypothesisEvaluation,
    PhysicsSolution,
    ScientificAnalysisResult,
    ScientificReasoningEngine,
)

__all__ = [
    "LogicalReasoningEngine",
    "LogicalPremise",
    "LogicalStep",
    "Contradiction",
    "CandidateSolution",
    "LogicalReasoningResult",
    "MathematicalReasoningEngine",
    "MathStep",
    "NumericalVerification",
    "MathematicalResult",
    "ScientificReasoningEngine",
    "PhysicsSolution",
    "HypothesisEvaluation",
    "EvidenceComparisonResult",
    "ScientificAnalysisResult",
    "CriticalThinkingEngine",
    "FallacyDetection",
    "BiasDetection",
    "EvidenceEvaluation",
    "CriticalThinkingResult",
    "CreativeProblemSolvingEngine",
    "AnalogyMapping",
    "ConstraintRelaxation",
    "CreativeSolutionVector",
    "CreativeProblemResult",
]
