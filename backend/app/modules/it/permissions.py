from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.permissions import LEVEL_VALUES, PermissionLevel
from app.models.module import Module
from app.models.user import User
from app.models.user_module_access import UserModuleAccess


def is_global_admin(user: User) -> bool:
    return bool(user.role and user.role.name in {"ADMIN", "MESSIAS"})


def get_it_level(db: Session, user: User) -> PermissionLevel:
    if is_global_admin(user):
        return PermissionLevel.ADMIN
    module = db.query(Module).filter(Module.code == "it").first()
    if not module or not module.is_active:
        return PermissionLevel.NO_ACCESS
    access = db.query(UserModuleAccess).filter(
        UserModuleAccess.user_id == user.id,
        UserModuleAccess.module_id == module.id,
    ).first()
    try:
        return PermissionLevel(access.permission_level if access else "NO_ACCESS")
    except ValueError:
        return PermissionLevel.NO_ACCESS


def has_it_level(db: Session, user: User, required: PermissionLevel) -> bool:
    return LEVEL_VALUES[get_it_level(db, user)] >= LEVEL_VALUES[required]


def require_it_level(db: Session, user: User, required: PermissionLevel) -> PermissionLevel:
    level = get_it_level(db, user)
    if LEVEL_VALUES[level] < LEVEL_VALUES[required]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado ao modulo TI.",
        )
    return level


def is_it_staff(db: Session, user: User) -> bool:
    return has_it_level(db, user, PermissionLevel.MANAGER)


def require_it_staff(db: Session, user: User) -> None:
    require_it_level(db, user, PermissionLevel.MANAGER)


def require_it_admin(db: Session, user: User) -> None:
    require_it_level(db, user, PermissionLevel.ADMIN)
