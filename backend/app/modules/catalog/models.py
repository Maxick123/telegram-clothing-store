from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Category(Base):
    __tablename__ = "categories"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    parent_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("categories.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(160))
    slug: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Collection(Base):
    __tablename__ = "collections"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(160))
    slug: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Product(Base):
    __tablename__ = "products"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    category_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("categories.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(220), unique=True, index=True)
    sku: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    brand: Mapped[str] = mapped_column(String(120), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    composition: Mapped[str] = mapped_column(Text, default="")
    care: Mapped[str] = mapped_column(Text, default="")
    size_chart: Mapped[str] = mapped_column(Text, default="")
    price_kopecks: Mapped[int] = mapped_column(Integer)
    old_price_kopecks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    variants: Mapped[list["ProductVariant"]] = relationship(back_populates="product", lazy="selectin")


class ProductVariant(Base):
    __tablename__ = "product_variants"
    __table_args__ = (UniqueConstraint("product_id", "color", "size", name="uq_variant_product_color_size"),)
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    product_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), index=True)
    sku: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    color: Mapped[str] = mapped_column(String(80))
    size: Mapped[str] = mapped_column(String(40))
    price_kopecks: Mapped[int] = mapped_column(Integer)
    stock_on_hand: Mapped[int] = mapped_column(Integer, default=0)
    stock_reserved: Mapped[int] = mapped_column(Integer, default=0)
    low_stock_threshold: Mapped[int] = mapped_column(Integer, default=2)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    product: Mapped[Product] = relationship(back_populates="variants")

    @property
    def available_quantity(self) -> int:
        return self.stock_on_hand - self.stock_reserved


class ProductMedia(Base):
    __tablename__ = "product_media"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    product_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), index=True)
    media_type: Mapped[str] = mapped_column(String(20))
    url: Mapped[str] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    variant_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("product_variants.id"), index=True)
    quantity_delta: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(80))
    reference_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    reference_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
