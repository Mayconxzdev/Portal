"""add_quality_status_to_stock_items

Revision ID: af6363a1e021
Revises: 292e93855eb0
Create Date: 2026-06-11 16:33:57.855694

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'af6363a1e021'
down_revision: Union[str, None] = '292e93855eb0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("stock_catalog_items", sa.Column("quality_status", sa.String(length=50), nullable=False, server_default="READY"))
    op.create_index(op.f("ix_stock_catalog_items_quality_status"), "stock_catalog_items", ["quality_status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_stock_catalog_items_quality_status"), table_name="stock_catalog_items")
    op.drop_column("stock_catalog_items", "quality_status")
