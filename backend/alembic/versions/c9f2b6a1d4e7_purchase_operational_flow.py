"""purchase operational flow

Revision ID: c9f2b6a1d4e7
Revises: b4e8a6d2c9f3
Create Date: 2026-06-22 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "c9f2b6a1d4e7"
down_revision = "b4e8a6d2c9f3"
branch_labels = None
depends_on = None


jsonb = postgresql.JSONB(astext_type=sa.Text())


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _create_index_if_missing(index_name: str, table_name: str, columns: list[str], *, unique: bool = False) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return
    existing = {idx["name"] for idx in inspector.get_indexes(table_name)}
    if index_name not in existing:
        op.create_index(index_name, table_name, columns, unique=unique)


def _drop_index_if_exists(index_name: str, table_name: str) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return
    existing = {idx["name"] for idx in inspector.get_indexes(table_name)}
    if index_name in existing:
        op.drop_index(index_name, table_name=table_name)


def _drop_table_if_exists(table_name: str) -> None:
    if _table_exists(table_name):
        op.drop_table(table_name)


def upgrade() -> None:
    if not _table_exists("purchase_request_idempotency_keys"):
        op.create_table(
            "purchase_request_idempotency_keys",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("idempotency_key", sa.String(length=128), nullable=False),
            sa.Column("purchase_request_id", sa.UUID(), nullable=True),
            sa.Column("payload_hash", sa.String(length=128), nullable=False),
            sa.Column("status", sa.String(length=40), nullable=False, server_default="started"),
            sa.Column("response_snapshot_json", jsonb, nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["purchase_request_id"], ["purchase_requests.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "idempotency_key", name="uq_purchase_request_idempotency_user_key"),
        )
    _create_index_if_missing("ix_purchase_request_idempotency_keys_user_id", "purchase_request_idempotency_keys", ["user_id"])
    _create_index_if_missing("ix_purchase_request_idempotency_keys_purchase_request_id", "purchase_request_idempotency_keys", ["purchase_request_id"])
    _create_index_if_missing("ix_purchase_request_idempotency_keys_status", "purchase_request_idempotency_keys", ["status"])
    _create_index_if_missing("ix_purchase_request_idempotency_keys_created_at", "purchase_request_idempotency_keys", ["created_at"])

    if not _table_exists("purchase_interpreted_drafts"):
        op.create_table(
            "purchase_interpreted_drafts",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("created_by_user_id", sa.Integer(), nullable=False),
            sa.Column("idempotency_key", sa.String(length=128), nullable=True),
            sa.Column("raw_input", sa.Text(), nullable=False),
            sa.Column("context", sa.String(length=80), nullable=True),
            sa.Column("status", sa.String(length=40), nullable=False, server_default="reviewing"),
            sa.Column("analysis_summary", jsonb, nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing("ix_purchase_interpreted_drafts_created_by_user_id", "purchase_interpreted_drafts", ["created_by_user_id"])
    _create_index_if_missing("ix_purchase_interpreted_drafts_idempotency_key", "purchase_interpreted_drafts", ["idempotency_key"])
    _create_index_if_missing("ix_purchase_interpreted_drafts_status", "purchase_interpreted_drafts", ["status"])
    _create_index_if_missing("ix_purchase_interpreted_drafts_created_at", "purchase_interpreted_drafts", ["created_at"])

    if not _table_exists("purchase_interpreted_draft_items"):
        op.create_table(
            "purchase_interpreted_draft_items",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("draft_id", sa.UUID(), nullable=False),
            sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("item_type", sa.String(length=30), nullable=False, server_default="external"),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("quantity", sa.Numeric(10, 2), nullable=False, server_default="1"),
            sa.Column("unit_of_measure", sa.String(length=30), nullable=False, server_default="un"),
            sa.Column("budget_limit", sa.Numeric(12, 2), nullable=True),
            sa.Column("destination", sa.Text(), nullable=True),
            sa.Column("department", sa.String(length=100), nullable=True),
            sa.Column("confidence_score", sa.Numeric(8, 4), nullable=True),
            sa.Column("classification_reason", sa.Text(), nullable=True),
            sa.Column("stock_catalog_item_id", sa.UUID(), nullable=True),
            sa.Column("missing_question_json", jsonb, nullable=True),
            sa.Column("metadata_json", jsonb, nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["draft_id"], ["purchase_interpreted_drafts.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["stock_catalog_item_id"], ["stock_catalog_items.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing("ix_purchase_interpreted_draft_items_draft_id", "purchase_interpreted_draft_items", ["draft_id"])
    _create_index_if_missing("ix_purchase_interpreted_draft_items_item_type", "purchase_interpreted_draft_items", ["item_type"])
    _create_index_if_missing("ix_purchase_interpreted_draft_items_stock_catalog_item_id", "purchase_interpreted_draft_items", ["stock_catalog_item_id"])

    if not _table_exists("purchase_research_jobs"):
        op.create_table(
            "purchase_research_jobs",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("search_session_id", sa.UUID(), nullable=False),
            sa.Column("queue_name", sa.String(length=80), nullable=False, server_default="purchases_research"),
            sa.Column("status", sa.String(length=40), nullable=False, server_default="queued"),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("locked_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["search_session_id"], ["purchase_search_sessions.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing("ix_purchase_research_jobs_search_session_id", "purchase_research_jobs", ["search_session_id"])
    _create_index_if_missing("ix_purchase_research_jobs_status", "purchase_research_jobs", ["status"])
    _create_index_if_missing("ix_purchase_research_jobs_created_at", "purchase_research_jobs", ["created_at"])

    if not _table_exists("purchase_offer_price_conditions"):
        op.create_table(
            "purchase_offer_price_conditions",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("option_id", sa.UUID(), nullable=False),
            sa.Column("condition_type", sa.String(length=40), nullable=False),
            sa.Column("amount", sa.Numeric(12, 2), nullable=False),
            sa.Column("currency", sa.String(length=8), nullable=False, server_default="BRL"),
            sa.Column("installments", sa.Integer(), nullable=True),
            sa.Column("installment_amount", sa.Numeric(12, 2), nullable=True),
            sa.Column("discount_percent", sa.Numeric(8, 4), nullable=True),
            sa.Column("is_recommended", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("source_label", sa.String(length=120), nullable=True),
            sa.Column("evidence_status", sa.String(length=40), nullable=False, server_default="estimated"),
            sa.Column("captured_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["option_id"], ["purchase_item_options.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing("ix_purchase_offer_price_conditions_option_id", "purchase_offer_price_conditions", ["option_id"])
    _create_index_if_missing("ix_purchase_offer_price_conditions_condition_type", "purchase_offer_price_conditions", ["condition_type"])
    _create_index_if_missing("ix_purchase_offer_price_conditions_captured_at", "purchase_offer_price_conditions", ["captured_at"])


def downgrade() -> None:
    _drop_index_if_exists("ix_purchase_offer_price_conditions_captured_at", "purchase_offer_price_conditions")
    _drop_index_if_exists("ix_purchase_offer_price_conditions_condition_type", "purchase_offer_price_conditions")
    _drop_index_if_exists("ix_purchase_offer_price_conditions_option_id", "purchase_offer_price_conditions")
    _drop_table_if_exists("purchase_offer_price_conditions")

    _drop_index_if_exists("ix_purchase_research_jobs_created_at", "purchase_research_jobs")
    _drop_index_if_exists("ix_purchase_research_jobs_status", "purchase_research_jobs")
    _drop_index_if_exists("ix_purchase_research_jobs_search_session_id", "purchase_research_jobs")
    _drop_table_if_exists("purchase_research_jobs")

    _drop_index_if_exists("ix_purchase_interpreted_draft_items_stock_catalog_item_id", "purchase_interpreted_draft_items")
    _drop_index_if_exists("ix_purchase_interpreted_draft_items_item_type", "purchase_interpreted_draft_items")
    _drop_index_if_exists("ix_purchase_interpreted_draft_items_draft_id", "purchase_interpreted_draft_items")
    _drop_table_if_exists("purchase_interpreted_draft_items")

    _drop_index_if_exists("ix_purchase_interpreted_drafts_created_at", "purchase_interpreted_drafts")
    _drop_index_if_exists("ix_purchase_interpreted_drafts_status", "purchase_interpreted_drafts")
    _drop_index_if_exists("ix_purchase_interpreted_drafts_idempotency_key", "purchase_interpreted_drafts")
    _drop_index_if_exists("ix_purchase_interpreted_drafts_created_by_user_id", "purchase_interpreted_drafts")
    _drop_table_if_exists("purchase_interpreted_drafts")

    _drop_index_if_exists("ix_purchase_request_idempotency_keys_created_at", "purchase_request_idempotency_keys")
    _drop_index_if_exists("ix_purchase_request_idempotency_keys_status", "purchase_request_idempotency_keys")
    _drop_index_if_exists("ix_purchase_request_idempotency_keys_purchase_request_id", "purchase_request_idempotency_keys")
    _drop_index_if_exists("ix_purchase_request_idempotency_keys_user_id", "purchase_request_idempotency_keys")
    _drop_table_if_exists("purchase_request_idempotency_keys")
