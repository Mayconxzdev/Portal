"""create_action_command_drafts

Revision ID: b52d9f32b91b
Revises: b7c2d9e4f1a8
Create Date: 2026-06-03 17:31:31.502242

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b52d9f32b91b'
down_revision: Union[str, None] = 'b7c2d9e4f1a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


from sqlalchemy.dialects import postgresql

def upgrade() -> None:
    op.create_table('action_command_drafts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('source_module', sa.String(), nullable=True),
        sa.Column('source_entity_type', sa.String(), nullable=True),
        sa.Column('source_entity_id', sa.String(), nullable=True),
        sa.Column('raw_text', sa.Text(), nullable=True),
        sa.Column('action_key', sa.String(), nullable=False),
        sa.Column('intent_type', sa.String(), nullable=False),
        sa.Column('module', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('extracted_data', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
        sa.Column('enriched_data', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
        sa.Column('missing_fields', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
        sa.Column('preview', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
        sa.Column('risk_level', sa.String(), nullable=False),
        sa.Column('requires_confirmation', sa.Boolean(), nullable=False),
        sa.Column('requires_approval', sa.Boolean(), nullable=False),
        sa.Column('target_action_type', sa.String(), nullable=False),
        sa.Column('created_entity_type', sa.String(), nullable=True),
        sa.Column('created_entity_id', sa.String(), nullable=True),
        sa.Column('action_intent_id', sa.UUID(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('confirmed_at', sa.DateTime(), nullable=True),
        sa.Column('tenant_id', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['action_intent_id'], ['action_intents.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_action_command_drafts_action_intent_id'), 'action_command_drafts', ['action_intent_id'], unique=False)
    op.create_index(op.f('ix_action_command_drafts_action_key'), 'action_command_drafts', ['action_key'], unique=False)
    op.create_index(op.f('ix_action_command_drafts_created_at'), 'action_command_drafts', ['created_at'], unique=False)
    op.create_index(op.f('ix_action_command_drafts_intent_type'), 'action_command_drafts', ['intent_type'], unique=False)
    op.create_index(op.f('ix_action_command_drafts_module'), 'action_command_drafts', ['module'], unique=False)
    op.create_index(op.f('ix_action_command_drafts_risk_level'), 'action_command_drafts', ['risk_level'], unique=False)
    op.create_index(op.f('ix_action_command_drafts_source'), 'action_command_drafts', ['source'], unique=False)
    op.create_index(op.f('ix_action_command_drafts_source_entity_id'), 'action_command_drafts', ['source_entity_id'], unique=False)
    op.create_index(op.f('ix_action_command_drafts_source_entity_type'), 'action_command_drafts', ['source_entity_type'], unique=False)
    op.create_index(op.f('ix_action_command_drafts_source_module'), 'action_command_drafts', ['source_module'], unique=False)
    op.create_index(op.f('ix_action_command_drafts_status'), 'action_command_drafts', ['status'], unique=False)
    op.create_index(op.f('ix_action_command_drafts_user_id'), 'action_command_drafts', ['user_id'], unique=False)

def downgrade() -> None:
    op.drop_table('action_command_drafts')
