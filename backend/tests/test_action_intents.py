import pytest
import uuid
import hmac
import hashlib
import json
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi import status
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.approval import Approval
from app.models.event_log import EventLog
from app.models.automation_callback_log import AutomationCallbackLog
from app.models.action_intent import ActionIntent

from app.modules.action_intents.schemas import ActionIntentCreateInternal, ActionIntentRead
from app.modules.action_intents.service import (
    create_action_intent,
    classify_action_risk,
    reject_action_intent,
    mark_reviewed_action_intent
)
from app.core.events import emit_event

# Helper to generate signatures for callback test
def make_callback_headers(
    event_id: str,
    callback_type: str,
    timestamp: str,
    idempotency_key: str,
    body_dict: dict,
    secret: str = "vesper_n8n_local_secret"
):
    raw_body = json.dumps(body_dict, sort_keys=True, separators=(",", ":"))
    base_string = f"{timestamp}.{idempotency_key}.{raw_body}"
    sig = hmac.new(secret.encode("utf-8"), base_string.encode("utf-8"), hashlib.sha256).hexdigest()
    return {
        "X-Vesper-Event-Id": event_id,
        "X-Vesper-Callback-Type": callback_type,
        "X-Vesper-Timestamp": timestamp,
        "X-Vesper-Signature": sig,
        "X-Vesper-Signature-Version": "v1",
        "X-Idempotency-Key": idempotency_key
    }

def test_risk_classification():
    # Teste de classificação de riscos
    assert classify_action_risk("reveal_secret", "it", {}) == "CRITICAL"
    assert classify_action_risk("change_permission", "admin", {}) == "CRITICAL"
    assert classify_action_risk("delete_file", "files", {}) == "CRITICAL"
    assert classify_action_risk("approve_payment", "purchases", {}) == "CRITICAL"
    
    assert classify_action_risk("approve_approval", "approvals", {}) == "HIGH"
    assert classify_action_risk("reject_approval", "approvals", {}) == "HIGH"
    assert classify_action_risk("create_purchase_order", "purchases", {}) == "HIGH"
    assert classify_action_risk("update_stock", "stock", {}) == "HIGH"
    
    assert classify_action_risk("create_kanban_card", "kanban", {}) == "LOW"
    assert classify_action_risk("create_it_ticket", "it", {}) == "LOW"
    assert classify_action_risk("move_kanban_card", "kanban", {}) == "LOW"
    assert classify_action_risk("update_price_reference", "purchases", {}) == "LOW"
    assert classify_action_risk("send_email_to_supplier", "purchases", {"purpose": "quote_request"}) == "LOW"
    
    assert classify_action_risk("create_draft", "proposals", {}) == "LOW"
    assert classify_action_risk("summarize", "automations", {}) == "LOW"
    
    # Fallback
    assert classify_action_risk("unknown_action_here", "custom", {}) == "MEDIUM"

def test_create_action_intent_manually(db: Session):
    # Teste de criação manual via service
    intent_in = ActionIntentCreateInternal(
        source="system",
        proposed_action="create_draft",
        target_module="proposals",
        title="Rascunho de Proposta",
        summary="Criação automática de rascunho",
        risk_level="LOW",
        action_payload={"proposal_id": 456}
    )
    
    # Valida que emite evento automation.action_intent.created
    intent = create_action_intent(db, intent_in)
    assert intent.id is not None
    assert intent.risk_level == "LOW"
    assert intent.status == "PENDING_REVIEW"
    assert intent.proposed_action == "create_draft"
    
    # Verifica evento emitido no event_logs
    event = db.query(EventLog).filter(
        EventLog.event_type == "automation.action_intent.created",
        EventLog.aggregate_id == str(intent.id)
    ).first()
    assert event is not None
    assert event.payload["proposed_action"] == "create_draft"

