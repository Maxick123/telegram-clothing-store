from uuid import UUID

from pydantic import BaseModel, Field


class CartItemCreate(BaseModel):
    variant_id: UUID
    quantity: int = Field(ge=1, le=20)
