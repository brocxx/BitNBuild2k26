"""Shared FastAPI dependencies.

The backend resolves the caller's business from the verified token. A create
request never supplies an owner ID, so a client cannot act on behalf of another
business by crafting a body.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.tokens import verify_token
from app.config import Settings, get_settings
from app.db.models import AppUser, Business
from app.db.session import get_db
from app.errors import unauthenticated

# Declared as a security scheme rather than a raw header so that /docs gets a
# single Authorize button, and so a generated client knows these routes are
# authenticated. auto_error=False keeps the failure inside our error envelope
# instead of FastAPI's default shape.
bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="AccessToken",
    description=(
        "AUTH_MODE=dev: paste `dev:<email>` (for example "
        "`dev:buyer1@demo.bitnbuild.local`). "
        "AUTH_MODE=supabase: paste a Supabase access token."
    ),
)


@dataclass(frozen=True)
class CurrentUser:
    user: AppUser
    business: Business

    @property
    def business_id(self) -> str:
        return self.business.id


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ] = None,
    db: Annotated[Session, Depends(get_db)] = None,  # type: ignore[assignment]
    settings: Annotated[Settings, Depends(get_settings)] = None,  # type: ignore[assignment]
) -> CurrentUser:
    if credentials is None or not credentials.credentials.strip():
        raise unauthenticated("Authorization header must be 'Bearer <token>'.")

    claims = verify_token(credentials.credentials.strip(), settings)

    user: AppUser | None = None
    if settings.auth_mode == "supabase":
        user = db.scalar(select(AppUser).where(AppUser.supabase_user_id == claims.subject))

    if user is None and claims.email:
        user = db.scalar(select(AppUser).where(AppUser.email == claims.email.lower()))
        # First real login for a seeded demo account: bind the Supabase subject
        # to it so subsequent logins resolve by subject.
        if user is not None and settings.auth_mode == "supabase" and not user.supabase_user_id:
            user.supabase_user_id = claims.subject
            db.commit()

    if user is None:
        raise unauthenticated("No business profile is linked to this account.")

    return CurrentUser(user=user, business=user.business)


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]
DbDep = Annotated[Session, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
