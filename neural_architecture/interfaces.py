"""
404 FOUNDERS — Neural Architecture Backend Interfaces
Establishes strict boundaries between PyTorch and JAX backends.
Frameworks are decoupled behind abstract interfaces to prevent cross-framework
leaks, invalid tensor casting, and redundant memory copies.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class BackendType(str, Enum):
    """Supported computational backends."""
    PYTORCH = "pytorch"
    JAX = "jax"
    CPU_REFERENCE = "cpu_reference"


@dataclass
class TensorMetadata:
    """Framework-agnostic metadata representing tensor shape and precision."""
    shape: Tuple[int, ...]
    dtype: str
    device: str
    requires_grad: bool = False


@dataclass
class ModelOutput:
    """Standardized prediction output structure across all backends."""
    logits: Any
    hidden_states: Optional[List[Any]] = None
    attentions: Optional[List[Any]] = None
    loss: Optional[float] = None
    metadata: Dict[str, Any] = None


class NeuralModuleInterface(ABC):
    """Abstract interface that all neural sub-modules (encoders, decoders, layers) must satisfy."""

    @property
    @abstractmethod
    def backend_type(self) -> BackendType:
        """Returns the active computational backend."""
        pass

    @property
    @abstractmethod
    def parameter_count(self) -> int:
        """Returns the total number of trainable parameters in this module."""
        pass

    @abstractmethod
    def forward(self, inputs: Any, **kwargs: Any) -> Any:
        """Execute the forward computation pass."""
        pass


class ModelBackendEngine(ABC):
    """
    Abstract Model Execution Engine.
    Implementations of this interface isolate PyTorch or JAX internally.
    The primary Python orchestration layer never directly imports framework-specific tensors.
    """

    @property
    @abstractmethod
    def backend_name(self) -> BackendType:
        """Identify which backend engine is active."""
        pass

    @abstractmethod
    def build_model(self, config: Dict[str, Any]) -> NeuralModuleInterface:
        """Construct model architecture graph with random weight initialization."""
        pass

    @abstractmethod
    def forward_pass(self, model: NeuralModuleInterface, batch: Dict[str, Any]) -> ModelOutput:
        """Perform forward inference or training computation pass."""
        pass

    @abstractmethod
    def compute_loss(self, outputs: ModelOutput, targets: Any) -> float:
        """Compute empirical training loss value."""
        pass

    @abstractmethod
    def save_checkpoint(self, model: NeuralModuleInterface, path: str) -> None:
        """Serialize model weights and optimizer state to persistent storage."""
        pass

    @abstractmethod
    def load_checkpoint(self, model: NeuralModuleInterface, path: str) -> None:
        """Restore model weights from a valid checkpoint file."""
        pass
