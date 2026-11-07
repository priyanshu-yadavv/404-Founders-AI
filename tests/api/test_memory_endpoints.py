"""
404 FOUNDERS — Memory & Continual Learning REST API Integration Tests
Tests all endpoints under /api/v1/memory/... and /api/v1/learning/...
"""

import pytest
from fastapi.testclient import TestClient

from api.rest.app import create_app, initialize_runtime_services
from database.connection import DatabaseManager


@pytest.fixture
def client(tmp_path):
    db_file = tmp_path / "test_api_memory.db"
    db_mgr = DatabaseManager(str(db_file))

    services = initialize_runtime_services()
    # Inject isolated db manager and dependencies into services
    from memory.long_term.long_term_memory import LongTermMemory
    from memory.short_term.short_term_memory import ShortTermMemory
    from memory.working_memory import WorkingMemory
    from memory.episodic.episodic_memory import EpisodicMemory
    from memory.knowledge.knowledge_memory import KnowledgeMemory
    from memory.user_preferences import UserPreferenceMemory
    from memory.retrieval.retrieval_engine import HybridMemoryRetrievalEngine
    from memory.consolidation.consolidation_engine import MemoryConsolidationEngine
    from memory.personalization.personalization_engine import PersonalizationEngine
    from memory.contextual_memory import ContextualMemoryEngine
    from learning.feedback.feedback_system import FeedbackSystem
    from learning.continual.learning_pipeline import ControlledLearningPipeline

    services["db_manager"] = db_mgr
    services["short_term_memory"] = ShortTermMemory(db_mgr)
    services["long_term_memory"] = LongTermMemory(db_mgr)
    services["working_memory"] = WorkingMemory(db_mgr)
    services["episodic_memory"] = EpisodicMemory(db_mgr)
    services["knowledge_memory"] = KnowledgeMemory(db_mgr)
    services["user_preference_memory"] = UserPreferenceMemory(db_mgr)
    services["retrieval_engine"] = HybridMemoryRetrievalEngine(db_mgr)
    services["consolidation_engine"] = MemoryConsolidationEngine(db_mgr)
    services["personalization_engine"] = PersonalizationEngine(pref_memory=services["user_preference_memory"], db_manager=db_mgr)
    services["contextual_memory"] = ContextualMemoryEngine(
        db_manager=db_mgr,
        short_term=services["short_term_memory"],
        working_mem=services["working_memory"],
        retrieval_engine=services["retrieval_engine"],
        personalization=services["personalization_engine"],
    )
    services["feedback_system"] = FeedbackSystem(db_mgr)
    services["learning_pipeline"] = ControlledLearningPipeline(db_manager=db_mgr, feedback_sys=services["feedback_system"])

    app = create_app(services=services)
    return TestClient(app)


def test_memory_records_crud_endpoints(client):
    user_id = "test_user_api_01"

    # POST create
    res = client.post(
        "/api/v1/memory/records",
        json={
            "user_id": user_id,
            "content": "The 404 Founders model is built without pretrained weights.",
            "summary": "Core architectural invariant",
            "importance": 0.95,
            "tags": ["core", "training"],
        },
    )
    assert res.status_code == 200
    data = res.json()
    record_id = data["record_id"]
    assert data["version"] == 1
    assert data["status"] == "ACTIVE"

    # GET list
    res_list = client.get(f"/api/v1/memory/records?user_id={user_id}")
    assert res_list.status_code == 200
    items = res_list.json()
    assert len(items) == 1
    assert items[0]["record_id"] == record_id

    # PUT update
    res_update = client.put(
        f"/api/v1/memory/records/{record_id}",
        json={
            "user_id": user_id,
            "new_content": "The 404 Founders model is strictly built from random initialization.",
            "importance": 0.99,
        },
    )
    assert res_update.status_code == 200
    up_data = res_update.json()
    assert up_data["version"] == 2
    assert up_data["parent_version_id"] == record_id

    # DELETE record
    res_del = client.delete(f"/api/v1/memory/records/{up_data['record_id']}?user_id={user_id}")
    assert res_del.status_code == 200
    assert res_del.json()["deleted"] is True


def test_short_term_memory_endpoints(client):
    user_id = "test_user_stm_api"
    session_id = "sess_stm_api_01"

    # POST message
    res = client.post(
        "/api/v1/memory/short-term",
        json={
            "user_id": user_id,
            "session_id": session_id,
            "role": "user",
            "content": "Execute preflight compute checks.",
        },
    )
    assert res.status_code == 200
    msg = res.json()
    assert msg["role"] == "user"

    # GET history
    res_hist = client.get(f"/api/v1/memory/short-term?user_id={user_id}&session_id={session_id}")
    assert res_hist.status_code == 200
    history = res_hist.json()
    assert len(history) == 1

    # DELETE session
    res_clear = client.delete(f"/api/v1/memory/short-term?user_id={user_id}&session_id={session_id}")
    assert res_clear.status_code == 200
    assert res_clear.json()["status"] == "success"


