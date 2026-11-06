"""
404 FOUNDERS — FastAPI REST API Pydantic Schemas
Defines request and response data contracts for health checks, telemetry,
tokenizer operations, neural core inference, and security validation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check endpoint response schema."""

    status: str = Field("healthy", description="Operational status of the API server")
    version: str = Field("0.5.0", description="404 FOUNDERS version")
    operating_mode: str = Field(..., description="System operating mode (general, personal, hybrid)")
    compute_backend: str = Field(..., description="Active compute execution backend (cpu, cuda, jax)")
    neural_core_ready: bool = Field(..., description="Whether the neural core is initialized")
    tokenizer_ready: bool = Field(..., description="Whether the Custom BPE Tokenizer is loaded")
    model_parameter_count: int = Field(..., description="Parameter count of current neural core")
    uptime_seconds: float = Field(..., description="Server uptime in seconds")


class TelemetryResponse(BaseModel):
    """Host system telemetry and resource budgeting response."""

    cpu_model: str
    physical_cores: int
    logical_threads: int
    has_avx2: bool
    total_ram_gb: float
    available_ram_gb: float
    total_swap_gb: float
    root_free_gb: float
    has_kvm: bool
    safe_memory_budget_gb: float
    cpu_thread_limit: int
    execution_mode: str


class PhaseStatusResponse(BaseModel):
    """Project phase-gate status response."""

    current_phase: str
    current_phase_status: str
    completed_phases: List[str]
    last_updated: str


class TokenizeRequest(BaseModel):
    """Text tokenization request."""

    text: str = Field(..., min_length=1, description="Input text to encode into subword tokens")
    add_bos: bool = Field(True, description="Prepend beginning-of-sequence token <bos>")
    add_eos: bool = Field(False, description="Append end-of-sequence token <eos>")


class TokenizeResponse(BaseModel):
    """Tokenization result response."""

    text: str
    tokens: List[str]
    ids: List[int]
    token_count: int
    vocab_size: int


class DecodeRequest(BaseModel):
    """Token decoding request."""

    ids: List[int] = Field(..., description="List of integer token IDs to reconstruct")
    skip_special_tokens: bool = Field(True, description="Omit special tags from output")


class DecodeResponse(BaseModel):
    """Token decoding result response."""

    ids: List[int]
    text: str


class InferenceRequest(BaseModel):
    """Neural forward inference request."""

    prompt: str = Field(..., min_length=1, description="Input prompt text")
    max_new_tokens: int = Field(5, ge=1, le=64, description="Number of tokens to generate greedily")
    mode: Optional[str] = Field("general", description="Inference mode (general, personal)")


class InferenceResponse(BaseModel):
    """Neural forward inference response computed from actual model weights."""

    prompt: str
    prompt_ids: List[int]
    generated_ids: List[int]
    generated_tokens: List[str]
    generated_text: str
    total_parameters: int
    is_random_initialization: bool = True
    notice: str = "Weights are from random Gaussian initialization (zero pretrained weights, pretraining planned in Phase 06)."
    latency_ms: float


class CommandValidationRequest(BaseModel):
    """Shell command security audit request."""

    command: str = Field(..., min_length=1, description="Shell command string to validate")


class CommandValidationResponse(BaseModel):
    """Shell command security audit response."""

    command: str
    is_safe: bool
    status: str
    required_tier: str
    detail: Optional[str] = None


class PromptSafetyRequest(BaseModel):
    """Prompt injection inspection request."""

    text: str = Field(..., min_length=1, description="User prompt text to scan for injection signatures")


class PromptSafetyResponse(BaseModel):
    """Prompt injection inspection response."""

    text: str
    is_safe: bool
    detected_signatures: List[str]
