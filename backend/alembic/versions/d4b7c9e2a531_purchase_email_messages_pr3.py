"""purchase_email_messages_pr3

Revision ID: d4b7c9e2a531
Revises: c6b2f4a9d8e1
Create Date: 2026-06-16 17:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d4b7c9e2a531"
down_revision: Union[str, None] = "c6b2f4a9d8e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return inspector.has_table(table_name)


def upgrade() -> None:
    if (
        _table_exists("purchase_sender_accounts")
        and _table_exists("purchase_sender_signatures")
        and _table_exists("purchase_email_messages")
    ):
        return

    op.create_table(
        "purchase_sender_accounts",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("company", sa.String(length=80), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("bcc_default_enabled", sa.Boolean(), nullable=False),
        sa.Column("default_bcc", sa.Text(), nullable=True),
        sa.Column("smtp_config_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("imap_config_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("secret_ref", sa.String(length=255), nullable=True),
        sa.Column("has_secret", sa.Boolean(), nullable=False),
        sa.Column("permissions_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("sent_folder", sa.String(length=255), nullable=True),
        sa.Column("monitored_folder", sa.String(length=255), nullable=True),
        sa.Column("last_test_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_purchase_sender_accounts_email"),
    )
    op.create_index(op.f("ix_purchase_sender_accounts_status"), "purchase_sender_accounts", ["status"], unique=False)

    op.create_table(
        "purchase_sender_signatures",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("account_id", sa.String(length=80), nullable=False),
        sa.Column("signature_name", sa.String(length=120), nullable=False),
        sa.Column("html_content", sa.Text(), nullable=False),
        sa.Column("text_content", sa.Text(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["purchase_sender_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_purchase_sender_signatures_account_id"), "purchase_sender_signatures", ["account_id"], unique=False)

    op.create_table(
        "purchase_email_messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("quote_id", sa.UUID(), nullable=False),
        sa.Column("rfq_id", sa.UUID(), nullable=False),
        sa.Column("rfq_supplier_id", sa.UUID(), nullable=True),
        sa.Column("supplier_id", sa.UUID(), nullable=False),
        sa.Column("supplier_contact_id", sa.UUID(), nullable=True),
        sa.Column("sender_account_id", sa.String(length=80), nullable=False),
        sa.Column("from_email", sa.String(length=255), nullable=False),
        sa.Column("from_name", sa.String(length=255), nullable=False),
        sa.Column("to_email", sa.String(length=255), nullable=True),
        sa.Column("cc", sa.Text(), nullable=True),
        sa.Column("bcc", sa.Text(), nullable=True),
        sa.Column("bcc_enabled", sa.Boolean(), nullable=False),
        sa.Column("bcc_source", sa.String(length=40), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("body_html", sa.Text(), nullable=False),
        sa.Column("body_text", sa.Text(), nullable=False),
        sa.Column("signature_html", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("environment", sa.String(length=40), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("message_id", sa.String(length=255), nullable=True),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("smtp_response", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("prepared_at", sa.DateTime(), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("failed_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["quote_id"], ["purchase_rfqs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rfq_supplier_id"], ["purchase_rfq_suppliers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sender_account_id"], ["purchase_sender_accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_purchase_email_messages_idempotency_key"),
    )
    op.create_index(op.f("ix_purchase_email_messages_created_at"), "purchase_email_messages", ["created_at"], unique=False)
    op.create_index(op.f("ix_purchase_email_messages_environment"), "purchase_email_messages", ["environment"], unique=False)
    op.create_index(op.f("ix_purchase_email_messages_quote_id"), "purchase_email_messages", ["quote_id"], unique=False)
    op.create_index(op.f("ix_purchase_email_messages_rfq_id"), "purchase_email_messages", ["rfq_id"], unique=False)
    op.create_index(op.f("ix_purchase_email_messages_rfq_supplier_id"), "purchase_email_messages", ["rfq_supplier_id"], unique=False)
    op.create_index(op.f("ix_purchase_email_messages_sender_account_id"), "purchase_email_messages", ["sender_account_id"], unique=False)
    op.create_index(op.f("ix_purchase_email_messages_status"), "purchase_email_messages", ["status"], unique=False)
    op.create_index(op.f("ix_purchase_email_messages_supplier_id"), "purchase_email_messages", ["supplier_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_purchase_email_messages_supplier_id"), table_name="purchase_email_messages")
    op.drop_index(op.f("ix_purchase_email_messages_status"), table_name="purchase_email_messages")
    op.drop_index(op.f("ix_purchase_email_messages_sender_account_id"), table_name="purchase_email_messages")
    op.drop_index(op.f("ix_purchase_email_messages_rfq_supplier_id"), table_name="purchase_email_messages")
    op.drop_index(op.f("ix_purchase_email_messages_rfq_id"), table_name="purchase_email_messages")
    op.drop_index(op.f("ix_purchase_email_messages_quote_id"), table_name="purchase_email_messages")
    op.drop_index(op.f("ix_purchase_email_messages_environment"), table_name="purchase_email_messages")
    op.drop_index(op.f("ix_purchase_email_messages_created_at"), table_name="purchase_email_messages")
    op.drop_table("purchase_email_messages")

    op.drop_index(op.f("ix_purchase_sender_signatures_account_id"), table_name="purchase_sender_signatures")
    op.drop_table("purchase_sender_signatures")

    op.drop_index(op.f("ix_purchase_sender_accounts_status"), table_name="purchase_sender_accounts")
    op.drop_table("purchase_sender_accounts")
