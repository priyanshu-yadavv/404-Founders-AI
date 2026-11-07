"""
404 FOUNDERS — Multi-Layer Memory Engine Unit Tests
Tests Short-Term, Long-Term, Working, Episodic, Knowledge, and User Preference layers.
"""

import pytest

from database.connection import DatabaseManager
from memory.episodic.episodic_memory import EpisodicMemory
from memory.knowledge.knowledge_memory import ClaimType, KnowledgeMemory
from memory.long_term.long_term_memory import LongTermMemory
from memory.short_term.short_term_memory import ShortTermMemory
from memory.user_preferences import UserPreferenceMemory
from memory.working_memory import WorkingMemory


@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_memory_layers.db"
    return DatabaseManager(str(db_file))


def test_short_term_memory_lifecycle_and_summarization(test_db):
    stm = ShortTermMemory(test_db)
    user_id = "user_stm_01"
    session_id = "sess_stm_01"

    # Add message turns
    m1 = stm.add_message(user_id, session_id, role="user", content="Hello 404 Founders!")
    m2 = stm.add_message(user_id, session_id, role="assistant", content="Welcome! How can I assist your engineering today?")

    assert m1.role == "user"
    assert m2.role == "assistant"

    # Retrieve history
    history = stm.get_history(user_id, session_id)
    assert len(history) == 2
    assert history[0].content == "Hello 404 Founders!"

    # Token count check
    toks = stm.get_session_token_count(user_id, session_id)
    assert toks > 0

    # Add many turns to trigger summarization
    stm.TOKEN_CEILING_FOR_SUMMARIZATION = 50  # Lower threshold for unit test
    for i in range(10):
        stm.add_message(user_id, session_id, role="user", content=f"Step {i}: Extensive instructions and detailed logs for processing task #{i}")

    # Check that summarization inserted milestone
    active_history = stm.get_history(user_id, session_id, limit=50)
    summaries = [m for m in active_history if "[Conversation Context Summary]" in m.content]
    assert len(summaries) >= 1

    # Clear session
    cleared = stm.clear_session(user_id, session_id)
    assert cleared > 0
    remaining = stm.get_history(user_id, session_id)
    assert len(remaining) == 0


def test_long_term_memory_deduplication_and_versioning(test_db):
    ltm = LongTermMemory(test_db)
    user_id = "user_ltm_01"

    # Save initial record
    r1 = ltm.save_record(
        user_id=user_id,
        content="Our primary backend framework is FastAPI.",
        summary="Backend framework definition",
        importance=0.9,
        tags=["architecture", "backend"],
    )
    assert r1.version == 1
    assert r1.status == "ACTIVE"

    # Save duplicate content -> returns existing record without new insertion
    r_dup = ltm.save_record(
        user_id=user_id,
        content="  Our primary backend framework is FastAPI.  ",
    )
    assert r_dup.record_id == r1.record_id

    # Update record -> creates incremented version, archives previous
    r2 = ltm.update_record(
        user_id=user_id,
        record_id=r1.record_id,
        new_content="Our primary backend framework is FastAPI with Uvicorn ASGI.",
        importance=0.95,
    )
    assert r2.version == 2
    assert r2.parent_version_id == r1.record_id
    assert r2.status == "ACTIVE"

    # Prior record must be archived
    prior = ltm.get_record(user_id, r1.record_id)
    assert prior.status == "ARCHIVED"

    # List records
    active_records = ltm.list_records(user_id=user_id)
    assert len(active_records) == 1
    assert active_records[0].record_id == r2.record_id

    # Delete record
    deleted = ltm.delete_record(user_id=user_id, record_id=r2.record_id)
    assert deleted is True
    assert len(ltm.list_records(user_id=user_id)) == 0


