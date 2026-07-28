"""add purchase item requires approval

Revision ID: a7d3e4c9b2f1
Revises: 59bfd27fcfa4
Create Date: 2026-06-19 18:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a7d3e4c9b2f1"
down_revision: Union[str, None] = "59bfd27fcfa4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("purchase_items")}

    if "requires_approval" not in columns:
        op.add_column(
            "purchase_items",
            sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
        op.alter_column("purchase_items", "requires_approval", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("purchase_items")}

    if "requires_approval" in columns:
        op.drop_column("purchase_items", "requires_approval")
