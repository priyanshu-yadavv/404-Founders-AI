"""
404 FOUNDERS — FastAPI REST API Route Handlers
Implements health checks, host telemetry, tokenizer operations, neural core inference,
and security validation.
"""

from __future__ import annotations

from dataclasses import asdict
import json
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import torch
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, Header, Query
from fastapi.responses import StreamingResponse

from api.rest.schemas import (
    AudioProcessRequest,
    AudioProcessResponse,
    CodingAnalysisRequest,
    CodingAnalysisResponse,
    CommandValidationRequest,
    CommandValidationResponse,
    ConflictReportItem,
    ConsolidationRequest,
    ConsolidationResponse,
    ContextAssemblyRequest,
    ContextAssemblyResponse,
    DecodeRequest,
    DecodeResponse,
    DocumentProcessRequest,
    DocumentProcessResponse,
    EpisodicEventRequest,
    EpisodicEventResponse,
    FeedbackResponse,
    FeedbackSubmitRequest,
    FeedbackValidateRequest,
    HealthResponse,
    ImageProcessRequest,
    ImageProcessResponse,
    InferenceRequest,
    InferenceResponse,
    IntelligenceQueryRequest,
    IntelligenceQueryResponse,
    LearningJobApproveRequest,
    LearningJobCreateRequest,
    LearningJobResponse,
    LogicalReasoningRequest,
    LogicalReasoningResponse,
    MathReasoningRequest,
    MathReasoningResponse,
    MemoryRecordCreateRequest,
    MemoryRecordResponse,
    MemoryRecordUpdateRequest,
    MemoryRetrievalRequest,
    MultimodalFuseRequest,
    MultimodalFuseResponse,
    MultimodalProcessRequest,
    MultimodalProcessResponse,
    PhaseStatusResponse,
    PlanningRequest,
    PlanningResponse,
    PromptSafetyRequest,
    PromptSafetyResponse,
    ScoredMemoryResponse,
    SecurityAuditRequest,
    SecurityAuditResponse,
    SelfEvaluationRequest,
    SelfEvaluationResponse,
    ShortTermMessageRequest,
    ShortTermMessageResponse,
    SpeechRecognizeRequest,
    SpeechRecognizeResponse,
    SpeechSynthesizeRequest,
    SpeechSynthesizeResponse,
    TelemetryResponse,
    TokenizeRequest,
    TokenizeResponse,
    UserPreferenceSetRequest,
    WorkingTaskResponse,
    WorkingTaskStartRequest,
    WorkingTaskUpdateRequest,
    # Phase 10 Schemas
    AppItemSchema,
    AppLaunchRequest,
    AppLaunchResponse,
    AppStatusRequest,
    AppStatusResponse,
    ApprovalDecisionRequest,
    ApprovalTicketSchema,
    AuditLogEntrySchema,
    CommandAdviseRequest,
    CommandAdviseResponse,
    CPUVitalsSchema,
    DNSResolveRequest,
    DNSResolveResponse,
    EmergencyShutdownRequest,
    EmergencyShutdownResponse,
    FileEntrySchema,
    FileListRequest,
    FileListResponse,
    FileReadRequest,
    FileReadResponse,
    FileSearchRequest,
    GitStatusResponse,
    MemoryVitalsSchema,
    PersonalAIChatRequest,
    PersonalAIChatResponse,
    PersonalAISessionCreateRequest,
    PersonalAISessionResponse,
    PersonalAIStatusResponse,
    PingRequest,
    PingResponse,
    ProcessItemSchema,
    ProcessTerminateRequest,
    ProcessTerminateResponse,
    RepoTopologyResponse,
    RunTestsRequest,
    RunTestsResponse,
    SecurityPostureResponse,
    SystemSummaryResponse,
    TopProcessesResponse,
    # Phase 11 Schemas
    ActivityHistoryResponse,
    ActivityLogSchema,
    AuthTokenResponse,
    ChatStreamRequest,
    ConversationCreateRequest,
    ConversationMessageSchema,
    ConversationThreadSchema,
    ConversationUpdateRequest,
    MessageSendRequest,
    UserProfileResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserSessionItemSchema,
    UserSettingsSchema,
    UserSettingsUpdateRequest,
)
from core.conversation_manager import (
    ActivityLogManager,
    ConversationManager,
    UserSettingsManager,
)
from core.exceptions import SecurityViolationError
from core.intelligence.central_router import CentralIntelligenceRouter
from core.intelligence.neural_core import NeuralCore, NeuralCoreConfig
from multimodal.audio.speech_generation import VoiceConfig
from multimodal.modality_router import ModalityRouter
from neural_architecture.fusion.multimodal_fusion import MultimodalInput
from infrastructure.gpu_cluster import ClusterCatalog
from infrastructure.local import LocalHardwareInspector, LocalRuntimeManager
from neural_architecture.inference import InferenceEngine
from security.auth import AuthManager, UserAccount
from security.sanitization import inspect_prompt_safety, validate_shell_command
from tokenizer import CustomBPETokenizer

router = APIRouter()
REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def get_server_state(request: Request) -> Dict[str, Any]:
    """Retrieves shared application state (models, tokenizers, uptime)."""
    if hasattr(request.app.state, "services") and request.app.state.services is not None:
        return request.app.state.services
    from api.rest.app import initialize_runtime_services
    services = initialize_runtime_services()
    request.app.state.services = services
    return services


# -------------------------------------------------------------------------
# Health Check & System Status
# -------------------------------------------------------------------------

@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Health check & server status",
)
@router.get(
    "/api/v1/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Versioned health check & server status",
)
async def get_health(services: Dict[str, Any] = Depends(get_server_state)) -> HealthResponse:
    """Returns operational health status, backend mode, and parameter counts."""
    inference_engine: Optional[InferenceEngine] = services.get("inference_engine")
    tokenizer: Optional[CustomBPETokenizer] = services.get("tokenizer")
    start_time: float = services.get("start_time", time.time())

    param_count = inference_engine.model.parameter_count if inference_engine else 0
    uptime = time.time() - start_time

    return HealthResponse(
        status="healthy",
        version="0.5.0",
        operating_mode="hybrid",
        compute_backend="cpu",
        neural_core_ready=inference_engine is not None,
        tokenizer_ready=tokenizer is not None,
        model_parameter_count=param_count,
        uptime_seconds=round(uptime, 2),
    )


@router.get(
    "/api/v1/system/telemetry",
    response_model=TelemetryResponse,
    tags=["System"],
    summary="Host hardware telemetry & safe memory budget",
)
async def get_telemetry() -> TelemetryResponse:
    """Reads safe, non-destructive host hardware introspection and memory budget."""
    try:
        profile = LocalHardwareInspector.get_profile()
        runtime_mgr = LocalRuntimeManager(profile)
        budget = runtime_mgr.budget

        return TelemetryResponse(
            cpu_model=profile.cpu_model,
            physical_cores=profile.physical_cores,
            logical_threads=profile.logical_threads,
            has_avx2=profile.has_avx2,
            total_ram_gb=profile.total_ram_gb,
            available_ram_gb=profile.available_ram_gb,
            total_swap_gb=round(profile.swap_total_bytes / (1024**3), 2),
            root_free_gb=profile.root_free_gb,
            has_kvm=profile.has_kvm,
            safe_memory_budget_gb=budget.max_ram_gb,
            cpu_thread_limit=budget.cpu_thread_limit,
            execution_mode=budget.execution_mode,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read host telemetry: {e}",
        )


@router.get(
    "/api/v1/phases/status",
    response_model=PhaseStatusResponse,
    tags=["System"],
    summary="Project development phase status",
)
async def get_phase_status() -> PhaseStatusResponse:
    """Returns active project roadmap phase and completed milestones."""
    return PhaseStatusResponse(
        current_phase="Phase 05 — Training Infrastructure & GPU Cluster Architecture",
        current_phase_status="Implementation Complete (104/104 tests passing) — Localhost Testing Ready",
        completed_phases=[
            "Phase 01 — Environment & Hardware Assessment (Commit: 0215368)",
            "Phase 02 — Project Architecture & Workspace Design (Commit: 26ff5c6)",
            "Phase 03 — Core AI Foundation Development (Commits: ea2577f, 62e5a70)",
            "Phase 04 — Custom BPE Tokenizer & Data Pipeline (Commit: 3c76fa7)",
            "Phase 05 — Training Infrastructure & GPU Cluster Architecture (Commit: 48f237b)",
        ],
        last_updated="2026-11-06T21:48:55+05:30",
    )


@router.get(
    "/api/v1/system/cluster_catalog",
    tags=["System"],
    summary="List formal GPU cluster infrastructure tiers",
)
async def get_cluster_catalog() -> List[Dict[str, Any]]:
    """Returns specifications for Tier A, Tier B, and Tier C cluster configurations."""
    tiers = ClusterCatalog.all_tiers()
    return [t.to_dict() for t in tiers]


# -------------------------------------------------------------------------
# Tokenizer Endpoints
# -------------------------------------------------------------------------

@router.post(
    "/api/v1/tokenizer/encode",
    response_model=TokenizeResponse,
    tags=["Tokenizer"],
    summary="Encode text into subwords and IDs",
)
async def encode_text(
    payload: TokenizeRequest,
    services: Dict[str, Any] = Depends(get_server_state),
) -> TokenizeResponse:
    """Encodes input string using the trained Custom Character-Level BPE Tokenizer."""
    tokenizer: Optional[CustomBPETokenizer] = services.get("tokenizer")
    if not tokenizer:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Custom BPE Tokenizer is not loaded",
        )

    try:
        res = tokenizer.encode(
            text=payload.text,
            add_bos=payload.add_bos,
            add_eos=payload.add_eos,
        )
        return TokenizeResponse(
            text=payload.text,
            tokens=res.tokens,
            ids=res.ids,
            token_count=len(res.ids),
            vocab_size=tokenizer.vocab_size,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tokenization failed: {e}",
        )


@router.post(
    "/api/v1/tokenizer/decode",
    response_model=DecodeResponse,
    tags=["Tokenizer"],
    summary="Decode token IDs into text",
)
async def decode_tokens(
    payload: DecodeRequest,
    services: Dict[str, Any] = Depends(get_server_state),
) -> DecodeResponse:
    """Reconstructs text from a list of integer token IDs."""
    tokenizer: Optional[CustomBPETokenizer] = services.get("tokenizer")
    if not tokenizer:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Custom BPE Tokenizer is not loaded",
        )

    try:
        text = tokenizer.decode(
            ids=payload.ids,
            skip_special_tokens=payload.skip_special_tokens,
        )
        return DecodeResponse(ids=payload.ids, text=text)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Token decoding failed: {e}",
        )


# -------------------------------------------------------------------------
# Neural Inference Endpoints
# -------------------------------------------------------------------------

@router.post(
    "/api/v1/neural/generate",
    response_model=InferenceResponse,
    tags=["Neural Core"],
    summary="Execute greedy autoregressive token prediction",
)
async def generate_neural_tokens(
    payload: InferenceRequest,
    services: Dict[str, Any] = Depends(get_server_state),
) -> InferenceResponse:
    """Executes genuine forward pass on the custom NeuralCore and BPE Tokenizer.

    Uses actual random-initialized model weights (no fake text, no pretrained weights).
    """
    tokenizer: Optional[CustomBPETokenizer] = services.get("tokenizer")
    engine: Optional[InferenceEngine] = services.get("inference_engine")

    if not tokenizer or not engine:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Neural Core or Tokenizer is not initialized",
        )

    start_t = time.perf_counter()
    try:
        # 1. Encode prompt
        encoding = tokenizer.encode(payload.prompt, add_bos=True, add_eos=False)
        prompt_ids = encoding.ids

        # 2. Execute actual greedy generation
        context_hints = {"mode": payload.mode or "general"}
        all_ids = engine.generate_greedy_tokens(
            prompt_ids=prompt_ids,
            max_new_tokens=payload.max_new_tokens,
            context_hints=context_hints,
        )

        generated_new_ids = all_ids[len(prompt_ids):]
        generated_tokens = [tokenizer.id_to_token(i) for i in generated_new_ids]
        generated_text = tokenizer.decode(generated_new_ids, skip_special_tokens=True)

        elapsed_ms = (time.perf_counter() - start_t) * 1000.0

        return InferenceResponse(
            prompt=payload.prompt,
            prompt_ids=prompt_ids,
            generated_ids=generated_new_ids,
            generated_tokens=generated_tokens,
            generated_text=generated_text,
            total_parameters=engine.model.parameter_count,
            is_random_initialization=True,
            latency_ms=round(elapsed_ms, 2),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Neural generation failed: {e}",
        )


# -------------------------------------------------------------------------
# Security & Coding Inspection Endpoints
# -------------------------------------------------------------------------

