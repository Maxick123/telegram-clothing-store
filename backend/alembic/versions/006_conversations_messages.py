"""Create CRM conversations and message delivery history."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "006_conversations_messages"
down_revision = "005_payments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    op.create_table(
        "conversations",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("customer_id", uuid, sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_id", uuid, sa.ForeignKey("orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("assigned_staff_id", uuid, sa.ForeignKey("staff.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_conversations_customer_id", "conversations", ["customer_id"])
    op.create_index("ix_conversations_order_id", "conversations", ["order_id"])
    op.create_index("ix_conversations_assigned_staff_id", "conversations", ["assigned_staff_id"])
    op.create_index("ix_conversations_status", "conversations", ["status"])
    op.create_index("ix_conversations_last_message_at", "conversations", ["last_message_at"])
    op.create_table(
        "messages",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("conversation_id", uuid, sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_type", sa.String(16), nullable=False),
        sa.Column("author_customer_id", uuid, sa.ForeignKey("customers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("author_staff_id", uuid, sa.ForeignKey("staff.id", ondelete="SET NULL"), nullable=True),
        sa.Column("direction", sa.String(16), nullable=False),
        sa.Column("channel", sa.String(32), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("media", sa.JSON(), nullable=False),
        sa.Column("telegram_message_id", sa.BigInteger(), nullable=True),
        sa.Column("delivery_status", sa.String(16), nullable=False),
        sa.Column("delivery_error", sa.Text(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.create_index("ix_messages_author_customer_id", "messages", ["author_customer_id"])
    op.create_index("ix_messages_author_staff_id", "messages", ["author_staff_id"])
    op.create_index("ix_messages_telegram_message_id", "messages", ["telegram_message_id"])
    op.create_index("ix_messages_delivery_status", "messages", ["delivery_status"])
    op.create_index("ix_messages_created_at", "messages", ["created_at"])


def downgrade() -> None:
    op.drop_table("messages")
    op.drop_table("conversations")
