"""
404 FOUNDERS — General Knowledge Processing Engine
Provides entity extraction and disambiguation, domain classification,
factual boundary verification, and epistemic limits enforcement.
"""

from dataclasses import dataclass, field
import re
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ExtractedEntity:
    """An extracted named entity with categorization and disambiguation details."""
    text: str
    category: str  # "TECHNOLOGY", "ORGANIZATION", "PERSON", "CONCEPT", "LOCATION"
    disambiguation_hint: str
    confidence: float


@dataclass
class DomainClassification:
    """Classified knowledge domain with associated confidence."""
    primary_domain: str
    secondary_domains: List[str]
    confidence: float
    domain_tags: List[str]


@dataclass
class KnowledgeProcessingResult:
    """Structured report from general knowledge processing and boundary checks."""
    query: str
    domain: DomainClassification
    entities: List[ExtractedEntity]
    verified_contextual_facts: List[str]
    epistemic_boundaries_detected: List[str]
    is_within_epistemic_bounds: bool
    summary: str


class GeneralKnowledgeEngine:
    """
    General knowledge processing engine.
    Extracts entities, disambiguates polysemous terms, classifies academic/engineering domains,
    and delineates strict epistemic boundaries regarding ungrounded or speculative topics.
    """

    KNOWN_ENTITIES = {
        "python": ("TECHNOLOGY", "Interpreted high-level programming language (not the reptile)"),
        "rust": ("TECHNOLOGY", "Systems programming language focusing on safety and concurrency (not iron oxide)"),
        "linux": ("TECHNOLOGY", "Open-source Unix-like operating system kernel"),
        "pytorch": ("TECHNOLOGY", "Open-source machine learning and deep learning tensor library"),
        "jax": ("TECHNOLOGY", "Composable transformations and automatic differentiation library for Python"),
        "fastapi": ("TECHNOLOGY", "Modern, high-performance web framework for building APIs with Python"),
        "cvss": ("CONCEPT", "Common Vulnerability Scoring System standard for IT vulnerability assessment"),
        "bpe": ("CONCEPT", "Byte Pair Encoding data compression and tokenization algorithm"),
    }

    DOMAIN_KEYWORDS = {
        "Computer Science": ["algorithm", "complexity", "ast", "compiler", "data structure", "memory", "turing"],
        "Cybersecurity": ["vulnerability", "exploit", "cvss", "firewall", "encryption", "entropy", "threat", "waf"],
        "Mathematics": ["equation", "derivative", "integral", "matrix", "determinant", "probability", "statistics", "calculus"],
        "Physics": ["kinematics", "velocity", "acceleration", "thermodynamics", "joule", "watt", "ohm", "gravity"],
        "Software Engineering": ["refactoring", "unit test", "api", "architecture", "rest", "ci/cd", "git"],
    }

    SPECULATIVE_OR_CONFIDENTIAL_MARKERS = [
        (re.compile(r"\b(who will win the next|future stock price of|predict future)\b", re.IGNORECASE), "Speculative future event: Cannot be factually determined."),
        (re.compile(r"\b(password|secret key|private token|classified information)\b", re.IGNORECASE), "Confidential credential boundary: Access denied under privacy/security policy."),
    ]

    def extract_entities(self, text: str) -> List[ExtractedEntity]:
        """Extract and disambiguate known technological and conceptual entities."""
        entities: List[ExtractedEntity] = []
        lower = text.lower()

        for term, (cat, hint) in self.KNOWN_ENTITIES.items():
            if re.search(rf"\b{term}\b", lower):
                entities.append(ExtractedEntity(
                    text=term,
                    category=cat,
                    disambiguation_hint=hint,
                    confidence=0.95,
                ))

        # Capitalized proper noun heuristics
        proper_nouns = re.findall(r"\b[A-Z][a-zA-Z0-9_\-]{3,}\b", text)
        for pn in proper_nouns[:5]:
            if pn.lower() not in self.KNOWN_ENTITIES:
                entities.append(ExtractedEntity(
                    text=pn,
                    category="CONCEPT",
                    disambiguation_hint="Proper noun detected in query context.",
                    confidence=0.60,
                ))

        return entities

    def classify_domain(self, text: str) -> DomainClassification:
        """Categorize input text into one or more academic/engineering domains."""
        lower = text.lower()
        domain_scores: Dict[str, int] = {}

        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            count = sum(1 for kw in keywords if kw in lower)
            if count > 0:
                domain_scores[domain] = count

        if not domain_scores:
            return DomainClassification(
                primary_domain="General Knowledge",
                secondary_domains=[],
                confidence=0.5,
                domain_tags=["general"],
            )

        sorted_domains = sorted(domain_scores.items(), key=lambda x: x[1], reverse=True)
        primary = sorted_domains[0][0]
        secondary = [d[0] for d in sorted_domains[1:3]]
        conf = min(0.99, 0.5 + 0.15 * sorted_domains[0][1])

        return DomainClassification(
            primary_domain=primary,
            secondary_domains=secondary,
            confidence=round(conf, 2),
            domain_tags=[primary.lower().replace(" ", "_")] + [s.lower().replace(" ", "_") for s in secondary],
        )

    def check_epistemic_boundaries(self, text: str) -> List[str]:
        """Detect out-of-bounds questions (speculative future, confidential secrets)."""
        boundaries: List[str] = []
        for pat, reason in self.SPECULATIVE_OR_CONFIDENTIAL_MARKERS:
            if pat.search(text):
                boundaries.append(reason)
        return boundaries

    def process(self, query: str, context_facts: Optional[List[str]] = None) -> KnowledgeProcessingResult:
        """Process general knowledge query, extract entities, classify domain, and enforce boundaries."""
        if not query.strip():
            raise ValueError("Query string cannot be empty.")

        domain = self.classify_domain(query)
        entities = self.extract_entities(query)
        boundaries = self.check_epistemic_boundaries(query)

        is_within_bounds = len(boundaries) == 0
        verified_facts = context_facts or []

        summary = (
            f"Categorized into domain '{domain.primary_domain}' (confidence: {domain.confidence}). "
            f"Extracted {len(entities)} named entities. "
            f"Epistemic boundaries: {'Clear' if is_within_bounds else f'{len(boundaries)} violation(s)'}."
        )

        return KnowledgeProcessingResult(
            query=query,
            domain=domain,
            entities=entities,
            verified_contextual_facts=verified_facts,
            epistemic_boundaries_detected=boundaries,
            is_within_epistemic_bounds=is_within_bounds,
            summary=summary,
        )
