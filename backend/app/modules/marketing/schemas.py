from datetime import datetime

from pydantic import BaseModel, Field


class PromoCodeCreate(BaseModel):
    code: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    discount_type: str = Field(pattern=r"^(percent|fixed)$")
    discount_value: int = Field(gt=0)
    minimum_order_kopecks: int = Field(default=0, ge=0)
    max_uses: int | None = Field(default=None, ge=1)
    per_customer_limit: int | None = Field(default=None, ge=1)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
