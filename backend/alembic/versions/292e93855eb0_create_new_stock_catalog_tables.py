"""create new stock catalog tables

Revision ID: 292e93855eb0
Revises: 1ed94c94764c
Create Date: 2026-06-11 10:35:02.570063

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '292e93855eb0'
down_revision: Union[str, None] = '1ed94c94764c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Habilitar a extensão pg_trgm para buscas tolerantes
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # 2. Drop das tabelas legadas vazias de stock para evitar conflitos de schema
    op.execute("DROP TABLE IF EXISTS stock_balances CASCADE")
    op.execute("DROP TABLE IF EXISTS stock_catalog_tree_cache CASCADE")
    op.execute("DROP TABLE IF EXISTS stock_costs CASCADE")
    op.execute("DROP TABLE IF EXISTS stock_supplier_links CASCADE")
    op.execute("DROP TABLE IF EXISTS stock_import_runs CASCADE")
    op.execute("DROP TABLE IF EXISTS stock_catalog_items CASCADE")

    # 3. Criação das novas tabelas oficiais
    op.create_table(
        'stock_catalog_sources',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_stock_catalog_sources_active'), 'stock_catalog_sources', ['active'], unique=False)

    op.create_table(
        'stock_catalog_suppliers',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('normalized_name', sa.String(length=255), nullable=False),
        sa.Column('document', sa.String(length=50), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('contact_name', sa.String(length=100), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_stock_catalog_suppliers_active'), 'stock_catalog_suppliers', ['active'], unique=False)
    op.create_index(op.f('ix_stock_catalog_suppliers_document'), 'stock_catalog_suppliers', ['document'], unique=False)
    op.create_index(op.f('ix_stock_catalog_suppliers_normalized_name'), 'stock_catalog_suppliers', ['normalized_name'], unique=True)

    op.create_table(
        'stock_catalog_import_runs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('source_path', sa.String(length=500), nullable=False),
        sa.Column('source_filename', sa.String(length=255), nullable=False),
        sa.Column('source_hash', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('total_rows', sa.Integer(), nullable=False),
        sa.Column('total_items', sa.Integer(), nullable=False),
        sa.Column('total_offers', sa.Integer(), nullable=False),
        sa.Column('total_errors', sa.Integer(), nullable=False),
        sa.Column('total_review', sa.Integer(), nullable=False),
        sa.Column('triggered_by_user_id', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['triggered_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_stock_catalog_import_runs_started_at'), 'stock_catalog_import_runs', ['started_at'], unique=False)
    op.create_index(op.f('ix_stock_catalog_import_runs_status'), 'stock_catalog_import_runs', ['status'], unique=False)

    op.create_table(
        'stock_catalog_cybersul_products',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('cybersul_code', sa.String(length=100), nullable=False),
        sa.Column('old_code', sa.String(length=100), nullable=True),
        sa.Column('description', sa.String(length=500), nullable=False),
        sa.Column('normalized_description', sa.String(length=500), nullable=False),
        sa.Column('complement', sa.Text(), nullable=True),
        sa.Column('unit', sa.String(length=30), nullable=False),
        sa.Column('balance_vesper', sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column('balance_ventrio', sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column('balance_total', sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column('cost_price', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('supplier_name', sa.String(length=255), nullable=True),
        sa.Column('ncm', sa.String(length=20), nullable=True),
        sa.Column('group_name', sa.String(length=100), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('source_row', sa.Integer(), nullable=False),
        sa.Column('import_run_id', sa.UUID(), nullable=False),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['import_run_id'], ['stock_catalog_import_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_stock_catalog_cybersul_products_active'), 'stock_catalog_cybersul_products', ['active'], unique=False)
    op.create_index(op.f('ix_stock_catalog_cybersul_products_cybersul_code'), 'stock_catalog_cybersul_products', ['cybersul_code'], unique=True)
    op.create_index(op.f('ix_stock_catalog_cybersul_products_import_run_id'), 'stock_catalog_cybersul_products', ['import_run_id'], unique=False)
    op.create_index(op.f('ix_stock_catalog_cybersul_products_normalized_description'), 'stock_catalog_cybersul_products', ['normalized_description'], unique=False)
    op.create_index(op.f('ix_stock_catalog_cybersul_products_old_code'), 'stock_catalog_cybersul_products', ['old_code'], unique=False)

    op.create_table(
        'stock_catalog_tree_nodes',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('import_run_id', sa.UUID(), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('source_sheet', sa.String(length=100), nullable=False),
        sa.Column('parent_id', sa.UUID(), nullable=True),
        sa.Column('node_type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('normalized_title', sa.String(length=255), nullable=False),
        sa.Column('path', sa.String(length=1000), nullable=False),
        sa.Column('depth', sa.Integer(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('start_row', sa.Integer(), nullable=False),
        sa.Column('end_row', sa.Integer(), nullable=False),
        sa.Column('style_signature', sa.String(length=255), nullable=True),
        sa.Column('confidence', sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column('needs_review', sa.Boolean(), nullable=False),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['import_run_id'], ['stock_catalog_import_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_id'], ['stock_catalog_tree_nodes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_stock_catalog_tree_nodes_import_run_id'), 'stock_catalog_tree_nodes', ['import_run_id'], unique=False)
    op.create_index(op.f('ix_stock_catalog_tree_nodes_needs_review'), 'stock_catalog_tree_nodes', ['needs_review'], unique=False)
    op.create_index(op.f('ix_stock_catalog_tree_nodes_normalized_title'), 'stock_catalog_tree_nodes', ['normalized_title'], unique=False)
    op.create_index(op.f('ix_stock_catalog_tree_nodes_parent_id'), 'stock_catalog_tree_nodes', ['parent_id'], unique=False)

    op.create_table(
        'stock_catalog_items',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('import_run_id', sa.UUID(), nullable=False),
        sa.Column('source_sheet', sa.String(length=100), nullable=False),
        sa.Column('family_node_id', sa.UUID(), nullable=True),
        sa.Column('product_node_id', sa.UUID(), nullable=True),
        sa.Column('variation_node_id', sa.UUID(), nullable=True),
        sa.Column('display_name', sa.String(length=255), nullable=False),
        sa.Column('base_name', sa.String(length=255), nullable=False),
        sa.Column('normalized_name', sa.String(length=255), nullable=False),
        sa.Column('variation_label', sa.String(length=100), nullable=True),
        sa.Column('normalized_measure', sa.String(length=100), nullable=True),
        sa.Column('specification_text', sa.Text(), nullable=True),
        sa.Column('identity_hash', sa.String(length=64), nullable=False),
        sa.Column('internal_code', sa.String(length=100), nullable=True),
        sa.Column('cybersul_product_id', sa.UUID(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('needs_review', sa.Boolean(), nullable=False),
        sa.Column('review_reason', sa.Text(), nullable=True),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['cybersul_product_id'], ['stock_catalog_cybersul_products.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['import_run_id'], ['stock_catalog_import_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['family_node_id'], ['stock_catalog_tree_nodes.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['product_node_id'], ['stock_catalog_tree_nodes.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['variation_node_id'], ['stock_catalog_tree_nodes.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_stock_catalog_items_active'), 'stock_catalog_items', ['active'], unique=False)
    op.create_index(op.f('ix_stock_catalog_items_cybersul_product_id'), 'stock_catalog_items', ['cybersul_product_id'], unique=False)
    op.create_index(op.f('ix_stock_catalog_items_family_node_id'), 'stock_catalog_items', ['family_node_id'], unique=False)
    op.create_index(op.f('ix_stock_catalog_items_identity_hash'), 'stock_catalog_items', ['identity_hash'], unique=True)
    op.create_index(op.f('ix_stock_catalog_items_import_run_id'), 'stock_catalog_items', ['import_run_id'], unique=False)
    op.create_index(op.f('ix_stock_catalog_items_internal_code'), 'stock_catalog_items', ['internal_code'], unique=False)
    op.create_index(op.f('ix_stock_catalog_items_needs_review'), 'stock_catalog_items', ['needs_review'], unique=False)
    op.create_index(op.f('ix_stock_catalog_items_normalized_name'), 'stock_catalog_items', ['normalized_name'], unique=False)
    op.create_index(op.f('ix_stock_catalog_items_product_node_id'), 'stock_catalog_items', ['product_node_id'], unique=False)
    op.create_index(op.f('ix_stock_catalog_items_variation_node_id'), 'stock_catalog_items', ['variation_node_id'], unique=False)
    op.create_index(op.f('ix_stock_catalog_items_created_at'), 'stock_catalog_items', ['created_at'], unique=False)

    op.create_table(
        'stock_catalog_alerts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('item_id', sa.UUID(), nullable=False),
        sa.Column('alert_type', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=30), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['item_id'], ['stock_catalog_items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_stock_catalog_alerts_created_at'), 'stock_catalog_alerts', ['created_at'], unique=False)
    op.create_index(op.f('ix_stock_catalog_alerts_item_id'), 'stock_catalog_alerts', ['item_id'], unique=False)
    op.create_index(op.f('ix_stock_catalog_alerts_status'), 'stock_catalog_alerts', ['status'], unique=False)

    op.create_table(
        'stock_catalog_item_specs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('item_id', sa.UUID(), nullable=False),
        sa.Column('spec_key', sa.String(length=100), nullable=False),
        sa.Column('spec_value', sa.String(length=255), nullable=False),
        sa.Column('normalized_value', sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(['item_id'], ['stock_catalog_items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_stock_catalog_item_specs_item_id'), 'stock_catalog_item_specs', ['item_id'], unique=False)
    op.create_index(op.f('ix_stock_catalog_item_specs_normalized_value'), 'stock_catalog_item_specs', ['normalized_value'], unique=False)

    op.create_table(
        'stock_catalog_links',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('stock_catalog_item_id', sa.UUID(), nullable=False),
        sa.Column('cybersul_product_id', sa.UUID(), nullable=False),
        sa.Column('match_type', sa.String(length=50), nullable=False),
        sa.Column('confidence', sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column('match_reason', sa.Text(), nullable=True),
        sa.Column('approved_by_user_id', sa.Integer(), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('needs_review', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['approved_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['cybersul_product_id'], ['stock_catalog_cybersul_products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['stock_catalog_item_id'], ['stock_catalog_items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_stock_catalog_links_cybersul_product_id'), 'stock_catalog_links', ['cybersul_product_id'], unique=False)
    op.create_index(op.f('ix_stock_catalog_links_needs_review'), 'stock_catalog_links', ['needs_review'], unique=False)
    op.create_index(op.f('ix_stock_catalog_links_stock_catalog_item_id'), 'stock_catalog_links', ['stock_catalog_item_id'], unique=False)

    op.create_table(
        'stock_catalog_offers',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('item_id', sa.UUID(), nullable=False),
        sa.Column('supplier_id', sa.UUID(), nullable=False),
        sa.Column('import_run_id', sa.UUID(), nullable=False),
        sa.Column('source_sheet', sa.String(length=100), nullable=False),
        sa.Column('source_row', sa.Integer(), nullable=False),
        sa.Column('price', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('price_raw', sa.String(length=50), nullable=True),
        sa.Column('final_value', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('final_value_raw', sa.String(length=50), nullable=True),
        sa.Column('currency', sa.String(length=10), nullable=False),
        sa.Column('unit', sa.String(length=30), nullable=False),
        sa.Column('availability', sa.String(length=100), nullable=True),
        sa.Column('delivery_time', sa.String(length=100), nullable=True),
        sa.Column('contact_email', sa.String(length=255), nullable=True),
        sa.Column('contact_phone', sa.String(length=50), nullable=True),
        sa.Column('is_current', sa.Boolean(), nullable=False),
        sa.Column('is_consolidated_line', sa.Boolean(), nullable=False),
        sa.Column('confidence', sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column('needs_review', sa.Boolean(), nullable=False),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['import_run_id'], ['stock_catalog_import_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['item_id'], ['stock_catalog_items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['supplier_id'], ['stock_catalog_suppliers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_stock_catalog_offers_created_at'), 'stock_catalog_offers', ['created_at'], unique=False)
    op.create_index(op.f('ix_stock_catalog_offers_import_run_id'), 'stock_catalog_offers', ['import_run_id'], unique=False)
    op.create_index(op.f('ix_stock_catalog_offers_is_current'), 'stock_catalog_offers', ['is_current'], unique=False)
    op.create_index(op.f('ix_stock_catalog_offers_item_id'), 'stock_catalog_offers', ['item_id'], unique=False)
    op.create_index(op.f('ix_stock_catalog_offers_needs_review'), 'stock_catalog_offers', ['needs_review'], unique=False)
    op.create_index(op.f('ix_stock_catalog_offers_supplier_id'), 'stock_catalog_offers', ['supplier_id'], unique=False)

    op.create_table(
        'stock_catalog_price_history',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('item_id', sa.UUID(), nullable=False),
        sa.Column('supplier_id', sa.UUID(), nullable=False),
        sa.Column('old_price', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('new_price', sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('source_reference', sa.String(length=255), nullable=True),
        sa.Column('changed_by_user_id', sa.Integer(), nullable=True),
        sa.Column('changed_at', sa.DateTime(), nullable=False),
        sa.Column('evidence_file_id', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['changed_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['evidence_file_id'], ['files.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['item_id'], ['stock_catalog_items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['supplier_id'], ['stock_catalog_suppliers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_stock_catalog_price_history_changed_at'), 'stock_catalog_price_history', ['changed_at'], unique=False)
    op.create_index(op.f('ix_stock_catalog_price_history_item_id'), 'stock_catalog_price_history', ['item_id'], unique=False)
    op.create_index(op.f('ix_stock_catalog_price_history_supplier_id'), 'stock_catalog_price_history', ['supplier_id'], unique=False)

    op.create_table(
        'stock_catalog_review_queue',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('item_id', sa.UUID(), nullable=False),
        sa.Column('import_run_id', sa.UUID(), nullable=False),
        sa.Column('review_type', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=30), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('raw_context_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('resolved_by_user_id', sa.Integer(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['import_run_id'], ['stock_catalog_import_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['item_id'], ['stock_catalog_items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['resolved_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_stock_catalog_review_queue_import_run_id'), 'stock_catalog_review_queue', ['import_run_id'], unique=False)
    op.create_index(op.f('ix_stock_catalog_review_queue_item_id'), 'stock_catalog_review_queue', ['item_id'], unique=False)
    op.create_index(op.f('ix_stock_catalog_review_queue_status'), 'stock_catalog_review_queue', ['status'], unique=False)

    op.create_table(
        'stock_catalog_search_index',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('item_id', sa.UUID(), nullable=False),
        sa.Column('search_text', sa.Text(), nullable=False),
        sa.Column('normalized_search_text', sa.Text(), nullable=False),
        sa.Column('tokens_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('supplier_names', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('cybersul_code', sa.String(length=100), nullable=True),
        sa.Column('source_sheet', sa.String(length=100), nullable=False),
        sa.Column('family_path', sa.String(length=1000), nullable=False),
        sa.Column('last_price', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('last_supplier', sa.String(length=255), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['item_id'], ['stock_catalog_items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_stock_catalog_search_index_cybersul_code'), 'stock_catalog_search_index', ['cybersul_code'], unique=False)
    op.create_index(op.f('ix_stock_catalog_search_index_item_id'), 'stock_catalog_search_index', ['item_id'], unique=True)
    op.create_index(op.f('ix_stock_catalog_search_index_normalized_search_text'), 'stock_catalog_search_index', ['normalized_search_text'], unique=False)

    # Criação do índice trigrama GIN no PostgreSQL
    op.create_index(
        'ix_stock_catalog_search_index_trgm',
        'stock_catalog_search_index',
        ['normalized_search_text'],
        postgresql_using='gin',
        postgresql_ops={'normalized_search_text': 'gin_trgm_ops'}
    )


def downgrade() -> None:
    # Drop das 13 tabelas novas
    op.execute("DROP TABLE IF EXISTS stock_catalog_search_index CASCADE")
    op.execute("DROP TABLE IF EXISTS stock_catalog_review_queue CASCADE")
    op.execute("DROP TABLE IF EXISTS stock_catalog_price_history CASCADE")
    op.execute("DROP TABLE IF EXISTS stock_catalog_offers CASCADE")
    op.execute("DROP TABLE IF EXISTS stock_catalog_links CASCADE")
    op.execute("DROP TABLE IF EXISTS stock_catalog_item_specs CASCADE")
    op.execute("DROP TABLE IF EXISTS stock_catalog_alerts CASCADE")
    op.execute("DROP TABLE IF EXISTS stock_catalog_items CASCADE")
    op.execute("DROP TABLE IF EXISTS stock_catalog_tree_nodes CASCADE")
    op.execute("DROP TABLE IF EXISTS stock_catalog_cybersul_products CASCADE")
    op.execute("DROP TABLE IF EXISTS stock_catalog_import_runs CASCADE")
    op.execute("DROP TABLE IF EXISTS stock_catalog_suppliers CASCADE")
    op.execute("DROP TABLE IF EXISTS stock_catalog_sources CASCADE")
