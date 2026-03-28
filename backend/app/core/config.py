from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    environment: str = "development"
    debug: bool = True
    secret_key: str
    frontend_url: str = "http://localhost:3000"

    # Database
    database_url: str
    supabase_url: str
    supabase_service_key: str

    # Anthropic
    anthropic_api_key: str
    anthropic_model: str = "claude-opus-4-6"

    # Telegram
    webhook_base_url: str
    webhook_secret: str = "webhook-secret"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
