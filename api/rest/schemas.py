"""
404 FOUNDERS — FastAPI REST API Pydantic Schemas
Defines request and response data contracts for health checks, telemetry,
tokenizer operations, neural core inference, and security validation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
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


# ==========================================
# PHASE 08 — Multimodal Intelligence Schemas
# ==========================================

class MultimodalProcessRequest(BaseModel):
    """Unified multimodal analysis request supporting text, image, audio, video, and documents."""
    text: Optional[str] = Field(None, description="Prompt text or question")
    image_base64: Optional[str] = Field(None, description="Base64-encoded image (PNG, JPEG, WEBP, BMP)")
    audio_base64: Optional[str] = Field(None, description="Base64-encoded audio (WAV, MP3, FLAC, OGG)")
    video_base64: Optional[str] = Field(None, description="Base64-encoded video (MP4, WEBM, MOV)")
    document_base64: Optional[str] = Field(None, description="Base64-encoded document (PDF, DOCX, CSV, JSON, TXT, MD)")
    filename_hints: Optional[Dict[str, str]] = Field(default_factory=dict, description="Filename or MIME hints")
    perform_fusion: bool = Field(True, description="Whether to execute multi-stage multimodal fusion")
    fusion_stage: str = Field("EARLY", description="Fusion stage: EARLY, INTERMEDIATE, or LATE")
    synthesize_speech: bool = Field(False, description="Generate spoken audio response (TTS)")


class MultimodalProcessResponse(BaseModel):
    """Consolidated multimodal analysis response."""
    primary_modality: str
    active_modalities: List[str]
    is_multimodal: bool
    text_summary: Optional[str] = None
    image_caption: Optional[str] = None
    audio_summary: Optional[str] = None
    speech_transcript: Optional[str] = None
    speech_audio_base64_uri: Optional[str] = None
    video_summary: Optional[str] = None
    document_summary: Optional[str] = None
    document_safe: Optional[bool] = None
    fusion_active_modalities: Optional[List[str]] = None
    combined_summary: str


class ImageProcessRequest(BaseModel):
    """Image intelligence inspection request."""
    image_base64: str = Field(..., min_length=16, description="Base64-encoded image payload")
    target_size: Optional[Tuple[int, int]] = Field((224, 224), description="Target spatial resolution")


class ImageProcessResponse(BaseModel):
    """Image intelligence analysis result."""
    format: str
    width: int
    height: int
    aspect_ratio: float
    channels: int
    patch_count: int
    caption: str
    reasoning_summary: str


class AudioProcessRequest(BaseModel):
    """Audio intelligence inspection request."""
    audio_base64: str = Field(..., min_length=16, description="Base64-encoded audio payload")


class AudioProcessResponse(BaseModel):
    """Audio intelligence analysis result."""
    format: str
    duration_seconds: float
    sample_rate: int
    channels: int
    rms_energy: float
    estimated_snr_db: float
    is_silent: bool
    summary: str


class SpeechRecognizeRequest(BaseModel):
    """Speech-to-text recognition request."""
    audio_base64: str = Field(..., min_length=16, description="Base64-encoded speech audio payload")
    language_hint: Optional[str] = Field("en", description="Optional language code (en, hi)")


class SpeechRecognizeResponse(BaseModel):
    """Speech-to-text transcription result."""
    full_transcript: str
    detected_language: str
    overall_confidence: float
    duration_seconds: float
    segments_count: int


class SpeechSynthesizeRequest(BaseModel):
    """Text-to-speech synthesis request."""
    text: str = Field(..., min_length=1, description="Text string to synthesize into spoken audio")
    language: str = Field("en", description="Target language (en, hi)")
    voice_id: str = Field("default_neutral", description="Voice profile identifier")
    speed_factor: float = Field(1.0, ge=0.5, le=2.0, description="Playback speed multiplier")
    pitch_hz: float = Field(220.0, ge=100.0, le=450.0, description="Baseline vocal pitch frequency")


class SpeechSynthesizeResponse(BaseModel):
    """Text-to-speech audio result."""
    text: str
    language: str
    duration_seconds: float
    sample_rate: int
    audio_base64_uri: str
    summary: str


class DocumentProcessRequest(BaseModel):
    """Document intelligence extraction request."""
    document_base64: str = Field(..., min_length=4, description="Base64-encoded document payload")
    filename: str = Field(..., min_length=1, description="Original filename with extension (.pdf, .docx, .csv, etc.)")


class DocumentProcessResponse(BaseModel):
    """Document intelligence analysis result."""
    format: str
    page_count: int
    word_count: int
    chunks_count: int
    has_tables: bool
    is_safe: bool
    detected_injection_risks: List[str]
    summary: str


class MultimodalFuseRequest(BaseModel):
    """Multimodal fusion tensor synthesis request."""
    active_modalities: List[str] = Field(..., min_length=1, description="Modalities to fuse (TEXT, IMAGE, AUDIO, VIDEO)")
    fusion_stage: str = Field("EARLY", description="Fusion stage: EARLY, INTERMEDIATE, or LATE")


class MultimodalFuseResponse(BaseModel):
    """Multimodal fusion tensor result."""
    fusion_stage: str
    active_modalities: List[str]
    missing_modalities: List[str]
    fused_tensor_shape: List[int]
    modality_weights: Dict[str, float]


# ==============================================================================
# PHASE 09 — ADVANCED MEMORY & CONTROLLED LEARNING SCHEMAS
# ==============================================================================


class MemoryRecordCreateRequest(BaseModel):
    """Save a record to long-term or knowledge memory."""
    user_id: str = Field(..., min_length=1, description="Tenant user ID")
    content: str = Field(..., min_length=1, description="Memory text content")
    summary: Optional[str] = Field(None, description="Optional concise summary")
    memory_layer: str = Field("LONG_TERM", description="Target layer (LONG_TERM or KNOWLEDGE)")
    importance: float = Field(0.5, ge=0.0, le=1.0, description="Importance weighting")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Confidence score")
    is_confirmed_by_user: bool = Field(False, description="Whether explicitly verified by user")
    source_type: str = Field("user_explicit", description="Source provenance attribution")
    tags: List[str] = Field(default_factory=list, description="Categorical tags")


class MemoryRecordResponse(BaseModel):
    """Memory record metadata."""
    record_id: str
    user_id: str
    content: str
    summary: str
    importance: float
    confidence: float
    is_confirmed_by_user: bool
    version: int
    parent_version_id: Optional[str]
    source_type: str
    tags: List[str]
    created_at: str
    updated_at: str
    status: str


class MemoryRecordUpdateRequest(BaseModel):
    """Update an existing memory record."""
    user_id: str = Field(..., min_length=1, description="Tenant user ID")
    new_content: Optional[str] = Field(None, description="Updated content")
    new_summary: Optional[str] = Field(None, description="Updated summary")
    importance: Optional[float] = Field(None, ge=0.0, le=1.0)
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    is_confirmed_by_user: Optional[bool] = None
    tags: Optional[List[str]] = None


class ShortTermMessageRequest(BaseModel):
    """Add a message turn to short-term conversational context."""
    user_id: str = Field(..., min_length=1)
    session_id: str = Field(..., min_length=1)
    role: str = Field("user", description="Role: user, assistant, system")
    content: str = Field(..., min_length=1)


class ShortTermMessageResponse(BaseModel):
    """Conversational message turn."""
    message_id: str
    user_id: str
    session_id: str
    role: str
    content: str
    timestamp: str
    token_count_estimate: int


class WorkingTaskStartRequest(BaseModel):
    """Initialize or resume an active working task."""
    session_id: str = Field(..., min_length=1)
    task_id: str = Field(..., min_length=1)
    task_name: str = Field(..., min_length=1)
    objectives: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    initial_results: Dict[str, Any] = Field(default_factory=dict)


class WorkingTaskResponse(BaseModel):
    """Working task representation."""
    session_id: str
    task_id: str
    task_name: str
    active_objectives: List[str]
    intermediate_results: Dict[str, Any]
    dependencies: List[str]
    pending_actions: List[Dict[str, Any]]
    status: str
    created_at: str
    updated_at: str


class WorkingTaskUpdateRequest(BaseModel):
    """Update progress for an active working task."""
    session_id: str = Field(..., min_length=1)
    intermediate_results: Optional[Dict[str, Any]] = None
    pending_actions: Optional[List[Dict[str, Any]]] = None
    active_objectives: Optional[List[str]] = None
    status: Optional[str] = None


class EpisodicEventRequest(BaseModel):
    """Record an episodic event log."""
    user_id: str = Field(..., min_length=1)
    event_description: str = Field(..., min_length=1)
    session_id: Optional[str] = None
    task_id: Optional[str] = None
    context_summary: Optional[str] = None
    outcome: Optional[str] = None
    related_memory_ids: List[str] = Field(default_factory=list)
    user_feedback: Optional[str] = None


class EpisodicEventResponse(BaseModel):
    """Episodic event log representation."""
    event_id: str
    user_id: str
    session_id: Optional[str]
    task_id: Optional[str]
    event_description: str
    context_summary: Optional[str]
    outcome: Optional[str]
    related_memory_ids: List[str]
    user_feedback: Optional[str]
    timestamp: str


class UserPreferenceSetRequest(BaseModel):
    """Set or update user preference."""
    user_id: str = Field(..., min_length=1)
    preference_key: str = Field(..., min_length=1)
    preference_val: str = Field(..., min_length=1)
    is_explicit: bool = Field(True)


class MemoryRetrievalRequest(BaseModel):
    """Multi-layer hybrid memory retrieval request."""
    user_id: str = Field(..., min_length=1)
    query: str = Field(..., description="Query terms for lexical/semantic matching")
    memory_layer: Optional[str] = Field(None, description="Optional layer filter (LONG_TERM, KNOWLEDGE, SHORT_TERM)")
    min_confidence: float = Field(0.0, ge=0.0, le=1.0)
    limit: int = Field(10, ge=1, le=50)


class ScoredMemoryResponse(BaseModel):
    """Retrieved memory with scoring breakdown."""
    record_id: str
    user_id: str
    memory_layer: str
    content: str
    summary: str
    final_score: float
    lexical_score: float
    recency_score: float
    importance_score: float
    confidence_score: float
    source_attribution: str
    created_at: str
    updated_at: str


class ConsolidationRequest(BaseModel):
    """Trigger memory consolidation and conflict detection."""
    user_id: str = Field(..., min_length=1)


class ConflictReportItem(BaseModel):
    """Detected contradiction report."""
    conflict_id: str
    existing_record_id: str
    conflicting_record_id: str
    subject_area: str
    existing_content: str
    conflicting_content: str
    resolution_status: str
    detected_at: str


class ConsolidationResponse(BaseModel):
    """Consolidation pass summary."""
    user_id: str
    duplicates_resolved: int
    conflicts_detected: List[ConflictReportItem]
    records_merged: int
    consolidated_at: str


class ContextAssemblyRequest(BaseModel):
    """Request to assemble dynamic prompt context from multi-layer memory."""
    user_id: str = Field(..., min_length=1)
    session_id: str = Field(..., min_length=1)
    current_query: str = Field(..., min_length=1)
    token_budget: int = Field(3000, ge=256, le=16384)


class ContextAssemblyResponse(BaseModel):
    """Assembled multi-layer context output."""
    full_context_text: str
    personalization_directive: str
    active_tasks_count: int
    retrieved_memories_count: int
    conversation_turns_count: int
    estimated_tokens: int
    budget_limit: int


class FeedbackSubmitRequest(BaseModel):
    """User feedback submission request."""
    user_id: str = Field(..., min_length=1)
    feedback_type: str = Field("POSITIVE", description="POSITIVE, NEGATIVE, CORRECTION, ERROR_REPORT")
    response_id: Optional[str] = None
    task_id: Optional[str] = None
    rating: Optional[int] = Field(None, ge=1, le=5)
    suggested_correction: Optional[str] = None
    category: str = Field("general", description="factual_accuracy, code_syntax, hallucination, formatting, etc.")
    comment: Optional[str] = None


class FeedbackResponse(BaseModel):
    """Feedback record schema."""
    feedback_id: str
    user_id: str
    response_id: Optional[str]
    task_id: Optional[str]
    feedback_type: str
    rating: Optional[int]
    suggested_correction: Optional[str]
    category: str
    comment: Optional[str]
    status: str
    created_at: str


class FeedbackValidateRequest(BaseModel):
    """Validate or reject feedback entry."""
    is_valid: bool
    notes: Optional[str] = None


class LearningJobCreateRequest(BaseModel):
    """Create a 10-stage continual learning pipeline job."""
    target_version: str = Field(..., min_length=1, description="Target model version identifier")


class LearningJobResponse(BaseModel):
    """Continual learning pipeline job status."""
    job_id: str
    current_stage: str
    status: str
    target_version: str
    dataset_manifest_hash: Optional[str]
    stage_history_count: int
    is_approved: bool
    created_at: str
    updated_at: str


class LearningJobApproveRequest(BaseModel):
    """Governance sign-off approval request."""
    approver: str = Field(..., min_length=1)
    approved: bool
    reason: str = Field("", description="Governance approval explanation")
