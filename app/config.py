"""Application configuration loaded from environment variables / .env file.

Centralizing settings here keeps secrets out of source code and lets the
Android app's API base URL be configured without touching logic.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the translation backend."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # NLLB-200 model identifier from the Hugging Face hub.
    nllb_model: str = "facebook/nllb-200-distilled-600M"

    # torch device: "cpu" or "cuda".
    device: str = "cpu"

    # Generation limits protect against runaway requests.
    max_source_length: int = 512
    max_target_length: int = 512

    # CORS: comma-separated origins, blank means allow all (dev only).
    allowed_origins: str = ""

    # Server bind settings.
    host: str = "0.0.0.0"
    port: int = 8000

    @property
    def cors_origins(self) -> list[str]:
        """Return the list of allowed CORS origins, or ["*"] when unset."""
        if not self.allowed_origins.strip():
            return ["*"]
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance so env is read only once."""
    return Settings()