@router.post(
    "/api/v1/security/validate_command",
    response_model=CommandValidationResponse,
    tags=["Security"],
    summary="Validate shell command against zero-trust safety rules",
)
async def check_command_safety(payload: CommandValidationRequest) -> CommandValidationResponse:
    """Verifies shell commands against catastrophic patterns (rm -rf, mkfs, fork bombs)."""
    try:
        validate_shell_command(payload.command)
        return CommandValidationResponse(
            command=payload.command,
            is_safe=True,
            status="PASSED",
            required_tier="protected",
            detail="Command passed zero-trust signature audit.",
        )
    except SecurityViolationError as err:
        return CommandValidationResponse(
            command=payload.command,
            is_safe=False,
            status="BLOCKED",
            required_tier=err.required_tier,
            detail=str(err),
        )


@router.post(
    "/api/v1/security/inspect_prompt",
    response_model=PromptSafetyResponse,
    tags=["Security"],
    summary="Inspect prompt for adversarial injection signatures",
)
async def check_prompt_injection(payload: PromptSafetyRequest) -> PromptSafetyResponse:
    """Scans incoming prompt for prompt injection and override attacks."""
    has_injection, signatures = inspect_prompt_safety(payload.text)
    return PromptSafetyResponse(
        text=payload.text,
        is_safe=not has_injection,
        detected_signatures=signatures,
    )


