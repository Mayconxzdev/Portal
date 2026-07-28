import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy.orm import Session
from app.models.action_intent import ActionIntent
from app.models.action_intent_execution import ActionIntentExecution
from app.modules.action_intents.schemas import ActionIntentCreateInternal
from app.core.events import emit_event

logger = logging.getLogger("vesper.modules.action_intents.service")


def classify_action_risk(proposed_action: str, target_module: str, payload: dict) -> str:
    """
    Classifica o nível de risco de uma ação proposta.
    Retorna CRITICAL, HIGH, MEDIUM ou LOW.
    """
    proposed_action_lower = proposed_action.lower()
    
    # CRITICAL: acoes sensiveis. Revelar senha continua critico, mas o fluxo
    # oficial do Cofre executa direto com permissao + auditoria, sem aprovacao previa.
    critical_actions = {"reveal_secret", "change_permission", "delete_file", "approve_payment"}
    if proposed_action_lower in critical_actions:
        return "CRITICAL"
        
    # HIGH: desembolso real, estoque, permissao ou decisao formal.
    high_actions = {
        "approve_approval", "reject_approval", "create_purchase_order", "update_stock"
    }
    if proposed_action_lower in high_actions:
        return "HIGH"

    # LOW: trabalho normal de modulo. Se o usuario tem permissao no modulo, o
    # Portal nao deve criar aprovacao indevida para operar o dia a dia.
    low_actions = {
        "create_draft",
        "summarize",
        "classify",
        "notify",
        "suggest",
        "send_rfq",
        "send_supplier_quote_email",
        "send_email_to_supplier",
        "register_supplier_response",
        "create_quote_response",
        "update_price_ref",
        "update_price_reference",
        "update_purchase_price",
        "create_kanban_card",
        "move_kanban_card",
        "create_it_ticket",
        "resolve_it_ticket",
        "create_proposal",
        "generate_proposal_pdf",
        "send_proposal",
    }
    if proposed_action_lower in low_actions:
        return "LOW"

    # MEDIUM: mudancas operacionais que exigem confirmacao/revisao no modulo,
    # mas nao aprovacao formal fora dele.
    medium_actions = {"update_proposal_status"}
    if proposed_action_lower in medium_actions:
        return "MEDIUM"
        
    return "MEDIUM"


def create_action_intent(db: Session, intent_in: ActionIntentCreateInternal) -> ActionIntent:
    """
    Cria uma intenção de ação no banco, classifica o risco e emite o evento automation.action_intent.created.
    """
    risk = classify_action_risk(intent_in.proposed_action, intent_in.target_module, intent_in.action_payload)
    
    # Se o status não for definido ou for PENDING_REVIEW padrão, decide baseado no risco
    status = intent_in.status
    if not status or status == "PENDING_REVIEW":
        proposed_action_lower = intent_in.proposed_action.lower()
        if proposed_action_lower == "reveal_secret":
            status = "AUDIT_REQUIRED"
        elif risk in ("MEDIUM", "HIGH", "CRITICAL"):
            status = "APPROVAL_REQUIRED"
        else:
            status = "PENDING_REVIEW"

    db_intent = ActionIntent(
        source=intent_in.source,
        source_ref_type=intent_in.source_ref_type,
        source_ref_id=intent_in.source_ref_id,
        proposed_action=intent_in.proposed_action,
        target_module=intent_in.target_module,
        target_type=intent_in.target_type,
        target_id=intent_in.target_id,
        title=intent_in.title,
        summary=intent_in.summary,
        risk_level=risk,
        status=status,
        action_payload=intent_in.action_payload,
        result_payload=intent_in.result_payload,
        reason=intent_in.reason,
        approval_id=intent_in.approval_id,
        callback_log_id=intent_in.callback_log_id,
        event_id=intent_in.event_id,
        created_by_user_id=intent_in.created_by_user_id,
        reviewed_by_user_id=intent_in.reviewed_by_user_id,
        expires_at=intent_in.expires_at,
        correlation_id=intent_in.correlation_id,
        tenant_id=intent_in.tenant_id
    )
    db.add(db_intent)
    db.commit()
    db.refresh(db_intent)
    
    # Emite evento do outbox (best-effort)
    try:
        emit_event(
            db=db,
            event_type="automation.action_intent.created",
            aggregate_type="action_intent",
            aggregate_id=str(db_intent.id),
            module="automations",
            payload={
                "id": str(db_intent.id),
                "proposed_action": db_intent.proposed_action,
                "risk_level": db_intent.risk_level,
                "status": db_intent.status
            },
            actor_user_id=db_intent.created_by_user_id,
            correlation_id=db_intent.correlation_id,
            tenant_id=db_intent.tenant_id
        )
        db.commit()
    except Exception as e:
        logger.warning(f"Failed to emit automation.action_intent.created event: {e}")
        
    return db_intent


def get_action_intent(db: Session, intent_id: uuid.UUID) -> Optional[ActionIntent]:
    """
    Retorna uma ActionIntent pelo seu ID UUID.
    """
    return db.query(ActionIntent).filter(ActionIntent.id == intent_id).first()


