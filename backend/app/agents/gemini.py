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
import re
import threading
import time

from app.agents.base import (
    AgentContext,
    AgentDecision,
    InvalidModelOutput,
    ProviderUnavailable,
)
from app.agents.prompts import build_brief, system_instruction
from app.config import Settings

logger = logging.getLogger(__name__)

# Google returns the wait it wants in the error body, e.g.
#   "Please retry in 26.506550745s"  /  "'retryDelay': '26s'"
# Honouring that is far better than guessing a backoff.
_RETRY_DELAY_PATTERN = re.compile(
    r"(?:retry in|retryDelay'?:?\s*'?)\s*([0-9]+(?:\.[0-9]+)?)s", re.IGNORECASE
)
# Never sleep longer than this for one attempt, so a broken quota cannot hang
# a negotiation indefinitely.
MAX_BACKOFF_SECONDS = 40.0


def _is_rate_limited(error: Exception) -> bool:
    text = str(error)
    return "429" in text or "RESOURCE_EXHAUSTED" in text


def _suggested_delay(error: Exception, attempt: int) -> float:
    match = _RETRY_DELAY_PATTERN.search(str(error))
    if match:
        # A second of headroom: the quota window is not perfectly aligned with
        # our clock, and retrying a hair early just burns another attempt.
        return min(float(match.group(1)) + 1.0, MAX_BACKOFF_SECONDS)
    return min(2.0**attempt, MAX_BACKOFF_SECONDS)


class _RateLimiter:
    """Spaces calls so the per-minute free-tier quota is not tripped.

    Shared across every agent in a run, because the quota is per project and
    per model, not per agent. A negotiation issues its calls sequentially, so
    a simple minimum interval is enough; the lock is there because FastAPI
    runs background tasks in a thread pool.
    """

    def __init__(self, max_rpm: int) -> None:
        self._min_interval = 60.0 / max_rpm if max_rpm > 0 else 0.0
        self._lock = threading.Lock()
        self._next_allowed_at = 0.0

    def wait(self) -> None:
        if self._min_interval <= 0:
            return
        with self._lock:
            now = time.monotonic()
            delay = self._next_allowed_at - now
            if delay > 0:
                time.sleep(delay)
                now = time.monotonic()
            self._next_allowed_at = now + self._min_interval

    def pause_for(self, seconds: float) -> None:
        """After a 429, hold every caller off for the window Google asked for."""
        with self._lock:
            self._next_allowed_at = max(
                self._next_allowed_at, time.monotonic() + seconds
            )

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
        self._max_attempts = max(1, settings.gemini_max_attempts)
        self._limiter = _RateLimiter(settings.gemini_max_rpm)

    def decide(self, context: AgentContext) -> AgentDecision:
        from google.genai import types  # noqa: PLC0415

        config = types.GenerateContentConfig(
            system_instruction=system_instruction(context.role),
            response_mime_type="application/json",
            response_schema=RESPONSE_SCHEMA,
            temperature=0.4,
        )

        last_error: Exception | None = None
        for attempt in range(self._max_attempts):
            self._limiter.wait()
            try:
                response = self._client.models.generate_content(
                    model=self._model,
                    contents=build_brief(context),
                    config=config,
                )
            except Exception as exc:  # provider/network/quota
                last_error = exc
                if _is_rate_limited(exc) and attempt < self._max_attempts - 1:
                    delay = _suggested_delay(exc, attempt)
                    # Hold every other agent off too - the quota is shared.
                    self._limiter.pause_for(delay)
                    logger.warning(
                        "Gemini rate limited (attempt %s/%s); waiting %.1fs as "
                        "instructed by the API.",
                        attempt + 1,
                        self._max_attempts,
                        delay,
                    )
                    continue
                logger.warning(
                    "Gemini call failed (attempt %s/%s): %s",
                    attempt + 1,
                    self._max_attempts,
                    exc,
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