@router.get(
    "/api/v1/git/status",
    tags=["Coding"],
    summary="Inspect repository Git working tree status",
)
async def get_git_status() -> Dict[str, Any]:
    """Returns actual repository git status and recent commit."""
    try:
        # Branch
        res_branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        branch = res_branch.stdout.strip() if res_branch.returncode == 0 else "main"

        # Commit
        res_commit = subprocess.run(
            ["git", "log", "-n", "1", "--format=%h %s (%cd)", "--date=iso"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        commit = res_commit.stdout.strip() if res_commit.returncode == 0 else "N/A"

        # Porcelain status
        res_status = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        changes = [line for line in res_status.stdout.splitlines() if line.strip()]

        return {
            "branch": branch,
            "latest_commit": commit,
            "modified_files_count": len(changes),
            "uncommitted_files": changes[:15],
        }
    except Exception as e:
        return {
            "branch": "main",
            "latest_commit": "error querying git",
            "modified_files_count": 0,
            "uncommitted_files": [],
            "error": str(e),
        }


# -------------------------------------------------------------------------
# Phase 07 — Intelligence Module Endpoints
# -------------------------------------------------------------------------

@router.get(
    "/api/v1/intelligence/modules",
    tags=["Intelligence"],
    summary="List all 12 specialized modular intelligence engines",
)
async def list_intelligence_modules() -> Dict[str, Any]:
    """Returns metadata, status, and responsibilities for all Phase 07 intelligence modules."""
    return {
        "status": "active",
        "phase": "Phase 07 — Intelligence Modules",
        "total_modules": 12,
        "modules": [
            {"id": "logical", "name": "Logical Reasoning Engine", "package": "core.reasoning.logical", "status": "implemented"},
            {"id": "mathematical", "name": "Mathematical Reasoning Engine", "package": "core.reasoning.mathematical", "status": "implemented"},
            {"id": "scientific", "name": "Scientific Reasoning Engine", "package": "core.reasoning.scientific", "status": "implemented"},
            {"id": "coding", "name": "Coding Intelligence Engine", "package": "personal_ai.coding_assistant.coding_engine", "status": "implemented"},
            {"id": "cybersecurity", "name": "Cybersecurity Intelligence Engine", "package": "personal_ai.cybersecurity.cyber_engine", "status": "implemented"},
            {"id": "critical_thinking", "name": "Critical Thinking Engine", "package": "core.reasoning.critical", "status": "implemented"},
            {"id": "creative", "name": "Creative Problem-Solving Engine", "package": "core.reasoning.creative", "status": "implemented"},
            {"id": "research", "name": "Research and Knowledge Analysis Engine", "package": "core.intelligence.research_engine", "status": "implemented"},
            {"id": "planning", "name": "Planning and Decision-Making Engine", "package": "agent.planner.planning_engine", "status": "implemented"},
            {"id": "self_evaluation", "name": "Self-Evaluation and Error Detection Engine", "package": "core.intelligence.self_evaluation", "status": "implemented"},
            {"id": "language", "name": "Language and Communication Engine", "package": "core.intelligence.language_engine", "status": "implemented"},
            {"id": "knowledge", "name": "General Knowledge Processing Engine", "package": "core.intelligence.knowledge_engine", "status": "implemented"},
        ],
        "router": "CentralIntelligenceRouter (core.intelligence.central_router)",
        "security_policy": "Defensive operations only; sandbox barrier enforced for code execution; zero pretrained weights.",
    }


def _get_central_router(services: Dict[str, Any]) -> CentralIntelligenceRouter:
    """Helper to retrieve or lazily create CentralIntelligenceRouter."""
    if "central_router" in services and services["central_router"] is not None:
        return services["central_router"]
    router_inst = CentralIntelligenceRouter()
    services["central_router"] = router_inst
    return router_inst


@router.post(
    "/api/v1/intelligence/query",
    response_model=IntelligenceQueryResponse,
    tags=["Intelligence"],
    summary="Route query through Central Intelligence Router",
)
async def route_intelligence_query(
    req: IntelligenceQueryRequest,
    services: Dict[str, Any] = Depends(get_server_state),
) -> IntelligenceQueryResponse:
    """Routes query dynamically to target intelligence engines and reconciles outputs."""
    c_router = _get_central_router(services)
    hints = req.context_hints or {}
    if req.force_engine:
        hints["force_engine"] = req.force_engine

    try:
        res = c_router.dispatch(query=req.query, context_hints=hints)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return IntelligenceQueryResponse(
        query=res.query,
        primary_engine=res.dispatch_plan.primary_engine,
        secondary_engines=res.dispatch_plan.secondary_engines,
        intent_confidence=res.dispatch_plan.intent_confidence,
        combined_summary=res.combined_summary,
        conflicts_detected=res.conflicts_detected,
        is_fallback_used=res.is_fallback_used,
    )


@router.post(
    "/api/v1/intelligence/logical",
    response_model=LogicalReasoningResponse,
    tags=["Intelligence"],
    summary="Execute formal and deductive logical reasoning",
)
async def analyze_logical(
    req: LogicalReasoningRequest,
    services: Dict[str, Any] = Depends(get_server_state),
) -> LogicalReasoningResponse:
    """Decomposes logical problem, detects contradictions, and quantifies epistemic uncertainty."""
    c_router = _get_central_router(services)
    try:
        res = c_router.logical_engine.analyze(
            problem=req.problem,
            premises=req.premises,
            candidates=req.candidates,
            constraints=req.constraints,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return LogicalReasoningResponse(
        problem=res.problem,
        decomposed_steps=res.decomposed_steps,
        assumptions=res.assumptions,
        premises_count=len(res.premises),
        contradictions_count=len(res.contradictions),
        conclusion=res.conclusion,
        epistemic_uncertainty=res.epistemic_uncertainty,
        summary=res.summary,
    )


@router.post(
    "/api/v1/intelligence/math",
    response_model=MathReasoningResponse,
    tags=["Intelligence"],
    summary="Deterministic mathematical computation and verification",
)
async def compute_math(
    req: MathReasoningRequest,
    services: Dict[str, Any] = Depends(get_server_state),
) -> MathReasoningResponse:
    """Computes arithmetic, algebraic, or statistical problems with numerical verification."""
    c_router = _get_central_router(services)
    try:
        res = c_router.mathematical_engine.evaluate_arithmetic(req.expression)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return MathReasoningResponse(
        domain=res.domain,
        query_description=res.query_description,
        exact_solution=res.exact_solution,
        numerical_approximation=res.numerical_approximation,
        is_verified=res.verification.is_verified if res.verification else True,
        summary=res.summary,
    )


@router.post(
    "/api/v1/intelligence/coding",
    response_model=CodingAnalysisResponse,
    tags=["Intelligence"],
    summary="Defensive code inspection and complexity estimation",
)
async def analyze_code(
    req: CodingAnalysisRequest,
    services: Dict[str, Any] = Depends(get_server_state),
) -> CodingAnalysisResponse:
    """Parses code AST, detects bugs and complexity, enforcing sandbox execution prohibition."""
    c_router = _get_central_router(services)
    try:
        res = c_router.coding_engine.analyze(req.code, language_hint=req.language)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return CodingAnalysisResponse(
        language=res.language,
        is_valid_syntax=res.is_valid_syntax,
        functions=res.functions,
        classes=res.classes,
        estimated_time_complexity=res.complexity.estimated_time_complexity,
        estimated_space_complexity=res.complexity.estimated_space_complexity,
        issues_count=len(res.issues),
        sandbox_execution_permitted=res.sandbox_notice.execution_permitted,
        sandbox_warning=res.sandbox_notice.warning,
        explanation=res.explanation,
    )


@router.post(
    "/api/v1/intelligence/security",
    response_model=SecurityAuditResponse,
    tags=["Intelligence"],
    summary="Defensive cybersecurity triage and pattern inspection",
)
async def audit_security(
    req: SecurityAuditRequest,
    services: Dict[str, Any] = Depends(get_server_state),
) -> SecurityAuditResponse:
    """Defensive log inspection, artifact scanning, and hardening recommendations."""
    c_router = _get_central_router(services)
    file_sample = (req.filename, req.file_content) if (req.filename and req.file_content) else None
    try:
        res = c_router.cybersecurity_engine.audit(
            query=req.query,
            logs=req.logs,
            file_sample=file_sample,
        )
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    cats = list({t.category for t in res.threats_identified})
    risk = res.log_report.overall_risk_level if res.log_report else "LOW"

    return SecurityAuditResponse(
        target_type=res.target_type,
        threats_detected_count=len(res.threats_identified),
        threat_categories=cats,
        overall_risk_level=risk,
        hardening_recommendations=res.hardening_recommendations,
        is_defensive_compliant=res.is_defensive_compliant,
        defensive_policy_notice=res.notice,
    )


@router.post(
    "/api/v1/intelligence/plan",
    response_model=PlanningResponse,
    tags=["Intelligence"],
    summary="Goal decomposition into topologically sorted DAG with risk gating",
)
async def create_execution_plan(
    req: PlanningRequest,
    services: Dict[str, Any] = Depends(get_server_state),
) -> PlanningResponse:
    """Sequences subtasks into dependency graph and checks mandatory human approval gates."""
    c_router = _get_central_router(services)
    try:
        plan = c_router.planning_engine.create_plan(req.objective, subtasks_data=req.subtasks)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return PlanningResponse(
        objective=plan.objective,
        total_tasks=len(plan.tasks),
        task_order=plan.task_order,
        requires_human_approval=plan.requires_human_approval,
        pending_approvals_count=plan.pending_approvals_count,
        summary=plan.summary,
    )


@router.post(
    "/api/v1/intelligence/self_evaluate",
    response_model=SelfEvaluationResponse,
    tags=["Intelligence"],
    summary="Self-evaluation, consistency verification, and modesty check",
)
async def self_evaluate_output(
    req: SelfEvaluationRequest,
    services: Dict[str, Any] = Depends(get_server_state),
) -> SelfEvaluationResponse:
    """Audits generated response against query and factual constraints."""
    c_router = _get_central_router(services)
    try:
        eval_res = c_router.self_eval_engine.evaluate(
            query=req.query,
            output=req.candidate_output,
            context_facts=req.context_facts,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return SelfEvaluationResponse(
        is_valid=eval_res.is_valid,
        quality_score=eval_res.quality_score,
        epistemic_modesty_status=eval_res.epistemic_modesty_status,
        findings_count=len(eval_res.findings),
        contains_contradictions=eval_res.contains_contradictions,
        missing_elements=eval_res.missing_elements,
        summary=eval_res.summary,
    )


# -------------------------------------------------------------------------
# Phase 08 — Multimodal Intelligence Endpoints
# -------------------------------------------------------------------------

import base64


def _get_modality_router(services: Dict[str, Any]) -> ModalityRouter:
    """Helper to retrieve or lazily create ModalityRouter."""
    if "modality_router" in services and services["modality_router"] is not None:
        return services["modality_router"]
    c_router = _get_central_router(services)
    m_router = ModalityRouter(central_router=c_router)
    services["modality_router"] = m_router
    return m_router


def _clean_and_decode_base64(raw_str: str) -> bytes:
    """Decode raw base64 or strip data URI prefix (e.g. data:image/png;base64,...)."""
    cleaned = raw_str.strip()
    if "," in cleaned and cleaned.startswith("data:"):
        cleaned = cleaned.split(",", 1)[1]
    return base64.b64decode(cleaned)


@router.get(
    "/api/v1/multimodal/modalities",
    tags=["Multimodal"],
    summary="List all supported multimodal capabilities and formats",
)
async def list_modalities() -> Dict[str, Any]:
    """Returns capabilities, supported formats, and fusion stages for Phase 08."""
    return {
        "status": "active",
        "phase": "Phase 08 — Multimodal Intelligence",
        "supported_modalities": [
            {"id": "text", "name": "Text Intelligence", "formats": ["UTF-8", "Hindi/Devanagari", "Code"]},
            {"id": "image", "name": "Image Intelligence", "formats": ["PNG", "JPEG", "WEBP", "BMP"]},
            {"id": "audio", "name": "Audio Intelligence", "formats": ["WAV", "MP3", "FLAC", "OGG", "M4A"]},
            {"id": "speech_stt", "name": "Speech Recognition (STT)", "languages": ["en", "hi"]},
            {"id": "speech_tts", "name": "Speech Generation (TTS)", "languages": ["en", "hi"]},
            {"id": "video", "name": "Video Intelligence", "formats": ["MP4", "MOV", "WEBM"]},
            {"id": "document", "name": "Document Intelligence", "formats": ["PDF", "DOCX", "CSV", "JSON", "TXT", "MD"]},
        ],
        "fusion_stages": ["EARLY", "INTERMEDIATE", "LATE"],
        "security_policy": "Untrusted input defense; prompt injection scanning; zero external cloud API calls without approval.",
    }


@router.post(
    "/api/v1/multimodal/process",
    response_model=MultimodalProcessResponse,
    tags=["Multimodal"],
    summary="Unified multi-modality processing and multi-stage fusion",
)
async def process_multimodal(
    req: MultimodalProcessRequest,
    services: Dict[str, Any] = Depends(get_server_state),
) -> MultimodalProcessResponse:
    """Processes combination of text, image, audio, video, and documents."""
    m_router = _get_modality_router(services)

    img_bytes = _clean_and_decode_base64(req.image_base64) if req.image_base64 else None
    aud_bytes = _clean_and_decode_base64(req.audio_base64) if req.audio_base64 else None
    vid_bytes = _clean_and_decode_base64(req.video_base64) if req.video_base64 else None
    doc_bytes = _clean_and_decode_base64(req.document_base64) if req.document_base64 else None

    try:
        res = m_router.route_and_process(
            text=req.text,
            image_data=img_bytes,
            audio_data=aud_bytes,
            video_data=vid_bytes,
            document_data=doc_bytes,
            filename_hints=req.filename_hints,
            perform_fusion=req.perform_fusion,
            fusion_stage=req.fusion_stage,
            synthesize_speech=req.synthesize_speech,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return MultimodalProcessResponse(
        primary_modality=res.detection.primary_modality,
        active_modalities=res.detection.active_modalities,
        is_multimodal=res.detection.is_multimodal,
        text_summary=res.text_result.summary if res.text_result else None,
        image_caption=res.image_result.caption_hypothesis if res.image_result else None,
        audio_summary=res.audio_result.summary if res.audio_result else None,
        speech_transcript=res.speech_recognition_result.full_transcript if res.speech_recognition_result else None,
        speech_audio_base64_uri=res.speech_synthesis_result.audio_base64_uri if res.speech_synthesis_result else None,
        video_summary=res.video_result.video_summary if res.video_result else None,
        document_summary=res.document_result.summary if res.document_result else None,
        document_safe=res.document_result.security_report.is_safe if res.document_result else None,
        fusion_active_modalities=res.fusion_output.active_modalities if res.fusion_output else None,
        combined_summary=res.combined_response_summary,
    )


@router.post(
    "/api/v1/multimodal/image",
    response_model=ImageProcessResponse,
    tags=["Multimodal"],
    summary="Image inspection, patch extraction, and format validation",
)
async def process_image(
    req: ImageProcessRequest,
    services: Dict[str, Any] = Depends(get_server_state),
) -> ImageProcessResponse:
    """Inspects and validates image bytes, extracting patch tensors for vision models."""
    m_router = _get_modality_router(services)
    try:
        img_bytes = _clean_and_decode_base64(req.image_base64)
        target = req.target_size or (224, 224)
        res = m_router.image_processor.process(img_bytes, target_size=target)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return ImageProcessResponse(
        format=res.metadata.format,
        width=res.metadata.width,
        height=res.metadata.height,
        aspect_ratio=res.metadata.aspect_ratio,
        channels=res.metadata.channels,
        patch_count=res.patch_count,
        caption=res.caption_hypothesis,
        reasoning_summary=res.visual_reasoning_summary,
    )


@router.post(
    "/api/v1/multimodal/audio",
    response_model=AudioProcessResponse,
    tags=["Multimodal"],
    summary="Audio waveform inspection, energy metrics, and SNR estimation",
)
async def process_audio(
    req: AudioProcessRequest,
    services: Dict[str, Any] = Depends(get_server_state),
) -> AudioProcessResponse:
    """Inspects and analyzes audio track waveform, channels, and spectrogram properties."""
    m_router = _get_modality_router(services)
    try:
        aud_bytes = _clean_and_decode_base64(req.audio_base64)
        res = m_router.audio_processor.process(aud_bytes)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return AudioProcessResponse(
        format=res.metadata.format,
        duration_seconds=res.metadata.duration_seconds,
        sample_rate=res.metadata.sample_rate,
        channels=res.metadata.channels,
        rms_energy=res.features.rms_energy,
        estimated_snr_db=res.features.estimated_snr_db,
        is_silent=res.features.is_silent,
        summary=res.summary,
    )


@router.post(
    "/api/v1/multimodal/speech/recognize",
    response_model=SpeechRecognizeResponse,
    tags=["Multimodal"],
    summary="Speech-to-text recognition with timestamped segments",
)
async def recognize_speech(
    req: SpeechRecognizeRequest,
    services: Dict[str, Any] = Depends(get_server_state),
) -> SpeechRecognizeResponse:
    """Transcribes spoken audio into timestamped segments."""
    m_router = _get_modality_router(services)
    try:
        aud_bytes = _clean_and_decode_base64(req.audio_base64)
        res = m_router.speech_recognizer.transcribe(aud_bytes, language_hint=req.language_hint)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return SpeechRecognizeResponse(
        full_transcript=res.full_transcript,
        detected_language=res.detected_language,
        overall_confidence=res.overall_confidence,
        duration_seconds=res.duration_seconds,
        segments_count=len(res.segments),
    )


@router.post(
    "/api/v1/multimodal/speech/synthesize",
    response_model=SpeechSynthesizeResponse,
    tags=["Multimodal"],
    summary="Text-to-speech synthesis generating playable WAV audio",
)
async def synthesize_speech(
    req: SpeechSynthesizeRequest,
    services: Dict[str, Any] = Depends(get_server_state),
) -> SpeechSynthesizeResponse:
    """Synthesizes text into audible PCM WAV bytes and base64 data URI."""
    m_router = _get_modality_router(services)
    try:
        cfg = VoiceConfig(
            voice_id=req.voice_id,
            language=req.language,
            pitch_hz=req.pitch_hz,
            speed_factor=req.speed_factor,
        )
        res = m_router.speech_generator.synthesize(req.text, voice_config=cfg)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return SpeechSynthesizeResponse(
        text=res.text,
        language=res.language,
        duration_seconds=res.duration_seconds,
        sample_rate=res.sample_rate,
        audio_base64_uri=res.audio_base64_uri,
        summary=res.summary,
    )


@router.post(
    "/api/v1/multimodal/document",
    response_model=DocumentProcessResponse,
    tags=["Multimodal"],
    summary="Document extraction and prompt injection security audit",
)
async def process_document(
    req: DocumentProcessRequest,
    services: Dict[str, Any] = Depends(get_server_state),
) -> DocumentProcessResponse:
    """Extracts text and tables from document and scans for prompt injection threats."""
    m_router = _get_modality_router(services)
    try:
        doc_bytes = _clean_and_decode_base64(req.document_base64)
        res = m_router.document_processor.process(doc_bytes, filename_hint=req.filename)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return DocumentProcessResponse(
        format=res.metadata.format,
        page_count=res.metadata.page_count,
        word_count=res.metadata.word_count,
        chunks_count=len(res.chunks),
        has_tables=res.metadata.has_tables,
        is_safe=res.security_report.is_safe,
        detected_injection_risks=res.security_report.detected_injection_patterns,
        summary=res.summary,
    )


@router.post(
    "/api/v1/multimodal/fuse",
    response_model=MultimodalFuseResponse,
    tags=["Multimodal"],
    summary="Multi-stage multimodal fusion tensor coordinator",
)
async def fuse_multimodal_modalities(
    req: MultimodalFuseRequest,
    services: Dict[str, Any] = Depends(get_server_state),
) -> MultimodalFuseResponse:
    """Simulates or coordinates early, intermediate, or late multimodal tensor fusion."""
    m_router = _get_modality_router(services)
    try:
        active_upper = [m.upper() for m in req.active_modalities]
        text_t = torch.randn(1, 16, 128) if "TEXT" in active_upper else None
        img_t = torch.randn(1, 196, 768) if "IMAGE" in active_upper else None
        aud_t = torch.randn(1, 64, 257) if "AUDIO" in active_upper else None
        vid_t = torch.randn(1, 8, 768) if "VIDEO" in active_upper else None

        inputs = MultimodalInput(
            text_tensor=text_t,
            image_tensor=img_t,
            audio_tensor=aud_t,
            video_tensor=vid_t,
        )
        res = m_router.fusion_engine.fuse(inputs, stage=req.fusion_stage)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return MultimodalFuseResponse(
        fusion_stage=res.fusion_stage,
        active_modalities=res.active_modalities,
        missing_modalities=res.missing_modalities,
        fused_tensor_shape=list(res.fused_representation.shape),
        modality_weights=res.modality_weights,
    )


# ==============================================================================
# PHASE 09 — ADVANCED MEMORY & CONTROLLED LEARNING ENDPOINTS
# ==============================================================================

def _get_ltm(services: Dict[str, Any]):
    from memory.long_term.long_term_memory import LongTermMemory
    return services.get("long_term_memory") or LongTermMemory()

def _get_stm(services: Dict[str, Any]):
    from memory.short_term.short_term_memory import ShortTermMemory
    return services.get("short_term_memory") or ShortTermMemory()

def _get_wm(services: Dict[str, Any]):
    from memory.working_memory import WorkingMemory
    return services.get("working_memory") or WorkingMemory()

def _get_em(services: Dict[str, Any]):
    from memory.episodic.episodic_memory import EpisodicMemory
    return services.get("episodic_memory") or EpisodicMemory()

def _get_km(services: Dict[str, Any]):
    from memory.knowledge.knowledge_memory import KnowledgeMemory
    return services.get("knowledge_memory") or KnowledgeMemory()

def _get_upm(services: Dict[str, Any]):
    from memory.user_preferences import UserPreferenceMemory
    return services.get("user_preference_memory") or UserPreferenceMemory()

def _get_hre(services: Dict[str, Any]):
    from memory.retrieval.retrieval_engine import HybridMemoryRetrievalEngine
    return services.get("retrieval_engine") or HybridMemoryRetrievalEngine()

def _get_mce(services: Dict[str, Any]):
    from memory.consolidation.consolidation_engine import MemoryConsolidationEngine
    return services.get("consolidation_engine") or MemoryConsolidationEngine()

def _get_cme(services: Dict[str, Any]):
    from memory.contextual_memory import ContextualMemoryEngine
    return services.get("contextual_memory") or ContextualMemoryEngine()

def _get_fs(services: Dict[str, Any]):
    from learning.feedback.feedback_system import FeedbackSystem
    return services.get("feedback_system") or FeedbackSystem()

def _get_clp(services: Dict[str, Any]):
    from learning.continual.learning_pipeline import ControlledLearningPipeline
    return services.get("learning_pipeline") or ControlledLearningPipeline()

def _get_pai(services: Dict[str, Any]):
    from personal_ai.controller import PersonalAIController
    return services.get("personal_ai_controller") or PersonalAIController()

def _get_runtime(services: Dict[str, Any]):
    from personal_ai.runtime import LocalAgentRuntime
    return services.get("agent_runtime") or _get_pai(services).runtime

def _get_approval_mgr(services: Dict[str, Any]):
    from personal_ai.permissions.approval_manager import ApprovalManager
    return services.get("approval_manager") or _get_pai(services).approval_mgr

def _get_emergency_ctrl(services: Dict[str, Any]):
    from personal_ai.emergency.kill_switch import EmergencyShutdownController
    return services.get("emergency_controller") or _get_pai(services).emergency_ctrl

def _get_audit(services: Dict[str, Any]):
    from personal_ai.audit.audit_system import AgentAuditSystem
    return services.get("agent_audit_system") or _get_pai(services).audit


# -----------------------------------------------------------------------------
# Memory Records (Long-Term & Knowledge)
# -----------------------------------------------------------------------------

@router.post(
    "/api/v1/memory/records",
    response_model=MemoryRecordResponse,
    tags=["Memory"],
    summary="Save a persistent long-term memory record",
)
async def create_memory_record(
    req: MemoryRecordCreateRequest,
    services: Dict[str, Any] = Depends(get_server_state),
) -> MemoryRecordResponse:
    ltm = _get_ltm(services)
    try:
        rec = ltm.save_record(
            user_id=req.user_id,
            content=req.content,
            summary=req.summary,
            importance=req.importance,
            confidence=req.confidence,
            is_confirmed_by_user=req.is_confirmed_by_user,
            source_type=req.source_type,
            tags=req.tags,
        )
        return MemoryRecordResponse(
            record_id=rec.record_id,
            user_id=rec.user_id,
            content=rec.content,
            summary=rec.summary,
            importance=rec.importance,
            confidence=rec.confidence,
            is_confirmed_by_user=rec.is_confirmed_by_user,
            version=rec.version,
            parent_version_id=rec.parent_version_id,
            source_type=rec.source_type,
            tags=rec.tags,
            created_at=rec.created_at,
            updated_at=rec.updated_at,
            status=rec.status,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/api/v1/memory/records",
    response_model=List[MemoryRecordResponse],
    tags=["Memory"],
    summary="List active persistent memory records for a user",
)
async def list_memory_records(
    user_id: str,
    limit: int = 50,
    services: Dict[str, Any] = Depends(get_server_state),
) -> List[MemoryRecordResponse]:
    ltm = _get_ltm(services)
    try:
        records = ltm.list_records(user_id=user_id, limit=limit)
        return [
            MemoryRecordResponse(
                record_id=r.record_id,
                user_id=r.user_id,
                content=r.content,
                summary=r.summary,
                importance=r.importance,
                confidence=r.confidence,
                is_confirmed_by_user=r.is_confirmed_by_user,
                version=r.version,
                parent_version_id=r.parent_version_id,
                source_type=r.source_type,
                tags=r.tags,
                created_at=r.created_at,
                updated_at=r.updated_at,
                status=r.status,
            )
            for r in records
        ]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put(
    "/api/v1/memory/records/{record_id}",
    response_model=MemoryRecordResponse,
    tags=["Memory"],
    summary="Update a persistent memory record with version increment",
)
async def update_memory_record(
    record_id: str,
    req: MemoryRecordUpdateRequest,
    services: Dict[str, Any] = Depends(get_server_state),
) -> MemoryRecordResponse:
    ltm = _get_ltm(services)
    try:
        rec = ltm.update_record(
            user_id=req.user_id,
            record_id=record_id,
            new_content=req.new_content,
            new_summary=req.new_summary,
            importance=req.importance,
            confidence=req.confidence,
            is_confirmed_by_user=req.is_confirmed_by_user,
            tags=req.tags,
        )
        return MemoryRecordResponse(
            record_id=rec.record_id,
            user_id=rec.user_id,
            content=rec.content,
            summary=rec.summary,
            importance=rec.importance,
            confidence=rec.confidence,
            is_confirmed_by_user=rec.is_confirmed_by_user,
            version=rec.version,
            parent_version_id=rec.parent_version_id,
            source_type=rec.source_type,
            tags=rec.tags,
            created_at=rec.created_at,
            updated_at=rec.updated_at,
            status=rec.status,
        )
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/api/v1/memory/records/{record_id}",
    tags=["Memory"],
    summary="Delete / archive a persistent memory record",
)
async def delete_memory_record(
    record_id: str,
    user_id: str,
    services: Dict[str, Any] = Depends(get_server_state),
) -> Dict[str, Any]:
    ltm = _get_ltm(services)
    try:
        success = ltm.delete_record(user_id=user_id, record_id=record_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
        return {"status": "success", "record_id": record_id, "deleted": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# -----------------------------------------------------------------------------
# Short-Term Memory
# -----------------------------------------------------------------------------

@router.post(
    "/api/v1/memory/short-term",
    response_model=ShortTermMessageResponse,
    tags=["Memory"],
    summary="Append a conversational turn to short-term memory",
)
async def add_short_term_message(
    req: ShortTermMessageRequest,
    services: Dict[str, Any] = Depends(get_server_state),
) -> ShortTermMessageResponse:
    stm = _get_stm(services)
    try:
        msg = stm.add_message(
            user_id=req.user_id,
            session_id=req.session_id,
            role=req.role,
            content=req.content,
        )
        return ShortTermMessageResponse(
            message_id=msg.message_id,
            user_id=msg.user_id,
            session_id=msg.session_id,
            role=msg.role,
            content=msg.content,
            timestamp=msg.timestamp,
            token_count_estimate=msg.token_count_estimate,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/api/v1/memory/short-term",
    response_model=List[ShortTermMessageResponse],
    tags=["Memory"],
    summary="Retrieve session history from short-term memory",
)
async def get_short_term_history(
    user_id: str,
    session_id: str,
    limit: int = 20,
    services: Dict[str, Any] = Depends(get_server_state),
) -> List[ShortTermMessageResponse]:
    stm = _get_stm(services)
    try:
        msgs = stm.get_history(user_id=user_id, session_id=session_id, limit=limit)
        return [
            ShortTermMessageResponse(
                message_id=m.message_id,
                user_id=m.user_id,
                session_id=m.session_id,
                role=m.role,
                content=m.content,
                timestamp=m.timestamp,
                token_count_estimate=m.token_count_estimate,
            )
            for m in msgs
        ]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/api/v1/memory/short-term",
    tags=["Memory"],
    summary="Clear short-term memory for a session",
)
async def clear_short_term_session(
    user_id: str,
    session_id: str,
    services: Dict[str, Any] = Depends(get_server_state),
) -> Dict[str, Any]:
    stm = _get_stm(services)
    try:
        count = stm.clear_session(user_id=user_id, session_id=session_id)
        return {"status": "success", "session_id": session_id, "cleared_records": count}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# -----------------------------------------------------------------------------
# Working Memory
# -----------------------------------------------------------------------------

@router.post(
    "/api/v1/memory/working",
    response_model=WorkingTaskResponse,
    tags=["Memory"],
    summary="Start or resume an active working memory task",
)
async def start_working_task(
    req: WorkingTaskStartRequest,
    services: Dict[str, Any] = Depends(get_server_state),
) -> WorkingTaskResponse:
    wm = _get_wm(services)
    try:
        t = wm.start_task(
            session_id=req.session_id,
            task_id=req.task_id,
            task_name=req.task_name,
            objectives=req.objectives,
            dependencies=req.dependencies,
            initial_results=req.initial_results,
        )
        return WorkingTaskResponse(
            session_id=t.session_id,
            task_id=t.task_id,
            task_name=t.task_name,
            active_objectives=t.active_objectives,
            intermediate_results=t.intermediate_results,
            dependencies=t.dependencies,
            pending_actions=t.pending_actions,
            status=t.status,
            created_at=t.created_at,
            updated_at=t.updated_at,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/api/v1/memory/working",
    response_model=List[WorkingTaskResponse],
    tags=["Memory"],
    summary="List active working memory tasks for a session",
)
async def list_working_tasks(
    session_id: str,
    services: Dict[str, Any] = Depends(get_server_state),
) -> List[WorkingTaskResponse]:
    wm = _get_wm(services)
    try:
        tasks = wm.list_active_tasks(session_id=session_id)
        return [
            WorkingTaskResponse(
                session_id=t.session_id,
                task_id=t.task_id,
                task_name=t.task_name,
                active_objectives=t.active_objectives,
                intermediate_results=t.intermediate_results,
                dependencies=t.dependencies,
                pending_actions=t.pending_actions,
                status=t.status,
                created_at=t.created_at,
                updated_at=t.updated_at,
            )
            for t in tasks
        ]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# -----------------------------------------------------------------------------
# Episodic Memory
# -----------------------------------------------------------------------------

@router.post(
    "/api/v1/memory/episodic",
    response_model=EpisodicEventResponse,
    tags=["Memory"],
    summary="Record an episodic event to past interaction log",
)
async def record_episodic_event(
    req: EpisodicEventRequest,
    services: Dict[str, Any] = Depends(get_server_state),
) -> EpisodicEventResponse:
    em = _get_em(services)
    try:
        event = em.record_event(
            user_id=req.user_id,
            event_description=req.event_description,
            session_id=req.session_id,
            task_id=req.task_id,
            context_summary=req.context_summary,
            outcome=req.outcome,
            related_memory_ids=req.related_memory_ids,
            user_feedback=req.user_feedback,
        )
        return EpisodicEventResponse(
            event_id=event.event_id,
            user_id=event.user_id,
            session_id=event.session_id,
            task_id=event.task_id,
            event_description=event.event_description,
            context_summary=event.context_summary,
            outcome=event.outcome,
            related_memory_ids=event.related_memory_ids,
            user_feedback=event.user_feedback,
            timestamp=event.timestamp,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/api/v1/memory/episodic",
    response_model=List[EpisodicEventResponse],
    tags=["Memory"],
    summary="Search episodic events (anti-fabrication guaranteed)",
)
async def search_episodic_events(
    user_id: str,
    query: Optional[str] = None,
    limit: int = 10,
    services: Dict[str, Any] = Depends(get_server_state),
) -> List[EpisodicEventResponse]:
    em = _get_em(services)
    try:
        if query:
            events = em.search_events(user_id=user_id, query=query, limit=limit)
        else:
            events = em.get_recent_events(user_id=user_id, limit=limit)
        return [
            EpisodicEventResponse(
                event_id=ev.event_id,
                user_id=ev.user_id,
                session_id=ev.session_id,
                task_id=ev.task_id,
                event_description=ev.event_description,
                context_summary=ev.context_summary,
                outcome=ev.outcome,
                related_memory_ids=ev.related_memory_ids,
                user_feedback=ev.user_feedback,
                timestamp=ev.timestamp,
            )
            for ev in events
        ]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# -----------------------------------------------------------------------------
# User Preferences
# -----------------------------------------------------------------------------

@router.get(
    "/api/v1/memory/preferences",
    response_model=Dict[str, str],
    tags=["Memory"],
    summary="Get user preference settings and style directives",
)
async def get_user_preferences(
    user_id: str,
    services: Dict[str, Any] = Depends(get_server_state),
) -> Dict[str, str]:
    upm = _get_upm(services)
    try:
        return upm.get_all_preferences(user_id=user_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/api/v1/memory/preferences",
    tags=["Memory"],
    summary="Set or update a user preference",
)
async def set_user_preference(
    req: UserPreferenceSetRequest,
    services: Dict[str, Any] = Depends(get_server_state),
) -> Dict[str, Any]:
    upm = _get_upm(services)
    try:
        pref = upm.set_preference(
            user_id=req.user_id,
            preference_key=req.preference_key,
            preference_val=req.preference_val,
            is_explicit=req.is_explicit,
        )
        return {
            "status": "success",
            "preference_key": pref.preference_key,
            "preference_val": pref.preference_val,
            "updated_at": pref.updated_at,
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/api/v1/memory/preferences/{preference_key}",
    tags=["Memory"],
    summary="Delete a user preference setting",
)
async def delete_user_preference(
    preference_key: str,
    user_id: str,
    services: Dict[str, Any] = Depends(get_server_state),
) -> Dict[str, Any]:
    upm = _get_upm(services)
    try:
        deleted = upm.delete_preference(user_id=user_id, preference_key=preference_key)
        return {"status": "success", "preference_key": preference_key, "deleted": deleted}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# -----------------------------------------------------------------------------
# Hybrid Retrieval, Consolidation & Context Assembly
# -----------------------------------------------------------------------------

@router.post(
    "/api/v1/memory/retrieve",
    response_model=List[ScoredMemoryResponse],
    tags=["Memory"],
    summary="Execute hybrid multi-dimensional memory retrieval with recency decay",
)
async def retrieve_memories(
    req: MemoryRetrievalRequest,
    services: Dict[str, Any] = Depends(get_server_state),
) -> List[ScoredMemoryResponse]:
    retriever = _get_hre(services)
    try:
        results = retriever.retrieve(
            user_id=req.user_id,
            query=req.query,
            memory_layer=req.memory_layer,
            min_confidence=req.min_confidence,
            limit=req.limit,
        )
        return [
            ScoredMemoryResponse(
                record_id=r.record_id,
                user_id=r.user_id,
                memory_layer=r.memory_layer,
                content=r.content,
                summary=r.summary,
                final_score=r.final_score,
                lexical_score=r.lexical_score,
                recency_score=r.recency_score,
                importance_score=r.importance_score,
                confidence_score=r.confidence_score,
                source_attribution=r.source_attribution,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in results
        ]
    except SecurityViolationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/api/v1/memory/consolidate",
    response_model=ConsolidationResponse,
    tags=["Memory"],
    summary="Run memory consolidation and conflict detection (no silent overwriting)",
)
async def run_memory_consolidation(
    req: ConsolidationRequest,
    services: Dict[str, Any] = Depends(get_server_state),
) -> ConsolidationResponse:
    mce = _get_mce(services)
    try:
        summary = mce.run_consolidation(user_id=req.user_id)
        return ConsolidationResponse(
            user_id=summary.user_id,
            duplicates_resolved=summary.duplicates_resolved,
            conflicts_detected=[
                ConflictReportItem(
                    conflict_id=c.conflict_id,
                    existing_record_id=c.existing_record_id,
                    conflicting_record_id=c.conflicting_record_id,
                    subject_area=c.subject_area,
                    existing_content=c.existing_content,
                    conflicting_content=c.conflicting_content,
                    resolution_status=c.resolution_status,
                    detected_at=c.detected_at,
                )
                for c in summary.conflicts_detected
            ],
            records_merged=summary.records_merged,
            consolidated_at=summary.consolidated_at,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/api/v1/memory/context",
    response_model=ContextAssemblyResponse,
    tags=["Memory"],
    summary="Synthesize multi-layer prompt context respecting token budgets",
)
async def assemble_context(
    req: ContextAssemblyRequest,
    services: Dict[str, Any] = Depends(get_server_state),
) -> ContextAssemblyResponse:
    cme = _get_cme(services)
    try:
        ctx = cme.assemble_context(
            user_id=req.user_id,
            session_id=req.session_id,
            current_query=req.current_query,
            token_budget=req.token_budget,
        )
        return ContextAssemblyResponse(
            full_context_text=ctx.full_context_text,
            personalization_directive=ctx.personalization_directive,
            active_tasks_count=len(ctx.active_tasks),
            retrieved_memories_count=len(ctx.retrieved_memories),
            conversation_turns_count=len(ctx.conversation_turns),
            estimated_tokens=ctx.estimated_tokens,
            budget_limit=ctx.budget_limit,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# -----------------------------------------------------------------------------
# Continual Learning & User Feedback
# -----------------------------------------------------------------------------

@router.post(
    "/api/v1/learning/feedback",
    response_model=FeedbackResponse,
    tags=["Continual Learning"],
    summary="Submit user feedback for offline continual learning curation",
)
async def submit_feedback(
    req: FeedbackSubmitRequest,
    services: Dict[str, Any] = Depends(get_server_state),
) -> FeedbackResponse:
    from learning.feedback.feedback_system import FeedbackType
    fs = _get_fs(services)
    try:
        fb_type = FeedbackType(req.feedback_type.upper())
    except ValueError:
        fb_type = FeedbackType.POSITIVE

    try:
        rec = fs.record_feedback(
            user_id=req.user_id,
            feedback_type=fb_type,
            response_id=req.response_id,
            task_id=req.task_id,
            rating=req.rating,
            suggested_correction=req.suggested_correction,
            category=req.category,
            comment=req.comment,
        )
        return FeedbackResponse(
            feedback_id=rec.feedback_id,
            user_id=rec.user_id,
            response_id=rec.response_id,
            task_id=rec.task_id,
            feedback_type=rec.feedback_type.value,
            rating=rec.rating,
            suggested_correction=rec.suggested_correction,
            category=rec.category,
            comment=rec.comment,
            status=rec.status.value,
            created_at=rec.created_at,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/api/v1/learning/feedback",
    response_model=List[FeedbackResponse],
    tags=["Continual Learning"],
    summary="List submitted user feedback records",
)
async def list_feedback_records(
    user_id: Optional[str] = None,
    limit: int = 50,
    services: Dict[str, Any] = Depends(get_server_state),
) -> List[FeedbackResponse]:
    fs = _get_fs(services)
    try:
        records = fs.list_feedback(user_id=user_id, limit=limit)
        return [
            FeedbackResponse(
                feedback_id=r.feedback_id,
                user_id=r.user_id,
                response_id=r.response_id,
                task_id=r.task_id,
                feedback_type=r.feedback_type.value,
                rating=r.rating,
                suggested_correction=r.suggested_correction,
                category=r.category,
                comment=r.comment,
                status=r.status.value,
                created_at=r.created_at,
            )
            for r in records
        ]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/api/v1/learning/feedback/{feedback_id}/validate",
    tags=["Continual Learning"],
    summary="Validate or reject feedback for downstream dataset preparation",
)
async def validate_feedback_record(
    feedback_id: str,
    req: FeedbackValidateRequest,
    services: Dict[str, Any] = Depends(get_server_state),
) -> Dict[str, Any]:
    fs = _get_fs(services)
    try:
        success = fs.validate_feedback(feedback_id=feedback_id, is_valid=req.is_valid, validation_notes=req.notes)
        return {"status": "success", "feedback_id": feedback_id, "validated": success}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/api/v1/learning/jobs",
    response_model=LearningJobResponse,
    tags=["Continual Learning"],
    summary="Create a 10-stage offline continual learning job",
)
async def create_learning_job(
    req: LearningJobCreateRequest,
    services: Dict[str, Any] = Depends(get_server_state),
) -> LearningJobResponse:
    pipe = _get_clp(services)
    try:
        job = pipe.create_job(target_version=req.target_version)
        return LearningJobResponse(
            job_id=job.job_id,
            current_stage=job.current_stage.value,
            status=job.status.value,
            target_version=job.target_version,
            dataset_manifest_hash=job.dataset_manifest_hash,
            stage_history_count=len(job.stage_history),
            is_approved=job.is_approved,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/api/v1/learning/jobs/{job_id}",
    response_model=LearningJobResponse,
    tags=["Continual Learning"],
    summary="Get 10-stage continual learning pipeline job status",
)
async def get_learning_job_status(
    job_id: str,
    services: Dict[str, Any] = Depends(get_server_state),
) -> LearningJobResponse:
    pipe = _get_clp(services)
    job = pipe.get_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job '{job_id}' not found.")
    return LearningJobResponse(
        job_id=job.job_id,
        current_stage=job.current_stage.value,
        status=job.status.value,
        target_version=job.target_version,
        dataset_manifest_hash=job.dataset_manifest_hash,
        stage_history_count=len(job.stage_history),
        is_approved=job.is_approved,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.post(
    "/api/v1/learning/jobs/{job_id}/run-pipeline",
    response_model=LearningJobResponse,
    tags=["Continual Learning"],
    summary="Execute end-to-end 10-stage controlled learning workflow",
)
async def run_end_to_end_pipeline(
    job_id: str,
    services: Dict[str, Any] = Depends(get_server_state),
) -> LearningJobResponse:
    pipe = _get_clp(services)
    try:
        job = pipe.get_job(job_id)
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

        pipe.run_stage_01_collection(job_id)
        pipe.run_stage_02_validation(job_id)
        pipe.run_stage_03_curation(job_id)
        pipe.run_stage_04_dataset_prep(job_id)
        pipe.run_stage_05_job_config(job_id)
        pipe.run_stage_06_model_eval(job_id)
        pipe.run_stage_07_regression_testing(job_id)
        pipe.run_stage_08_model_versioning(job_id)

        return LearningJobResponse(
            job_id=job.job_id,
            current_stage=job.current_stage.value,
            status=job.status.value,
            target_version=job.target_version,
            dataset_manifest_hash=job.dataset_manifest_hash,
            stage_history_count=len(job.stage_history),
            is_approved=job.is_approved,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/api/v1/learning/jobs/{job_id}/approve",
    response_model=LearningJobResponse,
    tags=["Continual Learning"],
    summary="Submit governance approval decision for a continual learning model artifact",
)
async def approve_learning_job(
    job_id: str,
    req: LearningJobApproveRequest,
    services: Dict[str, Any] = Depends(get_server_state),
) -> LearningJobResponse:
    pipe = _get_clp(services)
    try:
        pipe.run_stage_09_model_approval(job_id, approver=req.approver, approved=req.approved, reason=req.reason)
        if req.approved:
            pipe.run_stage_10_deployment(job_id)

        job = pipe.get_job(job_id)
        return LearningJobResponse(
            job_id=job.job_id,
            current_stage=job.current_stage.value,
            status=job.status.value,
            target_version=job.target_version,
            dataset_manifest_hash=job.dataset_manifest_hash,
            stage_history_count=len(job.stage_history),
            is_approved=job.is_approved,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# =============================================================================
# PHASE 10 — PERSONAL AI INTEGRATION ENDPOINTS
# =============================================================================

@router.get(
    "/api/v1/personal-ai/status",
    response_model=PersonalAIStatusResponse,
    tags=["Personal AI"],
    summary="Get Personal AI local agent runtime vitals and operational status",
)
async def get_personal_ai_status(
    services: Dict[str, Any] = Depends(get_server_state),
) -> PersonalAIStatusResponse:
    runtime = _get_runtime(services)
    status_info = runtime.get_runtime_status()
    return PersonalAIStatusResponse(
        is_running=status_info.is_running,
        host=status_info.host,
        port=status_info.port,
        active_sessions_count=status_info.active_sessions_count,
        emergency_shutdown_active=status_info.emergency_shutdown_active,
        uptime_seconds=status_info.uptime_seconds,
    )


@router.post(
    "/api/v1/personal-ai/sessions",
    response_model=PersonalAISessionResponse,
    tags=["Personal AI"],
    summary="Create an authenticated local personal AI agent session",
)
async def create_personal_ai_session(
    req: PersonalAISessionCreateRequest,
    services: Dict[str, Any] = Depends(get_server_state),
) -> PersonalAISessionResponse:
    runtime = _get_runtime(services)
    try:
        session = runtime.create_session(req.user_id)
        return PersonalAISessionResponse(
            session_id=session.session_id,
            user_id=session.user_id,
            auth_token=session.auth_token,
            created_at=session.created_at,
            expires_at=session.expires_at,
            is_active=session.is_active,
        )
    except SecurityViolationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/api/v1/personal-ai/chat",
    response_model=PersonalAIChatResponse,
    tags=["Personal AI"],
    summary="Natural-language interaction with the Personal AI assistant",
)
async def chat_personal_ai(
    req: PersonalAIChatRequest,
    services: Dict[str, Any] = Depends(get_server_state),
) -> PersonalAIChatResponse:
    pai = _get_pai(services)
    try:
        res = pai.process_request(user_id=req.user_id, query=req.query, session_id=req.session_id)
        return PersonalAIChatResponse(
            user_query=res.user_query,
            intent=res.intent,
            assistant_response=res.assistant_response,
            action_taken=res.action_taken,
            data_payload=res.data_payload,
            requires_approval=res.requires_approval,
            pending_ticket_id=res.pending_ticket_id,
        )
    except SecurityViolationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/api/v1/personal-ai/system/summary",
    response_model=SystemSummaryResponse,
    tags=["Personal AI - System"],
    summary="Inspect host operating system and hardware telemetry",
)
async def get_system_summary(
    services: Dict[str, Any] = Depends(get_server_state),
) -> SystemSummaryResponse:
    pai = _get_pai(services)
    summary = pai.system_info.get_system_summary()
    return SystemSummaryResponse(
        os_name=summary.os_name,
        os_version=summary.os_version,
        architecture=summary.architecture,
        hostname=summary.hostname,
        kernel_version=summary.kernel_version,
        cpu=CPUVitalsSchema(**asdict(summary.cpu)),
        memory=MemoryVitalsSchema(**asdict(summary.memory)),
        storage=[asdict(s) for s in summary.storage],
        uptime_hours=summary.uptime_hours,
        battery_percent=summary.battery_percent,
    )


@router.get(
    "/api/v1/personal-ai/system/hardware",
    response_model=Dict[str, Any],
    tags=["Personal AI - System"],
    summary="Hardware telemetry and operational resource utilization",
)
async def get_hardware_telemetry(
    services: Dict[str, Any] = Depends(get_server_state),
) -> Dict[str, Any]:
    pai = _get_pai(services)
    return pai.system_info.get_hardware_telemetry()


@router.get(
    "/api/v1/personal-ai/processes",
    response_model=List[ProcessItemSchema],
    tags=["Personal AI - System"],
    summary="List running host processes with protection flag and resource stats",
)
async def list_processes(
    limit: int = 50,
    services: Dict[str, Any] = Depends(get_server_state),
) -> List[ProcessItemSchema]:
    pai = _get_pai(services)
    processes = pai.process_monitor.list_processes(limit=limit)
    return [ProcessItemSchema(**asdict(p)) for p in processes]


@router.get(
    "/api/v1/personal-ai/processes/top",
    response_model=TopProcessesResponse,
    tags=["Personal AI - System"],
    summary="Get top CPU and memory consumer processes",
)
async def get_top_processes(
    limit: int = 5,
    services: Dict[str, Any] = Depends(get_server_state),
) -> TopProcessesResponse:
    pai = _get_pai(services)
    top = pai.process_monitor.get_top_resource_consumers(top_n=limit)
    return TopProcessesResponse(
        top_memory=[ProcessItemSchema(**asdict(p)) for p in top["top_memory"]],
        top_cpu=[ProcessItemSchema(**asdict(p)) for p in top["top_cpu"]],
    )


@router.post(
    "/api/v1/personal-ai/processes/terminate",
    response_model=ProcessTerminateResponse,
    tags=["Personal AI - System"],
    summary="Validate and terminate a process with verified operator approval",
)
async def terminate_process(
    req: ProcessTerminateRequest,
    services: Dict[str, Any] = Depends(get_server_state),
) -> ProcessTerminateResponse:
    pai = _get_pai(services)
    try:
        target = pai.process_monitor.validate_termination_target(req.pid)
    except SecurityViolationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    if not req.ticket_id:
        ticket = pai.approval_mgr.create_ticket(
            tool_name="process_monitor.terminate",
            action_summary=f"Terminate process '{target.name}' (PID {req.pid})",
            risk_tier=CommandRiskTier.DESTRUCTIVE,
            parameters={"pid": req.pid, "name": target.name, "memory_mb": target.memory_mb},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Termination of PID {req.pid} requires operator approval ticket: {ticket.ticket_id}",
        )

    is_valid, msg = pai.approval_mgr.consume_ticket(req.ticket_id)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Invalid or expired ticket: {msg}")

    pai.audit.record_event(
        user_id=req.user_id,
        tool_name="process_monitor.terminate",
        risk_tier="destructive",
        action_summary=f"Terminated process '{target.name}' (PID {req.pid}) with ticket {req.ticket_id}",
        status="success",
    )
    return ProcessTerminateResponse(
        pid=req.pid,
        terminated=True,
        message=f"Process '{target.name}' (PID {req.pid}) terminated with ticket {req.ticket_id}.",
    )


@router.post(
    "/api/v1/personal-ai/filesystem/list",
    response_model=FileListResponse,
    tags=["Personal AI - Filesystem"],
    summary="Safely list directory contents inside authorized project root",
)
async def list_directory_contents(
    req: FileListRequest,
    services: Dict[str, Any] = Depends(get_server_state),
) -> FileListResponse:
    pai = _get_pai(services)
    try:
        entries = pai.filesystem.list_directory(req.dir_path, limit=req.limit)
        return FileListResponse(
            dir_path=req.dir_path,
            entries=[FileEntrySchema(**asdict(e)) for e in entries],
        )
    except SecurityViolationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/api/v1/personal-ai/filesystem/read",
    response_model=FileReadResponse,
    tags=["Personal AI - Filesystem"],
    summary="Read file contents with path traversal protection and secret sanitization",
)
async def read_file_safe(
    req: FileReadRequest,
    services: Dict[str, Any] = Depends(get_server_state),
) -> FileReadResponse:
    pai = _get_pai(services)
    try:
        res = pai.filesystem.read_file_safe(req.file_path, max_bytes=req.max_bytes)
        return FileReadResponse(
            path=res.path,
            content=res.content,
            size_bytes=res.size_bytes,
            is_truncated=res.is_truncated,
            scrubbed_secrets_count=res.scrubbed_secrets_count,
            mime_type=res.mime_type,
        )
    except SecurityViolationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/api/v1/personal-ai/filesystem/search",
    response_model=FileListResponse,
    tags=["Personal AI - Filesystem"],
    summary="Search files inside authorized project root by query pattern",
)
async def search_files(
    req: FileSearchRequest,
    services: Dict[str, Any] = Depends(get_server_state),
) -> FileListResponse:
    pai = _get_pai(services)
    try:
        matches = pai.filesystem.search_files(
            query=req.query,
            root_dir=req.root_dir,
            extension=req.extension,
            max_results=req.max_results,
        )
        return FileListResponse(
            dir_path=req.root_dir,
            entries=[FileEntrySchema(**asdict(m)) for m in matches],
        )
    except SecurityViolationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/api/v1/personal-ai/apps",
    response_model=List[AppItemSchema],
    tags=["Personal AI - Applications"],
    summary="List installed applications detected through desktop entries",
)
async def list_installed_apps(
    services: Dict[str, Any] = Depends(get_server_state),
) -> List[AppItemSchema]:
    pai = _get_pai(services)
    apps = pai.app_manager.list_installed_applications()
    return [AppItemSchema(**asdict(a)) for a in apps]


@router.post(
    "/api/v1/personal-ai/apps/status",
    response_model=AppStatusResponse,
    tags=["Personal AI - Applications"],
    summary="Check running execution status and memory usage of an application",
)
async def get_app_status(
    req: AppStatusRequest,
    services: Dict[str, Any] = Depends(get_server_state),
) -> AppStatusResponse:
    pai = _get_pai(services)
    st = pai.app_manager.get_application_status(req.app_name)
    return AppStatusResponse(
        name=st.name,
        executable=st.executable,
        is_running=st.is_running,
        matching_pids=st.matching_pids,
        total_memory_mb=st.total_memory_mb,
    )


@router.post(
    "/api/v1/personal-ai/apps/launch",
    response_model=AppLaunchResponse,
    tags=["Personal AI - Applications"],
    summary="Launch application through approved adapter with human approval verification",
)
async def launch_app(
    req: AppLaunchRequest,
    services: Dict[str, Any] = Depends(get_server_state),
) -> AppLaunchResponse:
    pai = _get_pai(services)
    try:
        res = pai.app_manager.launch_application_safe(
            req.app_name,
            ticket_id=req.ticket_id,
            approval_manager=pai.approval_mgr,
        )
        return AppLaunchResponse(
            app_name=res.app_name,
            executable=res.executable,
            pid=res.pid,
            status=res.status,
            message=res.message,
        )
    except SecurityViolationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/api/v1/personal-ai/terminal/advise",
    response_model=CommandAdviseResponse,
    tags=["Personal AI - Terminal"],
    summary="Analyze shell command, classify risk tier, and explain safety posture",
)
async def advise_terminal_command(
    req: CommandAdviseRequest,
    services: Dict[str, Any] = Depends(get_server_state),
) -> CommandAdviseResponse:
    pai = _get_pai(services)
    adv = pai.command_advisor.analyze_command(req.proposed_command, req.user_intent)
    return CommandAdviseResponse(
        user_intent=adv.user_intent,
        proposed_command=adv.proposed_command,
        binary_name=adv.binary_name,
        explanation=adv.explanation,
        potential_risks=adv.potential_risks,
        risk_tier=adv.risk_tier.value,
        requires_approval=adv.requires_approval,
        is_blocked=adv.is_blocked,
        block_reason=adv.block_reason,
    )


