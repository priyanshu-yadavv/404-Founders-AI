"""
404 FOUNDERS — Core/Intelligence
Modular intelligence coordination, neural core, general knowledge, research analysis,
language communication, self-evaluation, and central intelligence routing.
"""

from core.intelligence.central_router import (
    CentralIntelligenceRouter,
    CentralRoutingResult,
    EngineDispatchPlan,
    EngineExecutionOutput,
)
from core.intelligence.knowledge_engine import (
    DomainClassification,
    ExtractedEntity,
    GeneralKnowledgeEngine,
    KnowledgeProcessingResult,
)
from core.intelligence.language_engine import (
    CommunicationStyle,
    LanguageCommunicationEngine,
    LanguageProcessingResult,
    ReadabilityMetrics,
    SummaryResult,
)
from core.intelligence.neural_core import NeuralCore, NeuralCoreConfig
from core.intelligence.research_engine import (
    CrossSourceContradiction,
    ResearchAnalysisEngine,
    ResearchSource,
    ResearchSynthesisResult,
    SourceClaim,
)
from core.intelligence.self_evaluation import (
    EvaluationFinding,
    FeedbackRecord,
    SelfEvaluationEngine,
    SelfEvaluationResult,
)

__all__ = [
    "NeuralCore",
    "NeuralCoreConfig",
    "CentralIntelligenceRouter",
    "CentralRoutingResult",
    "EngineDispatchPlan",
    "EngineExecutionOutput",
    "GeneralKnowledgeEngine",
    "ExtractedEntity",
    "DomainClassification",
    "KnowledgeProcessingResult",
    "ResearchAnalysisEngine",
    "ResearchSource",
    "SourceClaim",
    "CrossSourceContradiction",
    "ResearchSynthesisResult",
    "LanguageCommunicationEngine",
    "CommunicationStyle",
    "ReadabilityMetrics",
    "SummaryResult",
    "LanguageProcessingResult",
    "SelfEvaluationEngine",
    "EvaluationFinding",
    "FeedbackRecord",
    "SelfEvaluationResult",
]
