import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import get_current_user
from app.models.user import User
from app.modules.action_intents.schemas import ActionIntentRead, ActionIntentReject, ActionIntentReview, ActionIntentExecuteRequest, ActionIntentExecutionRead
from app.modules.action_intents import service

router = APIRouter()

def require_admin_or_manager(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.role or current_user.role.name not in ("ADMIN", "MANAGER"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Recurso restrito a administradores ou gerentes."
        )
    return current_user

@router.get("", response_model=List[ActionIntentRead])
def get_action_intents(
    status: Optional[str] = Query(None, description="Filtra por status"),
    source: Optional[str] = Query(None, description="Filtra por origem"),
    target_module: Optional[str] = Query(None, description="Filtra por modulo alvo"),
    risk_level: Optional[str] = Query(None, description="Filtra por nivel de risco"),
    limit: int = Query(50, ge=1, le=100, description="Limite de registros retornados"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """
    Retorna a lista de intenções de ação de automação cadastradas.
    Disponível apenas para administradores e gerentes.
    """
    return service.list_action_intents(
        db=db,
        status=status,
        source=source,
        target_module=target_module,
        risk_level=risk_level,
        limit=limit
    )

@router.get("/{id}", response_model=ActionIntentRead)
def get_action_intent_by_id(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """
    Retorna os detalhes de uma intenção de ação específica pelo seu ID.
    Disponível apenas para administradores e gerentes.
    """
    intent = service.get_action_intent(db, id)
    if not intent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Intenção de ação não encontrada."
        )
    return intent

@router.post("/{id}/reject", response_model=ActionIntentRead)
def reject_action_intent_endpoint(
    id: uuid.UUID,
    reject_in: ActionIntentReject,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """
    Rejeita uma intenção de ação, alterando seu status para REJECTED e registrando a justificativa.
    Disponível apenas para administradores e gerentes.
    """
    intent = service.reject_action_intent(db, id, current_user.id, reject_in.reason)
    if not intent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Intenção de ação não encontrada."
        )
    return intent

@router.post("/{id}/mark-reviewed", response_model=ActionIntentRead)
def mark_reviewed_action_intent_endpoint(
    id: uuid.UUID,
    review_in: ActionIntentReview,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """
    Aprova ou marca como revisada uma intenção de ação.
    Disponível apenas para administradores e gerentes.
    """
    intent = service.mark_reviewed_action_intent(db, id, current_user.id, review_in.reason)
    if not intent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Intenção de ação não encontrada."
        )
    return intent

@router.post("/{id}/execute", response_model=ActionIntentExecutionRead)
def execute_action_intent_endpoint(
    id: uuid.UUID,
    execute_in: ActionIntentExecuteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """
    Executa ou simula (dry_run) a intenção de ação proposta.
    Disponível apenas para administradores e gerentes.
    """
    idem_key = execute_in.idempotency_key or f"idem-exec-{uuid.uuid4()}"
    try:
        execution = service.execute_action_intent(
            db=db,
            intent_id=id,
            actor_user_id=current_user.id,
            idempotency_key=idem_key,
            dry_run=execute_in.dry_run
        )
        if not execution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Intenção de ação não encontrada."
            )
        return execution
    except ValueError as ex:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ex)
        )
