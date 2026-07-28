"""add_action_intent_executions

Revision ID: 9f19de8798a1
Revises: bbdf2e1696f8
Create Date: 2026-06-02 15:07:48.614073

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9f19de8798a1'
down_revision: Union[str, None] = 'bbdf2e1696f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('action_intent_executions',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('action_intent_id', sa.UUID(), nullable=False),
    sa.Column('executor_key', sa.String(), nullable=False),
    sa.Column('idempotency_key', sa.String(), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('started_at', sa.DateTime(), nullable=True),
    sa.Column('finished_at', sa.DateTime(), nullable=True),
    sa.Column('attempts', sa.Integer(), nullable=False),
    sa.Column('input_payload', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True),
    sa.Column('result_payload', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('created_by_user_id', sa.Integer(), nullable=True),
    sa.Column('correlation_id', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['action_intent_id'], ['action_intents.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_action_intent_executions_action_intent_id'), 'action_intent_executions', ['action_intent_id'], unique=False)
    op.create_index(op.f('ix_action_intent_executions_idempotency_key'), 'action_intent_executions', ['idempotency_key'], unique=True)
    op.create_index(op.f('ix_action_intent_executions_status'), 'action_intent_executions', ['status'], unique=False)
    op.create_index(op.f('ix_action_intent_executions_correlation_id'), 'action_intent_executions', ['correlation_id'], unique=False)
    op.create_index(op.f('ix_action_intent_executions_created_at'), 'action_intent_executions', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_action_intent_executions_created_at'), table_name='action_intent_executions')
    op.drop_index(op.f('ix_action_intent_executions_correlation_id'), table_name='action_intent_executions')
    op.drop_index(op.f('ix_action_intent_executions_status'), table_name='action_intent_executions')
    op.drop_index(op.f('ix_action_intent_executions_idempotency_key'), table_name='action_intent_executions')
    op.drop_index(op.f('ix_action_intent_executions_action_intent_id'), table_name='action_intent_executions')
    op.drop_table('action_intent_executions')

