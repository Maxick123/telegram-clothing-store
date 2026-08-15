from uuid import UUID

from pydantic import BaseModel, Field


class CartItemCreate(BaseModel):
    variant_id: UUID
    quantity: int = Field(ge=1, le=20)


class CheckoutCreate(BaseModel):
    cart_id: UUID
    recipient_first_name: str = Field(min_length=1, max_length=120)
    recipient_last_name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=5, max_length=30)
    delivery_method: str = Field(min_length=1, max_length=80)
    delivery_cost_kopecks: int = Field(ge=0)
    promo_code: str | None = Field(default=None, min_length=3, max_length=64)