def test_working_memory_endpoints(client):
    session_id = "sess_wm_api_01"
    task_id = "task_bpe_train"

    # POST start task
    res = client.post(
        "/api/v1/memory/working",
        json={
            "session_id": session_id,
            "task_id": task_id,
            "task_name": "Train Custom BPE",
            "objectives": ["Tokenize corpus", "Compute merge rules"],
            "initial_results": {"vocab_target": 32000},
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["task_id"] == task_id
    assert data["status"] == "ACTIVE"

    # GET list
    res_list = client.get(f"/api/v1/memory/working?session_id={session_id}")
    assert res_list.status_code == 200
    tasks = res_list.json()
    assert len(tasks) == 1


def test_episodic_memory_endpoints(client):
    user_id = "test_user_ep_api"

    # POST episode
    res = client.post(
        "/api/v1/memory/episodic",
        json={
            "user_id": user_id,
            "event_description": "Successfully trained toy model with loss reduction.",
            "outcome": "Loss converged under 0.1",
            "task_id": "toy_pretrain_01",
        },
    )
    assert res.status_code == 200
    ev = res.json()
    assert ev["event_id"].startswith("ep_")

    # GET search
    res_search = client.get(f"/api/v1/memory/episodic?user_id={user_id}&query=loss+reduction")
    assert res_search.status_code == 200
    results = res_search.json()
    assert len(results) >= 1


def test_preferences_endpoints(client):
    user_id = "test_user_pref_api"

    # GET defaults
    res_get = client.get(f"/api/v1/memory/preferences?user_id={user_id}")
    assert res_get.status_code == 200
    prefs = res_get.json()
    assert prefs["communication_style"] == "balanced"

    # POST set
    res_set = client.post(
        "/api/v1/memory/preferences",
        json={
            "user_id": user_id,
            "preference_key": "communication_style",
            "preference_val": "academic",
            "is_explicit": True,
        },
    )
    assert res_set.status_code == 200
    assert res_set.json()["preference_val"] == "academic"

    # DELETE pref
    res_del = client.delete(f"/api/v1/memory/preferences/communication_style?user_id={user_id}")
    assert res_del.status_code == 200
    assert res_del.json()["deleted"] is True


def test_hybrid_retrieval_and_context_endpoints(client):
    user_id = "test_user_ret_api"
    session_id = "sess_ret_api"

    # Save a record
    client.post(
        "/api/v1/memory/records",
        json={
            "user_id": user_id,
            "content": "Sparse attention sliding window uses window size of 256 tokens.",
            "summary": "Attention window specification",
            "importance": 0.88,
            "tags": ["sparse_attention", "window"],
        },
    )

    # POST retrieve
    res_ret = client.post(
        "/api/v1/memory/retrieve",
        json={
            "user_id": user_id,
            "query": "sliding window attention size",
            "limit": 5,
        },
    )
    assert res_ret.status_code == 200
    scored = res_ret.json()
    assert len(scored) >= 1
    assert scored[0]["final_score"] > 0

    # POST context assembly
    res_ctx = client.post(
        "/api/v1/memory/context",
        json={
            "user_id": user_id,
            "session_id": session_id,
            "current_query": "sliding window attention size",
            "token_budget": 2048,
        },
    )
    assert res_ctx.status_code == 200
    ctx_data = res_ctx.json()
    assert ctx_data["estimated_tokens"] <= 2048
    assert "sliding window" in ctx_data["full_context_text"]


def test_continual_learning_pipeline_endpoints(client):
    user_id = "test_user_cl_api"

    # Submit feedback
    res_fb = client.post(
        "/api/v1/learning/feedback",
        json={
            "user_id": user_id,
            "feedback_type": "POSITIVE",
            "rating": 5,
            "category": "factual_accuracy",
            "comment": "Perfect explanation of custom attention layers.",
        },
    )
    assert res_fb.status_code == 200
    fb_data = res_fb.json()
    fb_id = fb_data["feedback_id"]

    # Validate feedback
    res_val = client.post(
        f"/api/v1/learning/feedback/{fb_id}/validate",
        json={"is_valid": True, "notes": "Verified good response"},
    )
    assert res_val.status_code == 200

    # Create learning job
    res_job = client.post(
        "/api/v1/learning/jobs",
        json={"target_version": "0.5.1-offline"},
    )
    assert res_job.status_code == 200
    job = res_job.json()
    job_id = job["job_id"]
    assert job["status"] == "PENDING"

    # Run pipeline up to versioning
    res_run = client.post(f"/api/v1/learning/jobs/{job_id}/run-pipeline")
    assert res_run.status_code == 200
    run_data = res_run.json()
    assert run_data["status"] == "AWAITING_APPROVAL"
    assert run_data["stage_history_count"] == 8

    # Approve job
    res_app = client.post(
        f"/api/v1/learning/jobs/{job_id}/approve",
        json={"approver": "governance_director", "approved": True, "reason": "Benchmarks passed"},
    )
    assert res_app.status_code == 200
    app_data = res_app.json()
    assert app_data["status"] == "DEPLOYED"
    assert app_data["is_approved"] is True
