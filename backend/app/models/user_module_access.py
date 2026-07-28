from sqlalchemy import Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class UserModuleAccess(Base):
    __tablename__ = "user_module_access"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    module_id: Mapped[int] = mapped_column(ForeignKey("modules.id", ondelete="CASCADE"), nullable=False)
    permission_level: Mapped[str] = mapped_column(String, default="NO_ACCESS")  # NO_ACCESS, READ_ONLY, NORMAL, MANAGER, ADMIN

    # Relações
    user: Mapped["User"] = relationship("User", back_populates="module_accesses")
    module: Mapped["Module"] = relationship("Module", back_populates="user_accesses")

    __table_args__ = (
        UniqueConstraint("user_id", "module_id", name="uq_user_module"),
    )
