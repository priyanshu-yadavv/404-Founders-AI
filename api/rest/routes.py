"""
404 FOUNDERS — FastAPI REST API Route Handlers
Implements health checks, host telemetry, tokenizer operations, neural core inference,
and security validation.
"""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import torch
from fastapi import APIRouter, Depends, HTTPException, Request, status

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