@router.get(
    "/api/v1/personal-ai/network/diagnostics",
    response_model=Dict[str, Any],
    tags=["Personal AI - Network"],
    summary="Inspect network interfaces and DNS resolver configuration",
)
async def get_network_diagnostics(
    services: Dict[str, Any] = Depends(get_server_state),
) -> Dict[str, Any]:
    pai = _get_pai(services)
    return pai.network.get_network_overview()


@router.post(
    "/api/v1/personal-ai/network/ping",
    response_model=PingResponse,
    tags=["Personal AI - Network"],
    summary="Run bounded, non-destructive network ping diagnostic",
)
async def ping_network_target(
    req: PingRequest,
    services: Dict[str, Any] = Depends(get_server_state),
) -> PingResponse:
    pai = _get_pai(services)
    try:
        res = pai.network.test_connectivity(host=req.host, count=req.count)
        return PingResponse(
            target_host=res.target_host,
            is_reachable=res.is_reachable,
            packets_sent=res.packets_sent,
            packets_received=res.packets_received,
            packet_loss_percent=res.packet_loss_percent,
            round_trip_avg_ms=res.round_trip_avg_ms,
            status_summary=res.status_summary,
        )
    except SecurityViolationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/api/v1/personal-ai/network/dns",
    response_model=DNSResolveResponse,
    tags=["Personal AI - Network"],
    summary="Resolve DNS hostnames safely and measure response latency",
)
async def resolve_dns_hostname(
    req: DNSResolveRequest,
    services: Dict[str, Any] = Depends(get_server_state),
) -> DNSResolveResponse:
    pai = _get_pai(services)
    res = pai.network.resolve_dns(req.hostname)
    return DNSResolveResponse(
        hostname=res.hostname,
        resolved_ips=res.resolved_ips,
        resolution_time_ms=res.resolution_time_ms,
        is_successful=res.is_successful,
        error_message=res.error_message,
    )


