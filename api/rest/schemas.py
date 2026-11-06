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


# ==========================================
# PHASE 07 — Intelligence Module API Schemas
# ==========================================

class IntelligenceQueryRequest(BaseModel):
    """General query request routed via the Central Intelligence Router."""
    query: str = Field(..., min_length=1, description="Natural language problem or task statement")
    force_engine: Optional[str] = Field(None, description="Force routing to a specific intelligence engine")
    context_hints: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Contextual hints or parameters")


class IntelligenceQueryResponse(BaseModel):
    """Consolidated response from Central Intelligence Router dispatch."""
    query: str
    primary_engine: str
    secondary_engines: List[str]
    intent_confidence: float
    combined_summary: str
    conflicts_detected: List[str]
    is_fallback_used: bool


class LogicalReasoningRequest(BaseModel):
    """Logical deduction, decomposition, and contradiction analysis request."""
    problem: str = Field(..., min_length=1, description="Logical problem or proposition to analyze")
    premises: Optional[List[str]] = Field(default_factory=list, description="Explicit premises or given facts")
    candidates: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Candidate approaches to compare")
    constraints: Optional[List[str]] = Field(default_factory=list, description="Active boundary constraints")


class LogicalReasoningResponse(BaseModel):
    """Logical analysis report."""
    problem: str
    decomposed_steps: List[str]
    assumptions: List[str]
    premises_count: int
    contradictions_count: int
    conclusion: str
    epistemic_uncertainty: float
    summary: str


class MathReasoningRequest(BaseModel):
    """Deterministic mathematical computation request."""
    expression: str = Field(..., min_length=1, description="Mathematical expression or equation to compute")
    operation_type: str = Field("arithmetic", description="Operation category: arithmetic, linear, quadratic, stats")


class MathReasoningResponse(BaseModel):
    """Mathematical computation result."""
    domain: str
    query_description: str
    exact_solution: Any
    numerical_approximation: Optional[float]
    is_verified: bool
    summary: str


class CodingAnalysisRequest(BaseModel):
    """Defensive code inspection and AST analysis request."""
    code: str = Field(..., min_length=1, description="Source code snippet to analyze")
    language: Optional[str] = Field(None, description="Optional programming language hint")


class CodingAnalysisResponse(BaseModel):
    """Code analysis, complexity evaluation, and sandbox notice report."""
    language: str
    is_valid_syntax: bool
    functions: List[str]
    classes: List[str]
    estimated_time_complexity: str
    estimated_space_complexity: str
    issues_count: int
    sandbox_execution_permitted: bool = False
    sandbox_warning: str
    explanation: str


class SecurityAuditRequest(BaseModel):
    """Defensive cybersecurity inspection request."""
    query: str = Field("Defensive Security Audit", description="Audit query or scope")
    logs: Optional[List[str]] = Field(default_factory=list, description="Log lines to inspect for attack patterns")
    filename: Optional[str] = Field(None, description="File name for artifact scan")
    file_content: Optional[str] = Field(None, description="File content to inspect for malicious patterns or high entropy")


class SecurityAuditResponse(BaseModel):
    """Defensive cybersecurity audit report."""
    target_type: str
    threats_detected_count: int
    threat_categories: List[str]
    overall_risk_level: str
    hardening_recommendations: List[str]
    is_defensive_compliant: bool
    defensive_policy_notice: str


class PlanningRequest(BaseModel):
    """Hierarchical goal decomposition and DAG planning request."""
    objective: str = Field(..., min_length=1, description="High-level objective to decompose into an execution DAG")
    subtasks: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Optional explicit subtasks")


class PlanningResponse(BaseModel):
    """Sequenced execution plan and risk classification report."""
    objective: str
    total_tasks: int
    task_order: List[str]
    requires_human_approval: bool
    pending_approvals_count: int
    summary: str


class SelfEvaluationRequest(BaseModel):
    """Self-evaluation and factual error detection request."""
    query: str = Field(..., min_length=1, description="Original query or task prompt")
    candidate_output: str = Field(..., min_length=1, description="Candidate response text to evaluate")
    context_facts: Optional[List[str]] = Field(default_factory=list, description="Known context facts")


class SelfEvaluationResponse(BaseModel):
    """Output consistency, contradiction check, and epistemic modesty report."""
    is_valid: bool
    quality_score: float
    epistemic_modesty_status: str
    findings_count: int
    contains_contradictions: bool
    missing_elements: List[str]
    summary: str
