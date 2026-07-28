from fastapi import status
from app.models.audit_log import AuditLog
from app.models.approval import Approval
from app.models.approval_comment import ApprovalComment
from app.models.approval_decision import ApprovalDecision
from app.models.user_module_access import UserModuleAccess
from app.models.module import Module
from app.models.user import User

# Auxiliar para login e obter cabeçalhos de autenticação ou cookies
def login(client, username, password):
    login_data = {"username": username, "password": password}
    response = client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == status.HTTP_200_OK
    return response.json()["access_token"]

# 1. Bloquear criação de aprovação sem login
def test_create_approval_unauthenticated(client):
    payload = {
        "title": "Aumento de Limite de Teste",
        "description": "Solicitação de aumento de limite",
        "module_slug": "dashboard",
        "risk_level": "LOW",
        "action_type": "LIMIT_INCREASE",
        "action_payload": {"amount": 5000}
    }
    response = client.post("/api/v1/approvals/", json=payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

# 2. Bloquear criação de aprovação sem permissão no módulo de origem
def test_create_approval_no_module_access(client):
    token = login(client, "vesper_user", "userpass")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "title": "Ação Crítica de TI",
        "description": "Alteração no servidor",
        "module_slug": "it",  # vesper_user não tem acesso ao módulo it
        "risk_level": "HIGH",
        "action_type": "SERVER_RESTART",
        "action_payload": {}
    }
    response = client.post("/api/v1/approvals/", json=payload, headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "Permissao insuficiente" in response.json()["detail"]

# 3. Criar aprovação autenticado com sucesso
def test_create_approval_success(client, db):
    token = login(client, "vesper_user", "userpass")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "title": "Nova Proposta Comercial",
        "description": "Aprovação de proposta comercial para cliente X",
        "module_slug": "dashboard",  # vesper_user tem acesso NORMAL a dashboard no conftest
        "risk_level": "MEDIUM",
        "action_type": "PROPOSAL_SEND",
        "action_payload": {"client_id": 123, "value": 15000}
    }
    response = client.post("/api/v1/approvals/", json=payload, headers=headers)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["title"] == payload["title"]
    assert data["status"] == "PENDING"
    assert data["risk_level"] == "MEDIUM"
    assert data["module_slug"] == "dashboard"
    
    # Validar se o log de auditoria correspondente foi gerado
    audit = db.query(AuditLog).filter(AuditLog.action == "approval.created").first()
    assert audit is not None
    assert audit.user_id is not None
    assert audit.details["approval_id"] == data["id"]

# 4. Listar aprovações como admin vs usuário comum
def test_list_approvals_rbac(client, db):
    # vesper_user cria uma solicitação
    user_token = login(client, "vesper_user", "userpass")
    user_headers = {"Authorization": f"Bearer {user_token}"}
    payload = {
        "title": "Compra de Teclado",
        "description": "Compra de periféricos",
        "module_slug": "dashboard",
        "risk_level": "LOW",
        "action_type": "PURCHASE",
        "action_payload": {}
    }
    create_resp = client.post("/api/v1/approvals/", json=payload, headers=user_headers)
    assert create_resp.status_code == status.HTTP_201_CREATED
    approval_id = create_resp.json()["id"]

    # 4.1 Usuário comum lista: deve ver apenas a sua própria
    list_resp = client.get("/api/v1/approvals/", headers=user_headers)
    assert list_resp.status_code == status.HTTP_200_OK
    user_approvals = list_resp.json()
    assert len(user_approvals) >= 1
    # Garante que todas as listadas são do próprio usuário comum
    user_db = db.query(User).filter(User.username == "vesper_user").first()
    for app in user_approvals:
        assert app["requester_user_id"] == user_db.id

    # 4.2 Admin lista: deve ver tudo
    admin_token = login(client, "vesper_admin", "admin")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    list_admin_resp = client.get("/api/v1/approvals/", headers=admin_headers)
    assert list_admin_resp.status_code == status.HTTP_200_OK
    admin_approvals = list_admin_resp.json()
    assert len(admin_approvals) >= 1
    # Verifica se a solicitação criada pelo usuário comum está na lista do admin
    found = any(app["id"] == approval_id for app in admin_approvals)
    assert found is True

