"""drop_stock_search_text_btree_index

Revision ID: 84fb2c1d6e9a
Revises: 7c4f2a1d9b6e
Create Date: 2026-06-16 12:10:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "84fb2c1d6e9a"
down_revision: Union[str, None] = "7c4f2a1d9b6e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # normalized_search_text is an unbounded Text field. A btree index can fail
    # with realistic catalog aliases; the trigram GIN index is the useful one.
    op.execute("DROP INDEX IF EXISTS ix_stock_catalog_search_index_normalized_search_text")


def downgrade() -> None:
    op.create_index(
        "ix_stock_catalog_search_index_normalized_search_text",
        "stock_catalog_search_index",
        ["normalized_search_text"],
        unique=False,
    )