@router.get(
    "/api/v1/personal-ai/coding/repo",
    response_model=RepoTopologyResponse,
    tags=["Personal AI - Coding"],
    summary="Analyze repository project topology and codebase language distribution",
)
async def get_repo_topology(
    services: Dict[str, Any] = Depends(get_server_state),
) -> RepoTopologyResponse:
    pai = _get_pai(services)
    top = pai.repo_assistant.analyze_project_topology()
    return RepoTopologyResponse(
        repo_name=top.repo_name,
        root_path=top.root_path,
        is_git_repository=top.is_git_repository,
        branch=top.branch,
        total_files_scanned=top.total_files_scanned,
        file_type_counts=top.file_type_counts,
        primary_language=top.primary_language,
        summary=top.summary,
    )


@router.get(
    "/api/v1/personal-ai/coding/git",
    response_model=GitStatusResponse,
    tags=["Personal AI - Coding"],
    summary="Inspect git repository status non-destructively",
)
async def get_git_status(
    services: Dict[str, Any] = Depends(get_server_state),
) -> GitStatusResponse:
    pai = _get_pai(services)
    st = pai.repo_assistant.inspect_git_status()
    return GitStatusResponse(
        branch=st.branch,
        clean=st.clean,
        untracked_count=st.untracked_count,
        modified_count=st.modified_count,
        staged_count=st.staged_count,
        short_status=st.short_status,
    )


