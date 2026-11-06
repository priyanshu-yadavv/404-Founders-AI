"""
404 FOUNDERS — Creative Problem-Solving Engine
Provides lateral thinking prompts, cross-domain analogy generation,
constraint relaxation, and divergent solution synthesis.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AnalogyMapping:
    """Represents a cross-domain analogy mapped to the problem space."""
    source_domain: str  # e.g. "Biological Systems", "Fluid Dynamics", "Urban Architecture"
    analogous_concept: str
    structural_mapping: str
    actionable_insight: str


@dataclass
class ConstraintRelaxation:
    """Identification and strategic relaxation of an implicit problem constraint."""
    assumed_constraint: str
    relaxation_scenario: str
    unlocked_solution_space: str


@dataclass
class CreativeSolutionVector:
    """A distinct synthesized creative solution approach."""
    title: str
    paradigm: str  # "INVERSION", "ANALOGY", "DECENTRALIZATION", "DECOUPLING"
    description: str
    feasibility_score: float  # 0.0 to 1.0
    novelty_score: float      # 0.0 to 1.0
    pros: List[str]
    cons: List[str]


@dataclass
class CreativeProblemResult:
    """Complete structured output for creative problem-solving."""
    problem: str
    inverted_problem: str
    analogies: List[AnalogyMapping]
    relaxed_constraints: List[ConstraintRelaxation]
    solution_vectors: List[CreativeSolutionVector]
    divergence_summary: str


class CreativeProblemSolvingEngine:
    """
    Creative problem-solving engine.
    Applies lateral thinking, TRIZ-inspired constraint relaxation,
    cross-disciplinary analogies, and divergent synthesis.
    """

    ANALOGY_TEMPLATES = [
        AnalogyMapping(
            source_domain="Biological Systems (Immunology)",
            analogous_concept="Antigen detection and adaptive memory",
            structural_mapping="Map systemic vulnerabilities to pathogen exposure, and mitigation to antibodies.",
            actionable_insight="Decentralize anomaly detection so endpoints produce local immune responses before notifying central coordination.",
        ),
        AnalogyMapping(
            source_domain="Civil Engineering (Hydraulics)",
            analogous_concept="Surge tanks and spillways in high-pressure reservoirs",
            structural_mapping="Map traffic/workload spikes to fluid volume surges, and buffers to spillways.",
            actionable_insight="Implement backpressure dissipation channels and rate-decoupling reservoirs to prevent catastrophic cascading failure.",
        ),
        AnalogyMapping(
            source_domain="Forest Ecology (Mycelial Networks)",
            analogous_concept="Nutrient redistribution across symbiotic root graphs",
            structural_mapping="Map computing nodes to trees, and peer-to-peer data links to fungal hyphae.",
            actionable_insight="Route surplus resources and compute dynamically to starved nodes through direct neighbor sharing rather than top-down allocation.",
        ),
    ]

    def invert_problem(self, problem: str) -> str:
        """Formulate inverted problem: 'How could we maximize or guarantee the failure mode?'"""
        return (
            f"Inverted Problem Formulation: What specific actions or architectural constraints "
            f"would guarantee that '{problem}' becomes completely unsolvable, maximized in cost, or irreversibly bottlenecked?"
        )

    def relax_constraints(self, explicit_constraints: Optional[List[str]] = None) -> List[ConstraintRelaxation]:
        """Systematically relax standard default constraints to reveal hidden solution pathways."""
        constraints = explicit_constraints or ["Synchronous execution", "Centralized authority", "Instantaneous delivery"]
        relaxations: List[ConstraintRelaxation] = []

        for c in constraints:
            relaxations.append(ConstraintRelaxation(
                assumed_constraint=c,
                relaxation_scenario=f"What if '{c}' is entirely optional or deferred asynchronously?",
                unlocked_solution_space=(
                    f"By removing '{c}', processing can be batched, distributed among untrusted nodes, "
                    f"or resolved lazily only when requested."
                ),
            ))
        return relaxations

    def synthesize_solution_vectors(self, problem: str) -> List[CreativeSolutionVector]:
        """Generate diverse, orthogonal solution vectors."""
        vectors = [
            CreativeSolutionVector(
                title="Decoupled Asynchronous Staging",
                paradigm="DECOUPLING",
                description=f"Separate the ingestion, analysis, and execution phases of '{problem}' into discrete independent pipelines.",
                feasibility_score=0.90,
                novelty_score=0.65,
                pros=["High reliability", "Isolated fault domains", "Scales horizontally"],
                cons=["Increased architectural complexity", "Eventual consistency trade-off"],
            ),
            CreativeSolutionVector(
                title="Biological Mycelial Distribution",
                paradigm="ANALOGY",
                description=f"Deploy peer-to-peer gossip gossip protocols where nodes solve micro-slices of '{problem}' collaboratively.",
                feasibility_score=0.75,
                novelty_score=0.88,
                pros=["Zero single point of failure", "Self-healing topology"],
                cons=["Complex synchronization", "Non-deterministic propagation latency"],
            ),
            CreativeSolutionVector(
                title="Inverse Negative Elimination",
                paradigm="INVERSION",
                description=f"Rather than solving '{problem}' directly, eliminate all upstream conditions that trigger it.",
                feasibility_score=0.85,
                novelty_score=0.80,
                pros=["Removes technical debt at the root", "Zero ongoing runtime overhead"],
                cons=["Requires upstream organizational or architectural buy-in"],
            ),
        ]
        return vectors

    def solve(
        self,
        problem: str,
        constraints: Optional[List[str]] = None,
    ) -> CreativeProblemResult:
        """Execute creative divergent thinking pipeline on a problem statement."""
        if not problem.strip():
            raise ValueError("Problem statement cannot be empty.")

        inverted = self.invert_problem(problem)
        analogies = list(self.ANALOGY_TEMPLATES)
        relaxations = self.relax_constraints(constraints)
        solutions = self.synthesize_solution_vectors(problem)

        summary = (
            f"Generated {len(solutions)} divergent solution vectors and {len(analogies)} cross-domain analogies. "
            f"Analyzed {len(relaxations)} constraint relaxations to break fixed mental models."
        )

        return CreativeProblemResult(
            problem=problem,
            inverted_problem=inverted,
            analogies=analogies,
            relaxed_constraints=relaxations,
            solution_vectors=solutions,
            divergence_summary=summary,
        )
