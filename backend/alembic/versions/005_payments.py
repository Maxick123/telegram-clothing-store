"""Create payment records."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision = "005_payments"
down_revision = "004_orders_reservations"
branch_labels = None
depends_on = None
def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    op.create_table("payments", sa.Column("id", uuid, primary_key=True), sa.Column("order_id", uuid, sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, unique=True), sa.Column("provider", sa.String(32), nullable=False), sa.Column("external_id", sa.String(128), nullable=True, unique=True), sa.Column("status", sa.String(32), nullable=False), sa.Column("confirmation_url", sa.String(2048), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_payments_order_id", "payments", ["order_id"], unique=True)
    op.create_index("ix_payments_status", "payments", ["status"])
def downgrade() -> None:
    op.drop_table("payments")
