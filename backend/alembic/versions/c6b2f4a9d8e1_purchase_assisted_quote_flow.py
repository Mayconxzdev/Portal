"""purchase_assisted_quote_flow

Revision ID: c6b2f4a9d8e1
Revises: 84fb2c1d6e9a
Create Date: 2026-06-16 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c6b2f4a9d8e1"
down_revision: Union[str, None] = "84fb2c1d6e9a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {column["name"] for column in inspector.get_columns(table_name)}


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return inspector.has_table(table_name)


def _indexes(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {index["name"] for index in inspector.get_indexes(table_name)}


def _unique_constraints(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {constraint["name"] for constraint in inspector.get_unique_constraints(table_name)}


def _foreign_keys(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {constraint["name"] for constraint in inspector.get_foreign_keys(table_name)}


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if column.name not in _columns(table_name):
        op.add_column(table_name, column)


def _create_index_if_missing(index_name: str, table_name: str, columns: list[str]) -> None:
    if index_name not in _indexes(table_name):
        op.create_index(index_name, table_name, columns, unique=False)


def upgrade() -> None:
    _add_column_if_missing("purchase_requests", sa.Column("origin_type", sa.String(length=50), nullable=True))
    _add_column_if_missing("purchase_requests", sa.Column("origin_ref_id", sa.String(length=120), nullable=True))
    _add_column_if_missing("purchase_requests", sa.Column("origin_snapshot_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    _create_index_if_missing(op.f("ix_purchase_requests_origin_type"), "purchase_requests", ["origin_type"])
    _create_index_if_missing(op.f("ix_purchase_requests_origin_ref_id"), "purchase_requests", ["origin_ref_id"])

    _add_column_if_missing("purchase_items", sa.Column("stock_catalog_item_id", sa.UUID(), nullable=True))
    _add_column_if_missing("purchase_items", sa.Column("source_type", sa.String(length=50), nullable=True))
    _add_column_if_missing("purchase_items", sa.Column("source_ref_id", sa.String(length=120), nullable=True))
    _add_column_if_missing("purchase_items", sa.Column("source_confidence", sa.String(length=20), nullable=True))
    _add_column_if_missing("purchase_items", sa.Column("match_status", sa.String(length=40), nullable=False, server_default="confirmed"))
    _add_column_if_missing("purchase_items", sa.Column("source_snapshot_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    _create_index_if_missing(op.f("ix_purchase_items_stock_catalog_item_id"), "purchase_items", ["stock_catalog_item_id"])
    _create_index_if_missing(op.f("ix_purchase_items_source_type"), "purchase_items", ["source_type"])
    _create_index_if_missing(op.f("ix_purchase_items_source_ref_id"), "purchase_items", ["source_ref_id"])
    _create_index_if_missing(op.f("ix_purchase_items_match_status"), "purchase_items", ["match_status"])
    if op.f("fk_purchase_items_stock_catalog_item_id_stock_catalog_items") not in _foreign_keys("purchase_items"):
        op.create_foreign_key(
            op.f("fk_purchase_items_stock_catalog_item_id_stock_catalog_items"),
            "purchase_items",
            "stock_catalog_items",
            ["stock_catalog_item_id"],
            ["id"],
            ondelete="SET NULL",
        )

    if not _table_exists("purchase_rfq_supplier_items"):
        op.create_table(
            "purchase_rfq_supplier_items",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("rfq_supplier_id", sa.UUID(), nullable=False),
            sa.Column("purchase_item_id", sa.UUID(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["purchase_item_id"], ["purchase_items.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["rfq_supplier_id"], ["purchase_rfq_suppliers.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing(op.f("ix_purchase_rfq_supplier_items_rfq_supplier_id"), "purchase_rfq_supplier_items", ["rfq_supplier_id"])
    _create_index_if_missing(op.f("ix_purchase_rfq_supplier_items_purchase_item_id"), "purchase_rfq_supplier_items", ["purchase_item_id"])
    if "uq_purchase_rfq_supplier_item" not in _unique_constraints("purchase_rfq_supplier_items"):
        op.create_unique_constraint(
            "uq_purchase_rfq_supplier_item",
            "purchase_rfq_supplier_items",
            ["rfq_supplier_id", "purchase_item_id"],
        )


def downgrade() -> None:
    op.drop_constraint("uq_purchase_rfq_supplier_item", "purchase_rfq_supplier_items", type_="unique")
    op.drop_index(op.f("ix_purchase_rfq_supplier_items_purchase_item_id"), table_name="purchase_rfq_supplier_items")
    op.drop_index(op.f("ix_purchase_rfq_supplier_items_rfq_supplier_id"), table_name="purchase_rfq_supplier_items")
    op.drop_table("purchase_rfq_supplier_items")

    op.drop_constraint(op.f("fk_purchase_items_stock_catalog_item_id_stock_catalog_items"), "purchase_items", type_="foreignkey")
    op.drop_index(op.f("ix_purchase_items_match_status"), table_name="purchase_items")
    op.drop_index(op.f("ix_purchase_items_source_ref_id"), table_name="purchase_items")
    op.drop_index(op.f("ix_purchase_items_source_type"), table_name="purchase_items")
    op.drop_index(op.f("ix_purchase_items_stock_catalog_item_id"), table_name="purchase_items")
    op.drop_column("purchase_items", "source_snapshot_json")
    op.drop_column("purchase_items", "match_status")
    op.drop_column("purchase_items", "source_confidence")
    op.drop_column("purchase_items", "source_ref_id")
    op.drop_column("purchase_items", "source_type")
    op.drop_column("purchase_items", "stock_catalog_item_id")

    op.drop_index(op.f("ix_purchase_requests_origin_ref_id"), table_name="purchase_requests")
    op.drop_index(op.f("ix_purchase_requests_origin_type"), table_name="purchase_requests")
    op.drop_column("purchase_requests", "origin_snapshot_json")
    op.drop_column("purchase_requests", "origin_ref_id")
    op.drop_column("purchase_requests", "origin_type")
