"""
404 FOUNDERS — Interconnect Performance Modeling
Models communication overhead, latency, and all-reduce execution times across
PCIe Gen 4, NVLink 4/5, and InfiniBand NDR fabrics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass
class CommunicationMetrics:
    """Estimated communication statistics for an AllReduce or AllGather collective."""

    data_size_mb: float
    bus_bandwidth_gb_s: float
    effective_bandwidth_gb_s: float
    latency_microseconds: float
    allreduce_time_ms: float
    communication_efficiency: float


class InterconnectModel:
    """Models collective communication times using standard distributed Ring/Tree AllReduce equations."""

    # Reference effective bus bandwidths in GB/s
    BANDWIDTH_TABLE = {
        "pcie_gen4": 25.0,
        "pcie_gen5": 50.0,
        "nvlink3_a100": 500.0,
        "nvlink4_h100": 800.0,
        "infiniband_hdr_200g": 22.0,
        "infiniband_ndr_400g": 45.0,
        "infiniband_ndr_3200g_rail": 360.0,  # 8x 400G rail-optimized per node
    }

    # Reference base latencies in microseconds
    LATENCY_TABLE = {
        "pcie_gen4": 1.5,
        "pcie_gen5": 1.2,
        "nvlink3_a100": 0.8,
        "nvlink4_h100": 0.5,
        "infiniband_hdr_200g": 1.8,
        "infiniband_ndr_400g": 1.2,
        "infiniband_ndr_3200g_rail": 1.2,
    }

    @classmethod
    def calculate_allreduce_time(
        cls,
        data_size_bytes: int,
        gpu_count: int,
        interconnect_key: str = "nvlink4_h100",
    ) -> CommunicationMetrics:
        """Compute estimated Ring AllReduce collective communication time.

        Formula:
            Time = 2 * ((N - 1) / N) * (Size / Bandwidth) + Latency

        Args:
            data_size_bytes: Volume of gradient/tensor data to synchronize.
            gpu_count: Number of participating GPUs.
            interconnect_key: Interconnect identifier key from BANDWIDTH_TABLE.

        Returns:
            CommunicationMetrics instance.
        """
        eff_bw_gb_s = cls.BANDWIDTH_TABLE.get(interconnect_key, 25.0)
        latency_us = cls.LATENCY_TABLE.get(interconnect_key, 1.5)

        data_size_mb = data_size_bytes / (1024 * 1024)
        data_size_gb = data_size_bytes / (1024**3)

        if gpu_count <= 1:
            return CommunicationMetrics(
                data_size_mb=round(data_size_mb, 2),
                bus_bandwidth_gb_s=eff_bw_gb_s,
                effective_bandwidth_gb_s=eff_bw_gb_s,
                latency_microseconds=0.0,
                allreduce_time_ms=0.0,
                communication_efficiency=1.0,
            )

        # Standard Ring AllReduce multiplier: 2 * (N - 1) / N
        ring_factor = 2.0 * (gpu_count - 1) / gpu_count
        transferred_gb = data_size_gb * ring_factor

        transfer_seconds = transferred_gb / eff_bw_gb_s
        latency_seconds = (latency_us * 1e-6) * (2 * (gpu_count - 1))

        total_ms = (transfer_seconds + latency_seconds) * 1000.0

        # Efficiency compared to theoretical peak
        raw_peak = eff_bw_gb_s * 1.15
        efficiency = min(1.0, eff_bw_gb_s / raw_peak)

        return CommunicationMetrics(
            data_size_mb=round(data_size_mb, 2),
            bus_bandwidth_gb_s=round(eff_bw_gb_s, 1),
            effective_bandwidth_gb_s=round(eff_bw_gb_s, 1),
            latency_microseconds=round(latency_us, 2),
            allreduce_time_ms=round(total_ms, 3),
            communication_efficiency=round(efficiency, 3),
        )
