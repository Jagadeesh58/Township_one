"""bank matching and complaint system schema

Revision ID: f8a9b0c1d2e3
Revises: e7b8c9d0a1f2
Create Date: 2026-11-08 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f8a9b0c1d2e3"
down_revision: str | None = "e7b8c9d0a1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Bank Accounts
    op.create_table(
        "bank_accounts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("account_no", sa.String(length=50), nullable=False),
        sa.Column("bank_name", sa.String(length=100), nullable=False),
        sa.Column("ifsc_code", sa.String(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_bank_accounts_account_no"), "bank_accounts", ["account_no"], unique=True)

    # 2. Bank Import Files
    op.create_table(
        "bank_import_files",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("bank_account_id", sa.String(length=36), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_sha256", sa.String(length=64), nullable=False),
        sa.Column("uploaded_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(), nullable=True),
        sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("accepted_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("invalid_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["bank_account_id"], ["bank_accounts.id"]),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_bank_import_files_file_sha256"), "bank_import_files", ["file_sha256"], unique=False)

    # 3. Bank Rows
    op.create_table(
        "bank_rows",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("import_file_id", sa.String(length=36), nullable=False),
        sa.Column("bank_account_id", sa.String(length=36), nullable=False),
        sa.Column("original_row_number", sa.Integer(), nullable=False),
        sa.Column("raw_row", sa.JSON(), nullable=False),
        sa.Column("txn_date", sa.DateTime(), nullable=True),
        sa.Column("value_date", sa.DateTime(), nullable=True),
        sa.Column("narration", sa.Text(), nullable=True),
        sa.Column("direction", sa.String(length=10), nullable=True),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=10), server_default="INR", nullable=True),
        sa.Column("utr", sa.String(length=100), nullable=True),
        sa.Column("payer_upi", sa.String(length=100), nullable=True),
        sa.Column("flat_ref", sa.String(length=50), nullable=True),
        sa.Column("parse_status", sa.String(length=20), server_default="ACCEPTED", nullable=False),
        sa.Column("parse_errors", sa.JSON(), nullable=True),
        sa.Column("decision", sa.String(length=50), nullable=True),
        sa.Column("decision_reason", sa.String(length=100), nullable=True),
        sa.Column("next_action", sa.String(length=50), nullable=True),
        sa.Column("matched_flat_id", sa.String(length=36), nullable=True),
        sa.Column("matched_bill_id", sa.String(length=36), nullable=True),
        sa.Column("matched_payment_id", sa.String(length=36), nullable=True),
        sa.Column("review_status", sa.String(length=20), server_default="PENDING", nullable=False),
        sa.Column("reviewed_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("correction_reason", sa.Text(), nullable=True),
        sa.Column("audit_trail", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["bank_account_id"], ["bank_accounts.id"]),
        sa.ForeignKeyConstraint(["import_file_id"], ["bank_import_files.id"]),
        sa.ForeignKeyConstraint(["matched_bill_id"], ["bills.id"]),
        sa.ForeignKeyConstraint(["matched_flat_id"], ["flats.id"]),
        sa.ForeignKeyConstraint(["matched_payment_id"], ["payments.id"]),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("import_file_id", "original_row_number", name="uq_import_file_row"),
    )
    op.create_index(op.f("ix_bank_rows_flat_ref"), "bank_rows", ["flat_ref"], unique=False)
    op.create_index(op.f("ix_bank_rows_payer_upi"), "bank_rows", ["payer_upi"], unique=False)
    op.create_index(op.f("ix_bank_rows_utr"), "bank_rows", ["utr"], unique=False)

    # 4. Registered UPI IDs
    op.create_table(
        "registered_upi_ids",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("flat_id", sa.String(length=36), nullable=False),
        sa.Column("upi_id", sa.String(length=100), nullable=False),
        sa.Column("is_verified", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["flat_id"], ["flats.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_registered_upi_ids_upi_id"), "registered_upi_ids", ["upi_id"], unique=False)

    # 5. Audit Events
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("actor_user_id", sa.String(length=36), nullable=True),
        sa.Column("actor_role", sa.String(length=30), nullable=True),
        sa.Column("old_state", sa.JSON(), nullable=True),
        sa.Column("new_state", sa.JSON(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_events_entity_id"), "audit_events", ["entity_id"], unique=False)

    # 6. Staff Teams & Shifts
    op.create_table(
        "staff_teams",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "staff_shifts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("staff_id", sa.String(length=36), nullable=False),
        sa.Column("shift_name", sa.String(length=20), server_default="Morning", nullable=False),
        sa.Column("is_on_duty", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.ForeignKeyConstraint(["staff_id"], ["staff_members.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # 7. Incident Groups & Incident Group Members
    op.create_table(
        "incident_groups",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tower_id", sa.String(length=36), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("title", sa.String(length=150), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="ACTIVE", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["tower_id"], ["towers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "incident_group_members",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("incident_group_id", sa.String(length=36), nullable=False),
        sa.Column("complaint_id", sa.String(length=36), nullable=False),
        sa.Column("linked_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["complaint_id"], ["complaints.id"]),
        sa.ForeignKeyConstraint(["incident_group_id"], ["incident_groups.id"]),
        sa.ForeignKeyConstraint(["linked_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # 8. Update complaints table
    with op.batch_alter_table("complaints") as batch_op:
        batch_op.add_column(sa.Column("tower_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("language", sa.String(length=20), server_default="en", nullable=False))
        batch_op.add_column(sa.Column("version", sa.Integer(), server_default="1", nullable=False))
        batch_op.add_column(sa.Column("closed_at", sa.DateTime(), nullable=True))
        batch_op.add_column(
            sa.Column("reopen_requested", sa.Boolean(), server_default=sa.text("false"), nullable=False)
        )
        batch_op.add_column(sa.Column("reopen_reason", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("assigned_team", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("incident_group_id", sa.String(length=36), nullable=True))
        batch_op.create_foreign_key("fk_complaints_tower_id", "towers", ["tower_id"], ["id"])
        batch_op.create_foreign_key("fk_complaints_incident_group_id", "incident_groups", ["incident_group_id"], ["id"])

    # 9. Complaint Events
    op.create_table(
        "complaint_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("complaint_id", sa.String(length=36), nullable=False),
        sa.Column("actor_user_id", sa.String(length=36), nullable=True),
        sa.Column("actor_role", sa.String(length=30), nullable=True),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("from_status", sa.String(length=30), nullable=True),
        sa.Column("to_status", sa.String(length=30), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["complaint_id"], ["complaints.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # 10. Complaint Attachments
    op.create_table(
        "complaint_attachments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("complaint_id", sa.String(length=36), nullable=False),
        sa.Column("storage_key", sa.String(length=255), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=50), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("file_sha256", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["complaint_id"], ["complaints.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # 11. Classification Decisions
    op.create_table(
        "classification_decisions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("complaint_id", sa.String(length=36), nullable=False),
        sa.Column("actor_type", sa.String(length=20), nullable=False),
        sa.Column("actor_user_id", sa.String(length=36), nullable=True),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("urgency", sa.String(length=20), nullable=False),
        sa.Column("short_reason", sa.Text(), nullable=True),
        sa.Column("language", sa.String(length=20), server_default="en", nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("needs_human_review", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=True),
        sa.Column("model_version", sa.String(length=50), nullable=True),
        sa.Column("prompt_version", sa.String(length=50), nullable=True),
        sa.Column("fallback_used", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("expected_version", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["complaint_id"], ["complaints.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # 12. Safety Events & Actions
    op.create_table(
        "safety_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("complaint_id", sa.String(length=36), nullable=False),
        sa.Column("trigger_pattern", sa.String(length=100), nullable=False),
        sa.Column("matched_text", sa.Text(), nullable=False),
        sa.Column("language", sa.String(length=20), nullable=False),
        sa.Column("duty_manager_notified", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("notification_sent_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="ACTIVE", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["complaint_id"], ["complaints.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "safety_event_actions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("safety_event_id", sa.String(length=36), nullable=False),
        sa.Column("actor_user_id", sa.String(length=36), nullable=False),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["safety_event_id"], ["safety_events.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # 13. Notifications
    op.create_table(
        "notifications",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("channel", sa.String(length=20), server_default="IN_APP", nullable=False),
        sa.Column("notification_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=150), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("safety_event_actions")
    op.drop_table("safety_events")
    op.drop_table("classification_decisions")
    op.drop_table("complaint_attachments")
    op.drop_table("complaint_events")
    with op.batch_alter_table("complaints") as batch_op:
        batch_op.drop_constraint("fk_complaints_incident_group_id", type_="foreignkey")
        batch_op.drop_constraint("fk_complaints_tower_id", type_="foreignkey")
        batch_op.drop_column("incident_group_id")
        batch_op.drop_column("assigned_team")
        batch_op.drop_column("reopen_reason")
        batch_op.drop_column("reopen_requested")
        batch_op.drop_column("closed_at")
        batch_op.drop_column("version")
        batch_op.drop_column("language")
        batch_op.drop_column("tower_id")
    op.drop_table("incident_group_members")
    op.drop_table("incident_groups")
    op.drop_table("staff_shifts")
    op.drop_table("staff_teams")
    op.drop_table("audit_events")
    op.drop_table("registered_upi_ids")
    op.drop_table("bank_rows")
    op.drop_table("bank_import_files")
    op.drop_table("bank_accounts")
