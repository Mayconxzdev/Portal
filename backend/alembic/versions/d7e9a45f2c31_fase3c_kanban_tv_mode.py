"""fase3c_kanban_tv_mode

Revision ID: d7e9a45f2c31
Revises: c2f7d9a1e4b0
Create Date: 2026-05-22 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d7e9a45f2c31"
down_revision: Union[str, None] = "c2f7d9a1e4b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


json_type = sa.JSON().with_variant(postgresql.JSONB, "postgresql")


def upgrade() -> None:
    op.create_table(
        "kanban_tv_views",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("board_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False, server_default="Padrao"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("layout_type", sa.String(), nullable=False, server_default="COLUMNS"),
        sa.Column("refresh_interval_seconds", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("show_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("show_done_columns", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("show_checklist_progress", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("show_assignees", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("show_labels", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("show_due_date", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("show_card_description", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("group_by", sa.String(), nullable=True),
        sa.Column("sort_by", sa.String(), nullable=True),
        sa.Column("filters", json_type, nullable=True),
        sa.Column("visible_custom_fields", json_type, nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["board_id"], ["kanban_boards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_kanban_tv_views_id"), "kanban_tv_views", ["id"], unique=False)
    op.create_index(op.f("ix_kanban_tv_views_board_id"), "kanban_tv_views", ["board_id"], unique=False)
    op.create_index("ix_kanban_tv_views_board_default", "kanban_tv_views", ["board_id", "is_default"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_kanban_tv_views_board_default", table_name="kanban_tv_views")
    op.drop_index(op.f("ix_kanban_tv_views_board_id"), table_name="kanban_tv_views")
    op.drop_index(op.f("ix_kanban_tv_views_id"), table_name="kanban_tv_views")
    op.drop_table("kanban_tv_views")
