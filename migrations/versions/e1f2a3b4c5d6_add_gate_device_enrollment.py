"""Persist gate device enrollment and server-side sequence state."""

from alembic import op
import sqlalchemy as sa

revision = "e1f2a3b4c5d6"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "gate_devices",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("device_id", sa.String(length=64), nullable=False),
        sa.Column("generation_id", sa.String(length=64), nullable=False),
        sa.Column("gate_id", sa.String(length=36), nullable=False),
        sa.Column("enrolled_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_sequence", sa.Integer(), nullable=False),
        sa.Column("enrolled_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["gate_id"], ["gates.id"]),
        sa.ForeignKeyConstraint(["enrolled_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("device_id", name="uq_gate_devices_device_id"),
    )
    op.create_index("ix_gate_devices_gate_id", "gate_devices", ["gate_id"])
    with op.batch_alter_table("notice_reads") as batch_op:
        batch_op.create_unique_constraint(
            "uq_notice_reads_revision_user", ["notice_revision_id", "user_id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("notice_reads") as batch_op:
        batch_op.drop_constraint("uq_notice_reads_revision_user", type_="unique")
    op.drop_index("ix_gate_devices_gate_id", table_name="gate_devices")
    op.drop_table("gate_devices")
