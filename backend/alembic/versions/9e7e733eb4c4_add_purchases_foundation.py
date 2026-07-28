"""add_purchases_foundation

Revision ID: 9e7e733eb4c4
Revises: ab49968d9285
Create Date: 2026-06-03 12:02:37.578182

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9e7e733eb4c4'
down_revision: Union[str, None] = 'ab49968d9285'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Drop existing tables if they exist (drop in order of dependencies)
    op.execute("DROP TABLE IF EXISTS purchase_activities CASCADE;")
    op.execute("DROP TABLE IF EXISTS quotation_items CASCADE;")
    op.execute("DROP TABLE IF EXISTS quotations CASCADE;")
    op.execute("DROP TABLE IF EXISTS purchase_items CASCADE;")
    op.execute("DROP TABLE IF EXISTS purchase_requests CASCADE;")

    # 2. Recreate purchase_requests with UUID ID
    op.create_table('purchase_requests',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('justification', sa.Text(), nullable=True),
        sa.Column('requester_user_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='DRAFT'),
        sa.Column('priority', sa.String(length=20), nullable=False, server_default='NORMAL'),
        sa.Column('urgency', sa.String(length=20), nullable=False, server_default='NORMAL'),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('department', sa.String(length=100), nullable=True),
        sa.Column('estimated_total', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('approved_total', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('needed_by', sa.DateTime(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('tenant_id', sa.String(length=50), nullable=True),
        sa.Column('approval_id', sa.Integer(), nullable=True),
        sa.Column('selected_quotation_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['requester_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['approval_id'], ['approvals.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_purchase_requests_id', 'purchase_requests', ['id'], unique=False)
    op.create_index('ix_purchase_requests_status', 'purchase_requests', ['status'], unique=False)

    # 3. Recreate purchase_items (with UUID)
    op.create_table('purchase_items',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('purchase_request_id', sa.UUID(), nullable=False),
        sa.Column('item_id', sa.UUID(), nullable=True),
        sa.Column('service_id', sa.UUID(), nullable=True),
        sa.Column('free_text_description', sa.Text(), nullable=True),
        sa.Column('quantity', sa.Numeric(precision=10, scale=2), nullable=False, server_default='1'),
        sa.Column('unit_of_measure', sa.String(length=30), nullable=False, server_default='un'),
        sa.Column('specifications', sa.Text(), nullable=True),
        sa.Column('estimated_unit_price', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['purchase_request_id'], ['purchase_requests.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['item_id'], ['product_items.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['service_id'], ['services.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # 4. Recreate Quotations (Legado)
    op.create_table('quotations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('purchase_request_id', sa.UUID(), nullable=False),
        sa.Column('supplier_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='PENDING'),
        sa.Column('total_value', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('payment_terms', sa.String(length=255), nullable=True),
        sa.Column('delivery_days', sa.Integer(), nullable=True),
        sa.Column('valid_until', sa.DateTime(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('registered_by_user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['purchase_request_id'], ['purchase_requests.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['registered_by_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_quotations_id', 'quotations', ['id'], unique=False)
    op.create_index('ix_quotations_status', 'quotations', ['status'], unique=False)

    # 5. Recreate QuotationItems (Legado)
    op.create_table('quotation_items',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('quotation_id', sa.Integer(), nullable=False),
        sa.Column('purchase_item_id', sa.UUID(), nullable=False),
        sa.Column('quoted_unit_price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('delivery_days', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['quotation_id'], ['quotations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['purchase_item_id'], ['purchase_items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_quotation_items_id', 'quotation_items', ['id'], unique=False)

    # 6. Recreate PurchaseActivity
    op.create_table('purchase_activities',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('purchase_request_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['purchase_request_id'], ['purchase_requests.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_purchase_activities_id', 'purchase_activities', ['id'], unique=False)
    op.create_index('ix_purchase_activities_action', 'purchase_activities', ['action'], unique=False)

    # 7. Create purchase_rfqs
    op.create_table('purchase_rfqs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('purchase_request_id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='DRAFT'),
        sa.Column('deadline', sa.DateTime(), nullable=True),
        sa.Column('message_template', sa.Text(), nullable=True),
        sa.Column('created_by_user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['purchase_request_id'], ['purchase_requests.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_purchase_rfqs_created_at', 'purchase_rfqs', ['created_at'], unique=False)
    op.create_index('ix_purchase_rfqs_purchase_request_id', 'purchase_rfqs', ['purchase_request_id'], unique=False)
    op.create_index('ix_purchase_rfqs_status', 'purchase_rfqs', ['status'], unique=False)

    # 8. Create purchase_rfq_suppliers
    op.create_table('purchase_rfq_suppliers',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('rfq_id', sa.UUID(), nullable=False),
        sa.Column('supplier_id', sa.UUID(), nullable=False),
        sa.Column('contact_email', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='DRAFT'),
        sa.Column('message_subject', sa.String(length=255), nullable=True),
        sa.Column('message_body', sa.Text(), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('response_received_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['rfq_id'], ['purchase_rfqs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_purchase_rfq_suppliers_rfq_id', 'purchase_rfq_suppliers', ['rfq_id'], unique=False)
    op.create_index('ix_purchase_rfq_suppliers_status', 'purchase_rfq_suppliers', ['status'], unique=False)
    op.create_index('ix_purchase_rfq_suppliers_supplier_id', 'purchase_rfq_suppliers', ['supplier_id'], unique=False)

    # 9. Create purchase_quote_responses
    op.create_table('purchase_quote_responses',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('rfq_supplier_id', sa.UUID(), nullable=True),
        sa.Column('supplier_id', sa.UUID(), nullable=False),
        sa.Column('total_amount', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('currency', sa.String(length=10), nullable=False, server_default='BRL'),
        sa.Column('delivery_days', sa.Integer(), nullable=True),
        sa.Column('payment_terms', sa.String(length=255), nullable=True),
        sa.Column('validity_date', sa.DateTime(), nullable=True),
        sa.Column('raw_text', sa.Text(), nullable=True),
        sa.Column('attachment_file_id', sa.String(length=100), nullable=True),
        sa.Column('parsed_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='RECEIVED'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['rfq_supplier_id'], ['purchase_rfq_suppliers.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_purchase_quote_responses_rfq_supplier_id', 'purchase_quote_responses', ['rfq_supplier_id'], unique=False)
    op.create_index('ix_purchase_quote_responses_status', 'purchase_quote_responses', ['status'], unique=False)
    op.create_index('ix_purchase_quote_responses_supplier_id', 'purchase_quote_responses', ['supplier_id'], unique=False)

    # 10. Create purchase_quote_lines
    op.create_table('purchase_quote_lines',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('quote_response_id', sa.UUID(), nullable=False),
        sa.Column('request_item_id', sa.UUID(), nullable=True),
        sa.Column('description', sa.String(length=500), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('unit_price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('total_price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('delivery_days', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['quote_response_id'], ['purchase_quote_responses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['request_item_id'], ['purchase_items.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_purchase_quote_lines_quote_response_id', 'purchase_quote_lines', ['quote_response_id'], unique=False)
    op.create_index('ix_purchase_quote_lines_request_item_id', 'purchase_quote_lines', ['request_item_id'], unique=False)

    # 11. Create purchase_comparisons
    op.create_table('purchase_comparisons',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('rfq_id', sa.UUID(), nullable=False),
        sa.Column('best_supplier_id', sa.UUID(), nullable=True),
        sa.Column('recommendation_summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['best_supplier_id'], ['suppliers.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['rfq_id'], ['purchase_rfqs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_purchase_comparisons_rfq_id', 'purchase_comparisons', ['rfq_id'], unique=True)


def downgrade() -> None:
    op.drop_table('purchase_comparisons')
    op.drop_table('purchase_quote_lines')
    op.drop_table('purchase_quote_responses')
    op.drop_table('purchase_rfq_suppliers')
    op.drop_table('purchase_rfqs')
    op.drop_table('purchase_activities')
    op.drop_table('quotation_items')
    op.drop_table('quotations')
    op.drop_table('purchase_items')
    op.drop_table('purchase_requests')