def list_action_intents(
    db: Session,
    status: Optional[str] = None,
    source: Optional[str] = None,
    target_module: Optional[str] = None,
    risk_level: Optional[str] = None,
    limit: int = 50
) -> List[ActionIntent]:
    """
    Lista as ActionIntents com filtros de busca opcionais.
    """
    query = db.query(ActionIntent)
    if status:
        query = query.filter(ActionIntent.status == status)
    if source:
        query = query.filter(ActionIntent.source == source)
    if target_module:
        query = query.filter(ActionIntent.target_module == target_module)
    if risk_level:
        query = query.filter(ActionIntent.risk_level == risk_level)
    return query.order_by(ActionIntent.created_at.desc()).limit(limit).all()


def reject_action_intent(db: Session, intent_id: uuid.UUID, user_id: int, reason: str) -> Optional[ActionIntent]:
    """
    Rejeita uma ActionIntent, atribuindo status REJECTED, revisor e justificativa. Emite automation.action_intent.rejected.
    """
    db_intent = db.query(ActionIntent).filter(ActionIntent.id == intent_id).first()
    if not db_intent:
        return None
        
    db_intent.status = "REJECTED"
    db_intent.reviewed_by_user_id = user_id
    db_intent.reviewed_at = datetime.now(timezone.utc)
    db_intent.reason = reason
    
    db.commit()
    db.refresh(db_intent)
    
    try:
        emit_event(
            db=db,
            event_type="automation.action_intent.rejected",
            aggregate_type="action_intent",
            aggregate_id=str(db_intent.id),
            module="automations",
            payload={
                "id": str(db_intent.id),
                "reason": reason
            },
            actor_user_id=user_id,
            correlation_id=db_intent.correlation_id,
            tenant_id=db_intent.tenant_id
        )
        db.commit()
    except Exception as e:
        logger.warning(f"Failed to emit automation.action_intent.rejected event: {e}")
        
    return db_intent


def mark_reviewed_action_intent(db: Session, intent_id: uuid.UUID, user_id: int, reason: Optional[str] = None) -> Optional[ActionIntent]:
    """
    Marca uma ActionIntent como revisada, alterando o status para APPROVED. Emite automation.action_intent.reviewed.
    """
    db_intent = db.query(ActionIntent).filter(ActionIntent.id == intent_id).first()
    if not db_intent:
        return None
        
    db_intent.status = "APPROVED"
    db_intent.reviewed_by_user_id = user_id
    db_intent.reviewed_at = datetime.now(timezone.utc)
    if reason:
        db_intent.reason = reason
        
    db.commit()
    db.refresh(db_intent)
    
    try:
        emit_event(
            db=db,
            event_type="automation.action_intent.reviewed",
            aggregate_type="action_intent",
            aggregate_id=str(db_intent.id),
            module="automations",
            payload={
                "id": str(db_intent.id),
                "reason": reason
            },
            actor_user_id=user_id,
            correlation_id=db_intent.correlation_id,
            tenant_id=db_intent.tenant_id
        )
        db.commit()
    except Exception as e:
        logger.warning(f"Failed to emit automation.action_intent.reviewed event: {e}")
        
    return db_intent


SAFE_ACTIONS = {
    "notify",
    "create_draft",
    "classify",
    "summarize",
    "suggest",
    "send_rfq",
    "send_supplier_quote_email",
    "send_email_to_supplier",
    "register_supplier_response",
    "create_quote_response",
    "update_price_ref",
    "update_price_reference",
    "update_purchase_price",
    "create_kanban_card",
    "move_kanban_card",
    "create_it_ticket",
    "resolve_it_ticket",
    "create_proposal",
    "generate_proposal_pdf",
    "send_proposal",
}
BLOCKED_ACTIONS = {
    "update_stock", "create_purchase_order",
    "approve_approval", "reject_approval", "reveal_secret", "change_permission", "delete_file"
}

