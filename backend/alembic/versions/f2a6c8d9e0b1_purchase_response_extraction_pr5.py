"""purchase_response_extraction_pr5

Revision ID: f2a6c8d9e0b1
Revises: e8f1a2b3c4d5
Create Date: 2026-06-16 20:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f2a6c8d9e0b1"
down_revision: Union[str, None] = "e8f1a2b3c4d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return inspector.has_table(table_name)


def upgrade() -> None:
    if (
        _table_exists("purchase_response_extractions")
        and _table_exists("purchase_response_extracted_fields")
        and _table_exists("purchase_response_evidences")
        and _table_exists("purchase_response_review_decisions")
    ):
        return

    op.create_table(
        "purchase_response_extractions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("candidate_id", sa.UUID(), nullable=False),
        sa.Column("inbound_message_id", sa.UUID(), nullable=False),
        sa.Column("quote_id", sa.UUID(), nullable=True),
        sa.Column("supplier_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("extractor_version", sa.String(length=40), nullable=False),
        sa.Column("confidence_summary", sa.String(length=20), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("reviewed_by", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["purchase_response_candidates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["inbound_message_id"], ["purchase_email_inbound_messages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["quote_id"], ["purchase_rfqs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_purchase_response_extractions_candidate_id"), "purchase_response_extractions", ["candidate_id"], unique=False)
    op.create_index(op.f("ix_purchase_response_extractions_created_at"), "purchase_response_extractions", ["created_at"], unique=False)
    op.create_index(op.f("ix_purchase_response_extractions_inbound_message_id"), "purchase_response_extractions", ["inbound_message_id"], unique=False)
    op.create_index(op.f("ix_purchase_response_extractions_quote_id"), "purchase_response_extractions", ["quote_id"], unique=False)
    op.create_index(op.f("ix_purchase_response_extractions_status"), "purchase_response_extractions", ["status"], unique=False)
    op.create_index(op.f("ix_purchase_response_extractions_supplier_id"), "purchase_response_extractions", ["supplier_id"], unique=False)

    op.create_table(
        "purchase_response_extracted_fields",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("extraction_id", sa.UUID(), nullable=False),
        sa.Column("field_name", sa.String(length=80), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("raw_value", sa.Text(), nullable=True),
        sa.Column("normalized_value", sa.Text(), nullable=True),
        sa.Column("value_type", sa.String(length=40), nullable=False),
        sa.Column("confidence_level", sa.String(length=20), nullable=False),
        sa.Column("confidence_score", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("review_status", sa.String(length=40), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("source_label", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["extraction_id"], ["purchase_response_extractions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_purchase_response_extracted_fields_confidence_level"), "purchase_response_extracted_fields", ["confidence_level"], unique=False)
    op.create_index(op.f("ix_purchase_response_extracted_fields_extraction_id"), "purchase_response_extracted_fields", ["extraction_id"], unique=False)
    op.create_index(op.f("ix_purchase_response_extracted_fields_field_name"), "purchase_response_extracted_fields", ["field_name"], unique=False)
    op.create_index(op.f("ix_purchase_response_extracted_fields_review_status"), "purchase_response_extracted_fields", ["review_status"], unique=False)

    op.create_table(
        "purchase_response_evidences",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("extraction_id", sa.UUID(), nullable=False),
        sa.Column("field_id", sa.UUID(), nullable=True),
        sa.Column("attachment_id", sa.UUID(), nullable=True),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("source_label", sa.String(length=255), nullable=True),
        sa.Column("snippet", sa.Text(), nullable=False),
        sa.Column("char_start", sa.Integer(), nullable=True),
        sa.Column("char_end", sa.Integer(), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("row_number", sa.Integer(), nullable=True),
        sa.Column("confidence_level", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["attachment_id"], ["purchase_email_attachments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["extraction_id"], ["purchase_response_extractions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["field_id"], ["purchase_response_extracted_fields.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_purchase_response_evidences_attachment_id"), "purchase_response_evidences", ["attachment_id"], unique=False)
    op.create_index(op.f("ix_purchase_response_evidences_extraction_id"), "purchase_response_evidences", ["extraction_id"], unique=False)
    op.create_index(op.f("ix_purchase_response_evidences_field_id"), "purchase_response_evidences", ["field_id"], unique=False)

    op.create_table(
        "purchase_response_review_decisions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("extraction_id", sa.UUID(), nullable=False),
        sa.Column("field_id", sa.UUID(), nullable=True),
        sa.Column("decision", sa.String(length=40), nullable=False),
        sa.Column("previous_value", sa.Text(), nullable=True),
        sa.Column("reviewed_value", sa.Text(), nullable=True),
        sa.Column("reviewer_user_id", sa.Integer(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["extraction_id"], ["purchase_response_extractions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["field_id"], ["purchase_response_extracted_fields.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewer_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_purchase_response_review_decisions_created_at"), "purchase_response_review_decisions", ["created_at"], unique=False)
    op.create_index(op.f("ix_purchase_response_review_decisions_decision"), "purchase_response_review_decisions", ["decision"], unique=False)
    op.create_index(op.f("ix_purchase_response_review_decisions_extraction_id"), "purchase_response_review_decisions", ["extraction_id"], unique=False)
    op.create_index(op.f("ix_purchase_response_review_decisions_field_id"), "purchase_response_review_decisions", ["field_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_purchase_response_review_decisions_field_id"), table_name="purchase_response_review_decisions")
    op.drop_index(op.f("ix_purchase_response_review_decisions_extraction_id"), table_name="purchase_response_review_decisions")
    op.drop_index(op.f("ix_purchase_response_review_decisions_decision"), table_name="purchase_response_review_decisions")
    op.drop_index(op.f("ix_purchase_response_review_decisions_created_at"), table_name="purchase_response_review_decisions")
    op.drop_table("purchase_response_review_decisions")

    op.drop_index(op.f("ix_purchase_response_evidences_field_id"), table_name="purchase_response_evidences")
    op.drop_index(op.f("ix_purchase_response_evidences_extraction_id"), table_name="purchase_response_evidences")
    op.drop_index(op.f("ix_purchase_response_evidences_attachment_id"), table_name="purchase_response_evidences")
    op.drop_table("purchase_response_evidences")

    op.drop_index(op.f("ix_purchase_response_extracted_fields_review_status"), table_name="purchase_response_extracted_fields")
    op.drop_index(op.f("ix_purchase_response_extracted_fields_field_name"), table_name="purchase_response_extracted_fields")
    op.drop_index(op.f("ix_purchase_response_extracted_fields_extraction_id"), table_name="purchase_response_extracted_fields")
    op.drop_index(op.f("ix_purchase_response_extracted_fields_confidence_level"), table_name="purchase_response_extracted_fields")
    op.drop_table("purchase_response_extracted_fields")

    op.drop_index(op.f("ix_purchase_response_extractions_supplier_id"), table_name="purchase_response_extractions")
    op.drop_index(op.f("ix_purchase_response_extractions_status"), table_name="purchase_response_extractions")
    op.drop_index(op.f("ix_purchase_response_extractions_quote_id"), table_name="purchase_response_extractions")
    op.drop_index(op.f("ix_purchase_response_extractions_inbound_message_id"), table_name="purchase_response_extractions")
    op.drop_index(op.f("ix_purchase_response_extractions_created_at"), table_name="purchase_response_extractions")
    op.drop_index(op.f("ix_purchase_response_extractions_candidate_id"), table_name="purchase_response_extractions")
    op.drop_table("purchase_response_extractions")
