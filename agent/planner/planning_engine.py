"""
404 FOUNDERS — Planning and Decision-Making Engine
Provides goal decomposition, dependency DAG sequencing, alternative approach comparison,
risk level classification, and mandatory human approval gating for sensitive actions.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from security.permissions import PermissionTier, parse_tier


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class PlanTask:
    """Represents a discrete step or subtask within an execution plan."""
    id: str
    title: str
    description: str
    dependencies: List[str] = field(default_factory=list)
    risk_tier: str = "read_only"
    requires_human_approval: bool = False
    is_irreversible: bool = False
    status: TaskStatus = TaskStatus.PENDING
    assigned_tool: Optional[str] = None
    approval_granted: bool = False


@dataclass
class AlternativeApproach:
    """An alternative strategic path for achieving the goal."""
    title: str
    description: str
    pros: List[str]
    cons: List[str]
    estimated_risk: str
    complexity_level: str  # "LOW", "MEDIUM", "HIGH"


@dataclass
class ExecutionPlan:
    """Complete sequenced execution DAG for an objective."""
    objective: str
    tasks: List[PlanTask]
    task_order: List[str]
    has_cycles: bool
    requires_human_approval: bool
    pending_approvals_count: int
    alternative_approaches: List[AlternativeApproach]
    summary: str


class PlanningDecisionEngine:
    """
    Planning and decision-making engine.
    Decomposes objectives into topologically sorted subtasks,
    evaluates risk tiers against PermissionTier policies, and enforces
    mandatory operator approval gates for irreversible actions.
    """

    IRREVERSIBLE_KEYWORDS = [
        "delete", "drop", "overwrite", "format", "reboot",
        "kill", "modify system", "truncate", "wipe", "push to prod",
    ]

    PRIVILEGED_KEYWORDS = [
        "install", "configure", "iptables", "network", "chmod", "chown", "systemctl",
    ]

    def classify_task_risk(self, title: str, description: str) -> Tuple[str, bool, bool]:
        """Classify permission tier, irreversibility, and human approval requirement."""
        text = f"{title} {description}".lower()

        is_irreversible = any(k in text for k in self.IRREVERSIBLE_KEYWORDS)
        is_privileged = any(k in text for k in self.PRIVILEGED_KEYWORDS)

        if is_irreversible:
            risk_tier = "dangerous"
            requires_approval = True
        elif is_privileged:
            risk_tier = "privileged"
            requires_approval = True
        elif any(k in text for k in ["write", "update", "create", "edit"]):
            risk_tier = "protected"
            requires_approval = False
        else:
            risk_tier = "read_only"
            requires_approval = False

        return risk_tier, is_irreversible, requires_approval

    def topological_sort(self, tasks: List[PlanTask]) -> Tuple[List[str], bool]:
        """Compute valid topological ordering of tasks; returns (order, has_cycle)."""
        task_map = {t.id: t for t in tasks}
        in_degree: Dict[str, int] = {t.id: 0 for t in tasks}
        adjacency: Dict[str, List[str]] = {t.id: [] for t in tasks}

        for t in tasks:
            for dep in t.dependencies:
                if dep in task_map:
                    adjacency[dep].append(t.id)
                    in_degree[t.id] += 1

        # Queue nodes with in_degree == 0
        queue = [tid for tid, deg in in_degree.items() if deg == 0]
        order: List[str] = []

        while queue:
            curr = queue.pop(0)
            order.append(curr)
            for neighbor in adjacency[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        has_cycle = len(order) != len(tasks)
        if has_cycle:
            # Append remaining tasks
            for t in tasks:
                if t.id not in order:
                    order.append(t.id)

        return order, has_cycle

    def create_plan(
        self,
        objective: str,
        subtasks_data: Optional[List[Dict[str, Any]]] = None,
    ) -> ExecutionPlan:
        """Decompose objective into a sequenced execution DAG with risk analysis."""
        if not objective.strip():
            raise ValueError("Objective cannot be empty.")

        tasks: List[PlanTask] = []

        if subtasks_data:
            for item in subtasks_data:
                tid = str(item.get("id", f"task_{len(tasks)+1}"))
                title = str(item.get("title", ""))
                desc = str(item.get("description", ""))
                deps = list(item.get("dependencies", []))
                risk, is_irrev, req_app = self.classify_task_risk(title, desc)

                tasks.append(PlanTask(
                    id=tid,
                    title=title,
                    description=desc,
                    dependencies=deps,
                    risk_tier=risk,
                    requires_human_approval=req_app or is_irrev,
                    is_irreversible=is_irrev,
                    status=TaskStatus.READY if not deps else TaskStatus.PENDING,
                ))
        else:
            # Default structured decomposition
            step1_risk, step1_irrev, step1_app = self.classify_task_risk("Inspect Environment", "Inspect existing system configuration and prerequisites.")
            tasks.append(PlanTask("T1", "Inspect Environment", "Read-only inspection of prerequisites.", [], step1_risk, step1_app, step1_irrev, TaskStatus.READY))

            step2_risk, step2_irrev, step2_app = self.classify_task_risk("Execute Plan Operations", f"Implement changes required for '{objective}'.")
            tasks.append(PlanTask("T2", "Execute Plan Operations", f"Execute core actions for objective.", ["T1"], step2_risk, step2_app, step2_irrev, TaskStatus.PENDING))

            step3_risk, step3_irrev, step3_app = self.classify_task_risk("Verify Results", "Validate outcomes against success criteria.")
            tasks.append(PlanTask("T3", "Verify Results", "Validate that modifications meet target criteria.", ["T2"], step3_risk, step3_app, step3_irrev, TaskStatus.PENDING))

        task_order, has_cycle = self.topological_sort(tasks)

        approvals_needed = sum(1 for t in tasks if t.requires_human_approval and not t.approval_granted)

        alternatives = [
            AlternativeApproach(
                title="Incremental Conservative Rollout",
                description="Execute operations stage-by-stage with manual verification checkpoints between each step.",
                pros=["Lowest catastrophic failure risk", "Immediate rollback opportunity"],
                cons=["Slower end-to-end execution latency"],
                estimated_risk="read_only / protected",
                complexity_level="LOW",
            ),
            AlternativeApproach(
                title="Parallel Optimized Batching",
                description="Execute all independent non-dependent steps concurrently in parallel.",
                pros=["Fastest completion time", "Maximizes resource utilization"],
                cons=["Higher risk if transient dependencies exist", "Harder to isolate failures"],
                estimated_risk="privileged",
                complexity_level="MEDIUM",
            ),
        ]

        summary = (
            f"Plan constructed with {len(tasks)} tasks (topological cycle={has_cycle}). "
            f"Identified {approvals_needed} task(s) requiring mandatory human operator approval."
        )

        return ExecutionPlan(
            objective=objective,
            tasks=tasks,
            task_order=task_order,
            has_cycles=has_cycle,
            requires_human_approval=approvals_needed > 0,
            pending_approvals_count=approvals_needed,
            alternative_approaches=alternatives,
            summary=summary,
        )

    def grant_approval(self, plan: ExecutionPlan, task_id: str) -> bool:
        """Explicitly record operator approval for a sensitive task."""
        for t in plan.tasks:
            if t.id == task_id:
                t.approval_granted = True
                plan.pending_approvals_count = sum(1 for x in plan.tasks if x.requires_human_approval and not x.approval_granted)
                plan.requires_human_approval = plan.pending_approvals_count > 0
                return True
        return False
