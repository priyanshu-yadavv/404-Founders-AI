"""
404 FOUNDERS — Permission-Controlled File System Assistant
Provides sandboxed directory inspection, metadata extraction, search,
and secret-scrubbed content reading.
Enforces strict path-traversal guards, directory authorization whitelists,
and blocks sensitive credential/system files by default.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import mimetypes
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple

from core.exceptions import PermissionDeniedError, SecurityViolationError
from memory.security import MemorySecurityManager


@dataclass
class FileEntry:
    """Metadata for a single file or directory item."""
    name: str
    path: str
    is_directory: bool
    size_bytes: int
    modified_at: str
    extension: str
    mime_type: str


@dataclass
class DirectoryAnalysis:
    """Comprehensive directory structural audit."""
    root_path: str
    total_files: int
    total_dirs: int
    total_size_bytes: int
    extension_counts: Dict[str, int]
    largest_files: List[FileEntry]


@dataclass
class FileReadResult:
    """Result of safe file content reading."""
    path: str
    content: str
    size_bytes: int
    is_truncated: bool
    scrubbed_secrets_count: int
    mime_type: str


BLOCKED_SENSITIVE_PATTERNS = [
    r"(?i)\.ssh/(?:id_rsa|id_ed25519|id_ecdsa|authorized_keys|known_hosts)",
    r"(?i)\.aws/credentials",
    r"(?i)\.bash_history|\.zsh_history",
    r"(?i)/etc/(?:shadow|sudoers|master\.passwd|gshadow)",
    r"(?i)(?:^|/)\.env(?:$|\..*)",
    r"(?i)(?:^|/)(?:id_rsa|id_ecdsa|id_ed25519)(?:$|\.pub)",
    r"(?i)(?:^|/)credentials\.json$",
]


class FileSystemAssistant:
    """
    Permission-Controlled File System Assistant.
    Restricts access strictly to authorized root paths, prevents directory traversal,
    and sanitizes retrieved content against high-entropy secrets.
    """

    DEFAULT_MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB ceiling for direct text reads

    def __init__(self, allowed_roots: Optional[List[str]] = None) -> None:
        # Defaults to repository workspace root if none provided
        cwd = os.path.realpath(os.getcwd())
        roots = allowed_roots or [cwd]
        self.allowed_roots: List[str] = [os.path.realpath(r) for r in roots]

    def add_allowed_root(self, path: str) -> None:
        """Add an explicitly authorized directory root."""
        real_p = os.path.realpath(path)
        if real_p not in self.allowed_roots:
            self.allowed_roots.append(real_p)

    def _validate_path(self, target_path: str) -> Path:
        """
        Validate path against path traversal, sensitive file blocks, and allowed root boundaries.
        Raises SecurityViolationError or PermissionDeniedError on failure.
        """
        resolved = Path(os.path.realpath(target_path))
        resolved_str = str(resolved)

        # 1. Path traversal check: must reside inside at least one allowed root
        is_inside_allowed = any(
            resolved_str == root or resolved_str.startswith(root + os.sep)
            for root in self.allowed_roots
        )
        if not is_inside_allowed:
            raise SecurityViolationError(
                f"Path traversal blocked: '{target_path}' resolves outside authorized roots: {self.allowed_roots}",
                required_tier="protected",
                active_tier="unauthorized",
            )

        # 2. Block sensitive credential and OS security files
        for pattern in BLOCKED_SENSITIVE_PATTERNS:
            if re.search(pattern, resolved_str.replace("\\", "/")):
                raise SecurityViolationError(
                    f"Access denied: '{target_path}' matches sensitive security credential policy.",
                    required_tier="dangerous",
                    active_tier="blocked",
                )

        return resolved

    def list_directory(self, dir_path: str, limit: int = 100) -> List[FileEntry]:
        """List files and folders within an authorized directory."""
        validated_dir = self._validate_path(dir_path)
        if not validated_dir.is_dir():
            raise NotADirectoryError(f"Target path is not a directory: {dir_path}")

        entries: List[FileEntry] = []
        try:
            with os.scandir(validated_dir) as it:
                for entry in it:
                    try:
                        stat = entry.stat()
                        is_dir = entry.is_dir()
                        ext = Path(entry.name).suffix.lower()
                        mime = "inode/directory" if is_dir else (mimetypes.guess_type(entry.name)[0] or "application/octet-stream")

                        mod_time = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
                        entries.append(
                            FileEntry(
                                name=entry.name,
                                path=str(Path(entry.path).resolve()),
                                is_directory=is_dir,
                                size_bytes=0 if is_dir else stat.st_size,
                                modified_at=mod_time,
                                extension=ext,
                                mime_type=mime,
                            )
                        )
                        if len(entries) >= limit:
                            break
                    except (PermissionError, FileNotFoundError):
                        continue
        except PermissionError as e:
            raise PermissionDeniedError(tool_name="list_directory", required_tier="read_only", active_tier="denied") from e

        # Sort folders first, then alphabetically
        entries.sort(key=lambda e: (not e.is_directory, e.name.lower()))
        return entries

    def get_metadata(self, file_path: str) -> FileEntry:
        """Fetch detailed file metadata for an authorized path."""
        validated = self._validate_path(file_path)
        if not validated.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        stat = validated.stat()
        is_dir = validated.is_dir()
        ext = validated.suffix.lower()
        mime = "inode/directory" if is_dir else (mimetypes.guess_type(validated.name)[0] or "application/octet-stream")
        mod_time = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()

        return FileEntry(
            name=validated.name,
            path=str(validated),
            is_directory=is_dir,
            size_bytes=0 if is_dir else stat.st_size,
            modified_at=mod_time,
            extension=ext,
            mime_type=mime,
        )

    def read_file(
        self,
        file_path: str,
        max_bytes: int = DEFAULT_MAX_FILE_SIZE,
    ) -> FileReadResult:
        """
        Safely read text file content within authorized path, enforcing size bounds
        and redacting sensitive authentication credentials.
        """
        validated = self._validate_path(file_path)
        if not validated.is_file():
            raise FileNotFoundError(f"Target file does not exist or is a directory: {file_path}")

        stat = validated.stat()
        size = stat.st_size
        mime = mimetypes.guess_type(validated.name)[0] or "text/plain"

        is_truncated = False
        bytes_to_read = min(size, max_bytes)
        if size > max_bytes:
            is_truncated = True

        try:
            with open(validated, "rb") as f:
                raw_bytes = f.read(bytes_to_read)
            raw_text = raw_bytes.decode("utf-8", errors="replace")
        except Exception as e:
            raise IOError(f"Failed to read file '{file_path}': {str(e)}") from e

        # Scrub sensitive secrets
        sanitized_text, detected_secrets = MemorySecurityManager.scrub_secrets(raw_text)

        return FileReadResult(
            path=str(validated),
            content=sanitized_text,
            size_bytes=size,
            is_truncated=is_truncated,
            scrubbed_secrets_count=len(detected_secrets),
            mime_type=mime,
        )

    read_file_safe = read_file

    def search_files(
        self,
        query: str,
        root_dir: str = ".",
        extension: Optional[str] = None,
        max_results: int = 50,
        **kwargs: Any,
    ) -> List[FileEntry]:
        """Search files within an authorized root directory by name substring or extension."""
        if "query" in kwargs:
            root_dir = query
            query = kwargs["query"]
        validated_root = self._validate_path(root_dir)
        results: List[FileEntry] = []
        q_lower = query.lower()
        target_ext = extension.lower() if extension else None

        for dirpath, _, filenames in os.walk(validated_root):
            for fn in filenames:
                try:
                    # Sensitive pattern exclusion
                    f_full = os.path.join(dirpath, fn)
                    for pat in BLOCKED_SENSITIVE_PATTERNS:
                        if re.search(pat, f_full.replace("\\", "/")):
                            continue

                    ext = Path(fn).suffix.lower()
                    if target_ext and ext != target_ext:
                        continue

                    if q_lower in fn.lower():
                        st = os.stat(f_full)
                        results.append(
                            FileEntry(
                                name=fn,
                                path=str(Path(f_full).resolve()),
                                is_directory=False,
                                size_bytes=st.st_size,
                                modified_at=datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
                                extension=ext,
                                mime_type=mimetypes.guess_type(fn)[0] or "application/octet-stream",
                            )
                        )
                        if len(results) >= max_results:
                            return results
                except (PermissionError, FileNotFoundError):
                    continue

        return results

    def analyze_directory(self, root_dir: str) -> DirectoryAnalysis:
        """Perform comprehensive statistical analysis of directory structure."""
        validated_root = self._validate_path(root_dir)
        total_files = 0
        total_dirs = 0
        total_size = 0
        ext_counts: Dict[str, int] = {}
        all_files: List[FileEntry] = []

        for dirpath, dirnames, filenames in os.walk(validated_root):
            total_dirs += len(dirnames)
            for fn in filenames:
                f_full = os.path.join(dirpath, fn)
                try:
                    st = os.stat(f_full)
                    total_files += 1
                    total_size += st.st_size
                    ext = Path(fn).suffix.lower() or "no_ext"
                    ext_counts[ext] = ext_counts.get(ext, 0) + 1

                    all_files.append(
                        FileEntry(
                            name=fn,
                            path=str(Path(f_full).resolve()),
                            is_directory=False,
                            size_bytes=st.st_size,
                            modified_at=datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
                            extension=ext,
                            mime_type=mimetypes.guess_type(fn)[0] or "application/octet-stream",
                        )
                    )
                except (PermissionError, FileNotFoundError):
                    continue

        all_files.sort(key=lambda fe: fe.size_bytes, reverse=True)

        return DirectoryAnalysis(
            root_path=str(validated_root),
            total_files=total_files,
            total_dirs=total_dirs,
            total_size_bytes=total_size,
            extension_counts=ext_counts,
            largest_files=all_files[:5],
        )

    def suggest_organization(self, root_dir: str) -> List[Dict[str, str]]:
        """Analyze directory files and generate non-destructive organization recommendations."""
        analysis = self.analyze_directory(root_dir)
        suggestions: List[Dict[str, str]] = []

        # Suggest grouping if loose files exceed 10 in root
        if analysis.total_files > 15:
            grouped_exts = [ext for ext, count in analysis.extension_counts.items() if count >= 3 and ext != "no_ext"]
            for ext in grouped_exts:
                suggestions.append({
                    "category": f"Group by extension ({ext})",
                    "recommendation": f"Consider moving {analysis.extension_counts[ext]} files of type '{ext}' into a dedicated subfolder.",
                    "risk_tier": "LOW_RISK",
                })

        return suggestions
