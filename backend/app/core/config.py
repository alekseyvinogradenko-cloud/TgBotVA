from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    environment: str = "development"
    debug: bool = False  # default off — opt in via DEBUG=true (prevents SQL/PII echo in prod logs)
    secret_key: str
    frontend_url: str = "http://localhost:3000"
    admin_api_key: str = ""  # required header to register workspaces; empty = endpoint disabled

    # Database
    database_url: str
    supabase_url: str
    supabase_service_key: str

    # Anthropic
    anthropic_api_key: str
    anthropic_model: str = "claude-sonnet-4-6"

    # Telegram
    webhook_base_url: str
    webhook_secret: str = "webhook-secret"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