def test_callback_action_requested_creates_intent(client, db: Session):
    # Cria uma aprovação real no banco para evitar violação de FK
    admin_user = db.query(User).filter(User.username == "vesper_admin").first()
    approval = Approval(
        title="Solicitação de Compra de Teste",
        description="Compra de insumos teste",
        module_slug="purchases",
        requester_user_id=admin_user.id,
        status="PENDING",
        risk_level="HIGH",
        action_type="APPROVE_PURCHASE",
        action_payload={"item": "Notebook", "amount": 1}
    )
    db.add(approval)
    db.commit()

    # Cria evento original no banco
    event = emit_event(
        db=db,
        event_type="approval.created",
        aggregate_type="approval",
        aggregate_id=str(approval.id),
        module="approvals",
        payload={}
    )
    db.commit()

    body = {
        "event_id": str(event.id),
        "event_type": "approval.created",
        "status": "action_requested",
        "result": {
            "action": "approve_approval",
            "approval_id": approval.id,
            "decision": "approved"
        }
    }
    timestamp = datetime.now(timezone.utc).isoformat()
    headers = make_callback_headers(str(event.id), "action_requested", timestamp, "idem-intent-1", body)

    from app.core.config import settings
    with patch.object(settings, "N8N_CALLBACKS_ENABLED", True):
        response = client.post("/api/v1/integrations/n8n/callbacks", json=body, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["callback_type"] == "requires_manual_action"
        
        # O callback_log foi registrado
        callback_log = db.query(AutomationCallbackLog).filter(
            AutomationCallbackLog.idempotency_key == "idem-intent-1"
        ).first()
        assert callback_log is not None
        assert callback_log.action_intent_id is not None
        
        # A ActionIntent foi criada automaticamente
        intent = db.query(ActionIntent).filter(
            ActionIntent.id == uuid.UUID(callback_log.action_intent_id)
        ).first()
        assert intent is not None
        assert intent.source == "n8n"
        assert intent.status == "APPROVAL_REQUIRED" # Risco HIGH
        assert intent.proposed_action == "approve_approval"
        assert intent.callback_log_id == callback_log.id
        assert intent.approval_id == approval.id

def test_callback_requires_manual_action_creates_intent(client, db: Session):
    event = emit_event(
        db=db,
        event_type="approval.created",
        aggregate_type="approval",
        aggregate_id="201",
        module="approvals",
        payload={}
    )
    db.commit()

    body = {
        "event_id": str(event.id),
        "event_type": "approval.created",
        "status": "processed",
        "result": {
            "action": "update_stock",
            "stock_item_id": 10,
            "quantity": 5
        }
    }
    timestamp = datetime.now(timezone.utc).isoformat()
    # callback_type é detectado como "requires_manual_action" porque update_stock é sensível
    headers = make_callback_headers(str(event.id), "processed", timestamp, "idem-intent-2", body)

    from app.core.config import settings
    with patch.object(settings, "N8N_CALLBACKS_ENABLED", True):
        response = client.post("/api/v1/integrations/n8n/callbacks", json=body, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["callback_type"] == "requires_manual_action"
        
        callback_log = db.query(AutomationCallbackLog).filter(
            AutomationCallbackLog.idempotency_key == "idem-intent-2"
        ).first()
        assert callback_log is not None
        
        intent = db.query(ActionIntent).filter(
            ActionIntent.id == uuid.UUID(callback_log.action_intent_id)
        ).first()
        assert intent is not None
        assert intent.proposed_action == "update_stock"
        assert intent.status == "APPROVAL_REQUIRED"

def test_sensitive_action_does_not_modify_approval(client, db: Session):
    # Cria uma aprovação com status PENDING
    admin_user = db.query(User).filter(User.username == "vesper_admin").first()
    approval = Approval(
        title="Solicitação de Compra",
        description="Compra de insumos",
        module_slug="purchases",
        requester_user_id=admin_user.id,
        status="PENDING",
        risk_level="HIGH",
        action_type="APPROVE_PURCHASE",
        action_payload={"item": "Notebook", "amount": 1}
    )
    db.add(approval)
    db.commit()

    # Cria evento original no outbox
    event = emit_event(
        db=db,
        event_type="approval.created",
        aggregate_type="approval",
        aggregate_id=str(approval.id),
        module="approvals",
        payload={}
    )
    db.commit()

    body = {
        "event_id": str(event.id),
        "event_type": "approval.created",
        "status": "action_requested",
        "result": {
            "action": "approve_approval",
            "approval_id": approval.id,
            "decision": "approved"
        }
    }
    timestamp = datetime.now(timezone.utc).isoformat()
    headers = make_callback_headers(str(event.id), "action_requested", timestamp, "idem-intent-3", body)

    from app.core.config import settings
    with patch.object(settings, "N8N_CALLBACKS_ENABLED", True):
        # Dispara o callback n8n tentando aprovar
        response = client.post("/api/v1/integrations/n8n/callbacks", json=body, headers=headers)
        assert response.status_code == 200
        
        # A aprovação de negócio REAL deve permanecer PENDING, intocada.
        db.refresh(approval)
        assert approval.status == "PENDING"

def test_api_endpoints_permissions(client, db: Session):
    # 1. Sem login, GET /api/v1/action-intents deve dar 401 ou 403
    res_anon = client.get("/api/v1/action-intents")
    assert res_anon.status_code in {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN}

    # 2. Login como usuário comum (vesper_user)
    client.post("/api/v1/auth/login", json={"username": "vesper_user", "password": "userpass"})
    res_user = client.get("/api/v1/action-intents")
    assert res_user.status_code == status.HTTP_403_FORBIDDEN # Acesso restrito a admin/manager

    # 3. Login como admin (vesper_admin)
    client.post("/api/v1/auth/login", json={"username": "vesper_admin", "password": "admin"})
    res_admin = client.get("/api/v1/action-intents")
    assert res_admin.status_code == status.HTTP_200_OK
    assert isinstance(res_admin.json(), list)

def test_mask_sensitive_payload_in_read():
    payload = {
        "password": "secretpassword",
        "normal_field": "public",
        "nested": {
            "token": "secrettoken123"
        }
    }
    
    # ActionIntentRead deve aplicar a validação de máscara de chaves sensíveis
    read_obj = ActionIntentRead(
        id=uuid.uuid4(),
        source="system",
        proposed_action="reveal_secret",
        target_module="it",
        title="Teste Máscara",
        summary="Auditoria de máscara",
        risk_level="CRITICAL",
        status="PENDING_REVIEW",
        action_payload=payload,
        result_payload=payload,
        created_at=datetime.now(timezone.utc)
    )
    
    assert read_obj.action_payload["password"] == "******"
    assert read_obj.action_payload["normal_field"] == "public"
    assert read_obj.action_payload["nested"]["token"] == "******"
    assert read_obj.result_payload["nested"]["token"] == "******"

def test_reject_action_intent_flow(client, db: Session):
    # Cria uma ActionIntent
    intent_in = ActionIntentCreateInternal(
        source="koda",
        proposed_action="create_it_ticket",
        target_module="it",
        title="Criar chamado de suporte",
        summary="Ação proposta de chamado",
        risk_level="MEDIUM",
        action_payload={"user_id": 1, "description": "Problema no note"}
    )
    intent = create_action_intent(db, intent_in)
    
    # Login como admin para chamar a rejeição
    client.post("/api/v1/auth/login", json={"username": "vesper_admin", "password": "admin"})
    
    # Rejeita a ActionIntent
    response = client.post(
        f"/api/v1/action-intents/{str(intent.id)}/reject",
        json={"reason": "Chamado duplicado detectado"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "REJECTED"
    assert data["reason"] == "Chamado duplicado detectado"
    assert data["reviewed_by_user_id"] is not None
    
    # Confirma evento de rejeição emitido no outbox
    event = db.query(EventLog).filter(
        EventLog.event_type == "automation.action_intent.rejected",
        EventLog.aggregate_id == str(intent.id)
    ).first()
    assert event is not None
    assert event.payload["reason"] == "Chamado duplicado detectado"

def test_approve_action_intent_flow(client, db: Session):
    intent_in = ActionIntentCreateInternal(
        source="koda",
        proposed_action="create_draft",
        target_module="proposals",
        title="Criar proposta",
        summary="Proposta de minuta",
        risk_level="LOW",
        action_payload={"proposal_id": 1}
    )
    intent = create_action_intent(db, intent_in)
    
    # Login como admin
    client.post("/api/v1/auth/login", json={"username": "vesper_admin", "password": "admin"})
    
    # Aprova/marca revisado
    response = client.post(
        f"/api/v1/action-intents/{str(intent.id)}/mark-reviewed",
        json={"reason": "Proposta de rascunho aprovada"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "APPROVED"
    assert data["reason"] == "Proposta de rascunho aprovada"
    
    # Confirma evento de aprovação no outbox
    event = db.query(EventLog).filter(
        EventLog.event_type == "automation.action_intent.reviewed",
        EventLog.aggregate_id == str(intent.id)
    ).first()
    assert event is not None
    assert event.payload["reason"] == "Proposta de rascunho aprovada"

def test_execute_action_intent_permissions(client, db: Session):
    # 1. Anonymous user block
    intent_in = ActionIntentCreateInternal(
        source="system",
        proposed_action="suggest",
        target_module="proposals",
        title="Sugestão segura",
        summary="Ação sugerida",
        risk_level="LOW",
        action_payload={"val": 123}
    )
    intent = create_action_intent(db, intent_in)
    mark_reviewed_action_intent(db, intent.id, 1, "Aprovada")

    res_anon = client.post(f"/api/v1/action-intents/{str(intent.id)}/execute", json={"dry_run": True})
    assert res_anon.status_code in {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN}

    # 2. Common user block (vesper_user)
    client.post("/api/v1/auth/login", json={"username": "vesper_user", "password": "userpass"})
    res_user = client.post(f"/api/v1/action-intents/{str(intent.id)}/execute", json={"dry_run": True})
    assert res_user.status_code == status.HTTP_403_FORBIDDEN

    # 3. Admin user success (vesper_admin)
    client.post("/api/v1/auth/login", json={"username": "vesper_admin", "password": "admin"})
    res_admin = client.post(f"/api/v1/action-intents/{str(intent.id)}/execute", json={"dry_run": True})
    assert res_admin.status_code == status.HTTP_200_OK

def test_execute_action_intent_invalid_status(client, db: Session):
    intent_in = ActionIntentCreateInternal(
        source="system",
        proposed_action="suggest",
        target_module="proposals",
        title="Sugestão pendente",
        summary="Ação pendente",
        risk_level="LOW",
        action_payload={"val": 123}
    )
    intent = create_action_intent(db, intent_in)

    client.post("/api/v1/auth/login", json={"username": "vesper_admin", "password": "admin"})
    res = client.post(f"/api/v1/action-intents/{str(intent.id)}/execute", json={"dry_run": False})
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    assert "Intenção não pode ser executada no status atual" in res.json()["detail"]

def test_execute_safe_action_dry_run_vs_real(client, db: Session):
    client.post("/api/v1/auth/login", json={"username": "vesper_admin", "password": "admin"})

    intent_in = ActionIntentCreateInternal(
        source="system",
        proposed_action="suggest",
        target_module="proposals",
        title="Sugestão dry run",
        summary="Ação",
        risk_level="LOW",
        action_payload={"key": "val", "password": "my_secret_pwd"}
    )
    intent = create_action_intent(db, intent_in)
    mark_reviewed_action_intent(db, intent.id, 1, "Aprovada")

    # 1. Dry Run
    res_dry = client.post(f"/api/v1/action-intents/{str(intent.id)}/execute", json={"dry_run": True, "idempotency_key": "idem-dry-1"})
    assert res_dry.status_code == 200
    data_dry = res_dry.json()
    assert data_dry["status"] == "SUCCEEDED"
    assert data_dry["input_payload"]["password"] == "******"
    
    db.refresh(intent)
    assert intent.status == "APPROVED"

    # 2. Real Execution
    res_real = client.post(f"/api/v1/action-intents/{str(intent.id)}/execute", json={"dry_run": False, "idempotency_key": "idem-real-1"})
    assert res_real.status_code == 200
    data_real = res_real.json()
    assert data_real["status"] == "SUCCEEDED"
    assert data_real["result_payload"]["status"] == "simulated_success"

    db.refresh(intent)
    assert intent.status == "EXECUTED"

    event_start = db.query(EventLog).filter(
        EventLog.event_type == "automation.action_intent.execution.started"
    ).first()
    assert event_start is not None

    event_success = db.query(EventLog).filter(
        EventLog.event_type == "automation.action_intent.execution.succeeded"
    ).first()
    assert event_success is not None

def test_execute_blocked_action(client, db: Session):
    client.post("/api/v1/auth/login", json={"username": "vesper_admin", "password": "admin"})

    intent_in = ActionIntentCreateInternal(
        source="system",
        proposed_action="delete_file",
        target_module="files",
        title="Apagar arquivo crítico",
        summary="Ação perigosa",
        risk_level="CRITICAL",
        action_payload={"file_path": "/sensivel.txt"}
    )
    intent = create_action_intent(db, intent_in)
    mark_reviewed_action_intent(db, intent.id, 1, "Aprovada")

    res = client.post(f"/api/v1/action-intents/{str(intent.id)}/execute", json={"dry_run": False, "idempotency_key": "idem-blocked-1"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "BLOCKED"
    assert "Execução bloqueada: ação sensível" in data["error_message"]

    db.refresh(intent)
    assert intent.status == "EXECUTION_BLOCKED"

    event_blocked = db.query(EventLog).filter(
        EventLog.event_type == "automation.action_intent.execution.blocked"
    ).first()
    assert event_blocked is not None

def test_execute_idempotency(client, db: Session):
    client.post("/api/v1/auth/login", json={"username": "vesper_admin", "password": "admin"})

    intent_in = ActionIntentCreateInternal(
        source="system",
        proposed_action="summarize",
        target_module="proposals",
        title="Resumo seguro",
        summary="Ação",
        risk_level="LOW",
        action_payload={"val": 123}
    )
    intent = create_action_intent(db, intent_in)
    mark_reviewed_action_intent(db, intent.id, 1, "Aprovada")

    res1 = client.post(f"/api/v1/action-intents/{str(intent.id)}/execute", json={"dry_run": False, "idempotency_key": "idem-key-unique"})
    assert res1.status_code == 200
    exec1_id = res1.json()["id"]

    res2 = client.post(f"/api/v1/action-intents/{str(intent.id)}/execute", json={"dry_run": False, "idempotency_key": "idem-key-unique"})
    assert res2.status_code == 200
    exec2_id = res2.json()["id"]

    assert exec1_id == exec2_id
