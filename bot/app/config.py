from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    telegram_bot_token: str
    backend_url: str = "http://backend:8000"
    telegram_admin_group_id: int | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
