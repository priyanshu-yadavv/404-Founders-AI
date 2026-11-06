"""
404 FOUNDERS — Infrastructure/Local
Local workstation hardware introspection, memory budgeting, and runtime limits.
"""

from infrastructure.local.hardware import LocalHardwareInspector, LocalHardwareProfile
from infrastructure.local.runtime import (
    EXEC_MODE_LOCAL_CPU,
    EXEC_MODE_MOCK_GPU,
    EXEC_MODE_REMOTE_CLUSTER,
    LocalRuntimeManager,
    RuntimeBudget,
)

__all__ = [
    "LocalHardwareInspector",
    "LocalHardwareProfile",
    "LocalRuntimeManager",
    "RuntimeBudget",
    "EXEC_MODE_LOCAL_CPU",
    "EXEC_MODE_MOCK_GPU",
    "EXEC_MODE_REMOTE_CLUSTER",
]
