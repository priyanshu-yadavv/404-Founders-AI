"""
404 FOUNDERS — Pre-Flight Training Verifier
Executes the mandatory 10-step verification protocol prior to executing any pretraining workloads.
Confirms model initialization, forward pass, loss calculation, backward propagation,
gradient flow, optimizer weight updates, atomic checkpointing, recovery, evaluation, and toy overfitting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import math
import shutil
import tempfile
import time
import torch

from core.intelligence.neural_core import NeuralCore
from training.checkpoints.checkpoint_manager import CheckpointManager
from training.configs.model_config import (
    EXPERIMENTAL_TINY_CONFIG,
    FoundationModelConfig,
    PretrainingConfig,
)
from training.dataloaders.data_loader import FoundationDataLoader
from training.engine.device_manager import DeviceManager
from training.engine.forward_engine import ForwardEngine
from training.initialization.initializer import ModelInitializer
from training.objectives.loss_engine import AutoregressiveLossEngine
from training.optimizers.optimization_engine import OptimizationEngine
from training.schedulers.lr_scheduler import CosineWarmupScheduler
from training.validation.validation_engine import ValidationEngine


@dataclass
class PreflightStepResult:
    """Outcome of a single preflight verification step."""
    step_number: int
    step_name: str
    passed: bool
    duration_ms: float
    detail: str


@dataclass
class PreflightReport:
    """Comprehensive 10-step preflight verification report."""
    all_passed: bool
    total_duration_ms: float
    results: List[PreflightStepResult] = field(default_factory=list)

    def summary(self) -> str:
        """Formatted human-readable report."""
        lines = [
            "=== 404 FOUNDERS PRE-FLIGHT VERIFICATION REPORT ===",
            f"Overall Status: {'ALL 10 CHECKS PASSED' if self.all_passed else 'VERIFICATION FAILED'}",
            f"Total Duration: {self.total_duration_ms:.2f} ms",
            "---------------------------------------------------",
        ]
        for res in self.results:
            status = "PASS" if res.passed else "FAIL"
            lines.append(f"[{res.step_number:02d}] {status} - {res.step_name} ({res.duration_ms:.1f}ms): {res.detail}")
        lines.append("===================================================")
        return "\n".join(lines)


class PreflightVerifier:
    """
    Coordinates the 10-step mathematical and software integrity verification suite.
    """

    def __init__(
        self,
        model_config: Optional[FoundationModelConfig] = None,
        pretraining_config: Optional[PretrainingConfig] = None,
    ) -> None:
        self.model_config = model_config or EXPERIMENTAL_TINY_CONFIG
        self.pretraining_config = pretraining_config or PretrainingConfig(
            batch_size=2,
            max_steps=25,
            warmup_steps=5,
            learning_rate=1e-3,
        )
        self.device_manager = DeviceManager(requested_device="cpu", requested_precision="fp32")
        self.initializer = ModelInitializer(self.model_config)
        self.loss_engine = AutoregressiveLossEngine(ignore_index=0)

    def run_all_checks(self) -> PreflightReport:
        """
        Execute all 10 preflight checks in order.
        """
        results: List[PreflightStepResult] = []
        overall_start = time.time()
        temp_dir = tempfile.mkdtemp(prefix="404_preflight_")

        try:
            model = None
            forward_engine = None
            optimizer_engine = None
            scheduler = None
            synthetic_batch = None
            loss_out = None
            initial_param_clone = None
            saved_ckpt_path = None

            # -------------------------------------------------------------
            # Step 1: Model Initialization Test
            # -------------------------------------------------------------
            t0 = time.time()
            try:
                model, init_report = self.initializer.initialize_model(seed=self.model_config.random_seed)
                model = self.device_manager.to_device(model)
                forward_engine = ForwardEngine(model, self.device_manager)
                passed = init_report.all_finite and (init_report.total_parameters > 0)
                detail = f"Model initialized with {init_report.total_parameters:,} finite params. SHA: {init_report.weight_digest_sha256[:10]}"
            except Exception as e:
                passed = False
                detail = f"Initialization error: {str(e)}"
            results.append(PreflightStepResult(1, "Model Initialization", passed, (time.time() - t0) * 1000, detail))
            if not passed:
                return PreflightReport(False, (time.time() - overall_start) * 1000, results)

            # -------------------------------------------------------------
            # Step 2: Forward-Pass Test
            # -------------------------------------------------------------
            t0 = time.time()
            try:
                loader = FoundationDataLoader.create_synthetic_loader(
                    num_samples=4,
                    batch_size=2,
                    seq_len=16,
                    vocab_size=self.model_config.vocab_size,
                    seed=404,
                )
                synthetic_batch = next(iter(loader))
                input_ids = synthetic_batch["input_ids"]
                logits = forward_engine.forward(
                    input_ids,
                    context_hints={"force_mode": "general", "operating_mode": "general"},
                    is_causal=True,
                )
                passed = bool((logits.shape == (2, 16, self.model_config.vocab_size)) and torch.all(torch.isfinite(logits)).item())
                detail = f"Output logits shape: {tuple(logits.shape)}, all finite: {passed}"
            except Exception as e:
                passed = False
                detail = f"Forward pass error: {str(e)}"
            results.append(PreflightStepResult(2, "Forward Pass", passed, (time.time() - t0) * 1000, detail))
            if not passed:
                return PreflightReport(False, (time.time() - overall_start) * 1000, results)

            # -------------------------------------------------------------
            # Step 3: Loss Calculation Test
            # -------------------------------------------------------------
            t0 = time.time()
            try:
                loss_out = self.loss_engine.compute_loss(logits, synthetic_batch["labels"])
                passed = (loss_out.loss_value > 0.0) and math.isfinite(loss_out.loss_value)
                detail = f"Autoregressive loss: {loss_out.loss_value:.4f}, accuracy: {loss_out.token_accuracy*100:.1f}%, ppl: {loss_out.perplexity:.2f}"
            except Exception as e:
                passed = False
                detail = f"Loss calculation error: {str(e)}"
            results.append(PreflightStepResult(3, "Loss Calculation", passed, (time.time() - t0) * 1000, detail))
            if not passed:
                return PreflightReport(False, (time.time() - overall_start) * 1000, results)

            # -------------------------------------------------------------
            # Step 4: Backward-Pass Test
            # -------------------------------------------------------------
            t0 = time.time()
            try:
                optimizer_engine = OptimizationEngine(model, self.pretraining_config)
                optimizer_engine.zero_grad()
                loss_out.loss.backward()

                # Also backward through alternate expert route to verify all MoE pathways
                logits_alt = forward_engine.forward(
                    synthetic_batch["input_ids"],
                    context_hints={"force_mode": "personal", "operating_mode": "personal"},
                    is_causal=True,
                )
                loss_alt = self.loss_engine.compute_loss(logits_alt, synthetic_batch["labels"])
                loss_alt.loss.backward()

                passed = True
                detail = "Backward autograd propagation completed across all standard and routed pathways."
            except Exception as e:
                passed = False
                detail = f"Backward propagation error: {str(e)}"
            results.append(PreflightStepResult(4, "Backward Pass", passed, (time.time() - t0) * 1000, detail))
            if not passed:
                return PreflightReport(False, (time.time() - overall_start) * 1000, results)

            # -------------------------------------------------------------
            # Step 5: Gradient Validation
            # -------------------------------------------------------------
            t0 = time.time()
            try:
                missing_grads = []
                non_finite_grads = []
                for name, p in model.named_parameters():
                    if p.requires_grad:
                        if p.grad is None:
                            missing_grads.append(name)
                        elif not torch.all(torch.isfinite(p.grad)):
                            non_finite_grads.append(name)
                passed = (len(missing_grads) == 0) and (len(non_finite_grads) == 0)
                detail = f"Trainable params checked. Missing grads: {len(missing_grads)}, Non-finite grads: {len(non_finite_grads)}"
            except Exception as e:
                passed = False
                detail = f"Gradient validation error: {str(e)}"
            results.append(PreflightStepResult(5, "Gradient Validation", passed, (time.time() - t0) * 1000, detail))
            if not passed:
                return PreflightReport(False, (time.time() - overall_start) * 1000, results)

            # -------------------------------------------------------------
            # Step 6: Optimizer Update Test
            # -------------------------------------------------------------
            t0 = time.time()
            try:
                # Capture parameter copies before step
                before_vals = {name: p.clone() for name, p in model.named_parameters() if p.requires_grad}
                scheduler = CosineWarmupScheduler(
                    optimizer_engine.optimizer,
                    warmup_steps=self.pretraining_config.warmup_steps,
                    max_steps=self.pretraining_config.max_steps,
                )
                grad_norm = optimizer_engine.step()
                scheduler.step()
                diffs = [(p - before_vals[name]).abs().max().item() for name, p in model.named_parameters() if p.requires_grad]
                max_diff = max(diffs)
                updated_count = sum(1 for d in diffs if d > 0.0)
                passed = max_diff > 0.0 and math.isfinite(grad_norm)
                detail = f"Optimizer step succeeded. Updated tensors: {updated_count}/{len(diffs)}, Max change: {max_diff:.6f}, Grad norm: {grad_norm:.4f}"
            except Exception as e:
                passed = False
                detail = f"Optimizer update error: {str(e)}"
            results.append(PreflightStepResult(6, "Optimizer Update", passed, (time.time() - t0) * 1000, detail))
            if not passed:
                return PreflightReport(False, (time.time() - overall_start) * 1000, results)

            # -------------------------------------------------------------
            # Step 7: Checkpoint Save Test
            # -------------------------------------------------------------
            t0 = time.time()
            try:
                ckpt_mgr = CheckpointManager(checkpoint_dir=temp_dir)
                saved_ckpt_path, sha = ckpt_mgr.save_checkpoint(
                    step=1,
                    model=model,
                    optimizer_engine=optimizer_engine,
                    scheduler=scheduler,
                    model_config=self.model_config,
                    pretraining_config=self.pretraining_config,
                    metrics={"train_loss": loss_out.loss_value},
                )
                passed = saved_ckpt_path.is_file() and saved_ckpt_path.with_suffix(".pt.sha256").is_file()
                detail = f"Checkpoint saved atomically: {saved_ckpt_path.name} (SHA: {sha[:10]})"
            except Exception as e:
                passed = False
                detail = f"Checkpoint save error: {str(e)}"
            results.append(PreflightStepResult(7, "Checkpoint Save", passed, (time.time() - t0) * 1000, detail))
            if not passed:
                return PreflightReport(False, (time.time() - overall_start) * 1000, results)

            # -------------------------------------------------------------
            # Step 8: Checkpoint Recovery Test
            # -------------------------------------------------------------
            t0 = time.time()
            try:
                # Initialize new model and load checkpoint into it
                new_model = NeuralCore(self.model_config.to_neural_core_config())
                loaded_payload = ckpt_mgr.load_checkpoint(
                    saved_ckpt_path,
                    model=new_model,
                    verify_integrity=True,
                )
                # Compare weights
                mismatches = 0
                for (n1, p1), (n2, p2) in zip(model.named_parameters(), new_model.named_parameters()):
                    if not torch.allclose(p1, p2, atol=1e-6):
                        mismatches += 1
                passed = (mismatches == 0) and (loaded_payload["step"] == 1)
                detail = f"Checkpoint restored cleanly. Parameter tensor mismatches: {mismatches}"
            except Exception as e:
                passed = False
                detail = f"Checkpoint recovery error: {str(e)}"
            results.append(PreflightStepResult(8, "Checkpoint Recovery", passed, (time.time() - t0) * 1000, detail))
            if not passed:
                return PreflightReport(False, (time.time() - overall_start) * 1000, results)

            # -------------------------------------------------------------
            # Step 9: Validation Loop Test
            # -------------------------------------------------------------
            t0 = time.time()
            try:
                val_engine = ValidationEngine(forward_engine, self.loss_engine)
                val_loader = FoundationDataLoader.create_synthetic_loader(
                    num_samples=4,
                    batch_size=2,
                    seq_len=16,
                    vocab_size=self.model_config.vocab_size,
                    seed=777,
                )
                val_metrics = val_engine.evaluate(val_loader)
                passed = (val_metrics.val_loss > 0.0) and (val_metrics.num_batches == 2)
                detail = f"Validation evaluated: loss={val_metrics.val_loss:.4f}, ppl={val_metrics.perplexity:.2f}, tokens={val_metrics.total_tokens}"
            except Exception as e:
                passed = False
                detail = f"Validation loop error: {str(e)}"
            results.append(PreflightStepResult(9, "Validation Loop", passed, (time.time() - t0) * 1000, detail))
            if not passed:
                return PreflightReport(False, (time.time() - overall_start) * 1000, results)

            # -------------------------------------------------------------
            # Step 10: Small Synthetic Dataset Overfitting Test
            # -------------------------------------------------------------
            t0 = time.time()
            try:
                # Train model on 1 fixed synthetic sequence for 35 steps
                # To guarantee loss reduction, use simple repetitive sequence
                toy_loader = FoundationDataLoader.create_synthetic_loader(
                    num_samples=1,
                    batch_size=1,
                    seq_len=16,
                    vocab_size=self.model_config.vocab_size,
                    seed=404,
                    shuffle=False,
                )
                toy_batch = next(iter(toy_loader))
                toy_inputs = toy_batch["input_ids"]
                toy_labels = toy_batch["labels"]

                # Record initial loss
                model.train()
                with torch.no_grad():
                    init_logits = forward_engine.forward(toy_inputs, is_causal=True)
                    initial_loss = self.loss_engine.compute_loss(init_logits, toy_labels).loss_value

                # Train for 45 steps
                final_loss = initial_loss
                for step_idx in range(45):
                    optimizer_engine.zero_grad()
                    step_logits = forward_engine.forward(toy_inputs, is_causal=True)
                    step_loss = self.loss_engine.compute_loss(step_logits, toy_labels)
                    step_loss.loss.backward()
                    optimizer_engine.step()
                    scheduler.step()
                    final_loss = step_loss.loss_value

                # Verify loss decreased significantly (> 20%)
                loss_reduction_pct = ((initial_loss - final_loss) / initial_loss) * 100.0
                passed = (final_loss < initial_loss) and (loss_reduction_pct >= 20.0)
                detail = f"Toy overfitting: Initial loss {initial_loss:.4f} -> Final {final_loss:.4f} (-{loss_reduction_pct:.1f}% reduction)"
            except Exception as e:
                passed = False
                detail = f"Overfitting test error: {str(e)}"
            results.append(PreflightStepResult(10, "Toy Overfitting Verification", passed, (time.time() - t0) * 1000, detail))

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        all_passed = all(r.passed for r in results)
        total_time = (time.time() - overall_start) * 1000
        return PreflightReport(all_passed=all_passed, total_duration_ms=total_time, results=results)
