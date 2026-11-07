"""
404 FOUNDERS — Memory Retrieval, Consolidation & Context Assembly Tests
Verifies multi-dimensional scoring with recency decay, conflict detection without
silent overwriting, personalization prompt formatting, and token-bounded context assembly.
"""

import pytest

from database.connection import DatabaseManager
from memory.consolidation.consolidation_engine import MemoryConsolidationEngine
from memory.contextual_memory import ContextualMemoryEngine
from memory.knowledge.knowledge_memory import ClaimType, KnowledgeMemory
from memory.long_term.long_term_memory import LongTermMemory
from memory.personalization.personalization_engine import PersonalizationEngine
from memory.retrieval.retrieval_engine import HybridMemoryRetrievalEngine
from memory.short_term.short_term_memory import ShortTermMemory
from memory.user_preferences import UserPreferenceMemory
from memory.working_memory import WorkingMemory


@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_retrieval_consolidation.db"
    return DatabaseManager(str(db_file))


def test_hybrid_retrieval_scoring_and_recency_decay(test_db):
    ltm = LongTermMemory(test_db)
    retriever = HybridMemoryRetrievalEngine(test_db)
    user_id = "user_ret_01"

    # Insert two records: one highly relevant to query, one generic
    r1 = ltm.save_record(
        user_id=user_id,
        content="The neural core employs custom RMSNorm and Rotary Position Embeddings.",
        summary="RMSNorm & RoPE details",
        importance=0.9,
        confidence=1.0,
        tags=["neural", "rmsnorm", "rope"],
    )
    r2 = ltm.save_record(
        user_id=user_id,
        content="General documentation for CLI launch arguments.",
        summary="CLI flags",
        importance=0.3,
        confidence=0.8,
        tags=["cli"],
    )

    # Query matching r1
    results = retriever.retrieve(user_id=user_id, query="RMSNorm and Rotary embeddings")
    assert len(results) >= 1
    top = results[0]
    assert top.record_id == r1.record_id
    assert top.lexical_score > 0.0
    assert top.recency_score > 0.0
    assert top.final_score > results[1].final_score

    # Deterministic fallback query (empty string)
    fallback = retriever.retrieve(user_id=user_id, query="")
    assert len(fallback) == 2
    # Ranked by recency and importance
    assert fallback[0].final_score >= fallback[1].final_score


def test_memory_consolidation_conflict_detection_no_silent_overwrite(test_db):
    km = KnowledgeMemory(test_db)
    consolidator = MemoryConsolidationEngine(test_db)
    user_id = "user_cons_01"

    # Create two contradictory knowledge facts on the same subject and predicate
    f1 = km.store_fact(
        user_id=user_id,
        subject="CompilerTarget",
        predicate="uses_version",
        object_val="Python 3.12",
        claim_type=ClaimType.USER_STATED,
    )
    f2 = km.store_fact(
        user_id=user_id,
        subject="CompilerTarget",
        predicate="uses_version",
        object_val="Rust 1.80",
        claim_type=ClaimType.USER_STATED,
    )

    # Run consolidation pass
    summary = consolidator.run_consolidation(user_id=user_id)

    # Conflict MUST be detected
    assert len(summary.conflicts_detected) >= 1
    conflict = summary.conflicts_detected[0]
    assert "compilertarget:uses_version" in conflict.subject_area
    assert conflict.resolution_status == "UNRESOLVED"

    # INVARIANT: Conflicting records MUST NOT be silently deleted or overwritten!
    # They should be marked with status 'CONFLICT_DETECTED'
    with test_db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM memory_records WHERE id = ?", (f1.fact_id,))
        row1 = cursor.fetchone()
        cursor.execute("SELECT status FROM memory_records WHERE id = ?", (f2.fact_id,))
        row2 = cursor.fetchone()

        assert row1["status"] == "CONFLICT_DETECTED"
        assert row2["status"] == "CONFLICT_DETECTED"


def test_personalization_engine_directive_generation(test_db):
    upm = UserPreferenceMemory(test_db)
    pe = PersonalizationEngine(pref_memory=upm, db_manager=test_db)
    user_id = "user_pers_01"

    # Set custom preferences
    upm.set_preference(user_id, "communication_style", "concise")
    upm.set_preference(user_id, "technical_depth", "expert")
    upm.set_preference(user_id, "code_preference", "rust")

    profile = pe.get_personalization_profile(user_id)
    assert profile.communication_style == "concise"
    assert profile.technical_depth == "expert"
    assert profile.code_preference == "rust"

    guidance = pe.generate_prompt_guidance(user_id)
    assert "concise, direct answers" in guidance
    assert "advanced domain expertise" in guidance
    assert "Rust" in guidance


def test_contextual_memory_token_budget_bounded_assembly(test_db):
    stm = ShortTermMemory(test_db)
    wm = WorkingMemory(test_db)
    ltm = LongTermMemory(test_db)
    cme = ContextualMemoryEngine(db_manager=test_db)

    user_id = "user_ctx_01"
    session_id = "sess_ctx_01"

    # Add working task
    wm.start_task(
        session_id=session_id,
        task_id="task_math_opt",
        task_name="Hyperparameter Optimization",
        objectives=["Tune learning rate", "Evaluate perplexity"],
    )

    # Add conversational turn
    stm.add_message(user_id, session_id, role="user", content="What is the current learning rate schedule?")

    # Add long-term fact
    ltm.save_record(
        user_id=user_id,
        content="Current optimizer is AdamW with cosine decay warmup for 1000 steps.",
        tags=["optimizer", "learning_rate"],
    )

    # Assemble context
    ctx = cme.assemble_context(
        user_id=user_id,
        session_id=session_id,
        current_query="learning rate optimizer schedule",
        token_budget=2000,
    )

    assert len(ctx.active_tasks) == 1
    assert len(ctx.conversation_turns) == 1
    assert len(ctx.retrieved_memories) >= 1
    assert ctx.estimated_tokens <= 2000
    assert "[Active Working Tasks]" in ctx.full_context_text
    assert "[Conversation History]" in ctx.full_context_text
    assert "[Retrieved Knowledge & Persistent Memory]" in ctx.full_context_text
