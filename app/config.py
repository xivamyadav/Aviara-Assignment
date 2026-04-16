from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    GEMINI_API_KEY: str = ""
    API_KEY: str = "ase-lead-automation-2024"
    DATABASE_URL: str = "sqlite+aiosqlite:///./leads.db"
    NOTIFICATION_WEBHOOK_URL: str = ""
    REDIS_URL: str = ""


@lru_cache()
def get_settings() -> Settings:
    return Settings()
