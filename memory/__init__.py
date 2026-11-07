"""
404 FOUNDERS — Advanced Multi-Layer Memory System
Modular, secure cognitive memory architecture spanning short-term, working,
long-term, episodic, semantic knowledge, user preferences, hybrid retrieval,
and consolidation.
"""

from memory.consolidation.consolidation_engine import (
    ConflictReport,
    ConsolidationSummary,
    MemoryConsolidationEngine,
)
from memory.contextual_memory import AssembledContext, ContextualMemoryEngine
from memory.episodic.episodic_memory import EpisodicEvent, EpisodicMemory
from memory.knowledge.knowledge_memory import (
    ClaimType,
    KnowledgeFact,
    KnowledgeMemory,
    KnowledgeRelationship,
)
from memory.long_term.long_term_memory import LongTermMemory, LongTermRecord
from memory.personalization.personalization_engine import (
    PersonalizationEngine,
    PersonalizationProfile,
)
from memory.retrieval.retrieval_engine import (
    HybridMemoryRetrievalEngine,
    ScoredMemoryRecord,
)
from memory.security import MemorySecurityManager
from memory.short_term.short_term_memory import ChatMessage, ShortTermMemory
from memory.user_preferences import UserPreference, UserPreferenceMemory
from memory.working_memory import WorkingMemory, WorkingTask

__all__ = [
    "AssembledContext",
    "ChatMessage",
    "ClaimType",
    "ConflictReport",
    "ConsolidationSummary",
    "ContextualMemoryEngine",
    "EpisodicEvent",
    "EpisodicMemory",
    "HybridMemoryRetrievalEngine",
    "KnowledgeFact",
    "KnowledgeMemory",
    "KnowledgeRelationship",
    "LongTermMemory",
    "LongTermRecord",
    "MemoryConsolidationEngine",
    "MemorySecurityManager",
    "PersonalizationEngine",
    "PersonalizationProfile",
    "ScoredMemoryRecord",
    "ShortTermMemory",
    "UserPreference",
    "UserPreferenceMemory",
    "WorkingMemory",
    "WorkingTask",
]
