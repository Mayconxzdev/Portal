import uuid
from sqlalchemy import Integer, String, DateTime, ForeignKey, JSON, UUID, Text
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from app.core.database import Base

class ActionIntent(Base):
    __tablename__ = "action_intents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    source: Mapped[str] = mapped_column(String, index=True, nullable=False) # e.g. n8n, koda, reaction_engine, system, user
    source_ref_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    source_ref_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    proposed_action: Mapped[str] = mapped_column(String, index=True, nullable=False) # e.g. approve_approval, update_stock
    target_module: Mapped[str] = mapped_column(String, index=True, nullable=False) # e.g. approvals, purchases, stock
    target_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    target_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    title: Mapped[str] = mapped_column(String, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    risk_level: Mapped[str] = mapped_column(String, default="MEDIUM", index=True) # LOW, MEDIUM, HIGH, CRITICAL
    status: Mapped[str] = mapped_column(String, default="PENDING_REVIEW", index=True) # PENDING_REVIEW, APPROVAL_REQUIRED, APPROVED, REJECTED, CANCELLED, EXECUTION_BLOCKED, EXECUTED, FAILED
    
    action_payload: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        default=dict
    )
    result_payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        nullable=True
    )
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    approval_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("approvals.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    callback_log_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("automation_callback_logs.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    event_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("event_logs.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    created_by_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    reviewed_by_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        index=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    correlation_id: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
