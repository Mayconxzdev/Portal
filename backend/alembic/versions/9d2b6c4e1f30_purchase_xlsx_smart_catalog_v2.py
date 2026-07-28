"""purchase xlsx smart catalog v2

Revision ID: 9d2b6c4e1f30
Revises: f6c7c8d4f2b9
Create Date: 2026-06-09 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "9d2b6c4e1f30"
down_revision: Union[str, None] = "f6c7c8d4f2b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = "e2b7c8d4f2c0"


def upgrade() -> None:
    op.create_table(
        "purchase_xlsx_import_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_path", sa.String(length=1000), nullable=False),
        sa.Column("file_modified_at", sa.DateTime(), nullable=True),
        sa.Column("file_hash", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("metrics", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_purchase_xlsx_import_runs_started_at", "purchase_xlsx_import_runs", ["started_at"])
    op.create_index("ix_purchase_xlsx_import_runs_status", "purchase_xlsx_import_runs", ["status"])

    op.create_table(
        "purchase_xlsx_catalog_rows",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("import_run_id", sa.UUID(), nullable=False),
        sa.Column("row_key", sa.String(length=300), nullable=False),
        sa.Column("sheet", sa.String(length=255), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("parser_type", sa.String(length=80), nullable=False),
        sa.Column("category", sa.String(length=255), nullable=False),
        sa.Column("family", sa.String(length=255), nullable=False),
        sa.Column("subfamily", sa.String(length=255), nullable=True),
        sa.Column("group_name", sa.String(length=255), nullable=True),
        sa.Column("variation", sa.String(length=500), nullable=False),
        sa.Column("display_name", sa.String(length=500), nullable=False),
        sa.Column("original_description", sa.Text(), nullable=True),
        sa.Column("code", sa.String(length=120), nullable=True),
        sa.Column("manufacturer", sa.String(length=255), nullable=True),
        sa.Column("manufacturer_code", sa.String(length=255), nullable=True),
        sa.Column("product_item_id", sa.UUID(), nullable=True),
        sa.Column("current_supplier_id", sa.UUID(), nullable=True),
        sa.Column("current_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("raw_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("final_value", sa.Numeric(12, 2), nullable=True),
        sa.Column("price_type", sa.String(length=50), nullable=False),
        sa.Column("unit", sa.String(length=30), nullable=False),
        sa.Column("source_updated_at", sa.String(length=120), nullable=True),
        sa.Column("situation", sa.String(length=80), nullable=False),
        sa.Column("issues", sa.JSON(), nullable=True),
        sa.Column("attributes", sa.JSON(), nullable=True),
        sa.Column("technical_details", sa.JSON(), nullable=True),
        sa.Column("search_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["current_supplier_id"], ["suppliers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["import_run_id"], ["purchase_xlsx_import_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_item_id"], ["product_items.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("row_key"),
    )
    for column in (
        "category",
        "code",
        "current_supplier_id",
        "family",
        "import_run_id",
        "manufacturer_code",
        "parser_type",
        "product_item_id",
        "row_key",
        "sheet",
        "situation",
        "variation",
    ):
        op.create_index(f"ix_purchase_xlsx_catalog_rows_{column}", "purchase_xlsx_catalog_rows", [column])
    op.create_index("ix_purchase_xlsx_catalog_rows_created_at", "purchase_xlsx_catalog_rows", ["created_at"])

    op.create_table(
        "purchase_supplier_price_offers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("catalog_row_id", sa.UUID(), nullable=True),
        sa.Column("product_item_id", sa.UUID(), nullable=False),
        sa.Column("supplier_id", sa.UUID(), nullable=True),
        sa.Column("supplier_name_snapshot", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("raw_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("ipi", sa.Numeric(12, 2), nullable=True),
        sa.Column("adjustment", sa.Numeric(12, 2), nullable=True),
        sa.Column("final_value", sa.Numeric(12, 2), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("unit", sa.String(length=30), nullable=False),
        sa.Column("observed_at", sa.String(length=120), nullable=True),
        sa.Column("source_row_key", sa.String(length=300), nullable=True),
        sa.Column("is_current_supplier", sa.Boolean(), nullable=False),
        sa.Column("is_consolidated", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["catalog_row_id"], ["purchase_xlsx_catalog_rows.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["product_item_id"], ["product_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "catalog_row_id",
        "is_consolidated",
        "is_current_supplier",
        "product_item_id",
        "source_row_key",
        "status",
        "supplier_id",
        "supplier_name_snapshot",
    ):
        op.create_index(f"ix_purchase_supplier_price_offers_{column}", "purchase_supplier_price_offers", [column])
    op.create_index("ix_purchase_supplier_price_offers_created_at", "purchase_supplier_price_offers", ["created_at"])

    op.create_table(
        "purchase_catalog_search_index",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("product_item_id", sa.UUID(), nullable=True),
        sa.Column("family_id", sa.UUID(), nullable=True),
        sa.Column("catalog_row_id", sa.UUID(), nullable=True),
        sa.Column("category", sa.String(length=255), nullable=True),
        sa.Column("family", sa.String(length=255), nullable=True),
        sa.Column("variation", sa.String(length=500), nullable=True),
        sa.Column("supplier_names", sa.JSON(), nullable=True),
        sa.Column("search_text", sa.Text(), nullable=False),
        sa.Column("normalized_search_text", sa.Text(), nullable=False),
        sa.Column("rank_hint", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["catalog_row_id"], ["purchase_xlsx_catalog_rows.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["family_id"], ["product_families.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_item_id"], ["product_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("catalog_row_id", "category", "family", "family_id", "product_item_id", "rank_hint"):
        op.create_index(f"ix_purchase_catalog_search_index_{column}", "purchase_catalog_search_index", [column])


def downgrade() -> None:
    op.drop_table("purchase_catalog_search_index")
    op.drop_table("purchase_supplier_price_offers")
    op.drop_table("purchase_xlsx_catalog_rows")
    op.drop_table("purchase_xlsx_import_runs")
