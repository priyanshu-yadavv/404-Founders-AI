# Changelog

All notable changes to the 404 FOUNDERS project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to Phase-based Development Governance.

## [Phase-05] - 2026-11-06

### Added
- **Local Workstation Hardware & Runtime Management (`infrastructure/local/`):**
  - `LocalHardwareInspector`: Safe read-only host introspection of CPU (cores, threads, AVX, AVX2, FMA3, AVX-512), RAM, swap, storage, virtualization (`/dev/kvm`), and GPU.
  - `LocalRuntimeManager`: Budgets system resources, enforcing 60% available RAM ceiling on swapless hosts and CPU worker limits to prevent Linux kernel OOM panics.
- **Cloud Provider Specifications & Hybrid Workload Routing (`infrastructure/cloud/`):**
  - `CloudProfileRegistry`: Reference market pricing across Lambda Labs, RunPod, CoreWeave, and AWS for Q4 2026.
  - `HybridWorkloadRouter`: Automates execution placement across local workstation CPU, cloud single-node Tier A dev, Tier B research, and Tier C supercluster.
- **GPU Cluster Architecture Specifications (`infrastructure/gpu_cluster/`):**
  - Complete typed definitions for `TIER_A_DEV` (1-2x RTX 4090/L40S PCIe 4.0), `TIER_B_RESEARCH` (1 Node 8x H100 80GB SXM5 NVLink 4), and `TIER_C_FOUNDATION` (8 Nodes 64x H100/H200 SXM5 3.2 Tbps InfiniBand NDR).
  - `InterconnectModel`: Ring AllReduce collective communication latency and transfer duration models.
  - `RailOptimizedFabric`: Models 8-way rail-optimized InfiniBand fabrics and NVSwitch meshes with dedicated rail switches per GPU index.
- **Distributed Training Infrastructure (`infrastructure/distributed/`):**
  - `ParallelismConfig` & `ParallelismEngine`: 4D parallelism distribution validation ($DP \times TP \times PP \times SP == \text{Total GPUs}$) and cluster-specific topology recommendations.
  - `GradientSyncPolicy` & `GradientSyncManager`: Gradient bucketing, accumulation steps, and communication-computation overlap.
  - `DistributedCheckpointManager`: Atomic non-blocking persistence (staging directory + rename), SHA-256 integrity verification per shard, `checkpoint_manifest.json`, and rolling retention preserving milestones.
- **Storage Tiering & Checkpoint Vault (`infrastructure/storage/`):**
  - `StorageTierManager`: Hierarchical Hot (NVMe scratch), Warm (Lustre/WEKA parallel fs), and Cold (S3 object storage) lifecycle management with LRU cache eviction and capacity quotas.
  - `CheckpointVault`: Versioned checkpoint cataloging with SHA-256 integrity verification and immutability locking for milestone releases.
- **Containers & Slurm Orchestration (`infrastructure/containers/`):**
  - `ContainerSpecGenerator`: Generates production CUDA 12.4 + PyTorch + JAX Dockerfiles and docker-compose configurations.
  - `SlurmSpecGenerator`: Multi-node Slurm SBATCH job submission generator with Pyxis/Enroot and torchrun integration.
- **Telemetry & Experiment Tracking (`infrastructure/monitoring/`):**
  - `MetricsCollector`: System telemetry, load averages, memory utilization, step throughput (tokens/sec, achieved TFLOPS, MFU %).
  - `ExperimentTracker`: Offline air-gapped JSONL logging, hyperparameter tracking, and TensorBoard integration.
- **Cluster Security & Zero-Trust Governance (`infrastructure/security/`):**
  - `ClusterSecurityManager`: RBAC authorization across `cluster_admin`, `ml_engineer`, `researcher`, `auditor_observer`.
  - Zero-trust SSH validation enforcing Ed25519 and rejecting legacy RSA keys.
  - Automated regex credential masking for HuggingFace, GitHub, OpenAI, and AWS tokens.
  - Immutable audit logging to `logs/security_audit.jsonl`.
