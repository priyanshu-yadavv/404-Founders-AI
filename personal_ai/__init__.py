"""
404 FOUNDERS — Personal AI Subsystem
Operating system intelligence, desktop assistance, and defensive workstation copilot.
"""

from personal_ai.controller import (
    AgentInteractionResponse,
    PersonalAIController,
)
from personal_ai.emergency.kill_switch import (
    EmergencyShutdownController,
    EmergencyShutdownState,
)
from personal_ai.memory_bridge import PersonalAIMemoryBridge
from personal_ai.os_adapters import (
    BaseOSAdapter,
    LinuxAdapter,
    WindowsAdapter,
    get_os_adapter,
)
from personal_ai.permissions.approval_manager import (
    ApprovalManager,
    ApprovalTicket,
    CommandRiskTier,
    TicketStatus,
)
from personal_ai.router import (
    NaturalLanguageToolRouter,
    PersonalAIIntent,
    RoutedIntentResult,
)
from personal_ai.runtime import (
    AgentRuntimeStatus,
    AgentSession,
    LocalAgentRuntime,
)
from personal_ai.voice.voice_interface import (
    SpeakerVerificationResult,
    VoiceAssistantFoundation,
    VoiceProfile,
    VoiceSessionState,
    WakeWordDetectionResult,
)

__all__ = [
    "AgentInteractionResponse",
    "AgentRuntimeStatus",
    "AgentSession",
    "ApprovalManager",
    "ApprovalTicket",
    "BaseOSAdapter",
    "CommandRiskTier",
    "EmergencyShutdownController",
    "EmergencyShutdownState",
    "LinuxAdapter",
    "LocalAgentRuntime",
    "NaturalLanguageToolRouter",
    "PersonalAIController",
    "PersonalAIIntent",
    "PersonalAIMemoryBridge",
    "RoutedIntentResult",
    "SpeakerVerificationResult",
    "TicketStatus",
    "VoiceAssistantFoundation",
    "VoiceProfile",
    "VoiceSessionState",
    "WakeWordDetectionResult",
    "WindowsAdapter",
    "get_os_adapter",
]
