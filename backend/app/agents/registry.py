"""Provider selection.

There is no automatic fallback from gemini to fake. A failed provider run must
surface as a failed negotiation, never as a fabricated one.
"""

from __future__ import annotations

from app.agents.base import AgentProvider
from app.agents.fake import FakeAgentProvider
from app.config import Settings


def build_provider(settings: Settings) -> AgentProvider:
    if settings.agent_mode == "gemini":
        from app.agents.gemini import GeminiAgentProvider  # noqa: PLC0415

        return GeminiAgentProvider(settings)
    return FakeAgentProvider()
