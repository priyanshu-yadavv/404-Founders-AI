"""
404 FOUNDERS — Cluster Architecture & Interconnect Topology Tests
Validates Tier A/B/C definitions, interconnect latency/bandwidth models,
rail-optimized fabric mappings, and hybrid workload routing.
"""

from __future__ import annotations

import pytest

from infrastructure.cloud import CloudProfileRegistry, HybridWorkloadRouter
from infrastructure.gpu_cluster import (
    TIER_A_DEV,
    TIER_B_RESEARCH,
    TIER_C_FOUNDATION,
    ClusterCatalog,
    InterconnectModel,
    RailOptimizedFabric,
)


def test_cluster_tier_specifications() -> None:
    """Verify cluster tier specs match architectural requirements."""
    # Tier A
    assert TIER_A_DEV.node_count == 1
    assert TIER_A_DEV.total_gpus == 2
    assert TIER_A_DEV.vram_per_gpu_gb == 24
    assert TIER_A_DEV.interconnect.technology == "PCIe Gen 4.0 x16"

    # Tier B
    assert TIER_B_RESEARCH.node_count == 1
    assert TIER_B_RESEARCH.total_gpus == 8
    assert TIER_B_RESEARCH.vram_per_gpu_gb == 80
    assert TIER_B_RESEARCH.total_vram_gb == 640
    assert "NVLink 4" in TIER_B_RESEARCH.interconnect.technology

    # Tier C
    assert TIER_C_FOUNDATION.node_count == 8
    assert TIER_C_FOUNDATION.gpus_per_node == 8
    assert TIER_C_FOUNDATION.total_gpus == 64
    assert TIER_C_FOUNDATION.total_vram_gb == 5120
    assert "InfiniBand NDR" in TIER_C_FOUNDATION.interconnect.technology


def test_cluster_catalog_retrieval() -> None:
    """Verify catalog retrieves tiers correctly and handles invalid codes."""
    tier_a = ClusterCatalog.get_tier("A")
    tier_b = ClusterCatalog.get_tier("B")
    tier_c = ClusterCatalog.get_tier("C")

    assert tier_a.tier_name == TIER_A_DEV.tier_name
    assert tier_b.tier_name == TIER_B_RESEARCH.tier_name
    assert tier_c.tier_name == TIER_C_FOUNDATION.tier_name

    with pytest.raises(KeyError):
        ClusterCatalog.get_tier("INVALID_TIER")


def test_interconnect_ring_allreduce_simulation() -> None:
    """Verify interconnect model accurately computes AllReduce transfer durations."""
    tensor_bytes = 1 * 1024**3  # 1 GB

    nvlink_metrics = InterconnectModel.calculate_allreduce_time(
        data_size_bytes=tensor_bytes,
        gpu_count=8,
        interconnect_key="nvlink4_h100",
    )

    pcie_metrics = InterconnectModel.calculate_allreduce_time(
        data_size_bytes=tensor_bytes,
        gpu_count=8,
        interconnect_key="pcie_gen4",
    )

    # NVLink must be substantially faster than PCIe
    assert nvlink_metrics.allreduce_time_ms < pcie_metrics.allreduce_time_ms
    assert nvlink_metrics.allreduce_time_ms > 0
    assert pcie_metrics.allreduce_time_ms > 0


def test_rail_optimized_fabric_mapping() -> None:
    """Verify 8-way rail-optimized fabric maps GPU ranks to correct rails."""
    mappings = RailOptimizedFabric.generate_node_rail_mapping(gpus_per_node=8)
    assert len(mappings) == 8

    for idx, m in enumerate(mappings):
        assert m.gpu_index == idx
        assert m.rail_switch_id == idx
        assert m.hca_device == f"mlx5_{idx}"

    summary = RailOptimizedFabric.get_cluster_topology_summary(node_count=8, gpus_per_node=8)
    assert summary["total_gpus"] == 64
    assert summary["num_rail_switches"] == 8
    assert summary["total_hca_count"] == 64
    assert summary["bisectional_bandwidth_tb_s"] > 0


def test_hybrid_workload_routing_decisions() -> None:
    """Verify workload router directs jobs to appropriate environments."""
    router = HybridWorkloadRouter()

    # Small unit test (<50M params) -> local CPU workstation
    decision_local = router.route_training_job(
        parameter_count=10_000_000,
        dataset_tokens_count=1_000_000,
        batch_size=1,
    )
    assert decision_local.target == "local_workstation_cpu"

    # Medium model (500M parameters) -> Tier A dev node
    decision_a = router.route_training_job(
        parameter_count=500_000_000,
        dataset_tokens_count=10_000_000,
        batch_size=2,
    )
    assert decision_a.target == "cloud_tier_a_dev_node"

    # Multi-GPU Research model (7B parameters) -> Tier B research node
    decision_b = router.route_training_job(
        parameter_count=7_000_000_000,
        dataset_tokens_count=50_000_000,
        batch_size=4,
    )
    assert decision_b.target == "cloud_tier_b_research_node"

    # Large Pretraining model (16B parameters) -> Tier C supercluster
    decision_c = router.route_training_job(
        parameter_count=16_000_000_000,
        dataset_tokens_count=500_000_000_000,
        batch_size=8,
    )
    assert decision_c.target == "cloud_tier_c_gpu_supercluster"
