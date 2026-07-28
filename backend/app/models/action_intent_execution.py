import uuid
from sqlalchemy import Integer, String, DateTime, ForeignKey, JSON, UUID, Text
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from app.core.database import Base

class ActionIntentExecution(Base):
    __tablename__ = "action_intent_executions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    action_intent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("action_intents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    executor_key: Mapped[str] = mapped_column(String, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String, default="PENDING", index=True) # PENDING, RUNNING, SUCCEEDED, FAILED, BLOCKED, SKIPPED
    
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=1)
    
    input_payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        nullable=True
    )
    result_payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        nullable=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_by_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    correlation_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        index=True
    )
