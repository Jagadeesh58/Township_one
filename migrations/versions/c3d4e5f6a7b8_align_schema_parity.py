"""align schema parity for revoked tokens and column definitions

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-11-09 13:45:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Revoked tokens table for token revocation store
    op.create_table(
        "revoked_tokens",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("token_jti", sa.String(length=100), nullable=False),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
    )
    op.create_index(op.f("ix_revoked_tokens_token_jti"), "revoked_tokens", ["token_jti"], unique=True)

    # 2. Add created_at and enforce non-null idempotency_key on payments
    with op.batch_alter_table("payments") as batch_op:
        batch_op.add_column(sa.Column("created_at", sa.DateTime(), nullable=True))
        batch_op.alter_column("idempotency_key", existing_type=sa.String(length=100), nullable=False)

    # 3. Align complaint ticket_number length, status length and non-null constraints
    with op.batch_alter_table("complaints") as batch_op:
        batch_op.alter_column(
            "ticket_number", existing_type=sa.String(length=20), type_=sa.String(length=30), nullable=False
        )
        batch_op.alter_column("status", existing_type=sa.String(length=20), type_=sa.String(length=30), nullable=False)
        batch_op.alter_column("tower_id", existing_type=sa.String(length=36), nullable=False)
        batch_op.alter_column("urgency", existing_type=sa.String(length=20), nullable=False)

    # 4. Relax optional columns on payment idempotency records
    with op.batch_alter_table("payment_idempotency_records") as batch_op:
        batch_op.alter_column("bill_id", existing_type=sa.String(length=36), nullable=True)
        batch_op.alter_column("amount", existing_type=sa.Numeric(precision=14, scale=2), nullable=True)
        batch_op.alter_column("currency", existing_type=sa.String(length=10), nullable=True)


def downgrade():
    with op.batch_alter_table("payment_idempotency_records") as batch_op:
        batch_op.alter_column("currency", existing_type=sa.String(length=10), nullable=False)
        batch_op.alter_column("amount", existing_type=sa.Numeric(precision=14, scale=2), nullable=False)
        batch_op.alter_column("bill_id", existing_type=sa.String(length=36), nullable=False)
    with op.batch_alter_table("complaints") as batch_op:
        batch_op.alter_column("urgency", existing_type=sa.String(length=20), nullable=True)
        batch_op.alter_column("tower_id", existing_type=sa.String(length=36), nullable=True)
        batch_op.alter_column("status", existing_type=sa.String(length=30), type_=sa.String(length=20), nullable=True)
        batch_op.alter_column(
            "ticket_number", existing_type=sa.String(length=30), type_=sa.String(length=20), nullable=False
        )

    with op.batch_alter_table("payments") as batch_op:
        batch_op.alter_column("idempotency_key", existing_type=sa.String(length=100), nullable=True)
        batch_op.drop_column("created_at")

    op.drop_index(op.f("ix_revoked_tokens_token_jti"), table_name="revoked_tokens")
    op.drop_table("revoked_tokens")
