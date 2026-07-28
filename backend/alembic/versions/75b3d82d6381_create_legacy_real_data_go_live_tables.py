"""create_legacy_real_data_go_live_tables

Revision ID: 75b3d82d6381
Revises: e3d1f205e393
Create Date: 2026-06-05 09:16:37.870698

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '75b3d82d6381'
down_revision: Union[str, None] = 'e3d1f205e393'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. it_systems
    op.create_table('it_systems',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_it_systems_id'), 'it_systems', ['id'], unique=False)
    op.create_index(op.f('ix_it_systems_name'), 'it_systems', ['name'], unique=True)

    # 2. it_access_records
    op.create_table('it_access_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('person_id', sa.UUID(), nullable=True),
        sa.Column('legacy_user_name', sa.String(length=150), nullable=True),
        sa.Column('system_id', sa.Integer(), nullable=True),
        sa.Column('system_name', sa.String(length=100), nullable=False),
        sa.Column('access_profile', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('origin', sa.String(length=50), nullable=False),
        sa.Column('has_secret', sa.Boolean(), nullable=False),
        sa.Column('last_updated_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['person_id'], ['people.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['system_id'], ['it_systems.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_it_access_records_id'), 'it_access_records', ['id'], unique=False)

    # 3. legacy_entity_links
    op.create_table('legacy_entity_links',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('legacy_row_id', sa.UUID(), nullable=True),
        sa.Column('source_app', sa.String(length=50), nullable=False),
        sa.Column('entity_target', sa.String(length=100), nullable=False),
        sa.Column('official_entity_type', sa.String(length=100), nullable=False),
        sa.Column('official_entity_id', sa.String(length=100), nullable=False),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_legacy_entity_links_legacy_row_id'), 'legacy_entity_links', ['legacy_row_id'], unique=False)
    op.create_index(op.f('ix_legacy_entity_links_source_app'), 'legacy_entity_links', ['source_app'], unique=False)
    op.create_index(op.f('ix_legacy_entity_links_entity_target'), 'legacy_entity_links', ['entity_target'], unique=False)

    # 4. legacy_operational_records
    op.create_table('legacy_operational_records',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('legacy_row_id', sa.UUID(), nullable=True),
        sa.Column('source_app', sa.String(length=50), nullable=False),
        sa.Column('entity_target', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('responsible', sa.String(length=150), nullable=True),
        sa.Column('record_date', sa.DateTime(), nullable=True),
        sa.Column('data_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_legacy_operational_records_legacy_row_id'), 'legacy_operational_records', ['legacy_row_id'], unique=False)
    op.create_index(op.f('ix_legacy_operational_records_source_app'), 'legacy_operational_records', ['source_app'], unique=False)
    op.create_index(op.f('ix_legacy_operational_records_status'), 'legacy_operational_records', ['status'], unique=False)

    # 5. legacy_file_index
    op.create_table('legacy_file_index',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('legacy_row_id', sa.UUID(), nullable=True),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('file_path_masked', sa.String(length=500), nullable=False),
        sa.Column('file_type', sa.String(length=30), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('suggested_module', sa.String(length=100), nullable=True),
        sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_legacy_file_index_legacy_row_id'), 'legacy_file_index', ['legacy_row_id'], unique=False)
    op.create_index(op.f('ix_legacy_file_index_file_type'), 'legacy_file_index', ['file_type'], unique=False)
    op.create_index(op.f('ix_legacy_file_index_category'), 'legacy_file_index', ['category'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_legacy_file_index_category'), table_name='legacy_file_index')
    op.drop_index(op.f('ix_legacy_file_index_file_type'), table_name='legacy_file_index')
    op.drop_index(op.f('ix_legacy_file_index_legacy_row_id'), table_name='legacy_file_index')
    op.drop_table('legacy_file_index')

    op.drop_index(op.f('ix_legacy_operational_records_status'), table_name='legacy_operational_records')
    op.drop_index(op.f('ix_legacy_operational_records_source_app'), table_name='legacy_operational_records')
    op.drop_index(op.f('ix_legacy_operational_records_legacy_row_id'), table_name='legacy_operational_records')
    op.drop_table('legacy_operational_records')

    op.drop_index(op.f('ix_legacy_entity_links_entity_target'), table_name='legacy_entity_links')
    op.drop_index(op.f('ix_legacy_entity_links_source_app'), table_name='legacy_entity_links')
    op.drop_index(op.f('ix_legacy_entity_links_legacy_row_id'), table_name='legacy_entity_links')
    op.drop_table('legacy_entity_links')

    op.drop_index(op.f('ix_it_access_records_id'), table_name='it_access_records')
    op.drop_table('it_access_records')

    op.drop_index(op.f('ix_it_systems_name'), table_name='it_systems')
    op.drop_index(op.f('ix_it_systems_id'), table_name='it_systems')
    op.drop_table('it_systems')
