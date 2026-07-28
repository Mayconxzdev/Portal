import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict
from sqlalchemy.orm import Session

from app.models.event_log import EventLog
from app.models.reaction_rule import ReactionRule
from app.models.reaction_rule_run import ReactionRuleRun
from app.core.events import emit_event

logger = logging.getLogger("vesper.reactions")

# Ações permitidas por questões de segurança
ALLOWED_ACTION_TYPES = {
    "create_notification",
    "create_action_intent",
    "add_audit_note",
    "dry_run_log",
    "no_op"
}

# Ações bloqueadas explicitamente
BLOCKED_ACTION_TYPES = {
    "send_email",
    "update_stock",
    "create_purchase_order",
    "approve_approval",
    "reject_approval",
    "reveal_secret",
    "change_permission",
    "delete_file",
    "external_webhook",
    "n8n_call"
}


def get_field_value(obj: Any, field_path: str) -> Any:
    """
    Extrai um valor do objeto contexto usando a notação de ponto.
    Exemplo: field_path="payload.priority" retorna context["payload"]["priority"].
    """
    parts = field_path.split('.')
    current = obj
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        elif hasattr(current, part):
            current = getattr(current, part)
        else:
            return None
    return current


def evaluate_single_condition(condition: Dict[str, Any], context: Dict[str, Any]) -> bool:
    """
    Avalia uma única condição baseada em operando e valor.
    """
    if condition.get("always") is True or condition.get("op") == "always":
        return True
        
    field = condition.get("field")
    if not field:
        return False
        
    val = get_field_value(context, field)
    op = condition.get("op")
    target = condition.get("value")
    
    if op == "equals":
        return val == target
    elif op == "not_equals":
        return val != target
    elif op == "exists":
        return val is not None
    elif op == "in":
        if isinstance(target, list):
            return val in target
        return False
    elif op == "contains":
        if val is None:
            return False
        if isinstance(val, (list, str)):
            return target in val
        return False
    return False


def evaluate_conditions(condition_json: Dict[str, Any], context: Dict[str, Any]) -> bool:
    """
    Avalia condições estruturadas usando "all" ou "any" ou formato simples.
    """
    if not condition_json:
        return True
        
    if "all" in condition_json:
        conds = condition_json["all"]
        if not isinstance(conds, list):
            return False
        return all(evaluate_single_condition(c, context) for c in conds)
        
    if "any" in condition_json:
        conds = condition_json["any"]
        if not isinstance(conds, list):
            return False
        return any(evaluate_single_condition(c, context) for c in conds)
        
    return evaluate_single_condition(condition_json, context)


def check_rule_limits(db: Session, rule: ReactionRule) -> tuple[bool, str]:
    """
    Valida limites de cooldown e max_runs_per_hour para a regra fornecida.
    Retorna (pode_executar, status_motivo).
    """
    now = datetime.now(timezone.utc)
    
    # 1. Cooldown seconds check
    if rule.cooldown_seconds:
        cooldown_limit = now - timedelta(seconds=rule.cooldown_seconds)
        last_run = db.query(ReactionRuleRun).filter(
            ReactionRuleRun.rule_id == rule.id,
            ReactionRuleRun.status.in_(["EXECUTED", "FAILED", "MATCHED", "BLOCKED"]),
            ReactionRuleRun.created_at >= cooldown_limit
        ).order_by(ReactionRuleRun.created_at.desc()).first()
        
        if last_run:
            return False, "SKIPPED"  # Cooldown active
            
    # 2. Max runs per hour check
    if rule.max_runs_per_hour:
        hour_limit = now - timedelta(hours=1)
        runs_count = db.query(ReactionRuleRun).filter(
            ReactionRuleRun.rule_id == rule.id,
            ReactionRuleRun.status.in_(["EXECUTED", "FAILED", "MATCHED", "BLOCKED"]),
            ReactionRuleRun.created_at >= hour_limit
        ).count()
        
        if runs_count >= rule.max_runs_per_hour:
            return False, "SKIPPED"  # Hourly limit exceeded
            
    return True, ""


