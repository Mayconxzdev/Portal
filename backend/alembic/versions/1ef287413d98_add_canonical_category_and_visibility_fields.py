"""add_canonical_category_and_visibility_fields

Revision ID: 1ef287413d98
Revises: af6363a1e021
Create Date: 2026-06-11 17:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '1ef287413d98'
down_revision: Union[str, None] = 'af6363a1e021'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Alterar stock_catalog_items
    op.add_column("stock_catalog_items", sa.Column("canonical_category", sa.String(length=100), nullable=True))
    op.add_column("stock_catalog_items", sa.Column("canonical_category_display", sa.String(length=255), nullable=True))
    op.add_column("stock_catalog_items", sa.Column("visibility_scope", sa.String(length=50), nullable=False, server_default="COMMON"))
    op.add_column("stock_catalog_items", sa.Column("review_type", sa.String(length=50), nullable=False, server_default="none"))
    op.add_column("stock_catalog_items", sa.Column("is_operational", sa.Boolean(), nullable=False, server_default="true"))
    op.add_column("stock_catalog_items", sa.Column("is_searchable_common", sa.Boolean(), nullable=False, server_default="true"))
    op.add_column("stock_catalog_items", sa.Column("is_tree_visible_common", sa.Boolean(), nullable=False, server_default="true"))
    op.add_column("stock_catalog_items", sa.Column("is_offer_active", sa.Boolean(), nullable=False, server_default="true"))
    op.add_column("stock_catalog_items", sa.Column("is_category_only", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("stock_catalog_items", sa.Column("is_parser_junk", sa.Boolean(), nullable=False, server_default="false"))

    op.create_index(op.f("ix_stock_catalog_items_canonical_category"), "stock_catalog_items", ["canonical_category"], unique=False)
    op.create_index(op.f("ix_stock_catalog_items_visibility_scope"), "stock_catalog_items", ["visibility_scope"], unique=False)
    op.create_index(op.f("ix_stock_catalog_items_review_type"), "stock_catalog_items", ["review_type"], unique=False)
    op.create_index(op.f("ix_stock_catalog_items_is_operational"), "stock_catalog_items", ["is_operational"], unique=False)
    op.create_index(op.f("ix_stock_catalog_items_is_searchable_common"), "stock_catalog_items", ["is_searchable_common"], unique=False)
    op.create_index(op.f("ix_stock_catalog_items_is_tree_visible_common"), "stock_catalog_items", ["is_tree_visible_common"], unique=False)
    op.create_index(op.f("ix_stock_catalog_items_is_parser_junk"), "stock_catalog_items", ["is_parser_junk"], unique=False)

    # 2. Alterar stock_catalog_tree_nodes
    op.add_column("stock_catalog_tree_nodes", sa.Column("canonical_category", sa.String(length=100), nullable=True))
    op.add_column("stock_catalog_tree_nodes", sa.Column("canonical_category_display", sa.String(length=255), nullable=True))
    op.add_column("stock_catalog_tree_nodes", sa.Column("canonical_parent_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("stock_catalog_tree_nodes", sa.Column("is_visible_to_common_user", sa.Boolean(), nullable=False, server_default="true"))

    op.create_index(op.f("ix_stock_catalog_tree_nodes_canonical_category"), "stock_catalog_tree_nodes", ["canonical_category"], unique=False)
    op.create_index(op.f("ix_stock_catalog_tree_nodes_is_visible_to_common_user"), "stock_catalog_tree_nodes", ["is_visible_to_common_user"], unique=False)


def downgrade() -> None:
    # 1. Remover de stock_catalog_tree_nodes
    op.drop_index(op.f("ix_stock_catalog_tree_nodes_is_visible_to_common_user"), table_name="stock_catalog_tree_nodes")
    op.drop_index(op.f("ix_stock_catalog_tree_nodes_canonical_category"), table_name="stock_catalog_tree_nodes")
    op.drop_column("stock_catalog_tree_nodes", "is_visible_to_common_user")
    op.drop_column("stock_catalog_tree_nodes", "canonical_parent_id")
    op.drop_column("stock_catalog_tree_nodes", "canonical_category_display")
    op.drop_column("stock_catalog_tree_nodes", "canonical_category")

    # 2. Remover de stock_catalog_items
    op.drop_index(op.f("ix_stock_catalog_items_is_parser_junk"), table_name="stock_catalog_items")
    op.drop_index(op.f("ix_stock_catalog_items_is_tree_visible_common"), table_name="stock_catalog_items")
    op.drop_index(op.f("ix_stock_catalog_items_is_searchable_common"), table_name="stock_catalog_items")
    op.drop_index(op.f("ix_stock_catalog_items_is_operational"), table_name="stock_catalog_items")
    op.drop_index(op.f("ix_stock_catalog_items_review_type"), table_name="stock_catalog_items")
    op.drop_index(op.f("ix_stock_catalog_items_visibility_scope"), table_name="stock_catalog_items")
    op.drop_index(op.f("ix_stock_catalog_items_canonical_category"), table_name="stock_catalog_items")

    op.drop_column("stock_catalog_items", "is_parser_junk")
    op.drop_column("stock_catalog_items", "is_category_only")
    op.drop_column("stock_catalog_items", "is_offer_active")
    op.drop_column("stock_catalog_items", "is_tree_visible_common")
    op.drop_column("stock_catalog_items", "is_searchable_common")
    op.drop_column("stock_catalog_items", "is_operational")
    op.drop_column("stock_catalog_items", "review_type")
    op.drop_column("stock_catalog_items", "visibility_scope")
    op.drop_column("stock_catalog_items", "canonical_category_display")
    op.drop_column("stock_catalog_items", "canonical_category")
