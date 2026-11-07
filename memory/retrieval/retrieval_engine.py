"""
404 FOUNDERS — Hybrid Memory Retrieval Engine
Combines BM25-style lexical matching, semantic metadata filtering,
exponential recency decay, and deterministic fallback ranking.
Enforces strict cross-user tenant isolation and permission boundaries.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import math
import re
import sqlite3
from typing import Any, Dict, List, Optional, Set

from database.connection import DatabaseManager
from memory.security import MemorySecurityManager


@dataclass
class ScoredMemoryRecord:
    """A retrieved memory record with comprehensive relevance scoring breakdown."""
    record_id: str
    user_id: str
    memory_layer: str
    content: str
    summary: str
    final_score: float
    lexical_score: float
    recency_score: float
    importance_score: float
    confidence_score: float
    source_attribution: str
    created_at: str
    updated_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class HybridMemoryRetrievalEngine:
    """
    Hybrid Memory Retrieval Engine.
    Implements multi-dimensional scoring:
    S(d, q) = w_lex * S_lex(d, q) + w_imp * importance + w_conf * confidence + w_rec * e^(-lambda * dt)
    """

    DEFAULT_W_LEX = 0.50
    DEFAULT_W_IMP = 0.20
    DEFAULT_W_CONF = 0.15
    DEFAULT_W_REC = 0.15
    RECENCY_LAMBDA_HOURLY = 0.005  # Gentle decay over days/weeks

    STOPWORDS: Set[str] = {
        "a", "an", "the", "and", "or", "in", "on", "at", "to", "for",
        "of", "with", "by", "is", "it", "this", "that", "are", "was",
        "as", "be", "from", "which", "what", "how", "why"
    }

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        w_lex: float = DEFAULT_W_LEX,
        w_imp: float = DEFAULT_W_IMP,
        w_conf: float = DEFAULT_W_CONF,
        w_rec: float = DEFAULT_W_REC,
        decay_lambda: float = RECENCY_LAMBDA_HOURLY,
    ) -> None:
        self.db = db_manager or DatabaseManager.get_instance()
        self.w_lex = w_lex
        self.w_imp = w_imp
        self.w_conf = w_conf
        self.w_rec = w_rec
        self.decay_lambda = decay_lambda

    def _tokenize(self, text: str) -> List[str]:
        """Normalize and tokenize text into lowercase terms, discarding stopwords."""
        words = re.findall(r"\b[a-zA-Z0-9_\-\.]{2,}\b", text.lower())
        return [w for w in words if w not in self.STOPWORDS]

    def _compute_lexical_score(self, query_tokens: List[str], text: str) -> float:
        """
        Compute normalized term-frequency BM25-style lexical matching score.
        Score normalized to [0.0, 1.0].
        """
        if not query_tokens or not text:
            return 0.0

        doc_tokens = self._tokenize(text)
        if not doc_tokens:
            return 0.0

        doc_len = len(doc_tokens)
        matched = 0.0
        # Token frequency
        freqs: Dict[str, int] = {}
        for t in doc_tokens:
            freqs[t] = freqs.get(t, 0) + 1

        for qt in query_tokens:
            if qt in freqs:
                # Sub-linear term frequency scaling
                tf = freqs[qt]
                matched += math.log1p(tf)

        # Normalize relative to query length and doc length
        max_possible = len(query_tokens) * math.log1p(3)
        raw_score = matched / max(1.0, max_possible)
        return min(1.0, max(0.0, raw_score))

    def _compute_recency_score(self, updated_at_iso: str, now_dt: datetime) -> float:
        """
        Exponential recency decay: S_rec = exp(-lambda * dt_hours).
        Returns a value in (0.0, 1.0].
        """
        try:
            up_dt = datetime.fromisoformat(updated_at_iso)
            if up_dt.tzinfo is None:
                up_dt = up_dt.replace(tzinfo=timezone.utc)
            delta = now_dt - up_dt
            hours = max(0.0, delta.total_seconds() / 3600.0)
            return math.exp(-self.decay_lambda * hours)
        except Exception:
            return 0.5  # Fallback neutral score

    def retrieve(
        self,
        user_id: str,
        query: str,
        memory_layer: Optional[str] = None,
        min_confidence: float = 0.0,
        limit: int = 10,
    ) -> List[ScoredMemoryRecord]:
        """
        Execute hybrid multi-dimensional retrieval with strict tenant isolation.
        """
        query_tokens = self._tokenize(query)
        now_dt = datetime.now(timezone.utc)

        sql = """
            SELECT id, user_id, session_id, memory_layer, content, summary,
                   importance, confidence, version, created_at, updated_at, status, metadata_json
            FROM memory_records
            WHERE user_id = ? AND status = 'ACTIVE' AND confidence >= ?
        """
        params: List[Any] = [user_id, min_confidence]

        if memory_layer:
            sql += " AND memory_layer = ?"
            params.append(memory_layer.upper())

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()

        scored_records: List[ScoredMemoryRecord] = []

        for row in rows:
            # Cross-tenant permission check
            MemorySecurityManager.validate_user_access(user_id, row["user_id"])

            content = row["content"]
            summary = row["summary"] or ""
            importance = float(row["importance"])
            confidence = float(row["confidence"])
            meta = json.loads(row["metadata_json"] or "{}")
            source_attribution = meta.get("source_attribution") or meta.get("source_type") or "system"

            searchable_text = f"{content} {summary} {' '.join(meta.get('tags', []))} {meta.get('subject', '')} {meta.get('predicate', '')}"

            # Calculate score components
            lex_score = self._compute_lexical_score(query_tokens, searchable_text)
            rec_score = self._compute_recency_score(row["updated_at"], now_dt)

            # Combined weighted score
            # If query is non-empty, lexical match plays primary role; if empty, recency & importance dominate
            if query_tokens:
                final_score = (
                    self.w_lex * lex_score
                    + self.w_imp * importance
                    + self.w_conf * confidence
                    + self.w_rec * rec_score
                )
            else:
                # Deterministic fallback ranking when no search query tokens
                final_score = 0.5 * rec_score + 0.3 * importance + 0.2 * confidence

            scored_records.append(
                ScoredMemoryRecord(
                    record_id=row["id"],
                    user_id=row["user_id"],
                    memory_layer=row["memory_layer"],
                    content=content,
                    summary=summary,
                    final_score=round(final_score, 4),
                    lexical_score=round(lex_score, 4),
                    recency_score=round(rec_score, 4),
                    importance_score=round(importance, 4),
                    confidence_score=round(confidence, 4),
                    source_attribution=source_attribution,
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    metadata=meta,
                )
            )

        # Sort descending by final_score
        scored_records.sort(key=lambda r: r.final_score, reverse=True)
        return scored_records[:limit]