def test_working_memory_state_and_recovery(test_db):
    wm = WorkingMemory(test_db)
    session_id = "sess_wm_01"
    task_id = "task_matrix_01"

    # Start task
    task = wm.start_task(
        session_id=session_id,
        task_id=task_id,
        task_name="Matrix Factorization",
        objectives=["Initialize tensors", "Compute gradients"],
        dependencies=["cuda_init"],
        initial_results={"tensor_dim": 128},
    )
    assert task.status == "ACTIVE"
    assert "Compute gradients" in task.active_objectives

    # Update progress
    updated = wm.update_task(
        session_id=session_id,
        task_id=task_id,
        intermediate_results={"loss": 0.042},
        pending_actions=[{"step": "sync_weights"}],
    )
    assert updated.intermediate_results["loss"] == 0.042
    assert updated.intermediate_results["tensor_dim"] == 128  # Merged

    # List active tasks
    active = wm.list_active_tasks(session_id=session_id)
    assert len(active) == 1

    # Complete task
    completed = wm.complete_task(session_id=session_id, task_id=task_id, final_outcome={"verdict": "success"})
    assert completed.status == "COMPLETED"

    # Clear session tasks
    wm.clear_session_tasks(session_id=session_id)
    assert wm.get_task(session_id=session_id, task_id=task_id) is None


def test_episodic_memory_anti_fabrication_and_retrieval(test_db):
    em = EpisodicMemory(test_db)
    user_id = "user_ep_01"

    # Record genuine event
    ev1 = em.record_event(
        user_id=user_id,
        event_description="Completed Phase 08 multimodal fusion deployment.",
        outcome="All 17 tests passed.",
        task_id="task_phase_08",
    )
    assert ev1.event_id.startswith("ep_")

    # Search existing event
    found = em.search_events(user_id=user_id, query="multimodal fusion")
    assert len(found) >= 1
    assert found[0].event_id == ev1.event_id

    # Anti-fabrication check: non-existent queries MUST return empty / unrecorded
    verification = em.verify_past_occurrence(user_id=user_id, query="quantum teleportation experiment")
    assert verification["recorded"] is False
    assert len(verification["evidence"]) == 0
    assert "did not occur" in verification["status"]

    # Verify existing event
    verification_good = em.verify_past_occurrence(user_id=user_id, query="Phase 08 multimodal")
    assert verification_good["recorded"] is True
    assert len(verification_good["evidence"]) >= 1


def test_knowledge_memory_claim_types_and_relationships(test_db):
    km = KnowledgeMemory(test_db)
    user_id = "user_km_01"

    # Store verified fact
    f1 = km.store_fact(
        user_id=user_id,
        subject="NeuralCore",
        predicate="uses",
        object_val="SwiGLU",
        claim_type=ClaimType.VERIFIED_FACT,
        source_attribution="architecture_spec",
        confidence=0.99,
    )
    assert f1.claim_type == ClaimType.VERIFIED_FACT

    # Store user-stated assertion
    f2 = km.store_fact(
        user_id=user_id,
        subject="UserProject",
        predicate="targets",
        object_val="Robotics",
        claim_type=ClaimType.USER_STATED,
        source_attribution="user_chat",
        confidence=0.80,
    )
    assert f2.claim_type == ClaimType.USER_STATED

    # Query filtered by claim type
    verified_facts = km.query_facts(user_id=user_id, claim_type=ClaimType.VERIFIED_FACT)
    assert len(verified_facts) == 1
    assert verified_facts[0].subject == "NeuralCore"

    # Create directed semantic relationship
    rel = km.link_facts(
        user_id=user_id,
        source_id=f1.fact_id,
        target_id=f2.fact_id,
        relation_type="DEPENDS_ON",
    )
    assert rel.rel_id.startswith("rel_")

    # Get related facts
    related = km.get_related_facts(user_id=user_id, fact_id=f1.fact_id)
    assert len(related) == 1
    assert related[0]["related_fact_id"] == f2.fact_id


def test_user_preference_memory_crud_and_defaults(test_db):
    upm = UserPreferenceMemory(test_db)
    user_id = "user_pref_01"

    # Default values when unset
    default_style = upm.get_preference(user_id, "communication_style")
    assert default_style == "balanced"

    # Set explicit preference
    pref = upm.set_preference(user_id, "communication_style", "concise", is_explicit=True)
    assert pref.preference_val == "concise"

    # Check updated value
    assert upm.get_preference(user_id, "communication_style") == "concise"

    # List all preferences
    all_prefs = upm.get_all_preferences(user_id)
    assert all_prefs["communication_style"] == "concise"
    assert "response_length" in all_prefs

    # Delete preference -> reverts to default
    deleted = upm.delete_preference(user_id, "communication_style")
    assert deleted is True
    assert upm.get_preference(user_id, "communication_style") == "balanced"