- **Developer CLI Tooling (`scripts/`):**
  - `scripts/system_check.py`: Safe host hardware inspection and runtime budgeting.
  - `scripts/gpu_check.py`: GPU and CUDA compatibility inspection (gracefully handles CPU workstation).
  - `scripts/environment_check.py`: Toolchain audit (Python, PyTorch, JAX, compilers, Git, Docker).
  - `scripts/storage_check.py`: Storage tiering, disk space, and sequential I/O benchmark.
- **Configuration Templates (`configs/`):**
  - `configs/infrastructure/cluster_tier_a_dev.yaml`
  - `configs/infrastructure/cluster_tier_b_research.yaml`
  - `configs/infrastructure/cluster_tier_c_training.yaml`
  - `configs/training/fsdp_config.yaml`
  - `configs/training/distributed_mesh.yaml`
  - `configs/environments/pytorch_cuda_env.yaml`
  - `configs/environments/jax_cluster_env.yaml`
- **8 Technical Architecture Manuals in `docs/`:**
  - [`docs/GPU_CLUSTER_ARCHITECTURE.md`](docs/GPU_CLUSTER_ARCHITECTURE.md) (`DOC-INFRA-001`)
  - [`docs/DISTRIBUTED_TRAINING.md`](docs/DISTRIBUTED_TRAINING.md) (`DOC-INFRA-002`)
  - [`docs/PYTORCH_JAX_INFRASTRUCTURE.md`](docs/PYTORCH_JAX_INFRASTRUCTURE.md) (`DOC-INFRA-003`)
  - [`docs/CUDA_COMPATIBILITY.md`](docs/CUDA_COMPATIBILITY.md) (`DOC-INFRA-004`)
  - [`docs/STORAGE_ARCHITECTURE.md`](docs/STORAGE_ARCHITECTURE.md) (`DOC-INFRA-005`)
  - [`docs/INFRASTRUCTURE_SECURITY.md`](docs/INFRASTRUCTURE_SECURITY.md) (`DOC-INFRA-006`)
  - [`docs/TRAINING_COMPUTE_ESTIMATION.md`](docs/TRAINING_COMPUTE_ESTIMATION.md) (`DOC-INFRA-007`)
  - [`docs/INFRASTRUCTURE_COST_ANALYSIS.md`](docs/INFRASTRUCTURE_COST_ANALYSIS.md) (`DOC-INFRA-008`)
- **Automated Test Suites (25 New Tests in `tests/`):**
  - `tests/infrastructure/test_local_hardware.py` (3 tests)
  - `tests/infrastructure/test_cluster_architecture.py` (5 tests)
  - `tests/infrastructure/test_distributed_training.py` (5 tests)
  - `tests/infrastructure/test_storage_vault.py` (4 tests)
  - `tests/infrastructure/test_cluster_security.py` (4 tests)
  - `tests/configuration/test_infrastructure_configs.py` (4 tests)

### Changed
- Expanded `tests/architecture/test_architecture_consistency.py` to assert new infrastructure subpackages (`containers`, `distributed`, `storage`, `monitoring`, `security`) and all 28 technical manuals.
- Re-exported all new infrastructure classes in top-level `infrastructure/__init__.py`.
- Updated `README.md` with complete Phase 05 infrastructure specifications, cluster diagrams, and quickstart commands.
- Updated `PHASE_STATUS.md` and `DEVELOPMENT_LOG.md` preserving full records of Phases 01, 02, 03, and 04.

### Verified
- Executed `pytest tests/`: **98 tests passed in 1.88 seconds on CPU (100% success rate)**.

---

## [Phase-04] - 2026-11-06

