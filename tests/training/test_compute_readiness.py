"""
404 FOUNDERS — Unit Tests for Compute Readiness Gate
"""

from training.configs.model_config import (
    EXPERIMENTAL_LOCAL_CPU_CONFIG,
    EXPERIMENTAL_TINY_CONFIG,
    PRODUCTION_CLUSTER_SPEC,
    PretrainingConfig,
)
from training.engine.compute_readiness import ComputeReadinessGate


def test_memory_footprint_calculation() -> None:
    """Verify analytical memory breakdown equations across parameter scales."""
    gate = ComputeReadinessGate()

    # 1. Experimental Tiny Profile (<10 MB)
    mem_tiny = gate.calculate_memory_footprint(EXPERIMENTAL_TINY_CONFIG, PretrainingConfig(batch_size=2))
    assert mem_tiny.model_weights_mb < 5.0
    assert mem_tiny.total_training_memory_gb < 0.1

    # 2. Production Foundation Spec (Billion parameters)
    mem_prod = gate.calculate_memory_footprint(PRODUCTION_CLUSTER_SPEC, PretrainingConfig(batch_size=8))
    assert mem_prod.total_training_memory_gb > 10.0


def test_compute_readiness_verdict() -> None:
    """Verify local pilot is approved and cluster specification is blocked locally."""
    gate = ComputeReadinessGate()

    # Local pilot should be approved
    report_local = gate.evaluate_readiness(EXPERIMENTAL_TINY_CONFIG, PretrainingConfig(batch_size=2))
    assert report_local.verdict == "APPROVED_LOCAL_PILOT"
    assert report_local.is_safe_to_execute is True

    # Cluster production spec must be blocked from running on local workstation
    report_cluster = gate.evaluate_readiness(PRODUCTION_CLUSTER_SPEC, PretrainingConfig(batch_size=8))
    assert report_cluster.is_safe_to_execute is False
    assert report_cluster.verdict in ("BLOCKED_INSUFFICIENT_MEMORY", "REQUIRES_GPU_CLUSTER")
    assert report_cluster.blocker_reason is not None
