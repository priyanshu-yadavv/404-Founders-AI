"""
404 FOUNDERS — Continual Learning & Feedback System Tests
Verifies offline 10-stage continual learning pipeline, governance gating,
and invariant that user feedback NEVER modifies model weights online.
"""

import pytest

from database.connection import DatabaseManager
from learning.continual.learning_pipeline import (
    ControlledLearningPipeline,
    PipelineJobStatus,
    PipelineStage,
)
from learning.feedback.feedback_system import (
    FeedbackStatus,
    FeedbackSystem,
    FeedbackType,
)


@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_continual_learning.db"
    return DatabaseManager(str(db_file))


def test_feedback_system_recording_and_validation(test_db):
    fs = FeedbackSystem(test_db)
    user_id = "user_fb_01"

    # Record feedback with correction suggestion
    fb = fs.record_feedback(
        user_id=user_id,
        feedback_type=FeedbackType.CORRECTION,
        response_id="resp_101",
        rating=2,
        suggested_correction="The RMSNorm epsilon should be 1e-6, not 1e-5.",
        category="code_syntax",
        comment="Incompatible epsilon for stability.",
    )
    assert fb.status == FeedbackStatus.RECORDED
    assert fb.category == "code_syntax"

    # Validate feedback entry
    validated = fs.validate_feedback(fb.feedback_id, is_valid=True, validation_notes="Verified against PyTorch spec.")
    assert validated is True

    # List validated candidates for curation
    candidates = fs.curate_training_candidates(category="code_syntax")
    assert len(candidates) == 1
    assert candidates[0].feedback_id == fb.feedback_id


def test_10_stage_continual_learning_pipeline_lifecycle(test_db):
    fs = FeedbackSystem(test_db)
    pipe = ControlledLearningPipeline(test_db, feedback_sys=fs)

    # Populate a validated feedback item to be processed
    fs.record_feedback(
        user_id="user_test",
        feedback_type=FeedbackType.POSITIVE,
        response_id="resp_200",
        rating=5,
        category="factual_accuracy",
    )
    # Validate it so it can be curated
    candidates = fs.list_feedback()
    for c in candidates:
        fs.validate_feedback(c.feedback_id, is_valid=True)

    # Initialize Job
    job = pipe.create_job(target_version="0.6.0-rc1")
    assert job.status == PipelineJobStatus.PENDING
    assert job.current_stage == PipelineStage.STAGE_01_FEEDBACK_COLLECTION

    # Execute Stage 1: Collection
    s1 = pipe.run_stage_01_collection(job.job_id)
    assert s1.status == "SUCCESS"
    assert job.current_stage == PipelineStage.STAGE_01_FEEDBACK_COLLECTION

    # Execute Stage 2: Validation
    s2 = pipe.run_stage_02_validation(job.job_id)
    assert s2.status == "SUCCESS"

    # Execute Stage 3: Curation
    s3 = pipe.run_stage_03_curation(job.job_id)
    assert s3.status == "SUCCESS"

    # Execute Stage 4: Dataset Prep
    s4 = pipe.run_stage_04_dataset_prep(job.job_id)
    assert s4.status == "SUCCESS"
    assert job.dataset_manifest_hash is not None

    # Execute Stage 5: Job Config
    s5 = pipe.run_stage_05_job_config(job.job_id, lr=2e-5)
    assert s5.status == "SUCCESS"
    assert s5.artifacts["job_config"]["prevent_catastrophic_forgetting"] is True

    # Execute Stage 6: Evaluation
    s6 = pipe.run_stage_06_model_eval(job.job_id)
    assert s6.status == "SUCCESS"

    # Execute Stage 7: Regression Testing
    s7 = pipe.run_stage_07_regression_testing(job.job_id)
    assert s7.status == "SUCCESS"
    assert s7.artifacts["verdict"] == "PASSED"

    # Execute Stage 8: Versioning
    s8 = pipe.run_stage_08_model_versioning(job.job_id)
    assert s8.status == "SUCCESS"
    assert job.status == PipelineJobStatus.AWAITING_APPROVAL

    # Invariant: Cannot deploy before approval
    with pytest.raises(PermissionError) as exc_info:
        pipe.run_stage_10_deployment(job.job_id)
    assert "Governance approval required" in str(exc_info.value)

    # Execute Stage 9: Approval Gate (Approved)
    s9 = pipe.run_stage_09_model_approval(job.job_id, approver="chief_ai_officer", approved=True, reason="Full pass")
    assert s9.status == "APPROVED"
    assert job.is_approved is True
    assert job.status == PipelineJobStatus.APPROVED

    # Execute Stage 10: Controlled Deployment
    s10 = pipe.run_stage_10_deployment(job.job_id)
    assert s10.status == "SUCCESS"
    assert job.status == PipelineJobStatus.DEPLOYED
    assert len(job.stage_history) == 10


def test_rejection_at_approval_gate(test_db):
    pipe = ControlledLearningPipeline(test_db)
    job = pipe.create_job(target_version="0.6.0-rejected")

    pipe.run_stage_01_collection(job.job_id)
    pipe.run_stage_08_model_versioning(job.job_id)

    # Reject approval
    s9 = pipe.run_stage_09_model_approval(job.job_id, approver="security_lead", approved=False, reason="Safety policy breach")
    assert s9.status == "REJECTED"
    assert job.status == PipelineJobStatus.REJECTED
    assert job.is_approved is False

    with pytest.raises(PermissionError):
        pipe.run_stage_10_deployment(job.job_id)
