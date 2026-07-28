import uuid
from sqlalchemy import Integer, String, DateTime, ForeignKey, JSON, UUID
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from app.core.database import Base

class EventLog(Base):
    __tablename__ = "event_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    event_type: Mapped[str] = mapped_column(String, index=True, nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String, index=True, nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    
    actor_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    module: Mapped[str] = mapped_column(String, index=True, nullable=False)
    
    payload: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        default=dict
    )
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        default=dict
    )
    
    status: Mapped[str] = mapped_column(String, default="PENDING", index=True)  # PENDING, DISPATCHED, FAILED
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        index=True
    )
    dispatched_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