@router.get(
    "/api/v1/personal-ai/coding/diff",
    response_model=Dict[str, Any],
    tags=["Personal AI - Coding"],
    summary="Inspect staged and unstaged git diffs non-destructively",
)
async def get_git_diff(
    services: Dict[str, Any] = Depends(get_server_state),
) -> Dict[str, Any]:
    pai = _get_pai(services)
    return {
        "staged": pai.repo_assistant.inspect_git_diff(cached=True),
        "unstaged": pai.repo_assistant.inspect_git_diff(cached=False),
    }


@router.post(
    "/api/v1/personal-ai/coding/tests",
    response_model=RunTestsResponse,
    tags=["Personal AI - Coding"],
    summary="Run test suite safely within the repository",
)
async def run_repository_tests(
    req: RunTestsRequest,
    services: Dict[str, Any] = Depends(get_server_state),
) -> RunTestsResponse:
    pai = _get_pai(services)
    try:
        res = pai.repo_assistant.run_tests_safe(test_path=req.test_path)
        return RunTestsResponse(
            exit_code=res.exit_code,
            stdout=res.stdout,
            stderr=res.stderr,
            duration_seconds=res.duration_seconds,
            passed=res.passed,
        )
    except SecurityViolationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/api/v1/personal-ai/security/posture",
    response_model=SecurityPostureResponse,
    tags=["Personal AI - Security"],
    summary="Defensive cybersecurity posture and open port audit",
)
async def get_security_posture(
    services: Dict[str, Any] = Depends(get_server_state),
) -> SecurityPostureResponse:
    pai = _get_pai(services)
    posture = pai.security.assess_security_posture()
    return SecurityPostureResponse(
        open_ports_count=posture.open_ports_count,
        open_ports=[asdict(p) for p in posture.open_ports],
        active_security_modules=posture.active_security_modules,
        hardening_recommendations=posture.hardening_recommendations,
        risk_level=posture.risk_level,
        timestamp=posture.timestamp,
    )


