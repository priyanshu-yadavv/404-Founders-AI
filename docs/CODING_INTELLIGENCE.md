# 404 FOUNDERS — Coding Intelligence Engine Specification

**Tagline:** Intelligence Without Boundaries.  
**Module:** `personal_ai.coding_assistant.coding_engine` (`CodingIntelligenceEngine`)  
**Phase:** Phase 07 — Intelligence Modules  
**Status:** Implemented & Verified  

---

## 1. Architectural Scope & Objectives

The Coding Intelligence Engine delivers defensive code parsing, multi-language detection, structural AST inspection, code smell identification, algorithmic complexity analysis, and refactoring recommendations.

### Mandatory Security Constraint: Sandbox Boundary
In accordance with system policy, **the Coding Intelligence Engine strictly prohibits automatic execution of generated or analyzed code**. All code execution interfaces remain behind an explicit permission-controlled sandbox boundary requiring operator authorization.

---

## 2. Core Capabilities

### 2.1 Multi-Language Detection
Employs signature pattern matching to accurately identify source languages:
- **Python:** `def`, `class`, `import`, `elif`, `__init__`.
- **Rust:** `fn`, `let mut`, `impl`, `pub struct`, `match`, `::`.
- **C++:** `#include`, `std::`, `cout`, `nullptr`, `template`.
- **TypeScript:** Type annotations, `interface`, `type =`, `export const`.
- **JavaScript:** `const`, `let`, `function`, `=>`, `console.log`.
- **Java:** `public class`, `public static void main`, `System.out.println`.
- **SQL:** `SELECT ... FROM`, `INSERT INTO`, `UPDATE ... SET`, `GROUP BY`.

### 2.2 Python AST Parsing & Code Smells
Parses Python source code into abstract syntax trees (`ast.parse`) to extract:
- Function and class definitions.
- Syntax errors with precise line number reporting.
- **Code Smells:** Mutable default arguments in functions (e.g., `def fn(item, cache=[])`).
- **Runtime Risks:** Bare `except:` clauses masking critical system errors.

### 2.3 Algorithmic Complexity Estimation
Inspects loop nesting depths and recursive function calls:
- Nesting depth 0: $O(1)$ constant time.
- Nesting depth 1: $O(n)$ linear time.
- Nesting depth 2: $O(n^2)$ quadratic time.
- Nesting depth $k$: $O(n^k)$ polynomial time.
- Recursion: $O(2^n)$ branching / $O(n)$ stack frame depth.

---

## 3. Data Contracts & Schema

```python
@dataclass
class SandboxExecutionNotice:
    execution_permitted: bool = False
    sandbox_required: bool = True
    active_permission_tier: str = "read_only"
    warning: str

@dataclass
class CodeAnalysisResult:
    language: str
    is_valid_syntax: bool
    parsed_ast_node_count: int
    functions: List[str]
    classes: List[str]
    complexity: ComplexityReport
    issues: List[CodeIssue]
    refactoring_suggestions: List[str]
    explanation: str
    summary: str
    sandbox_notice: SandboxExecutionNotice
```