# 5. Detalhes da aprovação e permissões
def test_approval_details_permissions(client, db):
    # Cria uma aprovação como vesper_user
    user_token = login(client, "vesper_user", "userpass")
    user_headers = {"Authorization": f"Bearer {user_token}"}
    payload = {
        "title": "Aprovação Detalhes",
        "description": "Teste de detalhes",
        "module_slug": "dashboard",
        "risk_level": "LOW",
        "action_type": "TEST",
        "action_payload": {}
    }
    create_resp = client.post("/api/v1/approvals/", json=payload, headers=user_headers)
    approval_id = create_resp.json()["id"]

    # Usuário comum (criador) deve conseguir acessar
    detail_resp = client.get(f"/api/v1/approvals/{approval_id}", headers=user_headers)
    assert detail_resp.status_code == status.HTTP_200_OK
    assert detail_resp.json()["title"] == "Aprovação Detalhes"

    # Admin deve conseguir acessar
    admin_token = login(client, "vesper_admin", "admin")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    detail_admin_resp = client.get(f"/api/v1/approvals/{approval_id}", headers=admin_headers)
    assert detail_admin_resp.status_code == status.HTTP_200_OK

    # Um usuário comum que NÃO é criador e não tem acesso MANAGER ao módulo deve ser bloqueado
    # Vamos alterar o criador da aprovação no banco de dados para o ID do vesper_admin.
    # Assim, vesper_user tenta acessar e passa a ser "outro usuário" sem acesso.
    app_db = db.query(Approval).filter(Approval.id == approval_id).first()
    admin_user = db.query(User).filter(User.username == "vesper_admin").first()
    app_db.requester_user_id = admin_user.id
    db.commit()
    db.expire_all()

    # Limpa os cookies para evitar que o cookie de login do admin ativo no cliente
    # sobrescreva o cabeçalho Authorization do usuário comum.
    client.cookies.clear()

    # Agora vesper_user tenta acessar a aprovação criada por admin (ele não é manager de dashboard no conftest)
    detail_blocked_resp = client.get(f"/api/v1/approvals/{approval_id}", headers=user_headers)
    assert detail_blocked_resp.status_code == status.HTTP_403_FORBIDDEN
    assert "Acesso negado" in detail_blocked_resp.json()["detail"]

# 6. Aprovar solicitação com sucesso e auditoria
def test_approve_approval_success(client, db):
    user_token = login(client, "vesper_user", "userpass")
    user_headers = {"Authorization": f"Bearer {user_token}"}
    payload = {
        "title": "Aprovação Admin",
        "description": "Teste aprovação",
        "module_slug": "dashboard",
        "risk_level": "LOW",
        "action_type": "TEST",
        "action_payload": {}
    }
    create_resp = client.post("/api/v1/approvals/", json=payload, headers=user_headers)
    approval_id = create_resp.json()["id"]

    # Admin aprova
    admin_token = login(client, "vesper_admin", "admin")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    approve_resp = client.post(f"/api/v1/approvals/{approval_id}/approve", headers=admin_headers)
    assert approve_resp.status_code == status.HTTP_200_OK
    assert approve_resp.json()["status"] == "APPROVED"
    assert approve_resp.json()["approver_user_id"] is not None

    # Verifica se a decisão foi registrada
    decision = db.query(ApprovalDecision).filter(ApprovalDecision.approval_id == approval_id).first()
    assert decision is not None
    assert decision.decision == "APPROVED"

    # Verifica o log de auditoria
    audit = db.query(AuditLog).filter(AuditLog.action == "approval.approved").first()
    assert audit is not None
    assert audit.details["approval_id"] == approval_id

