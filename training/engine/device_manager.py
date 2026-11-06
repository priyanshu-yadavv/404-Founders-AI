"""
404 FOUNDERS — Device & Execution Hardware Manager
Safely probes local hardware, manages compute devices (CPU, CUDA, MPS),
and configures mixed-precision autocast execution contexts without crashing on CPU hosts.
"""

from __future__ import annotations

from contextlib import contextmanager, nullcontext
from typing import Any, Generator, Optional
import torch

from training.configs.model_config import PrecisionType


class DeviceManager:
    """
    Hardware abstraction layer resolving safe compute devices and precision contexts.
    """

    def __init__(self, requested_device: str = "cpu", requested_precision: str = "fp32") -> None:
        self.device = self._resolve_device(requested_device)
        self.precision = PrecisionType(requested_precision)
        self.dtype = self._resolve_dtype(self.precision)

    def _resolve_device(self, requested: str) -> torch.device:
        """Resolve valid execution device with graceful CPU fallback."""
        req_clean = requested.lower().strip()
        if "cuda" in req_clean:
            if torch.cuda.is_available():
                return torch.device(req_clean)
            return torch.device("cpu")
        elif "mps" in req_clean:
            if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return torch.device("mps")
            return torch.device("cpu")
        return torch.device("cpu")

    def _resolve_dtype(self, precision: PrecisionType) -> torch.dtype:
        """Resolve target floating-point dtype."""
        if precision == PrecisionType.BF16:
            # Check if bfloat16 is supported on CPU / GPU
            if self.device.type == "cuda" and torch.cuda.is_bf16_supported():
                return torch.bfloat16
            return torch.bfloat16
        elif precision == PrecisionType.FP16:
            return torch.float16
        return torch.float32

    @contextmanager
    def autocast_context(self) -> Generator[None, None, None]:
        """
        Yield appropriate mixed-precision autocast context manager.
        On CPU, autocast is enabled for bfloat16 if requested, otherwise nullcontext.
        """
        if self.device.type == "cuda" and self.precision in (PrecisionType.BF16, PrecisionType.FP16):
            with torch.autocast(device_type="cuda", dtype=self.dtype):
                yield
        elif self.device.type == "cpu" and self.precision == PrecisionType.BF16:
            with torch.autocast(device_type="cpu", dtype=torch.bfloat16):
                yield
        else:
            with nullcontext():
                yield

    def to_device(self, tensor_or_module: Any) -> Any:
        """Transfer tensor or nn.Module to managed device."""
        if hasattr(tensor_or_module, "to"):
            return tensor_or_module.to(self.device)
        return tensor_or_module

    @property
    def is_cuda(self) -> bool:
        return self.device.type == "cuda"

    @property
    def device_name(self) -> str:
        if self.is_cuda:
            return torch.cuda.get_device_name(self.device)
        return "Host CPU"
