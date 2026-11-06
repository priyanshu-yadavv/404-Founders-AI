"""
404 FOUNDERS — Research and Knowledge Analysis Engine
Provides multi-source document synthesis, cross-document contradiction detection,
strict source attribution, and factual confidence scoring without citation fabrication.
"""

from dataclasses import dataclass, field
import re
from typing import Any, Dict, List, Optional, Set


@dataclass
class ResearchSource:
    """Represents an input document or citation source."""
    source_id: str
    title: str
    author: Optional[str] = None
    year: Optional[int] = None
    content: str = ""
    is_peer_reviewed: bool = False


@dataclass
class SourceClaim:
    """A claim extracted from a specific document source."""
    claim_id: str
    source_id: str
    text: str
    confidence: float
    keywords: List[str] = field(default_factory=list)


@dataclass
class CrossSourceContradiction:
    """A detected contradiction between two distinct sources."""
    source_a_id: str
    source_b_id: str
    claim_a: str
    claim_b: str
    discrepancy_explanation: str


@dataclass
class ResearchSynthesisResult:
    """Structured report synthesizing research across multiple document sources."""
    query: str
    sources_analyzed: int
    extracted_claims: List[SourceClaim]
    corroborated_findings: List[str]
    contradictions: List[CrossSourceContradiction]
    unverified_hypotheses: List[str]
    overall_confidence: float
    summary: str


class ResearchAnalysisEngine:
    """
    Research and knowledge analysis engine.
    Cross-references claims across documents, identifies conflicting assertions,
    tracks citations deterministically, and never invents sources or citations.
    """

    OPPOSING_POLARITIES = [
        (r"\b(increases|increases?|accelerates|promotes)\b", r"\b(decreases|reduces?|decelerates|inhibits)\b"),
        (r"\b(positive|effective|beneficial|safe)\b", r"\b(negative|ineffective|harmful|unsafe)\b"),
        (r"\b(confirmed|proven|verified)\b", r"\b(refuted|disproven|unfounded)\b"),
    ]

    def extract_claims(self, source: ResearchSource) -> List[SourceClaim]:
        """Extract discrete factual sentences from a research source."""
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", source.content) if len(s.strip()) > 15]
        claims: List[SourceClaim] = []

        for idx, sentence in enumerate(sentences):
            words = [w.lower() for w in re.findall(r"\b[a-z]{4,}\b", sentence)]
            claims.append(SourceClaim(
                claim_id=f"{source.source_id}_C{idx+1}",
                source_id=source.source_id,
                text=sentence,
                confidence=0.9 if source.is_peer_reviewed else 0.7,
                keywords=words,
            ))
        return claims

    def detect_cross_contradictions(self, claims: List[SourceClaim]) -> List[CrossSourceContradiction]:
        """Compare claims across different sources to locate conflicting statements."""
        contradictions: List[CrossSourceContradiction] = []
        n = len(claims)

        for i in range(n):
            for j in range(i + 1, n):
                c1 = claims[i]
                c2 = claims[j]
                if c1.source_id == c2.source_id:
                    continue  # Only cross-source checks

                overlap = set(c1.keywords).intersection(set(c2.keywords))
                if len(overlap) >= 2:
                    # Check for opposing polarities
                    t1 = c1.text.lower()
                    t2 = c2.text.lower()
                    for pos_pat, neg_pat in self.OPPOSING_POLARITIES:
                        has_pos_1 = bool(re.search(pos_pat, t1))
                        has_neg_1 = bool(re.search(neg_pat, t1))
                        has_pos_2 = bool(re.search(pos_pat, t2))
                        has_neg_2 = bool(re.search(neg_pat, t2))

                        if (has_pos_1 and has_neg_2) or (has_neg_1 and has_pos_2):
                            contradictions.append(CrossSourceContradiction(
                                source_a_id=c1.source_id,
                                source_b_id=c2.source_id,
                                claim_a=c1.text,
                                claim_b=c2.text,
                                discrepancy_explanation=f"Contradictory polarity regarding concepts {list(overlap)[:3]}.",
                            ))
                            break

        return contradictions

    def synthesize(
        self,
        query: str,
        sources: List[ResearchSource],
    ) -> ResearchSynthesisResult:
        """Synthesize multiple research documents to answer a query with strict attribution."""
        if not sources:
            return ResearchSynthesisResult(
                query=query,
                sources_analyzed=0,
                extracted_claims=[],
                corroborated_findings=[],
                contradictions=[],
                unverified_hypotheses=["No sources provided. Strictly cannot fabricate citations or conclusions."],
                overall_confidence=0.0,
                summary="Zero sources provided for research synthesis.",
            )

        all_claims: List[SourceClaim] = []
        for s in sources:
            all_claims.extend(self.extract_claims(s))

        contradictions = self.detect_cross_contradictions(all_claims)

        # Corroboration: topics mentioned by >1 source
        source_by_keyword: Dict[str, Set[str]] = {}
        for c in all_claims:
            for kw in c.keywords:
                if kw not in source_by_keyword:
                    source_by_keyword[kw] = set()
                source_by_keyword[kw].add(c.source_id)

        corroborated: List[str] = []
        for kw, src_ids in source_by_keyword.items():
            if len(src_ids) >= 2:
                corroborated.append(f"Concept '{kw}' independently corroborated across sources: {sorted(list(src_ids))}")

        # Confidence calculation
        base_conf = 0.85
        if contradictions:
            base_conf -= 0.25 * min(1.0, len(contradictions) / 2.0)
        if not corroborated:
            base_conf -= 0.15

        conf = round(max(0.1, min(0.99, base_conf)), 2)

        summary = (
            f"Synthesized {len(sources)} source(s) yielding {len(all_claims)} discrete claims. "
            f"Identified {len(corroborated)} corroborated conceptual themes and "
            f"{len(contradictions)} cross-source contradiction(s). Overall confidence = {conf}."
        )

        return ResearchSynthesisResult(
            query=query,
            sources_analyzed=len(sources),
            extracted_claims=all_claims,
            corroborated_findings=corroborated[:5],
            contradictions=contradictions,
            unverified_hypotheses=[] if sources else ["Requires external experimental verification."],
            overall_confidence=conf,
            summary=summary,
        )
