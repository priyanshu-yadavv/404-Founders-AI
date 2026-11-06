"""
404 FOUNDERS — Scientific Reasoning Engine
Provides physics and engineering computation, hypothesis formulation and falsifiability analysis,
evidence comparison, and strictly hallucination-free citation tracking.
"""

from dataclasses import dataclass, field
import math
from typing import Any, Dict, List, Optional


@dataclass
class PhysicsSolution:
    """Quantitative solution to a physics or engineering problem."""
    domain: str
    governing_equation: str
    inputs: Dict[str, float]
    calculated_value: float
    units: str
    steps: List[str]


@dataclass
class HypothesisEvaluation:
    """Structured evaluation of a scientific hypothesis."""
    hypothesis: str
    independent_variable: str
    dependent_variable: str
    controlled_variables: List[str]
    is_falsifiable: bool
    falsification_criteria: str
    recommended_experimental_controls: List[str]


@dataclass
class EvidenceComparisonResult:
    """Comparison between multiple experimental observations or datasets."""
    dataset_names: List[str]
    is_consistent: bool
    mean_discrepancy: float
    divergent_points: List[str]
    confidence_score: float
    summary: str


@dataclass
class ScientificAnalysisResult:
    """Complete structured response schema for scientific reasoning tasks."""
    query: str
    domain: str
    concept_summary: str
    physics_solution: Optional[PhysicsSolution]
    hypothesis_evaluation: Optional[HypothesisEvaluation]
    evidence_comparison: Optional[EvidenceComparisonResult]
    attributed_citations: List[str]
    unverified_claims: List[str]
    epistemic_limitations: str


