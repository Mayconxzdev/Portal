"""purchase_email_monitoring_pr4

Revision ID: e8f1a2b3c4d5
Revises: d4b7c9e2a531
Create Date: 2026-06-16 19:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "e8f1a2b3c4d5"
down_revision: Union[str, None] = "d4b7c9e2a531"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return inspector.has_table(table_name)


def upgrade() -> None:
    if (
        _table_exists("purchase_monitored_accounts")
        and _table_exists("purchase_email_inbound_messages")
        and _table_exists("purchase_email_attachments")
        and _table_exists("purchase_response_candidates")
        and _table_exists("purchase_monitoring_events")
    ):
        return

    op.create_table(
        "purchase_monitored_accounts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("sender_account_id", sa.String(length=80), nullable=True),
        sa.Column("account_email", sa.String(length=255), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("folder", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("imap_enabled", sa.Boolean(), nullable=False),
        sa.Column("secret_ref", sa.String(length=255), nullable=True),
        sa.Column("has_secret", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True),
        sa.Column("last_success_at", sa.DateTime(), nullable=True),
        sa.Column("last_error_at", sa.DateTime(), nullable=True),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["sender_account_id"], ["purchase_sender_accounts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_email", "folder", name="uq_purchase_monitored_account_folder"),
    )
    op.create_index(op.f("ix_purchase_monitored_accounts_account_email"), "purchase_monitored_accounts", ["account_email"], unique=False)
    op.create_index(op.f("ix_purchase_monitored_accounts_is_active"), "purchase_monitored_accounts", ["is_active"], unique=False)
    op.create_index(op.f("ix_purchase_monitored_accounts_sender_account_id"), "purchase_monitored_accounts", ["sender_account_id"], unique=False)
    op.create_index(op.f("ix_purchase_monitored_accounts_status"), "purchase_monitored_accounts", ["status"], unique=False)

    op.create_table(
        "purchase_email_inbound_messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("monitored_account_id", sa.UUID(), nullable=False),
        sa.Column("account_email", sa.String(length=255), nullable=False),
        sa.Column("folder", sa.String(length=255), nullable=False),
        sa.Column("imap_uid", sa.String(length=120), nullable=True),
        sa.Column("message_id", sa.String(length=255), nullable=True),
        sa.Column("in_reply_to", sa.String(length=255), nullable=True),
        sa.Column("references_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("from_email", sa.String(length=255), nullable=False),
        sa.Column("from_name", sa.String(length=255), nullable=True),
        sa.Column("to_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("cc_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("subject", sa.String(length=500), nullable=True),
        sa.Column("normalized_subject", sa.String(length=500), nullable=True),
        sa.Column("body_text", sa.Text(), nullable=True),
        sa.Column("body_html_sanitized", sa.Text(), nullable=True),
        sa.Column("raw_headers_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("received_at", sa.DateTime(), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("classification_status", sa.String(length=60), nullable=False),
        sa.Column("linked_quote_id", sa.UUID(), nullable=True),
        sa.Column("linked_supplier_id", sa.UUID(), nullable=True),
        sa.Column("confidence_score", sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column("confidence_level", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["linked_quote_id"], ["purchase_rfqs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["linked_supplier_id"], ["suppliers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["monitored_account_id"], ["purchase_monitored_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_email", "folder", "imap_uid", name="uq_purchase_inbound_messages_imap_uid"),
        sa.UniqueConstraint("idempotency_key", name="uq_purchase_inbound_messages_idempotency_key"),
    )
    op.create_index(op.f("ix_purchase_email_inbound_messages_account_email"), "purchase_email_inbound_messages", ["account_email"], unique=False)
    op.create_index(op.f("ix_purchase_email_inbound_messages_classification_status"), "purchase_email_inbound_messages", ["classification_status"], unique=False)
    op.create_index(op.f("ix_purchase_email_inbound_messages_created_at"), "purchase_email_inbound_messages", ["created_at"], unique=False)
    op.create_index(op.f("ix_purchase_email_inbound_messages_from_email"), "purchase_email_inbound_messages", ["from_email"], unique=False)
    op.create_index(op.f("ix_purchase_email_inbound_messages_in_reply_to"), "purchase_email_inbound_messages", ["in_reply_to"], unique=False)
    op.create_index(op.f("ix_purchase_email_inbound_messages_linked_quote_id"), "purchase_email_inbound_messages", ["linked_quote_id"], unique=False)
    op.create_index(op.f("ix_purchase_email_inbound_messages_linked_supplier_id"), "purchase_email_inbound_messages", ["linked_supplier_id"], unique=False)
    op.create_index(op.f("ix_purchase_email_inbound_messages_message_id"), "purchase_email_inbound_messages", ["message_id"], unique=False)
    op.create_index(op.f("ix_purchase_email_inbound_messages_monitored_account_id"), "purchase_email_inbound_messages", ["monitored_account_id"], unique=False)
    op.create_index(op.f("ix_purchase_email_inbound_messages_normalized_subject"), "purchase_email_inbound_messages", ["normalized_subject"], unique=False)
    op.create_index(op.f("ix_purchase_email_inbound_messages_received_at"), "purchase_email_inbound_messages", ["received_at"], unique=False)
    op.create_index(op.f("ix_purchase_email_inbound_messages_status"), "purchase_email_inbound_messages", ["status"], unique=False)

    op.create_table(
        "purchase_email_attachments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("inbound_message_id", sa.UUID(), nullable=False),
        sa.Column("filename", sa.String(length=500), nullable=True),
        sa.Column("safe_filename", sa.String(length=500), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=True),
        sa.Column("detected_content_type", sa.String(length=255), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=128), nullable=True),
        sa.Column("storage_key", sa.String(length=500), nullable=True),
        sa.Column("scan_status", sa.String(length=40), nullable=False),
        sa.Column("blocked_reason", sa.Text(), nullable=True),
        sa.Column("text_preview", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["inbound_message_id"], ["purchase_email_inbound_messages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_purchase_email_attachments_inbound_message_id"), "purchase_email_attachments", ["inbound_message_id"], unique=False)
    op.create_index(op.f("ix_purchase_email_attachments_scan_status"), "purchase_email_attachments", ["scan_status"], unique=False)
    op.create_index(op.f("ix_purchase_email_attachments_sha256"), "purchase_email_attachments", ["sha256"], unique=False)

    op.create_table(
        "purchase_response_candidates",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("inbound_message_id", sa.UUID(), nullable=False),
        sa.Column("quote_id", sa.UUID(), nullable=True),
        sa.Column("rfq_id", sa.UUID(), nullable=True),
        sa.Column("supplier_id", sa.UUID(), nullable=True),
        sa.Column("candidate_status", sa.String(length=50), nullable=False),
        sa.Column("confidence_score", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("confidence_level", sa.String(length=20), nullable=False),
        sa.Column("match_reasons_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("risk_flags_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("user_decision", sa.String(length=40), nullable=True),
        sa.Column("decided_by", sa.Integer(), nullable=True),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["decided_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["inbound_message_id"], ["purchase_email_inbound_messages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["quote_id"], ["purchase_rfqs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("inbound_message_id", "quote_id", "supplier_id", name="uq_purchase_response_candidate_match"),
    )
    op.create_index(op.f("ix_purchase_response_candidates_candidate_status"), "purchase_response_candidates", ["candidate_status"], unique=False)
    op.create_index(op.f("ix_purchase_response_candidates_confidence_level"), "purchase_response_candidates", ["confidence_level"], unique=False)
    op.create_index(op.f("ix_purchase_response_candidates_created_at"), "purchase_response_candidates", ["created_at"], unique=False)
    op.create_index(op.f("ix_purchase_response_candidates_inbound_message_id"), "purchase_response_candidates", ["inbound_message_id"], unique=False)
    op.create_index(op.f("ix_purchase_response_candidates_quote_id"), "purchase_response_candidates", ["quote_id"], unique=False)
    op.create_index(op.f("ix_purchase_response_candidates_rfq_id"), "purchase_response_candidates", ["rfq_id"], unique=False)
    op.create_index(op.f("ix_purchase_response_candidates_supplier_id"), "purchase_response_candidates", ["supplier_id"], unique=False)

    op.create_table(
        "purchase_monitoring_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("account_email", sa.String(length=255), nullable=True),
        sa.Column("source", sa.String(length=80), nullable=True),
        sa.Column("webhook_id", sa.String(length=160), nullable=False),
        sa.Column("payload_hash", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("inbound_message_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["inbound_message_id"], ["purchase_email_inbound_messages.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("webhook_id", name="uq_purchase_monitoring_events_webhook_id"),
    )
    op.create_index(op.f("ix_purchase_monitoring_events_account_email"), "purchase_monitoring_events", ["account_email"], unique=False)
    op.create_index(op.f("ix_purchase_monitoring_events_created_at"), "purchase_monitoring_events", ["created_at"], unique=False)
    op.create_index(op.f("ix_purchase_monitoring_events_event_type"), "purchase_monitoring_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_purchase_monitoring_events_inbound_message_id"), "purchase_monitoring_events", ["inbound_message_id"], unique=False)
    op.create_index(op.f("ix_purchase_monitoring_events_source"), "purchase_monitoring_events", ["source"], unique=False)
    op.create_index(op.f("ix_purchase_monitoring_events_status"), "purchase_monitoring_events", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_purchase_monitoring_events_status"), table_name="purchase_monitoring_events")
    op.drop_index(op.f("ix_purchase_monitoring_events_source"), table_name="purchase_monitoring_events")
    op.drop_index(op.f("ix_purchase_monitoring_events_inbound_message_id"), table_name="purchase_monitoring_events")
    op.drop_index(op.f("ix_purchase_monitoring_events_event_type"), table_name="purchase_monitoring_events")
    op.drop_index(op.f("ix_purchase_monitoring_events_created_at"), table_name="purchase_monitoring_events")
    op.drop_index(op.f("ix_purchase_monitoring_events_account_email"), table_name="purchase_monitoring_events")
    op.drop_table("purchase_monitoring_events")

    op.drop_index(op.f("ix_purchase_response_candidates_supplier_id"), table_name="purchase_response_candidates")
    op.drop_index(op.f("ix_purchase_response_candidates_rfq_id"), table_name="purchase_response_candidates")
    op.drop_index(op.f("ix_purchase_response_candidates_quote_id"), table_name="purchase_response_candidates")
    op.drop_index(op.f("ix_purchase_response_candidates_inbound_message_id"), table_name="purchase_response_candidates")
    op.drop_index(op.f("ix_purchase_response_candidates_created_at"), table_name="purchase_response_candidates")
    op.drop_index(op.f("ix_purchase_response_candidates_confidence_level"), table_name="purchase_response_candidates")
    op.drop_index(op.f("ix_purchase_response_candidates_candidate_status"), table_name="purchase_response_candidates")
    op.drop_table("purchase_response_candidates")

    op.drop_index(op.f("ix_purchase_email_attachments_sha256"), table_name="purchase_email_attachments")
    op.drop_index(op.f("ix_purchase_email_attachments_scan_status"), table_name="purchase_email_attachments")
    op.drop_index(op.f("ix_purchase_email_attachments_inbound_message_id"), table_name="purchase_email_attachments")
    op.drop_table("purchase_email_attachments")

    op.drop_index(op.f("ix_purchase_email_inbound_messages_status"), table_name="purchase_email_inbound_messages")
    op.drop_index(op.f("ix_purchase_email_inbound_messages_received_at"), table_name="purchase_email_inbound_messages")
    op.drop_index(op.f("ix_purchase_email_inbound_messages_normalized_subject"), table_name="purchase_email_inbound_messages")
    op.drop_index(op.f("ix_purchase_email_inbound_messages_monitored_account_id"), table_name="purchase_email_inbound_messages")
    op.drop_index(op.f("ix_purchase_email_inbound_messages_message_id"), table_name="purchase_email_inbound_messages")
    op.drop_index(op.f("ix_purchase_email_inbound_messages_linked_supplier_id"), table_name="purchase_email_inbound_messages")
    op.drop_index(op.f("ix_purchase_email_inbound_messages_linked_quote_id"), table_name="purchase_email_inbound_messages")
    op.drop_index(op.f("ix_purchase_email_inbound_messages_in_reply_to"), table_name="purchase_email_inbound_messages")
    op.drop_index(op.f("ix_purchase_email_inbound_messages_from_email"), table_name="purchase_email_inbound_messages")
    op.drop_index(op.f("ix_purchase_email_inbound_messages_created_at"), table_name="purchase_email_inbound_messages")
    op.drop_index(op.f("ix_purchase_email_inbound_messages_classification_status"), table_name="purchase_email_inbound_messages")
    op.drop_index(op.f("ix_purchase_email_inbound_messages_account_email"), table_name="purchase_email_inbound_messages")
    op.drop_table("purchase_email_inbound_messages")

    op.drop_index(op.f("ix_purchase_monitored_accounts_status"), table_name="purchase_monitored_accounts")
    op.drop_index(op.f("ix_purchase_monitored_accounts_sender_account_id"), table_name="purchase_monitored_accounts")
    op.drop_index(op.f("ix_purchase_monitored_accounts_is_active"), table_name="purchase_monitored_accounts")
    op.drop_index(op.f("ix_purchase_monitored_accounts_account_email"), table_name="purchase_monitored_accounts")
    op.drop_table("purchase_monitored_accounts")
