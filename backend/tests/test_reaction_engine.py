import pytest
from fastapi import status
from datetime import datetime, timezone
import uuid

from app.core.events import emit_event
from app.core.security import create_access_token
from app.models.reaction_rule import ReactionRule
from app.models.reaction_rule_run import ReactionRuleRun
from app.models.notification import Notification
from app.modules.reactions import service


def auth_headers(username: str) -> dict[str, str]:
    token = create_access_token(subject=username)
    return {"Authorization": f"Bearer {token}"}


def test_reaction_rule_always_executed(db):
    # 1. Cria regra always
    rule = ReactionRule(
        name="Regra Teste Always",
        description="Executa sempre",
        event_type="test.reaction.always",
        module="test",
        enabled=True,
        priority=1,
        condition_json={"op": "always"},
        action_type="no_op",
        action_payload={}
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)

    # 2. Emite evento correspondente
    event = emit_event(
        db=db,
        event_type="test.reaction.always",
        aggregate_type="test",
        aggregate_id="1",
        module="test",
        payload={"foo": "bar"}
    )
    db.commit()

    # 3. Processa reações manualmente para garantir que rodou síncrono nos testes
    # O dispatcher já chama isso, mas chamamos para controle explícito
    service.process_reactions_for_event(event, db)
    db.commit()

    # 4. Verifica se gerou execução com status EXECUTED
    run = db.query(ReactionRuleRun).filter(ReactionRuleRun.rule_id == rule.id).first()
    assert run is not None
    assert run.status == "EXECUTED"
    assert run.condition_result is True


def test_reaction_rule_operators(db):
    # Cria regra com operadores compostos (all)
    rule = ReactionRule(
        name="Regra Teste Operadores",
        description="Filtra por prioridade e autor",
        event_type="test.reaction.operators",
        module="test",
        enabled=True,
        priority=5,
        condition_json={
            "all": [
                {"field": "payload.priority", "op": "equals", "value": "CRITICAL"},
                {"field": "payload.author", "op": "not_equals", "value": "bot"},
                {"field": "payload.tags", "op": "contains", "value": "security"},
                {"field": "payload.owner", "op": "exists"}
            ]
        },
        action_type="add_audit_note",
        action_payload={}
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)

    # Caso 1: Payload não atende
    event_fail = emit_event(
        db=db,
        event_type="test.reaction.operators",
        aggregate_type="test",
        aggregate_id="2",
        module="test",
        payload={
            "priority": "CRITICAL",
            "author": "bot",
            "tags": ["security"],
            "owner": "admin"
        }
    )
    db.commit()
    service.process_reactions_for_event(event_fail, db)
    db.commit()

    run_fail = db.query(ReactionRuleRun).filter(
        ReactionRuleRun.rule_id == rule.id,
        ReactionRuleRun.event_id == event_fail.id
    ).first()
    assert run_fail is not None
    assert run_fail.status == "SKIPPED"
    assert run_fail.condition_result is False

    # Caso 2: Payload atende perfeitamente
    event_pass = emit_event(
        db=db,
        event_type="test.reaction.operators",
        aggregate_type="test",
        aggregate_id="3",
        module="test",
        payload={
            "priority": "CRITICAL",
            "author": "user",
            "tags": ["monitoring", "security"],
            "owner": "admin"
        }
    )
    db.commit()
    service.process_reactions_for_event(event_pass, db)
    db.commit()

    run_pass = db.query(ReactionRuleRun).filter(
        ReactionRuleRun.rule_id == rule.id,
        ReactionRuleRun.event_id == event_pass.id
    ).first()
    assert run_pass is not None
    assert run_pass.status == "EXECUTED"
    assert run_pass.condition_result is True


def test_reaction_rule_blocked_action(db):
    # Cria regra com ação bloqueada
    rule = ReactionRule(
        name="Regra Acao Proibida",
        description="Tenta apagar arquivo",
        event_type="test.reaction.blocked_action",
        module="test",
        enabled=True,
        priority=1,
        condition_json={"op": "always"},
        action_type="delete_file",  # Ação perigosa bloqueada
        action_payload={"path": "/etc/passwd"}
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)

    event = emit_event(
        db=db,
        event_type="test.reaction.blocked_action",
        aggregate_type="test",
        aggregate_id="4",
        module="test",
        payload={}
    )
    db.commit()
    service.process_reactions_for_event(event, db)
    db.commit()

    run = db.query(ReactionRuleRun).filter(ReactionRuleRun.rule_id == rule.id).first()
    assert run is not None
    assert run.status == "BLOCKED"
    assert "blocked for security reasons" in run.error_message


