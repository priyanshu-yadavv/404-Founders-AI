"""
404 FOUNDERS — Cloud Provider Specifications
Defines cloud instance profiles and dated market cost estimates across major GPU cloud providers.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional


@dataclass
class CloudInstanceProfile:
    """Specification of a cloud GPU compute instance."""

    provider: str
    instance_type: str
    gpu_model: str
    gpu_count: int
    total_vram_gb: int
    system_ram_gb: int
    vcpus: int
    interconnect: str
    hourly_rate_usd: float
    pricing_model: str  # on-demand, spot, reserved
    pricing_date: str = "2026-Q4"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Canonical Reference Profiles (Based on Q4 2026 Market Telemetry)
CLOUD_PROFILES: List[CloudInstanceProfile] = [
    # Tier A Development Options (Single/Dual GPU)
    CloudInstanceProfile(
        provider="Lambda Labs",
        instance_type="1x.rtx4090",
        gpu_model="NVIDIA GeForce RTX 4090",
        gpu_count=1,
        total_vram_gb=24,
        system_ram_gb=64,
        vcpus=16,
        interconnect="PCIe Gen 4.0",
        hourly_rate_usd=0.50,
        pricing_model="on-demand",
    ),
    CloudInstanceProfile(
        provider="RunPod",
        instance_type="1x.l40s",
        gpu_model="NVIDIA L40S",
        gpu_count=1,
        total_vram_gb=48,
        system_ram_gb=64,
        vcpus=16,
        interconnect="PCIe Gen 4.0",
        hourly_rate_usd=0.89,
        pricing_model="on-demand",
    ),

    # Tier B Research Options (8x A100 / 8x H100)
    CloudInstanceProfile(
        provider="CoreWeave",
        instance_type="hgx-h100-80gb-8x",
        gpu_model="NVIDIA H100 SXM5",
        gpu_count=8,
        total_vram_gb=640,
        system_ram_gb=1024,
        vcpus=128,
        interconnect="NVLink 4 (900 GB/s bi-directional)",
        hourly_rate_usd=24.00,
        pricing_model="on-demand",
    ),
    CloudInstanceProfile(
        provider="AWS",
        instance_type="p5.48xlarge",
        gpu_model="NVIDIA H100 SXM5",
        gpu_count=8,
        total_vram_gb=640,
        system_ram_gb=2048,
        vcpus=192,
        interconnect="NVSwitch NVLink 4 + EFA 3.2 Tbps",
        hourly_rate_usd=40.96,
        pricing_model="on-demand",
    ),

    # Tier C Large-Scale Pretraining Multi-Node Options (32x to 64x H100/H200)
    CloudInstanceProfile(
        provider="CoreWeave / Custom Slurm Supercluster",
        instance_type="supercluster-64x-h100",
        gpu_model="NVIDIA H100 SXM5 (8 Nodes x 8 GPUs)",
        gpu_count=64,
        total_vram_gb=5120,
        system_ram_gb=8192,
        vcpus=1024,
        interconnect="NVSwitch + InfiniBand NDR 400Gbps Rail-Optimized",
        hourly_rate_usd=192.00,
        pricing_model="reserved-contract",
    ),
]


class CloudProfileRegistry:
    """Registry for querying and filtering cloud compute profiles."""

    @classmethod
    def get_all(cls) -> List[CloudInstanceProfile]:
        return list(CLOUD_PROFILES)

    @classmethod
    def get_by_gpu(cls, gpu_model_substring: str) -> List[CloudInstanceProfile]:
        sub = gpu_model_substring.lower()
        return [p for p in CLOUD_PROFILES if sub in p.gpu_model.lower()]

    @classmethod
    def get_by_provider(cls, provider_name: str) -> List[CloudInstanceProfile]:
        name = provider_name.lower()
        return [p for p in CLOUD_PROFILES if name in p.provider.lower()]
