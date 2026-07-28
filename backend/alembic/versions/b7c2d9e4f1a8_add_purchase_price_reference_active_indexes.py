"""add_purchase_price_reference_active_indexes

Revision ID: b7c2d9e4f1a8
Revises: a94aeda0364d
Create Date: 2026-06-03 17:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7c2d9e4f1a8"
down_revision: Union[str, None] = "a94aeda0364d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ux_purchase_price_ref_active_product_supplier",
        "purchase_price_references",
        ["product_item_id", "supplier_id"],
        unique=True,
        postgresql_where=sa.text("is_active = true AND supplier_id IS NOT NULL"),
    )
    op.create_index(
        "ux_purchase_price_ref_active_product_general",
        "purchase_price_references",
        ["product_item_id"],
        unique=True,
        postgresql_where=sa.text("is_active = true AND supplier_id IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ux_purchase_price_ref_active_product_general",
        table_name="purchase_price_references",
        postgresql_where=sa.text("is_active = true AND supplier_id IS NULL"),
    )
    op.drop_index(
        "ux_purchase_price_ref_active_product_supplier",
        table_name="purchase_price_references",
        postgresql_where=sa.text("is_active = true AND supplier_id IS NOT NULL"),
    )
