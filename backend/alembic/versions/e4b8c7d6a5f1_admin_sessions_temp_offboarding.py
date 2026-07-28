"""admin sessions temporary access offboarding

Revision ID: e4b8c7d6a5f1
Revises: d9a7c3e5f1b2
Create Date: 2026-06-17 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "e4b8c7d6a5f1"
down_revision: Union[str, None] = "d9a7c3e5f1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


json_type = postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")


def _table_exists(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def _index_exists(table_name: str, index_name: str) -> bool:
    indexes = sa.inspect(op.get_bind()).get_indexes(table_name)
    return any(index["name"] == index_name for index in indexes)


def _create_index_if_missing(index_name: str, table_name: str, columns: list[str], unique: bool = False) -> None:
    if _table_exists(table_name) and not _index_exists(table_name, index_name):
        op.create_index(index_name, table_name, columns, unique=unique)


def upgrade() -> None:
    if not _table_exists("user_sessions"):
        op.create_table(
            "user_sessions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("session_id", sa.String(length=64), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("jti_hash", sa.String(length=64), nullable=False),
            sa.Column("ip_address", sa.String(length=64), nullable=True),
            sa.Column("user_agent", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("last_activity_at", sa.DateTime(), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.Column("revoked_by_user_id", sa.Integer(), nullable=True),
            sa.Column("revocation_reason", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(["revoked_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("session_id"),
        )
    _create_index_if_missing(op.f("ix_user_sessions_expires_at"), "user_sessions", ["expires_at"])
    _create_index_if_missing(op.f("ix_user_sessions_id"), "user_sessions", ["id"])
    _create_index_if_missing(op.f("ix_user_sessions_jti_hash"), "user_sessions", ["jti_hash"])
    _create_index_if_missing(op.f("ix_user_sessions_revoked_at"), "user_sessions", ["revoked_at"])
    _create_index_if_missing(op.f("ix_user_sessions_session_id"), "user_sessions", ["session_id"], unique=True)
    _create_index_if_missing(op.f("ix_user_sessions_user_id"), "user_sessions", ["user_id"])

    if not _table_exists("user_temporary_access"):
        op.create_table(
            "user_temporary_access",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("target_user_id", sa.Integer(), nullable=False),
            sa.Column("module_id", sa.Integer(), nullable=False),
            sa.Column("permission_level", sa.String(length=30), nullable=False),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("starts_at", sa.DateTime(), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("created_by_user_id", sa.Integer(), nullable=False),
            sa.Column("revoked_by_user_id", sa.Integer(), nullable=True),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.Column("revocation_reason", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["module_id"], ["modules.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["revoked_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["target_user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing(op.f("ix_user_temporary_access_expires_at"), "user_temporary_access", ["expires_at"])
    _create_index_if_missing(op.f("ix_user_temporary_access_id"), "user_temporary_access", ["id"])
    _create_index_if_missing(op.f("ix_user_temporary_access_module_id"), "user_temporary_access", ["module_id"])
    _create_index_if_missing(op.f("ix_user_temporary_access_starts_at"), "user_temporary_access", ["starts_at"])
    _create_index_if_missing(op.f("ix_user_temporary_access_status"), "user_temporary_access", ["status"])
    _create_index_if_missing(op.f("ix_user_temporary_access_target_user_id"), "user_temporary_access", ["target_user_id"])

    if not _table_exists("user_temporary_substitutions"):
        op.create_table(
            "user_temporary_substitutions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("replaced_user_id", sa.Integer(), nullable=False),
            sa.Column("substitute_user_id", sa.Integer(), nullable=False),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("starts_at", sa.DateTime(), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("created_by_user_id", sa.Integer(), nullable=False),
            sa.Column("ended_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["replaced_user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["substitute_user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing(op.f("ix_user_temporary_substitutions_expires_at"), "user_temporary_substitutions", ["expires_at"])
    _create_index_if_missing(op.f("ix_user_temporary_substitutions_id"), "user_temporary_substitutions", ["id"])
    _create_index_if_missing(op.f("ix_user_temporary_substitutions_replaced_user_id"), "user_temporary_substitutions", ["replaced_user_id"])
    _create_index_if_missing(op.f("ix_user_temporary_substitutions_starts_at"), "user_temporary_substitutions", ["starts_at"])
    _create_index_if_missing(op.f("ix_user_temporary_substitutions_status"), "user_temporary_substitutions", ["status"])
    _create_index_if_missing(op.f("ix_user_temporary_substitutions_substitute_user_id"), "user_temporary_substitutions", ["substitute_user_id"])

    if not _table_exists("user_offboarding_cases"):
        op.create_table(
            "user_offboarding_cases",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("target_user_id", sa.Integer(), nullable=False),
            sa.Column("replacement_user_id", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("impact_snapshot", json_type, nullable=False),
            sa.Column("created_by_user_id", sa.Integer(), nullable=False),
            sa.Column("confirmed_by_user_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("confirmed_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["confirmed_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["replacement_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["target_user_id"], ["users.id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing(op.f("ix_user_offboarding_cases_id"), "user_offboarding_cases", ["id"])
    _create_index_if_missing(op.f("ix_user_offboarding_cases_status"), "user_offboarding_cases", ["status"])
    _create_index_if_missing(op.f("ix_user_offboarding_cases_target_user_id"), "user_offboarding_cases", ["target_user_id"])

    if not _table_exists("user_offboarding_tasks"):
        op.create_table(
            "user_offboarding_tasks",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("case_id", sa.Integer(), nullable=False),
            sa.Column("module", sa.String(length=60), nullable=False),
            sa.Column("title", sa.String(length=180), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("requires_human_review", sa.Boolean(), nullable=False),
            sa.Column("payload", json_type, nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["case_id"], ["user_offboarding_cases.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing(op.f("ix_user_offboarding_tasks_case_id"), "user_offboarding_tasks", ["case_id"])
    _create_index_if_missing(op.f("ix_user_offboarding_tasks_id"), "user_offboarding_tasks", ["id"])
    _create_index_if_missing(op.f("ix_user_offboarding_tasks_module"), "user_offboarding_tasks", ["module"])
    _create_index_if_missing(op.f("ix_user_offboarding_tasks_status"), "user_offboarding_tasks", ["status"])


def downgrade() -> None:
    op.drop_index(op.f("ix_user_offboarding_tasks_status"), table_name="user_offboarding_tasks")
    op.drop_index(op.f("ix_user_offboarding_tasks_module"), table_name="user_offboarding_tasks")
    op.drop_index(op.f("ix_user_offboarding_tasks_id"), table_name="user_offboarding_tasks")
    op.drop_index(op.f("ix_user_offboarding_tasks_case_id"), table_name="user_offboarding_tasks")
    op.drop_table("user_offboarding_tasks")

    op.drop_index(op.f("ix_user_offboarding_cases_target_user_id"), table_name="user_offboarding_cases")
    op.drop_index(op.f("ix_user_offboarding_cases_status"), table_name="user_offboarding_cases")
    op.drop_index(op.f("ix_user_offboarding_cases_id"), table_name="user_offboarding_cases")
    op.drop_table("user_offboarding_cases")

    op.drop_index(op.f("ix_user_temporary_substitutions_substitute_user_id"), table_name="user_temporary_substitutions")
    op.drop_index(op.f("ix_user_temporary_substitutions_status"), table_name="user_temporary_substitutions")
    op.drop_index(op.f("ix_user_temporary_substitutions_starts_at"), table_name="user_temporary_substitutions")
    op.drop_index(op.f("ix_user_temporary_substitutions_replaced_user_id"), table_name="user_temporary_substitutions")
    op.drop_index(op.f("ix_user_temporary_substitutions_id"), table_name="user_temporary_substitutions")
    op.drop_index(op.f("ix_user_temporary_substitutions_expires_at"), table_name="user_temporary_substitutions")
    op.drop_table("user_temporary_substitutions")

    op.drop_index(op.f("ix_user_temporary_access_target_user_id"), table_name="user_temporary_access")
    op.drop_index(op.f("ix_user_temporary_access_status"), table_name="user_temporary_access")
    op.drop_index(op.f("ix_user_temporary_access_starts_at"), table_name="user_temporary_access")
    op.drop_index(op.f("ix_user_temporary_access_module_id"), table_name="user_temporary_access")
    op.drop_index(op.f("ix_user_temporary_access_id"), table_name="user_temporary_access")
    op.drop_index(op.f("ix_user_temporary_access_expires_at"), table_name="user_temporary_access")
    op.drop_table("user_temporary_access")

    op.drop_index(op.f("ix_user_sessions_user_id"), table_name="user_sessions")
    op.drop_index(op.f("ix_user_sessions_session_id"), table_name="user_sessions")
    op.drop_index(op.f("ix_user_sessions_revoked_at"), table_name="user_sessions")
    op.drop_index(op.f("ix_user_sessions_jti_hash"), table_name="user_sessions")
    op.drop_index(op.f("ix_user_sessions_id"), table_name="user_sessions")
    op.drop_index(op.f("ix_user_sessions_expires_at"), table_name="user_sessions")
    op.drop_table("user_sessions")
