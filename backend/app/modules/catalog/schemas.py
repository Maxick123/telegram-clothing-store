from uuid import UUID

from pydantic import BaseModel, Field


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    parent_id: UUID | None = None


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    sku: str = Field(min_length=1, max_length=100)
    category_id: UUID
    price_kopecks: int = Field(ge=0)
    brand: str = ""
    description: str = ""


class VariantCreate(BaseModel):
    color: str = Field(min_length=1, max_length=80)
    size: str = Field(min_length=1, max_length=40)
    sku: str = Field(min_length=1, max_length=120)
    stock_on_hand: int = Field(ge=0)
    price_kopecks: int = Field(ge=0)
