"""fase3b_kanban_advanced

Revision ID: c2f7d9a1e4b0
Revises: b1f8c8f0f2c2
Create Date: 2026-05-22 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c2f7d9a1e4b0"
down_revision: Union[str, None] = "b1f8c8f0f2c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "kanban_card_checklists",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["card_id"], ["kanban_cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_kanban_card_checklists_id"), "kanban_card_checklists", ["id"], unique=False)
    op.create_index(op.f("ix_kanban_card_checklists_card_id"), "kanban_card_checklists", ["card_id"], unique=False)

    op.create_table(
        "kanban_card_checklist_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("checklist_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column("is_done", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("completed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["checklist_id"], ["kanban_card_checklists.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["completed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_kanban_card_checklist_items_id"), "kanban_card_checklist_items", ["id"], unique=False)
    op.create_index(op.f("ix_kanban_card_checklist_items_checklist_id"), "kanban_card_checklist_items", ["checklist_id"], unique=False)

    op.create_table(
        "kanban_card_comments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("comment", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("edited_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["card_id"], ["kanban_cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_kanban_card_comments_id"), "kanban_card_comments", ["id"], unique=False)
    op.create_index(op.f("ix_kanban_card_comments_card_id"), "kanban_card_comments", ["card_id"], unique=False)
    op.create_index(op.f("ix_kanban_card_comments_user_id"), "kanban_card_comments", ["user_id"], unique=False)

    op.create_table(
        "files",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(), nullable=False),
        sa.Column("stored_filename", sa.String(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("storage_provider", sa.String(), nullable=False),
        sa.Column("storage_bucket", sa.String(), nullable=False),
        sa.Column("storage_key", sa.String(), nullable=False),
        sa.Column("checksum_sha256", sa.String(), nullable=True),
        sa.Column("uploaded_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_files_id"), "files", ["id"], unique=False)

    op.create_table(
        "file_module_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("file_id", sa.Integer(), nullable=False),
        sa.Column("module_slug", sa.String(), nullable=False),
        sa.Column("entity_type", sa.String(), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["file_id"], ["files.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_file_module_links_id"), "file_module_links", ["id"], unique=False)
    op.create_index(op.f("ix_file_module_links_file_id"), "file_module_links", ["file_id"], unique=False)
    op.create_index("ix_file_module_links_entity", "file_module_links", ["module_slug", "entity_type", "entity_id"], unique=False)

    op.create_table(
        "kanban_card_attachments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("file_id", sa.Integer(), nullable=False),
        sa.Column("uploaded_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["card_id"], ["kanban_cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["file_id"], ["files.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_kanban_card_attachments_id"), "kanban_card_attachments", ["id"], unique=False)
    op.create_index(op.f("ix_kanban_card_attachments_card_id"), "kanban_card_attachments", ["card_id"], unique=False)
    op.create_index(op.f("ix_kanban_card_attachments_file_id"), "kanban_card_attachments", ["file_id"], unique=False)

    op.create_table(
        "kanban_labels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("board_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("color", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["board_id"], ["kanban_boards.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_kanban_labels_id"), "kanban_labels", ["id"], unique=False)
    op.create_index(op.f("ix_kanban_labels_board_id"), "kanban_labels", ["board_id"], unique=False)

    op.create_table(
        "kanban_card_labels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("label_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["card_id"], ["kanban_cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["label_id"], ["kanban_labels.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("card_id", "label_id", name="uq_kanban_card_label"),
    )
    op.create_index(op.f("ix_kanban_card_labels_id"), "kanban_card_labels", ["id"], unique=False)
    op.create_index(op.f("ix_kanban_card_labels_card_id"), "kanban_card_labels", ["card_id"], unique=False)
    op.create_index(op.f("ix_kanban_card_labels_label_id"), "kanban_card_labels", ["label_id"], unique=False)

    op.create_table(
        "kanban_card_assignees",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("assigned_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["card_id"], ["kanban_cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assigned_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("card_id", "user_id", name="uq_kanban_card_assignee"),
    )
    op.create_index(op.f("ix_kanban_card_assignees_id"), "kanban_card_assignees", ["id"], unique=False)
    op.create_index(op.f("ix_kanban_card_assignees_card_id"), "kanban_card_assignees", ["card_id"], unique=False)
    op.create_index(op.f("ix_kanban_card_assignees_user_id"), "kanban_card_assignees", ["user_id"], unique=False)


def downgrade() -> None:
    for index_name, table_name in [
        ("ix_kanban_card_assignees_user_id", "kanban_card_assignees"),
        ("ix_kanban_card_assignees_card_id", "kanban_card_assignees"),
        ("ix_kanban_card_assignees_id", "kanban_card_assignees"),
    ]:
        op.drop_index(index_name, table_name=table_name)
    op.drop_table("kanban_card_assignees")
    op.drop_index(op.f("ix_kanban_card_labels_label_id"), table_name="kanban_card_labels")
    op.drop_index(op.f("ix_kanban_card_labels_card_id"), table_name="kanban_card_labels")
    op.drop_index(op.f("ix_kanban_card_labels_id"), table_name="kanban_card_labels")
    op.drop_table("kanban_card_labels")
    op.drop_index(op.f("ix_kanban_labels_board_id"), table_name="kanban_labels")
    op.drop_index(op.f("ix_kanban_labels_id"), table_name="kanban_labels")
    op.drop_table("kanban_labels")
    op.drop_index(op.f("ix_kanban_card_attachments_file_id"), table_name="kanban_card_attachments")
    op.drop_index(op.f("ix_kanban_card_attachments_card_id"), table_name="kanban_card_attachments")
    op.drop_index(op.f("ix_kanban_card_attachments_id"), table_name="kanban_card_attachments")
    op.drop_table("kanban_card_attachments")
    op.drop_index("ix_file_module_links_entity", table_name="file_module_links")
    op.drop_index(op.f("ix_file_module_links_file_id"), table_name="file_module_links")
    op.drop_index(op.f("ix_file_module_links_id"), table_name="file_module_links")
    op.drop_table("file_module_links")
    op.drop_index(op.f("ix_files_id"), table_name="files")
    op.drop_table("files")
    op.drop_index(op.f("ix_kanban_card_comments_user_id"), table_name="kanban_card_comments")
    op.drop_index(op.f("ix_kanban_card_comments_card_id"), table_name="kanban_card_comments")
    op.drop_index(op.f("ix_kanban_card_comments_id"), table_name="kanban_card_comments")
    op.drop_table("kanban_card_comments")
    op.drop_index(op.f("ix_kanban_card_checklist_items_checklist_id"), table_name="kanban_card_checklist_items")
    op.drop_index(op.f("ix_kanban_card_checklist_items_id"), table_name="kanban_card_checklist_items")
    op.drop_table("kanban_card_checklist_items")
    op.drop_index(op.f("ix_kanban_card_checklists_card_id"), table_name="kanban_card_checklists")
    op.drop_index(op.f("ix_kanban_card_checklists_id"), table_name="kanban_card_checklists")
    op.drop_table("kanban_card_checklists")
