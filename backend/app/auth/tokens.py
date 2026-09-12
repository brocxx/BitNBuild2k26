"""Resolving an Authorization header to an authenticated principal.

Two modes:

dev       Accepts "Bearer dev:<email>" and looks the address up in app_users.
          Local development and tests only. It never parses a JWT, so a real
          Supabase token cannot accidentally be accepted unverified.

supabase  Verifies the access token's signature before reading any claim.
          Asymmetric keys (the current Supabase default) are fetched from the
          project JWKS endpoint and cached; a legacy HS256 project can instead
          set SUPABASE_JWT_SECRET. If neither is configured the request fails
          with 503 rather than falling back to trusting the token.

Nothing in this module ever reads claims from an unverified token.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import jwt
from jwt import PyJWKClient

from app.config import Settings
from app.errors import unauthenticated, unavailable


@dataclass(frozen=True)
class TokenClaims:
    subject: str
    email: str | None


DEV_PREFIX = "dev:"

# Tolerance for clock skew between this machine and Supabase's auth servers.
# Without it, PyJWT validates `iat` with zero slack and a machine even a couple
# of seconds behind rejects every freshly issued token as "not yet valid" -
# measured at 3 seconds of skew on a developer laptop during setup. Sixty
# seconds is the conventional allowance and is negligible against a one-hour
# token lifetime.
CLOCK_SKEW_LEEWAY_SECONDS = 60


@lru_cache(maxsize=4)
def _jwk_client(jwks_url: str) -> PyJWKClient:
    # PyJWKClient caches fetched keys internally; lru_cache keeps one client
    # per project so we are not re-fetching JWKS on every request.
    return PyJWKClient(jwks_url, cache_keys=True)


def verify_token(token: str, settings: Settings) -> TokenClaims:
    if settings.auth_mode == "dev":
        return _verify_dev(token)
    return _verify_supabase(token, settings)


def _verify_dev(token: str) -> TokenClaims:
    if not token.startswith(DEV_PREFIX):
        raise unauthenticated(
            "AUTH_MODE=dev expects a token of the form 'dev:<email>'."
        )
    email = token[len(DEV_PREFIX) :].strip().lower()
    if not email:
        raise unauthenticated("Dev token is missing an email address.")
    return TokenClaims(subject=f"dev:{email}", email=email)


def _verify_supabase(token: str, settings: Settings) -> TokenClaims:
    if not settings.supabase_url and not settings.supabase_jwt_secret:
        raise unavailable(
            "AUTH_NOT_CONFIGURED",
            "AUTH_MODE=supabase requires SUPABASE_URL or SUPABASE_JWT_SECRET.",
        )

    options = {"require": ["exp", "sub"]}
    audience = settings.supabase_jwt_audience or None

    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise unauthenticated("Malformed access token.") from exc

    algorithm = header.get("alg", "")

    try:
        if algorithm.startswith(("RS", "ES")):
            if not settings.supabase_url:
                raise unavailable(
                    "AUTH_NOT_CONFIGURED",
                    "Asymmetric Supabase token requires SUPABASE_URL for JWKS lookup.",
                )
            jwks_url = f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
            signing_key = _jwk_client(jwks_url).get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=[algorithm],
                audience=audience,
                options=options,
                leeway=CLOCK_SKEW_LEEWAY_SECONDS,
            )
        elif algorithm == "HS256":
            if not settings.supabase_jwt_secret:
                raise unauthenticated(
                    "Token is HS256 signed but SUPABASE_JWT_SECRET is not configured."
                )
            payload = jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience=audience,
                options=options,
                leeway=CLOCK_SKEW_LEEWAY_SECONDS,
            )
        else:
            raise unauthenticated(f"Unsupported token algorithm '{algorithm}'.")
    except jwt.ExpiredSignatureError as exc:
        raise unauthenticated("Access token has expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise unauthenticated("Access token failed verification.") from exc
    except jwt.PyJWKClientError as exc:
        raise unavailable(
            "AUTH_KEY_UNAVAILABLE", "Could not retrieve Supabase signing keys."
        ) from exc

    subject = payload.get("sub")
    if not subject:
        raise unauthenticated("Access token has no subject claim.")
    return TokenClaims(subject=str(subject), email=payload.get("email"))
