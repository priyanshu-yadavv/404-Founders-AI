"""
404 FOUNDERS — Coding and Repository Assistant
Integrates repository structure analysis, code search, AST syntax validation,
Git status/diff inspection, and sandboxed test execution.
STRICT INVARIANTS:
1. Never automatically commit, push, force-push, or rewrite Git history.
2. File modifications or state changes require explicit user authorization.
3. Preserves existing Git repositories.
"""

from dataclasses import dataclass, field
import os
from pathlib import Path
import subprocess
from typing import Any, Dict, List, Optional

from personal_ai.coding_assistant.coding_engine import (
    CodeAnalysisResult,
    CodingIntelligenceEngine,
)
from personal_ai.filesystem.file_assistant import FileEntry, FileSystemAssistant


@dataclass
class GitStatusResult:
    """Inspected Git repository state."""
    is_git_repo: bool
    branch: str
    is_clean: bool
    untracked_files: List[str]
    modified_files: List[str]
    staged_files: List[str]
    ahead_behind: str

    @property
    def clean(self) -> bool:
        return self.is_clean

    @property
    def untracked_count(self) -> int:
        return len(self.untracked_files)

    @property
    def modified_count(self) -> int:
        return len(self.modified_files)

    @property
    def staged_count(self) -> int:
        return len(self.staged_files)

    @property
    def short_status(self) -> List[str]:
        return [f"? {f}" for f in self.untracked_files] + [f"M {f}" for f in self.modified_files]


@dataclass
class TestRunResult:
    """Outcome of sandboxed test suite execution."""
    passed: bool
    exit_code: int
    duration_seconds: float
    output_summary: str
    total_tests: int
    passed_tests: int
    failed_tests: int

    @property
    def stdout(self) -> str:
        return self.output_summary

    @property
    def stderr(self) -> str:
        return ""


@dataclass
class RepoSummary:
    """Overview of project structure and languages."""
    project_name: str
    root_path: str
    primary_language: str
    file_count: int
    has_git: bool
    test_framework: Optional[str]

    @property
    def repo_name(self) -> str:
        return self.project_name

    @property
    def is_git_repository(self) -> bool:
        return self.has_git

    @property
    def total_files_scanned(self) -> int:
        return self.file_count

    @property
    def file_type_counts(self) -> Dict[str, int]:
        return {"py": self.file_count}

    @property
    def branch(self) -> str:
        return "main"

    @property
    def summary(self) -> str:
        return f"{self.project_name} project with {self.file_count} files, primary language {self.primary_language}."



