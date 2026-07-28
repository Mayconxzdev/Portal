from sqlalchemy import Integer, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class Module(Base):
    __tablename__ = "modules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    code: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_restricted: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relacionamento de acessos de usuários
    user_accesses: Mapped[list["UserModuleAccess"]] = relationship(
        "UserModuleAccess", 
        back_populates="module",
        cascade="all, delete-orphan"
    )