### Added
- **Custom BPE Tokenizer (`tokenizer/`):**
  - `CustomBPETokenizer`: Unified model interface supporting training from text iterators, subword encoding, lossless decoding, and JSON serialization.
  - Character-level Byte Pair Encoding (non-byte-level BPE), eliminating byte-fragmentation for Indic and multilingual scripts.
  - `BPETrainer` (`tokenizer/bpe_trainer.py`): Pair frequency calculation ($F(p_1, p_2) = \sum C(w) \cdot \text{count}$) with deterministic tie-breaking.
  - `PreTokenizer` (`tokenizer/pre_tokenizer.py`): Multi-character code operator detection, scientific notation preservation, multilingual grapheme cluster handling, and explicit whitespace representation (` ` / `\u2581`).
  - `TextNormalizer` (`tokenizer/normalization.py`): Non-destructive Unicode NFC/NFKC canonical normalization, newline unification (`\r\n` -> `\n`), and control character sanitization.
  - `SpecialTokenRegistry` (`tokenizer/special_tokens.py`): 25 canonical special tokens (`<pad>`, `<unk>`, `<bos>`, `<eos>`, `<eot>`, `<sys_start>`, `<sys_end>`, `<user_start>`, `<user_end>`, `<asst_start>`, `<asst_end>`, `<thought>`, `</thought>`, `<tool_call>`, `<tool_result>`, `<image>`, `</image>`, `<audio>`, `</audio>`, `<video>`, `</video>`, `<spatial>`, `</spatial>`, `<code_start>`, `<code_end>`) with atomic regex matching and stable ID mapping.
  - `Vocabulary` (`tokenizer/vocabulary/manager.py`): Bi-directional token-to-ID and ID-to-token lookup with unknown token fallback.
  - `BPEEncoder` (`tokenizer/encoder.py`) & `BPEDecoder` (`tokenizer/decoder.py`): Priority-ranked iterative subword merging and exact round-trip text reconstruction.
  - `TokenizerSerializer` (`tokenizer/serialization.py`): Standalone JSON model serialization and separate `vocab.json` / `merges.txt` export.
  - `TokenizerEvaluator` (`tokenizer/evaluation/evaluator.py`): Quantitative benchmarking for compression ratio, tokens per word, fertility, OOV rate, and round-trip parity.
- **Data Preparation Pipeline (`training/datasets/`):**
  - `DatasetIngestor` (`training/datasets/ingestion/`): Ingestion across 9 domains (`general_text`, `code`, `mathematics`, `scientific`, `cybersecurity`, `multilingual`, `instruction`, `synthetic`, `multimodal_metadata`) supporting JSONL, CSV, and plain text.
  - `DataValidator` (`training/datasets/validation/`): Format validation, UTF-8 integrity, schema enforcement, corrupted line detection, and workstation file size bounds.
  - `DataCleaner` (`training/datasets/cleaning/`): Text sanitization, symbol-to-word ratio filtering, repetition loop rejection, and heuristic language/code identification.
  - `Deduplicator` (`training/datasets/deduplication/`): Content SHA-256 exact deduplication and 32-permutation MinHash near-duplicate detection with Jaccard estimation.
  - `DataGovernanceEngine` (`training/datasets/governance/`): Provenance tracking, license whitelist compliance (Apache 2.0, MIT, BSD, CC-BY, CC0, OpenData, Synthetic), and regex PII/secret scanning & redaction (AWS keys, GitHub tokens, OpenAI keys, SSH private keys, private IPs, emails, SSNs, credit cards).
  - `DatasetSplitter` (`training/datasets/splitting/`): Zero-leakage deterministic hash partitioning ($\text{SHA256}(x) \pmod{1000}$) across Train (80%), Val (10%), and Test (10%).
  - `DatasetManifest` (`training/datasets/manifests/`): Cryptographic manifests tracking split records, byte volumes, domain distributions, and per-file SHA-256 checksums with disk verification.
  - `DatasetStatistics` (`training/datasets/statistics/`): Descriptive corpus statistics, subword token estimates, and formatted Markdown audit reporting.
