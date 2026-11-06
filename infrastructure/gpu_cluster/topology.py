"""
404 FOUNDERS — Cluster Network Topology
Models rail-optimized spine-leaf InfiniBand NDR fabrics and intra-node NVSwitch layouts.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List


@dataclass
class RailMapping:
    """Mapping of GPU ordinal on node to InfiniBand HCA and Rail Switch."""

    gpu_index: int
    hca_device: str
    rail_switch_id: int
    numa_node: int
    pcie_bus: str


class RailOptimizedFabric:
    """Constructs and validates rail-optimized networking layouts for multi-node GPU training."""

    @classmethod
    def generate_node_rail_mapping(cls, gpus_per_node: int = 8) -> List[RailMapping]:
        """Generate canonical 8-way rail mapping for NVIDIA HGX H100 systems.

        Each GPU is paired with a dedicated InfiniBand NDR 400G NIC on the same NUMA node,
        directly connecting to an independent rail switch to eliminate inter-rail cross-talk.
        """
        mappings: List[RailMapping] = []
        for i in range(gpus_per_node):
            numa = 0 if i < 4 else 1
            mapping = RailMapping(
                gpu_index=i,
                hca_device=f"mlx5_{i}",
                rail_switch_id=i,
                numa_node=numa,
                pcie_bus=f"0000:{'1' if numa == 0 else '8'}{i:02x}:00.0",
            )
            mappings.append(mapping)
        return mappings

    @classmethod
    def get_cluster_topology_summary(cls, node_count: int, gpus_per_node: int = 8) -> Dict[str, Any]:
        """Generate network topology overview for a multi-node cluster."""
        total_gpus = node_count * gpus_per_node
        return {
            "node_count": node_count,
            "gpus_per_node": gpus_per_node,
            "total_gpus": total_gpus,
            "num_rail_switches": gpus_per_node,
            "intra_node_fabric": "NVIDIA NVSwitch Full Mesh (NVLink 4, 900 GB/s per GPU)",
            "inter_node_fabric": f"{gpus_per_node}x Non-blocking InfiniBand NDR 400Gbps Rails (3.2 Tbps per node)",
            "spine_switches": max(2, node_count // 4),
            "total_hca_count": total_gpus,
            "bisectional_bandwidth_tb_s": round((total_gpus * 50.0) / 1000.0, 2),  # 50 GB/s per 400G port
        }
