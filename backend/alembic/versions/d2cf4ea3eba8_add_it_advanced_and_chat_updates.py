"""add_it_advanced_and_chat_updates

Revision ID: d2cf4ea3eba8
Revises: f1968e682af2
Create Date: 2026-05-25 16:33:51.883971

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd2cf4ea3eba8'
down_revision: Union[str, None] = 'f1968e682af2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Criação das novas tabelas
    op.create_table('it_asset_custom_fields',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('field_type', sa.String(length=30), nullable=False),
        sa.Column('options', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_it_asset_custom_fields_id'), 'it_asset_custom_fields', ['id'], unique=False)

    op.create_table('it_change_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('field_name', sa.String(length=100), nullable=True),
        sa.Column('old_value', sa.Text(), nullable=True),
        sa.Column('new_value', sa.Text(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=50), nullable=True),
        sa.Column('origin', sa.String(length=30), nullable=False, server_default='MANUAL'),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_it_change_logs_id'), 'it_change_logs', ['id'], unique=False)

    op.create_table('it_nas_folders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('network_path', sa.String(length=255), nullable=True),
        sa.Column('drive_letter', sa.String(length=5), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('permission_level', sa.String(length=30), nullable=False, server_default='LEITURA'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_it_nas_folders_id'), 'it_nas_folders', ['id'], unique=False)

    op.create_table('it_notes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=150), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('color', sa.String(length=30), nullable=False, server_default='yellow'),
        sa.Column('tags', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True),
        sa.Column('responsible_user_id', sa.Integer(), nullable=True),
        sa.Column('is_pinned', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_archived', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_by_user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['responsible_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_it_notes_id'), 'it_notes', ['id'], unique=False)

    op.create_table('it_corporate_emails',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email_address', sa.String(length=180), nullable=False),
        sa.Column('login', sa.String(length=100), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('server_config', sa.Text(), nullable=True),
        sa.Column('recommended_client', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='ATIVO'),
        sa.Column('credential_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['credential_id'], ['it_credentials_vault.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_it_corporate_emails_email_address'), 'it_corporate_emails', ['email_address'], unique=True)
    op.create_index(op.f('ix_it_corporate_emails_id'), 'it_corporate_emails', ['id'], unique=False)

    op.create_table('chat_message_deletes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('message_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['message_id'], ['chat_messages.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chat_message_deletes_id'), 'chat_message_deletes', ['id'], unique=False)
    op.create_index(op.f('ix_chat_message_deletes_message_id'), 'chat_message_deletes', ['message_id'], unique=False)
    op.create_index(op.f('ix_chat_message_deletes_user_id'), 'chat_message_deletes', ['user_id'], unique=False)

    # 2. Adição de novas colunas em chat_messages
    op.add_column('chat_messages', sa.Column('visibility_mode', sa.String(length=30), nullable=False, server_default='COMMON'))
    op.add_column('chat_messages', sa.Column('viewed_by_users', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True))

    # 3. Adição de novas colunas em it_assets
    op.add_column('it_assets', sa.Column('hostname', sa.String(length=100), nullable=True))
    op.add_column('it_assets', sa.Column('processor', sa.String(length=150), nullable=True))
    op.add_column('it_assets', sa.Column('ram', sa.String(length=100), nullable=True))
    op.add_column('it_assets', sa.Column('motherboard', sa.String(length=150), nullable=True))
    op.add_column('it_assets', sa.Column('gpu', sa.String(length=150), nullable=True))
    op.add_column('it_assets', sa.Column('network_card', sa.String(length=150), nullable=True))
    op.add_column('it_assets', sa.Column('power_supply', sa.String(length=100), nullable=True))
    op.add_column('it_assets', sa.Column('cabinet', sa.String(length=100), nullable=True))
    op.add_column('it_assets', sa.Column('monitor', sa.String(length=150), nullable=True))
    op.add_column('it_assets', sa.Column('mouse', sa.String(length=150), nullable=True))
    op.add_column('it_assets', sa.Column('mouse_pad', sa.String(length=150), nullable=True))
    op.add_column('it_assets', sa.Column('keyboard', sa.String(length=150), nullable=True))
    op.add_column('it_assets', sa.Column('storage', sa.Text(), nullable=True))
    op.add_column('it_assets', sa.Column('peripherals', sa.Text(), nullable=True))
    op.add_column('it_assets', sa.Column('ip_address', sa.String(length=50), nullable=True))
    op.add_column('it_assets', sa.Column('ramal', sa.String(length=50), nullable=True))
    op.add_column('it_assets', sa.Column('network_point', sa.String(length=100), nullable=True))
    op.add_column('it_assets', sa.Column('sector', sa.String(length=100), nullable=True))
    op.add_column('it_assets', sa.Column('it_responsible', sa.String(length=100), nullable=True))
    op.add_column('it_assets', sa.Column('last_collection_source', sa.String(length=50), nullable=True))
    op.add_column('it_assets', sa.Column('last_collection_at', sa.DateTime(), nullable=True))
    op.add_column('it_assets', sa.Column('custom_fields', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True))


def downgrade() -> None:
    # 1. Remoção de colunas de it_assets
    op.drop_column('it_assets', 'custom_fields')
    op.drop_column('it_assets', 'last_collection_at')
    op.drop_column('it_assets', 'last_collection_source')
    op.drop_column('it_assets', 'it_responsible')
    op.drop_column('it_assets', 'sector')
    op.drop_column('it_assets', 'network_point')
    op.drop_column('it_assets', 'ramal')
    op.drop_column('it_assets', 'ip_address')
    op.drop_column('it_assets', 'peripherals')
    op.drop_column('it_assets', 'storage')
    op.drop_column('it_assets', 'keyboard')
    op.drop_column('it_assets', 'mouse_pad')
    op.drop_column('it_assets', 'mouse')
    op.drop_column('it_assets', 'monitor')
    op.drop_column('it_assets', 'cabinet')
    op.drop_column('it_assets', 'power_supply')
    op.drop_column('it_assets', 'network_card')
    op.drop_column('it_assets', 'gpu')
    op.drop_column('it_assets', 'motherboard')
    op.drop_column('it_assets', 'ram')
    op.drop_column('it_assets', 'processor')
    op.drop_column('it_assets', 'hostname')

    # 2. Remoção de colunas de chat_messages
    op.drop_column('chat_messages', 'viewed_by_users')
    op.drop_column('chat_messages', 'visibility_mode')

    # 3. Remoção de tabelas
    op.drop_index(op.f('ix_chat_message_deletes_user_id'), table_name='chat_message_deletes')
    op.drop_index(op.f('ix_chat_message_deletes_message_id'), table_name='chat_message_deletes')
    op.drop_index(op.f('ix_chat_message_deletes_id'), table_name='chat_message_deletes')
    op.drop_table('chat_message_deletes')

    op.drop_index(op.f('ix_it_corporate_emails_id'), table_name='it_corporate_emails')
    op.drop_index(op.f('ix_it_corporate_emails_email_address'), table_name='it_corporate_emails')
    op.drop_table('it_corporate_emails')

    op.drop_index(op.f('ix_it_notes_id'), table_name='it_notes')
    op.drop_table('it_notes')

    op.drop_index(op.f('ix_it_nas_folders_id'), table_name='it_nas_folders')
    op.drop_table('it_nas_folders')

    op.drop_index(op.f('ix_it_change_logs_id'), table_name='it_change_logs')
    op.drop_table('it_change_logs')

    op.drop_index(op.f('ix_it_asset_custom_fields_id'), table_name='it_asset_custom_fields')
    op.drop_table('it_asset_custom_fields')
