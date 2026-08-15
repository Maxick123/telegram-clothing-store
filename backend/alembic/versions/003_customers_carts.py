"""Create customers, favorites and carts."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "003_customers_carts"
down_revision = "002_catalog_inventory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    op.create_table("customers", sa.Column("id", uuid, primary_key=True), sa.Column("telegram_id", sa.BigInteger(), nullable=False, unique=True), sa.Column("username", sa.String(80), nullable=True), sa.Column("first_name", sa.String(120), nullable=False), sa.Column("last_name", sa.String(120), nullable=False), sa.Column("phone", sa.String(30), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_customers_telegram_id", "customers", ["telegram_id"], unique=True)
    op.create_table("favorites", sa.Column("id", uuid, primary_key=True), sa.Column("customer_id", uuid, sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False), sa.Column("product_id", uuid, sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False), sa.UniqueConstraint("customer_id", "product_id", name="uq_favorite_customer_product"))
    op.create_table("carts", sa.Column("id", uuid, primary_key=True), sa.Column("customer_id", uuid, sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_carts_customer_id", "carts", ["customer_id"])
    op.create_index("ix_carts_status", "carts", ["status"])
    op.create_table("cart_items", sa.Column("id", uuid, primary_key=True), sa.Column("cart_id", uuid, sa.ForeignKey("carts.id", ondelete="CASCADE"), nullable=False), sa.Column("variant_id", uuid, sa.ForeignKey("product_variants.id"), nullable=False), sa.Column("quantity", sa.Integer(), nullable=False), sa.UniqueConstraint("cart_id", "variant_id", name="uq_cart_item_variant"))
    op.create_index("ix_cart_items_cart_id", "cart_items", ["cart_id"])
    op.create_index("ix_cart_items_variant_id", "cart_items", ["variant_id"])


def downgrade() -> None:
    op.drop_table("cart_items")
    op.drop_table("carts")
    op.drop_table("favorites")
    op.drop_table("customers")
