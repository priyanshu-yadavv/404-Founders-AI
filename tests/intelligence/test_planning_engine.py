"""
404 FOUNDERS — Planning and Decision-Making Engine Unit Tests
"""

import pytest
from agent.planner.planning_engine import PlanningDecisionEngine, TaskStatus


@pytest.fixture
def engine() -> PlanningDecisionEngine:
    return PlanningDecisionEngine()


def test_topological_sequencing(engine: PlanningDecisionEngine) -> None:
    subtasks = [
        {"id": "T3", "title": "Run Smoke Tests", "dependencies": ["T2"]},
        {"id": "T1", "title": "Fetch Dependencies", "dependencies": []},
        {"id": "T2", "title": "Compile Binaries", "dependencies": ["T1"]},
    ]
    plan = engine.create_plan("Build & Test Workspace", subtasks)
    assert plan.task_order == ["T1", "T2", "T3"]
    assert plan.has_cycles is False


def test_risk_classification_and_human_gating(engine: PlanningDecisionEngine) -> None:
    sensitive_subtasks = [
        {"id": "T1", "title": "Inspect File Tree", "description": "Read directory list", "dependencies": []},
        {"id": "T2", "title": "Delete Partition", "description": "Format disk partition", "dependencies": ["T1"]},
    ]
    plan = engine.create_plan("Disk maintenance", sensitive_subtasks)
    assert plan.requires_human_approval is True
    assert plan.pending_approvals_count == 1

    t2 = next(t for t in plan.tasks if t.id == "T2")
    assert t2.risk_tier == "dangerous"
    assert t2.is_irreversible is True
    assert t2.requires_human_approval is True
    assert t2.approval_granted is False

    # Grant operator approval
    granted = engine.grant_approval(plan, "T2")
    assert granted is True
    assert plan.requires_human_approval is False
    assert plan.pending_approvals_count == 0


def test_default_decomposition(engine: PlanningDecisionEngine) -> None:
    plan = engine.create_plan("Upgrade GPU driver package on training cluster")
    assert len(plan.tasks) == 3
    assert plan.tasks[0].id == "T1"
    assert plan.tasks[0].status == TaskStatus.READY
    assert len(plan.alternative_approaches) >= 2
