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
    CommandValidationRequest,
    CommandValidationResponse,
    DecodeRequest,
    DecodeResponse,
    HealthResponse,
    InferenceRequest,
    InferenceResponse,
    PhaseStatusResponse,
    PromptSafetyRequest,
    PromptSafetyResponse,
    TelemetryResponse,
    TokenizeRequest,
    TokenizeResponse,
)
from core.exceptions import SecurityViolationError
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
    return request.app.state.services


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
