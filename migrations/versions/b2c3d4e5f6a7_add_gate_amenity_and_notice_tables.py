"""add gate amenity and notice tables

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-11-09 00:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Visitor Photos
    op.create_table(
        'visitor_photos',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('storage_key', sa.String(length=255), nullable=True),
        sa.Column('sha256', sa.String(length=64), nullable=False),
        sa.Column('capture_time', sa.DateTime(), nullable=False),
        sa.Column('content_type', sa.String(length=50), nullable=False, server_default='image/jpeg'),
        sa.Column('size', sa.Integer(), nullable=False),
        sa.Column('retention_expires_at', sa.DateTime(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    # 2. Pre-approvals (guest codes)
    op.create_table(
        'pre_approvals',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('flat_id', sa.String(length=36), sa.ForeignKey('flats.id'), nullable=False),
        sa.Column('created_by_user_id', sa.String(length=36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('guest_name', sa.String(length=100), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('purpose', sa.String(length=100), nullable=False),
        sa.Column('gate_id', sa.String(length=36), sa.ForeignKey('gates.id'), nullable=True),
        sa.Column('valid_from', sa.DateTime(), nullable=False),
        sa.Column('valid_until', sa.DateTime(), nullable=False),
        sa.Column('max_uses', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('used_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('code_hash', sa.String(length=128), nullable=False),
        sa.Column('credential_jwt', sa.Text(), nullable=True),
        sa.Column('is_revoked', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    # 3. Visitor Entries
    op.create_table(
        'visitor_entries',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('gate_id', sa.String(length=36), sa.ForeignKey('gates.id'), nullable=False),
        sa.Column('flat_id', sa.String(length=36), sa.ForeignKey('flats.id'), nullable=False),
        sa.Column('visitor_name', sa.String(length=100), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('purpose', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='AWAITING_APPROVAL'),
        sa.Column('created_by_guard', sa.String(length=36), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('approval_decided_by', sa.String(length=36), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('approval_decided_at', sa.DateTime(), nullable=True),
        sa.Column('admitted_at', sa.DateTime(), nullable=True),
        sa.Column('exited_at', sa.DateTime(), nullable=True),
        sa.Column('photo_id', sa.String(length=36), sa.ForeignKey('visitor_photos.id'), nullable=True),
        sa.Column('pre_approval_id', sa.String(length=36), sa.ForeignKey('pre_approvals.id'), nullable=True),
        sa.Column('source', sa.String(length=20), nullable=False, server_default='ONLINE'),
        sa.Column('client_event_id', sa.String(length=64), unique=True, nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # 4. Visitor Events
    op.create_table(
        'visitor_events',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('visitor_entry_id', sa.String(length=36), sa.ForeignKey('visitor_entries.id'), nullable=False),
        sa.Column('actor_user_id', sa.String(length=36), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('actor_role', sa.String(length=50), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('from_status', sa.String(length=30), nullable=True),
        sa.Column('to_status', sa.String(length=30), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    # 5. Supervisor Overrides
    op.create_table(
        'supervisor_overrides',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('visitor_entry_id', sa.String(length=36), sa.ForeignKey('visitor_entries.id'), nullable=False),
        sa.Column('actor_user_id', sa.String(length=36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('override_type', sa.String(length=50), nullable=False, server_default='OVERRIDDEN_ADMIT'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    # 6. Amenity Slots
    op.create_table(
        'amenity_slots',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('amenity_id', sa.String(length=36), sa.ForeignKey('amenities.id'), nullable=False),
        sa.Column('slot_date', sa.Date(), nullable=False),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.Column('capacity', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('booked_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
    )

    # 7. Amenity Rules
    op.create_table(
        'amenity_rules',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('amenity_id', sa.String(length=36), sa.ForeignKey('amenities.id'), nullable=False),
        sa.Column('booking_window_days', sa.Integer(), nullable=False, server_default='7'),
        sa.Column('max_daily_slots_per_flat', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('cancellation_cutoff_hours', sa.Integer(), nullable=False, server_default='2'),
    )

    # 8. Amenity Closures
    op.create_table(
        'amenity_closures',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('amenity_id', sa.String(length=36), sa.ForeignKey('amenities.id'), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('created_by_user_id', sa.String(length=36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    # 9. Amenity Bookings
    op.create_table(
        'amenity_bookings',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('flat_id', sa.String(length=36), sa.ForeignKey('flats.id'), nullable=False),
        sa.Column('slot_id', sa.String(length=36), sa.ForeignKey('amenity_slots.id'), nullable=False),
        sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='CONFIRMED'),
        sa.Column('fee', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0.00'),
        sa.Column('fee_status', sa.String(length=30), nullable=False, server_default='PAID_TEST'),
        sa.Column('idempotency_key', sa.String(length=64), unique=True, nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('cancelled_at', sa.DateTime(), nullable=True),
    )

    # 10. Notice Revisions
    op.create_table(
        'notice_revisions',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('notice_id', sa.String(length=36), sa.ForeignKey('notices.id'), nullable=False),
        sa.Column('revision_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('body_en', sa.Text(), nullable=False),
        sa.Column('body_hi', sa.Text(), nullable=True),
        sa.Column('body_mr', sa.Text(), nullable=True),
        sa.Column('publish_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('audience', sa.String(length=20), nullable=False, server_default='ALL'),
        sa.Column('tower_id', sa.String(length=36), sa.ForeignKey('towers.id'), nullable=True),
        sa.Column('severity', sa.String(length=20), nullable=False, server_default='NORMAL'),
        sa.Column('created_by_user_id', sa.String(length=36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    # 11. Notice Reads
    op.create_table(
        'notice_reads',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('notice_revision_id', sa.String(length=36), sa.ForeignKey('notice_revisions.id'), nullable=False),
        sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('read_at', sa.DateTime(), nullable=False),
    )

    # 12. Add columns to notices
    with op.batch_alter_table('notices') as batch_op:
        batch_op.add_column(sa.Column('status', sa.String(length=20), server_default='PUBLISHED', nullable=False))
        batch_op.add_column(sa.Column('current_revision_id', sa.String(length=36), nullable=True))


def downgrade():
    with op.batch_alter_table('notices') as batch_op:
        batch_op.drop_column('current_revision_id')
        batch_op.drop_column('status')

    op.drop_table('notice_reads')
    op.drop_table('notice_revisions')
    op.drop_table('amenity_bookings')
    op.drop_table('amenity_closures')
    op.drop_table('amenity_rules')
    op.drop_table('amenity_slots')
    op.drop_table('supervisor_overrides')
    op.drop_table('visitor_events')
    op.drop_table('visitor_entries')
    op.drop_table('pre_approvals')
    op.drop_table('visitor_photos')