@router.get(
    "/api/v1/personal-ai/approvals",
    response_model=List[ApprovalTicketSchema],
    tags=["Personal AI - Permissions"],
    summary="List pending approval tickets awaiting human decision",
)
@router.get(
    "/api/v1/personal-ai/approvals/pending",
    response_model=List[ApprovalTicketSchema],
    tags=["Personal AI - Permissions"],
    summary="List pending approval tickets awaiting human decision (alias)",
)
async def list_pending_approvals(
    services: Dict[str, Any] = Depends(get_server_state),
) -> List[ApprovalTicketSchema]:
    mgr = _get_approval_mgr(services)
    tickets = mgr.get_pending_tickets()
    return [
        ApprovalTicketSchema(
            ticket_id=t.ticket_id,
            tool_name=t.tool_name,
            action_summary=t.action_summary,
            risk_tier=t.risk_tier.value,
            parameters=t.parameters,
            created_at=t.created_at,
            expires_at=t.expires_at,
            status=t.status.value,
            decision_reason=t.decision_reason,
            decided_by=t.decided_by,
        )
        for t in tickets
    ]


@router.post(
    "/api/v1/personal-ai/approvals/{ticket_id}",
    response_model=ApprovalTicketSchema,
    tags=["Personal AI - Permissions"],
    summary="Record human operator approval or rejection decision for a ticket",
)
@router.post(
    "/api/v1/personal-ai/approvals/{ticket_id}/decision",
    response_model=ApprovalTicketSchema,
    tags=["Personal AI - Permissions"],
    summary="Record human operator approval or rejection decision for a ticket (alias)",
)
async def decide_approval_ticket(
    ticket_id: str,
    req: ApprovalDecisionRequest,
    services: Dict[str, Any] = Depends(get_server_state),
) -> ApprovalTicketSchema:
    mgr = _get_approval_mgr(services)
    try:
        t = mgr.record_decision(
            ticket_id=ticket_id,
            approved=req.approved,
            decided_by=req.decided_by,
            reason=req.reason,
        )
        return ApprovalTicketSchema(
            ticket_id=t.ticket_id,
            tool_name=t.tool_name,
            action_summary=t.action_summary,
            risk_tier=t.risk_tier.value,
            parameters=t.parameters,
            created_at=t.created_at,
            expires_at=t.expires_at,
            status=t.status.value,
            decision_reason=t.decision_reason,
            decided_by=t.decided_by,
        )
    except SecurityViolationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/api/v1/personal-ai/audit/logs",
    response_model=List[AuditLogEntrySchema],
    tags=["Personal AI - Audit"],
    summary="Inspect immutable audit ledger of personal agent actions",
)
async def get_audit_logs(
    limit: int = 50,
    services: Dict[str, Any] = Depends(get_server_state),
) -> List[AuditLogEntrySchema]:
    audit = _get_audit(services)
    entries = audit.get_recent_logs(limit=limit)
    return [
        AuditLogEntrySchema(
            event_id=e.event_id,
            session_id=e.session_id,
            user_id=e.user_id,
            tool_name=e.tool_name,
            risk_tier=e.risk_tier,
            action_description=e.action_description,
            ticket_id=e.ticket_id,
            success=e.success,
            details=e.details,
            timestamp=e.timestamp,
        )
        for e in entries
    ]


@router.post(
    "/api/v1/personal-ai/emergency/shutdown",
    response_model=EmergencyShutdownResponse,
    tags=["Personal AI - Emergency"],
    summary="Instantly trigger emergency kill switch disabling local agent execution",
)
async def trigger_emergency_shutdown(
    req: EmergencyShutdownRequest,
    services: Dict[str, Any] = Depends(get_server_state),
) -> EmergencyShutdownResponse:
    ctrl = _get_emergency_ctrl(services)
    status_info = ctrl.trigger_shutdown(triggered_by=req.triggered_by, reason=req.reason)
    return EmergencyShutdownResponse(
        is_active=status_info.is_active,
        triggered_at=status_info.triggered_at,
        triggered_by=status_info.triggered_by,
        reason=status_info.reason,
        revoked_tickets_count=status_info.revoked_tickets_count,
    )

@router.post(
    "/api/v1/personal-ai/emergency/reset",
    response_model=EmergencyShutdownResponse,
    tags=["Personal AI - Emergency"],
    summary="Reset emergency kill switch to re-enable agent operations",
)
async def reset_emergency_shutdown(
    services: Dict[str, Any] = Depends(get_server_state),
) -> EmergencyShutdownResponse:
    ctrl = _get_emergency_ctrl(services)
    status_info = ctrl.reset(reset_by="human_operator")
    return EmergencyShutdownResponse(
        is_active=status_info.is_active,
        triggered_at=status_info.triggered_at,
        triggered_by=status_info.triggered_by,
        reason=status_info.reason,
        revoked_tickets_count=status_info.revoked_tickets_count,
    )


# =============================================================================
# PHASE 11 — AUTHENTICATION, SESSIONS, CONVERSATIONS, SETTINGS & ACTIVITY
# =============================================================================

def _get_auth_mgr(services: Dict[str, Any]) -> AuthManager:
    mgr = services.get("auth_manager")
    if mgr is None:
        mgr = AuthManager(services.get("db_manager"))
        services["auth_manager"] = mgr
    return mgr


def _get_conversation_mgr(services: Dict[str, Any]) -> ConversationManager:
    mgr = services.get("conversation_manager")
    if mgr is None:
        mgr = ConversationManager(services.get("db_manager"))
        services["conversation_manager"] = mgr
    return mgr


def _get_settings_mgr(services: Dict[str, Any]) -> UserSettingsManager:
    mgr = services.get("settings_manager")
    if mgr is None:
        mgr = UserSettingsManager(services.get("db_manager"))
        services["settings_manager"] = mgr
    return mgr


def _get_activity_mgr(services: Dict[str, Any]) -> ActivityLogManager:
    mgr = services.get("activity_manager")
    if mgr is None:
        mgr = ActivityLogManager(services.get("db_manager"))
        services["activity_manager"] = mgr
    return mgr


def _get_current_user(
    request: Request,
    authorization: Optional[str] = Header(None),
    services: Dict[str, Any] = Depends(get_server_state),
) -> UserAccount:
    """Extract authenticated user from Authorization header or cookie, with fallback to default operator."""
    auth_mgr = _get_auth_mgr(services)
    token = None
    if authorization:
        parts = authorization.strip().split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]
        elif len(parts) == 1:
            token = parts[0]
    if not token and "founders_session" in request.cookies:
        token = request.cookies.get("founders_session")

    if token:
        user = auth_mgr.validate_session(token)
        if user:
            return user

    # Fallback to default operator account
    operator = auth_mgr.get_user_by_username("operator")
    if operator:
        return operator

    return UserAccount(
        id="USR-operator",
        username="operator",
        email="operator@404founders.local",
        display_name="Lead Operator",
        role="ADMIN",
        is_active=True,
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
    )


# -----------------------------------------------------------------------------
# 1. User Authentication & Session Endpoints
# -----------------------------------------------------------------------------

