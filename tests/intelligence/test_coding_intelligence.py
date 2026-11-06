"""
404 FOUNDERS — Coding Intelligence Engine Unit Tests
"""

import pytest
from personal_ai.coding_assistant.coding_engine import CodingIntelligenceEngine


@pytest.fixture
def engine() -> CodingIntelligenceEngine:
    return CodingIntelligenceEngine()


def test_language_detection(engine: CodingIntelligenceEngine) -> None:
    py_code = "def compute_loss(logits, targets):\n    return torch.nn.functional.cross_entropy(logits, targets)"
    res_py = engine.detect_language(py_code)
    assert res_py.detected_language == "python"

    rust_code = "pub struct NeuralBlock {\n    weights: Vec<f32>,\n}\nimpl NeuralBlock {\n    pub fn new() -> Self {\n        Self { weights: Vec::new() }\n    }\n}"
    res_rs = engine.detect_language(rust_code)
    assert res_rs.detected_language == "rust"

    sql_code = "SELECT user_id, COUNT(*) FROM audit_logs GROUP BY user_id HAVING COUNT(*) > 10;"
    res_sql = engine.detect_language(sql_code)
    assert res_sql.detected_language == "sql"


def test_python_ast_analysis_and_code_smells(engine: CodingIntelligenceEngine) -> None:
    code_with_smells = (
        "def append_item(item, cache=[]):\n"
        "    try:\n"
        "        cache.append(item)\n"
        "    except:\n"
        "        pass\n"
        "    return cache\n"
    )
    is_valid, nodes, funcs, classes, issues = engine.analyze_python_ast(code_with_smells)
    assert is_valid is True
    assert "append_item" in funcs

    # Should flag mutable default argument and bare except
    issue_types = {i.issue_type for i in issues}
    assert "CODE_SMELL" in issue_types
    assert "RUNTIME_RISK" in issue_types


def test_python_syntax_error_detection(engine: CodingIntelligenceEngine) -> None:
    broken_code = "def invalid_func(\n    print('Missing closing parenthesis')"
    res = engine.analyze(broken_code, language_hint="python")
    assert res.is_valid_syntax is False
    assert len(res.issues) > 0
    assert res.issues[0].issue_type == "SYNTAX_ERROR"


def test_complexity_estimation(engine: CodingIntelligenceEngine) -> None:
    nested_loops = (
        "def matrix_mul(A, B):\n"
        "    n = len(A)\n"
        "    C = [[0]*n for _ in range(n)]\n"
        "    for i in range(n):\n"
        "        for j in range(n):\n"
        "            for k in range(n):\n"
        "                C[i][j] += A[i][k] * B[k][j]\n"
        "    return C\n"
    )
    report = engine.estimate_complexity(nested_loops, "python")
    assert "O(n^" in report.estimated_time_complexity or "O(n^3)" in report.estimated_time_complexity
    assert report.loop_nesting_depth >= 2


def test_sandbox_security_barrier_enforced(engine: CodingIntelligenceEngine) -> None:
    code = "import os; os.system('echo Hello')"
    res = engine.analyze(code)
    # Automatic execution MUST be strictly prohibited
    assert res.sandbox_notice.execution_permitted is False
    assert res.sandbox_notice.sandbox_required is True
    assert "SECURITY NOTICE" in res.sandbox_notice.warning
