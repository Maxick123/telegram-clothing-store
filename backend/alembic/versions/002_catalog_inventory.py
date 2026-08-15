"""Create catalogue, variants, media and inventory movements."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "002_catalog_inventory"
down_revision = "001_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    op.create_table("categories", sa.Column("id", uuid, primary_key=True), sa.Column("parent_id", uuid, sa.ForeignKey("categories.id"), nullable=True), sa.Column("name", sa.String(160), nullable=False), sa.Column("slug", sa.String(180), nullable=False, unique=True), sa.Column("sort_order", sa.Integer(), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False))
    op.create_index("ix_categories_slug", "categories", ["slug"], unique=True)
    op.create_table("collections", sa.Column("id", uuid, primary_key=True), sa.Column("name", sa.String(160), nullable=False), sa.Column("slug", sa.String(180), nullable=False, unique=True), sa.Column("description", sa.Text(), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False))
    op.create_index("ix_collections_slug", "collections", ["slug"], unique=True)
    op.create_table("products", sa.Column("id", uuid, primary_key=True), sa.Column("category_id", uuid, sa.ForeignKey("categories.id"), nullable=False), sa.Column("name", sa.String(200), nullable=False), sa.Column("slug", sa.String(220), nullable=False, unique=True), sa.Column("sku", sa.String(100), nullable=False, unique=True), sa.Column("brand", sa.String(120), nullable=False), sa.Column("description", sa.Text(), nullable=False), sa.Column("composition", sa.Text(), nullable=False), sa.Column("care", sa.Text(), nullable=False), sa.Column("size_chart", sa.Text(), nullable=False), sa.Column("price_kopecks", sa.Integer(), nullable=False), sa.Column("old_price_kopecks", sa.Integer(), nullable=True), sa.Column("is_published", sa.Boolean(), nullable=False), sa.Column("is_archived", sa.Boolean(), nullable=False))
    for name, columns, unique in (("ix_products_category_id", ["category_id"], False), ("ix_products_slug", ["slug"], True), ("ix_products_sku", ["sku"], True)):
        op.create_index(name, "products", columns, unique=unique)
    op.create_table("product_variants", sa.Column("id", uuid, primary_key=True), sa.Column("product_id", uuid, sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False), sa.Column("sku", sa.String(120), nullable=False, unique=True), sa.Column("color", sa.String(80), nullable=False), sa.Column("size", sa.String(40), nullable=False), sa.Column("price_kopecks", sa.Integer(), nullable=False), sa.Column("stock_on_hand", sa.Integer(), nullable=False), sa.Column("stock_reserved", sa.Integer(), nullable=False), sa.Column("low_stock_threshold", sa.Integer(), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False), sa.UniqueConstraint("product_id", "color", "size", name="uq_variant_product_color_size"))
    op.create_index("ix_product_variants_product_id", "product_variants", ["product_id"])
    op.create_index("ix_product_variants_sku", "product_variants", ["sku"], unique=True)
    op.create_table("product_media", sa.Column("id", uuid, primary_key=True), sa.Column("product_id", uuid, sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False), sa.Column("media_type", sa.String(20), nullable=False), sa.Column("url", sa.Text(), nullable=False), sa.Column("sort_order", sa.Integer(), nullable=False))
    op.create_index("ix_product_media_product_id", "product_media", ["product_id"])
    op.create_table("inventory_movements", sa.Column("id", uuid, primary_key=True), sa.Column("variant_id", uuid, sa.ForeignKey("product_variants.id"), nullable=False), sa.Column("quantity_delta", sa.Integer(), nullable=False), sa.Column("reason", sa.String(80), nullable=False), sa.Column("reference_type", sa.String(40), nullable=True), sa.Column("reference_id", uuid, nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_inventory_movements_variant_id", "inventory_movements", ["variant_id"])


def downgrade() -> None:
    for table in ("inventory_movements", "product_media", "product_variants", "products", "collections", "categories"):
        op.drop_table(table)
