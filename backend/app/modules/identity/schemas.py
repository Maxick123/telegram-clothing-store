from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    login: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=8, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class StaffResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    login: str
    display_name: str
    permissions: list[str]
