"""add_stock_measure_identity_fields

Revision ID: 7c4f2a1d9b6e
Revises: 1ef287413d98
Create Date: 2026-06-15 09:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "7c4f2a1d9b6e"
down_revision: Union[str, None] = "1ef287413d98"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("stock_catalog_items", sa.Column("canonical_measure_key", sa.String(length=160), nullable=True))
    op.add_column("stock_catalog_items", sa.Column("measure_display", sa.String(length=160), nullable=True))
    op.add_column("stock_catalog_items", sa.Column("measure_kind", sa.String(length=40), nullable=True))
    op.add_column(
        "stock_catalog_items",
        sa.Column("measure_aliases_json", sa.JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True),
    )
    op.add_column("stock_catalog_items", sa.Column("canonical_identity_key", sa.String(length=500), nullable=True))

    op.create_index(op.f("ix_stock_catalog_items_canonical_measure_key"), "stock_catalog_items", ["canonical_measure_key"], unique=False)
    op.create_index(op.f("ix_stock_catalog_items_measure_kind"), "stock_catalog_items", ["measure_kind"], unique=False)
    op.create_index(op.f("ix_stock_catalog_items_canonical_identity_key"), "stock_catalog_items", ["canonical_identity_key"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_stock_catalog_items_canonical_identity_key"), table_name="stock_catalog_items")
    op.drop_index(op.f("ix_stock_catalog_items_measure_kind"), table_name="stock_catalog_items")
    op.drop_index(op.f("ix_stock_catalog_items_canonical_measure_key"), table_name="stock_catalog_items")

    op.drop_column("stock_catalog_items", "canonical_identity_key")
    op.drop_column("stock_catalog_items", "measure_aliases_json")
    op.drop_column("stock_catalog_items", "measure_kind")
    op.drop_column("stock_catalog_items", "measure_display")
    op.drop_column("stock_catalog_items", "canonical_measure_key")

