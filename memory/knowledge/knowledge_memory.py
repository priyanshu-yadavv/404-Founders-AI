"""
404 FOUNDERS — Semantic & Knowledge Memory Subsystem
Maintains structured facts, concepts, entities, and causal/semantic relationships.
Strictly distinguishes verified facts from unverified claims and user assertions.
Tracks source attribution, confidence levels, and relational links.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
import sqlite3
from typing import Any, Dict, List, Optional
import uuid

from database.connection import DatabaseManager
from memory.security import MemorySecurityManager


class ClaimType(str, Enum):
    """Classification of epistemic status for stored knowledge."""
    VERIFIED_FACT = "VERIFIED_FACT"        # Independently verified via ground-truth sources/benchmarks
    UNVERIFIED_CLAIM = "UNVERIFIED_CLAIM"  # Extracted assertion without external verification
    USER_STATED = "USER_STATED"            # Explicitly declared by user during conversation


@dataclass
class KnowledgeFact:
    """A structured knowledge proposition or fact."""
    fact_id: str
    user_id: str
    subject: str
    predicate: str
    object_val: str
    claim_type: ClaimType
    source_attribution: str
    confidence: float
    importance: float
    created_at: str
    updated_at: str
    status: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class KnowledgeRelationship:
    """A directed semantic or causal link between two knowledge records."""
    rel_id: str
    source_id: str
    target_id: str
    relation_type: str  # e.g., "CAUSES", "DEPENDS_ON", "PART_OF", "SUBCLASS_OF", "CONTRADICTS"
    confidence: float
    created_at: str


class KnowledgeMemory:
    """
    Semantic & Knowledge Memory Engine.
    Stores epistemic statements, validates source attributions, manages graph relationships,
    and ensures strict boundaries between factual reality and user-stated claims.
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None) -> None:
        self.db = db_manager or DatabaseManager.get_instance()

    def store_fact(
        self,
        user_id: str,
        subject: str,
        predicate: str,
        object_val: str,
        claim_type: ClaimType = ClaimType.USER_STATED,
        source_attribution: str = "direct_user_input",
        confidence: float = 1.0,
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> KnowledgeFact:
        """Store a structured knowledge fact after secret scrubbing."""
        clean_subj, _ = MemorySecurityManager.scrub_secrets(subject)
        clean_pred, _ = MemorySecurityManager.scrub_secrets(predicate)
        clean_obj, _ = MemorySecurityManager.scrub_secrets(object_val)
        clean_source, _ = MemorySecurityManager.scrub_secrets(source_attribution)

        fact_id = f"km_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        content = f"({clean_subj}) -[{clean_pred}]-> ({clean_obj})"
        meta = metadata or {}
        meta.update({
            "subject": clean_subj,
            "predicate": clean_pred,
            "object_val": clean_obj,
            "claim_type": claim_type.value if isinstance(claim_type, ClaimType) else str(claim_type),
            "source_attribution": clean_source,
        })

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO memory_records (
                    id, user_id, session_id, memory_layer, content, summary,
                    importance, confidence, is_confirmed_by_user, version,
                    created_at, updated_at, status, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fact_id,
                    user_id,
                    None,
                    "KNOWLEDGE",
                    content,
                    content[:100],
                    importance,
                    confidence,
                    1 if claim_type == ClaimType.USER_STATED else 0,
                    1,
                    now,
                    now,
                    "ACTIVE",
                    json.dumps(meta),
                ),
            )
            MemorySecurityManager.log_audit_event(
                conn, user_id=user_id, action="STORE_FACT", memory_id=fact_id,
                details={"subject": clean_subj, "claim_type": meta["claim_type"]}
            )

        return KnowledgeFact(
            fact_id=fact_id,
            user_id=user_id,
            subject=clean_subj,
            predicate=clean_pred,
            object_val=clean_obj,
            claim_type=claim_type,
            source_attribution=clean_source,
            confidence=confidence,
            importance=importance,
            created_at=now,
            updated_at=now,
            status="ACTIVE",
            metadata=meta,
        )

    def query_facts(
        self,
        user_id: str,
        subject: Optional[str] = None,
        predicate: Optional[str] = None,
        claim_type: Optional[ClaimType] = None,
        min_confidence: float = 0.0,
        limit: int = 50,
    ) -> List[KnowledgeFact]:
        """Query knowledge facts filtered by subject, predicate, confidence, and epistemic category."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT id, user_id, content, summary, importance, confidence,
                       is_confirmed_by_user, version, created_at, updated_at, status, metadata_json
                FROM memory_records
                WHERE user_id = ? AND memory_layer = 'KNOWLEDGE' AND status = 'ACTIVE' AND confidence >= ?
            """
            params: List[Any] = [user_id, min_confidence]

            if subject:
                query += " AND json_extract(metadata_json, '$.subject') = ?"
                params.append(subject)
            if predicate:
                query += " AND json_extract(metadata_json, '$.predicate') = ?"
                params.append(predicate)
            if claim_type:
                ct_val = claim_type.value if isinstance(claim_type, ClaimType) else str(claim_type)
                query += " AND json_extract(metadata_json, '$.claim_type') = ?"
                params.append(ct_val)

            query += " ORDER BY confidence DESC, importance DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [self._row_to_fact(r) for r in rows]

    def link_facts(
        self,
        user_id: str,
        source_id: str,
        target_id: str,
        relation_type: str,
        confidence: float = 1.0,
    ) -> KnowledgeRelationship:
        """Create a directed relational link between two knowledge facts."""
        rel_id = f"rel_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO memory_relationships (
                    id, source_id, target_id, relation_type, confidence, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (rel_id, source_id, target_id, relation_type, confidence, now),
            )
            MemorySecurityManager.log_audit_event(
                conn, user_id=user_id, action="LINK_FACTS",
                details={"rel_id": rel_id, "source": source_id, "target": target_id, "type": relation_type}
            )

        return KnowledgeRelationship(
            rel_id=rel_id,
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            confidence=confidence,
            created_at=now,
        )

    def get_related_facts(
        self,
        user_id: str,
        fact_id: str,
    ) -> List[Dict[str, Any]]:
        """Retrieve all facts linked to or from a given fact identifier."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT r.id AS rel_id, r.relation_type, r.confidence AS rel_conf,
                       m.id AS related_id, m.content, m.metadata_json
                FROM memory_relationships r
                JOIN memory_records m ON (r.target_id = m.id AND r.source_id = ?)
                                      OR (r.source_id = m.id AND r.target_id = ?)
                WHERE m.user_id = ? AND m.status = 'ACTIVE'
                """,
                (fact_id, fact_id, user_id),
            )
            rows = cursor.fetchall()
            results: List[Dict[str, Any]] = []
            for row in rows:
                meta = json.loads(row["metadata_json"] or "{}")
                results.append({
                    "relationship_id": row["rel_id"],
                    "relation_type": row["relation_type"],
                    "confidence": row["rel_conf"],
                    "related_fact_id": row["related_id"],
                    "content": row["content"],
                    "subject": meta.get("subject"),
                    "predicate": meta.get("predicate"),
                    "object_val": meta.get("object_val"),
                    "claim_type": meta.get("claim_type"),
                })
            return results

    @staticmethod
    def _row_to_fact(row: sqlite3.Row) -> KnowledgeFact:
        meta = json.loads(row["metadata_json"] or "{}")
        ct_str = meta.get("claim_type", ClaimType.USER_STATED.value)
        try:
            claim_type = ClaimType(ct_str)
        except ValueError:
            claim_type = ClaimType.USER_STATED

        return KnowledgeFact(
            fact_id=row["id"],
            user_id=row["user_id"],
            subject=meta.get("subject", ""),
            predicate=meta.get("predicate", ""),
            object_val=meta.get("object_val", ""),
            claim_type=claim_type,
            source_attribution=meta.get("source_attribution", "unknown"),
            confidence=float(row["confidence"]),
            importance=float(row["importance"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            status=row["status"],
            metadata=meta,
        )
