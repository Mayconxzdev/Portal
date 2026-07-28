import uuid
from sqlalchemy import Integer, String, DateTime, ForeignKey, JSON, UUID, Text, Float
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from app.core.database import Base

class LegacyImportBatch(Base):
    __tablename__ = "legacy_import_batches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    source_app: Mapped[str] = mapped_column(String, index=True, nullable=False) # e.g. COMPRASAPP2, HELPDESK, etc.
    source_name: Mapped[str] = mapped_column(String, nullable=False)
    source_path_masked: Mapped[str] = mapped_column(String, nullable=False)
    module_target: Mapped[str] = mapped_column(String, index=True, nullable=False) # e.g. purchases, it, etc.
    status: Mapped[str] = mapped_column(String, default="DISCOVERED", index=True, nullable=False) # DISCOVERED, EXTRACTED, NEEDS_REVIEW, READY_TO_IMPORT, IMPORTED, FAILED, CANCELLED
    
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    valid_rows: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_rows: Mapped[int] = mapped_column(Integer, default=0)
    error_rows: Mapped[int] = mapped_column(Integer, default=0)
    
    created_by_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        index=True
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Relationships
    rows: Mapped[List["LegacyImportRow"]] = relationship("LegacyImportRow", back_populates="batch", cascade="all, delete-orphan")


class LegacyImportRow(Base):
    __tablename__ = "legacy_import_rows"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("legacy_import_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    source_app: Mapped[str] = mapped_column(String, index=True, nullable=False)
    source_table_or_sheet: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    source_row_id: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True)
    module_target: Mapped[str] = mapped_column(String, index=True, nullable=False)
    entity_target: Mapped[str] = mapped_column(String, index=True, nullable=False) # e.g. SUPPLIER, PRODUCT_ITEM, etc.
    
    raw_data_json: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        default=dict,
        nullable=False
    )
    normalized_data_json: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        default=dict,
        nullable=False
    )
    detected_duplicates_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        nullable=True
    )
    issues_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        nullable=True
    )
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String, default="PENDING_REVIEW", index=True, nullable=False) # PENDING_REVIEW, READY, DUPLICATE_CANDIDATE, REJECTED, IMPORTED, ERROR
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        index=True
    )
    reviewed_by_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Relationships
    batch: Mapped[LegacyImportBatch] = relationship("LegacyImportBatch", back_populates="rows")
    duplicate_candidates: Mapped[List["LegacyDuplicateCandidate"]] = relationship("LegacyDuplicateCandidate", back_populates="row", cascade="all, delete-orphan")
    decisions: Mapped[List["LegacyImportDecision"]] = relationship("LegacyImportDecision", back_populates="row", cascade="all, delete-orphan")


class LegacyDuplicateCandidate(Base):
    __tablename__ = "legacy_duplicate_candidates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    row_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("legacy_import_rows.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    target_entity_type: Mapped[str] = mapped_column(String, nullable=False)
    target_entity_id: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True)
    match_type: Mapped[str] = mapped_column(String, nullable=False) # e.g. DOCUMENT, EMAIL, NAME, SKU, TITLE, PATH, FUZZY
    score: Mapped[float] = mapped_column(Float, default=1.0)
    status: Mapped[str] = mapped_column(String, default="PENDING", index=True, nullable=False) # PENDING, CONFIRMED_DUPLICATE, NOT_DUPLICATE, MERGE_LATER
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        index=True
    )

    # Relationships
    row: Mapped[LegacyImportRow] = relationship("LegacyImportRow", back_populates="duplicate_candidates")


class LegacyImportDecision(Base):
    __tablename__ = "legacy_import_decisions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    row_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("legacy_import_rows.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    decision: Mapped[str] = mapped_column(String, nullable=False) # e.g. ACCEPT, REJECT, MERGE, CREATE_NEW, UPDATE_EXISTING, NEEDS_MORE_INFO
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decided_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    decided_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        index=True
    )

    # Relationships
    row: Mapped[LegacyImportRow] = relationship("LegacyImportRow", back_populates="decisions")


class LegacyEntityLink(Base):
    __tablename__ = "legacy_entity_links"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    legacy_row_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True
    )
    source_app: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_target: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    official_entity_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    official_entity_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False) # CREATED, LINKED_EXISTING, UPDATED_EXISTING, SKIPPED
    created_by_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )


class LegacyOperationalRecord(Base):
    __tablename__ = "legacy_operational_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    legacy_row_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True
    )
    source_app: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_target: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    responsible: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    record_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    data_json: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        default=dict,
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )


class LegacyFileIndex(Base):
    __tablename__ = "legacy_file_index"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    legacy_row_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path_masked: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True) # ODT, DOCX, HTML, PDF
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True) # TEMPLATE, PROPOSAL, MANUAL
    suggested_module: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True) # purchases, production, projects, proposals
    tags: Mapped[Optional[List[str]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        default=list
    )
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

