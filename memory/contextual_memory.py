"""
404 FOUNDERS — Contextual Memory Synthesis Engine
Assembles multi-layer memory state into dynamic, bounded prompt context
incorporating working objectives, conversational history, retrieved knowledge,
and personalization directives while respecting token budget limits.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from database.connection import DatabaseManager
from memory.episodic.episodic_memory import EpisodicMemory
from memory.personalization.personalization_engine import PersonalizationEngine
from memory.retrieval.retrieval_engine import HybridMemoryRetrievalEngine, ScoredMemoryRecord
from memory.short_term.short_term_memory import ChatMessage, ShortTermMemory
from memory.working_memory import WorkingMemory, WorkingTask


@dataclass
class AssembledContext:
    """The synthesized context ready for foundation model generation."""
    full_context_text: str
    personalization_directive: str
    active_tasks: List[WorkingTask]
    retrieved_memories: List[ScoredMemoryRecord]
    conversation_turns: List[ChatMessage]
    estimated_tokens: int
    budget_limit: int


class ContextualMemoryEngine:
    """
    Contextual Memory Engine.
    Dynamically orchestrates multi-layer memory retrieval and budget-bounded
    prompt synthesis for end-to-end generation workflows.
    """

    DEFAULT_BUDGET_TOKENS = 3000

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        short_term: Optional[ShortTermMemory] = None,
        working_mem: Optional[WorkingMemory] = None,
        retrieval_engine: Optional[HybridMemoryRetrievalEngine] = None,
        personalization: Optional[PersonalizationEngine] = None,
    ) -> None:
        db = db_manager or DatabaseManager.get_instance()
        self.short_term = short_term or ShortTermMemory(db)
        self.working_mem = working_mem or WorkingMemory(db)
        self.retrieval = retrieval_engine or HybridMemoryRetrievalEngine(db)
        self.personalization = personalization or PersonalizationEngine(db_manager=db)

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        return max(1, len(text) // 4)

    def assemble_context(
        self,
        user_id: str,
        session_id: str,
        current_query: str,
        token_budget: int = DEFAULT_BUDGET_TOKENS,
        max_retrieved_memories: int = 5,
        max_conversation_turns: int = 10,
    ) -> AssembledContext:
        """
        Dynamically synthesize multi-layer memory context for a given prompt query.
        Budget allocation order:
        1. Personalization Directives (approx 100 tokens)
        2. Active Working Tasks (approx 300 tokens)
        3. Retrieved Relevant Memories (approx 800 tokens)
        4. Recent Conversation History (remaining tokens)
        """
        # 1. Personalization
        persona_directive = self.personalization.generate_prompt_guidance(user_id)

        # 2. Active working tasks
        active_tasks = self.working_mem.list_active_tasks(session_id)

        # 3. Retrieved relevant memories
        retrieved = self.retrieval.retrieve(
            user_id=user_id,
            query=current_query,
            limit=max_retrieved_memories,
        )

        # 4. Recent conversational turns
        turns = self.short_term.get_history(
            user_id=user_id,
            session_id=session_id,
            limit=max_conversation_turns,
        )

        # Assemble blocks respecting budget
        sections: List[str] = []

        if persona_directive:
            sections.append(persona_directive)

        if active_tasks:
            task_lines = ["[Active Working Tasks]:"]
            for t in active_tasks:
                task_lines.append(f"- Task: {t.task_name} (Status: {t.status})")
                if t.active_objectives:
                    task_lines.append(f"  Objectives: {', '.join(t.active_objectives)}")
                if t.intermediate_results:
                    task_lines.append(f"  Intermediate: {t.intermediate_results}")
            sections.append("\n".join(task_lines))

        if retrieved:
            mem_lines = ["[Retrieved Knowledge & Persistent Memory]:"]
            for m in retrieved:
                mem_lines.append(f"- ({m.memory_layer}) [{m.source_attribution} | Conf: {m.confidence_score:.2f}]: {m.content}")
            sections.append("\n".join(mem_lines))

        if turns:
            turn_lines = ["[Conversation History]:"]
            for turn in turns:
                turn_lines.append(f"{turn.role.capitalize()}: {turn.content}")
            sections.append("\n".join(turn_lines))

        # Join full context
        full_text = "\n\n".join(sections)
        estimated_tokens = self._estimate_tokens(full_text)

        # Token budget enforcement: truncate oldest sections if budget exceeded
        if estimated_tokens > token_budget:
            # Truncate conversation history to fit budget
            excess_tokens = estimated_tokens - token_budget
            chars_to_cut = excess_tokens * 4
            if len(full_text) > chars_to_cut:
                full_text = full_text[chars_to_cut:]
                full_text = "[... truncated prior context ...]\n" + full_text
            estimated_tokens = self._estimate_tokens(full_text)

        return AssembledContext(
            full_context_text=full_text,
            personalization_directive=persona_directive,
            active_tasks=active_tasks,
            retrieved_memories=retrieved,
            conversation_turns=turns,
            estimated_tokens=estimated_tokens,
            budget_limit=token_budget,
        )
