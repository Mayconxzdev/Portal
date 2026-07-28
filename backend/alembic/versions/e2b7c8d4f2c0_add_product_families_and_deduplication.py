"""Add product families and deduplication queue.

Revision ID: e2b7c8d4f2c0
Revises: f6c7c8d4f2b9
Create Date: 2026-06-05
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e2b7c8d4f2c0'
down_revision = '75b3d82d6381'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Cria a tabela product_families
    op.create_table(
        'product_families',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_product_families_created_at'), 'product_families', ['created_at'], unique=False)
    op.create_index(op.f('ix_product_families_name'), 'product_families', ['name'], unique=True)

    # 2. Adiciona as colunas na tabela product_items
    op.add_column('product_items', sa.Column('family_id', sa.UUID(), nullable=True))
    op.add_column('product_items', sa.Column('canonical_key', sa.String(length=500), nullable=True))
    op.add_column('product_items', sa.Column('attributes', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    
    op.create_foreign_key('fk_product_items_family_id', 'product_items', 'product_families', ['family_id'], ['id'], ondelete='SET NULL')
    op.create_index(op.f('ix_product_items_family_id'), 'product_items', ['family_id'], unique=False)
    op.create_index(op.f('ix_product_items_canonical_key'), 'product_items', ['canonical_key'], unique=True)

    # 3. Cria a tabela product_deduplication_queue
    op.create_table(
        'product_deduplication_queue',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('item_a_id', sa.UUID(), nullable=False),
        sa.Column('item_b_id', sa.UUID(), nullable=False),
        sa.Column('relation_type', sa.String(length=50), nullable=False),
        sa.Column('similarity_score', sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('resolved_by_user_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['item_a_id'], ['product_items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['item_b_id'], ['product_items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['resolved_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_product_deduplication_queue_created_at'), 'product_deduplication_queue', ['created_at'], unique=False)
    op.create_index(op.f('ix_product_deduplication_queue_item_a_id'), 'product_deduplication_queue', ['item_a_id'], unique=False)
    op.create_index(op.f('ix_product_deduplication_queue_item_b_id'), 'product_deduplication_queue', ['item_b_id'], unique=False)
    op.create_index(op.f('ix_product_deduplication_queue_status'), 'product_deduplication_queue', ['status'], unique=False)

def downgrade() -> None:
    # 1. Remove tabelas e colunas
    op.drop_index(op.f('ix_product_deduplication_queue_status'), table_name='product_deduplication_queue')
    op.drop_index(op.f('ix_product_deduplication_queue_item_b_id'), table_name='product_deduplication_queue')
    op.drop_index(op.f('ix_product_deduplication_queue_item_a_id'), table_name='product_deduplication_queue')
    op.drop_index(op.f('ix_product_deduplication_queue_created_at'), table_name='product_deduplication_queue')
    op.drop_table('product_deduplication_queue')

    op.drop_index(op.f('ix_product_items_canonical_key'), table_name='product_items')
    op.drop_index(op.f('ix_product_items_family_id'), table_name='product_items')
    op.drop_constraint('fk_product_items_family_id', 'product_items', type_='foreignkey')
    op.drop_column('product_items', 'attributes')
    op.drop_column('product_items', 'canonical_key')
    op.drop_column('product_items', 'family_id')

    op.drop_index(op.f('ix_product_families_name'), table_name='product_families')
    op.drop_index(op.f('ix_product_families_created_at'), table_name='product_families')
    op.drop_table('product_families')
