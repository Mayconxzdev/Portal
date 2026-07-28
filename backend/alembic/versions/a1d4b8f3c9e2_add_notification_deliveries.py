"""add_notification_deliveries

Revision ID: a1d4b8f3c9e2
Revises: 51c73b706d71
Create Date: 2026-06-02 21:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1d4b8f3c9e2'
down_revision: Union[str, None] = '51c73b706d71'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table('notification_deliveries'):
        op.create_table(
            'notification_deliveries',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('notification_id', sa.UUID(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('status', sa.String(), nullable=False),
            sa.Column('delivered_at', sa.DateTime(), nullable=False),
            sa.Column('read_at', sa.DateTime(), nullable=True),
            sa.Column('archived_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('tenant_id', sa.String(), nullable=True),
            sa.ForeignKeyConstraint(['notification_id'], ['notifications.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('notification_id', 'user_id', name='uq_notification_delivery_notification_user'),
        )

    existing_indexes = {index['name'] for index in inspector.get_indexes('notification_deliveries')}
    indexes = [
        ('ix_notification_deliveries_created_at', ['created_at']),
        ('ix_notification_deliveries_notification_id', ['notification_id']),
        ('ix_notification_deliveries_status', ['status']),
        ('ix_notification_deliveries_user_id', ['user_id']),
    ]
    for index_name, columns in indexes:
        if index_name not in existing_indexes:
            op.create_index(index_name, 'notification_deliveries', columns, unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_notification_deliveries_user_id'), table_name='notification_deliveries')
    op.drop_index(op.f('ix_notification_deliveries_status'), table_name='notification_deliveries')
    op.drop_index(op.f('ix_notification_deliveries_notification_id'), table_name='notification_deliveries')
    op.drop_index(op.f('ix_notification_deliveries_created_at'), table_name='notification_deliveries')
    op.drop_table('notification_deliveries')
