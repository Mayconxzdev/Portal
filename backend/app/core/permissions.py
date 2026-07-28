from enum import Enum
from datetime import datetime, timezone
from fastapi import HTTPException, status, Depends, Request
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from typing import Callable, Any
from app.core.database import get_db
from app.core.config import settings
from app.core.security import hash_token_identifier
from app.models.user import User


class PermissionLevel(str, Enum):
    NO_ACCESS = "NO_ACCESS"
    READ_ONLY = "READ_ONLY"
    NORMAL = "NORMAL"
    MANAGER = "MANAGER"
    ADMIN = "ADMIN"


LEVEL_VALUES = {
    PermissionLevel.NO_ACCESS: 0,
    PermissionLevel.READ_ONLY: 1,
    PermissionLevel.NORMAL: 2,
    PermissionLevel.MANAGER: 3,
    PermissionLevel.ADMIN: 4,
}


def get_token_from_request(request: Request) -> str:
    """
    Extrai JWT por Bearer ou cookie HttpOnly. Bearer tem prioridade para
    clientes API e testes que podem manter cookie de outra sessao.
    """
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:]

    token = request.cookies.get("access_token")
    if token:
        if token.startswith("Bearer "):
            token = token[7:]
        return token

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Nao autenticado. Por favor, faca login.",
    )


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _decode_auth_payload(request: Request) -> dict[str, Any]:
    token = get_token_from_request(request)
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.ALGORITHM])


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    try:
        payload = _decode_auth_payload(request)
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de autenticacao invalido")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessao expirada. Faca login novamente.")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessao invalida. Faca login novamente.")

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario associado ao token nao encontrado")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario inativo ou desabilitado.")

    session_id = payload.get("sid")
    token_id = payload.get("jti")
    if session_id and token_id:
        from app.models.admin_lifecycle import UserSession

        user_session = db.query(UserSession).filter(
            UserSession.session_id == session_id,
            UserSession.user_id == user.id,
        ).first()
        if (
            not user_session
            or user_session.revoked_at is not None
            or user_session.jti_hash != hash_token_identifier(token_id)
            or _as_utc(user_session.expires_at) <= _utcnow()
        ):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessao encerrada. Faca login novamente.")
        user_session.last_activity_at = _utcnow()
        db.flush()
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.role or current_user.role.name != "ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado. Recurso restrito a administradores.")
    return current_user


def check_module_access(module_code: str, required_level: PermissionLevel) -> Callable:
    def dependency(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> bool:
        if current_user.role and current_user.role.name == "ADMIN":
            return True

        from app.models.module import Module
        from app.models.user_module_access import UserModuleAccess
        from app.models.admin_lifecycle import UserTemporaryAccess
        from app.core.audit import log_action

        module = db.query(Module).filter(Module.code == module_code).first()
        if not module:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Modulo '{module_code}' nao cadastrado")
        if not module.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Modulo '{module.name}' esta desativado")

        access = db.query(UserModuleAccess).filter(
            UserModuleAccess.user_id == current_user.id,
            UserModuleAccess.module_id == module.id,
        ).first()
        user_level_str = access.permission_level if access else "NO_ACCESS"
        try:
            user_level = PermissionLevel(user_level_str)
        except ValueError:
            user_level = PermissionLevel.NO_ACCESS

        active_temp = db.query(UserTemporaryAccess).filter(
            UserTemporaryAccess.target_user_id == current_user.id,
            UserTemporaryAccess.module_id == module.id,
            UserTemporaryAccess.status == "ACTIVE",
            UserTemporaryAccess.starts_at <= _utcnow(),
            UserTemporaryAccess.expires_at > _utcnow(),
            UserTemporaryAccess.revoked_at.is_(None),
        ).order_by(UserTemporaryAccess.expires_at.desc()).first()
        if active_temp:
            try:
                temp_level = PermissionLevel(active_temp.permission_level)
            except ValueError:
                temp_level = PermissionLevel.NO_ACCESS
            if LEVEL_VALUES[temp_level] > LEVEL_VALUES[user_level]:
                user_level = temp_level
                user_level_str = temp_level.value

        if LEVEL_VALUES[user_level] < LEVEL_VALUES[required_level]:
            log_action(
                db=db,
                user_id=current_user.id,
                action="ACCESS_DENIED",
                module=module_code,
                details={"required_level": required_level.value, "user_level": user_level_str},
                commit=True,
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Acesso negado ao módulo: {module.name}")
        return True

    return dependency
