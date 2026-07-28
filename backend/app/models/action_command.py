import uuid
from sqlalchemy import Integer, String, DateTime, ForeignKey, JSON, UUID, Boolean, Text
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from app.core.database import Base

class ActionCommandDraft(Base):
    __tablename__ = "action_command_drafts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    source: Mapped[str] = mapped_column(String, index=True, nullable=False) # e.g. chat, global_bar, module_button, card_menu, drawer, koda
    source_module: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True)
    source_entity_type: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True)
    source_entity_id: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True)
    
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    action_key: Mapped[str] = mapped_column(String, index=True, nullable=False)
    intent_type: Mapped[str] = mapped_column(String, index=True, nullable=False)
    module: Mapped[str] = mapped_column(String, index=True, nullable=False)
    
    status: Mapped[str] = mapped_column(
        String, 
        default="DRAFT", 
        index=True, 
        nullable=False
    ) # DRAFT, NEEDS_MORE_INFO, READY_TO_CONFIRM, CONFIRMED, CANCELLED, EXECUTED, FAILED, APPROVAL_REQUIRED
    
    extracted_data: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        default=dict,
        nullable=False
    )
    enriched_data: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        default=dict,
        nullable=False
    )
    missing_fields: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        default=dict,
        nullable=False
    )
    preview: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        default=dict,
        nullable=False
    )
    
    risk_level: Mapped[str] = mapped_column(
        String, 
        default="LOW", 
        index=True, 
        nullable=False
    ) # LOW, MEDIUM, HIGH, CRITICAL
    
    requires_confirmation: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    target_action_type: Mapped[str] = mapped_column(String, nullable=False)
    
    created_entity_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_entity_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    action_intent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("action_intents.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
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
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
