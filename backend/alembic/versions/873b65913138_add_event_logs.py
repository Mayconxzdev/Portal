"""add_event_logs

Revision ID: 873b65913138
Revises: ac519e02ab6d
Create Date: 2026-06-02 12:36:59.632253

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '873b65913138'
down_revision: Union[str, None] = 'ac519e02ab6d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    if 'event_logs' not in tables:
        op.create_table(
            'event_logs',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('event_type', sa.String(), nullable=False),
            sa.Column('aggregate_type', sa.String(), nullable=False),
            sa.Column('aggregate_id', sa.String(), nullable=False),
            sa.Column('actor_user_id', sa.Integer(), nullable=True),
            sa.Column('module', sa.String(), nullable=False),
            sa.Column('payload', sa.JSON(), nullable=False),
            sa.Column('metadata_json', sa.JSON(), nullable=False),
            sa.Column('status', sa.String(), nullable=False, server_default='PENDING'),
            sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('last_error', sa.String(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('dispatched_at', sa.DateTime(), nullable=True),
            sa.Column('correlation_id', sa.String(), nullable=True),
            sa.Column('tenant_id', sa.String(), nullable=True),
            sa.ForeignKeyConstraint(['actor_user_id'], ['users.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_event_logs_event_type'), 'event_logs', ['event_type'], unique=False)
        op.create_index(op.f('ix_event_logs_aggregate_type'), 'event_logs', ['aggregate_type'], unique=False)
        op.create_index(op.f('ix_event_logs_aggregate_id'), 'event_logs', ['aggregate_id'], unique=False)
        op.create_index(op.f('ix_event_logs_actor_user_id'), 'event_logs', ['actor_user_id'], unique=False)
        op.create_index(op.f('ix_event_logs_module'), 'event_logs', ['module'], unique=False)
        op.create_index(op.f('ix_event_logs_status'), 'event_logs', ['status'], unique=False)
        op.create_index(op.f('ix_event_logs_created_at'), 'event_logs', ['created_at'], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    if 'event_logs' in tables:
        op.drop_index(op.f('ix_event_logs_created_at'), table_name='event_logs')
        op.drop_index(op.f('ix_event_logs_status'), table_name='event_logs')
        op.drop_index(op.f('ix_event_logs_module'), table_name='event_logs')
        op.drop_index(op.f('ix_event_logs_actor_user_id'), table_name='event_logs')
        op.drop_index(op.f('ix_event_logs_aggregate_id'), table_name='event_logs')
        op.drop_index(op.f('ix_event_logs_aggregate_type'), table_name='event_logs')
        op.drop_index(op.f('ix_event_logs_event_type'), table_name='event_logs')
        op.drop_table('event_logs')
