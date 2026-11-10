"""Add offline gate event/photo idempotency and device sequence fields."""

from alembic import op
import sqlalchemy as sa

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("visitor_photos", sa.Column("client_photo_id", sa.String(length=64), nullable=True))
    with op.batch_alter_table("visitor_photos") as batch_op:
        batch_op.create_unique_constraint("uq_visitor_photos_client_photo_id", ["client_photo_id"])
    op.add_column("visitor_entries", sa.Column("device_id", sa.String(length=64), nullable=True))
    op.add_column("visitor_entries", sa.Column("device_generation_id", sa.String(length=64), nullable=True))
    op.add_column("visitor_entries", sa.Column("device_sequence", sa.Integer(), nullable=True))
    with op.batch_alter_table("visitor_entries") as batch_op:
        batch_op.create_unique_constraint(
            "uq_visitor_device_generation_sequence",
            ["device_id", "device_generation_id", "device_sequence"],
        )


def downgrade() -> None:
    with op.batch_alter_table("visitor_entries") as batch_op:
        batch_op.drop_constraint("uq_visitor_device_generation_sequence", type_="unique")
    op.drop_column("visitor_entries", "device_sequence")
    op.drop_column("visitor_entries", "device_generation_id")
    op.drop_column("visitor_entries", "device_id")
    with op.batch_alter_table("visitor_photos") as batch_op:
        batch_op.drop_constraint("uq_visitor_photos_client_photo_id", type_="unique")
    op.drop_column("visitor_photos", "client_photo_id")
