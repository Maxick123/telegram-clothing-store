from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Cart(Base):
    __tablename__ = "carts"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    customer_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))


class CartItem(Base):
    __tablename__ = "cart_items"
    __table_args__ = (UniqueConstraint("cart_id", "variant_id", name="uq_cart_item_variant"),)
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    cart_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("carts.id", ondelete="CASCADE"), index=True)
    variant_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("product_variants.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer)


class Order(Base):
    __tablename__ = "orders"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    customer_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("customers.id"), index=True)
    cart_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("carts.id"), unique=True)
    status_code: Mapped[str] = mapped_column(String(40), default="awaiting_payment", index=True)
    recipient_first_name: Mapped[str] = mapped_column(String(120))
    recipient_last_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(30))
    delivery_method: Mapped[str] = mapped_column(String(80))
    delivery_cost_kopecks: Mapped[int] = mapped_column(Integer, default=0)
    subtotal_kopecks: Mapped[int] = mapped_column(Integer)
    discount_kopecks: Mapped[int] = mapped_column(Integer, default=0)
    total_kopecks: Mapped[int] = mapped_column(Integer)
    reservation_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class OrderItem(Base):
    __tablename__ = "order_items"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    variant_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("product_variants.id"))
    product_name: Mapped[str] = mapped_column(String(200))
    product_sku: Mapped[str] = mapped_column(String(100))
    variant_sku: Mapped[str] = mapped_column(String(120))
    color: Mapped[str] = mapped_column(String(80))
    size: Mapped[str] = mapped_column(String(40))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price_kopecks: Mapped[int] = mapped_column(Integer)


class StockReservation(Base):
    __tablename__ = "stock_reservations"
    __table_args__ = (UniqueConstraint("order_id", "variant_id", name="uq_stock_reservation_order_variant"),)
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    variant_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("product_variants.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
