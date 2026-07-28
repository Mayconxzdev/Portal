"""Sprint 0 head compatibility marker.

Revision ID: f6c7c8d4f2b9
Revises: d2cf4ea3eba8
Create Date: 2026-06-01
"""

from typing import Sequence, Union

from alembic import op


revision: str = "f6c7c8d4f2b9"
down_revision: Union[str, None] = "d2cf4ea3eba8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Compatibility marker for local databases already stamped at this head.
    pass


def downgrade() -> None:
    pass
