"""create_chat_tables

Revision ID: f1968e682af2
Revises: d2f4a9c8b7e1
Create Date: 2026-05-25 15:29:03.922948

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f1968e682af2'
down_revision: Union[str, None] = 'd2f4a9c8b7e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Tabelas do Módulo de Chat ---
    op.create_table('chat_conversations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('type', sa.String(length=30), nullable=False),
    sa.Column('name', sa.String(length=150), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('is_private', sa.Boolean(), nullable=False),
    sa.Column('is_archived', sa.Boolean(), nullable=False),
    sa.Column('created_by_user_id', sa.Integer(), nullable=False),
    sa.Column('owner_user_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('archived_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['owner_user_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chat_conversations_id'), 'chat_conversations', ['id'], unique=False)

    op.create_table('chat_conversation_members',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('conversation_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('role', sa.String(length=30), nullable=False),
    sa.Column('is_muted', sa.Boolean(), nullable=False),
    sa.Column('joined_at', sa.DateTime(), nullable=False),
    sa.Column('last_read_message_id', sa.Integer(), nullable=True),
    sa.Column('last_read_at', sa.DateTime(), nullable=True),
    sa.Column('notification_level', sa.String(length=30), nullable=False),
    sa.Column('archived_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['conversation_id'], ['chat_conversations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chat_conversation_members_conversation_id'), 'chat_conversation_members', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_chat_conversation_members_id'), 'chat_conversation_members', ['id'], unique=False)
    op.create_index(op.f('ix_chat_conversation_members_user_id'), 'chat_conversation_members', ['user_id'], unique=False)

    op.create_table('chat_messages',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('conversation_id', sa.Integer(), nullable=False),
    sa.Column('sender_user_id', sa.Integer(), nullable=False),
    sa.Column('parent_message_id', sa.Integer(), nullable=True),
    sa.Column('message_type', sa.String(length=30), nullable=False),
    sa.Column('body', sa.Text(), nullable=True),
    sa.Column('body_search', sa.Text(), nullable=True),
    sa.Column('is_edited', sa.Boolean(), nullable=False),
    sa.Column('is_deleted', sa.Boolean(), nullable=False),
    sa.Column('is_pinned', sa.Boolean(), nullable=False),
    sa.Column('is_ephemeral', sa.Boolean(), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=True),
    sa.Column('reply_count', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.Column('deleted_by_user_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['conversation_id'], ['chat_conversations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['deleted_by_user_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['parent_message_id'], ['chat_messages.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['sender_user_id'], ['users.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chat_messages_conversation_id'), 'chat_messages', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_chat_messages_created_at'), 'chat_messages', ['created_at'], unique=False)
    op.create_index(op.f('ix_chat_messages_id'), 'chat_messages', ['id'], unique=False)
    op.create_index(op.f('ix_chat_messages_sender_user_id'), 'chat_messages', ['sender_user_id'], unique=False)

    op.create_table('chat_notification_settings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('conversation_id', sa.Integer(), nullable=True),
    sa.Column('global_level', sa.String(length=30), nullable=False),
    sa.Column('muted_until', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['conversation_id'], ['chat_conversations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chat_notification_settings_conversation_id'), 'chat_notification_settings', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_chat_notification_settings_id'), 'chat_notification_settings', ['id'], unique=False)
    op.create_index(op.f('ix_chat_notification_settings_user_id'), 'chat_notification_settings', ['user_id'], unique=False)

    op.create_table('chat_activity',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('conversation_id', sa.Integer(), nullable=True),
    sa.Column('message_id', sa.Integer(), nullable=True),
    sa.Column('actor_user_id', sa.Integer(), nullable=True),
    sa.Column('action', sa.String(length=100), nullable=False),
    sa.Column('metadata', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['actor_user_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['conversation_id'], ['chat_conversations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['message_id'], ['chat_messages.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chat_activity_actor_user_id'), 'chat_activity', ['actor_user_id'], unique=False)
    op.create_index(op.f('ix_chat_activity_conversation_id'), 'chat_activity', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_chat_activity_id'), 'chat_activity', ['id'], unique=False)
    op.create_index(op.f('ix_chat_activity_message_id'), 'chat_activity', ['message_id'], unique=False)

    op.create_table('chat_conversation_links',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('conversation_id', sa.Integer(), nullable=True),
    sa.Column('message_id', sa.Integer(), nullable=True),
    sa.Column('module_slug', sa.String(length=50), nullable=False),
    sa.Column('entity_type', sa.String(length=50), nullable=False),
    sa.Column('entity_id', sa.Integer(), nullable=False),
    sa.Column('created_by_user_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['conversation_id'], ['chat_conversations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['message_id'], ['chat_messages.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chat_conversation_links_conversation_id'), 'chat_conversation_links', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_chat_conversation_links_id'), 'chat_conversation_links', ['id'], unique=False)
    op.create_index(op.f('ix_chat_conversation_links_message_id'), 'chat_conversation_links', ['message_id'], unique=False)

    op.create_table('chat_mentions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('message_id', sa.Integer(), nullable=False),
    sa.Column('mention_type', sa.String(length=30), nullable=False),
    sa.Column('target_id', sa.Integer(), nullable=True),
    sa.Column('target_slug', sa.String(length=100), nullable=True),
    sa.Column('display_label', sa.String(length=150), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['message_id'], ['chat_messages.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chat_mentions_id'), 'chat_mentions', ['id'], unique=False)
    op.create_index(op.f('ix_chat_mentions_message_id'), 'chat_mentions', ['message_id'], unique=False)

    op.create_table('chat_message_attachments',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('message_id', sa.Integer(), nullable=False),
    sa.Column('file_id', sa.Integer(), nullable=False),
    sa.Column('attachment_type', sa.String(length=30), nullable=False),
    sa.Column('uploaded_by_user_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['file_id'], ['files.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['message_id'], ['chat_messages.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['uploaded_by_user_id'], ['users.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chat_message_attachments_file_id'), 'chat_message_attachments', ['file_id'], unique=False)
    op.create_index(op.f('ix_chat_message_attachments_id'), 'chat_message_attachments', ['id'], unique=False)
    op.create_index(op.f('ix_chat_message_attachments_message_id'), 'chat_message_attachments', ['message_id'], unique=False)

    op.create_table('chat_message_versions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('message_id', sa.Integer(), nullable=False),
    sa.Column('previous_body', sa.Text(), nullable=False),
    sa.Column('new_body', sa.Text(), nullable=False),
    sa.Column('edited_by_user_id', sa.Integer(), nullable=False),
    sa.Column('edited_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['edited_by_user_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['message_id'], ['chat_messages.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chat_message_versions_id'), 'chat_message_versions', ['id'], unique=False)
    op.create_index(op.f('ix_chat_message_versions_message_id'), 'chat_message_versions', ['message_id'], unique=False)

    op.create_table('chat_messias_audit',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('messias_user_id', sa.Integer(), nullable=False),
    sa.Column('action', sa.String(length=100), nullable=False),
    sa.Column('target_user_id', sa.Integer(), nullable=True),
    sa.Column('conversation_id', sa.Integer(), nullable=True),
    sa.Column('message_id', sa.Integer(), nullable=True),
    sa.Column('metadata', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['conversation_id'], ['chat_conversations.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['message_id'], ['chat_messages.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['messias_user_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['target_user_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chat_messias_audit_id'), 'chat_messias_audit', ['id'], unique=False)
    op.create_index(op.f('ix_chat_messias_audit_messias_user_id'), 'chat_messias_audit', ['messias_user_id'], unique=False)

    op.create_table('chat_pins',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('conversation_id', sa.Integer(), nullable=False),
    sa.Column('message_id', sa.Integer(), nullable=False),
    sa.Column('pinned_by_user_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['conversation_id'], ['chat_conversations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['message_id'], ['chat_messages.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['pinned_by_user_id'], ['users.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chat_pins_conversation_id'), 'chat_pins', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_chat_pins_id'), 'chat_pins', ['id'], unique=False)
    op.create_index(op.f('ix_chat_pins_message_id'), 'chat_pins', ['message_id'], unique=False)

    op.create_table('chat_reactions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('message_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('emoji', sa.String(length=50), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['message_id'], ['chat_messages.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('message_id', 'user_id', 'emoji', name='uq_chat_message_user_reaction')
    )
    op.create_index(op.f('ix_chat_reactions_id'), 'chat_reactions', ['id'], unique=False)
    op.create_index(op.f('ix_chat_reactions_message_id'), 'chat_reactions', ['message_id'], unique=False)
    op.create_index(op.f('ix_chat_reactions_user_id'), 'chat_reactions', ['user_id'], unique=False)

    op.create_table('chat_read_receipts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('message_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('read_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['message_id'], ['chat_messages.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chat_read_receipts_id'), 'chat_read_receipts', ['id'], unique=False)
    op.create_index(op.f('ix_chat_read_receipts_message_id'), 'chat_read_receipts', ['message_id'], unique=False)
    op.create_index(op.f('ix_chat_read_receipts_user_id'), 'chat_read_receipts', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_table('chat_read_receipts')
    op.drop_table('chat_reactions')
    op.drop_table('chat_pins')
    op.drop_table('chat_messias_audit')
    op.drop_table('chat_message_versions')
    op.drop_table('chat_message_attachments')
    op.drop_table('chat_mentions')
    op.drop_table('chat_conversation_links')
    op.drop_table('chat_activity')
    op.drop_table('chat_notification_settings')
    op.drop_table('chat_messages')
    op.drop_table('chat_conversation_members')
    op.drop_table('chat_conversations')
