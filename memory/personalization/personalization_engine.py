"""
404 FOUNDERS — Personalization Engine
Derives authorized behavioral formatting rules, response verbosity,
technical depth, and domain conventions from user preferences.
Ensures transparent, non-manipulative personalization.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from database.connection import DatabaseManager
from memory.user_preferences import UserPreferenceMemory


@dataclass
class PersonalizationProfile:
    """Active personalization parameters for an authorized user."""
    user_id: str
    communication_style: str
    response_length: str
    technical_depth: str
    code_preference: str
    explanation_mode: str
    guidance_directive: str


class PersonalizationEngine:
    """
    Personalization Engine.
    Translates stored user preferences into concrete generation directives.
    """

    def __init__(
        self,
        pref_memory: Optional[UserPreferenceMemory] = None,
        db_manager: Optional[DatabaseManager] = None,
    ) -> None:
        self.pref_memory = pref_memory or UserPreferenceMemory(db_manager)

    def get_personalization_profile(self, user_id: str) -> PersonalizationProfile:
        """Fetch active personalization parameters and formulate runtime prompt directives."""
        prefs = self.pref_memory.get_all_preferences(user_id)

        style = prefs.get("communication_style", "balanced")
        length = prefs.get("response_length", "medium")
        depth = prefs.get("technical_depth", "intermediate")
        code = prefs.get("code_preference", "python")
        mode = prefs.get("explanation_mode", "step_by_step")

        directive_parts = []

        # Style directive
        if style == "concise":
            directive_parts.append("Provide concise, direct answers with minimal conversational filler.")
        elif style == "detailed":
            directive_parts.append("Provide thorough, in-depth explanations covering background and edge cases.")
        elif style == "academic":
            directive_parts.append("Adopt a rigorous, formal academic tone citing formal principles.")
        else:
            directive_parts.append("Maintain a balanced, clear, and professional tone.")

        # Length directive
        if length == "short":
            directive_parts.append("Keep response length compact and tightly focused on core conclusions.")
        elif length == "comprehensive":
            directive_parts.append("Provide comprehensive coverage with full details.")

        # Depth directive
        if depth == "beginner":
            directive_parts.append("Explain concepts using accessible terminology and gentle foundational context.")
        elif depth == "expert":
            directive_parts.append("Assume advanced domain expertise; omit introductory fundamentals.")

        # Code preference
        if code:
            directive_parts.append(f"When providing code examples, prefer {code.capitalize()} unless specified otherwise.")

        # Explanation mode
        if mode == "step_by_step":
            directive_parts.append("Structure complex solutions sequentially step-by-step.")
        elif mode == "direct_summary":
            directive_parts.append("Present the direct solution upfront first.")

        directive_text = " ".join(directive_parts)

        return PersonalizationProfile(
            user_id=user_id,
            communication_style=style,
            response_length=length,
            technical_depth=depth,
            code_preference=code,
            explanation_mode=mode,
            guidance_directive=directive_text,
        )

    def generate_prompt_guidance(self, user_id: str) -> str:
        """Return the formatted system prompt instruction for personalized generation."""
        profile = self.get_personalization_profile(user_id)
        return f"[User Preferences & Persona Directive]: {profile.guidance_directive}"
