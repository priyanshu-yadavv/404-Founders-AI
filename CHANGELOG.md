# Changelog

All notable changes to the 404 FOUNDERS project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to Phase-based Development Governance.

## [Phase-03] - 2026-11-06

### Added
- **Central Neural Core (`core/intelligence/neural_core.py`):** Central coordinator supporting configurable dimensions, input projection, hierarchical transformer blocks, dynamic routing, specialized experts, and prediction output (~0.63M prototype parameters).
- **Custom Neural Layers (`neural_architecture/layers/`):**
  - `CustomRMSNorm`: Root Mean Square Layer Normalization with learnable gains.
  - `InputProjectionLayer`: Dual-mode projection for discrete tokens and continuous embeddings.
  - `OutputProjectionLayer`: Final un-embedding projection layer.
  - `FeatureTransformationLayer`: Gated SwiGLU feed-forward network.
  - `ResidualConnection`: Pre-normalized residual connection with LayerScale scaling.
  - `RotaryPositionEmbedding`: Rotary Position Embedding (RoPE) relative encoding.
- **Custom Multi-Mechanism Attention (MMA) Prototypes (`core/attention/`):**
  - `GlobalAttention`: Dense pairwise scaled dot-product multi-head attention.
  - `SparseAttention`: Sliding-window banded diagonal attention ($O(T \cdot W)$).
  - `HierarchicalAttention`: Two-tier micro intra-chunk and macro inter-chunk attention.
  - `AttentionFusionController`: Input-conditioned 3-way gating network dynamically synthesizing all three attention branches.
- **Neural Routing Foundation (`core/routing/`):**
  - `RuleBasedRouter`: Deterministic routing based on task hints and operating modes.
  - `LearnedRouter`: Top-$k$ neural gating with softmax normalization and auxiliary load-balancing loss.
  - `DynamicRouter`: Hybrid policy router combining rule overrides and learned neural gating.
- **Hierarchical Modules (`neural_architecture/modules/`):**
  - `HierarchicalTransformerBlock`: Integrates pre-RMSNorm, MMA Attention, LayerScale residuals, and SwiGLU FFN.
  - `SpecializedExpert`: Dedicated domain FFN pathways (`GeneralReasoningExpert`, `PersonalAISystemExpert`).
- **Inference Harness (`neural_architecture/inference.py`):**
  - `InferenceEngine`: Validates input ranks, enforces vocabulary boundaries, prevents NaN/Inf generation, and performs greedy autoregressive token prediction.
- **Separated JAX Interface (`neural_architecture/jax_interface.py`):**
  - Pure-functional model contracts (`JAXModelInterface`, `JAXBackendEngine`) isolating JAX without cross-framework tensor transfers.
- **4 Comprehensive Technical Architecture Manuals in `docs/`:**
  - [`docs/CORE_AI_FOUNDATION.md`](docs/CORE_AI_FOUNDATION.md)
  - [`docs/CUSTOM_ATTENTION_DESIGN.md`](docs/CUSTOM_ATTENTION_DESIGN.md)
  - [`docs/NEURAL_ROUTING_DESIGN.md`](docs/NEURAL_ROUTING_DESIGN.md)
  - [`docs/MODEL_INITIALIZATION.md`](docs/MODEL_INITIALIZATION.md)
- **Unit Test Suites in `tests/unit/`:**
  - `test_neural_layers.py`, `test_custom_attention.py`, `test_neural_routing.py`, `test_neural_core.py`, `test_inference_engine.py`.

### Changed
- Expanded `README.md` to reflect Phase 03 core AI foundation deliverables, architecture diagrams, and quickstart commands.
- Updated `PHASE_STATUS.md` marking Phase 03 implementation complete (awaiting user review).
- Updated `DEVELOPMENT_LOG.md` with complete Phase 03 engineering records and test logs.

### Verified
- Executed `pytest tests/`: **44 tests passed in 1.49 seconds on CPU (100% success rate)**.

---

## [Phase-02] - 2026-11-06

### Added
- Complete modular directory and package structure across 17 architectural subsystems with documented `__init__.py` initializers.
- Software engineering foundation: `pyproject.toml` and `.env.example`.
- Unified exception hierarchy in `core/exceptions.py`.
- Type-safe configuration management in `core/config.py` and `configs/default_config.yaml`.
- Structured logging system in `core/logging.py`.
- Framework-agnostic neural engine contracts in `neural_architecture/interfaces.py`.
- Four-tier security permission model in `security/permissions.py`.
- Append-only security audit logger in `security/audit.py`.
- Threat sanitization engine in `security/sanitization.py`.
- Permission-controlled tool registry in `agent/tools/registry.py` and validator in `agent/permissions/validator.py`.
- 10 architectural manuals in `docs/`.

---

## [Phase-01] - 2026-11-06

### Added
- Comprehensive technical assessment report: [`docs/phase-01-hardware-assessment.md`](docs/phase-01-hardware-assessment.md).
- Hardware telemetry, runtime audit, compute feasibility, and GPU cluster recommendations.
