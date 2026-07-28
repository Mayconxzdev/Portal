"""add_user_lifecycle_fields

Revision ID: d9a7c3e5f1b2
Revises: 7c4a1d9e2f6b
Create Date: 2026-06-17 14:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d9a7c3e5f1b2"
down_revision: Union[str, None] = "7c4a1d9e2f6b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    if not _column_exists("users", "full_name"):
        op.add_column("users", sa.Column("full_name", sa.String(length=180), nullable=True))
    if not _column_exists("users", "department"):
        op.add_column("users", sa.Column("department", sa.String(length=120), nullable=True))
    if not _column_exists("users", "job_title"):
        op.add_column("users", sa.Column("job_title", sa.String(length=120), nullable=True))
    if not _column_exists("users", "must_change_password"):
        op.add_column("users", sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    if _column_exists("users", "must_change_password"):
        op.drop_column("users", "must_change_password")
    if _column_exists("users", "job_title"):
        op.drop_column("users", "job_title")
    if _column_exists("users", "department"):
        op.drop_column("users", "department")
    if _column_exists("users", "full_name"):
        op.drop_column("users", "full_name")
