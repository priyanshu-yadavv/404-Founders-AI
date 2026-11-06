"""
404 FOUNDERS — Central Intelligence Router
Connects all 12 modular intelligence engines through the existing hybrid routing architecture.
Supports intent classification, multi-engine dispatch, composite synthesis,
conflict resolution, and graceful fallback handling.
"""

from dataclasses import dataclass, field
import re
from typing import Any, Dict, List, Optional, Set
import torch

from agent.planner.planning_engine import PlanningDecisionEngine
from core.intelligence.knowledge_engine import GeneralKnowledgeEngine
from core.intelligence.language_engine import LanguageCommunicationEngine
from core.intelligence.research_engine import ResearchAnalysisEngine
from core.intelligence.self_evaluation import SelfEvaluationEngine
from core.reasoning.creative import CreativeProblemSolvingEngine
from core.reasoning.critical import CriticalThinkingEngine
from core.reasoning.logical import LogicalReasoningEngine
from core.reasoning.mathematical import MathematicalReasoningEngine
from core.reasoning.scientific import ScientificReasoningEngine
from core.routing.base import RoutingDecision
from core.routing.dynamic_router import DynamicRouter
from personal_ai.coding_assistant.coding_engine import CodingIntelligenceEngine
from personal_ai.cybersecurity.cyber_engine import CybersecurityIntelligenceEngine


@dataclass
class EngineDispatchPlan:
    """Represents the routing dispatch plan for an incoming request."""
    primary_engine: str
    secondary_engines: List[str]
    intent_confidence: float
    detected_intents: List[str]
    routing_decision: Optional[RoutingDecision] = None


@dataclass
class EngineExecutionOutput:
    """Structured result returned by an individual intelligence engine."""
    engine_name: str
    is_successful: bool
    data: Any
    error_message: Optional[str] = None


@dataclass
class CentralRoutingResult:
    """Consolidated multi-engine execution response."""
    query: str
    dispatch_plan: EngineDispatchPlan
    engine_outputs: Dict[str, EngineExecutionOutput]
    conflicts_detected: List[str]
    combined_summary: str
    is_fallback_used: bool = False


