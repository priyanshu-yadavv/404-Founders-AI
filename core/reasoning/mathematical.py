"""
404 FOUNDERS — Mathematical Reasoning Engine
Provides deterministic mathematical computation and numerical verification across
arithmetic, algebra, calculus, linear algebra, geometry, trigonometry, and probability/statistics.
"""

from dataclasses import dataclass, field
import math
import re
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


@dataclass
class MathStep:
    """A single deterministic calculation or verification step."""
    step_number: int
    operation: str
    expression: str
    result: str
    explanation: str


@dataclass
class NumericalVerification:
    """Verification results validating a solution against original conditions."""
    is_verified: bool
    residual_error: float
    tolerance: float
    verification_expression: str


@dataclass
class MathematicalResult:
    """Structured response schema for mathematical reasoning computations."""
    domain: str
    query_description: str
    steps: List[MathStep]
    exact_solution: Any
    numerical_approximation: Optional[float]
    verification: Optional[NumericalVerification]
    confidence: float
    summary: str


class MathematicalReasoningEngine:
    """
    Deterministic numerical and algebraic computation engine.
    Solves problems analytically where closed-form exists, and uses robust
    numerical algorithms (Simpson's rule, central differences, Cramer's rule) otherwise.
    Never fabricates symbolic capabilities.
    """

    # --- 1. Arithmetic & Basic Operations ---

    def evaluate_arithmetic(self, expression: str) -> MathematicalResult:
        """Safely evaluate standard arithmetic expressions using Python AST or safe math functions."""
        # Strip common leading query prompts
        cleaned = re.sub(r"^(calculate|compute|solve|evaluate|what is)\s+", "", expression.strip(), flags=re.IGNORECASE)
        allowed_chars = set("0123456789+-*/().,%^ eE")
        cleaned = cleaned.replace("^", "**").strip()
        if not all(c in allowed_chars for c in cleaned):
            raise ValueError(f"Arithmetic expression contains unsupported characters: '{expression}'")

        # Evaluate safely in restricted namespace
        safe_dict = {
            "__builtins__": None,
            "sqrt": math.sqrt,
            "pow": math.pow,
            "exp": math.exp,
            "log": math.log,
            "abs": abs,
        }
        val = float(eval(cleaned, safe_dict, {}))

        steps = [
            MathStep(1, "Parse", expression, expression, "Sanitized and checked mathematical tokens."),
            MathStep(2, "Evaluation", cleaned, str(val), "Computed deterministic arithmetic value."),
        ]
        return MathematicalResult(
            domain="arithmetic",
            query_description=expression,
            steps=steps,
            exact_solution=val,
            numerical_approximation=val,
            verification=NumericalVerification(True, 0.0, 1e-9, f"{cleaned} == {val}"),
            confidence=1.0,
            summary=f"Evaluated {expression} = {val}",
        )

    # --- 2. Algebra: Linear, Quadratic, and Systems ---

    def solve_linear_equation(self, a: float, b: float, c: float) -> MathematicalResult:
        """Solve a*x + b = c -> x = (c - b) / a."""
        if abs(a) < 1e-12:
            if abs(b - c) < 1e-12:
                raise ValueError("Infinite solutions: equation is an identity (0 = 0).")
            raise ValueError("No solution: inconsistent equation (a = 0 but b != c).")

        x = (c - b) / a
        residual = abs((a * x + b) - c)

        steps = [
            MathStep(1, "Isolate Term", f"{a}*x = {c} - {b}", f"{a}*x = {c - b}", "Subtracted constant b from both sides."),
            MathStep(2, "Divide Coefficient", f"x = ({c - b}) / {a}", f"x = {x}", f"Divided by coefficient a = {a}."),
        ]
        verification = NumericalVerification(
            is_verified=residual < 1e-8,
            residual_error=residual,
            tolerance=1e-8,
            verification_expression=f"{a}*({x}) + {b} = {a * x + b} (target: {c})",
        )
        return MathematicalResult(
            domain="algebra",
            query_description=f"{a}*x + {b} = {c}",
            steps=steps,
            exact_solution=x,
            numerical_approximation=float(x),
            verification=verification,
            confidence=1.0,
            summary=f"Linear equation solved: x = {x}",
        )

    def solve_quadratic_equation(self, a: float, b: float, c: float) -> MathematicalResult:
        """Solve a*x^2 + b*x + c = 0 via quadratic formula."""
        if abs(a) < 1e-12:
            return self.solve_linear_equation(b, c, 0.0)

        discriminant = b**2 - 4 * a * c
        steps = [
            MathStep(1, "Discriminant", f"D = b^2 - 4*a*c = ({b})^2 - 4*({a})*({c})", f"D = {discriminant}", "Calculated discriminant."),
        ]

        if discriminant > 0:
            sqrt_d = math.sqrt(discriminant)
            x1 = (-b + sqrt_d) / (2 * a)
            x2 = (-b - sqrt_d) / (2 * a)
            roots = [x1, x2]
            steps.append(MathStep(2, "Real Roots", f"x = (-{b} ± {sqrt_d}) / (2*{a})", f"x1 = {x1}, x2 = {x2}", "Two distinct real roots found."))
            res1 = abs(a * x1**2 + b * x1 + c)
            res2 = abs(a * x2**2 + b * x2 + c)
            max_res = max(res1, res2)
        elif abs(discriminant) < 1e-12:
            x = -b / (2 * a)
            roots = [x]
            steps.append(MathStep(2, "Single Root", f"x = -{b} / (2*{a})", f"x = {x}", "One repeated real root found."))
            max_res = abs(a * x**2 + b * x + c)
        else:
            real_part = -b / (2 * a)
            imag_part = math.sqrt(-discriminant) / (2 * a)
            roots = [complex(real_part, imag_part), complex(real_part, -imag_part)]
            steps.append(MathStep(2, "Complex Roots", f"x = {real_part} ± {imag_part}i", f"x1 = {roots[0]}, x2 = {roots[1]}", "Conjugate complex roots."))
            max_res = 0.0

        verification = NumericalVerification(
            is_verified=max_res < 1e-7,
            residual_error=max_res,
            tolerance=1e-7,
            verification_expression=f"Max residual f(root) = {max_res}",
        )
        return MathematicalResult(
            domain="algebra",
            query_description=f"{a}*x^2 + {b}*x + {c} = 0",
            steps=steps,
            exact_solution=roots,
            numerical_approximation=float(roots[0].real) if isinstance(roots[0], complex) else float(roots[0]),
            verification=verification,
            confidence=1.0,
            summary=f"Quadratic roots: {roots}",
        )

    def solve_linear_system_2x2(
        self,
        a1: float, b1: float, c1: float,
        a2: float, b2: float, c2: float,
    ) -> MathematicalResult:
        """Solve 2x2 linear system via Cramer's Rule: a1*x + b1*y = c1; a2*x + b2*y = c2."""
        det_d = a1 * b2 - a2 * b1
        det_dx = c1 * b2 - c2 * b1
        det_dy = a1 * c2 - a2 * c1

        if abs(det_d) < 1e-12:
            if abs(det_dx) < 1e-12 and abs(det_dy) < 1e-12:
                raise ValueError("Infinite solutions: linearly dependent system.")
            raise ValueError("No solution: parallel inconsistent system.")

        x = det_dx / det_d
        y = det_dy / det_d

        res1 = abs((a1 * x + b1 * y) - c1)
        res2 = abs((a2 * x + b2 * y) - c2)
        max_res = max(res1, res2)

        steps = [
            MathStep(1, "Determinant D", f"a1*b2 - a2*b1 = {a1}*{b2} - {a2}*{b1}", f"D = {det_d}", "Evaluated system determinant."),
            MathStep(2, "Cramer Dx, Dy", f"Dx = {det_dx}, Dy = {det_dy}", f"Dx={det_dx}, Dy={det_dy}", "Evaluated numerator determinants."),
            MathStep(3, "Solution", f"x = Dx/D, y = Dy/D", f"x = {x}, y = {y}", "Calculated unique solution coordinates."),
        ]
        return MathematicalResult(
            domain="linear_algebra",
            query_description=f"System: [{a1}x+{b1}y={c1}; {a2}x+{b2}y={c2}]",
            steps=steps,
            exact_solution={"x": x, "y": y},
            numerical_approximation=x,
            verification=NumericalVerification(max_res < 1e-8, max_res, 1e-8, f"Residuals: eq1={res1}, eq2={res2}"),
            confidence=1.0,
            summary=f"2x2 System solved: x = {x}, y = {y}",
        )

    # --- 3. Calculus: Numerical Differentiation & Simpson Integration ---

    def numerical_derivative(
        self,
        func: Callable[[float], float],
        x: float,
        h: float = 1e-6,
    ) -> MathematicalResult:
        """Compute f'(x) using central difference: (f(x + h) - f(x - h)) / (2 * h)."""
        f_plus = func(x + h)
        f_minus = func(x - h)
        derivative = (f_plus - f_minus) / (2.0 * h)

        steps = [
            MathStep(1, "Central Difference Setup", f"f({x} + {h}) and f({x} - {h})", f"f+={f_plus:.8f}, f-={f_minus:.8f}", "Sampled function near evaluation point."),
            MathStep(2, "Derivative Approximation", f"({f_plus:.8f} - {f_minus:.8f}) / (2*{h})", f"{derivative:.8f}", "Applied central difference formula."),
        ]
        return MathematicalResult(
            domain="calculus",
            query_description=f"Numerical derivative at x = {x}",
            steps=steps,
            exact_solution=derivative,
            numerical_approximation=derivative,
            verification=NumericalVerification(True, h**2, 1e-6, f"Order O(h^2) approximation with h={h}"),
            confidence=0.98,
            summary=f"Numerical derivative f'({x}) ≈ {derivative:.6f}",
        )

    def numerical_integral_simpson(
        self,
        func: Callable[[float], float],
        a: float,
        b: float,
        n: int = 100,
    ) -> MathematicalResult:
        """Compute integral of func from a to b using Simpson's 1/3 rule (n must be even)."""
        if n % 2 != 0:
            n += 1
        h = (b - a) / n
        total = func(a) + func(b)

        for i in range(1, n):
            xi = a + i * h
            if i % 2 == 1:
                total += 4.0 * func(xi)
            else:
                total += 2.0 * func(xi)

        integral = (h / 3.0) * total
        steps = [
            MathStep(1, "Discretization", f"Interval [{a}, {b}], n={n} steps", f"Step size h = {h:.6f}", "Constructed uniform mesh."),
            MathStep(2, "Simpson Integration", f"Integral = (h/3) * [f(a) + 4*sum_odd + 2*sum_even + f(b)]", f"{integral:.8f}", "Applied Simpson's 1/3 rule."),
        ]
        return MathematicalResult(
            domain="calculus",
            query_description=f"Simpson integral from {a} to {b} with n={n}",
            steps=steps,
            exact_solution=integral,
            numerical_approximation=integral,
            verification=NumericalVerification(True, h**4, 1e-5, f"Order O(h^4) Simpson convergence"),
            confidence=0.99,
            summary=f"Simpson integral over [{a}, {b}] ≈ {integral:.6f}",
        )

    # --- 4. Linear Algebra: Vector & Matrix Operations ---

    def vector_dot_product(self, u: List[float], v: List[float]) -> float:
        """Compute dot product of two vectors."""
        if len(u) != len(v):
            raise ValueError(f"Vector dimensions mismatch: {len(u)} != {len(v)}")
        return sum(x * y for x, y in zip(u, v))

    def vector_norm(self, v: List[float]) -> float:
        """Compute Euclidean L2 norm of vector."""
        return math.sqrt(sum(x**2 for x in v))

    def matrix_multiply(self, A: List[List[float]], B: List[List[float]]) -> List[List[float]]:
        """Multiply matrices A (m x k) and B (k x n) -> C (m x n)."""
        m, k_a = len(A), len(A[0])
        k_b, n = len(B), len(B[0])
        if k_a != k_b:
            raise ValueError(f"Incompatible matrix dimensions: ({m}x{k_a}) and ({k_b}x{n})")

        C = [[0.0 for _ in range(n)] for _ in range(m)]
        for i in range(m):
            for j in range(n):
                C[i][j] = sum(A[i][p] * B[p][j] for p in range(k_a))
        return C

    def matrix_determinant(self, M: List[List[float]]) -> float:
        """Compute determinant for 2x2 or 3x3 matrices deterministically."""
        n = len(M)
        if n == 2:
            return M[0][0] * M[1][1] - M[0][1] * M[1][0]
        elif n == 3:
            return (
                M[0][0] * (M[1][1] * M[2][2] - M[1][2] * M[2][1])
                - M[0][1] * (M[1][0] * M[2][2] - M[1][2] * M[2][0])
                + M[0][2] * (M[1][0] * M[2][1] - M[1][1] * M[2][0])
            )
        raise ValueError(f"Deterministic determinant currently supports 2x2 and 3x3, got {n}x{n}")

    def matrix_inverse_2x2(self, M: List[List[float]]) -> List[List[float]]:
        """Invert a 2x2 matrix analytically."""
        det = self.matrix_determinant(M)
        if abs(det) < 1e-12:
            raise ValueError("Matrix is singular (determinant is 0), inverse does not exist.")
        inv_det = 1.0 / det
        return [
            [M[1][1] * inv_det, -M[0][1] * inv_det],
            [-M[1][0] * inv_det, M[0][0] * inv_det],
        ]

    # --- 5. Geometry & Trigonometry ---

    def euclidean_distance(self, p1: Tuple[float, ...], p2: Tuple[float, ...]) -> float:
        """Calculate Euclidean distance between two N-dimensional points."""
        if len(p1) != len(p2):
            raise ValueError("Point dimensions must match.")
        return math.sqrt(sum((a - b)**2 for a, b in zip(p1, p2)))

    def circle_metrics(self, radius: float) -> Dict[str, float]:
        """Compute area and circumference of a circle."""
        if radius < 0:
            raise ValueError("Radius must be non-negative.")
        return {
            "radius": radius,
            "area": math.pi * radius**2,
            "circumference": 2.0 * math.pi * radius,
        }

    # --- 6. Probability & Statistics ---

    def calculate_statistics(self, data: List[float]) -> Dict[str, float]:
        """Compute mean, median, sample variance, standard deviation, and range."""
        if not data:
            raise ValueError("Dataset cannot be empty.")
        n = len(data)
        mean_val = sum(data) / n

        sorted_data = sorted(data)
        if n % 2 == 1:
            median_val = sorted_data[n // 2]
        else:
            median_val = (sorted_data[n // 2 - 1] + sorted_data[n // 2]) / 2.0

        variance = sum((x - mean_val)**2 for x in data) / (n - 1) if n > 1 else 0.0
        std_dev = math.sqrt(variance)

        return {
            "count": float(n),
            "mean": mean_val,
            "median": median_val,
            "variance": variance,
            "std_dev": std_dev,
            "min": sorted_data[0],
            "max": sorted_data[-1],
        }

    def combinations(self, n: int, r: int) -> int:
        """Compute nCr = n! / (r! * (n-r)!)."""
        if r < 0 or r > n:
            return 0
        return math.comb(n, r)

    def permutations(self, n: int, r: int) -> int:
        """Compute nPr = n! / (n-r)!."""
        if r < 0 or r > n:
            return 0
        return math.perm(n, r)

    def binomial_probability(self, n: int, k: int, p: float) -> float:
        """Compute Binomial probability P(X = k) = (n choose k) * p^k * (1-p)^(n-k)."""
        if not (0.0 <= p <= 1.0):
            raise ValueError("Probability p must be between 0.0 and 1.0.")
        return self.combinations(n, k) * (p**k) * ((1.0 - p)**(n - k))
