"""fase4 it legacy columns

Revision ID: b9d1f6e2c4a7
Revises: a8c4f2d9e6b1
Create Date: 2026-05-25
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b9d1f6e2c4a7"
down_revision: Union[str, None] = "a8c4f2d9e6b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    inspector = sa.inspect(bind)

    def has_column(table_name: str, column_name: str) -> bool:
        if not inspector.has_table(table_name):
            return False
        return any(column["name"] == column_name for column in inspector.get_columns(table_name))

    legacy_columns = ["sla_limit_hours", "total_seconds_spent", "is_paused", "last_timer_action_at"]
    for column in legacy_columns:
        if has_column("it_tickets", column):
            op.execute(sa.text(f"ALTER TABLE IF EXISTS it_tickets ALTER COLUMN {column} DROP NOT NULL"))
    for column in ["alerts_enabled", "alerts_before_days"]:
        if has_column("it_certificates", column):
            op.execute(sa.text(f"ALTER TABLE IF EXISTS it_certificates ALTER COLUMN {column} DROP NOT NULL"))


def downgrade() -> None:
    pass
