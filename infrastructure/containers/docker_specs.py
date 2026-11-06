"""
404 FOUNDERS — Docker & Container Specifications
Generates reproducible Dockerfiles and Docker Compose manifests for single-node development
and GPU-accelerated research environments.
"""

from __future__ import annotations

from typing import Dict, List, Optional


class ContainerSpecGenerator:
    """Generates standard container specifications for development and research."""

    @classmethod
    def generate_dockerfile(
        cls,
        base_image: str = "nvidia/cuda:12.4.1-devel-ubuntu22.04",
        python_version: str = "3.11",
        include_pytorch: bool = True,
        include_jax: bool = True,
    ) -> str:
        """Generate a production Dockerfile for containerized GPU training."""
        lines = [
            f"# 404 FOUNDERS — Official Training Container Specification",
            f"# Base Image: {base_image}",
            f"FROM {base_image}",
            "",
            "ENV DEBIAN_FRONTEND=noninteractive \\",
            "    PYTHONUNBUFFERED=1 \\",
            "    PYTHONDONTWRITEBYTECODE=1 \\",
            "    CUDA_DEVICE_ORDER=PCI_BUS_ID \\",
            "    NCCL_DEBUG=INFO \\",
            "    NCCL_IB_DISABLE=0 \\",
            "    FOUNDERS_ENV=container",
            "",
            "# System Dependencies",
            "RUN apt-get update && apt-get install -y --no-install-recommends \\",
            "    build-essential \\",
            "    cmake \\",
            "    git \\",
            "    curl \\",
            "    ca-certificates \\",
            f"    python{python_version} \\",
            f"    python{python_version}-dev \\",
            f"    python{python_version}-venv \\",
            "    python3-pip \\",
            "    iproute2 \\",
            "    pciutils \\",
            "    && rm -rf /var/lib/apt/lists/*",
            "",
            f"RUN update-alternatives --install /usr/bin/python python /usr/bin/python{python_version} 1 \\",
            f"    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python{python_version} 1",
            "",
            "WORKDIR /workspace/404-FOUNDERS",
            "COPY pyproject.toml .",
            "",
            "# Python Environment Setup",
            "RUN pip install --no-cache-dir --upgrade pip setuptools wheel",
        ]

        if include_pytorch:
            lines.append("RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124")

        if include_jax:
            lines.append("RUN pip install --no-cache-dir -U \"jax[cuda12]\"")

        lines.extend([
            "",
            "COPY . .",
            "",
            "CMD [\"/bin/bash\"]",
        ])
        return "\n".join(lines)

    @classmethod
    def generate_docker_compose(
        cls,
        gpu_count: int = 1,
        shared_memory_size: str = "32g",
    ) -> str:
        """Generate docker-compose.yml for workstation or multi-GPU single-node dev."""
        return f"""version: '3.8'

services:
  training-node:
    build:
      context: .
      dockerfile: infrastructure/containers/Dockerfile
    container_name: 404_founders_node
    ipc: host
    shm_size: '{shared_memory_size}'
    ulimits:
      memlock: -1
      stack: 67108864
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: {gpu_count}
              capabilities: [gpu, utility, compute]
    volumes:
      - .:/workspace/404-FOUNDERS
      - ./data:/workspace/404-FOUNDERS/data
      - ./logs:/workspace/404-FOUNDERS/logs
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - NCCL_DEBUG=INFO
      - FOUNDERS_LOG_FORMAT=json
    stdin_open: true
    tty: true
"""
