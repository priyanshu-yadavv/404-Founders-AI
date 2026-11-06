"""
404 FOUNDERS — General Knowledge Processing Engine Unit Tests
"""

import pytest
from core.intelligence.knowledge_engine import GeneralKnowledgeEngine


@pytest.fixture
def engine() -> GeneralKnowledgeEngine:
    return GeneralKnowledgeEngine()


def test_entity_extraction_and_disambiguation(engine: GeneralKnowledgeEngine) -> None:
    text = "We configured PyTorch and JAX on Linux to train with custom BPE tokenization."
    entities = engine.extract_entities(text)
    assert len(entities) >= 4
    entity_names = {e.text for e in entities}
    assert "pytorch" in entity_names
    assert "linux" in entity_names
    assert "bpe" in entity_names


def test_domain_classification(engine: GeneralKnowledgeEngine) -> None:
    cs_query = "Analyze the time complexity and AST node traversal for recursive search algorithms."
    res_cs = engine.classify_domain(cs_query)
    assert res_cs.primary_domain in ["Computer Science", "Software Engineering"]

    sec_query = "Assess CVSS scores and firewall rules against SQL injection vulnerabilities."
    res_sec = engine.classify_domain(sec_query)
    assert res_sec.primary_domain == "Cybersecurity"


def test_epistemic_boundaries_enforced(engine: GeneralKnowledgeEngine) -> None:
    speculative_query = "Predict the future stock price of NVDA on December 31 2030"
    boundaries = engine.check_epistemic_boundaries(speculative_query)
    assert len(boundaries) > 0
    assert any("Speculative future" in b for b in boundaries)

    res = engine.process(speculative_query)
    assert res.is_within_epistemic_bounds is False
    assert len(res.epistemic_boundaries_detected) > 0