- **Developer CLI Tooling (`scripts/`):**
  - `scripts/train_tokenizer.py`: Train custom BPE models from corpus files.
  - `scripts/encode_text.py`: Encode strings to token IDs with optional BOS/EOS tags.
  - `scripts/decode_tokens.py`: Decode token IDs back into formatted text.
  - `scripts/inspect_dataset.py`: Comprehensive dataset validation, cleaning, governance audit, and statistical reporting.
- **Configuration Templates (`configs/`):**
  - `configs/tokenizer/default_tokenizer.yaml`
  - `configs/datasets/pipeline_config.yaml`
- **6 Technical Architecture Manuals in `docs/`:**
  - [`docs/CUSTOM_BPE_TOKENIZER.md`](docs/CUSTOM_BPE_TOKENIZER.md) (`DOC-TOK-001`)
  - [`docs/TOKENIZER_TRAINING.md`](docs/TOKENIZER_TRAINING.md) (`DOC-TOK-002`)
  - [`docs/MULTILINGUAL_TOKENIZATION.md`](docs/MULTILINGUAL_TOKENIZATION.md) (`DOC-TOK-003`)
  - [`docs/DATA_PIPELINE.md`](docs/DATA_PIPELINE.md) (`DOC-DATA-001`)
  - [`docs/DATA_GOVERNANCE.md`](docs/DATA_GOVERNANCE.md) (`DOC-DATA-002`)
  - [`docs/DATASET_LICENSE_POLICY.md`](docs/DATASET_LICENSE_POLICY.md) (`DOC-DATA-003`)
- **Automated Test Suites (29 New Tests in `tests/`):**
  - `tests/tokenizer/test_bpe_tokenizer.py` (8 tests)
  - `tests/tokenizer/test_multilingual_code.py` (5 tests)
  - `tests/data_pipeline/test_data_validation.py` (6 tests)
  - `tests/data_pipeline/test_cleaning_dedup.py` (5 tests)
  - `tests/data_pipeline/test_governance_splitting.py` (5 tests)

### Changed
- Expanded `tests/architecture/test_architecture_consistency.py` to verify all 8 dataset subpackages and 20 architectural manuals.
- Updated `.gitignore` to prevent raw dataset storage (`data/raw/`, `data/processed/`, `*.parquet`, archives) from being committed to repository.
- Expanded `README.md` to reflect Phase 04 Custom BPE Tokenizer and Data Pipeline components, documentation index, and quickstart commands.
- Updated `PHASE_STATUS.md` and `DEVELOPMENT_LOG.md` preserving full historical records of Phases 01, 02, and 03.

### Verified
- Executed `pytest tests/`: **73 tests passed in 1.74 seconds on CPU (100% success rate)**.

---

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
- Expanded `README.md` to reflect Phase 03 core AI foundation deliverables, architecture diagrams, and quickstart commands while preserving the complete Phase 02 repository tree.
- Updated `PHASE_STATUS.md` marking Phase 03 implementation complete (awaiting user review) while preserving Phase 01 and Phase 02 task checklists.
- Updated `DEVELOPMENT_LOG.md` with complete Phase 03 engineering records while preserving detailed Phase 01 and Phase 02 logs.

### Verified
- Executed `pytest tests/`: **44 tests passed in 1.49 seconds on CPU (100% success rate)**.

---

## [Phase-02] - 2026-11-06

