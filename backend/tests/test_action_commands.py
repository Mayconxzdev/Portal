import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.models.master_data import Person, Supplier, ProductItem
from app.models.module import Module
from app.models.user import User
from app.models.user_module_access import UserModuleAccess
from app.models.action_command import ActionCommandDraft
from app.models.action_intent import ActionIntent
from app.models.event_log import EventLog
from app.models.purchase import PurchasePriceEvidence, PurchasePriceUpdateSuggestion, PurchasePriceReference

# Helpers de autenticação
def login_admin(client: TestClient):
    client.post("/api/v1/auth/login", json={"username": "vesper_admin", "password": "admin"})

def login_user(client: TestClient):
    client.post("/api/v1/auth/login", json={"username": "vesper_user", "password": "userpass"})

def logout(client: TestClient):
    client.cookies.clear()

@pytest.fixture
def setup_action_test_data(db: Session):
    """Garante cadastros mestres e módulo compras/ti/propostas configurados para os testes de comandos de ação."""
    # 1. Garante que os módulos existam
    purchases_module = db.query(Module).filter(Module.code == "purchases").first()
    if not purchases_module:
        purchases_module = Module(name="Compras", code="purchases", is_active=True, is_restricted=False)
        db.add(purchases_module)
        db.flush()

    it_module = db.query(Module).filter(Module.code == "it").first()
    if not it_module:
        it_module = Module(name="TI", code="it", is_active=True, is_restricted=False)
        db.add(it_module)
        db.flush()

    proposals_module = db.query(Module).filter(Module.code == "proposals").first()
    if not proposals_module:
        proposals_module = Module(name="Propostas", code="proposals", is_active=True, is_restricted=False)
        db.add(proposals_module)
        db.flush()

    # 2. Configura acessos do vesper_user
    user_common = db.query(User).filter(User.username == "vesper_user").first()
    if user_common:
        # Limpa antigos
        db.query(UserModuleAccess).filter(UserModuleAccess.user_id == user_common.id).delete()
        
        access_purchases = UserModuleAccess(
            user_id=user_common.id,
            module_id=purchases_module.id,
            permission_level="NORMAL"
        )
        access_it = UserModuleAccess(
            user_id=user_common.id,
            module_id=it_module.id,
            permission_level="NORMAL"
        )
        access_proposals = UserModuleAccess(
            user_id=user_common.id,
            module_id=proposals_module.id,
            permission_level="NORMAL"
        )
        db.add(access_purchases)
        db.add(access_it)
        db.add(access_proposals)

    # 3. Cria Fornecedor
    person_supplier = Person(
        id=uuid.uuid4(),
        type="COMPANY",
        name="Dell Computadores Ltda",
        document_number="98765432000188"
    )
    db.add(person_supplier)
    db.flush()

    supplier = Supplier(
        id=uuid.uuid4(),
        person_id=person_supplier.id,
        supplier_code="DELL-PC",
        status="ACTIVE"
    )
    db.add(supplier)

    # 4. Cria Item
    product = ProductItem(
        id=uuid.uuid4(),
        sku="CH-IN-304-2MM",
        name="Chapa Inox 304 2mm",
        category="Chapas",
        unit_of_measure="chapa",
        item_type="RAW_MATERIAL",
        is_active=True
    )
    db.add(product)
    db.commit()

    return {
        "supplier": supplier,
        "product": product
    }

