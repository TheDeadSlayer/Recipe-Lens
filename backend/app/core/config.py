from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str

    # Providers
    transcript_provider: str = "mock"
    llm_provider: str = "mock"

    # OpenAI (only required when llm_provider=openai)
    # SecretStr prevents the key appearing in repr() / logs
    openai_api_key: SecretStr = SecretStr("")
    openai_model: str = ""
    openai_timeout_seconds: int = 60
    openai_max_retries: int = 2

    # Gemini (only required when llm_provider=gemini)
    # SecretStr prevents the key appearing in repr() / logs
    gemini_api_key: SecretStr = SecretStr("")
    gemini_model: str = "gemini-2.0-flash"
    gemini_timeout_seconds: int = 300

    # Whisper audio transcription (fallback when YouTube captions are unavailable)
    # Uses the same OPENAI_API_KEY — no additional secret needed.
    whisper_model: str = "whisper-1"
    whisper_timeout_seconds: int = 300

    # Application
    log_level: str = "INFO"

    # Connection pool — tune per deployment to avoid exhausting PostgreSQL connections
    # With N replicas each uses pool_size + max_overflow connections at peak.
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30

    # Testing
    test_database_url: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