### Added
- Complete modular directory and package structure across 17 architectural subsystems with documented `__init__.py` initializers.
- Software engineering foundation: `pyproject.toml` (PEP 517/518 build setup, ruff, mypy, pytest configs) and `.env.example`.
- Unified exception hierarchy in `core/exceptions.py` with structured error codes.
- Type-safe, environment-variable-aware configuration management in `core/config.py` and `configs/default_config.yaml`.
- Structured logging system in `core/logging.py` featuring JSON formatting, console formatting, and trace ID context.
- Framework-agnostic neural engine contracts in `neural_architecture/interfaces.py` cleanly isolating PyTorch and JAX.
- Four-tier security permission model in `security/permissions.py` (`READ_ONLY`, `PROTECTED`, `PRIVILEGED`, `DANGEROUS`).
- Append-only security audit logger in `security/audit.py` persisting structured audit records to `logs/security_audit.log`.
- Threat sanitization engine in `security/sanitization.py` scanning for prompt injection signatures and catastrophic shell patterns.
- Permission-controlled agent tool registry in `agent/tools/registry.py` and validation engine in `agent/permissions/validator.py`.
- 10 exhaustive technical architecture specifications in `docs/`:
  - [`docs/SYSTEM_ARCHITECTURE.md`](docs/SYSTEM_ARCHITECTURE.md)
  - [`docs/NEURAL_ARCHITECTURE.md`](docs/NEURAL_ARCHITECTURE.md)
  - [`docs/MULTIMODAL_ARCHITECTURE.md`](docs/MULTIMODAL_ARCHITECTURE.md)
  - [`docs/MEMORY_ARCHITECTURE.md`](docs/MEMORY_ARCHITECTURE.md)
  - [`docs/PERSONAL_AI_ARCHITECTURE.md`](docs/PERSONAL_AI_ARCHITECTURE.md)
  - [`docs/API_ARCHITECTURE.md`](docs/API_ARCHITECTURE.md)
  - [`docs/SECURITY_ARCHITECTURE.md`](docs/SECURITY_ARCHITECTURE.md)
  - [`docs/DATA_ARCHITECTURE.md`](docs/DATA_ARCHITECTURE.md)
  - [`docs/INFRASTRUCTURE_ARCHITECTURE.md`](docs/INFRASTRUCTURE_ARCHITECTURE.md)
  - [`docs/DEVELOPMENT_STANDARDS.md`](docs/DEVELOPMENT_STANDARDS.md)
- Automated test suite in `tests/` covering unit tests, security permissions, and architecture consistency.

### Changed
- Expanded `README.md` to reflect complete Phase 02 repository tree, operating modes, architectural tenets, documentation links, and quickstart commands.
- Updated `PHASE_STATUS.md` marking Phase 02 implementation complete (awaiting user review).
- Updated `DEVELOPMENT_LOG.md` recording technical actions, framework decoupling, and test validation.

### Verified
- Executed `pytest tests/`: **23 tests passed cleanly in 0.06 seconds (100% success rate)**.

---

## [Phase-01] - 2026-11-06

### Added
- Comprehensive technical assessment report: [`docs/phase-01-hardware-assessment.md`](docs/phase-01-hardware-assessment.md).
- Detailed hardware telemetry covering CPU (Intel i5-8365U, 4C/8T, AVX2, FMA3), RAM (15.4 GiB, 5.17 GiB free, 0B swap), GPU (Intel UHD 620 UMA, 0 VRAM), Storage (NVMe 110GB, 43GB free), OS (Kali 2026.3, Linux 7.1.5), Networking (Intel GbE + Wireless-AC), and Virtualization (VT-x, `/dev/kvm`).
- Toolchain and runtime audit identifying installed compilers/runtimes and missing utilities (`cmake`, `rustc`, `cargo`, `docker`, `gh`, `jupyter`).
- Python framework inspection for PyTorch, JAX, Transformers, and CUDA compatibility.
- Compute feasibility analysis establishing boundaries between local laptop capabilities and GPU cluster requirements.
- Three enterprise GPU cluster infrastructure architectures (Scenario A: 4x–8x RTX 4090, Scenario B: 8x H100 SXM5, Scenario C: 32x–64x H100/H200).
- Standardized `.gitignore` protecting secrets, environments, large weights, and temporary artifacts.
- Phase governance documents: `PHASE_STATUS.md` and `DEVELOPMENT_LOG.md`.

### Changed
- Expanded `README.md` with full project architecture, hardware baseline, roadmap, and links to technical assessment documentation.
- Synchronized local repository branch `main` with upstream `origin/main`.