def execute_reaction_action(db: Session, rule: ReactionRule, event: EventLog) -> Dict[str, Any]:
    """
    Tenta executar a ação canônica do reaction engine no backend.
    Sempre injeta source="reaction_engine" nos metadados para novos eventos
    visando evitar loop infinito.
    """
    action_type = rule.action_type
    payload = rule.action_payload or {}
    
    if action_type == "no_op":
        logger.info(f"[REACTION ENGINE] No-op executed for rule {rule.name}")
        return {"message": "No-op executed successfully"}
        
    elif action_type == "dry_run_log":
        logger.info(f"[REACTION ENGINE] Dry run executed successfully for rule {rule.name}. Params: {payload}")
        return {"dry_run": True, "params": payload}
        
    elif action_type == "add_audit_note":
        logger.info(f"[REACTION AUDIT] Rule '{rule.name}' matched. Context: {payload}")
        return {"audit_note_added": True}
        
    elif action_type == "create_notification":
        from app.modules.notifications.service import create_notification
        
        # Constrói notificação usando metadados e parâmetros configurados
        user_id = payload.get("user_id")
        role_target = payload.get("role_target")
        
        # Pode interpolar strings na mensagem
        msg = payload.get("message", "")
        if event.payload:
            for k, v in event.payload.items():
                msg = msg.replace(f"{{payload.{k}}}", str(v))
                
        notif = create_notification(
            db=db,
            user_id=user_id,
            role_target=role_target,
            module=rule.module,
            event_type=f"reaction.{rule.action_type}",
            title=payload.get("title", f"Regra: {rule.name}"),
            message=msg,
            severity=payload.get("severity", "INFO"),
            source_type="reaction_rule",
            source_id=str(rule.id),
            action_url=payload.get("action_url"),
            payload_json=event.payload,
            correlation_id=event.correlation_id,
            tenant_id=rule.tenant_id
        )
        return {"notification_id": str(notif.id)}
        
    elif action_type == "create_action_intent":
        from app.modules.action_intents.service import create_action_intent
        from app.modules.action_intents.schemas import ActionIntentCreateInternal
        
        # Injeta correlation_id do evento original e marca origem
        intent_in = ActionIntentCreateInternal(
            source="reaction_engine",
            source_ref_type="reaction_rule",
            source_ref_id=str(rule.id),
            proposed_action=payload.get("proposed_action"),
            target_module=payload.get("target_module"),
            target_type=payload.get("target_type"),
            target_id=payload.get("target_id"),
            title=payload.get("title", f"Sugerido por {rule.name}"),
            summary=payload.get("summary", ""),
            action_payload=payload.get("action_payload", {}),
            correlation_id=event.correlation_id,
            tenant_id=rule.tenant_id
        )
        intent = create_action_intent(db=db, intent_in=intent_in)
        return {"action_intent_id": str(intent.id)}
        
    raise ValueError(f"Unknown or unsupported action type: {action_type}")


def process_reactions_for_event(event: EventLog, db: Session) -> None:
    """
    Avalia todas as regras de reação cadastradas e ativas para o tipo do evento fornecido.
    Grava os logs de execução (reaction_rule_runs) no banco de dados.
    """
    # 1. Prevenção de loop infinito
    # Se o evento foi gerado pelo próprio reaction_engine, ignoramos
    metadata = event.metadata_json or {}
    if metadata.get("source") == "reaction_engine":
        logger.debug(f"[REACTION ENGINE] Ignorando evento {event.event_type} ({event.id}) com origem em reaction_engine.")
        return

    # 2. Busca todas as regras ativas ordenadas por prioridade decrescente
    rules = db.query(ReactionRule).filter(
        ReactionRule.event_type == event.event_type,
        ReactionRule.enabled == True
    ).order_by(ReactionRule.priority.desc()).all()
    
    if not rules:
        return
        
    logger.info(f"[REACTION ENGINE] Avaliando {len(rules)} regras para o evento {event.event_type} (ID: {event.id})")
    
    context = {
        "payload": event.payload or {},
        "event_type": event.event_type,
        "actor_user_id": event.actor_user_id,
        "module": event.module
    }
    
    for rule in rules:
        run_record = ReactionRuleRun(
            rule_id=rule.id,
            event_id=event.id,
            status="PENDING",
            condition_result=False,
            correlation_id=event.correlation_id
        )
        db.add(run_record)
        db.flush()
        
        try:
            # 3. Validação de Cooldown e Limits
            can_run, skip_status = check_rule_limits(db, rule)
            if not can_run:
                run_record.status = skip_status
                db.flush()
                continue
                
            # 4. Avaliação de condições
            cond_passed = evaluate_conditions(rule.condition_json, context)
            run_record.condition_result = cond_passed
            
            if not cond_passed:
                run_record.status = "SKIPPED"
                db.flush()
                continue
                
            run_record.status = "MATCHED"
            db.flush()
            
            # 5. Validação de Segurança de Ações
            if rule.action_type in BLOCKED_ACTION_TYPES or rule.action_type not in ALLOWED_ACTION_TYPES:
                run_record.status = "BLOCKED"
                run_record.error_message = f"Action '{rule.action_type}' is blocked for security reasons."
                db.flush()
                
                # Opcional: emitir evento de bloqueio
                emit_event(
                    db=db,
                    event_type="automation.reaction.blocked",
                    aggregate_type="reaction_rule",
                    aggregate_id=str(rule.id),
                    module="automations",
                    payload={
                        "rule_name": rule.name,
                        "action_type": rule.action_type,
                        "reason": "Security block"
                    },
                    metadata_json={"source": "reaction_engine"},
                    correlation_id=event.correlation_id,
                    tenant_id=rule.tenant_id
                )
                continue
                
            # 6. Execução da ação
            result = execute_reaction_action(db, rule, event)
            run_record.status = "EXECUTED"
            run_record.action_result = result
            run_record.executed_at = datetime.now(timezone.utc)
            db.flush()
            
            # Opcional: emitir evento de sucesso
            emit_event(
                db=db,
                event_type="automation.reaction.executed",
                aggregate_type="reaction_rule",
                aggregate_id=str(rule.id),
                module="automations",
                payload={
                    "rule_name": rule.name,
                    "action_type": rule.action_type,
                    "status": "success",
                    "result": result
                },
                metadata_json={"source": "reaction_engine"},
                correlation_id=event.correlation_id,
                tenant_id=rule.tenant_id
            )
            
        except Exception as err:
            run_record.status = "FAILED"
            run_record.error_message = str(err)
            db.flush()
            logger.error(f"[REACTION ENGINE] Erro ao executar a regra {rule.name}: {err}")


