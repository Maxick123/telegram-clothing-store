from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str
    redis_url: str = "redis://redis:6379/0"
    jwt_secret: str
    access_token_minutes: int = 15
    refresh_token_days: int = 14
    cookie_secure: bool = False
    bootstrap_admin_login: str = "admin"
    bootstrap_admin_password: str | None = None
    bootstrap_support_login: str = "support"
    bootstrap_support_password: str | None = None
    auto_create_schema: bool = False
    stock_reservation_minutes: int = 15


@lru_cache
def get_settings() -> Settings:
    return Settings()
