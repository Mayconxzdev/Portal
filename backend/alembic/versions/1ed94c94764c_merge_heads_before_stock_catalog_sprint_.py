"""merge heads before stock catalog sprint 1

Revision ID: 1ed94c94764c
Revises: ('e2b7c8d4f2c0', '9d2b6c4e1f30')
Create Date: 2026-06-11 10:30:31.951029

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1ed94c94764c'
down_revision: Union[str, None] = ('e2b7c8d4f2c0', '9d2b6c4e1f30')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