class CentralIntelligenceRouter:
    """
    Central Intelligence Coordinator.
    Wraps the existing DynamicRouter to dispatch user and system queries
    across the 12 specialized intelligence engines, combining their outputs
    and resolving cross-module discrepancies.
    """

    INTENT_KEYWORDS: Dict[str, List[str]] = {
        "mathematical": ["calculate", "solve", "equation", "derivative", "integral", "matrix", "algebra", "arithmetic", "sin(", "cos("],
        "coding": ["code", "function", "class", "syntax", "refactor", "complexity", "debug", "python", "rust", "cpp", "javascript"],
        "cybersecurity": ["security", "vulnerability", "cvss", "exploit", "threat", "firewall", "log analysis", "injection", "reconnaissance"],
        "logical": ["deduce", "premise", "contradiction", "validity", "syllogism", "if-then", "assumption"],
        "scientific": ["physics", "kinematics", "ohm's law", "ideal gas", "hypothesis", "falsifiable", "scientific"],
        "critical_thinking": ["fallacy", "bias", "ad hominem", "straw man", "evidence quality", "correlation vs causation"],
        "creative": ["brainstorm", "lateral thinking", "analogy", "creative", "relax constraint", "invert problem"],
        "research": ["synthesize", "cross-reference", "literature", "citations", "document comparison", "corroborate"],
        "planning": ["plan", "subtasks", "decompose goal", "dependencies", "task list", "execution order"],
        "self_evaluation": ["evaluate output", "check errors", "verify consistency", "audit response"],
        "language": ["summarize", "readability", "rewrite", "tone", "style adaptation", "flesch"],
        "knowledge": ["what is", "define", "entity", "domain", "concept"],
    }

    def __init__(
        self,
        d_model: int = 128,
        dynamic_router: Optional[DynamicRouter] = None,
    ) -> None:
        self.dynamic_router = dynamic_router or DynamicRouter(d_model=d_model, num_experts=4)

        # Initialize the 12 specialized intelligence engines
        self.logical_engine = LogicalReasoningEngine()
        self.mathematical_engine = MathematicalReasoningEngine()
        self.scientific_engine = ScientificReasoningEngine()
        self.coding_engine = CodingIntelligenceEngine()
        self.cybersecurity_engine = CybersecurityIntelligenceEngine()
        self.critical_engine = CriticalThinkingEngine()
        self.creative_engine = CreativeProblemSolvingEngine()
        self.research_engine = ResearchAnalysisEngine()
        self.planning_engine = PlanningDecisionEngine()
        self.self_eval_engine = SelfEvaluationEngine()
        self.language_engine = LanguageCommunicationEngine()
        self.knowledge_engine = GeneralKnowledgeEngine()

        self.engines: Dict[str, Any] = {
            "logical": self.logical_engine,
            "mathematical": self.mathematical_engine,
            "scientific": self.scientific_engine,
            "coding": self.coding_engine,
            "cybersecurity": self.cybersecurity_engine,
            "critical_thinking": self.critical_engine,
            "creative": self.creative_engine,
            "research": self.research_engine,
            "planning": self.planning_engine,
            "self_evaluation": self.self_eval_engine,
            "language": self.language_engine,
            "knowledge": self.knowledge_engine,
        }

    def classify_intent(self, query: str, context_hints: Optional[Dict[str, Any]] = None) -> EngineDispatchPlan:
        """Classify query intent against known engine vocabularies and context hints."""
        hints = context_hints or {}
        forced_engine = hints.get("force_engine")

        if forced_engine and forced_engine in self.engines:
            return EngineDispatchPlan(
                primary_engine=forced_engine,
                secondary_engines=[],
                intent_confidence=1.0,
                detected_intents=[forced_engine],
            )

        lower_q = query.lower()
        scored_intents: List[Tuple[str, int]] = []

        for engine_name, keywords in self.INTENT_KEYWORDS.items():
            matches = sum(1 for kw in keywords if kw in lower_q)
            if matches > 0:
                scored_intents.append((engine_name, matches))

        scored_intents.sort(key=lambda x: x[1], reverse=True)

        if not scored_intents:
            # Fallback to general knowledge engine
            return EngineDispatchPlan(
                primary_engine="knowledge",
                secondary_engines=[],
                intent_confidence=0.50,
                detected_intents=["knowledge"],
            )

        primary = scored_intents[0][0]
        confidence = min(0.99, 0.60 + 0.10 * scored_intents[0][1])

        # Secondary engines for composite routing
        secondary = [item[0] for item in scored_intents[1:3]]

        # Domain composite pairings:
        # If coding is primary and query contains security keywords, add cybersecurity
        if primary == "coding" and any(k in lower_q for k in ["secure", "unsafe", "vulnerability", "sanitize"]):
            if "cybersecurity" not in secondary:
                secondary.append("cybersecurity")

        # If planning is primary, add logical verification
        if primary == "planning" and "logical" not in secondary:
            secondary.append("logical")

        return EngineDispatchPlan(
            primary_engine=primary,
            secondary_engines=secondary,
            intent_confidence=round(confidence, 2),
            detected_intents=[item[0] for item in scored_intents],
        )

    def dispatch(
        self,
        query: str,
        context_hints: Optional[Dict[str, Any]] = None,
        x_tensor: Optional[torch.Tensor] = None,
    ) -> CentralRoutingResult:
        """Dispatch query to primary and secondary engines and reconcile results."""
        if not query.strip():
            raise ValueError("Query string cannot be empty.")

        hints = context_hints or {}
        plan = self.classify_intent(query, hints)

        # Call underlying DynamicRouter for neural routing decision tracking
        if x_tensor is not None:
            plan.routing_decision = self.dynamic_router.route(x_tensor, hints)
        else:
            # Create lightweight dummy tensor for routing policy evaluation
            dummy_x = torch.zeros((1, self.dynamic_router.learned_router.d_model))
            plan.routing_decision = self.dynamic_router.route(dummy_x, hints)

        engine_outputs: Dict[str, EngineExecutionOutput] = {}
        target_engines = [plan.primary_engine] + plan.secondary_engines

        for eng_name in target_engines:
            eng = self.engines.get(eng_name)
            if not eng:
                continue

            try:
                res_data = self._execute_engine(eng_name, eng, query, hints)
                engine_outputs[eng_name] = EngineExecutionOutput(
                    engine_name=eng_name,
                    is_successful=True,
                    data=res_data,
                )
            except Exception as e:
                engine_outputs[eng_name] = EngineExecutionOutput(
                    engine_name=eng_name,
                    is_successful=False,
                    data=None,
                    error_message=str(e),
                )

        # Detect cross-engine conflicts
        conflicts = self._detect_conflicts(engine_outputs)

        # Combine summaries
        summaries: List[str] = []
        for name, out in engine_outputs.items():
            if out.is_successful and out.data:
                # Check for standard summary attribute
                summ = getattr(out.data, "summary", None)
                if not summ and isinstance(out.data, dict):
                    summ = str(out.data.get("summary", ""))
                if summ:
                    summaries.append(f"[{name.upper()}]: {summ}")
                else:
                    summaries.append(f"[{name.upper()}]: Processed successfully.")
            elif not out.is_successful:
                summaries.append(f"[{name.upper()}]: Execution failed ({out.error_message})")

        combined = " | ".join(summaries) if summaries else "Processed query with active engines."

        return CentralRoutingResult(
            query=query,
            dispatch_plan=plan,
            engine_outputs=engine_outputs,
            conflicts_detected=conflicts,
            combined_summary=combined,
            is_fallback_used=plan.primary_engine == "knowledge" and plan.intent_confidence <= 0.50,
        )

    def _execute_engine(
        self,
        name: str,
        engine: Any,
        query: str,
        hints: Dict[str, Any],
    ) -> Any:
        """Route to appropriate method signature on target engine."""
        if name == "logical":
            return engine.analyze(query, premises=hints.get("premises"), candidates=hints.get("candidates"))
        elif name == "mathematical":
            # If explicit expression in hints or query
            expr = hints.get("expression") or query
            return engine.evaluate_arithmetic(expr)
        elif name == "scientific":
            return engine.analyze(query, provided_sources=hints.get("sources"))
        elif name == "coding":
            code = hints.get("code") or query
            if not hints.get("code"):
                code = re.sub(r"^(analyze|review|check|inspect)\s+([a-zA-Z0-9_\-]+\s+)?code[:\s]+", "", code.strip(), flags=re.IGNORECASE)
            return engine.analyze(code, language_hint=hints.get("language"))
        elif name == "cybersecurity":
            return engine.audit(query, logs=hints.get("logs"), file_sample=hints.get("file_sample"))
        elif name == "critical_thinking":
            return engine.analyze(query)
        elif name == "creative":
            return engine.solve(query, constraints=hints.get("constraints"))
        elif name == "research":
            return engine.synthesize(query, sources=hints.get("sources", []))
        elif name == "planning":
            return engine.create_plan(query, subtasks_data=hints.get("subtasks"))
        elif name == "self_evaluation":
            candidate = hints.get("candidate_output") or query
            return engine.evaluate(query, candidate, log_feedback=hints.get("log_feedback", False))
        elif name == "language":
            return engine.process(query)
        elif name == "knowledge":
            return engine.process(query, context_facts=hints.get("context_facts"))
        else:
            raise ValueError(f"Unknown engine target: '{name}'")

    def _detect_conflicts(self, outputs: Dict[str, EngineExecutionOutput]) -> List[str]:
        """Detect cross-module contradictions (e.g. valid syntax vs high security threat)."""
        conflicts: List[str] = []

        code_out = outputs.get("coding")
        sec_out = outputs.get("cybersecurity")

        if code_out and sec_out and code_out.is_successful and sec_out.is_successful:
            code_data = code_out.data
            sec_data = sec_out.data
            if getattr(code_data, "is_valid_syntax", False) and getattr(sec_data, "threats_identified", []):
                critical_threats = [t for t in sec_data.threats_identified if getattr(t, "severity", "") == "CRITICAL"]
                if critical_threats:
                    conflicts.append("Code is syntactically valid but flagged as containing critical security threats.")

        return conflicts
