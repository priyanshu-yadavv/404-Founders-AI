"""
404 FOUNDERS — Working Memory Subsystem
Maintains session- and task-isolated temporary memory, active objectives,
intermediate computation results, dependencies, and pending actions with restart recovery.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import sqlite3
from typing import Any, Dict, List, Optional
import uuid

from database.connection import DatabaseManager
from memory.security import MemorySecurityManager


@dataclass
class WorkingTask:
    """A working task state representation."""
    task_id: str
    session_id: str
    task_name: str
    active_objectives: List[str]
    intermediate_results: Dict[str, Any]
    dependencies: List[str]
    pending_actions: List[Dict[str, Any]]
    status: str  # "ACTIVE", "PAUSED", "COMPLETED", "FAILED"
    created_at: str
    updated_at: str


class WorkingMemory:
    """
    Session- and Task-Isolated Working Memory Engine.
    Ensures safe persistence of intermediate states, multi-step execution tracking,
    and automatic state recovery across system restarts.
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None) -> None:
        self.db = db_manager or DatabaseManager.get_instance()

    def start_task(
        self,
        session_id: str,
        task_id: str,
        task_name: str,
        objectives: Optional[List[str]] = None,
        dependencies: Optional[List[str]] = None,
        initial_results: Optional[Dict[str, Any]] = None,
    ) -> WorkingTask:
        """Initialize or resume an active working task."""
        now = datetime.now(timezone.utc).isoformat()
        objectives_clean = [MemorySecurityManager.scrub_secrets(obj)[0] for obj in (objectives or [])]
        dependencies_clean = dependencies or []
        results = initial_results or {}

        # Sanitize string values inside initial_results
        cleaned_results = self._sanitize_dict(results)

        task_uuid = f"wt_{uuid.uuid4().hex[:12]}"

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO working_memory_tasks (
                    id, session_id, task_id, task_name, active_objectives_json,
                    intermediate_results_json, dependencies_json, pending_actions_json,
                    status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id, task_id) DO UPDATE SET
                    task_name = excluded.task_name,
                    active_objectives_json = excluded.active_objectives_json,
                    dependencies_json = excluded.dependencies_json,
                    status = 'ACTIVE',
                    updated_at = excluded.updated_at
                """,
                (
                    task_uuid,
                    session_id,
                    task_id,
                    task_name,
                    json.dumps(objectives_clean),
                    json.dumps(cleaned_results),
                    json.dumps(dependencies_clean),
                    json.dumps([]),
                    "ACTIVE",
                    now,
                    now,
                ),
            )
            # Memory audit log
            MemorySecurityManager.log_audit_event(
                conn, user_id=f"session_{session_id}", action="WORKING_TASK_START",
                session_id=session_id, details={"task_id": task_id, "task_name": task_name}
            )

        return WorkingTask(
            task_id=task_id,
            session_id=session_id,
            task_name=task_name,
            active_objectives=objectives_clean,
            intermediate_results=cleaned_results,
            dependencies=dependencies_clean,
            pending_actions=[],
            status="ACTIVE",
            created_at=now,
            updated_at=now,
        )

    def update_task(
        self,
        session_id: str,
        task_id: str,
        intermediate_results: Optional[Dict[str, Any]] = None,
        pending_actions: Optional[List[Dict[str, Any]]] = None,
        active_objectives: Optional[List[str]] = None,
        status: Optional[str] = None,
    ) -> WorkingTask:
        """Update progress, intermediate checkpoints, or pending actions for a task."""
        current = self.get_task(session_id, task_id)
        if not current:
            raise KeyError(f"Working task '{task_id}' in session '{session_id}' not found.")

        now = datetime.now(timezone.utc).isoformat()
        new_status = status if status is not None else current.status

        # Merge intermediate results
        merged_results = dict(current.intermediate_results)
        if intermediate_results:
            merged_results.update(self._sanitize_dict(intermediate_results))

        # Update objectives if given
        new_objectives = current.active_objectives
        if active_objectives is not None:
            new_objectives = [MemorySecurityManager.scrub_secrets(obj)[0] for obj in active_objectives]

        # Update pending actions if given
        new_actions = pending_actions if pending_actions is not None else current.pending_actions

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE working_memory_tasks
                SET active_objectives_json = ?,
                    intermediate_results_json = ?,
                    pending_actions_json = ?,
                    status = ?,
                    updated_at = ?
                WHERE session_id = ? AND task_id = ?
                """,
                (
                    json.dumps(new_objectives),
                    json.dumps(merged_results),
                    json.dumps(new_actions),
                    new_status,
                    now,
                    session_id,
                    task_id,
                ),
            )
            MemorySecurityManager.log_audit_event(
                conn, user_id=f"session_{session_id}", action="WORKING_TASK_UPDATE",
                session_id=session_id, details={"task_id": task_id, "status": new_status}
            )

        return WorkingTask(
            task_id=task_id,
            session_id=session_id,
            task_name=current.task_name,
            active_objectives=new_objectives,
            intermediate_results=merged_results,
            dependencies=current.dependencies,
            pending_actions=new_actions,
            status=new_status,
            created_at=current.created_at,
            updated_at=now,
        )

    def get_task(self, session_id: str, task_id: str) -> Optional[WorkingTask]:
        """Fetch working task state by session and task identifier."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT session_id, task_id, task_name, active_objectives_json,
                       intermediate_results_json, dependencies_json, pending_actions_json,
                       status, created_at, updated_at
                FROM working_memory_tasks
                WHERE session_id = ? AND task_id = ?
                """,
                (session_id, task_id),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_task(row)

    def list_active_tasks(self, session_id: str) -> List[WorkingTask]:
        """List all active or paused tasks within a specific session."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT session_id, task_id, task_name, active_objectives_json,
                       intermediate_results_json, dependencies_json, pending_actions_json,
                       status, created_at, updated_at
                FROM working_memory_tasks
                WHERE session_id = ? AND status IN ('ACTIVE', 'PAUSED')
                ORDER BY updated_at DESC
                """,
                (session_id,),
            )
            rows = cursor.fetchall()
            return [self._row_to_task(r) for r in rows]

    def complete_task(self, session_id: str, task_id: str, final_outcome: Optional[Dict[str, Any]] = None) -> WorkingTask:
        """Mark a working task as completed and persist final results."""
        return self.update_task(
            session_id=session_id,
            task_id=task_id,
            intermediate_results=final_outcome,
            pending_actions=[],
            status="COMPLETED",
        )

    def clear_session_tasks(self, session_id: str) -> int:
        """Clear all working memory tasks for a terminated session."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM working_memory_tasks WHERE session_id = ?",
                (session_id,),
            )
            count = cursor.rowcount
            MemorySecurityManager.log_audit_event(
                conn, user_id=f"session_{session_id}", action="WORKING_TASKS_CLEAR",
                session_id=session_id, details={"cleared_count": count}
            )
            return count

    @staticmethod
    def _sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively scrub secrets from dict string values."""
        clean: Dict[str, Any] = {}
        for k, v in data.items():
            if isinstance(v, str):
                clean[k], _ = MemorySecurityManager.scrub_secrets(v)
            elif isinstance(v, dict):
                clean[k] = WorkingMemory._sanitize_dict(v)
            elif isinstance(v, list):
                clean[k] = [
                    MemorySecurityManager.scrub_secrets(item)[0] if isinstance(item, str) else item
                    for item in v
                ]
            else:
                clean[k] = v
        return clean

    @staticmethod
    def _row_to_task(row: sqlite3.Row) -> WorkingTask:
        return WorkingTask(
            session_id=row["session_id"],
            task_id=row["task_id"],
            task_name=row["task_name"],
            active_objectives=json.loads(row["active_objectives_json"] or "[]"),
            intermediate_results=json.loads(row["intermediate_results_json"] or "{}"),
            dependencies=json.loads(row["dependencies_json"] or "[]"),
            pending_actions=json.loads(row["pending_actions_json"] or "[]"),
            status=row["status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
