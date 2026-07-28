from sqlalchemy import Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from app.core.database import Base

class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    module_slug: Mapped[str] = mapped_column(String, index=True, nullable=False)
    
    requester_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), 
        index=True, 
        nullable=False
    )
    approver_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), 
        index=True, 
        nullable=True
    )
    
    status: Mapped[str] = mapped_column(String, default="PENDING", index=True)  # PENDING, APPROVED, REJECTED, CANCELLED, EXPIRED
    risk_level: Mapped[str] = mapped_column(String, default="LOW", index=True)  # LOW, MEDIUM, HIGH, CRITICAL
    action_type: Mapped[str] = mapped_column(String, nullable=False)           # ex: "APPROVE_PURCHASE", "TI_ACTION"
    
    action_payload: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        default=dict
    )
    result_payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        nullable=True
    )
    
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=lambda: datetime.now(timezone.utc),
        index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relacionamentos
    requester = relationship("User", foreign_keys=[requester_user_id], back_populates="requested_approvals")
    approver = relationship("User", foreign_keys=[approver_user_id], back_populates="decided_approvals")
    comments = relationship("ApprovalComment", back_populates="approval", cascade="all, delete-orphan")
    decisions = relationship("ApprovalDecision", back_populates="approval", cascade="all, delete-orphan")
