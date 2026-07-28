from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.permissions import get_current_user
from app.models.user import User
from app.modules.approvals.service import ApprovalService
from app.modules.approvals.schemas import (
    ApprovalCreate,
    ApprovalResponse,
    ApprovalCommentCreate,
    ApprovalCommentResponse,
    ApprovalSummaryResponse,
    ApprovalApprovePayload,
    ApprovalRejectPayload
)

router = APIRouter()

@router.get("/", response_model=List[ApprovalResponse])
def list_approvals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lista aprovações visíveis para o usuário autenticado de acordo com o RBAC:
    - ADMIN: Vê todas as aprovações.
    - MANAGER: Vê todas as aprovações dos módulos que gerencia.
    - USER comum: Vê apenas as suas próprias solicitações criadas.
    """
    return ApprovalService.list_approvals(db, current_user)

@router.get("/summary", response_model=ApprovalSummaryResponse)
def get_approvals_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retorna o resumo/métricas de aprovações (pendentes, minhas pendentes, aguardando minha decisão, etc.)
    respeitando o escopo de visualização do usuário logado.
    """
    return ApprovalService.get_summary(db, current_user)

@router.post("/", response_model=ApprovalResponse, status_code=status.HTTP_201_CREATED)
def create_approval_request(
    payload: ApprovalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cria uma solicitação de aprovação genérica.
    Exige autenticação e permissão de nível NORMAL ou superior no módulo de origem (module_slug).
    """
    return ApprovalService.create_approval(db, payload, current_user)

@router.get("/{approval_id}", response_model=ApprovalResponse)
def get_approval_detail(
    approval_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retorna os detalhes de uma aprovação específica, incluindo comentários e histórico de decisões.
    Valida a permissão de visualização do usuário logado.
    """
    return ApprovalService.get_approval_by_id(db, approval_id, current_user)

@router.post("/{approval_id}/approve", response_model=ApprovalResponse)
def approve_request(
    approval_id: int,
    payload: ApprovalApprovePayload = ApprovalApprovePayload(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Aprova uma solicitação pendente.
    Apenas ADMIN ou MANAGER do módulo correspondente podem aprovar.
    Impede auto-aprovação de usuários não-admin.
    """
    return ApprovalService.approve_approval(
        db,
        approval_id,
        current_user,
        reason=payload.reason,
        result_payload=payload.result_payload
    )

@router.post("/{approval_id}/reject", response_model=ApprovalResponse)
def reject_request(
    approval_id: int,
    payload: ApprovalRejectPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Rejeita uma solicitação pendente com motivo opcional.
    Apenas ADMIN ou MANAGER do módulo correspondente podem rejeitar.
    """
    return ApprovalService.reject_approval(db, approval_id, payload.reason, current_user, payload.result_payload)

@router.post("/{approval_id}/cancel", response_model=ApprovalResponse)
def cancel_request(
    approval_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cancela uma solicitação pendente.
    Apenas o solicitante original ou um ADMIN podem cancelar.
    """
    return ApprovalService.cancel_approval(db, approval_id, current_user)

@router.post("/{approval_id}/comments", response_model=ApprovalCommentResponse)
def add_approval_comment(
    approval_id: int,
    payload: ApprovalCommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Adiciona um comentário à solicitação de aprovação informada.
    """
    return ApprovalService.add_comment(db, approval_id, payload.comment, current_user)
