"""approval_payloads_jsonb

Revision ID: 6b8d4d4b9f31
Revises: 2cc69e555951
Create Date: 2026-05-21 17:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "6b8d4d4b9f31"
down_revision: Union[str, None] = "2cc69e555951"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.alter_column(
            "approvals",
            "action_payload",
            existing_type=sa.JSON(),
            type_=postgresql.JSONB(astext_type=sa.Text()),
            postgresql_using="action_payload::jsonb",
            existing_nullable=False,
        )
        op.alter_column(
            "approvals",
            "result_payload",
            existing_type=sa.JSON(),
            type_=postgresql.JSONB(astext_type=sa.Text()),
            postgresql_using="result_payload::jsonb",
            existing_nullable=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.alter_column(
            "approvals",
            "result_payload",
            existing_type=postgresql.JSONB(astext_type=sa.Text()),
            type_=sa.JSON(),
            postgresql_using="result_payload::json",
            existing_nullable=True,
        )
        op.alter_column(
            "approvals",
            "action_payload",
            existing_type=postgresql.JSONB(astext_type=sa.Text()),
            type_=sa.JSON(),
            postgresql_using="action_payload::json",
            existing_nullable=False,
        )
