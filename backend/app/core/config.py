"""
Centralized environment configuration for H.I.R.E.

This module is the single source of truth for all environment-based
configuration. No other module should call os.getenv() or otherwise
read environment variables directly; import `settings` (or call
`get_settings()`) from here instead.
"""

from enum import Enum
from functools import lru_cache
from typing import List, Optional, Union
from typing_extensions import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Environment(str, Enum):
    """Restricts ENVIRONMENT to a known set of valid deployment targets."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables / .env file.

    Field requirements follow HIRE-BE-002 decisions:
    - SECRET_KEY is required (no default) so the app fails fast if unset.
    - DATABASE_URL remains optional until the database implementation
      ticket introduces an actual connection.
    - OPENAI_API_KEY / GEMINI_API_KEY are reserved for future AI
      integration; no AI provider logic is implemented in this ticket.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # ------------------------------------------------------------------
    # Application metadata
    # ------------------------------------------------------------------
    APP_NAME: str = Field(default="H.I.R.E.", min_length=1)
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "Human-Interactive Intelligent Recruitment Engine"

    # ------------------------------------------------------------------
    # Runtime environment
    # ------------------------------------------------------------------
    ENVIRONMENT: Environment = Environment.DEVELOPMENT
    DEBUG: bool = True

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------
    API_PREFIX: str = "/api/v1"

    # ------------------------------------------------------------------
    # Security / Auth
    # ------------------------------------------------------------------
    SECRET_KEY: str = Field(min_length=32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, gt=0)

    # ------------------------------------------------------------------
    # Database (optional until HIRE-BE-DB ticket)
    # ------------------------------------------------------------------
    DATABASE_URL: Optional[str] = None

    # ------------------------------------------------------------------
    # Reserved AI provider configuration (no AI implementation yet)
    # ------------------------------------------------------------------
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None

    # ------------------------------------------------------------------
    # File uploads
    # ------------------------------------------------------------------
    UPLOAD_DIRECTORY: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = Field(default=10, gt=0)

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------
    ALLOWED_ORIGINS: Annotated[List[str], NoDecode] = ["http://localhost:3000"]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def split_allowed_origins(cls, value: Union[str, List[str]]) -> List[str]:
        """
        Allow ALLOWED_ORIGINS to be provided as a comma-separated string
        in the .env file (e.g. "http://localhost:3000,http://localhost:5173")
        while exposing it to the application as a List[str].

        NoDecode prevents pydantic-settings from attempting to JSON-decode
        this field before the validator runs, since the .env value is a
        plain comma-separated string rather than a JSON array.
        """
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    """
    Return a cached Settings instance.

    Using lru_cache ensures the .env file is parsed once per process
    rather than on every import/request, while still allowing tests
    to override settings via dependency overrides if needed later.
    """
    return Settings()


settings = get_settings()