def test_approve_purchase_options_with_result_payload(client, db):
    user_token = login(client, "vesper_user", "userpass")
    user_headers = {"Authorization": f"Bearer {user_token}"}
    payload = {
        "title": "Escolha de headset",
        "description": "Escolher a melhor opcao dentro do limite aprovado.",
        "module_slug": "dashboard",
        "risk_level": "MEDIUM",
        "action_type": "SUPPLIER_SELECTION",
        "action_payload": {
            "request_type": "purchase_options",
            "item": "headset",
            "max_price": 150,
            "currency": "BRL",
            "criteria": ["bom microfone", "confortavel"],
            "options": [
                {
                    "title": "Headset Exemplo 1",
                    "store": "Loja Exemplo",
                    "price": 129.90,
                    "url": "https://exemplo.com/produto"
                },
                {
                    "title": "Headset Exemplo 2",
                    "store": "Loja Exemplo",
                    "price": 149.90,
                    "url": "https://exemplo.com/produto-2"
                }
            ],
            "agent_recommendation": "Opcao 1 parece o melhor custo-beneficio."
        }
    }
    create_resp = client.post("/api/v1/approvals/", json=payload, headers=user_headers)
    assert create_resp.status_code == status.HTTP_201_CREATED
    approval_id = create_resp.json()["id"]

    admin_token = login(client, "vesper_admin", "admin")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    approve_payload = {
        "reason": "Aprovado pelo custo-beneficio.",
        "result_payload": {
            "selected_option_index": 0,
            "decision_type": "selected_purchase_option"
        }
    }
    approve_resp = client.post(f"/api/v1/approvals/{approval_id}/approve", json=approve_payload, headers=admin_headers)
    assert approve_resp.status_code == status.HTTP_200_OK
    data = approve_resp.json()
    assert data["status"] == "APPROVED"
    assert data["result_payload"]["selected_option_index"] == 0
    assert data["result_payload"]["selected_option_title"] == "Headset Exemplo 1"
    assert data["result_payload"]["selected_option_url"] == "https://exemplo.com/produto"
    assert data["result_payload"]["approved_price"] == 129.90

    decision = db.query(ApprovalDecision).filter(ApprovalDecision.approval_id == approval_id).first()
    assert decision is not None
    assert decision.reason == "Aprovado pelo custo-beneficio."

    audits = db.query(AuditLog).filter(AuditLog.action == "approval.approved").all()
    audit = next((item for item in audits if item.details.get("approval_id") == approval_id), None)
    assert audit is not None
    assert audit.details["result_payload_summary"]["selected_option_title"] == "Headset Exemplo 1"

def test_purchase_options_invalid_selected_index_blocked(client):
    user_token = login(client, "vesper_user", "userpass")
    user_headers = {"Authorization": f"Bearer {user_token}"}
    payload = {
        "title": "Escolha invalida",
        "description": "Teste de indice invalido",
        "module_slug": "dashboard",
        "risk_level": "LOW",
        "action_type": "SUPPLIER_SELECTION",
        "action_payload": {
            "request_type": "purchase_options",
            "options": [{"title": "Opcao unica", "price": 99}]
        }
    }
    create_resp = client.post("/api/v1/approvals/", json=payload, headers=user_headers)
    approval_id = create_resp.json()["id"]

    admin_token = login(client, "vesper_admin", "admin")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    approve_resp = client.post(
        f"/api/v1/approvals/{approval_id}/approve",
        json={
            "result_payload": {
                "selected_option_index": 3,
                "decision_type": "selected_purchase_option"
            }
        },
        headers=admin_headers
    )
    assert approve_resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "opcao de compra selecionada nao existe" in approve_resp.json()["detail"]

