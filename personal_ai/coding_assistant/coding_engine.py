"""
404 FOUNDERS — Coding Intelligence Engine
Provides defensive code parsing, syntax inspection, multi-language detection,
algorithmic complexity analysis, debugging assistance, and enforces strict sandbox boundaries.
"""

import ast
from dataclasses import dataclass, field
import re
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class SandboxExecutionNotice:
    """Explicit security barrier preventing unauthorized code execution."""
    execution_permitted: bool = False
    sandbox_required: bool = True
    active_permission_tier: str = "read_only"
    warning: str = (
        "SECURITY NOTICE: 404 FOUNDERS does not permit automatic execution of generated code. "
        "Any code execution must occur within an isolated, resource-limited sandbox environment "
        "and requires explicit human operator authorization."
    )


@dataclass
class LanguageDetectionResult:
    """Result of language detection heuristic analysis."""
    detected_language: str
    confidence: float
    indicators: List[str]


@dataclass
class ComplexityReport:
    """Algorithmic time and space complexity evaluation."""
    estimated_time_complexity: str
    estimated_space_complexity: str
    loop_nesting_depth: int
    has_recursion: bool
    explanation: str


@dataclass
class CodeIssue:
    """Represents a detected bug, syntax error, or code smell."""
    issue_type: str  # "SYNTAX_ERROR", "RUNTIME_RISK", "CODE_SMELL", "SECURITY_RISK"
    line_number: Optional[int]
    message: str
    suggestion: str


@dataclass
class CodeAnalysisResult:
    """Comprehensive analysis report for a code snippet."""
    language: str
    is_valid_syntax: bool
    parsed_ast_node_count: int
    functions: List[str]
    classes: List[str]
    complexity: ComplexityReport
    issues: List[CodeIssue]
    refactoring_suggestions: List[str]
    explanation: str
    summary: str = ""
    sandbox_notice: SandboxExecutionNotice = field(default_factory=SandboxExecutionNotice)


