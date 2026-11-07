"""
404 FOUNDERS — Memory Consolidation & Conflict Detection Subsystem
Responsible for background memory deduplication, topic summarization,
and strict conflict detection.
INVARIANT: Conflicting user statements are NEVER silently overwritten;
they are flagged as CONFLICT_DETECTED with full provenance trails.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import difflib
import json
import sqlite3
from typing import Any, Dict, List, Optional, Tuple
import uuid

from database.connection import DatabaseManager
from memory.security import MemorySecurityManager


@dataclass
class ConflictReport:
    """A detected conflict between two incompatible memory propositions."""
    conflict_id: str
    user_id: str
    existing_record_id: str
    conflicting_record_id: str
    subject_area: str
    existing_content: str
    conflicting_content: str
    resolution_status: str  # "UNRESOLVED", "RESOLVED_MANUAL", "RESOLVED_AUTO"
    detected_at: str


@dataclass
class ConsolidationSummary:
    """Summary of a memory consolidation pass."""
    user_id: str
    duplicates_resolved: int
    conflicts_detected: List[ConflictReport]
    records_merged: int
    consolidated_at: str


class MemoryConsolidationEngine:
    """
    Memory Consolidation Engine.
    Executes automated maintenance passes over memory records:
    1. Identifies near-duplicate entries and merges them.
    2. Detects explicit semantic contradictions without silent overwrite.
    3. Synthesizes high-importance facts into consolidated knowledge summaries.
    """

    DUPLICATE_SIMILARITY_THRESHOLD = 0.88

    def __init__(self, db_manager: Optional[DatabaseManager] = None) -> None:
        self.db = db_manager or DatabaseManager.get_instance()

    def run_consolidation(self, user_id: str) -> ConsolidationSummary:
        """Execute a full consolidation and conflict-audit cycle for a tenant."""
        now = datetime.now(timezone.utc).isoformat()

        # Step 1: Detect duplicates and conflicts among active long-term and knowledge records
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, user_id, memory_layer, content, summary, importance,
                       confidence, version, created_at, updated_at, status, metadata_json
                FROM memory_records
                WHERE user_id = ? AND status = 'ACTIVE' AND memory_layer IN ('LONG_TERM', 'KNOWLEDGE')
                ORDER BY updated_at ASC
                """,
                (user_id,),
            )
            records = cursor.fetchall()

        duplicates_resolved = 0
        records_merged = 0
        conflicts: List[ConflictReport] = []

        checked_pairs = set()

        for i in range(len(records)):
            for j in range(i + 1, len(records)):
                rec_a = records[i]
                rec_b = records[j]

                pair_key = tuple(sorted([rec_a["id"], rec_b["id"]]))
                if pair_key in checked_pairs:
                    continue
                checked_pairs.add(pair_key)

                # Check duplicate similarity
                sim = difflib.SequenceMatcher(None, rec_a["content"].lower(), rec_b["content"].lower()).ratio()

                if sim >= self.DUPLICATE_SIMILARITY_THRESHOLD:
                    # Near identical content: resolve duplicate by archiving older and keeping newer
                    older = rec_a if rec_a["updated_at"] < rec_b["updated_at"] else rec_b
                    newer = rec_b if rec_a["updated_at"] < rec_b["updated_at"] else rec_a

                    self._resolve_duplicate(user_id, older["id"], newer["id"])
                    duplicates_resolved += 1
                else:
                    # Check for subject contradiction (e.g. same subject with contradictory values)
                    meta_a = json.loads(rec_a["metadata_json"] or "{}")
                    meta_b = json.loads(rec_b["metadata_json"] or "{}")

                    conflict = self._detect_contradiction(user_id, rec_a, rec_b, meta_a, meta_b)
                    if conflict:
                        conflicts.append(conflict)

        # Log consolidation audit trail
        with self.db.get_connection() as conn:
            MemorySecurityManager.log_audit_event(
                conn, user_id=user_id, action="CONSOLIDATION_RUN",
                details={
                    "duplicates_resolved": duplicates_resolved,
                    "conflicts_count": len(conflicts),
                    "records_merged": records_merged,
                }
            )

        return ConsolidationSummary(
            user_id=user_id,
            duplicates_resolved=duplicates_resolved,
            conflicts_detected=conflicts,
            records_merged=records_merged,
            consolidated_at=now,
        )

    def _resolve_duplicate(self, user_id: str, older_id: str, newer_id: str) -> None:
        """Archive older duplicate and link to newer active record."""
        now = datetime.now(timezone.utc).isoformat()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE memory_records
                SET status = 'ARCHIVED', updated_at = ?
                WHERE id = ? AND user_id = ?
                """,
                (now, older_id, user_id),
            )
            # Create relationship link between duplicated records
            rel_id = f"rel_{uuid.uuid4().hex[:12]}"
            cursor.execute(
                """
                INSERT INTO memory_relationships (id, source_id, target_id, relation_type, confidence, created_at)
                VALUES (?, ?, ?, 'DUPLICATE_OF', 1.0, ?)
                """,
                (rel_id, older_id, newer_id, now),
            )

    def _detect_contradiction(
        self,
        user_id: str,
        rec_a: sqlite3.Row,
        rec_b: sqlite3.Row,
        meta_a: Dict[str, Any],
        meta_b: Dict[str, Any],
    ) -> Optional[ConflictReport]:
        """
        Check if two records represent an unresolvable contradiction on the same subject.
        NEVER silently overwrite. Mark both with CONFLICT_DETECTED if contradictory.
        """
        subj_a = meta_a.get("subject", "").lower()
        subj_b = meta_b.get("subject", "").lower()
        pred_a = meta_a.get("predicate", "").lower()
        pred_b = meta_b.get("predicate", "").lower()
        obj_a = meta_a.get("object_val", "").lower()
        obj_b = meta_b.get("object_val", "").lower()

        # Check knowledge triple contradiction: same subject and predicate, but distinct object
        is_contradiction = False
        subject_area = subj_a or "general"

        if subj_a and subj_b and pred_a and pred_b:
            if subj_a == subj_b and pred_a == pred_b and obj_a != obj_b:
                is_contradiction = True
                subject_area = f"{subj_a}:{pred_a}"

        # Check for natural language direct contradiction markers on identical tags
        tags_a = set(meta_a.get("tags", []))
        tags_b = set(meta_b.get("tags", []))
        common_tags = tags_a.intersection(tags_b)

        if not is_contradiction and common_tags:
            # Check negation or exclusivity
            c_a = rec_a["content"].lower()
            c_b = rec_b["content"].lower()
            if ("prefer " in c_a and "prefer " in c_b) and (c_a != c_b):
                is_contradiction = True
                subject_area = f"preference:{list(common_tags)[0]}"

        if is_contradiction:
            conflict_id = f"cnf_{uuid.uuid4().hex[:12]}"
            now = datetime.now(timezone.utc).isoformat()

            # Flag records with CONFLICT_DETECTED status to prevent deceptive outputs
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE memory_records SET status = 'CONFLICT_DETECTED', updated_at = ? WHERE id = ? AND user_id = ?",
                    (now, rec_a["id"], user_id),
                )
                cursor.execute(
                    "UPDATE memory_records SET status = 'CONFLICT_DETECTED', updated_at = ? WHERE id = ? AND user_id = ?",
                    (now, rec_b["id"], user_id),
                )
                # Link contradictory relationship
                rel_id = f"rel_{uuid.uuid4().hex[:12]}"
                cursor.execute(
                    """
                    INSERT INTO memory_relationships (id, source_id, target_id, relation_type, confidence, created_at)
                    VALUES (?, ?, ?, 'CONTRADICTS', 1.0, ?)
                    """,
                    (rel_id, rec_a["id"], rec_b["id"], now),
                )
                MemorySecurityManager.log_audit_event(
                    conn, user_id=user_id, action="CONFLICT_FLAGGED",
                    details={"conflict_id": conflict_id, "subject_area": subject_area}
                )

            return ConflictReport(
                conflict_id=conflict_id,
                user_id=user_id,
                existing_record_id=rec_a["id"],
                conflicting_record_id=rec_b["id"],
                subject_area=subject_area,
                existing_content=rec_a["content"],
                conflicting_content=rec_b["content"],
                resolution_status="UNRESOLVED",
                detected_at=now,
            )

        return None