# 7. Bloquear decisão por usuário sem permissão
def test_approve_denied_to_user(client):
    user_token = login(client, "vesper_user", "userpass")
    user_headers = {"Authorization": f"Bearer {user_token}"}
    
    # Cria
    payload = {
        "title": "Aprovação User",
        "description": "Teste bloqueio",
        "module_slug": "dashboard",
        "risk_level": "LOW",
        "action_type": "TEST",
        "action_payload": {}
    }
    create_resp = client.post("/api/v1/approvals/", json=payload, headers=user_headers)
    approval_id = create_resp.json()["id"]

    # vesper_user (solicitante) tenta aprovar a própria (vesper_user tem apenas NORMAL no dashboard)
    # Isso deve retornar 403 Forbidden por permissão insuficiente (requer MANAGER ou ADMIN)
    approve_resp = client.post(f"/api/v1/approvals/{approval_id}/approve", headers=user_headers)
    assert approve_resp.status_code == status.HTTP_403_FORBIDDEN
    assert "Permissao insuficiente" in approve_resp.json()["detail"]

# 8. Regra de Auto-Aprovação (bloqueia MANAGER que solicita aprovar sua própria solicitação)
def test_manager_auto_approval_blocked(client, db):
    # Vamos dar permissão MANAGER para o vesper_user no módulo dashboard no banco de dados temporariamente
    user_db = db.query(User).filter(User.username == "vesper_user").first()
    dash_module = db.query(Module).filter(Module.code == "dashboard").first()
    
    access = db.query(UserModuleAccess).filter(
        UserModuleAccess.user_id == user_db.id,
        UserModuleAccess.module_id == dash_module.id
    ).first()
    original_level = access.permission_level
    
    try:
        # Altera para MANAGER
        access.permission_level = "MANAGER"
        db.commit()

        user_token = login(client, "vesper_user", "userpass")
        user_headers = {"Authorization": f"Bearer {user_token}"}
        
        # Cria solicitação
        payload = {
            "title": "Aprovação Auto Bloqueio",
            "description": "Teste auto aprovação",
            "module_slug": "dashboard",
            "risk_level": "LOW",
            "action_type": "TEST",
            "action_payload": {}
        }
        create_resp = client.post("/api/v1/approvals/", json=payload, headers=user_headers)
        approval_id = create_resp.json()["id"]

        # vesper_user agora é MANAGER de dashboard. Ele tenta aprovar sua própria solicitação.
        # Deve retornar 400 Bad Request por causa da regra de auto-aprovação.
        approve_resp = client.post(f"/api/v1/approvals/{approval_id}/approve", headers=user_headers)
        assert approve_resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "Nao e permitido aprovar sua propria solicitacao" in approve_resp.json()["detail"]

    finally:
        # Restaura permissão original
        access.permission_level = original_level
        db.commit()

# 9. Bloquear aprovação duplicada
def test_double_approval_blocked(client, db):
    user_token = login(client, "vesper_user", "userpass")
    user_headers = {"Authorization": f"Bearer {user_token}"}
    payload = {
        "title": "Aprovação Duplicada",
        "description": "Teste duplicidade",
        "module_slug": "dashboard",
        "risk_level": "LOW",
        "action_type": "TEST",
        "action_payload": {}
    }
    create_resp = client.post("/api/v1/approvals/", json=payload, headers=user_headers)
    approval_id = create_resp.json()["id"]

    # Admin aprova uma vez
    admin_token = login(client, "vesper_admin", "admin")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    approve_resp = client.post(f"/api/v1/approvals/{approval_id}/approve", headers=admin_headers)
    assert approve_resp.status_code == status.HTTP_200_OK

    # Admin tenta aprovar uma segunda vez
    approve_twice_resp = client.post(f"/api/v1/approvals/{approval_id}/approve", headers=admin_headers)
    assert approve_twice_resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "Esta aprovacao ja foi finalizada" in approve_twice_resp.json()["detail"]

