"""Application settings, loaded from backend/.env or the process environment."""

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent
DATASET_DIR = REPO_ROOT / "dataset"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Which database the app and migrations actually talk to.
    #   local    -> database_url (SQLite by default; no credentials needed)
    #   supabase -> supabase_database_url
    # Both connection strings live in .env at once so a teammate without
    # Supabase credentials can run the whole backend on DB_TARGET=local.
    db_target: Literal["local", "supabase"] = "local"
    database_url: str = "sqlite:///./bitnbuild.db"
    supabase_database_url: str = ""

    auth_mode: Literal["dev", "supabase"] = "dev"
    supabase_url: str = ""
    # Supabase's new-style secret key (sb_secret_...), formerly service_role.
    # Full admin access: used only by the demo-account provisioning script,
    # never on a request path, and never sent to the frontend.
    supabase_secret_key: str = ""
    # Only for a legacy project that still signs tokens with a shared HS256
    # secret. Projects on asymmetric signing keys do not need this.
    supabase_jwt_secret: str = ""
    supabase_jwt_audience: str = "authenticated"

    agent_mode: Literal["fake", "gemini"] = "fake"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    # Free-tier Gemini limits requests per MINUTE, not only per day
    # (gemini-3.1-flash-lite: 15/min). A negotiation fires calls back to back
    # and will trip it partway through unless they are paced. Read the real
    # number off https://aistudio.google.com/rate-limit for your model.
    gemini_max_rpm: int = 15
    gemini_max_attempts: int = 4

    max_rounds_per_candidate: int = 4
    max_candidates_per_negotiation: int = 3
    max_transport_options_per_listing: int = 2

    # Run the coordinator inline inside the POST request instead of in a
    # background task. Tests set this; the served app leaves it False so
    # POST /negotiations returns 202 immediately and the UI polls.
    negotiation_run_inline: bool = False

    # NoDecode: the env value is a plain comma-separated list, not JSON, so
    # pydantic-settings must hand it to the validator below untouched.
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def active_database_url(self) -> str:
        """The connection string everything should actually use."""
        if self.db_target == "supabase":
            if not self.supabase_database_url:
                raise ValueError(
                    "DB_TARGET=supabase but SUPABASE_DATABASE_URL is not set."
                )
            return self.supabase_database_url
        return self.database_url

    @property
    def is_sqlite(self) -> bool:
        return self.active_database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
