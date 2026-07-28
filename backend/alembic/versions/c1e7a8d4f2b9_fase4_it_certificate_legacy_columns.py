"""fase4 it certificate legacy columns

Revision ID: c1e7a8d4f2b9
Revises: b9d1f6e2c4a7
Create Date: 2026-05-25
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c1e7a8d4f2b9"
down_revision: Union[str, None] = "b9d1f6e2c4a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    inspector = sa.inspect(bind)
    if not inspector.has_table("it_certificates"):
        return
    columns = {column["name"] for column in inspector.get_columns("it_certificates")}
    for column in ["alerts_enabled", "alerts_before_days"]:
        if column in columns:
            op.execute(sa.text(f"ALTER TABLE IF EXISTS it_certificates ALTER COLUMN {column} DROP NOT NULL"))


def downgrade() -> None:
    pass
