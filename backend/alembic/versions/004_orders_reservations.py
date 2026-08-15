"""Create orders, snapshots and stock reservations."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "004_orders_reservations"
down_revision = "003_customers_carts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    op.create_table("orders", sa.Column("id", uuid, primary_key=True), sa.Column("customer_id", uuid, sa.ForeignKey("customers.id"), nullable=False), sa.Column("cart_id", uuid, sa.ForeignKey("carts.id"), nullable=False, unique=True), sa.Column("status_code", sa.String(40), nullable=False), sa.Column("recipient_first_name", sa.String(120), nullable=False), sa.Column("recipient_last_name", sa.String(120), nullable=False), sa.Column("phone", sa.String(30), nullable=False), sa.Column("delivery_method", sa.String(80), nullable=False), sa.Column("delivery_cost_kopecks", sa.Integer(), nullable=False), sa.Column("subtotal_kopecks", sa.Integer(), nullable=False), sa.Column("discount_kopecks", sa.Integer(), nullable=False), sa.Column("total_kopecks", sa.Integer(), nullable=False), sa.Column("reservation_expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_orders_customer_id", "orders", ["customer_id"])
    op.create_index("ix_orders_status_code", "orders", ["status_code"])
    op.create_index("ix_orders_reservation_expires_at", "orders", ["reservation_expires_at"])
    op.create_table("order_items", sa.Column("id", uuid, primary_key=True), sa.Column("order_id", uuid, sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False), sa.Column("variant_id", uuid, sa.ForeignKey("product_variants.id"), nullable=False), sa.Column("product_name", sa.String(200), nullable=False), sa.Column("product_sku", sa.String(100), nullable=False), sa.Column("variant_sku", sa.String(120), nullable=False), sa.Column("color", sa.String(80), nullable=False), sa.Column("size", sa.String(40), nullable=False), sa.Column("quantity", sa.Integer(), nullable=False), sa.Column("unit_price_kopecks", sa.Integer(), nullable=False))
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"])
    op.create_table("stock_reservations", sa.Column("id", uuid, primary_key=True), sa.Column("order_id", uuid, sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False), sa.Column("variant_id", uuid, sa.ForeignKey("product_variants.id"), nullable=False), sa.Column("quantity", sa.Integer(), nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("released_at", sa.DateTime(timezone=True), nullable=True), sa.UniqueConstraint("order_id", "variant_id", name="uq_stock_reservation_order_variant"))
    op.create_index("ix_stock_reservations_order_id", "stock_reservations", ["order_id"])
    op.create_index("ix_stock_reservations_variant_id", "stock_reservations", ["variant_id"])
    op.create_index("ix_stock_reservations_expires_at", "stock_reservations", ["expires_at"])
    op.create_table("promo_codes", sa.Column("id", uuid, primary_key=True), sa.Column("code", sa.String(64), nullable=False, unique=True), sa.Column("discount_type", sa.String(16), nullable=False), sa.Column("discount_value", sa.Integer(), nullable=False), sa.Column("minimum_order_kopecks", sa.Integer(), nullable=False), sa.Column("max_uses", sa.Integer(), nullable=True), sa.Column("per_customer_limit", sa.Integer(), nullable=True), sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True), sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True), sa.Column("is_active", sa.Boolean(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_promo_codes_code", "promo_codes", ["code"], unique=True)
    op.create_table("promo_redemptions", sa.Column("id", uuid, primary_key=True), sa.Column("promo_code_id", uuid, sa.ForeignKey("promo_codes.id"), nullable=False), sa.Column("customer_id", uuid, sa.ForeignKey("customers.id"), nullable=False), sa.Column("order_id", uuid, sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False), sa.Column("discount_kopecks", sa.Integer(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("promo_code_id", "order_id", name="uq_promo_redemption_order"))
    op.create_index("ix_promo_redemptions_promo_code_id", "promo_redemptions", ["promo_code_id"])
    op.create_index("ix_promo_redemptions_customer_id", "promo_redemptions", ["customer_id"])
    op.create_index("ix_promo_redemptions_order_id", "promo_redemptions", ["order_id"])


def downgrade() -> None:
    op.drop_table("promo_redemptions")
    op.drop_table("promo_codes")
    op.drop_table("stock_reservations")
    op.drop_table("order_items")
    op.drop_table("orders")
