"""make_user_email_optional

Revision ID: 7c4a1d9e2f6b
Revises: f2a6c8d9e0b1
Create Date: 2026-06-17 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7c4a1d9e2f6b"
down_revision: Union[str, None] = "f2a6c8d9e0b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_is_nullable(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for column in inspector.get_columns(table_name):
        if column["name"] == column_name:
            return bool(column.get("nullable"))
    return True


def upgrade() -> None:
    if not _column_is_nullable("users", "email"):
        op.alter_column("users", "email", existing_type=sa.String(), nullable=True)


def downgrade() -> None:
    op.alter_column("users", "email", existing_type=sa.String(), nullable=False)
