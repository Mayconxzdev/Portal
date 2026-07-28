"""add_master_data_foundation

Revision ID: ab49968d9285
Revises: 3271c0e19dcc
Create Date: 2026-06-03 11:47:16.753045

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'ab49968d9285'
down_revision: Union[str, None] = '3271c0e19dcc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Tabela central de Pessoas (people)
    op.create_table(
        'people',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('legal_name', sa.String(length=255), nullable=True),
        sa.Column('document_type', sa.String(length=50), nullable=True),
        sa.Column('document_number', sa.String(length=50), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('tenant_id', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_people_document_number', 'people', ['document_number'], unique=True)
    op.create_index('ix_people_email', 'people', ['email'], unique=False)
    op.create_index('ix_people_is_active', 'people', ['is_active'], unique=False)

    # 2. Tabela de Endereços (person_addresses)
    op.create_table(
        'person_addresses',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('person_id', sa.UUID(), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False, server_default='MAIN'),
        sa.Column('street', sa.String(length=255), nullable=False),
        sa.Column('number', sa.String(length=50), nullable=False),
        sa.Column('complement', sa.String(length=255), nullable=True),
        sa.Column('district', sa.String(length=100), nullable=False),
        sa.Column('city', sa.String(length=100), nullable=False),
        sa.Column('state', sa.String(length=50), nullable=False),
        sa.Column('zip_code', sa.String(length=30), nullable=False),
        sa.Column('country', sa.String(length=100), nullable=False, server_default='Brasil'),
        sa.ForeignKeyConstraint(['person_id'], ['people.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_person_addresses_person_id', 'person_addresses', ['person_id'], unique=False)

    # 3. Tabela de Contatos (person_contacts)
    op.create_table(
        'person_contacts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('person_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=100), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('whatsapp', sa.String(length=50), nullable=True),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.ForeignKeyConstraint(['person_id'], ['people.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_person_contacts_person_id', 'person_contacts', ['person_id'], unique=False)

    # 4. Tabela de Clientes (customers)
    op.create_table(
        'customers',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('person_id', sa.UUID(), nullable=False),
        sa.Column('customer_code', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='ACTIVE'),
        sa.Column('default_payment_terms', sa.String(length=255), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['person_id'], ['people.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_customers_person_id', 'customers', ['person_id'], unique=True)
    op.create_index('ix_customers_customer_code', 'customers', ['customer_code'], unique=True)
    op.create_index('ix_customers_status', 'customers', ['status'], unique=False)

    # 5. Tabela de Fornecedores (suppliers) com UUID
    op.create_table(
        'suppliers',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('person_id', sa.UUID(), nullable=False),
        sa.Column('supplier_code', sa.String(length=50), nullable=True),
        sa.Column('categories', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('preferred_contact_email', sa.String(length=255), nullable=True),
        sa.Column('rating', sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='ACTIVE'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['person_id'], ['people.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_suppliers_person_id', 'suppliers', ['person_id'], unique=True)
    op.create_index('ix_suppliers_supplier_code', 'suppliers', ['supplier_code'], unique=True)
    op.create_index('ix_suppliers_status', 'suppliers', ['status'], unique=False)

    # 6. Tabela de Produtos / Itens (product_items)
    op.create_table(
        'product_items',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('sku', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('item_type', sa.String(length=50), nullable=False),
        sa.Column('unit_of_measure', sa.String(length=30), nullable=False, server_default='un'),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('ncm', sa.String(length=20), nullable=True),
        sa.Column('barcode', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_product_items_sku', 'product_items', ['sku'], unique=True)
    op.create_index('ix_product_items_is_active', 'product_items', ['is_active'], unique=False)

    # 7. Tabela de Serviços (services)
    op.create_table(
        'services',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('code', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('default_price', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_services_code', 'services', ['code'], unique=True)
    op.create_index('ix_services_is_active', 'services', ['is_active'], unique=False)

    # 8. Tabela de Requisições de Compra (purchase_requests)
    op.create_table(
        'purchase_requests',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('justification', sa.Text(), nullable=True),
        sa.Column('requester_user_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='DRAFT'),
        sa.Column('urgency', sa.String(length=20), nullable=False, server_default='NORMAL'),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('estimated_total', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('approved_total', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('needed_by', sa.DateTime(), nullable=True),
        sa.Column('approval_id', sa.Integer(), nullable=True),
        sa.Column('selected_quotation_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['requester_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['approval_id'], ['approvals.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_purchase_requests_requester_user_id', 'purchase_requests', ['requester_user_id'], unique=False)
    op.create_index('ix_purchase_requests_status', 'purchase_requests', ['status'], unique=False)
    op.create_index('ix_purchase_requests_approval_id', 'purchase_requests', ['approval_id'], unique=False)

    # 9. Tabela de Itens da Requisição (purchase_items)
    op.create_table(
        'purchase_items',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('purchase_request_id', sa.Integer(), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=10, scale=2), nullable=False, server_default='1'),
        sa.Column('unit', sa.String(length=30), nullable=False, server_default='un'),
        sa.Column('estimated_unit_price', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['purchase_request_id'], ['purchase_requests.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_purchase_items_purchase_request_id', 'purchase_items', ['purchase_request_id'], unique=False)

    # 10. Tabela de Cotações (quotations) vinculada ao Fornecedor por UUID
    op.create_table(
        'quotations',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('purchase_request_id', sa.Integer(), nullable=False),
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
    op.create_index('ix_quotations_purchase_request_id', 'quotations', ['purchase_request_id'], unique=False)
    op.create_index('ix_quotations_supplier_id', 'quotations', ['supplier_id'], unique=False)
    op.create_index('ix_quotations_status', 'quotations', ['status'], unique=False)

    # 11. Tabela de Itens da Cotação (quotation_items)
    op.create_table(
        'quotation_items',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('quotation_id', sa.Integer(), nullable=False),
        sa.Column('purchase_item_id', sa.Integer(), nullable=False),
        sa.Column('quoted_unit_price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('delivery_days', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['quotation_id'], ['quotations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['purchase_item_id'], ['purchase_items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_quotation_items_quotation_id', 'quotation_items', ['quotation_id'], unique=False)
    op.create_index('ix_quotation_items_purchase_item_id', 'quotation_items', ['purchase_item_id'], unique=False)

    # 12. Tabela de Log de Atividades de Compras (purchase_activities)
    op.create_table(
        'purchase_activities',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('purchase_request_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['purchase_request_id'], ['purchase_requests.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_purchase_activities_purchase_request_id', 'purchase_activities', ['purchase_request_id'], unique=False)
    op.create_index('ix_purchase_activities_action', 'purchase_activities', ['action'], unique=False)


def downgrade() -> None:
    # Remove tabelas na ordem inversa de dependência
    op.drop_table('purchase_activities')
    op.drop_table('quotation_items')
    op.drop_table('quotations')
    op.drop_table('purchase_items')
    op.drop_table('purchase_requests')
    op.drop_table('services')
    op.drop_table('product_items')
    op.drop_table('suppliers')
    op.drop_table('customers')
    op.drop_table('person_contacts')
    op.drop_table('person_addresses')
    op.drop_table('people')
