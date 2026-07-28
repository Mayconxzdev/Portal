"""fase3a_kanban_core

Revision ID: b1f8c8f0f2c2
Revises: 6b8d4d4b9f31
Create Date: 2026-05-21 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b1f8c8f0f2c2"
down_revision: Union[str, None] = "6b8d4d4b9f31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


jsonb_type = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "kanban_boards",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("module_origin", sa.String(), nullable=True),
        sa.Column("color", sa.String(), nullable=True),
        sa.Column("icon", sa.String(), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_kanban_boards_id"), "kanban_boards", ["id"], unique=False)
    op.create_index(op.f("ix_kanban_boards_slug"), "kanban_boards", ["slug"], unique=True)
    op.create_index(op.f("ix_kanban_boards_created_by_user_id"), "kanban_boards", ["created_by_user_id"], unique=False)

    op.create_table(
        "kanban_board_permissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("board_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("role_id", sa.Integer(), nullable=True),
        sa.Column("access_level", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["board_id"], ["kanban_boards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_kanban_board_permissions_id"), "kanban_board_permissions", ["id"], unique=False)
    op.create_index(op.f("ix_kanban_board_permissions_board_id"), "kanban_board_permissions", ["board_id"], unique=False)
    op.create_index(op.f("ix_kanban_board_permissions_user_id"), "kanban_board_permissions", ["user_id"], unique=False)
    op.create_index(op.f("ix_kanban_board_permissions_role_id"), "kanban_board_permissions", ["role_id"], unique=False)

    op.create_table(
        "kanban_columns",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("board_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("color", sa.String(), nullable=True),
        sa.Column("wip_limit", sa.Integer(), nullable=True),
        sa.Column("is_done_column", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["board_id"], ["kanban_boards.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_kanban_columns_id"), "kanban_columns", ["id"], unique=False)
    op.create_index(op.f("ix_kanban_columns_board_id"), "kanban_columns", ["board_id"], unique=False)
    op.create_index("ix_kanban_columns_board_position", "kanban_columns", ["board_id", "position"], unique=False)

    op.create_table(
        "kanban_cards",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("board_id", sa.Integer(), nullable=False),
        sa.Column("column_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("priority", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("due_date", sa.DateTime(), nullable=True),
        sa.Column("assigned_to_user_id", sa.Integer(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("custom_fields", jsonb_type, nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["assigned_to_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["board_id"], ["kanban_boards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["column_id"], ["kanban_columns.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_kanban_cards_id"), "kanban_cards", ["id"], unique=False)
    op.create_index(op.f("ix_kanban_cards_board_id"), "kanban_cards", ["board_id"], unique=False)
    op.create_index(op.f("ix_kanban_cards_column_id"), "kanban_cards", ["column_id"], unique=False)
    op.create_index(op.f("ix_kanban_cards_assigned_to_user_id"), "kanban_cards", ["assigned_to_user_id"], unique=False)
    op.create_index(op.f("ix_kanban_cards_due_date"), "kanban_cards", ["due_date"], unique=False)
    op.create_index(op.f("ix_kanban_cards_priority"), "kanban_cards", ["priority"], unique=False)
    op.create_index("ix_kanban_cards_custom_fields_gin", "kanban_cards", ["custom_fields"], unique=False, postgresql_using="gin")

    op.create_table(
        "kanban_custom_fields",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("board_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("field_type", sa.String(), nullable=False),
        sa.Column("options", jsonb_type, nullable=True),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["board_id"], ["kanban_boards.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("board_id", "key", name="uq_kanban_custom_field_board_key"),
    )
    op.create_index(op.f("ix_kanban_custom_fields_id"), "kanban_custom_fields", ["id"], unique=False)
    op.create_index(op.f("ix_kanban_custom_fields_board_id"), "kanban_custom_fields", ["board_id"], unique=False)

    op.create_table(
        "kanban_activity",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("board_id", sa.Integer(), nullable=False),
        sa.Column("card_id", sa.Integer(), nullable=True),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("metadata", jsonb_type, nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["board_id"], ["kanban_boards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["card_id"], ["kanban_cards.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_kanban_activity_id"), "kanban_activity", ["id"], unique=False)
    op.create_index(op.f("ix_kanban_activity_board_id"), "kanban_activity", ["board_id"], unique=False)
    op.create_index(op.f("ix_kanban_activity_card_id"), "kanban_activity", ["card_id"], unique=False)
    op.create_index(op.f("ix_kanban_activity_actor_user_id"), "kanban_activity", ["actor_user_id"], unique=False)
    op.create_index(op.f("ix_kanban_activity_created_at"), "kanban_activity", ["created_at"], unique=False)
    op.create_index("ix_kanban_activity_board_created_at", "kanban_activity", ["board_id", "created_at"], unique=False)
    op.create_index("ix_kanban_activity_card_created_at", "kanban_activity", ["card_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_kanban_activity_card_created_at", table_name="kanban_activity")
    op.drop_index("ix_kanban_activity_board_created_at", table_name="kanban_activity")
    op.drop_index(op.f("ix_kanban_activity_created_at"), table_name="kanban_activity")
    op.drop_index(op.f("ix_kanban_activity_actor_user_id"), table_name="kanban_activity")
    op.drop_index(op.f("ix_kanban_activity_card_id"), table_name="kanban_activity")
    op.drop_index(op.f("ix_kanban_activity_board_id"), table_name="kanban_activity")
    op.drop_index(op.f("ix_kanban_activity_id"), table_name="kanban_activity")
    op.drop_table("kanban_activity")
    op.drop_index(op.f("ix_kanban_custom_fields_board_id"), table_name="kanban_custom_fields")
    op.drop_index(op.f("ix_kanban_custom_fields_id"), table_name="kanban_custom_fields")
    op.drop_table("kanban_custom_fields")
    op.drop_index("ix_kanban_cards_custom_fields_gin", table_name="kanban_cards")
    op.drop_index(op.f("ix_kanban_cards_priority"), table_name="kanban_cards")
    op.drop_index(op.f("ix_kanban_cards_due_date"), table_name="kanban_cards")
    op.drop_index(op.f("ix_kanban_cards_assigned_to_user_id"), table_name="kanban_cards")
    op.drop_index(op.f("ix_kanban_cards_column_id"), table_name="kanban_cards")
    op.drop_index(op.f("ix_kanban_cards_board_id"), table_name="kanban_cards")
    op.drop_index(op.f("ix_kanban_cards_id"), table_name="kanban_cards")
    op.drop_table("kanban_cards")
    op.drop_index("ix_kanban_columns_board_position", table_name="kanban_columns")
    op.drop_index(op.f("ix_kanban_columns_board_id"), table_name="kanban_columns")
    op.drop_index(op.f("ix_kanban_columns_id"), table_name="kanban_columns")
    op.drop_table("kanban_columns")
    op.drop_index(op.f("ix_kanban_board_permissions_role_id"), table_name="kanban_board_permissions")
    op.drop_index(op.f("ix_kanban_board_permissions_user_id"), table_name="kanban_board_permissions")
    op.drop_index(op.f("ix_kanban_board_permissions_board_id"), table_name="kanban_board_permissions")
    op.drop_index(op.f("ix_kanban_board_permissions_id"), table_name="kanban_board_permissions")
    op.drop_table("kanban_board_permissions")
    op.drop_index(op.f("ix_kanban_boards_created_by_user_id"), table_name="kanban_boards")
    op.drop_index(op.f("ix_kanban_boards_slug"), table_name="kanban_boards")
    op.drop_index(op.f("ix_kanban_boards_id"), table_name="kanban_boards")
    op.drop_table("kanban_boards")
