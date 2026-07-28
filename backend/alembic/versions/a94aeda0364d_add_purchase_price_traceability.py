"""add_purchase_price_traceability

Revision ID: a94aeda0364d
Revises: 9e7e733eb4c4
Create Date: 2026-06-03 16:23:58.560999

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a94aeda0364d'
down_revision: Union[str, None] = '9e7e733eb4c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Criar purchase_price_evidences
    op.create_table(
        'purchase_price_evidences',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('supplier_id', sa.UUID(), nullable=True),
        sa.Column('product_item_id', sa.UUID(), nullable=True),
        sa.Column('service_id', sa.UUID(), nullable=True),
        sa.Column('document_number', sa.String(length=100), nullable=True),
        sa.Column('document_date', sa.DateTime(), nullable=True),
        sa.Column('unit_price', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('quantity', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('total_amount', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('currency', sa.String(length=10), nullable=False),
        sa.Column('unit_of_measure', sa.String(length=30), nullable=True),
        sa.Column('payment_terms', sa.String(length=255), nullable=True),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('file_id', sa.String(length=100), nullable=True),
        sa.Column('raw_summary', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by_user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('tenant_id', sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_item_id'], ['product_items.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['service_id'], ['services.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_purchase_price_evidences_created_at'), 'purchase_price_evidences', ['created_at'], unique=False)
    op.create_index(op.f('ix_purchase_price_evidences_product_item_id'), 'purchase_price_evidences', ['product_item_id'], unique=False)
    op.create_index(op.f('ix_purchase_price_evidences_service_id'), 'purchase_price_evidences', ['service_id'], unique=False)
    op.create_index(op.f('ix_purchase_price_evidences_supplier_id'), 'purchase_price_evidences', ['supplier_id'], unique=False)

    # 2. Criar purchase_price_history
    op.create_table(
        'purchase_price_history',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('product_item_id', sa.UUID(), nullable=False),
        sa.Column('supplier_id', sa.UUID(), nullable=True),
        sa.Column('evidence_id', sa.UUID(), nullable=True),
        sa.Column('rfq_id', sa.UUID(), nullable=True),
        sa.Column('quote_response_id', sa.UUID(), nullable=True),
        sa.Column('unit_price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('total_amount', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('currency', sa.String(length=10), nullable=False),
        sa.Column('unit_of_measure', sa.String(length=30), nullable=True),
        sa.Column('observed_at', sa.DateTime(), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('source_id', sa.String(length=100), nullable=True),
        sa.Column('created_by_user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('invalidated_at', sa.DateTime(), nullable=True),
        sa.Column('invalidated_by_user_id', sa.Integer(), nullable=True),
        sa.Column('invalidation_reason', sa.Text(), nullable=True),
        sa.Column('tenant_id', sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['evidence_id'], ['purchase_price_evidences.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['invalidated_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['product_item_id'], ['product_items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['quote_response_id'], ['purchase_quote_responses.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['rfq_id'], ['purchase_rfqs.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_purchase_price_history_created_at'), 'purchase_price_history', ['created_at'], unique=False)
    op.create_index(op.f('ix_purchase_price_history_evidence_id'), 'purchase_price_history', ['evidence_id'], unique=False)
    op.create_index(op.f('ix_purchase_price_history_observed_at'), 'purchase_price_history', ['observed_at'], unique=False)
    op.create_index(op.f('ix_purchase_price_history_product_item_id'), 'purchase_price_history', ['product_item_id'], unique=False)
    op.create_index(op.f('ix_purchase_price_history_quote_response_id'), 'purchase_price_history', ['quote_response_id'], unique=False)
    op.create_index(op.f('ix_purchase_price_history_rfq_id'), 'purchase_price_history', ['rfq_id'], unique=False)
    op.create_index(op.f('ix_purchase_price_history_supplier_id'), 'purchase_price_history', ['supplier_id'], unique=False)

    # 3. Criar purchase_price_references
    op.create_table(
        'purchase_price_references',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('product_item_id', sa.UUID(), nullable=False),
        sa.Column('supplier_id', sa.UUID(), nullable=True),
        sa.Column('current_unit_price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=False),
        sa.Column('unit_of_measure', sa.String(length=30), nullable=True),
        sa.Column('source_history_id', sa.UUID(), nullable=True),
        sa.Column('source_evidence_id', sa.UUID(), nullable=True),
        sa.Column('approved_by_user_id', sa.Integer(), nullable=False),
        sa.Column('approved_at', sa.DateTime(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('tenant_id', sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(['approved_by_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_item_id'], ['product_items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_evidence_id'], ['purchase_price_evidences.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['source_history_id'], ['purchase_price_history.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_purchase_price_references_product_item_id'), 'purchase_price_references', ['product_item_id'], unique=False)
    op.create_index(op.f('ix_purchase_price_references_supplier_id'), 'purchase_price_references', ['supplier_id'], unique=False)

    # 4. Criar purchase_price_update_suggestions
    op.create_table(
        'purchase_price_update_suggestions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('product_item_id', sa.UUID(), nullable=False),
        sa.Column('supplier_id', sa.UUID(), nullable=True),
        sa.Column('evidence_id', sa.UUID(), nullable=False),
        sa.Column('history_id', sa.UUID(), nullable=True),
        sa.Column('reference_id', sa.UUID(), nullable=True),
        sa.Column('old_unit_price', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('new_unit_price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('pct_variation', sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column('variation_direction', sa.String(length=30), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        sa.Column('created_by_user_id', sa.Integer(), nullable=False),
        sa.Column('reviewed_by_user_id', sa.Integer(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('tenant_id', sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['evidence_id'], ['purchase_price_evidences.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['history_id'], ['purchase_price_history.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['product_item_id'], ['product_items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reference_id'], ['purchase_price_references.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['reviewed_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_purchase_price_update_suggestions_created_at'), 'purchase_price_update_suggestions', ['created_at'], unique=False)
    op.create_index(op.f('ix_purchase_price_update_suggestions_evidence_id'), 'purchase_price_update_suggestions', ['evidence_id'], unique=False)
    op.create_index(op.f('ix_purchase_price_update_suggestions_history_id'), 'purchase_price_update_suggestions', ['history_id'], unique=False)
    op.create_index(op.f('ix_purchase_price_update_suggestions_product_item_id'), 'purchase_price_update_suggestions', ['product_item_id'], unique=False)
    op.create_index(op.f('ix_purchase_price_update_suggestions_reference_id'), 'purchase_price_update_suggestions', ['reference_id'], unique=False)
    op.create_index(op.f('ix_purchase_price_update_suggestions_status'), 'purchase_price_update_suggestions', ['status'], unique=False)
    op.create_index(op.f('ix_purchase_price_update_suggestions_supplier_id'), 'purchase_price_update_suggestions', ['supplier_id'], unique=False)


def downgrade() -> None:
    op.drop_table('purchase_price_update_suggestions')
    op.drop_table('purchase_price_references')
    op.drop_table('purchase_price_history')
    op.drop_table('purchase_price_evidences')
