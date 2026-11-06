"""
404 FOUNDERS — GPU Cluster Configuration
Formal specifications for Tier A (Dev), Tier B (Research), and Tier C (Foundation Pretraining)
GPU computing cluster infrastructure.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class InterconnectSpec:
    """Interconnect technology and bandwidth parameters."""

    technology: str  # NVLink, NVSwitch, PCIe, InfiniBand NDR, RoCE v2
    raw_bandwidth_gb_per_sec: float
    effective_bandwidth_gb_per_sec: float
    latency_microseconds: float
    topology_type: str  # Mesh, Ring, Tree, Rail-Optimized Spine-Leaf

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StorageTierSpec:
    """Storage tier capacities and performance metrics."""

    hot_local_nvme_tb: float
    hot_nvme_read_gb_per_sec: float
    warm_shared_parallel_tb: float
    warm_filesystem_type: str  # Lustre, GPFS, WEKA, High-Speed NFS
    cold_object_storage_tb: float
    backup_retention_days: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ClusterTierDefinition:
    """Complete specification of a GPU cluster infrastructure tier."""

    tier_name: str
    target_workload: str
    node_count: int
    gpus_per_node: int
    total_gpus: int
    gpu_model: str
    vram_per_gpu_gb: int
    total_vram_gb: int
    cpu_model: str
    cpu_cores_per_node: int
    system_ram_per_node_gb: int
    total_system_ram_gb: int
    interconnect: InterconnectSpec
    storage: StorageTierSpec
    cluster_network: str
    power_draw_kw: float
    cooling_requirement: str  # Air-cooled, Direct-to-Chip Liquid, Immersion
    orchestrator: str  # Docker, Docker Compose, Slurm + Pyxis/Enroot, Kubernetes
    estimated_hourly_cost_usd: float
    estimated_monthly_cost_usd: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Tier A: Development Infrastructure Specification
TIER_A_DEV = ClusterTierDefinition(
    tier_name="Tier A — Development Infrastructure",
    target_workload="Tokenizer training, dataset preprocessing, unit tests, micro-model prototypes (<=1.5B)",
    node_count=1,
    gpus_per_node=2,
    total_gpus=2,
    gpu_model="NVIDIA GeForce RTX 4090 or L40S",
    vram_per_gpu_gb=24,
    total_vram_gb=48,
    cpu_model="AMD Ryzen 9 7950X or Intel Core i9-14900K (16C/32T)",
    cpu_cores_per_node=16,
    system_ram_per_node_gb=128,
    total_system_ram_gb=128,
    interconnect=InterconnectSpec(
        technology="PCIe Gen 4.0 x16",
        raw_bandwidth_gb_per_sec=31.5,
        effective_bandwidth_gb_per_sec=25.0,
        latency_microseconds=1.5,
        topology_type="Dual-Slot PCIe",
    ),
    storage=StorageTierSpec(
        hot_local_nvme_tb=4.0,
        hot_nvme_read_gb_per_sec=7.0,
        warm_shared_parallel_tb=10.0,
        warm_filesystem_type="High-Speed NFS over 10GbE",
        cold_object_storage_tb=20.0,
        backup_retention_days=30,
    ),
    cluster_network="10 Gbps Ethernet",
    power_draw_kw=1.2,
    cooling_requirement="Air-Cooled (Standard Workstation / Server Room)",
    orchestrator="Docker & Docker Compose",
    estimated_hourly_cost_usd=1.00,
    estimated_monthly_cost_usd=730.00,
)

# Tier B: Research Infrastructure Specification
TIER_B_RESEARCH = ClusterTierDefinition(
    tier_name="Tier B — Research Infrastructure",
    target_workload="Multi-GPU distributed training prototypes, FSDP/Megatron experiments, multimodal research (1.5B to 14B)",
    node_count=1,
    gpus_per_node=8,
    total_gpus=8,
    gpu_model="NVIDIA H100 80GB SXM5",
    vram_per_gpu_gb=80,
    total_vram_gb=640,
    cpu_model="Dual AMD EPYC 9654 (192 Cores Total)",
    cpu_cores_per_node=192,
    system_ram_per_node_gb=1024,
    total_system_ram_gb=1024,
    interconnect=InterconnectSpec(
        technology="NVIDIA NVLink 4 / NVSwitch",
        raw_bandwidth_gb_per_sec=900.0,
        effective_bandwidth_gb_per_sec=800.0,
        latency_microseconds=0.5,
        topology_type="Full Crossbar NVSwitch Mesh",
    ),
    storage=StorageTierSpec(
        hot_local_nvme_tb=15.36,
        hot_nvme_read_gb_per_sec=28.0,
        warm_shared_parallel_tb=50.0,
        warm_filesystem_type="Parallel NVMe-oF / Lustre",
        cold_object_storage_tb=100.0,
        backup_retention_days=90,
    ),
    cluster_network="Dual 100 Gbps RoCE v2 / InfiniBand",
    power_draw_kw=10.2,
    cooling_requirement="Data Center Air-Cooled / Rear-Door Heat Exchanger",
    orchestrator="Docker with NVIDIA Container Toolkit / Slurm single-node",
    estimated_hourly_cost_usd=24.00,
    estimated_monthly_cost_usd=17520.00,
)

# Tier C: Large-Scale Foundation Model Training Supercluster Specification
TIER_C_FOUNDATION = ClusterTierDefinition(
    tier_name="Tier C — Foundation Training Supercluster",
    target_workload="From-scratch foundation model pretraining, large-scale multimodal pretraining, multi-node 4D parallelism (>14B to 70B+)",
    node_count=8,
    gpus_per_node=8,
    total_gpus=64,
    gpu_model="NVIDIA H100 / H200 SXM5",
    vram_per_gpu_gb=80,
    total_vram_gb=5120,
    cpu_model="Dual AMD EPYC 9654 per node (1,536 Cores Across Cluster)",
    cpu_cores_per_node=192,
    system_ram_per_node_gb=1024,
    total_system_ram_gb=8192,
    interconnect=InterconnectSpec(
        technology="NVLink 4 Intra-Node (900 GB/s) + 8x InfiniBand NDR 400Gbps Inter-Node (3.2 Tbps/node)",
        raw_bandwidth_gb_per_sec=400.0,  # 8 x 50 GB/s inter-node
        effective_bandwidth_gb_per_sec=360.0,
        latency_microseconds=1.2,
        topology_type="Non-Blocking Rail-Optimized Spine-Leaf InfiniBand NDR Fabric",
    ),
    storage=StorageTierSpec(
        hot_local_nvme_tb=122.88,  # 8 nodes x 15.36TB
        hot_nvme_read_gb_per_sec=224.0,  # 8 nodes x 28 GB/s
        warm_shared_parallel_tb=500.0,
        warm_filesystem_type="Distributed Lustre / WEKA Parallel File System",
        cold_object_storage_tb=2000.0,  # 2 PB
        backup_retention_days=365,
    ),
    cluster_network="8x InfiniBand NDR 400Gbps per node + 100GbE Out-of-Band Management Network",
    power_draw_kw=85.0,
    cooling_requirement="Direct-to-Chip Liquid Cooling (DLC) with Dry Cooler Loop",
    orchestrator="Slurm Workload Manager + Pyxis/Enroot Container Runtime + PMIx",
    estimated_hourly_cost_usd=192.00,
    estimated_monthly_cost_usd=140160.00,
)


class ClusterCatalog:
    """Catalog holding all three approved infrastructure tiers."""

    @classmethod
    def get_tier(cls, tier_code: str) -> ClusterTierDefinition:
        code = tier_code.upper()
        if code in ("A", "TIER_A", "DEV"):
            return TIER_A_DEV
        if code in ("B", "TIER_B", "RESEARCH"):
            return TIER_B_RESEARCH
        if code in ("C", "TIER_C", "TRAINING", "FOUNDATION"):
            return TIER_C_FOUNDATION
        raise KeyError(f"Unknown cluster tier '{tier_code}'. Choose 'A', 'B', or 'C'.")

    @classmethod
    def all_tiers(cls) -> List[ClusterTierDefinition]:
        return [TIER_A_DEV, TIER_B_RESEARCH, TIER_C_FOUNDATION]
