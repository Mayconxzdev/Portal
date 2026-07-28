from fastapi import APIRouter, Depends, HTTPException, Request, status, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Optional
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    generate_token_identifier,
    hash_token_identifier,
    verify_password,
)
from app.core.permissions import get_current_user, get_token_from_request
from app.core.config import settings
from app.core.audit import log_action
from app.core.rate_limit import login_rate_limiter
from app.core.events import emit_event
from app.models.admin_lifecycle import UserSession
from app.models.user import User
from app.models.module import Module

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    role: str
    is_active: bool
    module_permissions: Dict[str, str]


def _client_host(request: Request) -> Optional[str]:
    return request.client.host if request.client else None


def _current_session_from_request(request: Request, db: Session, user_id: int) -> Optional[UserSession]:
    try:
        token = get_token_from_request(request)
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.ALGORITHM])
    except (HTTPException, JWTError):
        return None

    session_id = payload.get("sid")
    token_id = payload.get("jti")
    if not session_id or not token_id:
        return None

    return db.query(UserSession).filter(
        UserSession.user_id == user_id,
        UserSession.session_id == session_id,
        UserSession.jti_hash == hash_token_identifier(token_id),
    ).first()

@router.post("/login")
def login(
    request: Request,
    response: Response,
    request_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Autentica o usuário, gera o token JWT, define o cookie HttpOnly e retorna os dados do usuário.
    """
    login_rate_limiter.assert_allowed(request, request_data.username)
    user = db.query(User).filter(User.username == request_data.username).first()
    
    if not user or not verify_password(request_data.password, user.hashed_password):
        login_rate_limiter.record_failure(request, request_data.username)
        # Auditoria: Login falhou (credenciais incorretas)
        log_action(
            db=db,
            user_id=user.id if user else None,
            action="LOGIN_FAILED",
            module="auth",
            details={"username": request_data.username, "reason": "Credenciais incorretas"},
            commit=True
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nome de usuário ou senha incorretos"
        )

    if not user.is_active:
        login_rate_limiter.record_failure(request, request_data.username)
        # Auditoria: Login falhou (usuário inativo)
        log_action(
            db=db,
            user_id=user.id,
            action="LOGIN_FAILED",
            module="auth",
            details={"username": request_data.username, "reason": "Usuário inativo"},
            commit=True
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seu usuário está inativo. Contate o administrador."
        )

    # Atualiza o último login
    login_rate_limiter.clear(request, request_data.username)
    user.last_login = datetime.now(timezone.utc)

    # Emite evento de login bem-sucedido (Outbox pattern)
    emit_event(
        db=db,
        event_type="auth.user.logged_in",
        aggregate_type="user",
        aggregate_id=str(user.id),
        module="auth",
        payload={
            "username": user.username,
            "email": user.email,
            "role": user.role.name if user.role else "USER",
            "ip_address": _client_host(request)
        },
        actor_user_id=user.id
    )

    now = datetime.now(timezone.utc)
    session_id = generate_token_identifier()
    token_id = generate_token_identifier()
    expires_at = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    user_session = UserSession(
        session_id=session_id,
        user_id=user.id,
        jti_hash=hash_token_identifier(token_id),
        ip_address=_client_host(request),
        user_agent=(request.headers.get("user-agent") or "")[:255] or None,
        created_at=now,
        last_activity_at=now,
        expires_at=expires_at,
    )
    db.add(user_session)
    db.commit()

    # Cria o token de acesso vinculado a uma sessao revogavel
    access_token = create_access_token(
        subject=user.username,
        session_id=session_id,
        token_id=token_id,
    )

    # Configura o cookie HttpOnly para o cliente web
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        expires=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.COOKIE_SECURE,
    )

    # Auditoria: Login bem sucedido
    log_action(
        db=db,
        user_id=user.id,
        action="LOGIN_SUCCESS",
        module="auth",
        commit=True
    )

    # Constrói o mapeamento de permissões de módulos do usuário
    permissions_map = {}
    modules = db.query(Module).all()
    if user.role and user.role.name == "ADMIN":
        for m in modules:
            permissions_map[m.code] = "ADMIN"
    else:
        for acc in user.module_accesses:
            permissions_map[acc.module.code] = acc.permission_level

    # Garante que todo módulo tem pelo menos NO_ACCESS mapeado
    for m in modules:
        if m.code not in permissions_map:
            permissions_map[m.code] = "NO_ACCESS"

    return {
        "status": "success",
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role.name if user.role else "USER",
            "is_active": user.is_active,
            "module_permissions": permissions_map
        }
    }

@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Remove o cookie HttpOnly de sessão e registra o logout do usuário.
    """
    response.delete_cookie(
        key="access_token",
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.COOKIE_SECURE,
    )
    
    now = datetime.now(timezone.utc)
    user_session = _current_session_from_request(request, db, current_user.id)
    if user_session and user_session.revoked_at is None:
        user_session.revoked_at = now
        user_session.revoked_by_user_id = current_user.id
        user_session.revocation_reason = "Logout feito pelo usuario"

    # Auditoria: Logout do sistema
    log_action(
        db=db,
        user_id=current_user.id,
        action="LOGOUT",
        module="auth",
        details={"session_revoked": bool(user_session)},
        commit=False
    )
    db.commit()
    
    return {
        "status": "success",
        "detail": "Sessão encerrada com sucesso"
    }

@router.get("/me", response_model=UserResponse)
def get_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retorna os dados do usuário autenticado atual e seus acessos configurados.
    """
    permissions_map = {}
    modules = db.query(Module).all()
    
    if current_user.role and current_user.role.name == "ADMIN":
        for m in modules:
            permissions_map[m.code] = "ADMIN"
    else:
        for acc in current_user.module_accesses:
            permissions_map[acc.module.code] = acc.permission_level

    # Garante que todos os módulos cadastrados apareçam no mapa de permissões
    for m in modules:
        if m.code not in permissions_map:
            permissions_map[m.code] = "NO_ACCESS"

    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role.name if current_user.role else "USER",
        "is_active": current_user.is_active,
        "module_permissions": permissions_map
    }

@router.post("/refresh")
def refresh_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Gera um novo token JWT atualizado mantendo a sessão ativa.
    """
    user_session = _current_session_from_request(request, db, current_user.id)
    if not user_session or user_session.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessao encerrada. Faca login novamente.")

    token_id = generate_token_identifier()
    user_session.jti_hash = hash_token_identifier(token_id)
    user_session.last_activity_at = datetime.now(timezone.utc)
    db.commit()

    access_token = create_access_token(
        subject=current_user.username,
        session_id=user_session.session_id,
        token_id=token_id,
    )
    
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        expires=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.COOKIE_SECURE,
    )
    
    return {
        "status": "success",
        "access_token": access_token,
        "token_type": "bearer"
    }
