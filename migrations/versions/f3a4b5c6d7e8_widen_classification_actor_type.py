"""widen classification actor identifier for emergency rule provenance

Revision ID: f3a4b5c6d7e8
Revises: e1f2a3b4c5d6
Create Date: 2026-11-09
"""

import sqlalchemy as sa
from alembic import op

revision = "f3a4b5c6d7e8"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("classification_decisions") as batch_op:
        batch_op.alter_column(
            "actor_type",
            existing_type=sa.String(length=20),
            type_=sa.String(length=50),
            existing_nullable=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    long_identifiers = bind.execute(
        sa.text("SELECT COUNT(*) FROM classification_decisions WHERE LENGTH(actor_type) > 20")
    ).scalar_one()
    if long_identifiers:
        raise RuntimeError("Cannot downgrade classification_decisions.actor_type while values exceed 20 characters.")
    with op.batch_alter_table("classification_decisions") as batch_op:
        batch_op.alter_column(
            "actor_type",
            existing_type=sa.String(length=50),
            type_=sa.String(length=20),
            existing_nullable=False,
        )