def test_reaction_rule_disabled_does_not_execute(db):
    rule = ReactionRule(
        name="Regra Desativada",
        description="Esta desativada",
        event_type="test.reaction.disabled",
        module="test",
        enabled=False,  # Desativada
        priority=1,
        condition_json={"op": "always"},
        action_type="no_op",
        action_payload={}
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)

    event = emit_event(
        db=db,
        event_type="test.reaction.disabled",
        aggregate_type="test",
        aggregate_id="5",
        module="test",
        payload={}
    )
    db.commit()
    service.process_reactions_for_event(event, db)
    db.commit()

    run = db.query(ReactionRuleRun).filter(ReactionRuleRun.rule_id == rule.id).first()
    assert run is None  # Nenhuma execução deve ser gerada para regras desabilitadas


def test_reaction_rule_cooldown(db):
    rule = ReactionRule(
        name="Regra Cooldown",
        description="Evita flood de eventos",
        event_type="test.reaction.cooldown",
        module="test",
        enabled=True,
        priority=1,
        condition_json={"op": "always"},
        action_type="no_op",
        action_payload={},
        cooldown_seconds=60  # Cooldown ativo
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)

    # Primeiro evento: executa
    event1 = emit_event(db=db, event_type="test.reaction.cooldown", aggregate_type="t", aggregate_id="1", module="t", payload={})
    db.commit()
    service.process_reactions_for_event(event1, db)
    db.commit()

    # Segundo evento imediato: pula (SKIPPED)
    event2 = emit_event(db=db, event_type="test.reaction.cooldown", aggregate_type="t", aggregate_id="2", module="t", payload={})
    db.commit()
    service.process_reactions_for_event(event2, db)
    db.commit()

    run1 = db.query(ReactionRuleRun).filter(ReactionRuleRun.event_id == event1.id).first()
    run2 = db.query(ReactionRuleRun).filter(ReactionRuleRun.event_id == event2.id).first()

    assert run1.status == "EXECUTED"
    assert run2.status == "SKIPPED"


def test_reaction_rule_max_runs_per_hour(db):
    rule = ReactionRule(
        name="Regra Max Runs",
        description="Maximo de 2 execucoes por hora",
        event_type="test.reaction.max_runs",
        module="test",
        enabled=True,
        priority=1,
        condition_json={"op": "always"},
        action_type="no_op",
        action_payload={},
        max_runs_per_hour=2
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)

    # Dispara 3 eventos
    e1 = emit_event(db=db, event_type="test.reaction.max_runs", aggregate_type="t", aggregate_id="1", module="t", payload={})
    e2 = emit_event(db=db, event_type="test.reaction.max_runs", aggregate_type="t", aggregate_id="2", module="t", payload={})
    e3 = emit_event(db=db, event_type="test.reaction.max_runs", aggregate_type="t", aggregate_id="3", module="t", payload={})
    db.commit()

    service.process_reactions_for_event(e1, db)
    service.process_reactions_for_event(e2, db)
    service.process_reactions_for_event(e3, db)
    db.commit()

    run1 = db.query(ReactionRuleRun).filter(ReactionRuleRun.event_id == e1.id).first()
    run2 = db.query(ReactionRuleRun).filter(ReactionRuleRun.event_id == e2.id).first()
    run3 = db.query(ReactionRuleRun).filter(ReactionRuleRun.event_id == e3.id).first()

    assert run1.status == "EXECUTED"
    assert run2.status == "EXECUTED"
    assert run3.status == "SKIPPED"


def test_reaction_loop_prevention(db):
    rule = ReactionRule(
        name="Regra Evita Loop",
        description="Regra comum",
        event_type="test.reaction.loop",
        module="test",
        enabled=True,
        priority=1,
        condition_json={"op": "always"},
        action_type="no_op",
        action_payload={}
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)

    # Emite evento com source = reaction_engine nos metadados
    event = emit_event(
        db=db,
        event_type="test.reaction.loop",
        aggregate_type="test",
        aggregate_id="1",
        module="test",
        payload={},
        metadata_json={"source": "reaction_engine"}
    )
    db.commit()
    service.process_reactions_for_event(event, db)
    db.commit()

    # Nenhuma execução deve ser gerada para evitar loops
    run = db.query(ReactionRuleRun).filter(ReactionRuleRun.rule_id == rule.id).first()
    assert run is None


def test_admin_endpoints_authorization(client, db):
    # 1. Usuário comum deve ser bloqueado (HTTP 403)
    user_headers = auth_headers("vesper_user")
    res_rules = client.get("/api/v1/reactions/rules", headers=user_headers)
    assert res_rules.status_code == status.HTTP_403_FORBIDDEN

    # 2. Administrador deve acessar com sucesso (HTTP 200)
    admin_headers = auth_headers("vesper_admin")
    res_admin = client.get("/api/v1/reactions/rules", headers=admin_headers)
    assert res_admin.status_code == status.HTTP_200_OK

    # 3. Criação de regra de reação via POST /rules
    rule_payload = {
        "name": "Nova Regra API",
        "description": "Criada via API",
        "event_type": "api.test.event",
        "module": "api",
        "enabled": True,
        "priority": 10,
        "condition_json": {"op": "always"},
        "action_type": "no_op",
        "action_payload": {}
    }
    res_create = client.post("/api/v1/reactions/rules", json=rule_payload, headers=admin_headers)
    assert res_create.status_code == status.HTTP_200_OK
    created_rule = res_create.json()
    assert created_rule["name"] == "Nova Regra API"

    # 4. Listagem de execuções históricas
    res_runs = client.get("/api/v1/reactions/runs", headers=admin_headers)
    assert res_runs.status_code == status.HTTP_200_OK


