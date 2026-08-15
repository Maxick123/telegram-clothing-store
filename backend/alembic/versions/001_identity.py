"""Create staff identity and RBAC tables."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001_identity"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    op.create_table("permissions", sa.Column("id", uuid, primary_key=True), sa.Column("code", sa.String(120), nullable=False, unique=True))
    op.create_index("ix_permissions_code", "permissions", ["code"], unique=True)
    op.create_table("roles", sa.Column("id", uuid, primary_key=True), sa.Column("name", sa.String(80), nullable=False, unique=True))
    op.create_table(
        "staff",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("login", sa.String(80), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_staff_login", "staff", ["login"], unique=True)
    op.create_table("role_permissions", sa.Column("role_id", uuid, sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True), sa.Column("permission_id", uuid, sa.ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True))
    op.create_table("staff_roles", sa.Column("staff_id", uuid, sa.ForeignKey("staff.id", ondelete="CASCADE"), primary_key=True), sa.Column("role_id", uuid, sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True))
    op.create_table(
        "refresh_sessions",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("staff_id", uuid, sa.ForeignKey("staff.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_refresh_sessions_staff_id", "refresh_sessions", ["staff_id"])
    op.create_index("ix_refresh_sessions_token_hash", "refresh_sessions", ["token_hash"], unique=True)


def downgrade() -> None:
    op.drop_table("refresh_sessions")
    op.drop_table("staff_roles")
    op.drop_table("role_permissions")
    op.drop_table("staff")
    op.drop_table("roles")
    op.drop_table("permissions")