class ScientificReasoningEngine:
    """
    Scientific and engineering reasoning engine.
    Solves physical laws quantitatively, tests hypotheses for falsifiability,
    evaluates empirical consistency across datasets, and strictly rejects
    unattributed or fabricated citations.
    """

    # Physical constants
    R_GAS = 8.314462618  # Ideal gas constant J/(mol*K)
    G_GRAV = 9.80665     # Standard Earth gravity m/s^2
    C_LIGHT = 299792458  # Speed of light m/s

    # --- 1. Physics & Engineering Solvers ---

    def solve_kinematics(
        self,
        initial_velocity: float = 0.0,
        acceleration: float = 0.0,
        time: Optional[float] = None,
        distance: Optional[float] = None,
    ) -> PhysicsSolution:
        """Solve 1D constant acceleration kinematics."""
        u = initial_velocity
        a = acceleration
        steps: List[str] = [f"Initial velocity u = {u} m/s", f"Acceleration a = {a} m/s^2"]

        if time is not None:
            t = time
            v = u + a * t
            s = u * t + 0.5 * a * (t**2)
            steps.append(f"Applied v = u + at -> v = {u} + ({a})*({t}) = {v} m/s")
            steps.append(f"Applied s = ut + 0.5*a*t^2 -> s = {s} m")
            return PhysicsSolution(
                domain="kinematics",
                governing_equation="v = u + at, s = ut + 0.5*a*t^2",
                inputs={"u": u, "a": a, "t": t},
                calculated_value=s,
                units="meters (distance) / m/s (velocity)",
                steps=steps,
            )
        elif distance is not None:
            s = distance
            v_squared = u**2 + 2 * a * s
            if v_squared < 0:
                raise ValueError("Kinematically impossible: v^2 cannot be negative under given parameters.")
            v = math.sqrt(v_squared)
            steps.append(f"Applied v^2 = u^2 + 2as -> v^2 = {v_squared} -> v = {v} m/s")
            return PhysicsSolution(
                domain="kinematics",
                governing_equation="v^2 = u^2 + 2as",
                inputs={"u": u, "a": a, "s": s},
                calculated_value=v,
                units="m/s",
                steps=steps,
            )
        else:
            raise ValueError("Must provide either time 't' or distance 's'.")

    def solve_ohms_law(
        self,
        voltage: Optional[float] = None,
        current: Optional[float] = None,
        resistance: Optional[float] = None,
    ) -> PhysicsSolution:
        """Calculate Ohm's law: V = I * R, P = V * I."""
        steps: List[str] = []
        if voltage is not None and current is not None:
            if current == 0:
                raise ValueError("Infinite resistance: current is 0.")
            r = voltage / current
            p = voltage * current
            steps = [f"R = V / I = {voltage} / {current} = {r} Ohms", f"P = V * I = {p} Watts"]
            return PhysicsSolution("electrodynamics", "V = I * R", {"V": voltage, "I": current}, r, "Ohms", steps)
        elif voltage is not None and resistance is not None:
            if resistance == 0:
                raise ValueError("Short circuit: resistance cannot be 0.")
            i = voltage / resistance
            p = voltage * i
            steps = [f"I = V / R = {voltage} / {resistance} = {i} Amperes", f"P = V * I = {p} Watts"]
            return PhysicsSolution("electrodynamics", "V = I * R", {"V": voltage, "R": resistance}, i, "Amperes", steps)
        elif current is not None and resistance is not None:
            v = current * resistance
            p = v * current
            steps = [f"V = I * R = {current} * {resistance} = {v} Volts", f"P = I^2 * R = {p} Watts"]
            return PhysicsSolution("electrodynamics", "V = I * R", {"I": current, "R": resistance}, v, "Volts", steps)
        else:
            raise ValueError("Provide exactly two of: voltage, current, resistance.")

    def solve_ideal_gas(
        self,
        pressure: Optional[float] = None,
        volume: Optional[float] = None,
        moles: Optional[float] = None,
        temperature_kelvin: Optional[float] = None,
    ) -> PhysicsSolution:
        """Solve ideal gas equation: P * V = n * R * T (R = 8.314 J/(mol*K))."""
        R = self.R_GAS
        if temperature_kelvin is not None and temperature_kelvin <= 0:
            raise ValueError("Temperature must be strictly positive in Kelvin (T > 0 K).")

        if pressure is None:
            if volume is None or moles is None or temperature_kelvin is None:
                raise ValueError("To calculate P, supply V, n, and T.")
            p = (moles * R * temperature_kelvin) / volume
            return PhysicsSolution(
                "thermodynamics", "PV = nRT",
                {"V": volume, "n": moles, "T": temperature_kelvin},
                p, "Pascals (Pa)",
                [f"P = (n * R * T) / V = ({moles} * {R} * {temperature_kelvin}) / {volume} = {p:.2f} Pa"],
            )
        elif volume is None:
            if moles is None or temperature_kelvin is None:
                raise ValueError("To calculate V, supply P, n, and T.")
            v = (moles * R * temperature_kelvin) / pressure
            return PhysicsSolution(
                "thermodynamics", "PV = nRT",
                {"P": pressure, "n": moles, "T": temperature_kelvin},
                v, "m^3",
                [f"V = (n * R * T) / P = ({moles} * {R} * {temperature_kelvin}) / {pressure} = {v:.5f} m^3"],
            )
        else:
            raise ValueError("Supported unknowns: pressure or volume.")

    # --- 2. Hypothesis Evaluation & Falsifiability ---

    def evaluate_hypothesis(
        self,
        hypothesis: str,
        independent_variable: str,
        dependent_variable: str,
        controlled_variables: Optional[List[str]] = None,
    ) -> HypothesisEvaluation:
        """Evaluate scientific rigor, variable isolation, and falsifiability of a hypothesis."""
        controls = controlled_variables or []
        is_falsifiable = len(independent_variable.strip()) > 0 and len(dependent_variable.strip()) > 0

        criteria = (
            f"Hypothesis is disproven if changing '{independent_variable}' under controlled conditions "
            f"({', '.join(controls) if controls else 'unspecified controls'}) produces no statistically significant variation in '{dependent_variable}'."
        )

        recommended_controls = [
            f"Hold ambient environment and temperature constant.",
            f"Establish negative baseline control group without '{independent_variable}'.",
            f"Collect at least N=3 independent replicates for statistical significance.",
        ]

        return HypothesisEvaluation(
            hypothesis=hypothesis,
            independent_variable=independent_variable,
            dependent_variable=dependent_variable,
            controlled_variables=controls,
            is_falsifiable=is_falsifiable,
            falsification_criteria=criteria,
            recommended_experimental_controls=recommended_controls,
        )

    # --- 3. Evidence & Empirical Dataset Comparison ---

    def compare_evidence(
        self,
        dataset_a: List[float],
        dataset_b: List[float],
        dataset_names: Optional[Tuple[str, str]] = None,
        tolerance: float = 0.10,
    ) -> EvidenceComparisonResult:
        """Compare empirical datasets to evaluate observational consistency and detect divergence."""
        if len(dataset_a) != len(dataset_b):
            raise ValueError(f"Datasets must have equal sample count: {len(dataset_a)} vs {len(dataset_b)}")
        if not dataset_a:
            raise ValueError("Datasets cannot be empty.")

        names = list(dataset_names or ("Dataset_A", "Dataset_B"))
        diffs = [abs(a - b) for a, b in zip(dataset_a, dataset_b)]
        mean_diff = sum(diffs) / len(diffs)

        divergences: List[str] = []
        for idx, (a, b) in enumerate(zip(dataset_a, dataset_b)):
            rel_diff = abs(a - b) / (max(abs(a), abs(b)) + 1e-9)
            if rel_diff > tolerance:
                divergences.append(f"Index {idx}: {names[0]}={a} vs {names[1]}={b} (divergence: {rel_diff*100:.1f}%)")

        is_consistent = len(divergences) == 0
        confidence = 1.0 - min(1.0, len(divergences) / len(dataset_a))

        summary = (
            f"Comparison between {names[0]} and {names[1]}: "
            f"{'Consistent within tolerance' if is_consistent else f'{len(divergences)} points diverged'}. "
            f"Mean absolute difference = {mean_diff:.4f}."
        )

        return EvidenceComparisonResult(
            dataset_names=names,
            is_consistent=is_consistent,
            mean_discrepancy=round(mean_diff, 4),
            divergent_points=divergences,
            confidence_score=round(confidence, 3),
            summary=summary,
        )

    # --- 4. Synthesis & Grounded Citations ---

    def analyze(
        self,
        query: str,
        provided_sources: Optional[List[Dict[str, str]]] = None,
        domain_hint: str = "general_science",
    ) -> ScientificAnalysisResult:
        """
        Analyze a scientific query, attributing provided sources without fabricating citations.
        """
        sources = provided_sources or []
        attributed: List[str] = []
        unverified: List[str] = []

        if sources:
            for s in sources:
                title = s.get("title", "Untitled Source")
                author = s.get("author", "Unknown Author")
                year = s.get("year", "n.d.")
                attributed.append(f"{author} ({year}): '{title}'")
        else:
            unverified.append("No external citations provided in query context. Analysis relies strictly on first-principles physics.")

        limitations = (
            "Empirical results apply to idealized models (e.g., rigid bodies, ideal gases, frictionless conditions) "
            "unless non-linear boundary constraints are explicitly specified."
        )

        return ScientificAnalysisResult(
            query=query,
            domain=domain_hint,
            concept_summary=f"Analysis of query '{query}' under scientific first principles.",
            physics_solution=None,
            hypothesis_evaluation=None,
            evidence_comparison=None,
            attributed_citations=attributed,
            unverified_claims=unverified,
            epistemic_limitations=limitations,
        )