def test_toggle_reaction_rule_permissions_and_fields(client, db):
    # Cria uma regra inicial
    rule = ReactionRule(
        name="Regra Para Testar Toggle",
        description="Descrição inicial",
        event_type="test.toggle",
        module="test",
        enabled=True,
        priority=3,
        condition_json={"op": "always"},
        action_type="no_op",
        action_payload={"secret_key": "some_secret"}
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)

    # 1. Usuário comum tenta desativar (HTTP 403)
    user_headers = auth_headers("vesper_user")
    res_toggle_user = client.patch(
        f"/api/v1/reactions/rules/{rule.id}/enabled",
        json={"enabled": False},
        headers=user_headers
    )
    assert res_toggle_user.status_code == status.HTTP_403_FORBIDDEN

    # 2. Administrador desativa com sucesso (HTTP 200)
    admin_headers = auth_headers("vesper_admin")
    res_toggle_admin = client.patch(
        f"/api/v1/reactions/rules/{rule.id}/enabled",
        json={"enabled": False},
        headers=admin_headers
    )
    assert res_toggle_admin.status_code == status.HTTP_200_OK
    data = res_toggle_admin.json()
    assert data["enabled"] is False

    # Garante que condition_json e action_payload NÃO foram alterados ou removidos
    assert data["condition_json"] == {"op": "always"}
    # Observe que "secret_key" deve ser mascarado no retorno, mas no banco continua intacto
    db.refresh(rule)
    assert rule.enabled is False
    assert rule.action_payload == {"secret_key": "some_secret"}

    # 3. Verifica se o evento automation.reaction_rule.enabled_changed foi emitido
    from app.models.event_log import EventLog
    event_changed = db.query(EventLog).filter(
        EventLog.event_type == "automation.reaction_rule.enabled_changed"
    ).order_by(EventLog.created_at.desc()).first()
    assert event_changed is not None
    assert event_changed.aggregate_id == str(rule.id)
    assert event_changed.payload["new_enabled"] is False

    # 4. Verifica se o log de auditoria foi gerado
    from app.models.audit_log import AuditLog
    audit_log = db.query(AuditLog).filter(
        AuditLog.module == "reactions",
        AuditLog.action == "toggle_enabled"
    ).order_by(AuditLog.created_at.desc()).first()
    assert audit_log is not None
    assert audit_log.details["rule_id"] == str(rule.id)
    assert audit_log.details["new_enabled"] is False


def test_reaction_payload_masking_in_api(client, db):
    # Cria uma regra com payload contendo chaves sensíveis
    rule = ReactionRule(
        name="Regra Sensivel",
        description="Regra com dados secretos",
        event_type="test.sensitive",
        module="test",
        enabled=True,
        condition_json={"op": "always"},
        action_type="no_op",
        action_payload={
            "api_key": "supersecretkey123",
            "password": "my_password",
            "public_field": "hello"
        }
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)

    # Executa a regra gerando uma execução com resultado contendo dados sensíveis
    event = emit_event(
        db=db,
        event_type="test.sensitive",
        aggregate_type="test",
        aggregate_id="masking_test",
        module="test",
        payload={}
    )
    db.commit()

    # Processa e preenche o action_result com dados sensíveis
    run = ReactionRuleRun(
        rule_id=rule.id,
        event_id=event.id,
        status="EXECUTED",
        condition_result=True,
        action_result={
            "token": "secret_token_abc",
            "authorization": "Bearer xyz123",
            "status": "success"
        }
    )
    db.add(run)
    db.commit()

    admin_headers = auth_headers("vesper_admin")

    # 1. Faz GET nas regras e verifica mascaramento do action_payload
    res_rules = client.get("/api/v1/reactions/rules", headers=admin_headers)
    assert res_rules.status_code == status.HTTP_200_OK
    rules_data = res_rules.json()
    matched_rule = next(r for r in rules_data if r["id"] == str(rule.id))
    
    assert matched_rule["action_payload"]["api_key"] == "******"
    assert matched_rule["action_payload"]["password"] == "******"
    assert matched_rule["action_payload"]["public_field"] == "hello"

    # 2. Faz GET nas execuções e verifica mascaramento do action_result
    res_runs = client.get("/api/v1/reactions/runs", headers=admin_headers)
    assert res_runs.status_code == status.HTTP_200_OK
    runs_data = res_runs.json()
    matched_run = next(r for r in runs_data if r["id"] == str(run.id))

    assert matched_run["action_result"]["token"] == "******"
    assert matched_run["action_result"]["authorization"] == "******"
    assert matched_run["action_result"]["status"] == "success"

