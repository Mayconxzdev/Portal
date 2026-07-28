import uuid
from sqlalchemy import String, DateTime, ForeignKey, JSON, UUID, Boolean
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from app.core.database import Base

class ReactionRuleRun(Base):
    __tablename__ = "reaction_rule_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reaction_rules.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )
    status: Mapped[str] = mapped_column(String, index=True, nullable=False)  # SKIPPED, MATCHED, EXECUTED, FAILED, BLOCKED
    condition_result: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    action_result: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        nullable=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False
    )
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True)
