from sqlalchemy import Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from typing import Optional, List
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String, unique=True, index=True, nullable=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(180), nullable=True)
    department: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    job_title: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
    
    role_id: Mapped[Optional[int]] = mapped_column(ForeignKey("roles.id", ondelete="SET NULL"), nullable=True)
    role: Mapped[Optional["Role"]] = relationship("Role")

    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relacionamento de acessos aos módulos
    module_accesses: Mapped[List["UserModuleAccess"]] = relationship(
        "UserModuleAccess", 
        back_populates="user",
        cascade="all, delete-orphan"
    )

    # Relacionamentos de aprovações
    requested_approvals = relationship("Approval", foreign_keys="[Approval.requester_user_id]", back_populates="requester")
    decided_approvals = relationship("Approval", foreign_keys="[Approval.approver_user_id]", back_populates="approver")

    @property
    def role_name(self) -> Optional[str]:
        return self.role.name if self.role else None
