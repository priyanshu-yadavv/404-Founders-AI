"""
404 FOUNDERS — Configuration Management System
Provides type-safe, environment-variable-aware configuration for the entire system.
"""

import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import yaml  # type: ignore
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from core.exceptions import ConfigurationError


@dataclass
class SecurityConfig:
    default_tier: str = "read_only"
    require_user_confirmation: bool = True
    audit_log_enabled: bool = True
    audit_log_path: str = "logs/security_audit.log"
    allowed_read_paths: list[str] = field(default_factory=lambda: ["/proc", "/sys", "."])
    forbidden_commands: list[str] = field(
        default_factory=lambda: ["rm -rf", "mkfs", "dd", "shutdown", "reboot", ":(){ :|:& };:"]
    )


@dataclass
class ComputeConfig:
    backend: str = "cpu"  # cpu, cuda, jax
    max_local_memory_mb: int = 4096
    max_cpu_threads: int = 8
    quantization_bits: int = 4


@dataclass
class APIConfig:
    rest_host: str = "127.0.0.1"
    rest_port: int = 8000
    ws_port: int = 8001
    grpc_port: int = 50051


@dataclass
class MemoryConfig:
    max_short_term_tokens: int = 8192
    long_term_vector_dim: int = 768
    consolidation_interval_seconds: int = 300


@dataclass
class SystemConfig:
    env: str = "development"
    operating_mode: str = "hybrid"  # general, personal, hybrid
    log_level: str = "INFO"
    log_format: str = "json"  # json, console
    security: SecurityConfig = field(default_factory=SecurityConfig)
    compute: ComputeConfig = field(default_factory=ComputeConfig)
    api: APIConfig = field(default_factory=APIConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)

    @classmethod
    def from_env(cls) -> "SystemConfig":
        """Instantiate configuration populated and overridden by environment variables."""
        cfg = cls()
        cfg.env = os.getenv("FOUNDERS_ENV", cfg.env)
        cfg.operating_mode = os.getenv("FOUNDERS_OPERATING_MODE", cfg.operating_mode)
        cfg.log_level = os.getenv("FOUNDERS_LOG_LEVEL", cfg.log_level).upper()
        cfg.log_format = os.getenv("FOUNDERS_LOG_FORMAT", cfg.log_format)

        # Security overrides
        sec_tier = os.getenv("FOUNDERS_SECURITY_DEFAULT_TIER")
        if sec_tier:
            cfg.security.default_tier = sec_tier
        req_confirm = os.getenv("FOUNDERS_REQUIRE_USER_CONFIRMATION")
        if req_confirm is not None:
            cfg.security.require_user_confirmation = req_confirm.lower() in ("true", "1", "yes")

        # Compute overrides
        compute_backend = os.getenv("FOUNDERS_COMPUTE_BACKEND")
        if compute_backend:
            cfg.compute.backend = compute_backend
        mem_mb = os.getenv("FOUNDERS_MAX_LOCAL_MEMORY_MB")
        if mem_mb:
            try:
                cfg.compute.max_local_memory_mb = int(mem_mb)
            except ValueError:
                raise ConfigurationError(f"Invalid integer for FOUNDERS_MAX_LOCAL_MEMORY_MB: {mem_mb}")

        # API overrides
        api_port = os.getenv("FOUNDERS_REST_PORT")
        if api_port:
            try:
                cfg.api.rest_port = int(api_port)
            except ValueError:
                raise ConfigurationError(f"Invalid integer for FOUNDERS_REST_PORT: {api_port}")

        return cfg

    @classmethod
    def from_file(cls, path: str | Path) -> "SystemConfig":
        """Load configuration from a YAML or JSON file."""
        p = Path(path)
        if not p.exists():
            raise ConfigurationError(f"Config file not found: {path}")

        raw_text = p.read_text(encoding="utf-8")
        if HAS_YAML and (p.suffix in (".yaml", ".yml")):
            data = yaml.safe_load(raw_text) or {}
        else:
            import json
            try:
                data = json.loads(raw_text)
            except Exception as e:
                raise ConfigurationError(f"Failed to parse config file: {e}")

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SystemConfig":
        """Construct config from dictionary with nested dataclass mappings."""
        cfg = cls()
        if "env" in data:
            cfg.env = str(data["env"])
        if "operating_mode" in data:
            cfg.operating_mode = str(data["operating_mode"])
        if "log_level" in data:
            cfg.log_level = str(data["log_level"]).upper()
        if "log_format" in data:
            cfg.log_format = str(data["log_format"])

        if "security" in data and isinstance(data["security"], dict):
            s = data["security"]
            cfg.security = SecurityConfig(
                default_tier=s.get("default_tier", cfg.security.default_tier),
                require_user_confirmation=s.get("require_user_confirmation", cfg.security.require_user_confirmation),
                audit_log_enabled=s.get("audit_log_enabled", cfg.security.audit_log_enabled),
                audit_log_path=s.get("audit_log_path", cfg.security.audit_log_path),
                allowed_read_paths=s.get("allowed_read_paths", cfg.security.allowed_read_paths),
                forbidden_commands=s.get("forbidden_commands", cfg.security.forbidden_commands),
            )

        if "compute" in data and isinstance(data["compute"], dict):
            c = data["compute"]
            cfg.compute = ComputeConfig(
                backend=c.get("backend", cfg.compute.backend),
                max_local_memory_mb=c.get("max_local_memory_mb", cfg.compute.max_local_memory_mb),
                max_cpu_threads=c.get("max_cpu_threads", cfg.compute.max_cpu_threads),
                quantization_bits=c.get("quantization_bits", cfg.compute.quantization_bits),
            )

        if "api" in data and isinstance(data["api"], dict):
            a = data["api"]
            cfg.api = APIConfig(
                rest_host=a.get("rest_host", cfg.api.rest_host),
                rest_port=a.get("rest_port", cfg.api.rest_port),
                ws_port=a.get("ws_port", cfg.api.ws_port),
                grpc_port=a.get("grpc_port", cfg.api.grpc_port),
            )

        return cfg

    def to_dict(self) -> Dict[str, Any]:
        """Convert system configuration to dictionary."""
        return asdict(self)
