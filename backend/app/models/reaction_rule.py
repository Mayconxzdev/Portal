import uuid
from sqlalchemy import Integer, String, DateTime, ForeignKey, JSON, UUID, Boolean
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from app.core.database import Base

class ReactionRule(Base):
    __tablename__ = "reaction_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    event_type: Mapped[str] = mapped_column(String, index=True, nullable=False)
    module: Mapped[str] = mapped_column(String, index=True, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    condition_json: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        default=dict,
        nullable=False
    )
    action_type: Mapped[str] = mapped_column(String, nullable=False)
    action_payload: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        default=dict,
        nullable=False
    )
    
    cooldown_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_runs_per_hour: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    created_by_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    tenant_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
