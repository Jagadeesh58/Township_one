"""add ip_address to otp_challenges

Revision ID: e7b8c9d0a1f2
Revises: c0c7c862d0b3
Create Date: 2026-11-07 21:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7b8c9d0a1f2'
down_revision: Union[str, None] = 'c0c7c862d0b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('otp_challenges', sa.Column('ip_address', sa.String(length=45), nullable=True))
    op.create_index(op.f('ix_otp_challenges_ip_address'), 'otp_challenges', ['ip_address'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_otp_challenges_ip_address'), table_name='otp_challenges')
    op.drop_column('otp_challenges', 'ip_address')
