"""
404 FOUNDERS — FastAPI Application Factory
Builds the ASGI REST API application with safe CORS middleware, lifecycle state management,
and interactive OpenAPI documentation.
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.rest.routes import router
from core.intelligence.central_router import CentralIntelligenceRouter
from core.intelligence.neural_core import NeuralCore, NeuralCoreConfig
from database.connection import DatabaseManager
from learning.continual.learning_pipeline import ControlledLearningPipeline
from learning.feedback.feedback_system import FeedbackSystem
from memory.consolidation.consolidation_engine import MemoryConsolidationEngine
from memory.contextual_memory import ContextualMemoryEngine
from memory.episodic.episodic_memory import EpisodicMemory
from memory.knowledge.knowledge_memory import KnowledgeMemory
from memory.long_term.long_term_memory import LongTermMemory
from memory.personalization.personalization_engine import PersonalizationEngine
from memory.retrieval.retrieval_engine import HybridMemoryRetrievalEngine
from memory.short_term.short_term_memory import ShortTermMemory
from memory.user_preferences import UserPreferenceMemory
from memory.working_memory import WorkingMemory
from multimodal.modality_router import ModalityRouter
from neural_architecture.inference import InferenceEngine
from personal_ai.controller import PersonalAIController
from personal_ai.memory_bridge import PersonalAIMemoryBridge
from tokenizer import CustomBPETokenizer

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def initialize_runtime_services() -> Dict[str, Any]:
    """Initializes and returns shared runtime services: tokenizer and neural core."""
    tokenizer_path = REPO_ROOT / "configs/tokenizer/tokenizer_model.json"
    if tokenizer_path.is_file():
        tokenizer = CustomBPETokenizer.load(tokenizer_path)
    else:
        # Fallback to in-memory tokenizer if JSON artifact not found
        tokenizer = CustomBPETokenizer()

    # Initialize custom neural core using tokenizer's exact vocabulary size
    vocab_size = max(512, tokenizer.vocab_size)
    core_cfg = NeuralCoreConfig(
        d_model=128,
        n_layers=2,
        n_heads=4,
        vocab_size=vocab_size,
        max_seq_len=512,
        random_seed=404,
    )
    neural_model = NeuralCore(config=core_cfg)
    inference_engine = InferenceEngine(model=neural_model)
    central_router = CentralIntelligenceRouter(d_model=core_cfg.d_model)
    modality_router = ModalityRouter(central_router=central_router)

    # Multi-Layer Memory & Continual Learning Services
    db_mgr = DatabaseManager.get_instance()
    short_term_mem = ShortTermMemory(db_mgr)
    long_term_mem = LongTermMemory(db_mgr)
    working_mem = WorkingMemory(db_mgr)
    episodic_mem = EpisodicMemory(db_mgr)
    knowledge_mem = KnowledgeMemory(db_mgr)
    pref_mem = UserPreferenceMemory(db_mgr)
    retrieval_eng = HybridMemoryRetrievalEngine(db_mgr)
    consolidation_eng = MemoryConsolidationEngine(db_mgr)
    personalization_eng = PersonalizationEngine(pref_memory=pref_mem, db_manager=db_mgr)
    contextual_mem = ContextualMemoryEngine(
        db_manager=db_mgr,
        short_term=short_term_mem,
        working_mem=working_mem,
        retrieval_engine=retrieval_eng,
        personalization=personalization_eng,
    )
    feedback_sys = FeedbackSystem(db_mgr)
    learning_pipe = ControlledLearningPipeline(db_manager=db_mgr, feedback_sys=feedback_sys)

    # Phase 10 — Personal AI Subsystems
    personal_ai_ctrl = PersonalAIController(
        memory_bridge=PersonalAIMemoryBridge(
            db_manager=db_mgr,
            pref_memory=pref_mem,
            episodic_memory=episodic_mem,
            long_term_memory=long_term_mem,
            working_memory=working_mem,
        )
    )

    return {
        "tokenizer": tokenizer,
        "neural_model": neural_model,
        "inference_engine": inference_engine,
        "central_router": central_router,
        "modality_router": modality_router,
        "db_manager": db_mgr,
        "short_term_memory": short_term_mem,
        "long_term_memory": long_term_mem,
        "working_memory": working_mem,
        "episodic_memory": episodic_mem,
        "knowledge_memory": knowledge_mem,
        "user_preference_memory": pref_mem,
        "retrieval_engine": retrieval_eng,
        "consolidation_engine": consolidation_eng,
        "personalization_engine": personalization_eng,
        "contextual_memory": contextual_mem,
        "feedback_system": feedback_sys,
        "learning_pipeline": learning_pipe,
        "personal_ai_controller": personal_ai_ctrl,
        "agent_runtime": personal_ai_ctrl.runtime,
        "approval_manager": personal_ai_ctrl.approval_mgr,
        "emergency_controller": personal_ai_ctrl.emergency_ctrl,
        "agent_audit_system": personal_ai_ctrl.audit,
        "start_time": time.time(),
    }


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manages application startup and teardown lifecycle."""
    # Startup: Initialize services if not already injected
    if not hasattr(app.state, "services") or not app.state.services:
        app.state.services = initialize_runtime_services()
    yield
    # Teardown logic can go here


def create_app(
    services: Optional[Dict[str, Any]] = None,
    allowed_origins: Optional[list[str]] = None,
) -> FastAPI:
    """Creates and configures the 404 FOUNDERS FastAPI application."""
    app = FastAPI(
        title="404 FOUNDERS API",
        description=(
            "Intelligence Without Boundaries — Unified REST API for the custom multimodal "
            "foundation AI and personal operating intelligence system."
        ),
        version="0.5.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Safe CORS configuration: allows local dev frontend (port 5173 / 3000) and localhost
    origins = allowed_origins or [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    if services is not None:
        app.state.services = services

    # Mount API routers
    app.include_router(router)

    return app


# Default ASGI application instance for uvicorn
app = create_app()
