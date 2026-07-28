import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import get_current_user
from app.models.user import User
from app.models.reaction_rule import ReactionRule
from app.models.reaction_rule_run import ReactionRuleRun
from app.modules.reactions.schemas import ReactionRuleCreate, ReactionRuleRead, ReactionRuleRunRead, ReactionRuleToggleEnabled
from app.core.audit import log_action
from app.core.events import emit_event

router = APIRouter()

def require_admin_or_manager(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.role or current_user.role.name not in ("ADMIN", "MANAGER"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Recurso restrito a administradores ou gerentes."
        )
    return current_user


@router.get("/rules", response_model=List[ReactionRuleRead])
def get_reaction_rules(
    event_type: Optional[str] = Query(None),
    module: Optional[str] = Query(None),
    enabled: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """
    Retorna a lista de regras de reação cadastradas.
    """
    query = db.query(ReactionRule)
    if event_type is not None:
        query = query.filter(ReactionRule.event_type == event_type)
    if module is not None:
        query = query.filter(ReactionRule.module == module)
    if enabled is not None:
        query = query.filter(ReactionRule.enabled == enabled)
        
    return query.order_by(ReactionRule.priority.desc(), ReactionRule.created_at.desc()).limit(limit).all()


@router.post("/rules", response_model=ReactionRuleRead)
def create_reaction_rule(
    rule_in: ReactionRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """
    Cria uma nova regra de reação.
    """
    rule = ReactionRule(
        name=rule_in.name,
        description=rule_in.description,
        event_type=rule_in.event_type,
        module=rule_in.module,
        enabled=rule_in.enabled,
        priority=rule_in.priority,
        condition_json=rule_in.condition_json,
        action_type=rule_in.action_type,
        action_payload=rule_in.action_payload,
        cooldown_seconds=rule_in.cooldown_seconds,
        max_runs_per_hour=rule_in.max_runs_per_hour,
        created_by_user_id=current_user.id,
        tenant_id=rule_in.tenant_id
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.patch("/rules/{id}/enabled", response_model=ReactionRuleRead)
def toggle_reaction_rule(
    id: uuid.UUID,
    enabled_in: ReactionRuleToggleEnabled,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """
    Ativa ou desativa uma regra de reação.
    """
    rule = db.query(ReactionRule).filter(ReactionRule.id == id).first()
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Regra de reação não encontrada."
        )
        
    old_enabled = rule.enabled
    rule.enabled = enabled_in.enabled
    db.commit()
    db.refresh(rule)
    
    # Registra auditoria
    log_action(
        db=db,
        user_id=current_user.id,
        action="toggle_enabled",
        module="reactions",
        details={
            "rule_id": str(rule.id),
            "rule_name": rule.name,
            "old_enabled": old_enabled,
            "new_enabled": rule.enabled
        },
        commit=True
    )
    
    # Emite evento automation.reaction_rule.enabled_changed
    emit_event(
        db=db,
        event_type="automation.reaction_rule.enabled_changed",
        aggregate_type="reaction_rule",
        aggregate_id=str(rule.id),
        module="automations",
        payload={
            "rule_name": rule.name,
            "old_enabled": old_enabled,
            "new_enabled": rule.enabled
        },
        actor_user_id=current_user.id
    )
    db.commit()
    
    return rule


@router.get("/runs", response_model=List[ReactionRuleRunRead])
def get_reaction_runs(
    rule_id: Optional[uuid.UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    event_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """
    Retorna o histórico de execuções de regras de reação.
    """
    query = db.query(ReactionRuleRun)
    if rule_id is not None:
        query = query.filter(ReactionRuleRun.rule_id == rule_id)
    if status_filter is not None:
        query = query.filter(ReactionRuleRun.status == status_filter)
    if event_type is not None:
        query = query.join(ReactionRule).filter(ReactionRule.event_type == event_type)
        
    return query.order_by(ReactionRuleRun.created_at.desc()).limit(limit).all()
