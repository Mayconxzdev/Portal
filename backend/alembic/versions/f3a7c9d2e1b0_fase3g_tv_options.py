"""fase3g_tv_options

Revision ID: f3a7c9d2e1b0
Revises: e4f7a2b1c9d0
Create Date: 2026-05-25 09:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f3a7c9d2e1b0"
down_revision: Union[str, None] = "e4f7a2b1c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


json_type = sa.JSON().with_variant(postgresql.JSONB, "postgresql")


def upgrade() -> None:
    op.add_column("kanban_tv_views", sa.Column("display_options", json_type, nullable=True))
    op.add_column("kanban_tv_views", sa.Column("kpi_options", json_type, nullable=True))
    op.add_column("kanban_tv_views", sa.Column("layout_options", json_type, nullable=True))
    op.add_column("kanban_tv_views", sa.Column("external_mode_options", json_type, nullable=True))


def downgrade() -> None:
    op.drop_column("kanban_tv_views", "external_mode_options")
    op.drop_column("kanban_tv_views", "layout_options")
    op.drop_column("kanban_tv_views", "kpi_options")
    op.drop_column("kanban_tv_views", "display_options")
