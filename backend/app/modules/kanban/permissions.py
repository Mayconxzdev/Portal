from enum import Enum
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.audit import log_action
from app.core.permissions import LEVEL_VALUES, PermissionLevel
from app.models.kanban import KanbanBoard, KanbanBoardPermission
from app.models.module import Module
from app.models.user import User
from app.models.user_module_access import UserModuleAccess


class BoardAccessLevel(str, Enum):
    NO_ACCESS = "NO_ACCESS"
    READ_ONLY = "READ_ONLY"
    NORMAL = "NORMAL"
    MANAGER = "MANAGER"
    ADMIN = "ADMIN"


BOARD_LEVEL_VALUES = {
    BoardAccessLevel.NO_ACCESS: 0,
    BoardAccessLevel.READ_ONLY: 1,
    BoardAccessLevel.NORMAL: 2,
    BoardAccessLevel.MANAGER: 3,
    BoardAccessLevel.ADMIN: 4,
}


def get_module_level(db: Session, user: User, module_code: str = "kanban") -> PermissionLevel:
    if user.role and user.role.name == "ADMIN":
        return PermissionLevel.ADMIN

    module = db.query(Module).filter(Module.code == module_code, Module.is_active == True).first()
    if not module:
        return PermissionLevel.NO_ACCESS

    access = db.query(UserModuleAccess).filter(
        UserModuleAccess.user_id == user.id,
        UserModuleAccess.module_id == module.id,
    ).first()
    if not access:
        return PermissionLevel.NO_ACCESS
    try:
        return PermissionLevel(access.permission_level)
    except ValueError:
        return PermissionLevel.NO_ACCESS


def require_module_level(db: Session, user: User, required: PermissionLevel) -> None:
    level = get_module_level(db, user, "kanban")
    if LEVEL_VALUES[level] < LEVEL_VALUES[required]:
        log_action(
            db=db,
            user_id=user.id,
            action="kanban.access.denied",
            module="kanban",
            details={"required_level": required.value, "user_level": level.value},
            commit=True,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Acesso negado ao Kanban (requer nivel {required.value}).",
        )


def get_board_access_level(db: Session, board: KanbanBoard, user: User) -> BoardAccessLevel:
    if user.role and user.role.name == "ADMIN":
        return BoardAccessLevel.ADMIN
    if board.created_by_user_id == user.id:
        return BoardAccessLevel.ADMIN

    user_permission = db.query(KanbanBoardPermission).filter(
        KanbanBoardPermission.board_id == board.id,
        KanbanBoardPermission.user_id == user.id,
    ).first()
    role_permission: Optional[KanbanBoardPermission] = None
    if user.role_id:
        role_permission = db.query(KanbanBoardPermission).filter(
            KanbanBoardPermission.board_id == board.id,
            KanbanBoardPermission.role_id == user.role_id,
        ).first()

    levels = []
    for permission in (user_permission, role_permission):
        if not permission:
            continue
        try:
            levels.append(BoardAccessLevel(permission.access_level))
        except ValueError:
            levels.append(BoardAccessLevel.NO_ACCESS)

    if not levels:
        return BoardAccessLevel.NO_ACCESS
    return max(levels, key=lambda item: BOARD_LEVEL_VALUES[item])


def require_board_level(db: Session, board: KanbanBoard, user: User, required: BoardAccessLevel) -> BoardAccessLevel:
    module_level = get_module_level(db, user, "kanban")
    if LEVEL_VALUES[module_level] < LEVEL_VALUES[PermissionLevel.READ_ONLY]:
        log_denied(db, user, board, "Sem acesso ao modulo Kanban")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado ao modulo Kanban.")

    level = get_board_access_level(db, board, user)
    if BOARD_LEVEL_VALUES[level] < BOARD_LEVEL_VALUES[required]:
        log_denied(db, user, board, f"Nivel insuficiente no board: {level.value}, requer {required.value}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Acesso negado ao board '{board.name}' (requer {required.value}).",
        )
    return level


def log_denied(db: Session, user: User, board: Optional[KanbanBoard], reason: str) -> None:
    log_action(
        db=db,
        user_id=user.id,
        action="kanban.access.denied",
        module="kanban",
        details={"board_id": board.id if board else None, "reason": reason},
        commit=True,
    )
