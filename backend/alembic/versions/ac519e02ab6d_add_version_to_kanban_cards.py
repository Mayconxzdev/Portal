"""add_version_to_kanban_cards

Revision ID: ac519e02ab6d
Revises: f6c7c8d4f2b9
Create Date: 2026-06-02 09:04:58.695393

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ac519e02ab6d'
down_revision: Union[str, None] = 'f6c7c8d4f2b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Adiciona a coluna version à tabela kanban_cards com valor inicial default = 1
    op.add_column('kanban_cards', sa.Column('version', sa.Integer(), nullable=False, server_default='1'))


def downgrade() -> None:
    # Remove a coluna version da tabela kanban_cards
    op.drop_column('kanban_cards', 'version')