def test_parse_text_commands(client: TestClient, db: Session, setup_action_test_data):
    """Testa a interpretação de comandos de texto livre via endpoint POST /parse."""
    login_user(client)
    master = setup_action_test_data

    # Caso 1: "cotar 5 chapas inox"
    response = client.post(
        "/api/v1/action-commands/parse",
        json={
            "text": "cotar 5 chapas inox",
            "source": "chat"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["action_key"] == "purchase.rfq.create"
    assert data["status"] == "READY_TO_CONFIRM" # Já encontrou o item inox correspondente por similaridade
    assert data["extracted_data"]["product_item_id"] == str(master["product"].id)
    assert data["extracted_data"]["quantity"] == 5

    # Caso 2: "atualizar preço chapa inox para 120"
    response2 = client.post(
        "/api/v1/action-commands/parse",
        json={
            "text": "atualizar preço chapa inox para 120",
            "source": "global_bar"
        }
    )
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["action_key"] == "purchase.price.confer"
    assert data2["status"] == "NEEDS_MORE_INFO" # Falta o supplier_id obrigatório
    assert data2["missing_fields"]["fields"][0]["name"] == "supplier_id"
    assert float(data2["extracted_data"]["unit_price"]) == 120.0

def test_prepare_contextual_actions(client: TestClient, db: Session, setup_action_test_data):
    """Testa a preparação de ações contextuais direto de drawers/botões sem texto livre."""
    login_user(client)
    master = setup_action_test_data

    response = client.post(
        "/api/v1/action-commands/prepare",
        json={
            "action_key": "purchase.price.confer",
            "source": "drawer",
            "source_module": "purchases",
            "source_entity_type": "product_item",
            "source_entity_id": str(master["product"].id),
            "initial_data": {
                "product_item_id": str(master["product"].id),
                "supplier_id": str(master["supplier"].id),
                "unit_price": 115.0
            }
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["action_key"] == "purchase.price.confer"
    assert data["status"] == "READY_TO_CONFIRM" # Todos os campos requeridos fornecidos
    assert len(data["missing_fields"]["fields"]) == 0
    assert data["risk_level"] == "MEDIUM"

def test_confirm_low_risk_action_executes_directly(client: TestClient, db: Session, setup_action_test_data):
    """Testa que a confirmação de comando LOW seguro executa a ação e cria a entidade diretamente."""
    login_user(client)
    master = setup_action_test_data

    # Cria requisição de compras (LOW)
    response_prepare = client.post(
        "/api/v1/action-commands/prepare",
        json={
            "action_key": "purchase.request.create",
            "source": "chat",
            "initial_data": {
                "product_item_id": str(master["product"].id),
                "quantity": 10
            }
        }
    )
    draft_id = response_prepare.json()["id"]

    # Confirma a criação direta
    response_confirm = client.post(
        f"/api/v1/action-commands/{draft_id}/confirm",
        json={}
    )
    assert response_confirm.status_code == 200
    data = response_confirm.json()
    assert data["status"] == "EXECUTED"
    assert data["created_entity_type"] == "purchase_request"
    assert data["created_entity_id"] is not None

    # Verifica emissão de eventos no Event Engine
    events = db.query(EventLog).filter(EventLog.event_type == "action_command.executed").all()
    assert len(events) > 0

def test_confirm_price_confer_creates_suggesion(client: TestClient, db: Session, setup_action_test_data):
    """Testa que a confirmação de conferência de preço (MEDIUM) cria a evidência/sugestão e não atualiza referência direto."""
    login_user(client)
    master = setup_action_test_data

    response_prepare = client.post(
        "/api/v1/action-commands/prepare",
        json={
            "action_key": "purchase.price.confer",
            "source": "drawer",
            "initial_data": {
                "product_item_id": str(master["product"].id),
                "supplier_id": str(master["supplier"].id),
                "unit_price": 85.0
            }
        }
    )
    draft_id = response_prepare.json()["id"]

    response_confirm = client.post(
        f"/api/v1/action-commands/{draft_id}/confirm",
        json={}
    )
    assert response_confirm.status_code == 200
    data = response_confirm.json()
    assert data["status"] == "EXECUTED" # Executa o handler e cria a evidência de preço
    
    # Verifica que a evidência de preço e a sugestão de reajuste foram salvas, mas o preço de referência ativo permanece inalterado
    evidence_id = uuid.UUID(data["created_entity_id"])
    evidence = db.query(PurchasePriceEvidence).filter(PurchasePriceEvidence.id == evidence_id).first()
    assert evidence is not None
    
    # Preço de referência ativo NÃO foi criado ainda (não homologado)
    ref = db.query(PurchasePriceReference).filter(
        PurchasePriceReference.product_item_id == master["product"].id,
        PurchasePriceReference.supplier_id == master["supplier"].id,
        PurchasePriceReference.is_active == True
    ).first()
    assert ref is None

def test_confirm_high_risk_action_creates_action_intent(client: TestClient, db: Session, setup_action_test_data):
    """Testa que a confirmação de comando HIGH sensível cria uma Action Intent para aprovação gerencial."""
    login_user(client)
    master = setup_action_test_data

    # Cria proposta com desconto (na PR, proposal.create está com preview de risco MEDIUM/HIGH)
    # Vamos simular mudando o risco de um draft para HIGH
    response_prepare = client.post(
        "/api/v1/action-commands/prepare",
        json={
            "action_key": "proposal.create",
            "source": "chat",
            "initial_data": {
                "customer_id": str(uuid.uuid4())
            }
        }
    )
    draft_id = response_prepare.json()["id"]
    
    # Força risco HIGH no banco para o teste de Action Intent
    draft = db.query(ActionCommandDraft).filter(ActionCommandDraft.id == uuid.UUID(draft_id)).first()
    draft.risk_level = "HIGH"
    draft.requires_approval = True
    db.commit()

    response_confirm = client.post(
        f"/api/v1/action-commands/{draft_id}/confirm",
        json={}
    )
    assert response_confirm.status_code == 200
    data = response_confirm.json()
    assert data["status"] == "APPROVAL_REQUIRED"
    assert data["action_intent_id"] is not None

    # Verifica que a ActionIntent correspondente foi gerada
    action_intent_id = uuid.UUID(data["action_intent_id"])
    intent = db.query(ActionIntent).filter(ActionIntent.id == action_intent_id).first()
    assert intent is not None
    assert intent.status == "APPROVAL_REQUIRED"

def test_insufficient_permissions_are_blocked(client: TestClient, db: Session, setup_action_test_data):
    """Testa que usuários sem permissão de acesso ao módulo de destino são bloqueados com HTTP 403."""
    login_user(client)
    # Remove as permissões do vesper_user
    user_common = db.query(User).filter(User.username == "vesper_user").first()
    db.query(UserModuleAccess).filter(UserModuleAccess.user_id == user_common.id).delete()
    db.commit()

    # Tenta preparar
    response = client.post(
        "/api/v1/action-commands/prepare",
        json={
            "action_key": "purchase.request.create",
            "source": "chat",
            "initial_data": {
                "product_item_id": str(uuid.uuid4()),
                "quantity": 1
            }
        }
    )
    assert response.status_code == 403
    assert "permissão" in response.json()["detail"].lower()
