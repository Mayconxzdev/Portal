"""fase4.1 it schema reconcile

Revision ID: d2f4a9c8b7e1
Revises: c1e7a8d4f2b9
Create Date: 2026-05-25
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d2f4a9c8b7e1"
down_revision: Union[str, None] = "c1e7a8d4f2b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return

    statements = [
        "ALTER TABLE IF EXISTS it_ticket_comments ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL",
        "ALTER TABLE IF EXISTS it_ticket_comments ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP",
        "ALTER TABLE IF EXISTS it_ticket_checklist_items ADD COLUMN IF NOT EXISTS created_by_user_id INTEGER REFERENCES users(id)",
        "ALTER TABLE IF EXISTS it_ticket_checklist_items ADD COLUMN IF NOT EXISTS completed_by_user_id INTEGER REFERENCES users(id)",
        "ALTER TABLE IF EXISTS it_ticket_checklist_items ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP",
        "ALTER TABLE IF EXISTS it_ticket_checklist_items ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL",
    ]
    for statement in statements:
        op.execute(sa.text(statement))


def downgrade() -> None:
    pass
