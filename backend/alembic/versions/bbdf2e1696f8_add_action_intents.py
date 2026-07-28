"""add action intents

Revision ID: bbdf2e1696f8
Revises: 5cde65cfbabd
Create Date: 2026-06-02 14:44:24.491090

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'bbdf2e1696f8'
down_revision: Union[str, None] = '5cde65cfbabd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('action_intents',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('source', sa.String(), nullable=False),
    sa.Column('source_ref_type', sa.String(), nullable=True),
    sa.Column('source_ref_id', sa.String(), nullable=True),
    sa.Column('proposed_action', sa.String(), nullable=False),
    sa.Column('target_module', sa.String(), nullable=False),
    sa.Column('target_type', sa.String(), nullable=True),
    sa.Column('target_id', sa.String(), nullable=True),
    sa.Column('title', sa.String(), nullable=False),
    sa.Column('summary', sa.Text(), nullable=False),
    sa.Column('risk_level', sa.String(), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('action_payload', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('result_payload', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.Column('approval_id', sa.Integer(), nullable=True),
    sa.Column('callback_log_id', sa.UUID(), nullable=True),
    sa.Column('event_id', sa.UUID(), nullable=True),
    sa.Column('created_by_user_id', sa.Integer(), nullable=True),
    sa.Column('reviewed_by_user_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('reviewed_at', sa.DateTime(), nullable=True),
    sa.Column('executed_at', sa.DateTime(), nullable=True),
    sa.Column('expires_at', sa.DateTime(), nullable=True),
    sa.Column('correlation_id', sa.String(), nullable=True),
    sa.Column('tenant_id', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['approval_id'], ['approvals.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['callback_log_id'], ['automation_callback_logs.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['event_id'], ['event_logs.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['reviewed_by_user_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_action_intents_approval_id'), 'action_intents', ['approval_id'], unique=False)
    op.create_index(op.f('ix_action_intents_callback_log_id'), 'action_intents', ['callback_log_id'], unique=False)
    op.create_index(op.f('ix_action_intents_correlation_id'), 'action_intents', ['correlation_id'], unique=False)
    op.create_index(op.f('ix_action_intents_created_at'), 'action_intents', ['created_at'], unique=False)
    op.create_index(op.f('ix_action_intents_proposed_action'), 'action_intents', ['proposed_action'], unique=False)
    op.create_index(op.f('ix_action_intents_risk_level'), 'action_intents', ['risk_level'], unique=False)
    op.create_index(op.f('ix_action_intents_source'), 'action_intents', ['source'], unique=False)
    op.create_index(op.f('ix_action_intents_status'), 'action_intents', ['status'], unique=False)
    op.create_index(op.f('ix_action_intents_target_module'), 'action_intents', ['target_module'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_action_intents_target_module'), table_name='action_intents')
    op.drop_index(op.f('ix_action_intents_status'), table_name='action_intents')
    op.drop_index(op.f('ix_action_intents_source'), table_name='action_intents')
    op.drop_index(op.f('ix_action_intents_risk_level'), table_name='action_intents')
    op.drop_index(op.f('ix_action_intents_proposed_action'), table_name='action_intents')
    op.drop_index(op.f('ix_action_intents_created_at'), table_name='action_intents')
    op.drop_index(op.f('ix_action_intents_correlation_id'), table_name='action_intents')
    op.drop_index(op.f('ix_action_intents_callback_log_id'), table_name='action_intents')
    op.drop_index(op.f('ix_action_intents_approval_id'), table_name='action_intents')
    op.drop_table('action_intents')
