"""
404 FOUNDERS — Personal AI Memory Bridge
Connects the local agent with Phase 09 Multi-Layer Memory subsystems.
Enforces privacy scrubbing, retrieves user preferences, logs episodic events,
and maintains working task states across local operations.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from database.connection import DatabaseManager
from memory.episodic.episodic_memory import EpisodicEvent, EpisodicMemory
from memory.long_term.long_term_memory import LongTermMemory, LongTermRecord
from memory.security import MemorySecurityManager
from memory.user_preferences import UserPreferenceMemory
from memory.working_memory import WorkingMemory, WorkingTask


class PersonalAIMemoryBridge:
    """Memory bridge coordinating Personal AI operations with durable memory layers."""

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        pref_memory: Optional[UserPreferenceMemory] = None,
        episodic_memory: Optional[EpisodicMemory] = None,
        long_term_memory: Optional[LongTermMemory] = None,
        working_memory: Optional[WorkingMemory] = None,
    ) -> None:
        db = db_manager or DatabaseManager.get_instance()
        self.pref_mem = pref_memory or UserPreferenceMemory(db)
        self.episodic_mem = episodic_memory or EpisodicMemory(db)
        self.ltm = long_term_memory or LongTermMemory(db)
        self.working_mem = working_memory or WorkingMemory(db)

    def get_user_preferences(self, user_id: str) -> Dict[str, str]:
        """Fetch active user preferences and style directives."""
        return self.pref_mem.get_all_preferences(user_id)

    def log_agent_episode(
        self,
        user_id: str,
        event_description: str,
        session_id: Optional[str] = None,
        outcome: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> EpisodicEvent:
        """Record an episodic event log of an executed agent action (zero fabrication)."""
        return self.episodic_mem.record_event(
            user_id=user_id,
            event_description=event_description,
            session_id=session_id,
            task_id=task_id,
            outcome=outcome,
        )

    def record_system_insight(
        self,
        user_id: str,
        insight_content: str,
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
    ) -> LongTermRecord:
        """Save a persistent system insight or environment reference to long-term memory."""
        tag_list = tags or ["system_insight"]
        return self.ltm.save_record(
            user_id=user_id,
            content=insight_content,
            importance=importance,
            source_type="personal_ai_agent",
            tags=tag_list,
        )

    def get_active_tasks(self, session_id: str) -> List[WorkingTask]:
        """Retrieve active working tasks for the current session."""
        return self.working_mem.list_active_tasks(session_id)
