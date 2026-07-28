import uuid
from sqlalchemy import String, DateTime, ForeignKey, JSON, UUID, Boolean
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from app.core.database import Base

class AutomationCallbackLog(Base):
    __tablename__ = "automation_callback_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    event_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("event_logs.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    event_type: Mapped[str] = mapped_column(String, index=True, nullable=False)
    workflow_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    workflow_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    execution_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    callback_type: Mapped[str] = mapped_column(String, index=True, nullable=False) # e.g. received, processed, failed, action_requested
    
    payload: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        default=dict
    )
    
    error: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    signature_valid: Mapped[bool] = mapped_column(Boolean, default=False)
    
    received_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        index=True
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    action_intent_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_by: Mapped[str] = mapped_column(String, default="n8n")
