"""Application settings loaded from environment variables.

Twelve-Factor app methodology stores configuration in the environment, never in
code or in the repository. That keeps the same build artifact deployable as the
public online demo (EXTRACTION_MODE=mock) and as Local Docker Mode (real
Vision LLM): only the environment changes.

``get_settings`` is cached with :func:`functools.lru_cache` so the environment
is parsed and validated once per process instead of on every request; reads
after the first are a dictionary lookup. The cached getter also means a test
that mutates the environment must clear the cache
(``get_settings.cache_clear()``) to see new values.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven application settings.

    Raises:
        ValidationError: If an environment value cannot be parsed into the
            declared field type (for example a non-integer where an integer
            is required).
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ENVIRONMENT: str = "development"
    APP_VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]
    LOG_LEVEL: str = "INFO"

    @property
    def is_production(self) -> bool:
        """Return True when the app runs with production settings applied."""
        return self.ENVIRONMENT == "production"


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide cached Settings instance."""
    return Settings()