def execute_action_intent(
    db: Session,
    intent_id: uuid.UUID,
    actor_user_id: int,
    idempotency_key: str,
    dry_run: bool = False
) -> ActionIntentExecution:
    # 1. Idempotency Check
    existing_execution = db.query(ActionIntentExecution).filter(
        ActionIntentExecution.idempotency_key == idempotency_key
    ).first()
    if existing_execution:
        logger.info(f"Replay detected for idempotency key {idempotency_key}. Returning existing execution.")
        return existing_execution

    # 2. Get ActionIntent
    intent = db.query(ActionIntent).filter(ActionIntent.id == intent_id).first()
    if not intent:
        raise ValueError("Intenção de ação não encontrada.")

    # 3. Status Check
    if intent.status != "APPROVED":
        raise ValueError(f"Intenção não pode ser executada no status atual: {intent.status}")

    proposed_action = intent.proposed_action.lower()

    # 4. Dry Run Logic
    if dry_run:
        if proposed_action in BLOCKED_ACTIONS or proposed_action not in SAFE_ACTIONS:
            execution = ActionIntentExecution(
                id=uuid.uuid4(),
                action_intent_id=intent.id,
                executor_key=proposed_action,
                idempotency_key=idempotency_key,
                status="BLOCKED",
                attempts=1,
                input_payload=intent.action_payload,
                result_payload={"dry_run": True, "detail": "Ação perigosa bloqueada no dry run."},
                error_message="Ação de negócio bloqueada.",
                created_by_user_id=actor_user_id,
                correlation_id=intent.correlation_id,
                created_at=datetime.now(timezone.utc)
            )
            return execution
        else:
            execution = ActionIntentExecution(
                id=uuid.uuid4(),
                action_intent_id=intent.id,
                executor_key=proposed_action,
                idempotency_key=idempotency_key,
                status="SUCCEEDED",
                attempts=1,
                input_payload=intent.action_payload,
                result_payload={"dry_run": True, "detail": "Ação segura executável (simulação)."},
                created_by_user_id=actor_user_id,
                correlation_id=intent.correlation_id,
                created_at=datetime.now(timezone.utc)
            )
            return execution

    # 5. Real (Simulated) Execution
    execution = ActionIntentExecution(
        action_intent_id=intent.id,
        executor_key=proposed_action,
        idempotency_key=idempotency_key,
        status="RUNNING",
        started_at=datetime.now(timezone.utc),
        attempts=1,
        input_payload=intent.action_payload,
        created_by_user_id=actor_user_id,
        correlation_id=intent.correlation_id
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)

    # Emit Started Event
    try:
        emit_event(
            db=db,
            event_type="automation.action_intent.execution.started",
            aggregate_type="action_intent_execution",
            aggregate_id=str(execution.id),
            module="automations",
            payload={"execution_id": str(execution.id), "action_intent_id": str(intent.id)},
            actor_user_id=actor_user_id,
            correlation_id=intent.correlation_id,
            tenant_id=intent.tenant_id
        )
        db.commit()
    except Exception as e:
        logger.warning(f"Failed to emit execution.started event: {e}")

    # Check action category
    if proposed_action in BLOCKED_ACTIONS or proposed_action not in SAFE_ACTIONS:
        execution.status = "BLOCKED"
        execution.finished_at = datetime.now(timezone.utc)
        execution.result_payload = {"error": "Execution blocked: action is sensitive."}
        execution.error_message = "Execução bloqueada: ação sensível requer canal seguro/futuro."

        intent.status = "EXECUTION_BLOCKED"
        db.commit()
        db.refresh(execution)
        db.refresh(intent)

        # Emit Blocked Event
        try:
            emit_event(
                db=db,
                event_type="automation.action_intent.execution.blocked",
                aggregate_type="action_intent_execution",
                aggregate_id=str(execution.id),
                module="automations",
                payload={"execution_id": str(execution.id), "action_intent_id": str(intent.id), "reason": execution.error_message},
                actor_user_id=actor_user_id,
                correlation_id=intent.correlation_id,
                tenant_id=intent.tenant_id
            )
            db.commit()
        except Exception as e:
            logger.warning(f"Failed to emit execution.blocked event: {e}")

        return execution

    else:
        try:
            result = {
                "status": "simulated_success",
                "proposed_action": proposed_action,
                "message": f"Ação {proposed_action} executada com sucesso de forma segura.",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            execution.status = "SUCCEEDED"
            execution.finished_at = datetime.now(timezone.utc)
            execution.result_payload = result

            intent.status = "EXECUTED"
            db.commit()
            db.refresh(execution)
            db.refresh(intent)

            # Emit Succeeded Event
            try:
                emit_event(
                    db=db,
                    event_type="automation.action_intent.execution.succeeded",
                    aggregate_type="action_intent_execution",
                    aggregate_id=str(execution.id),
                    module="automations",
                    payload={"execution_id": str(execution.id), "action_intent_id": str(intent.id)},
                    actor_user_id=actor_user_id,
                    correlation_id=intent.correlation_id,
                    tenant_id=intent.tenant_id
                )
                db.commit()
            except Exception as e:
                logger.warning(f"Failed to emit execution.succeeded event: {e}")

            return execution

        except Exception as ex:
            execution.status = "FAILED"
            execution.finished_at = datetime.now(timezone.utc)
            execution.error_message = str(ex)
            execution.result_payload = {"error": str(ex)}

            intent.status = "FAILED"
            db.commit()
            db.refresh(execution)
            db.refresh(intent)

            # Emit Failed Event
            try:
                emit_event(
                    db=db,
                    event_type="automation.action_intent.execution.failed",
                    aggregate_type="action_intent_execution",
                    aggregate_id=str(execution.id),
                    module="automations",
                    payload={"execution_id": str(execution.id), "action_intent_id": str(intent.id), "error": str(ex)},
                    actor_user_id=actor_user_id,
                    correlation_id=intent.correlation_id,
                    tenant_id=intent.tenant_id
                )
                db.commit()
            except Exception as e:
                logger.warning(f"Failed to emit execution.failed event: {e}")

            return execution
