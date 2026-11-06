# 404 FOUNDERS — Training Experiments & Reproducibility Tracking

**Document ID:** `DOC-TRAIN-007`  
**Phase:** Phase 06 Baseline  
**Authors:** Principal AI Research Scientist & MLOps Architect  

---

## 1. Overview & Reproducibility Standards

Scientific validity requires that every training run be fully reproducible and auditable.
Every pretraining experiment within 404 FOUNDERS captures:
- Unique immutable `experiment_id`
- Full model and pretraining hyperparameter configuration dictionaries
- PRNG initialization seeds (`seed = 404`)
- Dataset manifest version and tokenizer model hash
- Git repository commit hash
- Step-by-step telemetry stream (`metrics.jsonl`)
- Checkpoint directory and final evaluation metrics

---

## 2. Experiment Directory Hierarchy

Experiments are stored under `experiments/` (excluded from Git tracking):

```text
experiments/
└── run_1793985556/
    ├── manifest.json                  # Experiment manifest specification
    ├── metrics.jsonl                  # Step-by-step training telemetry
    └── checkpoints/
        ├── checkpoint_step_0000005.pt
        ├── checkpoint_step_0000005.pt.sha256
        ├── checkpoint_step_0000010.pt
        ├── checkpoint_step_0000010.pt.sha256
        ├── best_model.pt
        └── best_model.pt.sha256
```

---

## 3. Experiment Manifest Schema

The `ExperimentTracker` (`training/experiments/experiment_tracker.py`) persists:

```json
{
  "experiment_id": "run_1793985556",
  "description": "Local pilot pretraining (tiny)",
  "created_at": "2026-11-06T17:19:17.557451+00:00",
  "model_config": {
    "vocab_size": 512,
    "d_model": 64,
    "n_layers": 2,
    "n_heads": 2,
    "max_seq_len": 64,
    "dropout": 0.0,
    "init_strategy": "scaled_gaussian"
  },
  "pretraining_config": {
    "batch_size": 2,
    "gradient_accumulation_steps": 1,
    "learning_rate": 0.0005,
    "max_steps": 15,
    "precision": "fp32",
    "device": "cpu"
  },
  "initialization_seed": 404,
  "dataset_version": "v0.4.0",
  "tokenizer_version": "custom-bpe-v0.4.0",
  "hardware_profile": {
    "device": "Host CPU",
    "precision": "fp32",
    "parameter_count": 221760
  },
  "git_commit": "6c32bba",
  "completed_steps": 15,
  "total_tokens": 1920,
  "final_train_loss": 6.17334,
  "best_val_loss": 6.23136,
  "duration_seconds": 0.26,
  "status": "COMPLETED"
}
```

---

## 4. Operational Best Practices

1. **Preflight Verification First:** Never launch a training experiment without running `scripts/validate_training.py`.
2. **Compute Readiness Inspection:** Ensure `ComputeReadinessGate` verifies memory headroom before starting runs.
3. **Reproducible Resumption:** Use `scripts/resume_training.py` with verified `.pt.sha256` sidecars to continue interrupted training runs.
