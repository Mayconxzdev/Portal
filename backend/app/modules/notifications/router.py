import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import get_current_user
from app.models.user import User
from app.modules.notifications.schemas import NotificationListRead, NotificationRead
from app.modules.notifications import service

router = APIRouter()

@router.get("", response_model=NotificationListRead)
def get_notifications(
    unread_only: bool = Query(False),
    status_filter: Optional[str] = Query(None, alias="status"),
    module: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    cursor: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retorna as notificações direcionadas ao usuário ou ao seu papel,
    dentro do objeto { "items": [...] } esperado pelo frontend.
    """
    user_role = current_user.role.name if current_user.role else "USER"
    items, next_cursor = service.list_notifications(
        db=db,
        user_id=current_user.id,
        user_role=user_role,
        unread_only=unread_only,
        status_filter=status_filter,
        module=module,
        severity=severity,
        limit=limit,
        cursor=cursor,
    )
    return {"items": items, "next_cursor": next_cursor}

@router.get("/unread-count")
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retorna a contagem de notificações não lidas.
    """
    user_role = current_user.role.name if current_user.role else "USER"
    count = service.unread_count(
        db=db,
        user_id=current_user.id,
        user_role=user_role,
    )
    return {"count": count}

@router.post("/{notification_id}/read", response_model=NotificationRead)
def mark_notification_as_read(
    notification_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Marca uma notificação específica como lida, validando a permissão do usuário.
    """
    user_role = current_user.role.name if current_user.role else "USER"
    updated = service.mark_notification_read(
        db=db,
        notification_id=notification_id,
        user_id=current_user.id,
        user_role=user_role
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found or access denied."
        )
    return updated


@router.post("/{notification_id}/unread", response_model=NotificationRead)
def mark_notification_as_unread(
    notification_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Marca uma notificaÃ§Ã£o especÃ­fica como nÃ£o lida para o usuÃ¡rio autenticado.
    """
    user_role = current_user.role.name if current_user.role else "USER"
    updated = service.mark_notification_unread(
        db=db,
        notification_id=notification_id,
        user_id=current_user.id,
        user_role=user_role
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found or access denied."
        )
    return updated


@router.post("/{notification_id}/archive", response_model=NotificationRead)
def archive_notification(
    notification_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Arquiva uma notificaÃ§Ã£o especÃ­fica somente para o usuÃ¡rio autenticado.
    """
    user_role = current_user.role.name if current_user.role else "USER"
    updated = service.archive_notification(
        db=db,
        notification_id=notification_id,
        user_id=current_user.id,
        user_role=user_role
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found or access denied."
        )
    return updated

@router.post("/read-all")
def mark_all_notifications_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Marca todas as notificações não lidas acessíveis ao usuário como lidas.
    """
    user_role = current_user.role.name if current_user.role else "USER"
    count = service.mark_all_read(
        db=db,
        user_id=current_user.id,
        user_role=user_role
    )
    return {"status": "success", "marked_count": count}
