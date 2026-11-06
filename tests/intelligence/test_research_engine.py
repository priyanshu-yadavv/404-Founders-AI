"""
404 FOUNDERS — Research and Knowledge Analysis Engine Unit Tests
"""

import pytest
from core.intelligence.research_engine import ResearchAnalysisEngine, ResearchSource


@pytest.fixture
def engine() -> ResearchAnalysisEngine:
    return ResearchAnalysisEngine()


def test_extract_claims(engine: ResearchAnalysisEngine) -> None:
    src = ResearchSource(
        source_id="S1",
        title="Distributed Model Parallelism Study",
        content="Pipeline parallelism decreases memory pressure across GPUs. Tensor slicing requires high interconnect bandwidth.",
    )
    claims = engine.extract_claims(src)
    assert len(claims) == 2
    assert claims[0].source_id == "S1"


def test_cross_source_contradiction(engine: ResearchAnalysisEngine) -> None:
    s1 = ResearchSource(
        source_id="DOC_A",
        title="Optimization Report Alpha",
        content="Quantization increases inference throughput across edge devices significantly.",
    )
    s2 = ResearchSource(
        source_id="DOC_B",
        title="Optimization Report Beta",
        content="Quantization decreases inference throughput across edge devices due to decompression overhead.",
    )
    res = engine.synthesize("Impact of quantization on edge throughput", [s1, s2])
    assert len(res.contradictions) >= 1
    assert res.contradictions[0].source_a_id == "DOC_A"
    assert res.contradictions[0].source_b_id == "DOC_B"


def test_corroboration_and_attribution(engine: ResearchAnalysisEngine) -> None:
    s1 = ResearchSource(
        source_id="S1",
        title="Flash Attention Study",
        content="Tiling memory blocks reduces memory access latency in attention kernels.",
    )
    s2 = ResearchSource(
        source_id="S2",
        title="Memory Hierarchy Benchmark",
        content="Tiling memory buffers improves cache locality and reduces IO bottleneck.",
    )
    res = engine.synthesize("Memory access optimization", [s1, s2])
    assert res.overall_confidence > 0.60
    assert len(res.corroborated_findings) > 0


def test_no_hallucinated_sources(engine: ResearchAnalysisEngine) -> None:
    res = engine.synthesize("Verify quantum teleportation of macroscopic objects", sources=[])
    assert res.sources_analyzed == 0
    assert len(res.extracted_claims) == 0
    assert res.overall_confidence == 0.0
    assert "No sources provided" in res.unverified_hypotheses[0]
