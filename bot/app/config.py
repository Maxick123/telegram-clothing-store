from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    telegram_bot_token: str
    backend_url: str = "http://backend:8000"
    telegram_admin_group_id: int | None = None

    @field_validator("telegram_admin_group_id", mode="before")
    @classmethod
    def blank_group_id_is_none(cls, value: Any) -> Any:
        return None if value == "" else value


@lru_cache
def get_settings() -> Settings:
    return Settings()
