"""
404 FOUNDERS — Training Orchestrator
Coordinates the complete pretraining lifecycle: model initialization, data feeding,
forward execution, loss computation, backward accumulation, optimization, periodic validation,
atomic checkpointing, telemetry logging, and clean interruption handling.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import signal
import sys
import time
import torch
from torch.utils.data import DataLoader

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
from training.experiments.experiment_tracker import ExperimentManifest, ExperimentTracker
from training.initialization.initializer import ModelInitializer
from training.monitoring.training_monitor import TrainingMonitor
from training.objectives.loss_engine import AutoregressiveLossEngine
from training.optimizers.optimization_engine import OptimizationEngine
from training.schedulers.lr_scheduler import CosineWarmupScheduler
from training.validation.validation_engine import ValidationEngine, ValidationMetrics


@dataclass
class TrainingSummary:
    """Summary of completed or interrupted pretraining run."""
    run_id: str
    status: str
    total_steps: int
    total_tokens: int
    final_train_loss: float
    best_val_loss: Optional[float]
    elapsed_seconds: float
    checkpoints_saved: int


class TrainingOrchestrator:
    """
    Central pretraining coordinator.
    """

    def __init__(
        self,
        model_config: Optional[FoundationModelConfig] = None,
        pretraining_config: Optional[PretrainingConfig] = None,
        run_id: Optional[str] = None,
        description: str = "404 Founders Pretraining Run",
    ) -> None:
        self.model_config = model_config or EXPERIMENTAL_TINY_CONFIG
        self.pretraining_config = pretraining_config or PretrainingConfig()
        self.run_id = run_id or f"run_{int(time.time())}"
        self.description = description

        # Subsystems
        self.device_manager = DeviceManager(
            requested_device=self.pretraining_config.device,
            requested_precision=self.pretraining_config.precision,
        )
        self.initializer = ModelInitializer(self.model_config)
        self.loss_engine = AutoregressiveLossEngine(ignore_index=self.pretraining_config.ignore_index)

        # Output and tracking paths
        self.output_dir = Path(self.pretraining_config.output_dir) / self.run_id
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.monitor = TrainingMonitor(output_dir=str(self.output_dir))
        self.tracker = ExperimentTracker(base_dir=str(Path(self.pretraining_config.output_dir) / "experiments"))
        self.checkpoint_manager = CheckpointManager(
            checkpoint_dir=str(self.output_dir / "checkpoints"),
            keep_last_n=3,
        )

        # Model and optimization engines (instantiated in setup())
        self.model: Optional[NeuralCore] = None
        self.forward_engine: Optional[ForwardEngine] = None
        self.optimizer_engine: Optional[OptimizationEngine] = None
        self.scheduler: Optional[CosineWarmupScheduler] = None
        self.validation_engine: Optional[ValidationEngine] = None

        self._interrupted = False
        self._setup_signal_handlers()

    def _setup_signal_handlers(self) -> None:
        """Register graceful shutdown handlers for SIGINT and SIGTERM."""
        def handler(sig, frame):
            print(f"\n[TrainingOrchestrator] Interruption signal ({sig}) received. Finalizing current step and saving emergency checkpoint...")
            self._interrupted = True

        try:
            signal.signal(signal.SIGINT, handler)
            signal.signal(signal.SIGTERM, handler)
        except (ValueError, AttributeError):
            # When executed in non-main thread
            pass

    def setup(self, seed: Optional[int] = None) -> None:
        """
        Instantiate model from random initialization, build optimization engine,
        and register experiment manifest.
        """
        active_seed = seed if seed is not None else self.pretraining_config.seed

        # 1. Random initialization
        self.model, init_report = self.initializer.initialize_model(seed=active_seed)
        self.model = self.device_manager.to_device(self.model)

        # 2. Engines
        self.forward_engine = ForwardEngine(self.model, self.device_manager)
        self.optimizer_engine = OptimizationEngine(self.model, self.pretraining_config)
        self.scheduler = CosineWarmupScheduler(
            self.optimizer_engine.optimizer,
            warmup_steps=self.pretraining_config.warmup_steps,
            max_steps=self.pretraining_config.max_steps,
            min_lr=self.pretraining_config.min_learning_rate,
        )
        self.validation_engine = ValidationEngine(self.forward_engine, self.loss_engine)

        # 3. Create initial manifest
        self.tracker.create_experiment(
            experiment_id=self.run_id,
            description=self.description,
            model_config=self.model_config,
            pretraining_config=self.pretraining_config,
            hardware_profile={
                "device": self.device_manager.device_name,
                "precision": self.device_manager.precision.value,
                "parameter_count": init_report.total_parameters,
            },
        )

    def train(
        self,
        train_loader: DataLoader,
        val_loader: Optional[DataLoader] = None,
        resume_from: Optional[str] = None,
    ) -> TrainingSummary:
        """
        Execute pretraining loop across batches.
        """
        if self.model is None or self.optimizer_engine is None or self.scheduler is None or self.forward_engine is None:
            self.setup()

        start_step = 0
        best_val_loss = float("inf")
        checkpoints_saved = 0
        start_time = time.time()

        # Checkpoint restoration if resuming
        if resume_from:
            print(f"[TrainingOrchestrator] Resuming from checkpoint: {resume_from}")
            payload = self.checkpoint_manager.load_checkpoint(
                resume_from,
                model=self.model,
                optimizer_engine=self.optimizer_engine,
                scheduler=self.scheduler,
            )
            start_step = payload.get("step", 0)
            best_val_loss = payload.get("metrics", {}).get("best_val_loss", float("inf"))

        self.model.train()
        global_step = start_step
        running_train_loss = 0.0
        last_train_loss = 0.0

        train_iter = iter(train_loader)

        while global_step < self.pretraining_config.max_steps and not self._interrupted:
            try:
                batch = next(train_iter)
            except StopIteration:
                train_iter = iter(train_loader)
                batch = next(train_iter)

            input_ids = batch["input_ids"]
            labels = batch["labels"]
            batch_tokens = int((labels != self.pretraining_config.ignore_index).sum().item())

            # Forward pass
            logits = self.forward_engine.forward(input_ids, is_causal=True)
            loss_out = self.loss_engine.compute_loss(logits, labels)
            running_train_loss += loss_out.loss_value
            last_train_loss = loss_out.loss_value

            # Backward pass & accumulation
            is_step_ready = self.optimizer_engine.backward_and_accumulate(loss_out.loss)

            if is_step_ready:
                global_step += 1
                grad_norm = self.optimizer_engine.step()
                current_lr = self.scheduler.get_last_lr()[0]
                self.scheduler.step()

                # Step telemetry logging
                val_metrics_step: Optional[ValidationMetrics] = None
                if val_loader is not None and (
                    global_step % self.pretraining_config.eval_interval == 0
                    or global_step == self.pretraining_config.max_steps
                ):
                    val_metrics_step = self.validation_engine.evaluate(val_loader, max_batches=5)
                    if val_metrics_step.val_loss < best_val_loss:
                        best_val_loss = val_metrics_step.val_loss
                        # Save best model checkpoint
                        self.checkpoint_manager.save_checkpoint(
                            step=global_step,
                            model=self.model,
                            optimizer_engine=self.optimizer_engine,
                            scheduler=self.scheduler,
                            model_config=self.model_config,
                            pretraining_config=self.pretraining_config,
                            metrics={"train_loss": loss_out.loss_value, "val_loss": val_metrics_step.val_loss},
                            is_best=True,
                        )
                        checkpoints_saved += 1

                step_metrics = self.monitor.record_step(
                    step=global_step,
                    train_loss=loss_out.loss_value,
                    perplexity=loss_out.perplexity,
                    token_accuracy=loss_out.token_accuracy,
                    learning_rate=current_lr,
                    grad_norm=grad_norm,
                    batch_tokens=batch_tokens,
                    val_loss=val_metrics_step.val_loss if val_metrics_step else None,
                    val_perplexity=val_metrics_step.perplexity if val_metrics_step else None,
                )

                if global_step % self.pretraining_config.log_interval == 0 or global_step == 1:
                    print(self.monitor.format_log_line(step_metrics))

                # Periodic checkpoint persistence
                if global_step % self.pretraining_config.save_interval == 0:
                    self.checkpoint_manager.save_checkpoint(
                        step=global_step,
                        model=self.model,
                        optimizer_engine=self.optimizer_engine,
                        scheduler=self.scheduler,
                        model_config=self.model_config,
                        pretraining_config=self.pretraining_config,
                        metrics={"train_loss": loss_out.loss_value},
                        is_best=False,
                    )
                    checkpoints_saved += 1

        elapsed = time.time() - start_time
        status = "INTERRUPTED" if self._interrupted else "COMPLETED"

        # Final checkpoint on completion or interruption
        self.checkpoint_manager.save_checkpoint(
            step=global_step,
            model=self.model,
            optimizer_engine=self.optimizer_engine,
            scheduler=self.scheduler,
            model_config=self.model_config,
            pretraining_config=self.pretraining_config,
            metrics={"train_loss": last_train_loss, "best_val_loss": best_val_loss if best_val_loss != float("inf") else last_train_loss},
            tag="final",
        )
        checkpoints_saved += 1

        # Update experiment manifest
        manifest = self.tracker.load_manifest(self.run_id)
        manifest.completed_steps = global_step
        manifest.total_tokens = self.monitor.total_tokens_processed
        manifest.final_train_loss = round(last_train_loss, 5)
        manifest.best_val_loss = round(best_val_loss, 5) if best_val_loss != float("inf") else None
        manifest.duration_seconds = round(elapsed, 2)
        manifest.status = status
        self.tracker.save_manifest(manifest)

        return TrainingSummary(
            run_id=self.run_id,
            status=status,
            total_steps=global_step,
            total_tokens=self.monitor.total_tokens_processed,
            final_train_loss=round(last_train_loss, 5),
            best_val_loss=round(best_val_loss, 5) if best_val_loss != float("inf") else None,
            elapsed_seconds=round(elapsed, 2),
            checkpoints_saved=checkpoints_saved,
        )