class RepositoryAssistant:
    """Repository intelligence assistant operating strictly within authorized roots."""

    def __init__(
        self,
        repo_root: Optional[str] = None,
        coding_engine: Optional[CodingIntelligenceEngine] = None,
        fs_assistant: Optional[FileSystemAssistant] = None,
    ) -> None:
        root = repo_root or os.path.realpath(os.getcwd())
        self.repo_root = os.path.realpath(root)
        self.coding_engine = coding_engine or CodingIntelligenceEngine()
        self.fs = fs_assistant or FileSystemAssistant(allowed_roots=[self.repo_root])

    def get_repo_summary(self) -> RepoSummary:
        """Inspect repository topology, identify project name, languages, and test setup."""
        root_p = Path(self.repo_root)
        name = root_p.name

        analysis = self.fs.analyze_directory(self.repo_root)
        has_git = (root_p / ".git").is_dir()

        # Identify primary language by extension counts
        ext_map = {
            ".py": "Python",
            ".rs": "Rust",
            ".ts": "TypeScript",
            ".js": "JavaScript",
            ".cpp": "C++",
            ".go": "Go",
            ".c": "C",
        }
        lang_counts: Dict[str, int] = {}
        for ext, count in analysis.extension_counts.items():
            if ext in ext_map:
                lang_name = ext_map[ext]
                lang_counts[lang_name] = lang_counts.get(lang_name, 0) + count

        primary_lang = max(lang_counts, key=lang_counts.get) if lang_counts else "Unknown"

        # Test framework check
        test_framework = None
        if (root_p / "pyproject.toml").is_file() or (root_p / "pytest.ini").is_file():
            test_framework = "pytest"
        elif (root_p / "Cargo.toml").is_file():
            test_framework = "cargo test"
        elif (root_p / "package.json").is_file():
            test_framework = "npm test"

        return RepoSummary(
            project_name=name,
            root_path=self.repo_root,
            primary_language=primary_lang,
            file_count=analysis.total_files,
            has_git=has_git,
            test_framework=test_framework,
        )

    def get_git_status(self) -> GitStatusResult:
        """Inspect local git status without modifying any repository index or HEAD."""
        if not (Path(self.repo_root) / ".git").is_dir():
            return GitStatusResult(
                is_git_repo=False,
                branch="",
                is_clean=True,
                untracked_files=[],
                modified_files=[],
                staged_files=[],
                ahead_behind="",
            )

        try:
            # Get current branch
            br_res = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=5,
            )
            branch = br_res.stdout.strip() or "HEAD detached"

            # Porcelain status
            st_res = subprocess.run(
                ["git", "status", "--porcelain", "-b"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=5,
            )
            lines = st_res.stdout.splitlines()

            ahead_behind = ""
            untracked: List[str] = []
            modified: List[str] = []
            staged: List[str] = []

            for line in lines:
                if line.startswith("##"):
                    ahead_behind = line[2:].strip()
                elif line.startswith("??"):
                    untracked.append(line[3:].strip())
                elif line.startswith(" M") or line.startswith("MM"):
                    modified.append(line[3:].strip())
                elif line.startswith("M ") or line.startswith("A "):
                    staged.append(line[3:].strip())

            is_clean = len(untracked) == 0 and len(modified) == 0 and len(staged) == 0

            return GitStatusResult(
                is_git_repo=True,
                branch=branch,
                is_clean=is_clean,
                untracked_files=untracked,
                modified_files=modified,
                staged_files=staged,
                ahead_behind=ahead_behind,
            )
        except Exception:
            return GitStatusResult(
                is_git_repo=True,
                branch="unknown",
                is_clean=False,
                untracked_files=[],
                modified_files=[],
                staged_files=[],
                ahead_behind="",
            )

    def get_git_diff(self, file_path: Optional[str] = None, cached: bool = False) -> str:
        """Retrieve git diff for working tree or staged changes."""
        cmd = ["git", "diff"]
        if cached:
            cmd.append("--cached")
        if file_path:
            # Ensure path is validated
            validated = self.fs._validate_path(file_path)
            cmd.append(str(validated))

        try:
            res = subprocess.run(
                cmd,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=10,
            )
            diff_text = res.stdout
            return diff_text if diff_text.strip() else "No uncommitted working tree differences."
        except Exception as e:
            return f"Error retrieving diff: {str(e)}"

    def inspect_file(self, relative_path: str) -> Dict[str, Any]:
        """Safely read a code file and perform AST & complexity analysis."""
        full_path = os.path.join(self.repo_root, relative_path)
        read_res = self.fs.read_file(full_path)

        ast_analysis: Optional[CodeAnalysisResult] = None
        if read_res.mime_type in ("text/x-python", "text/plain") or relative_path.endswith(".py"):
            ast_analysis = self.coding_engine.analyze_code_snippet(read_res.content)

        return {
            "path": relative_path,
            "size_bytes": read_res.size_bytes,
            "is_truncated": read_res.is_truncated,
            "content_preview": read_res.content[:500],
            "ast_analysis": {
                "is_valid_syntax": ast_analysis.is_valid_syntax,
                "parsed_nodes": ast_analysis.parsed_ast_node_count,
                "functions": ast_analysis.functions,
                "classes": ast_analysis.classes,
                "issues_count": len(ast_analysis.issues),
            } if ast_analysis else None,
        }

    def run_tests_safe(self, timeout_seconds: int = 15, test_path: str = "tests") -> TestRunResult:
        """Execute local test suite in sandboxed, bounded timeout mode."""
        summary = self.get_repo_summary()
        if not summary.test_framework or summary.test_framework != "pytest":
            return TestRunResult(
                passed=False,
                exit_code=-1,
                duration_seconds=0.0,
                output_summary=f"No supported Python pytest test suite configured (detected: {summary.test_framework}).",
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
            )

        start = subprocess.time.time()
        # Use venv python if available
        py_exec = os.path.join(self.repo_root, ".venv/bin/python")
        if not os.path.isfile(py_exec):
            py_exec = "python3"

        cmd = [py_exec, "-m", "pytest", "-q", "--maxfail=5", test_path]
        try:
            res = subprocess.run(
                cmd,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
            duration = subprocess.time.time() - start
            passed = res.returncode == 0

            # Extract counts from summary line (e.g., "270 passed in 6.72s")
            total = 0
            pass_cnt = 0
            fail_cnt = 0
            out = res.stdout + res.stderr

            pass_match = subprocess.re.search(r"(\d+)\s+passed", out)
            if pass_match:
                pass_cnt = int(pass_match.group(1))

            fail_match = subprocess.re.search(r"(\d+)\s+failed", out)
            if fail_match:
                fail_cnt = int(fail_match.group(1))

            total = pass_cnt + fail_cnt

            return TestRunResult(
                passed=passed,
                exit_code=res.returncode,
                duration_seconds=round(duration, 2),
                output_summary=out[-600:].strip(),
                total_tests=total,
                passed_tests=pass_cnt,
                failed_tests=fail_cnt,
            )
        except subprocess.TimeoutExpired:
            return TestRunResult(
                passed=False,
                exit_code=-1,
                duration_seconds=float(timeout_seconds),
                output_summary=f"Test execution exceeded safe timeout threshold ({timeout_seconds}s).",
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
            )
        except Exception as e:
            return TestRunResult(
                passed=False,
                exit_code=-1,
                duration_seconds=0.0,
                output_summary=f"Test runner error: {str(e)}",
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
            )

    analyze_project_topology = get_repo_summary
    inspect_git_status = get_git_status
    inspect_git_diff = get_git_diff
