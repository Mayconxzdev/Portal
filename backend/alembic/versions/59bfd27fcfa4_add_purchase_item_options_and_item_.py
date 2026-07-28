"""add_purchase_item_options_and_item_status

Revision ID: 59bfd27fcfa4
Revises: f9b2d7c1a6e4
Create Date: 2026-06-19 10:14:25.301875

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '59bfd27fcfa4'
down_revision: Union[str, None] = 'f9b2d7c1a6e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    
    # 1. Adiciona as novas colunas à tabela purchase_items de forma condicional
    purchase_items_cols = [c['name'] for c in inspector.get_columns('purchase_items')]
    
    if 'normalized_name' not in purchase_items_cols:
        op.add_column('purchase_items', sa.Column('normalized_name', sa.String(length=255), nullable=True))
    if 'destination' not in purchase_items_cols:
        op.add_column('purchase_items', sa.Column('destination', sa.Text(), nullable=True))
    if 'department' not in purchase_items_cols:
        op.add_column('purchase_items', sa.Column('department', sa.String(length=100), nullable=True))
    if 'budget_limit' not in purchase_items_cols:
        op.add_column('purchase_items', sa.Column('budget_limit', sa.Numeric(precision=12, scale=2), nullable=True))
    if 'classification' not in purchase_items_cols:
        op.add_column('purchase_items', sa.Column('classification', sa.String(length=30), nullable=True, server_default='EXTERNAL'))
    if 'classification_confidence' not in purchase_items_cols:
        op.add_column('purchase_items', sa.Column('classification_confidence', sa.Numeric(precision=8, scale=4), nullable=True))
    if 'selected_option_id' not in purchase_items_cols:
        op.add_column('purchase_items', sa.Column('selected_option_id', sa.UUID(), nullable=True))
    if 'approval_status' not in purchase_items_cols:
        op.add_column('purchase_items', sa.Column('approval_status', sa.String(length=30), nullable=False, server_default='PENDING'))
    if 'purchasing_status' not in purchase_items_cols:
        op.add_column('purchase_items', sa.Column('purchasing_status', sa.String(length=30), nullable=False, server_default='PENDING'))
    if 'delivery_status' not in purchase_items_cols:
        op.add_column('purchase_items', sa.Column('delivery_status', sa.String(length=30), nullable=False, server_default='PENDING'))
    if 'updated_at' not in purchase_items_cols:
        op.add_column('purchase_items', sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')))

    # 2. Cria a nova tabela purchase_item_options de forma condicional
    if 'purchase_item_options' not in tables:
        op.create_table('purchase_item_options',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('purchase_item_id', sa.UUID(), nullable=False),
            sa.Column('source_type', sa.String(length=50), nullable=False),
            sa.Column('supplier_id', sa.UUID(), nullable=True),
            sa.Column('store_name', sa.String(length=255), nullable=True),
            sa.Column('seller_name', sa.String(length=255), nullable=True),
            sa.Column('title', sa.String(length=255), nullable=False),
            sa.Column('brand', sa.String(length=255), nullable=True),
            sa.Column('model', sa.String(length=255), nullable=True),
            sa.Column('image_url', sa.Text(), nullable=True),
            sa.Column('product_url', sa.Text(), nullable=True),
            sa.Column('unit_price', sa.Numeric(precision=12, scale=2), nullable=False),
            sa.Column('shipping_price', sa.Numeric(precision=12, scale=2), nullable=True),
            sa.Column('total_price', sa.Numeric(precision=12, scale=2), nullable=False),
            sa.Column('delivery_estimate', sa.String(length=255), nullable=True),
            sa.Column('availability', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('rating', sa.Numeric(precision=3, scale=2), nullable=True),
            sa.Column('review_count', sa.Integer(), nullable=True),
            sa.Column('specifications', sa.Text(), nullable=True),
            sa.Column('captured_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
            sa.Column('raw_source_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column('status', sa.String(length=30), nullable=True),
            sa.Column('selected', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('rejection_reason', sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(['purchase_item_id'], ['purchase_items.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        
        # 3. Cria índices para a nova tabela
        op.create_index(op.f('ix_purchase_item_options_purchase_item_id'), 'purchase_item_options', ['purchase_item_id'], unique=False)
        op.create_index(op.f('ix_purchase_item_options_source_type'), 'purchase_item_options', ['source_type'], unique=False)
        op.create_index(op.f('ix_purchase_item_options_supplier_id'), 'purchase_item_options', ['supplier_id'], unique=False)


def downgrade() -> None:
    # 1. Drop indices e tabela purchase_item_options
    op.drop_index(op.f('ix_purchase_item_options_supplier_id'), table_name='purchase_item_options')
    op.drop_index(op.f('ix_purchase_item_options_source_type'), table_name='purchase_item_options')
    op.drop_index(op.f('ix_purchase_item_options_purchase_item_id'), table_name='purchase_item_options')
    op.drop_table('purchase_item_options')

    # 2. Remove as colunas adicionadas à tabela purchase_items
    op.drop_column('purchase_items', 'updated_at')
    op.drop_column('purchase_items', 'delivery_status')
    op.drop_column('purchase_items', 'purchasing_status')
    op.drop_column('purchase_items', 'approval_status')
    op.drop_column('purchase_items', 'selected_option_id')
    op.drop_column('purchase_items', 'classification_confidence')
    op.drop_column('purchase_items', 'classification')
    op.drop_column('purchase_items', 'budget_limit')
    op.drop_column('purchase_items', 'department')
    op.drop_column('purchase_items', 'destination')
    op.drop_column('purchase_items', 'normalized_name')
