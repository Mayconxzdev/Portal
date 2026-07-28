"""fase3e_kanban_board_views

Revision ID: e4f7a2b1c9d0
Revises: d7e9a45f2c31
Create Date: 2026-05-22 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "e4f7a2b1c9d0"
down_revision: Union[str, None] = "d7e9a45f2c31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


json_type = sa.JSON().with_variant(postgresql.JSONB, "postgresql")


def upgrade() -> None:
    op.create_table(
        "kanban_board_views",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("board_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("view_type", sa.String(), nullable=False, server_default="BOARD"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("density", sa.String(), nullable=False, server_default="COMFORTABLE"),
        sa.Column("visible_columns", json_type, nullable=True),
        sa.Column("column_order", json_type, nullable=True),
        sa.Column("column_widths", json_type, nullable=True),
        sa.Column("filters", json_type, nullable=True),
        sa.Column("sort_by", sa.String(), nullable=True),
        sa.Column("group_by", sa.String(), nullable=True),
        sa.Column("color_rules", json_type, nullable=True),
        sa.Column("font_scale", sa.String(), nullable=True),
        sa.Column("auto_scroll", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("auto_scroll_seconds", sa.Integer(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["board_id"], ["kanban_boards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_kanban_board_views_id"), "kanban_board_views", ["id"], unique=False)
    op.create_index(op.f("ix_kanban_board_views_board_id"), "kanban_board_views", ["board_id"], unique=False)
    op.create_index("ix_kanban_board_views_board_default", "kanban_board_views", ["board_id", "is_default"], unique=False)
    op.create_index("ix_kanban_board_views_board_type", "kanban_board_views", ["board_id", "view_type"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_kanban_board_views_board_type", table_name="kanban_board_views")
    op.drop_index("ix_kanban_board_views_board_default", table_name="kanban_board_views")
    op.drop_index(op.f("ix_kanban_board_views_board_id"), table_name="kanban_board_views")
    op.drop_index(op.f("ix_kanban_board_views_id"), table_name="kanban_board_views")
    op.drop_table("kanban_board_views")