# 10. Rejeitar solicitação com motivo
def test_reject_approval_with_reason(client, db):
    user_token = login(client, "vesper_user", "userpass")
    user_headers = {"Authorization": f"Bearer {user_token}"}
    payload = {
        "title": "Aprovação Rejeitada",
        "description": "Teste rejeição",
        "module_slug": "dashboard",
        "risk_level": "LOW",
        "action_type": "TEST",
        "action_payload": {}
    }
    create_resp = client.post("/api/v1/approvals/", json=payload, headers=user_headers)
    approval_id = create_resp.json()["id"]

    # Admin rejeita com motivo
    admin_token = login(client, "vesper_admin", "admin")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    reject_payload = {"reason": "Orçamento estourado."}
    reject_resp = client.post(f"/api/v1/approvals/{approval_id}/reject", json=reject_payload, headers=admin_headers)
    assert reject_resp.status_code == status.HTTP_200_OK
    assert reject_resp.json()["status"] == "REJECTED"

    # Valida no banco se a decisão contém o motivo
    decision = db.query(ApprovalDecision).filter(
        ApprovalDecision.approval_id == approval_id,
        ApprovalDecision.decision == "REJECTED"
    ).first()
    assert decision is not None
    assert decision.reason == "Orçamento estourado."

    # Verifica auditoria
    audit = db.query(AuditLog).filter(AuditLog.action == "approval.rejected").first()
    assert audit is not None
    assert audit.details["reason"] == "Orçamento estourado."

# 11. Cancelar solicitação
def test_cancel_approval(client):
    user_token = login(client, "vesper_user", "userpass")
    user_headers = {"Authorization": f"Bearer {user_token}"}
    payload = {
        "title": "Aprovação Cancelada",
        "description": "Teste cancelamento",
        "module_slug": "dashboard",
        "risk_level": "LOW",
        "action_type": "TEST",
        "action_payload": {}
    }
    create_resp = client.post("/api/v1/approvals/", json=payload, headers=user_headers)
    approval_id = create_resp.json()["id"]

    # Solicitante cancela
    cancel_resp = client.post(f"/api/v1/approvals/{approval_id}/cancel", headers=user_headers)
    assert cancel_resp.status_code == status.HTTP_200_OK
    assert cancel_resp.json()["status"] == "CANCELLED"

# 12. Adicionar comentários
def test_add_comment(client, db):
    user_token = login(client, "vesper_user", "userpass")
    user_headers = {"Authorization": f"Bearer {user_token}"}
    payload = {
        "title": "Comentários",
        "description": "Teste comentários",
        "module_slug": "dashboard",
        "risk_level": "LOW",
        "action_type": "TEST",
        "action_payload": {}
    }
    create_resp = client.post("/api/v1/approvals/", json=payload, headers=user_headers)
    approval_id = create_resp.json()["id"]

    # Adiciona comentário
    comment_payload = {"comment": "Documento em anexo."}
    comment_resp = client.post(f"/api/v1/approvals/{approval_id}/comments", json=comment_payload, headers=user_headers)
    assert comment_resp.status_code == status.HTTP_200_OK
    assert comment_resp.json()["comment"] == "Documento em anexo."

    # Verifica no banco
    comment_db = db.query(ApprovalComment).filter(ApprovalComment.approval_id == approval_id).first()
    assert comment_db is not None
    assert comment_db.comment == "Documento em anexo."

# 13. Sumário/Métricas de aprovações
def test_approvals_summary(client):
    user_token = login(client, "vesper_user", "userpass")
    user_headers = {"Authorization": f"Bearer {user_token}"}
    
    response = client.get("/api/v1/approvals/summary", headers=user_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "total_pending" in data
    assert "my_requests_pending" in data
    assert "waiting_my_decision" in data
    assert "approved_recent" in data
    assert "rejected_recent" in data
    assert "by_risk" in data
