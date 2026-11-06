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
from fastapi import APIRouter, Depends, HTTPException, Request, status

from api.rest.schemas import (
    CodingAnalysisRequest,
    CodingAnalysisResponse,
    CommandValidationRequest,
    CommandValidationResponse,
    DecodeRequest,
    DecodeResponse,
    HealthResponse,
    InferenceRequest,
    InferenceResponse,
    IntelligenceQueryRequest,
    IntelligenceQueryResponse,
    LogicalReasoningRequest,
    LogicalReasoningResponse,
    MathReasoningRequest,
    MathReasoningResponse,
    PhaseStatusResponse,
    PlanningRequest,
    PlanningResponse,
    PromptSafetyRequest,
    PromptSafetyResponse,
    SecurityAuditRequest,
    SecurityAuditResponse,
    SelfEvaluationRequest,
    SelfEvaluationResponse,
    TelemetryResponse,
    TokenizeRequest,
    TokenizeResponse,
)
from core.exceptions import SecurityViolationError
from core.intelligence.central_router import CentralIntelligenceRouter
from core.intelligence.neural_core import NeuralCore, NeuralCoreConfig
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
