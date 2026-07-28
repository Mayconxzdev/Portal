"""add notification dedup key

Revision ID: f9b2d7c1a6e4
Revises: e4b8c7d6a5f1
Create Date: 2026-06-18 10:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f9b2d7c1a6e4"
down_revision: Union[str, None] = "e4b8c7d6a5f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = {column["name"] for column in inspector.get_columns("notifications")}
    if "dedup_key" not in columns:
        op.add_column("notifications", sa.Column("dedup_key", sa.String(), nullable=True))

    existing_indexes = {index["name"] for index in inspector.get_indexes("notifications")}
    if "ix_notifications_dedup_key" not in existing_indexes:
        op.create_index("ix_notifications_dedup_key", "notifications", ["dedup_key"], unique=False)
    if "uq_notifications_dedup_key_not_null" not in existing_indexes and bind.dialect.name == "postgresql":
        op.create_index(
            "uq_notifications_dedup_key_not_null",
            "notifications",
            ["dedup_key"],
            unique=True,
            postgresql_where=sa.text("dedup_key IS NOT NULL"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_indexes = {index["name"] for index in inspector.get_indexes("notifications")}

    if "uq_notifications_dedup_key_not_null" in existing_indexes:
        op.drop_index("uq_notifications_dedup_key_not_null", table_name="notifications")
    if "ix_notifications_dedup_key" in existing_indexes:
        op.drop_index("ix_notifications_dedup_key", table_name="notifications")

    columns = {column["name"] for column in inspector.get_columns("notifications")}
    if "dedup_key" in columns:
        op.drop_column("notifications", "dedup_key")