class CodingIntelligenceEngine:
    """
    Defensive code intelligence engine.
    Analyzes Python AST structures and lexical patterns for C++, Rust, JavaScript, TypeScript, Java, and SQL.
    Strictly prohibits automatic code execution.
    """

    LANGUAGE_PATTERNS = {
        "python": [
            r"\bdef\s+\w+\s*\(",
            r"\bclass\s+\w+[\(:]",
            r"\bimport\s+\w+",
            r"\bfrom\s+\w+\s+import",
            r"\belif\b",
            r"__init__",
        ],
        "rust": [
            r"\bfn\s+\w+\s*\(",
            r"\blet\s+mut\s+",
            r"\bimpl\b",
            r"\bpub\s+struct\b",
            r"\bmatch\s+\w+\s*\{",
            r"::\w+",
        ],
        "cpp": [
            r"#include\s*<",
            r"\bstd::",
            r"\bcout\s*<<",
            r"\bnullptr\b",
            r"\btemplate\s*<",
        ],
        "typescript": [
            r":\s*(string|number|boolean|any|void)\b",
            r"\binterface\s+\w+\s*\{",
            r"\btype\s+\w+\s*=",
            r"\bexport\s+(const|interface|type)",
        ],
        "javascript": [
            r"\bconst\s+\w+\s*=",
            r"\blet\s+\w+\s*=",
            r"\bfunction\s+\w+\s*\(",
            r"=>",
            r"console\.log\(",
        ],
        "java": [
            r"\bpublic\s+class\s+\w+",
            r"\bpublic\s+static\s+void\s+main",
            r"\bSystem\.out\.println",
            r"\bprivate\s+final\b",
        ],
        "sql": [
            r"\bSELECT\b.*?\bFROM\b",
            r"\bINSERT\s+INTO\b",
            r"\bUPDATE\b.*?\bSET\b",
            r"\bCREATE\s+TABLE\b",
            r"\bGROUP\s+BY\b",
        ],
    }

    def detect_language(self, code: str) -> LanguageDetectionResult:
        """Detect programming language using pattern recognition."""
        cleaned = code.strip()
        if not cleaned:
            return LanguageDetectionResult("unknown", 0.0, ["Empty code buffer"])

        scores: Dict[str, Tuple[int, List[str]]] = {}
        for lang, patterns in self.LANGUAGE_PATTERNS.items():
            matches: List[str] = []
            for pat in patterns:
                m = re.findall(pat, cleaned, flags=re.IGNORECASE if lang == "sql" else 0)
                if m:
                    matches.append(pat)
            scores[lang] = (len(matches), matches)

        best_lang, (best_count, best_matches) = max(scores.items(), key=lambda item: item[1][0])

        if best_count == 0:
            return LanguageDetectionResult("plain_text", 0.3, ["No language-specific keywords matched."])

        confidence = min(0.99, 0.4 + 0.15 * best_count)
        return LanguageDetectionResult(
            detected_language=best_lang,
            confidence=round(confidence, 2),
            indicators=best_matches,
        )

    def analyze_python_ast(self, code: str) -> Tuple[bool, int, List[str], List[str], List[CodeIssue]]:
        """Parse Python source into AST and extract structural symbols and issues."""
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            issue = CodeIssue(
                issue_type="SYNTAX_ERROR",
                line_number=e.lineno,
                message=f"Syntax Error: {e.msg}",
                suggestion="Review syntax near indicated line.",
            )
            return False, 0, [], [], [issue]

        functions: List[str] = []
        classes: List[str] = []
        issues: List[CodeIssue] = []
        node_count = 0

        for node in ast.walk(tree):
            node_count += 1
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(node.name)
                # Check for mutable default arguments
                for default in node.args.defaults:
                    if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        issues.append(CodeIssue(
                            issue_type="CODE_SMELL",
                            line_number=node.lineno,
                            message=f"Function '{node.name}' uses mutable default argument.",
                            suggestion="Use 'None' as default value and initialize inside the function body.",
                        ))
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)
            # Check for bare except
            elif isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    issues.append(CodeIssue(
                        issue_type="RUNTIME_RISK",
                        line_number=node.lineno,
                        message="Bare 'except:' clause caught.",
                        suggestion="Catch specific exception types (e.g. 'except ValueError:') rather than masking all errors.",
                    ))

        return True, node_count, functions, classes, issues

    def estimate_complexity(self, code: str, language: str) -> ComplexityReport:
        """Estimate time and space complexity based on control flow and recursion."""
        max_depth = 0
        current_depth = 0
        has_recursion = False

        if language == "python":
            try:
                tree = ast.parse(code)
                func_names = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}

                for node in ast.walk(tree):
                    if isinstance(node, (ast.For, ast.While)):
                        # Count parent loops
                        depth = 1
                        parent = getattr(node, "_parent", None)
                        # Estimate via indentation
                    elif isinstance(node, ast.Call):
                        if isinstance(node.func, ast.Name) and node.func.id in func_names:
                            has_recursion = True
            except Exception:
                pass

        # Text-based indentation/nesting heuristic
        lines = code.split("\n")
        loop_keywords = ("for ", "while ", "for(", "while(")
        loop_depths = [0]
        active_loops = 0

        for line in lines:
            stripped = line.strip()
            if any(stripped.startswith(k) for k in loop_keywords):
                active_loops += 1
                loop_depths.append(active_loops)
            elif stripped.endswith("}") or (line.startswith("def ") and active_loops > 0):
                active_loops = max(0, active_loops - 1)

        max_depth = max(loop_depths)

        # Map depth to Big-O
        if max_depth == 0:
            time_comp = "O(1)"
        elif max_depth == 1:
            time_comp = "O(n)"
        elif max_depth == 2:
            time_comp = "O(n^2)"
        else:
            time_comp = f"O(n^{max_depth})"

        if has_recursion:
            time_comp = f"O(2^n) (recursive branch) or {time_comp}"
            space_comp = "O(n) (call stack frames)"
        else:
            space_comp = "O(1) (in-place) or O(n) (auxiliary buffers)"

        return ComplexityReport(
            estimated_time_complexity=time_comp,
            estimated_space_complexity=space_comp,
            loop_nesting_depth=max_depth,
            has_recursion=has_recursion,
            explanation=f"Identified max loop nesting depth of {max_depth} and recursion={has_recursion}.",
        )

    def analyze(self, code: str, language_hint: Optional[str] = None) -> CodeAnalysisResult:
        """Perform comprehensive defensive code analysis."""
        if not code.strip():
            raise ValueError("Code snippet cannot be empty.")

        # Detect language
        det = self.detect_language(code)
        lang = language_hint.lower() if language_hint else det.detected_language

        is_valid = True
        node_count = 0
        functions: List[str] = []
        classes: List[str] = []
        issues: List[CodeIssue] = []
        refactorings: List[str] = []

        if lang == "python":
            is_valid, node_count, functions, classes, issues = self.analyze_python_ast(code)
            if is_valid:
                refactorings.append("Add complete PEP 484 type annotations for function parameters and return types.")
                refactorings.append("Include docstrings with parameter descriptions and return value specifications.")
        else:
            # Generic token extraction for other languages
            functions = re.findall(r"\b(?:fn|function|def|void|int|double)\s+(\w+)\s*\(", code)
            classes = re.findall(r"\b(?:class|struct|interface)\s+(\w+)", code)
            node_count = len(code.split())

        complexity = self.estimate_complexity(code, lang)

        explanation = (
            f"Code written in {lang.upper()}. Contains {len(functions)} function(s) "
            f"({', '.join(functions[:4]) if functions else 'none'}) and {len(classes)} class/struct definitions. "
            f"Estimated runtime complexity is {complexity.estimated_time_complexity}."
        )

        return CodeAnalysisResult(
            language=lang,
            is_valid_syntax=is_valid,
            parsed_ast_node_count=node_count,
            functions=functions,
            classes=classes,
            complexity=complexity,
            issues=issues,
            refactoring_suggestions=refactorings,
            explanation=explanation,
            summary=explanation,
            sandbox_notice=SandboxExecutionNotice(),
        )
