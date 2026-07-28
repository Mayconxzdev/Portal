"""add_reaction_rules_and_runs

Revision ID: 3271c0e19dcc
Revises: a1d4b8f3c9e2
Create Date: 2026-06-03 11:07:18.142487

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '3271c0e19dcc'
down_revision: Union[str, None] = 'a1d4b8f3c9e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Criação da tabela reaction_rules
    if not inspector.has_table('reaction_rules'):
        op.create_table('reaction_rules',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('module', sa.String(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('condition_json', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
        sa.Column('action_type', sa.String(), nullable=False),
        sa.Column('action_payload', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
        sa.Column('cooldown_seconds', sa.Integer(), nullable=True),
        sa.Column('max_runs_per_hour', sa.Integer(), nullable=True),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_reaction_rules_created_at'), 'reaction_rules', ['created_at'], unique=False)
        op.create_index(op.f('ix_reaction_rules_created_by_user_id'), 'reaction_rules', ['created_by_user_id'], unique=False)
        op.create_index(op.f('ix_reaction_rules_enabled'), 'reaction_rules', ['enabled'], unique=False)
        op.create_index(op.f('ix_reaction_rules_event_type'), 'reaction_rules', ['event_type'], unique=False)
        op.create_index(op.f('ix_reaction_rules_module'), 'reaction_rules', ['module'], unique=False)
    
    # Criação da tabela reaction_rule_runs
    if not inspector.has_table('reaction_rule_runs'):
        op.create_table('reaction_rule_runs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('rule_id', sa.UUID(), nullable=False),
        sa.Column('event_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('condition_result', sa.Boolean(), nullable=False),
        sa.Column('action_result', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('executed_at', sa.DateTime(), nullable=True),
        sa.Column('correlation_id', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['rule_id'], ['reaction_rules.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_reaction_rule_runs_correlation_id'), 'reaction_rule_runs', ['correlation_id'], unique=False)
        op.create_index(op.f('ix_reaction_rule_runs_created_at'), 'reaction_rule_runs', ['created_at'], unique=False)
        op.create_index(op.f('ix_reaction_rule_runs_event_id'), 'reaction_rule_runs', ['event_id'], unique=False)
        op.create_index(op.f('ix_reaction_rule_runs_rule_id'), 'reaction_rule_runs', ['rule_id'], unique=False)
        op.create_index(op.f('ix_reaction_rule_runs_status'), 'reaction_rule_runs', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_reaction_rule_runs_status'), table_name='reaction_rule_runs')
    op.drop_index(op.f('ix_reaction_rule_runs_rule_id'), table_name='reaction_rule_runs')
    op.drop_index(op.f('ix_reaction_rule_runs_event_id'), table_name='reaction_rule_runs')
    op.drop_index(op.f('ix_reaction_rule_runs_created_at'), table_name='reaction_rule_runs')
    op.drop_index(op.f('ix_reaction_rule_runs_correlation_id'), table_name='reaction_rule_runs')
    op.drop_table('reaction_rule_runs')
    
    op.drop_index(op.f('ix_reaction_rules_module'), table_name='reaction_rules')
    op.drop_index(op.f('ix_reaction_rules_event_type'), table_name='reaction_rules')
    op.drop_index(op.f('ix_reaction_rules_enabled'), table_name='reaction_rules')
    op.drop_index(op.f('ix_reaction_rules_created_by_user_id'), table_name='reaction_rules')
    op.drop_index(op.f('ix_reaction_rules_created_at'), table_name='reaction_rules')
    op.drop_table('reaction_rules')
