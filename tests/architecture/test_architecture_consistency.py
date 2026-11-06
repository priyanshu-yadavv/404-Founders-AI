"""
404 FOUNDERS — Architecture Consistency & Workspace Integrity Tests
"""

import importlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

EXPECTED_PACKAGES = [
    "core",
    "core.intelligence",
    "core.reasoning",
    "core.attention",
    "core.routing",
    "core.context",
    "core.orchestration",
    "neural_architecture",
    "neural_architecture.layers",
    "neural_architecture.modules",
    "neural_architecture.encoders",
    "neural_architecture.decoders",
    "neural_architecture.fusion",
    "neural_architecture.research",
    "memory",
    "memory.short_term",
    "memory.long_term",
    "memory.knowledge",
    "memory.episodic",
    "memory.retrieval",
    "memory.consolidation",
    "multimodal",
    "multimodal.text",
    "multimodal.vision",
    "multimodal.audio",
    "multimodal.video",
    "multimodal.documents",
    "tokenizer",
    "tokenizer.training",
    "tokenizer.vocabulary",
    "tokenizer.evaluation",
    "learning",
    "learning.supervised",
    "learning.self_supervised",
    "learning.reinforcement",
    "learning.continual",
    "learning.meta_learning",
    "training",
    "training.datasets",
    "training.preprocessing",
    "training.experiments",
    "training.checkpoints",
    "training.evaluation",
    "personal_ai",
    "personal_ai.system_monitor",
    "personal_ai.coding_assistant",
    "personal_ai.cybersecurity",
    "personal_ai.network_analysis",
    "personal_ai.automation",
    "agent",
    "agent.planner",
    "agent.tools",
    "agent.permissions",
    "agent.execution",
    "api",
    "api.rest",
    "api.websocket",
    "api.grpc",
    "infrastructure",
    "infrastructure.local",
    "infrastructure.cloud",
    "infrastructure.gpu_cluster",
    "infrastructure.deployment",
    "database",
    "security",
    "scripts",
]

EXPECTED_DOCS = [
    "docs/SYSTEM_ARCHITECTURE.md",
    "docs/NEURAL_ARCHITECTURE.md",
    "docs/MULTIMODAL_ARCHITECTURE.md",
    "docs/MEMORY_ARCHITECTURE.md",
    "docs/PERSONAL_AI_ARCHITECTURE.md",
    "docs/API_ARCHITECTURE.md",
    "docs/SECURITY_ARCHITECTURE.md",
    "docs/DATA_ARCHITECTURE.md",
    "docs/INFRASTRUCTURE_ARCHITECTURE.md",
    "docs/DEVELOPMENT_STANDARDS.md",
]


def test_package_directories_and_init_files_exist() -> None:
    """Verify that all architectural packages exist with non-empty __init__.py files."""
    for pkg in EXPECTED_PACKAGES:
        rel_path = pkg.replace(".", "/")
        pkg_dir = REPO_ROOT / rel_path
        init_file = pkg_dir / "__init__.py"
        assert pkg_dir.is_dir(), f"Missing architectural package directory: {rel_path}"
        assert init_file.is_file(), f"Missing __init__.py in package: {rel_path}"
        assert len(init_file.read_text(encoding="utf-8").strip()) > 0, f"Empty __init__.py in: {rel_path}"


def test_clean_package_imports() -> None:
    """Verify that all core architectural modules import cleanly without errors."""
    for pkg in EXPECTED_PACKAGES:
        module = importlib.import_module(pkg)
        assert module is not None, f"Failed to import package: {pkg}"


def test_documentation_files_exist_and_non_empty() -> None:
    """Verify that all 10 architectural specification documents exist and have content."""
    for doc_rel in EXPECTED_DOCS:
        doc_path = REPO_ROOT / doc_rel
        assert doc_path.is_file(), f"Missing architectural specification document: {doc_rel}"
        content = doc_path.read_text(encoding="utf-8")
        assert len(content.strip()) > 100, f"Document appears empty or too short: {doc_rel}"


def test_neural_interfaces_instantiable() -> None:
    """Verify neural architecture abstract interfaces can be referenced and implemented."""
    from neural_architecture.interfaces import (
        BackendType,
        NeuralModuleInterface,
        ModelOutput,
        TensorMetadata,
    )

    meta = TensorMetadata(shape=(2, 128, 768), dtype="float32", device="cpu")
    assert meta.shape == (2, 128, 768)
    assert meta.device == "cpu"

    output = ModelOutput(logits=[0.1, 0.9], loss=0.45)
    assert output.loss == 0.45
    assert BackendType.PYTORCH == "pytorch"
    assert BackendType.JAX == "jax"
