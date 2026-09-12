"""Gemini Developer API provider.

Build 1 status: written against the google-genai structured-output API and
wired into the provider registry, but NOT yet verified against the live
service - no API key has been configured for this project. Build 2 owns
verifying a real structured-output call and tuning the prompts.

Until then, AGENT_MODE=fake is the supported path. Selecting AGENT_MODE=gemini
without GEMINI_API_KEY raises ProviderUnavailable rather than silently
degrading, because the plan forbids substituting a fabricated negotiation for a
failed provider run.
"""

from __future__ import annotations

import json
import logging

from app.agents.base import (
    AgentContext,
    AgentDecision,
    InvalidModelOutput,
    ProviderUnavailable,
)
from app.agents.prompts import build_brief, system_instruction
from app.config import Settings

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 2

# Mirrors AgentDecision. Kept explicit rather than generated from the model so
# an accidental schema change here cannot silently widen what an agent may say.
RESPONSE_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["propose", "counter", "accept", "reject"]},
        "listing_id": {"type": "string"},
        "transport_option_id": {"type": "string"},
        "unit_price_paise_per_tonne": {"type": "integer"},
        "responds_to_offer_id": {"type": "string", "nullable": True},
        "explanation": {"type": "string"},
    },
    "required": [
        "action",
        "listing_id",
        "transport_option_id",
        "unit_price_paise_per_tonne",
        "explanation",
    ],
}


class GeminiAgentProvider:
    name = "gemini"

    def __init__(self, settings: Settings) -> None:
        if not settings.gemini_api_key:
            raise ProviderUnavailable("GEMINI_API_KEY is not configured.")
        try:
            from google import genai  # noqa: PLC0415 - optional dependency
        except ImportError as exc:  # pragma: no cover - depends on install
            raise ProviderUnavailable(
                "google-genai is not installed; run pip install -r requirements.txt."
            ) from exc

        self._genai = genai
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = settings.gemini_model

    def decide(self, context: AgentContext) -> AgentDecision:
        from google.genai import types  # noqa: PLC0415

        config = types.GenerateContentConfig(
            system_instruction=system_instruction(context.role),
            response_mime_type="application/json",
            response_schema=RESPONSE_SCHEMA,
            temperature=0.4,
        )

        last_error: Exception | None = None
        for attempt in range(MAX_ATTEMPTS):
            try:
                response = self._client.models.generate_content(
                    model=self._model,
                    contents=build_brief(context),
                    config=config,
                )
            except Exception as exc:  # provider/network/quota
                last_error = exc
                logger.warning(
                    "Gemini call failed (attempt %s/%s): %s", attempt + 1, MAX_ATTEMPTS, exc
                )
                continue

            text = (getattr(response, "text", None) or "").strip()
            if not text:
                last_error = InvalidModelOutput("Empty response from model.")
                continue

            try:
                return AgentDecision.model_validate(json.loads(text))
            except (json.JSONDecodeError, ValueError) as exc:
                last_error = InvalidModelOutput(str(exc))
                logger.warning("Gemini returned unusable output: %s", exc)

        if isinstance(last_error, InvalidModelOutput):
            raise last_error
        raise ProviderUnavailable(str(last_error) if last_error else "Gemini call failed.")