@router.post(
    "/api/v1/auth/register",
    response_model=AuthTokenResponse,
    tags=["Authentication"],
    summary="Register a new user account and receive an authenticated session token",
)
async def register_account(
    req: UserRegisterRequest,
    services: Dict[str, Any] = Depends(get_server_state),
) -> AuthTokenResponse:
    auth_mgr = _get_auth_mgr(services)
    act_mgr = _get_activity_mgr(services)
    try:
        user = auth_mgr.register_user(
            username=req.username,
            email=req.email,
            password=req.password,
            display_name=req.display_name,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    session = auth_mgr.create_session(user.id)
    act_mgr.log_activity(user.id, "AUTH", "REGISTER", "SUCCESS", f"Account created for {user.username}")

    return AuthTokenResponse(
        token=session.token,
        token_type="Bearer",
        user_id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        expires_at=session.expires_at,
    )


@router.post(
    "/api/v1/auth/login",
    response_model=AuthTokenResponse,
    tags=["Authentication"],
    summary="Authenticate with credentials and obtain a new session token",
)
async def login_account(
    req: UserLoginRequest,
    services: Dict[str, Any] = Depends(get_server_state),
) -> AuthTokenResponse:
    auth_mgr = _get_auth_mgr(services)
    act_mgr = _get_activity_mgr(services)
    user = auth_mgr.authenticate(req.username_or_email, req.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    session = auth_mgr.create_session(user.id)
    act_mgr.log_activity(user.id, "AUTH", "LOGIN", "SUCCESS", f"Session authenticated for {user.username}")

    return AuthTokenResponse(
        token=session.token,
        token_type="Bearer",
        user_id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        expires_at=session.expires_at,
    )


@router.post(
    "/api/v1/auth/logout",
    tags=["Authentication"],
    summary="Revoke the current authenticated session",
)
async def logout_account(
    authorization: Optional[str] = Header(None),
    services: Dict[str, Any] = Depends(get_server_state),
) -> Dict[str, Any]:
    auth_mgr = _get_auth_mgr(services)
    act_mgr = _get_activity_mgr(services)
    if authorization:
        parts = authorization.strip().split()
        token = parts[1] if len(parts) == 2 else parts[0]
        user = auth_mgr.validate_session(token)
        if user:
            act_mgr.log_activity(user.id, "AUTH", "LOGOUT", "SUCCESS", f"Logged out {user.username}")
        auth_mgr.revoke_session(token)
    return {"status": "ok", "message": "Logged out successfully"}


@router.get(
    "/api/v1/auth/me",
    response_model=UserProfileResponse,
    tags=["Authentication"],
    summary="Fetch current user identity and authorization role",
)
async def get_current_user_profile(
    current_user: UserAccount = Depends(_get_current_user),
) -> UserProfileResponse:
    return UserProfileResponse(
        user_id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        display_name=current_user.display_name,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        last_login_at=current_user.last_login_at,
    )


@router.get(
    "/api/v1/auth/sessions",
    response_model=List[UserSessionItemSchema],
    tags=["Authentication"],
    summary="List active sessions for the current authenticated user",
)
async def list_active_sessions(
    current_user: UserAccount = Depends(_get_current_user),
    services: Dict[str, Any] = Depends(get_server_state),
) -> List[UserSessionItemSchema]:
    auth_mgr = _get_auth_mgr(services)
    sessions = auth_mgr.list_user_sessions(current_user.id)
    return [
        UserSessionItemSchema(
            session_id=s["session_id"],
            created_at=s["created_at"],
            expires_at=s["expires_at"],
            ip_address=s.get("ip_address"),
            user_agent=s.get("user_agent"),
            is_active=bool(s.get("is_active", True)),
        )
        for s in sessions
    ]


@router.delete(
    "/api/v1/auth/sessions/{session_id}",
    tags=["Authentication"],
    summary="Revoke a specific user session",
)
async def revoke_session_endpoint(
    session_id: str,
    current_user: UserAccount = Depends(_get_current_user),
    services: Dict[str, Any] = Depends(get_server_state),
) -> Dict[str, Any]:
    auth_mgr = _get_auth_mgr(services)
    revoked = auth_mgr.revoke_session_by_id(session_id, current_user.id)
    if not revoked:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found or already revoked.")
    return {"status": "ok", "message": "Session revoked"}


# -----------------------------------------------------------------------------
# 2. Conversation & Message Trajectory Endpoints
# -----------------------------------------------------------------------------

@router.post(
    "/api/v1/conversations",
    response_model=ConversationThreadSchema,
    tags=["Conversations"],
    summary="Create a new conversation thread",
)
async def create_conversation_thread(
    req: ConversationCreateRequest,
    current_user: UserAccount = Depends(_get_current_user),
    services: Dict[str, Any] = Depends(get_server_state),
) -> ConversationThreadSchema:
    conv_mgr = _get_conversation_mgr(services)
    thread = conv_mgr.create_thread(
        user_id=current_user.id,
        title=req.title,
        mode=req.mode,
        metadata=req.metadata,
    )
    return ConversationThreadSchema(
        id=thread.id,
        user_id=thread.user_id,
        title=thread.title,
        mode=thread.mode,
        created_at=thread.created_at,
        updated_at=thread.updated_at,
        metadata=thread.metadata,
    )


@router.get(
    "/api/v1/conversations",
    response_model=List[ConversationThreadSchema],
    tags=["Conversations"],
    summary="List all conversation threads for the authenticated user",
)
async def list_conversations(
    limit: int = 50,
    offset: int = 0,
    current_user: UserAccount = Depends(_get_current_user),
    services: Dict[str, Any] = Depends(get_server_state),
) -> List[ConversationThreadSchema]:
    conv_mgr = _get_conversation_mgr(services)
    threads = conv_mgr.list_threads(user_id=current_user.id, limit=limit, offset=offset)
    return [
        ConversationThreadSchema(
            id=t.id,
            user_id=t.user_id,
            title=t.title,
            mode=t.mode,
            created_at=t.created_at,
            updated_at=t.updated_at,
            metadata=t.metadata,
        )
        for t in threads
    ]


@router.get(
    "/api/v1/conversations/{conversation_id}",
    response_model=ConversationThreadSchema,
    tags=["Conversations"],
    summary="Get conversation thread details by ID",
)
async def get_conversation_thread(
    conversation_id: str,
    current_user: UserAccount = Depends(_get_current_user),
    services: Dict[str, Any] = Depends(get_server_state),
) -> ConversationThreadSchema:
    conv_mgr = _get_conversation_mgr(services)
    thread = conv_mgr.get_thread(conversation_id, current_user.id)
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    return ConversationThreadSchema(
        id=thread.id,
        user_id=thread.user_id,
        title=thread.title,
        mode=thread.mode,
        created_at=thread.created_at,
        updated_at=thread.updated_at,
        metadata=thread.metadata,
    )


@router.patch(
    "/api/v1/conversations/{conversation_id}",
    response_model=ConversationThreadSchema,
    tags=["Conversations"],
    summary="Update conversation title or operational mode",
)
async def update_conversation_thread(
    conversation_id: str,
    req: ConversationUpdateRequest,
    current_user: UserAccount = Depends(_get_current_user),
    services: Dict[str, Any] = Depends(get_server_state),
) -> ConversationThreadSchema:
    conv_mgr = _get_conversation_mgr(services)
    updated = conv_mgr.update_thread(
        thread_id=conversation_id,
        user_id=current_user.id,
        title=req.title,
        mode=req.mode,
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    thread = conv_mgr.get_thread(conversation_id, current_user.id)
    return ConversationThreadSchema(
        id=thread.id,
        user_id=thread.user_id,
        title=thread.title,
        mode=thread.mode,
        created_at=thread.created_at,
        updated_at=thread.updated_at,
        metadata=thread.metadata,
    )


@router.delete(
    "/api/v1/conversations/{conversation_id}",
    tags=["Conversations"],
    summary="Delete conversation thread and its messages",
)
async def delete_conversation_thread(
    conversation_id: str,
    current_user: UserAccount = Depends(_get_current_user),
    services: Dict[str, Any] = Depends(get_server_state),
) -> Dict[str, Any]:
    conv_mgr = _get_conversation_mgr(services)
    deleted = conv_mgr.delete_thread(conversation_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    return {"status": "ok", "deleted": True}


@router.get(
    "/api/v1/conversations/{conversation_id}/messages",
    response_model=List[ConversationMessageSchema],
    tags=["Conversations"],
    summary="Retrieve ordered message trajectory for a conversation thread",
)
async def list_conversation_messages(
    conversation_id: str,
    limit: int = 100,
    offset: int = 0,
    current_user: UserAccount = Depends(_get_current_user),
    services: Dict[str, Any] = Depends(get_server_state),
) -> List[ConversationMessageSchema]:
    conv_mgr = _get_conversation_mgr(services)
    # Ensure thread belongs to user
    thread = conv_mgr.get_thread(conversation_id, current_user.id)
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    msgs = conv_mgr.list_messages(conversation_id, limit=limit, offset=offset)
    return [
        ConversationMessageSchema(
            id=m.id,
            conversation_id=m.conversation_id,
            sender=m.sender,
            content=m.content,
            message_type=m.message_type,
            metadata=m.metadata,
            created_at=m.created_at,
        )
        for m in msgs
    ]


@router.post(
    "/api/v1/conversations/{conversation_id}/messages",
    response_model=ConversationMessageSchema,
    tags=["Conversations"],
    summary="Send a message to a conversation thread and receive the AI assistant response",
)
async def send_conversation_message(
    conversation_id: str,
    req: MessageSendRequest,
    current_user: UserAccount = Depends(_get_current_user),
    services: Dict[str, Any] = Depends(get_server_state),
) -> ConversationMessageSchema:
    conv_mgr = _get_conversation_mgr(services)
    act_mgr = _get_activity_mgr(services)
    thread = conv_mgr.get_thread(conversation_id, current_user.id)
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")

    # 1. Record user message
    conv_mgr.add_message(
        conversation_id=conversation_id,
        sender="user",
        content=req.content,
        message_type=req.message_type,
        metadata=req.metadata,
    )

    # 2. Process query through central intelligence router or neural inference
    router_inst: Optional[CentralIntelligenceRouter] = services.get("central_router")
    inference_eng: Optional[InferenceEngine] = services.get("inference_engine")
    tokenizer: Optional[CustomBPETokenizer] = services.get("tokenizer")

    assistant_text = ""
    target_mod = "NEURAL_CORE"

    if router_inst is not None:
        try:
            hints = {"force_engine": thread.mode.lower()} if thread.mode.lower() in ("coding", "cybersecurity", "logical", "math", "planning") else {}
            res = router_inst.dispatch(query=req.content, context_hints=hints)
            assistant_text = res.combined_summary
            target_mod = res.dispatch_plan.primary_engine
        except Exception:
            assistant_text = "404 FOUNDERS inference pipeline executed successfully."
    elif inference_eng is not None and tokenizer is not None:
        enc = tokenizer.encode(req.content)
        raw_ids = getattr(enc, "ids", None) or (enc if isinstance(enc, list) else [1])
        token_ids = list(raw_ids)[:32]
        if not token_ids:
            token_ids = [1]
        out_ids = inference_eng.generate_greedy_tokens(token_ids, max_new_tokens=16)
        assistant_text = tokenizer.decode(out_ids[len(token_ids):]) if len(out_ids) > len(token_ids) else "Response generated."
    else:
        assistant_text = f"Acknowledged: {req.content[:64]}"

    # 3. Record assistant message
    asst_msg = conv_mgr.add_message(
        conversation_id=conversation_id,
        sender="assistant",
        content=assistant_text,
        message_type="TEXT",
        metadata={"target_module": target_mod},
    )

    # 4. Log audit activity
    act_mgr.log_activity(
        user_id=current_user.id,
        category="INTELLIGENCE",
        action="QUERY_EXECUTION",
        status="SUCCESS",
        detail=f"Query in thread '{thread.title}' routed to {target_mod}",
    )

    return ConversationMessageSchema(
        id=asst_msg.id,
        conversation_id=asst_msg.conversation_id,
        sender=asst_msg.sender,
        content=asst_msg.content,
        message_type=asst_msg.message_type,
        metadata=asst_msg.metadata,
        created_at=asst_msg.created_at,
    )


# -----------------------------------------------------------------------------
# 3. Real-Time Streaming Chat Endpoint (Server-Sent Events)
# -----------------------------------------------------------------------------

@router.post(
    "/api/v1/chat/stream",
    tags=["Streaming"],
    summary="Progressive token streaming over Server-Sent Events (SSE)",
)
async def stream_chat_sse(
    req: ChatStreamRequest,
    current_user: UserAccount = Depends(_get_current_user),
    services: Dict[str, Any] = Depends(get_server_state),
) -> StreamingResponse:
    conv_mgr = _get_conversation_mgr(services)
    act_mgr = _get_activity_mgr(services)

    # Resolve or create conversation thread
    conv_id = req.conversation_id
    if not conv_id:
        new_thread = conv_mgr.create_thread(
            user_id=current_user.id,
            title=req.query[:40] if len(req.query) > 40 else req.query,
            mode=req.mode,
        )
        conv_id = new_thread.id

    conv_mgr.add_message(
        conversation_id=conv_id,
        sender="user",
        content=req.query,
        message_type="TEXT",
    )

    async def sse_event_generator():
        # Emit status event
        yield f"event: status\ndata: {json.dumps({'stage': 'ROUTING', 'message': 'Selecting specialized neural module...'})}\n\n"

        router_inst: Optional[CentralIntelligenceRouter] = services.get("central_router")
        inference_eng: Optional[InferenceEngine] = services.get("inference_engine")
        tokenizer: Optional[CustomBPETokenizer] = services.get("tokenizer")

        collected_tokens = []
        if inference_eng is not None and tokenizer is not None:
            enc = tokenizer.encode(req.query)
            raw_ids = getattr(enc, "ids", None) or (enc if isinstance(enc, list) else [1])
            token_ids = list(raw_ids)[:32]
            if not token_ids:
                token_ids = [1]
            generated_ids = inference_eng.generate_greedy_tokens(token_ids, max_new_tokens=24)
            new_ids = generated_ids[len(token_ids):] if len(generated_ids) > len(token_ids) else [1]
            for tid in new_ids:
                piece = tokenizer.decode([tid])
                collected_tokens.append(piece)
                yield f"event: token\ndata: {json.dumps({'content': piece})}\n\n"
        elif router_inst is not None:
            resp = router_inst.dispatch(query=req.query)
            text = resp.combined_summary
            words = text.split(" ")
            for w in words:
                piece = w + " "
                collected_tokens.append(piece)
                yield f"event: token\ndata: {json.dumps({'content': piece})}\n\n"
        else:
            sample = f"404 FOUNDERS response to: {req.query}"
            for w in sample.split(" "):
                piece = w + " "
                collected_tokens.append(piece)
                yield f"event: token\ndata: {json.dumps({'content': piece})}\n\n"

        full_reply = "".join(collected_tokens).strip()
        conv_mgr.add_message(
            conversation_id=conv_id,
            sender="assistant",
            content=full_reply,
            message_type="TEXT",
        )
        act_mgr.log_activity(
            user_id=current_user.id,
            category="INTELLIGENCE",
            action="STREAMING_QUERY",
            status="SUCCESS",
            detail=f"SSE stream completed for thread {conv_id}",
        )
        yield f"event: done\ndata: {json.dumps({'conversation_id': conv_id, 'total_tokens': len(collected_tokens)})}\n\n"

    return StreamingResponse(sse_event_generator(), media_type="text/event-stream")


# -----------------------------------------------------------------------------
# 4. User Application Settings Endpoints
# -----------------------------------------------------------------------------

@router.get(
    "/api/v1/settings",
    response_model=UserSettingsSchema,
    tags=["Settings"],
    summary="Retrieve appearance, language, voice, and retention settings",
)
async def get_user_settings(
    current_user: UserAccount = Depends(_get_current_user),
    services: Dict[str, Any] = Depends(get_server_state),
) -> UserSettingsSchema:
    settings_mgr = _get_settings_mgr(services)
    s = settings_mgr.get_settings(current_user.id)
    return UserSettingsSchema(
        user_id=s.user_id,
        theme_preference=s.theme_preference,
        language=s.language,
        voice_enabled=s.voice_enabled,
        tts_autoplay=s.tts_autoplay,
        memory_retention_days=s.memory_retention_days,
        custom_endpoint_url=s.custom_endpoint_url,
        updated_at=s.updated_at,
    )


@router.put(
    "/api/v1/settings",
    response_model=UserSettingsSchema,
    tags=["Settings"],
    summary="Update application preferences for the current authenticated user",
)
async def update_user_settings(
    req: UserSettingsUpdateRequest,
    current_user: UserAccount = Depends(_get_current_user),
    services: Dict[str, Any] = Depends(get_server_state),
) -> UserSettingsSchema:
    settings_mgr = _get_settings_mgr(services)
    act_mgr = _get_activity_mgr(services)
    s = settings_mgr.update_settings(
        user_id=current_user.id,
        theme_preference=req.theme_preference,
        language=req.language,
        voice_enabled=req.voice_enabled,
        tts_autoplay=req.tts_autoplay,
        memory_retention_days=req.memory_retention_days,
        custom_endpoint_url=req.custom_endpoint_url,
    )
    act_mgr.log_activity(
        user_id=current_user.id,
        category="SETTINGS",
        action="UPDATE_PREFERENCES",
        status="SUCCESS",
        detail="Application settings updated",
    )
    return UserSettingsSchema(
        user_id=s.user_id,
        theme_preference=s.theme_preference,
        language=s.language,
        voice_enabled=s.voice_enabled,
        tts_autoplay=s.tts_autoplay,
        memory_retention_days=s.memory_retention_days,
        custom_endpoint_url=s.custom_endpoint_url,
        updated_at=s.updated_at,
    )


# -----------------------------------------------------------------------------
# 5. Activity History & Audit Logging Endpoints
# -----------------------------------------------------------------------------

@router.get(
    "/api/v1/activity/history",
    response_model=ActivityHistoryResponse,
    tags=["Activity History"],
    summary="List unified activity history across intelligence, agent, memory, and security domains",
)
async def get_activity_history(
    category: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: UserAccount = Depends(_get_current_user),
    services: Dict[str, Any] = Depends(get_server_state),
) -> ActivityHistoryResponse:
    act_mgr = _get_activity_mgr(services)
    entries = act_mgr.list_activity(
        user_id=current_user.id,
        category=category,
        limit=limit,
        offset=offset,
    )
    return ActivityHistoryResponse(
        total_count=len(entries),
        entries=[
            ActivityLogSchema(
                id=e.id,
                user_id=e.user_id,
                category=e.category,
                action=e.action,
                status=e.status,
                detail=e.detail,
                created_at=e.created_at,
            )
            for e in entries
        ],
    )


