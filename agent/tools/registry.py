"""
404 FOUNDERS — Permission-Controlled Tool Registry
Manages available tools, execution decorators, and enforces least-privilege invocation.
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from agent.permissions.validator import PermissionValidator
from core.exceptions import ToolExecutionError
from security.permissions import parse_tier


@dataclass
class ToolDefinition:
    name: str
    description: str
    required_tier: str
    func: Callable[..., Any]
    read_only: bool = True


class ToolRegistry:
    """Registry maintaining authorized tools and executing them with permission controls."""

    def __init__(self, validator: Optional[PermissionValidator] = None) -> None:
        self.tools: Dict[str, ToolDefinition] = {}
        self.validator = validator or PermissionValidator()

    def register(
        self,
        name: str,
        description: str,
        required_tier: str = "read_only",
        read_only: bool = True,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Decorator to register a function as an authorized agent tool."""
        # Validate tier string validity upon registration
        parse_tier(required_tier)

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.tools[name] = ToolDefinition(
                name=name,
                description=description,
                required_tier=required_tier,
                func=func,
                read_only=read_only,
            )
            return func

        return decorator

    def execute(
        self,
        name: str,
        user_confirmed: bool = False,
        **kwargs: Any,
    ) -> Any:
        """Validate permissions and execute registered tool safely."""
        if name not in self.tools:
            raise ToolExecutionError(tool_name=name, reason="Tool is not registered in ToolRegistry.")

        tool = self.tools[name]
        self.validator.validate(
            tool_name=tool.name,
            required_tier_str=tool.required_tier,
            user_confirmed=user_confirmed,
            call_params=kwargs,
        )

        try:
            return tool.func(**kwargs)
        except Exception as e:
            raise ToolExecutionError(tool_name=name, reason=str(e), details={"kwargs": kwargs})