def seed_initial_reaction_rules(db: Session) -> None:
    """
    Cria as 3 regras de reação padrão/iniciais se elas não existirem no banco de dados.
    """
    seeds = [
        {
            "name": "Notificar gestores sobre nova acao sugerida",
            "description": "Envia notificacao para managers quando uma action intent de automacao for criada",
            "event_type": "automation.action_intent.created",
            "module": "automations",
            "enabled": True,
            "priority": 10,
            "condition_json": {},
            "action_type": "create_notification",
            "action_payload": {
                "role_target": "MANAGER",
                "title": "Acao sugerida pendente",
                "message": "Uma nova acao sugerida precisa de revisao.",
                "severity": "INFO",
                "action_url": "/automations"
            }
        },
        {
            "name": "Notificar administradores sobre falha de automacao",
            "description": "Envia notificacao para admins caso a execucao de uma action intent falhe",
            "event_type": "automation.action_intent.execution.failed",
            "module": "automations",
            "enabled": True,
            "priority": 10,
            "condition_json": {},
            "action_type": "create_notification",
            "action_payload": {
                "role_target": "ADMIN",
                "title": "Falha na execucao",
                "message": "A execucao de uma acao automatizada falhou.",
                "severity": "ERROR",
                "action_url": "/automations"
            }
        },
        {
            "name": "Notificar TI sobre chamado critico",
            "description": "Envia notificacao para gestores/TI caso um chamado seja criado com prioridade CRITICAL",
            "event_type": "it.ticket.created",
            "module": "it",
            "enabled": True,
            "priority": 20,
            "condition_json": {
                "field": "payload.priority",
                "op": "equals",
                "value": "CRITICAL"
            },
            "action_type": "create_notification",
            "action_payload": {
                "role_target": "MANAGER",
                "title": "Novo chamado critico de TI",
                "message": "Um novo chamado de TI com prioridade critica foi aberto: '{payload.title}'.",
                "severity": "CRITICAL",
                "action_url": "/it"
            }
        }
    ]
    
    for seed in seeds:
        rule = db.query(ReactionRule).filter(ReactionRule.name == seed["name"]).first()
        if not rule:
            rule = ReactionRule(
                name=seed["name"],
                description=seed["description"],
                event_type=seed["event_type"],
                module=seed["module"],
                enabled=seed["enabled"],
                priority=seed["priority"],
                condition_json=seed["condition_json"],
                action_type=seed["action_type"],
                action_payload=seed["action_payload"]
            )
            db.add(rule)
            logger.info(f"[SEED] Regra de reacao '{seed['name']}' semeada com sucesso.")
            
    db.commit()

