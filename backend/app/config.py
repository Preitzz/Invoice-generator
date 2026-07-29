from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+psycopg://app_user:app_password@localhost:5432/invoice_reminder"
    DATABASE_URL_SYNC_ADMIN: str = "postgresql+psycopg://postgres:postgres@localhost:5432/invoice_reminder"
    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str = "change-me-in-production"
    EMAIL_PROVIDER: str = "fake"
    REMINDER_KILL_SWITCH_DEFAULT: bool = False
    SEED_ADMIN_PASSWORD: str = "ChangeMe123!"
    APP_DB_ROLE: str = "app_user"
    ENVIRONMENT: str = "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
