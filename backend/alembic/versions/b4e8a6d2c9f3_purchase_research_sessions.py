"""purchase research sessions

Revision ID: b4e8a6d2c9f3
Revises: a7d3e4c9b2f1
Create Date: 2026-06-22 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "b4e8a6d2c9f3"
down_revision = "a7d3e4c9b2f1"
branch_labels = None
depends_on = None


jsonb = postgresql.JSONB(astext_type=sa.Text())


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns(table_name)}
    if column.name not in existing:
        op.add_column(table_name, column)


def _create_index_if_missing(index_name: str, table_name: str, columns: list[str]) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return
    existing = {idx["name"] for idx in inspector.get_indexes(table_name)}
    if index_name not in existing:
        op.create_index(index_name, table_name, columns, unique=False)


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _create_fk_if_missing(
    constraint_name: str,
    source_table: str,
    referent_table: str,
    local_cols: list[str],
    remote_cols: list[str],
    *,
    ondelete: str | None = None,
) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if source_table not in inspector.get_table_names():
        return
    existing = {fk["name"] for fk in inspector.get_foreign_keys(source_table)}
    if constraint_name not in existing:
        op.create_foreign_key(
            constraint_name,
            source_table,
            referent_table,
            local_cols,
            remote_cols,
            ondelete=ondelete,
        )


def upgrade() -> None:
    if not _table_exists("purchase_search_sessions"):
        op.create_table(
            "purchase_search_sessions",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("purchase_request_id", sa.UUID(), nullable=False),
            sa.Column("purchase_item_id", sa.UUID(), nullable=False),
            sa.Column("query", sa.String(length=500), nullable=False),
            sa.Column("category", sa.String(length=80), nullable=False, server_default="general_external"),
            sa.Column("status", sa.String(length=40), nullable=False, server_default="queued"),
            sa.Column("progress_percent", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("current_step", sa.String(length=120), nullable=False, server_default="interpretando necessidade"),
            sa.Column("destination", sa.String(length=255), nullable=True),
            sa.Column("shipping_postal_code", sa.String(length=20), nullable=False, server_default="21043-030"),
            sa.Column("budget_limit", sa.Numeric(12, 2), nullable=True),
            sa.Column("planner_summary", jsonb, nullable=True),
            sa.Column("recommendation_summary", jsonb, nullable=True),
            sa.Column("missing_questions", jsonb, nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_by_user_id", sa.Integer(), nullable=False),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["purchase_item_id"], ["purchase_items.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["purchase_request_id"], ["purchase_requests.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing(op.f("ix_purchase_search_sessions_category"), "purchase_search_sessions", ["category"])
    _create_index_if_missing(op.f("ix_purchase_search_sessions_created_at"), "purchase_search_sessions", ["created_at"])
    _create_index_if_missing(op.f("ix_purchase_search_sessions_purchase_item_id"), "purchase_search_sessions", ["purchase_item_id"])
    _create_index_if_missing(op.f("ix_purchase_search_sessions_purchase_request_id"), "purchase_search_sessions", ["purchase_request_id"])
    _create_index_if_missing(op.f("ix_purchase_search_sessions_status"), "purchase_search_sessions", ["status"])

    if not _table_exists("purchase_research_tasks"):
        op.create_table(
            "purchase_research_tasks",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("search_session_id", sa.UUID(), nullable=False),
            sa.Column("task_type", sa.String(length=80), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("criteria", jsonb, nullable=True),
            sa.Column("status", sa.String(length=40), nullable=False, server_default="pending"),
            sa.Column("result_summary", jsonb, nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["search_session_id"], ["purchase_search_sessions.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing(op.f("ix_purchase_research_tasks_search_session_id"), "purchase_research_tasks", ["search_session_id"])
    _create_index_if_missing(op.f("ix_purchase_research_tasks_status"), "purchase_research_tasks", ["status"])
    _create_index_if_missing(op.f("ix_purchase_research_tasks_task_type"), "purchase_research_tasks", ["task_type"])

    if not _table_exists("purchase_search_sources"):
        op.create_table(
            "purchase_search_sources",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("search_session_id", sa.UUID(), nullable=False),
            sa.Column("source_type", sa.String(length=80), nullable=False),
            sa.Column("source_label", sa.String(length=255), nullable=False),
            sa.Column("url", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=40), nullable=False, server_default="pending"),
            sa.Column("duration_ms", sa.Integer(), nullable=True),
            sa.Column("result_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("evidence_summary", jsonb, nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["search_session_id"], ["purchase_search_sessions.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing(op.f("ix_purchase_search_sources_search_session_id"), "purchase_search_sources", ["search_session_id"])
    _create_index_if_missing(op.f("ix_purchase_search_sources_source_type"), "purchase_search_sources", ["source_type"])
    _create_index_if_missing(op.f("ix_purchase_search_sources_status"), "purchase_search_sources", ["status"])

    if not _table_exists("purchase_canonical_products"):
        op.create_table(
            "purchase_canonical_products",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("search_session_id", sa.UUID(), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("brand", sa.String(length=255), nullable=True),
            sa.Column("model", sa.String(length=255), nullable=True),
            sa.Column("normalized_key", sa.String(length=300), nullable=False),
            sa.Column("image_url", sa.Text(), nullable=True),
            sa.Column("compatibility_score", sa.Numeric(8, 4), nullable=True),
            sa.Column("recommendation_label", sa.String(length=80), nullable=True),
            sa.Column("risk_summary", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["search_session_id"], ["purchase_search_sessions.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing(op.f("ix_purchase_canonical_products_normalized_key"), "purchase_canonical_products", ["normalized_key"])
    _create_index_if_missing(op.f("ix_purchase_canonical_products_search_session_id"), "purchase_canonical_products", ["search_session_id"])

    _add_column_if_missing("purchase_item_options", sa.Column("search_session_id", sa.UUID(), nullable=True))
    _add_column_if_missing("purchase_item_options", sa.Column("canonical_product_id", sa.UUID(), nullable=True))
    _add_column_if_missing("purchase_item_options", sa.Column("source_domain", sa.String(length=255), nullable=True))
    _add_column_if_missing("purchase_item_options", sa.Column("source_rank", sa.Integer(), nullable=True))
    _add_column_if_missing("purchase_item_options", sa.Column("compatibility_score", sa.Numeric(8, 4), nullable=True))
    _add_column_if_missing("purchase_item_options", sa.Column("confidence_score", sa.Numeric(8, 4), nullable=True))
    _add_column_if_missing("purchase_item_options", sa.Column("evidence_level", sa.String(length=30), nullable=True))
    _add_column_if_missing("purchase_item_options", sa.Column("shipping_destination", sa.String(length=255), nullable=True))
    _add_column_if_missing("purchase_item_options", sa.Column("invoice_available", sa.Boolean(), nullable=True))
    _add_column_if_missing("purchase_item_options", sa.Column("payment_summary", sa.String(length=255), nullable=True))
    _add_column_if_missing("purchase_item_options", sa.Column("warranty_summary", sa.String(length=255), nullable=True))
    _add_column_if_missing("purchase_item_options", sa.Column("captured_method", sa.String(length=80), nullable=True))
    _add_column_if_missing("purchase_item_options", sa.Column("verification_status", sa.String(length=40), nullable=False, server_default="DISCOVERED"))
    _add_column_if_missing("purchase_item_options", sa.Column("verification_summary", sa.Text(), nullable=True))
    _create_index_if_missing(op.f("ix_purchase_item_options_search_session_id"), "purchase_item_options", ["search_session_id"])
    _create_index_if_missing(op.f("ix_purchase_item_options_canonical_product_id"), "purchase_item_options", ["canonical_product_id"])
    _create_index_if_missing(op.f("ix_purchase_item_options_source_domain"), "purchase_item_options", ["source_domain"])
    _create_index_if_missing(op.f("ix_purchase_item_options_verification_status"), "purchase_item_options", ["verification_status"])
    _create_fk_if_missing(
        "fk_purchase_item_options_search_session_id",
        "purchase_item_options",
        "purchase_search_sessions",
        ["search_session_id"],
        ["id"],
        ondelete="SET NULL",
    )
    _create_fk_if_missing(
        "fk_purchase_item_options_canonical_product_id",
        "purchase_item_options",
        "purchase_canonical_products",
        ["canonical_product_id"],
        ["id"],
        ondelete="SET NULL",
    )

    if not _table_exists("purchase_offer_field_evidence"):
        op.create_table(
            "purchase_offer_field_evidence",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("option_id", sa.UUID(), nullable=False),
            sa.Column("search_session_id", sa.UUID(), nullable=True),
            sa.Column("field_name", sa.String(length=80), nullable=False),
            sa.Column("field_status", sa.String(length=40), nullable=False, server_default="unavailable"),
            sa.Column("source_type", sa.String(length=80), nullable=False),
            sa.Column("method", sa.String(length=80), nullable=False),
            sa.Column("confidence", sa.Numeric(8, 4), nullable=True),
            sa.Column("source_url", sa.Text(), nullable=True),
            sa.Column("snapshot_hash", sa.String(length=128), nullable=True),
            sa.Column("captured_value", sa.Text(), nullable=True),
            sa.Column("captured_at", sa.DateTime(), nullable=True),
            sa.Column("last_verified_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["option_id"], ["purchase_item_options.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["search_session_id"], ["purchase_search_sessions.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    else:
        _add_column_if_missing("purchase_offer_field_evidence", sa.Column("search_session_id", sa.UUID(), nullable=True))
        _create_fk_if_missing(
            "fk_purchase_offer_field_evidence_search_session_id",
            "purchase_offer_field_evidence",
            "purchase_search_sessions",
            ["search_session_id"],
            ["id"],
            ondelete="CASCADE",
        )
    _create_index_if_missing(op.f("ix_purchase_offer_field_evidence_captured_at"), "purchase_offer_field_evidence", ["captured_at"])
    _create_index_if_missing(op.f("ix_purchase_offer_field_evidence_field_name"), "purchase_offer_field_evidence", ["field_name"])
    _create_index_if_missing(op.f("ix_purchase_offer_field_evidence_field_status"), "purchase_offer_field_evidence", ["field_status"])
    _create_index_if_missing(op.f("ix_purchase_offer_field_evidence_option_id"), "purchase_offer_field_evidence", ["option_id"])
    _create_index_if_missing(op.f("ix_purchase_offer_field_evidence_search_session_id"), "purchase_offer_field_evidence", ["search_session_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_purchase_offer_field_evidence_option_id"), table_name="purchase_offer_field_evidence")
    op.drop_index(op.f("ix_purchase_offer_field_evidence_search_session_id"), table_name="purchase_offer_field_evidence")
    op.drop_index(op.f("ix_purchase_offer_field_evidence_field_status"), table_name="purchase_offer_field_evidence")
    op.drop_index(op.f("ix_purchase_offer_field_evidence_field_name"), table_name="purchase_offer_field_evidence")
    op.drop_index(op.f("ix_purchase_offer_field_evidence_captured_at"), table_name="purchase_offer_field_evidence")
    op.drop_table("purchase_offer_field_evidence")

    op.drop_constraint("fk_purchase_item_options_canonical_product_id", "purchase_item_options", type_="foreignkey")
    op.drop_constraint("fk_purchase_item_options_search_session_id", "purchase_item_options", type_="foreignkey")
    for idx in [
        op.f("ix_purchase_item_options_verification_status"),
        op.f("ix_purchase_item_options_source_domain"),
        op.f("ix_purchase_item_options_canonical_product_id"),
        op.f("ix_purchase_item_options_search_session_id"),
    ]:
        op.drop_index(idx, table_name="purchase_item_options")
    for column in [
        "verification_summary",
        "verification_status",
        "captured_method",
        "warranty_summary",
        "payment_summary",
        "invoice_available",
        "shipping_destination",
        "evidence_level",
        "confidence_score",
        "compatibility_score",
        "source_rank",
        "source_domain",
        "canonical_product_id",
        "search_session_id",
    ]:
        op.drop_column("purchase_item_options", column)

    op.drop_index(op.f("ix_purchase_canonical_products_search_session_id"), table_name="purchase_canonical_products")
    op.drop_index(op.f("ix_purchase_canonical_products_normalized_key"), table_name="purchase_canonical_products")
    op.drop_table("purchase_canonical_products")

    op.drop_index(op.f("ix_purchase_search_sources_status"), table_name="purchase_search_sources")
    op.drop_index(op.f("ix_purchase_search_sources_source_type"), table_name="purchase_search_sources")
    op.drop_index(op.f("ix_purchase_search_sources_search_session_id"), table_name="purchase_search_sources")
    op.drop_table("purchase_search_sources")

    op.drop_index(op.f("ix_purchase_research_tasks_task_type"), table_name="purchase_research_tasks")
    op.drop_index(op.f("ix_purchase_research_tasks_status"), table_name="purchase_research_tasks")
    op.drop_index(op.f("ix_purchase_research_tasks_search_session_id"), table_name="purchase_research_tasks")
    op.drop_table("purchase_research_tasks")

    op.drop_index(op.f("ix_purchase_search_sessions_status"), table_name="purchase_search_sessions")
    op.drop_index(op.f("ix_purchase_search_sessions_purchase_request_id"), table_name="purchase_search_sessions")
    op.drop_index(op.f("ix_purchase_search_sessions_purchase_item_id"), table_name="purchase_search_sessions")
    op.drop_index(op.f("ix_purchase_search_sessions_created_at"), table_name="purchase_search_sessions")
    op.drop_index(op.f("ix_purchase_search_sessions_category"), table_name="purchase_search_sessions")
    op.drop_table("purchase_search_sessions")
