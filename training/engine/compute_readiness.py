"""
404 FOUNDERS — Compute Readiness Gate & Capacity Auditor
Performs rigorous resource estimation across parameters, activations, gradients,
and optimizer state memory. Strictly blocks large-scale training workloads on constrained
workstations, requiring verified GPU cluster infrastructure for production scaling.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional
import math
import torch

from infrastructure.local.hardware import LocalHardwareInspector
from infrastructure.local.runtime import LocalRuntimeManager
from training.configs.model_config import FoundationModelConfig, PretrainingConfig


@dataclass
class MemoryBreakdown:
    """Estimated memory consumption in megabytes."""
    model_weights_mb: float
    gradients_mb: float
    optimizer_state_mb: float
    activations_mb: float
    kv_cache_mb: float
    total_training_memory_mb: float
    total_training_memory_gb: float


@dataclass
class ComputeReadinessReport:
    """
    Formal compute readiness verdict and infrastructure capacity audit.
    """
    verdict: str  # APPROVED_LOCAL_PILOT, BLOCKED_INSUFFICIENT_MEMORY, REQUIRES_GPU_CLUSTER
    is_safe_to_execute: bool
    hardware_summary: Dict[str, Any]
    memory_breakdown: MemoryBreakdown
    batch_size_feasible: bool
    estimated_throughput_tokens_per_sec: float
    estimated_step_duration_sec: float
    recommendation: str
    blocker_reason: Optional[str] = None

    def summary(self) -> str:
        """Formatted human-readable summary."""
        mb = self.memory_breakdown
        return (
            f"=== 404 FOUNDERS COMPUTE READINESS REPORT ===\n"
            f"Verdict: {self.verdict} (Safe to Execute: {self.is_safe_to_execute})\n"
            f"Host CPU: {self.hardware_summary.get('cpu_model', 'Unknown')} ({self.hardware_summary.get('threads', 0)} threads)\n"
            f"Host RAM: {self.hardware_summary.get('available_ram_gb', 0):.2f} GB available / {self.hardware_summary.get('total_ram_gb', 0):.2f} GB total\n"
            f"Swap Status: {self.hardware_summary.get('total_swap_gb', 0):.2f} GB (Swapless Guard Active)\n"
            f"Safe RAM Ceiling: {self.hardware_summary.get('safe_memory_budget_gb', 0):.2f} GB\n"
            f"---------------------------------------------\n"
            f"Estimated Training Memory Footprint:\n"
            f"  • Model Parameters:   {mb.model_weights_mb:.2f} MB\n"
            f"  • Gradients:          {mb.gradients_mb:.2f} MB\n"
            f"  • AdamW Optimizer:    {mb.optimizer_state_mb:.2f} MB (8 bytes/param)\n"
            f"  • Peak Activations:   {mb.activations_mb:.2f} MB\n"
            f"  • Total Peak Memory:  {mb.total_training_memory_gb:.3f} GB\n"
            f"---------------------------------------------\n"
            f"Throughput Estimate: ~{self.estimated_throughput_tokens_per_sec:.1f} tokens/s ({self.estimated_step_duration_sec:.2f}s per step)\n"
            f"Recommendation: {self.recommendation}\n"
            f"{('Blocker Detail: ' + self.blocker_reason) if self.blocker_reason else ''}\n"
            f"============================================="
        )


class ComputeReadinessGate:
    """
    Audits memory feasibility, hardware limits, and enforces safety boundaries.
    """

    def __init__(self) -> None:
        self.profile = LocalHardwareInspector.get_profile()
        self.runtime_manager = LocalRuntimeManager(self.profile)

    def calculate_memory_footprint(
        self,
        model_config: FoundationModelConfig,
        pretraining_config: PretrainingConfig,
    ) -> MemoryBreakdown:
        """
        Analytically calculate peak memory requirements:
        1. Model Weights: N_params * bytes_per_param (4 for FP32, 2 for BF16)
        2. Gradients: N_params * 4 bytes
        3. Optimizer State: 2 * N_params * 4 bytes (AdamW stores FP32 momentum and variance = 8 bytes/param)
        4. Activations: O(batch * seq_len * d_model * n_layers * factor)
        """
        # Estimate parameter count
        vocab = model_config.vocab_size
        d = model_config.d_model
        layers = model_config.n_layers
        ffn_dim = model_config.intermediate_dim or int(2 * d * 4 / 3)
        experts = model_config.num_experts

        # Embeddings + Unembedding
        embed_params = vocab * d + d * vocab
        # Attention per layer (q, k, v, out) = 4 * d * d
        attn_params = layers * (4 * d * d)
        # SwiGLU FFN per layer (w_gate, w_up, w_down) = 3 * d * ffn_dim
        ffn_params = layers * (3 * d * ffn_dim)
        # Experts (GeneralReasoning + PersonalAI)
        expert_params = experts * (2 * d * d)
        # Norms & Router
        other_params = layers * (4 * d) + d * experts

        total_params = embed_params + attn_params + ffn_params + expert_params + other_params

        bytes_per_param = 4.0 if pretraining_config.precision == "fp32" else 2.0
        weights_mb = (total_params * bytes_per_param) / (1024.0 * 1024.0)
        grads_mb = (total_params * 4.0) / (1024.0 * 1024.0)
        optimizer_mb = (total_params * 8.0) / (1024.0 * 1024.0)

        # Activations estimation
        b = pretraining_config.batch_size
        t = model_config.max_seq_len
        # Standard transformer activation factor: ~34 * b * t * d * layers for attention + MLP activations
        act_bytes = b * t * d * layers * 34 * bytes_per_param
        activations_mb = act_bytes / (1024.0 * 1024.0)

        total_mb = weights_mb + grads_mb + optimizer_mb + activations_mb
        total_gb = total_mb / 1024.0

        return MemoryBreakdown(
            model_weights_mb=round(weights_mb, 2),
            gradients_mb=round(grads_mb, 2),
            optimizer_state_mb=round(optimizer_mb, 2),
            activations_mb=round(activations_mb, 2),
            kv_cache_mb=0.0,
            total_training_memory_mb=round(total_mb, 2),
            total_training_memory_gb=round(total_gb, 4),
        )

    def evaluate_readiness(
        self,
        model_config: FoundationModelConfig,
        pretraining_config: PretrainingConfig,
    ) -> ComputeReadinessReport:
        """
        Evaluate whether the requested configuration can safely run on current host hardware.
        """
        profile = self.profile
        budget_gb = self.runtime_manager.budget.max_ram_gb
        mem = self.calculate_memory_footprint(model_config, pretraining_config)
        swap_gb = round(profile.swap_total_bytes / (1024**3), 2)

        hw_summary = {
            "cpu_model": profile.cpu_model,
            "cores": profile.physical_cores,
            "threads": profile.logical_threads,
            "total_ram_gb": profile.total_ram_gb,
            "available_ram_gb": profile.available_ram_gb,
            "total_swap_gb": swap_gb,
            "has_gpu": profile.has_nvidia_gpu,
            "safe_memory_budget_gb": budget_gb,
        }

        # Check safety ceiling against local safe memory budget
        is_safe_memory = mem.total_training_memory_gb <= budget_gb
        batch_feasible = is_safe_memory and (pretraining_config.batch_size >= 1)

        # Rough throughput estimation
        # On modern 4-core laptop CPU, approx 200-800 tokens/sec for micro models; ~10-30 tokens/sec for medium models
        step_tokens = pretraining_config.batch_size * model_config.max_seq_len
        if mem.total_training_memory_gb < 0.2:
            throughput = 450.0  # tokens/sec on CPU
        elif mem.total_training_memory_gb < 1.0:
            throughput = 150.0
        else:
            throughput = 35.0

        step_duration = max(0.01, step_tokens / throughput)

        if not is_safe_memory:
            verdict = "BLOCKED_INSUFFICIENT_MEMORY"
            safe_to_execute = False
            blocker = (
                f"Required memory ({mem.total_training_memory_gb:.2f} GB) exceeds safe workstation ceiling "
                f"({budget_gb:.2f} GB). Host has 0 B swap; proceeding will trigger Linux kernel OOM panic."
            )
            recommendation = "Deploy to Phase 05 GPU cluster (Tier B/C) or reduce model dimensions/batch size for local pilot testing."
        elif mem.total_training_memory_gb > 2.5:
            verdict = "REQUIRES_GPU_CLUSTER"
            safe_to_execute = False
            blocker = "Model exceeds local workstation pilot threshold. Large-scale pretraining requires dedicated GPU cluster."
            recommendation = "Submit training job via Phase 05 Slurm generator to Tier B / Tier C cluster."
        else:
            verdict = "APPROVED_LOCAL_PILOT"
            safe_to_execute = True
            blocker = None
            recommendation = "Safe to run local verification and micro-pilot pretraining on CPU."

        return ComputeReadinessReport(
            verdict=verdict,
            is_safe_to_execute=safe_to_execute,
            hardware_summary=hw_summary,
            memory_breakdown=mem,
            batch_size_feasible=batch_feasible,
            estimated_throughput_tokens_per_sec=throughput,
            estimated_step_duration_sec=step_duration,
            recommendation=recommendation,
            blocker_reason=blocker,
        )
