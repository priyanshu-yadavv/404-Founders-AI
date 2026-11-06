"""
404 FOUNDERS — Mathematical Reasoning Engine Unit Tests
"""

import math
import pytest
from core.reasoning.mathematical import MathematicalReasoningEngine


@pytest.fixture
def engine() -> MathematicalReasoningEngine:
    return MathematicalReasoningEngine()


def test_evaluate_arithmetic(engine: MathematicalReasoningEngine) -> None:
    res = engine.evaluate_arithmetic("12 * (3 + 4) - 10 / 2")
    assert res.domain == "arithmetic"
    assert res.exact_solution == 79.0
    assert res.verification.is_verified is True


def test_evaluate_arithmetic_invalid_chars(engine: MathematicalReasoningEngine) -> None:
    with pytest.raises(ValueError, match="unsupported characters"):
        engine.evaluate_arithmetic("import os; os.system('ls')")


def test_solve_linear_equation(engine: MathematicalReasoningEngine) -> None:
    # 3*x + 5 = 20 -> 3*x = 15 -> x = 5
    res = engine.solve_linear_equation(3.0, 5.0, 20.0)
    assert res.exact_solution == 5.0
    assert res.verification.is_verified is True
    assert res.verification.residual_error < 1e-8


def test_solve_quadratic_real_roots(engine: MathematicalReasoningEngine) -> None:
    # x^2 - 5x + 6 = 0 -> roots 3 and 2
    res = engine.solve_quadratic_equation(1.0, -5.0, 6.0)
    roots = sorted(res.exact_solution)
    assert pytest.approx(roots[0]) == 2.0
    assert pytest.approx(roots[1]) == 3.0
    assert res.verification.is_verified is True


def test_solve_quadratic_complex_roots(engine: MathematicalReasoningEngine) -> None:
    # x^2 + 1 = 0 -> roots +i, -i
    res = engine.solve_quadratic_equation(1.0, 0.0, 1.0)
    roots = res.exact_solution
    assert isinstance(roots[0], complex)
    assert pytest.approx(roots[0].imag) == 1.0
    assert pytest.approx(roots[1].imag) == -1.0


def test_solve_linear_system_2x2(engine: MathematicalReasoningEngine) -> None:
    # 2x + y = 5
    # x + 3y = 5
    # Solution: x = 2, y = 1
    res = engine.solve_linear_system_2x2(2.0, 1.0, 5.0, 1.0, 3.0, 5.0)
    assert pytest.approx(res.exact_solution["x"]) == 2.0
    assert pytest.approx(res.exact_solution["y"]) == 1.0
    assert res.verification.is_verified is True


def test_numerical_derivative(engine: MathematicalReasoningEngine) -> None:
    # f(x) = x^2, f'(3) = 6
    func = lambda x: x**2
    res = engine.numerical_derivative(func, 3.0)
    assert pytest.approx(res.exact_solution, abs=1e-4) == 6.0


def test_simpson_integral(engine: MathematicalReasoningEngine) -> None:
    # integral of x^2 from 0 to 2 is 8/3 ≈ 2.666667
    func = lambda x: x**2
    res = engine.numerical_integral_simpson(func, 0.0, 2.0, n=50)
    assert pytest.approx(res.exact_solution, abs=1e-4) == 8.0 / 3.0


def test_linear_algebra_operations(engine: MathematicalReasoningEngine) -> None:
    # Vector dot product
    u = [1.0, 2.0, 3.0]
    v = [4.0, 5.0, 6.0]
    assert engine.vector_dot_product(u, v) == 32.0

    # Vector norm
    assert pytest.approx(engine.vector_norm([3.0, 4.0])) == 5.0

    # 2x2 Matrix Determinant & Inverse
    A = [[1.0, 2.0], [3.0, 4.0]]
    det = engine.matrix_determinant(A)
    assert pytest.approx(det) == -2.0

    A_inv = engine.matrix_inverse_2x2(A)
    mult = engine.matrix_multiply(A, A_inv)
    assert pytest.approx(mult[0][0]) == 1.0
    assert pytest.approx(mult[0][1], abs=1e-9) == 0.0
    assert pytest.approx(mult[1][0], abs=1e-9) == 0.0
    assert pytest.approx(mult[1][1]) == 1.0


def test_geometry_and_statistics(engine: MathematicalReasoningEngine) -> None:
    # Circle metrics
    circ = engine.circle_metrics(10.0)
    assert pytest.approx(circ["area"]) == math.pi * 100.0
    assert pytest.approx(circ["circumference"]) == 20.0 * math.pi

    # Statistics
    data = [2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]
    stats = engine.calculate_statistics(data)
    assert stats["count"] == 8.0
    assert pytest.approx(stats["mean"]) == 5.0
    assert stats["median"] == 4.5
    assert stats["variance"] > 0

    # Combinations & Binomial
    assert engine.combinations(5, 2) == 10
    assert engine.permutations(5, 2) == 20
    p = engine.binomial_probability(10, 5, 0.5)
    assert 0.2 < p < 0.3
