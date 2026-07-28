import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.permissions import get_current_user
from app.models.user import User
from app.modules.action_commands.service import ActionCommandsService
from app.modules.action_commands.schemas import (
    ActionCommandParseRequest,
    ActionCommandPrepareRequest,
    ActionCommandConfirmRequest,
    ActionCommandDraftRead,
    AvailableAction
)

router = APIRouter()

@router.post("/parse", response_model=ActionCommandDraftRead)
def parse_command(
    payload: ActionCommandParseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Analisa texto livre do Chat ou barra global e retorna uma prévia da ação sugerida.
    """
    return ActionCommandsService.parse_command(
        db=db,
        text=payload.text,
        source=payload.source,
        context=payload.context,
        current_user=current_user
    )

@router.post("/prepare", response_model=ActionCommandDraftRead)
def prepare_action(
    payload: ActionCommandPrepareRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Prepara um rascunho de ação contextual direto da UI (ex: drawer, botão rápido de módulo).
    """
    return ActionCommandsService.prepare_action(
        db=db,
        action_key=payload.action_key,
        source=payload.source,
        source_module=payload.source_module,
        source_entity_type=payload.source_entity_type,
        source_entity_id=payload.source_entity_id,
        raw_text=None,
        initial_data=payload.initial_data or {},
        current_user=current_user
    )

@router.post("/{draft_id}/confirm", response_model=ActionCommandDraftRead)
def confirm_action(
    draft_id: uuid.UUID,
    payload: ActionCommandConfirmRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Confirma e executa a ação proposta ou gera uma Action Intent técnica (caso seja sensível).
    """
    return ActionCommandsService.confirm_action(
        db=db,
        draft_id=draft_id,
        override_data=payload.override_data or {},
        current_user=current_user
    )

@router.post("/{draft_id}/cancel", response_model=ActionCommandDraftRead)
def cancel_action(
    draft_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cancela o rascunho de comando proposto.
    """
    return ActionCommandsService.cancel_action(
        db=db,
        draft_id=draft_id,
        current_user=current_user
    )

@router.get("/recent", response_model=List[ActionCommandDraftRead])
def get_recent_commands(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retorna a lista de comandos e ações propostas recentes do usuário logado.
    """
    return ActionCommandsService.get_recent_commands(db=db, current_user=current_user, limit=limit)

@router.get("/available-actions", response_model=List[AvailableAction])
def get_available_actions(
    module: Optional[str] = None,
    entity_type: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Retorna as ações disponíveis filtradas por módulo e/ou tipo de entidade para renderizar botões contextuais.
    """
    return ActionCommandsService.get_available_actions(module=module, entity_type=entity_type)
