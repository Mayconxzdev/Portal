import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from app.models.master_data import Person, Supplier, ProductItem, Service
from app.models.purchase import (
    PurchaseRequest,
    PurchaseRequestItem,
    PurchaseRFQ,
    PurchaseRFQSupplier,
    PurchaseRFQSupplierItem,
    PurchaseQuoteResponse,
    PurchaseQuoteLine,
    PurchaseComparison,
    PurchaseSearchSession,
    PurchaseOfferFieldEvidence,
    PurchaseRequestIdempotencyKey,
    PurchaseInterpretedDraft,
    PurchaseResearchJob,
    PurchaseOfferPriceCondition,
)
from app.models.approval import Approval
from app.core.config import settings
from app.models.stock import StockCatalogImportRun, StockCatalogItem, StockCatalogSupplier, StockCatalogOffer
from app.models.event_log import EventLog
from app.models.notification import Notification
from app.models.action_intent import ActionIntent
from app.modules.stock.service import StockCatalogService
from app.modules.purchases.offer_extractor import extract_offer_from_html

# Helpers de autenticação
def login_admin(client: TestClient):
    client.post("/api/v1/auth/login", json={"username": "vesper_admin", "password": "admin"})

def login_user(client: TestClient):
    client.post("/api/v1/auth/login", json={"username": "vesper_user", "password": "userpass"})

def logout(client: TestClient):
    client.cookies.clear()


def _stock_match(
    item_id: str,
    name: str,
    *,
    specification: str = "",
    family: str = "Arame e Tela",
    code: str = "AR-BTC-15",
) -> dict:
    return {
        "id": item_id,
        "display_name": name,
        "name": name,
        "description": name,
        "specification_text": specification,
        "measure_display": specification,
        "variation_label": specification,
        "family_name": family,
        "category_name": family,
        "cybersul_code": code,
        "internal_code": code,
        "current_price": 13.01,
        "supplier_name": "FERACO",
    }


def test_purchase_need_persists_item_approval_flag_and_filters_queue(client: TestClient, db: Session):
    login_admin(client)

    response = client.post("/api/v1/purchases/needs", json={
        "title": "Memoria RAM para aprovacao",
        "items": [
            {
                "free_text_description": "Memoria RAM DDR4",
                "quantity": 2,
                "unit_of_measure": "un",
                "classification": "EXTERNAL",
                "estimated_unit_price": 240.0,
                "requires_approval": True,
            }
        ],
    })

    assert response.status_code == 201
    payload = response.json()
    assert payload["items"][0]["requires_approval"] is True

    item_id = uuid.UUID(payload["items"][0]["id"])
    item = db.query(PurchaseRequestItem).filter(PurchaseRequestItem.id == item_id).one()
    assert item.requires_approval is True

    filtered = client.get("/api/v1/purchases/needs?queue_filter=approval")
    assert filtered.status_code == 200
    assert any(request["id"] == payload["id"] for request in filtered.json())


def test_purchase_analyze_creates_review_draft_without_request(client: TestClient, db: Session, monkeypatch):
    login_admin(client)
    monkeypatch.setattr(
        StockCatalogService,
        "list_items",
        lambda *args, **kwargs: [_stock_match("00000000-0000-4000-8000-000000000001", "Arame BTC CL 1,5 mm")],
    )

    before_count = db.query(PurchaseRequest).count()
    response = client.post("/api/v1/purchases/analyze", json={
        "text": "2 memorias RAM DDR4 para o PC do Operador Demo ate R$ 5000\n1 Arame BTC CL 1,5 mm",
        "context": "new_purchase",
        "idempotency_key": "draft-test-1",
    })

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "reviewing"
    assert len(payload["items"]) == 2
    assert any(item["item_type"] == "external" for item in payload["items"])
    assert any(item["item_type"] == "internal" for item in payload["items"])
    assert db.query(PurchaseRequest).count() == before_count
    assert db.query(PurchaseInterpretedDraft).filter(
        PurchaseInterpretedDraft.id == uuid.UUID(payload["draft_id"])
    ).first() is not None


def test_purchase_request_creation_is_idempotent(client: TestClient, db: Session):
    login_admin(client)
    payload = {
        "idempotency_key": "teste-idempotencia",
        "title": "Compra idempotente",
        "items": [
            {
                "free_text_description": "Memoria RAM DDR5",
                "quantity": 1,
                "unit_of_measure": "un",
                "classification": "EXTERNAL",
            }
        ],
    }

    first = client.post("/api/v1/purchases/needs", json=payload)
    second = client.post("/api/v1/purchases/needs", json=payload)
    lookup = client.get("/api/v1/purchases/requests/by-idempotency/teste-idempotencia")

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    assert lookup.status_code == 200
    assert lookup.json()["request"]["id"] == first.json()["id"]
    assert db.query(PurchaseRequestIdempotencyKey).filter(
        PurchaseRequestIdempotencyKey.idempotency_key == "teste-idempotencia"
    ).count() == 1


def test_purchase_request_idempotency_rejects_reused_key_with_different_payload(client: TestClient):
    login_admin(client)
    base = {
        "idempotency_key": "purchase-idem-conflict",
        "title": "Compra A",
        "items": [{"free_text_description": "SSD NVME", "quantity": 1, "unit_of_measure": "un"}],
    }
    conflict = {
        **base,
        "title": "Compra B",
    }

    first = client.post("/api/v1/purchases/needs", json=base)
    second = client.post("/api/v1/purchases/needs", json=conflict)

    assert first.status_code == 201
    assert second.status_code == 409


def test_research_session_async_endpoint_queues_job(client: TestClient, db: Session, monkeypatch):
    login_admin(client)
    monkeypatch.setattr(settings, "PURCHASES_RESEARCH_ASYNC_ENABLED", True)
    created = client.post("/api/v1/purchases/needs", json={
        "title": "Pesquisa assíncrona",
        "items": [{"free_text_description": "Memoria RAM DDR5", "quantity": 1, "unit_of_measure": "un", "classification": "EXTERNAL"}],
    })
    assert created.status_code == 201
    item_id = created.json()["items"][0]["id"]

    response = client.post(
        f"/api/v1/purchases/items/{item_id}/research-sessions",
        json={"query": "Memoria RAM DDR5", "run_immediately": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["progress_percent"] == 0
    assert payload["status"] in {"queued", "retryable_error"}
    assert db.query(PurchaseResearchJob).filter(
        PurchaseResearchJob.search_session_id == uuid.UUID(payload["id"])
    ).count() == 1


def test_offer_extractor_prefers_confirmed_pix_over_previous_price():
    html = """
    <html><head><title>Placa de Video Teste</title></head>
    <body>
      <span>De R$ 5.240,09</span>
      <strong>R$ 4.199,00 no Pix</strong>
      <p>ou R$ 4.564,13 parcelado no cartao</p>
    </body></html>
    """

    extracted = extract_offer_from_html(html, fallback_title="GPU")
    conditions = {condition.condition_type: condition.amount for condition in extracted.price_conditions}

    assert extracted.recommended_condition == "pix"
    assert conditions["previous"] > conditions["pix"]
    assert conditions["pix"].to_eng_string() == "4199.00"


def test_revalidate_option_persists_promotional_price_condition(client: TestClient, db: Session, monkeypatch):
    login_admin(client)
    created = client.post("/api/v1/purchases/needs", json={
        "title": "Validar preco promocional",
        "items": [{
            "free_text_description": "Placa de video QA",
            "quantity": 1,
            "unit_of_measure": "un",
            "classification": "EXTERNAL",
        }],
    })
    assert created.status_code == 201
    item_id = created.json()["items"][0]["id"]

    option = client.post(f"/api/v1/purchases/items/{item_id}/options", json={
        "source_type": "EXTERNAL_MARKET",
        "store_name": "Loja QA",
        "title": "Placa de Video QA",
        "product_url": "https://www.kabum.com.br/produto/qa",
        "unit_price": 5240.09,
        "shipping_price": 0,
        "total_price": 5240.09,
    })
    assert option.status_code == 201
    option_id = option.json()["id"]

    html = """
    <html><head><title>Placa de Video QA</title></head>
    <body>
      <span>De R$ 5.240,09</span>
      <strong>R$ 4.199,00 no Pix</strong>
      <p>ou R$ 4.564,13 parcelado no cartao</p>
    </body></html>
    """
    monkeypatch.setattr("app.modules.purchases.research_engine.is_safe_url", lambda url: (True, url))
    monkeypatch.setattr("app.modules.purchases.research_engine.safe_fetch_html", lambda *args, **kwargs: html)

    response = client.post(f"/api/v1/purchases/options/{option_id}/revalidate")

    assert response.status_code == 200
    payload = response.json()
    assert payload["unit_price"] == 4199.0
    assert payload["payment_summary"] == "Pix"
    assert any(cond["condition_type"] == "pix" and cond["is_recommended"] for cond in payload["price_conditions"])
    assert db.query(PurchaseOfferPriceCondition).filter(
        PurchaseOfferPriceCondition.option_id == uuid.UUID(option_id),
        PurchaseOfferPriceCondition.condition_type == "pix",
    ).count() == 1


def test_external_search_missing_credentials_returns_human_message(client: TestClient, monkeypatch):
    login_admin(client)
    monkeypatch.setenv("PURCHASES_SEARCH_FORCE_REAL", "true")
    monkeypatch.delenv("SERPAPI_API_KEY", raising=False)

    response = client.get("/api/v1/purchases/external-search?q=Memoria%20RAM%20DDR4")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "credentials_missing"
    assert payload["results"] == []
    assert "SERPAPI" not in payload["message"].upper()
    assert "SERPAPI_API_KEY" not in payload["message"]
    assert "missing_keys" not in payload
    assert "provider" not in payload


def test_purchase_research_session_persists_progress_evidence_and_recommendation(
    client: TestClient,
    db: Session,
    monkeypatch,
):
    login_admin(client)
    monkeypatch.setattr(settings, "PURCHASES_SEARXNG_URL", "")
    monkeypatch.setattr(settings, "PURCHASES_RESEARCH_ASYNC_ENABLED", False)

    created = client.post("/api/v1/purchases/needs", json={
        "title": "Memoria RAM para pesquisa persistente",
        "items": [
            {
                "free_text_description": "Memoria RAM DDR4",
                "quantity": 2,
                "unit_of_measure": "un",
                "classification": "EXTERNAL",
                "budget_limit": 4000,
                "destination": "PC do Operador Demo",
            }
        ],
    })
    assert created.status_code == 201
    payload = created.json()
    item_id = payload["items"][0]["id"]

    response = client.post(
        f"/api/v1/purchases/items/{item_id}/research-sessions",
        json={"query": "Memoria RAM DDR4 para o PC do Operador Demo ate R$ 4000"},
    )
    assert response.status_code == 200
    session_payload = response.json()
    assert session_payload["purchase_item_id"] == item_id
    assert session_payload["progress_percent"] >= 70
    assert session_payload["recommendation_summary"]["summary"]
    assert session_payload["options"]
    assert session_payload["canonical_products"]

    session_id = uuid.UUID(session_payload["id"])
    assert db.query(PurchaseSearchSession).filter(PurchaseSearchSession.id == session_id).first() is not None
    assert db.query(PurchaseOfferFieldEvidence).filter(
        PurchaseOfferFieldEvidence.search_session_id == session_id
    ).count() > 0

    reloaded = client.get(f"/api/v1/purchases/research-sessions/{session_id}")
    assert reloaded.status_code == 200
    assert reloaded.json()["options"][0]["verification_status"] in {"CONFIRMED", "PARTIALLY_CONFIRMED", "DISCOVERED"}

    recommendation = client.get(f"/api/v1/purchases/items/{item_id}/recommendation")
    assert recommendation.status_code == 200
    assert recommendation.json()["summary"]
    assert "SerpApi" not in str(recommendation.json())
    assert "SearXNG" not in str(recommendation.json())


def test_purchase_item_approval_is_optional_and_targets_exact_item(client: TestClient, db: Session):
    login_admin(client)

    created = client.post("/api/v1/purchases/needs", json={
        "title": "Memoria RAM com aprovacao por item",
        "items": [
            {
                "free_text_description": "Memoria RAM DDR4",
                "quantity": 1,
                "unit_of_measure": "un",
                "classification": "EXTERNAL",
            }
        ],
    })
    assert created.status_code == 201
    item_id = created.json()["items"][0]["id"]

    option = client.post(f"/api/v1/purchases/items/{item_id}/options", json={
        "source_type": "EXTERNAL_MARKET",
        "store_name": "Loja Teste",
        "seller_name": "Loja Teste",
        "title": "Memoria RAM DDR4 16GB",
        "unit_price": 250,
        "shipping_price": 20,
        "total_price": 270,
        "delivery_estimate": "3 dias",
        "product_url": "https://example.com/produto/memoria-ddr4",
    })
    assert option.status_code == 201
    option_id = option.json()["id"]

    approval_response = client.post(
        f"/api/v1/purchases/items/{item_id}/request-approval",
        json={"option_id": option_id, "justification": "Compra acima da politica do setor."},
    )
    assert approval_response.status_code == 200
    updated = approval_response.json()
    assert updated["status"] == "PENDING_APPROVAL"
    assert updated["items"][0]["approval_status"] == "PENDING"

    approval = db.query(Approval).filter(Approval.id == updated["approval_id"]).first()
    assert approval is not None
    assert approval.action_payload["request_type"] == "purchase_options"
    assert approval.action_payload["item_approval"] is True
    assert approval.action_payload["items"][0]["purchase_item_id"] == item_id
    assert approval.action_payload["items"][0]["selected_option_id"] == option_id


def test_prepare_supplier_rfq_for_item_creates_review_draft(client: TestClient, setup_master_data):
    login_admin(client)
    supplier1 = setup_master_data["supplier_a"]
    supplier2 = setup_master_data["supplier_b"]

    created = client.post("/api/v1/purchases/needs", json={
        "title": "Arame para cotacao direta",
        "items": [
            {
                "free_text_description": "Arame BTC CL 1,5 mm",
                "quantity": 1,
                "unit_of_measure": "un",
                "classification": "INTERNAL",
            }
        ],
    })
    assert created.status_code == 201
    item_id = created.json()["items"][0]["id"]

    response = client.post(
        f"/api/v1/purchases/items/{item_id}/prepare-supplier-rfq",
        json={"supplier_ids": [str(supplier1.id), str(supplier2.id)], "homologation_mode": True},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["supplier_count"] == 2
    assert payload["homologation_mode"] is True
    assert payload["message"] == "Cotacao preparada para revisao antes do envio."


@pytest.fixture
def setup_master_data(db: Session):
    """Cria cadastros mestres para testes de compras."""
    # 1. Pessoa e Fornecedor 1
    person1 = Person(
        id=uuid.uuid4(),
        type="COMPANY",
        name="Fornecedor Teste A",
        document_type="CNPJ",
        document_number="11111111000111",
        email="fornecedora@teste.com",
        is_active=True
    )
    db.add(person1)
    db.flush()
    
    supplier1 = Supplier(
        id=uuid.uuid4(),
        person_id=person1.id,
        supplier_code="FOR-A",
        preferred_contact_email="fornecedora@teste.com",
        status="ACTIVE"
    )
    db.add(supplier1)
    
    # 2. Pessoa e Fornecedor 2
    person2 = Person(
        id=uuid.uuid4(),
        type="COMPANY",
        name="Fornecedor Teste B",
        document_type="CNPJ",
        document_number="22222222000122",
        email="fornecedorb@teste.com",
        is_active=True
    )
    db.add(person2)
    db.flush()
    
    supplier2 = Supplier(
        id=uuid.uuid4(),
        person_id=person2.id,
        supplier_code="FOR-B",
        preferred_contact_email="fornecedorb@teste.com",
        status="ACTIVE"
    )
    db.add(supplier2)
    
    # 3. Produto
    product = ProductItem(
        id=uuid.uuid4(),
        sku=f"PROD-{uuid.uuid4().hex[:6].upper()}",
        name="Produto Master Teste",
        item_type="RAW_MATERIAL",
        unit_of_measure="un",
        is_active=True
    )
    db.add(product)
    
    # 4. Serviço
    service = Service(
        id=uuid.uuid4(),
        code=f"SERV-{uuid.uuid4().hex[:6].upper()}",
        name="Servico Master Teste",
        is_active=True
    )
    db.add(service)
    
    db.commit()
    
    return {
        "supplier_a": supplier1,
        "supplier_b": supplier2,
        "product": product,
        "service": service
    }


def test_create_purchase_request_validation(client: TestClient, db: Session, setup_master_data):
    login_admin(client)
    master = setup_master_data

    # Payload válido misturando item_id, service_id e free_text_description
    payload = {
        "title": "Requisicao de Compra TI",
        "description": "Necessidade de insumos para os novos devs",
        "justification": "Contratacao de 3 devs",
        "priority": "HIGH",
        "category": "TI",
        "items": [
            {
                "item_id": str(master["product"].id),
                "quantity": 10,
                "unit": "un",
                "estimated_unit_price": 50.0
            },
            {
                "service_id": str(master["service"].id),
                "quantity": 2,
                "unit": "h",
                "estimated_unit_price": 120.0
            },
            {
                "free_text_description": "Teclado Mecanico Avulso",
                "quantity": 5,
                "unit": "un",
                "estimated_unit_price": 80.0
            }
        ]
    }

    response = client.post("/api/v1/purchases/requests", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Requisicao de Compra TI"
    assert data["status"] == "DRAFT"
    assert data["priority"] == "HIGH"
    
    # 10*50 + 2*120 + 5*80 = 500 + 240 + 400 = 1140
    assert float(data["estimated_total"]) == 1140.0
    assert len(data["items"]) == 3

    # Verifica se os itens foram criados corretamente
    db_items = db.query(PurchaseRequestItem).filter(PurchaseRequestItem.purchase_request_id == uuid.UUID(data["id"])).all()
    assert len(db_items) == 3
    
    # Evento foi gerado
    event = db.query(EventLog).filter(
        EventLog.event_type == "purchase.request.created",
        EventLog.aggregate_id == data["id"]
    ).first()
    assert event is not None
    assert event.payload["title"] == "Requisicao de Compra TI"

    # Notificação foi criada
    notif = db.query(Notification).filter(
        Notification.event_type == "purchase.request.created",
        Notification.source_id == data["id"]
    ).first()
    assert notif is not None
    assert notif.role_target == "MANAGER"


def test_create_purchase_request_invalid_references(client: TestClient, db: Session, setup_master_data):
    login_admin(client)
    
    # 1. item_id inexistente
    payload_invalid_item = {
        "title": "Compra Invalida",
        "items": [
            {
                "item_id": str(uuid.uuid4()),
                "quantity": 1
            }
        ]
    }
    response = client.post("/api/v1/purchases/requests", json=payload_invalid_item)
    assert response.status_code == 400
    assert "no Master Data" in response.json()["detail"]

    # 2. Sem item_id, service_id ou free_text_description
    payload_empty_item = {
        "title": "Compra Invalida 2",
        "items": [
            {
                "quantity": 1
            }
        ]
    }
    response2 = client.post("/api/v1/purchases/requests", json=payload_empty_item)
    assert response2.status_code == 400
    assert "precisa ter item_id, service_id ou free_text_description" in response2.json()["detail"]


def test_parse_purchase_need_does_not_force_external_text_into_stock(client: TestClient, monkeypatch):
    login_admin(client)

    def fake_list_items(*args, **kwargs):
        return [
            _stock_match(
                "00000000-0000-0000-0000-000000000015",
                "Arame BTC CL 1,5 mm",
                specification="1,5 mm",
            )
        ]

    monkeypatch.setattr(StockCatalogService, "list_items", fake_list_items)

    response = client.post("/api/v1/purchases/needs/parse-text", json={"text": "Memoria RAM DDR4"})

    assert response.status_code == 200
    line = response.json()[0]
    assert line["description"] == "Memoria RAM DDR4"
    assert line["purchase_type"] == "external"
    assert line["suggested_stock_catalog_item_id"] is None
    assert "compra externa" in line["classification_message"].lower()


def test_parse_purchase_need_links_strong_stock_match(client: TestClient, monkeypatch):
    login_admin(client)

    stock_id = "00000000-0000-0000-0000-000000000015"

    def fake_list_items(*args, **kwargs):
        return [
            _stock_match(
                stock_id,
                "Arame BTC CL 1,5 mm",
                specification="Arame BTC CL 1,5 mm 1,5 mm",
            )
        ]

    monkeypatch.setattr(StockCatalogService, "list_items", fake_list_items)

    response = client.post("/api/v1/purchases/needs/parse-text", json={"text": "Arame BTC CL 1,5 mm"})

    assert response.status_code == 200
    line = response.json()[0]
    assert line["purchase_type"] == "internal"
    assert line["suggested_stock_catalog_item_id"] == stock_id
    assert line["match_score"] >= 0.72
    assert "Item interno" in line["classification_message"]


def test_permission_gates_purchases(client: TestClient, db: Session, setup_master_data):
    master = setup_master_data
    
    # Usuário comum (sem login)
    logout(client)
    res = client.get("/api/v1/purchases/requests")
    assert res.status_code == 401

    # Usuário logado mas sem permissão de MANAGER tentando criar fornecedor
    login_user(client)
    res_create_supplier = client.post("/api/v1/purchases/suppliers", json={
        "company_name": "Novo Fornecedor Hacker",
        "cnpj": "99999999000199"
    })
    assert res_create_supplier.status_code == 403


def test_complete_rfq_flow(client: TestClient, db: Session, setup_master_data):
    login_admin(client)
    master = setup_master_data

    # 1. Cria Recomposição/Requisição de compra e aprova
    req_payload = {
        "title": "Compra de Servidores Dell",
        "items": [
            {
                "item_id": str(master["product"].id),
                "quantity": 2,
                "estimated_unit_price": 5000.0
            }
        ]
    }
    req_res = client.post("/api/v1/purchases/requests", json=req_payload)
    assert req_res.status_code == 201
    req_id = req_res.json()["id"]

    # Mudar status para APPROVED para permitir RFQ (emulador de fluxo de aprovações)
    req_db = db.query(PurchaseRequest).filter(PurchaseRequest.id == uuid.UUID(req_id)).first()
    req_db.status = "APPROVED"
    db.commit()

    # 2. Cria RFQ
    rfq_payload = {
        "title": "RFQ Servidores Dell",
        "deadline": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat(),
        "message_template": "Olá {supplier_name}, cote {request_title} com os itens:\n{items_list}."
    }
    rfq_res = client.post(f"/api/v1/purchases/requests/{req_id}/rfqs", json=rfq_payload)
    assert rfq_res.status_code == 201
    rfq_id = rfq_res.json()["id"]
    assert rfq_res.json()["title"] == "RFQ Servidores Dell"
    assert rfq_res.json()["status"] == "DRAFT"

    # Status da requisição mudou para RFQ_PREPARING
    db.refresh(req_db)
    assert req_db.status == "RFQ_PREPARING"

    # 3. Adiciona Fornecedores (com bloqueio para inexistente)
    sup_err_res = client.post(f"/api/v1/purchases/rfqs/{rfq_id}/suppliers", json={"supplier_id": str(uuid.uuid4())})
    assert sup_err_res.status_code == 400

    sup_a_res = client.post(f"/api/v1/purchases/rfqs/{rfq_id}/suppliers", json={"supplier_id": str(master["supplier_a"].id)})
    assert sup_a_res.status_code == 201
    assert sup_a_res.json()["status"] == "DRAFT"

    sup_b_res = client.post(f"/api/v1/purchases/rfqs/{rfq_id}/suppliers", json={"supplier_id": str(master["supplier_b"].id)})
    assert sup_b_res.status_code == 201

    # 4. Gera rascunhos de RFQ
    drafts_res = client.post(f"/api/v1/purchases/rfqs/{rfq_id}/generate-drafts")
    assert drafts_res.status_code == 200
    assert len(drafts_res.json()) == 2
    assert drafts_res.json()[0]["status"] == "READY"
    assert drafts_res.json()[0]["message_subject"] is not None
    assert drafts_res.json()[0]["message_body"] is not None
    
    # Garante que NÃO enviou e-mail (sent_at é nulo)
    assert drafts_res.json()[0]["sent_at"] is None

    # Visualiza rascunhos via GET
    get_drafts = client.get(f"/api/v1/purchases/rfqs/{rfq_id}/drafts")
    assert get_drafts.status_code == 200
    assert len(get_drafts.json()) == 2
    assert get_drafts.json()[0]["subject"].startswith("Solicitação de Cotação")
    assert "Dell" in get_drafts.json()[0]["body"]

    # 5. Registra respostas de cotações
    rfq_sup_a = db.query(PurchaseRFQSupplier).filter(
        PurchaseRFQSupplier.rfq_id == uuid.UUID(rfq_id),
        PurchaseRFQSupplier.supplier_id == master["supplier_a"].id
    ).first()
    
    rfq_sup_b = db.query(PurchaseRFQSupplier).filter(
        PurchaseRFQSupplier.rfq_id == uuid.UUID(rfq_id),
        PurchaseRFQSupplier.supplier_id == master["supplier_b"].id
    ).first()

    req_item_id = req_db.items[0].id

    # Resposta Fornecedor A: R$ 4.500,00 cada, 3 dias de entrega
    resp_a_payload = {
        "rfq_supplier_id": str(rfq_sup_a.id),
        "supplier_id": str(master["supplier_a"].id),
        "total_amount": 9000.0,
        "delivery_days": 3,
        "payment_terms": "Faturado 15 dias",
        "lines": [
            {
                "request_item_id": str(req_item_id),
                "description": "Servidor Teste",
                "quantity": 2,
                "unit_price": 4500.0,
                "delivery_days": 3
            }
        ]
    }
    resp_a_res = client.post(f"/api/v1/purchases/rfqs/{rfq_id}/responses", json=resp_a_payload)
    assert resp_a_res.status_code == 201

    # Resposta Fornecedor B: R$ 4.200,00 cada, 10 dias de entrega (Mais barato, mais lento)
    resp_b_payload = {
        "rfq_supplier_id": str(rfq_sup_b.id),
        "supplier_id": str(master["supplier_b"].id),
        "total_amount": 8400.0,
        "delivery_days": 10,
        "payment_terms": "Faturado 30 dias",
        "lines": [
            {
                "request_item_id": str(req_item_id),
                "description": "Servidor Teste",
                "quantity": 2,
                "unit_price": 4200.0,
                "delivery_days": 10
            }
        ]
    }
    resp_b_res = client.post(f"/api/v1/purchases/rfqs/{rfq_id}/responses", json=resp_b_payload)
    assert resp_b_res.status_code == 201

    # 6. Gera Comparativo side-by-side
    comp_res = client.get(f"/api/v1/purchases/rfqs/{rfq_id}/comparison")
    assert comp_res.status_code == 200
    comp_data = comp_res.json()
    
    # Melhor preço deve ser Fornecedor B (8400 < 9000)
    assert comp_data["best_supplier_id"] == str(master["supplier_b"].id)
    assert "Fornecedor Teste B" in comp_data["recommendation_summary"]
    
    # 2 ofertas no agrupamento por item
    assert len(comp_data["items_comparison"]) == 1
    assert len(comp_data["items_comparison"][0]["offers"]) == 2
    
    # Resumos consolidados
    assert len(comp_data["suppliers_summary"]) == 2
    summary_b = next(s for s in comp_data["suppliers_summary"] if s["supplier_id"] == str(master["supplier_b"].id))
    assert summary_b["is_best_price"] is True
    assert summary_b["is_best_delivery"] is False
    
    summary_a = next(s for s in comp_data["suppliers_summary"] if s["supplier_id"] == str(master["supplier_a"].id))
    assert summary_a["is_best_price"] is False
    assert summary_a["is_best_delivery"] is True

    # 7. Compatibilidade: envio de cotacao nao exige aprovacao formal
    approval_send_res = client.post(f"/api/v1/purchases/rfqs/{rfq_id}/request-send-approval")
    assert approval_send_res.status_code == 200
    assert approval_send_res.json()["status"] == "no_approval_required"

    # Status da cotacao nao muda para fila de aprovacao
    rfq_db = db.query(PurchaseRFQ).filter(PurchaseRFQ.id == uuid.UUID(rfq_id)).first()
    assert rfq_db.status != "PENDING_APPROVAL"

    # Nao cria ActionIntent para trabalho normal de compras
    intent_db = db.query(ActionIntent).filter(
        ActionIntent.proposed_action == "send_rfq",
        ActionIntent.target_id == rfq_id
    ).first()
    assert intent_db is None

    # 8. Teste de Envio Direto
    rfq_db.status = "READY"
    db.commit()

    send_res = client.post(f"/api/v1/purchases/rfqs/{rfq_id}/send")
    assert send_res.status_code == 200
    assert send_res.json()["status"] == "SENT"

    # Reenvio de e-mail de cotação para fornecedor específico
    resend_res = client.post(f"/api/v1/purchases/rfqs/{rfq_id}/suppliers/{str(master['supplier_a'].id)}/resend")
    assert resend_res.status_code == 200
    assert resend_res.json()["status"] == "SENT"

    # Escolha de fornecedor vencedor
    choose_res = client.post(f"/api/v1/purchases/rfqs/{rfq_id}/choose-supplier", json={"quote_response_id": str(resp_b_res.json()["id"])})
    assert choose_res.status_code == 200
    assert choose_res.json()["status"] == "ORDERED"


def test_purchases_overview_and_attention_use_real_rfq_flow(client: TestClient, db: Session, setup_master_data):
    login_admin(client)
    master = setup_master_data

    req_res = client.post("/api/v1/purchases/requests", json={
        "title": "Cotacao operacional de motores",
        "items": [
            {
                "item_id": str(master["product"].id),
                "quantity": 3,
                "estimated_unit_price": 100.0,
            }
        ],
    })
    assert req_res.status_code == 201
    req_id = req_res.json()["id"]

    req_db = db.query(PurchaseRequest).filter(PurchaseRequest.id == uuid.UUID(req_id)).first()
    req_db.status = "APPROVED"
    db.commit()

    rfq_res = client.post(f"/api/v1/purchases/requests/{req_id}/rfqs", json={
        "title": "Cotacao de motores",
        "deadline": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
    })
    assert rfq_res.status_code == 201
    rfq_id = rfq_res.json()["id"]

    supplier_res = client.post(f"/api/v1/purchases/rfqs/{rfq_id}/suppliers", json={
        "supplier_id": str(master["supplier_a"].id),
    })
    assert supplier_res.status_code == 201

    drafts_res = client.post(f"/api/v1/purchases/rfqs/{rfq_id}/generate-drafts")
    assert drafts_res.status_code == 200

    overview_res = client.get("/api/v1/purchases/overview")
    assert overview_res.status_code == 200
    overview = overview_res.json()
    assert overview["summary"]["total_requests"] >= 1
    assert any(group["key"] == "preparation" for group in overview["status_groups"])
    assert any(row["request_id"] == req_id for row in overview["ongoing_quotes"])

    attention_res = client.get("/api/v1/purchases/attention")
    assert attention_res.status_code == 200
    attention = attention_res.json()
    assert any(item["type"] == "quote_ready_for_review" and item["quote_id"] == rfq_id for item in attention)

    quotes_res = client.get("/api/v1/purchases/quotes")
    assert quotes_res.status_code == 200
    assert any(quote["id"] == rfq_id for quote in quotes_res.json())


def test_assisted_quote_pr2_flow_catalog_list_suppliers_preview(client: TestClient, db: Session, setup_master_data):
    login_admin(client)
    master = setup_master_data

    import_run = StockCatalogImportRun(
        source_type="COMPRAS_NOVA",
        source_path="sanitized.xlsx",
        source_filename="sanitized.xlsx",
        source_hash=uuid.uuid4().hex,
        status="SUCCESS",
    )
    db.add(import_run)
    db.flush()

    catalog_item = StockCatalogItem(
        import_run_id=import_run.id,
        source_sheet="Materiais",
        display_name='Parafuso Allen inox 1/4"',
        base_name="Parafuso Allen inox",
        normalized_name="parafuso allen inox 1/4",
        variation_label='1/4"',
        normalized_measure="1/4",
        measure_display='1/4"',
        specification_text='Parafuso Allen inox 1/4"',
        identity_hash=uuid.uuid4().hex,
        internal_code="CYB-PA-14",
        canonical_category="fixadores",
        canonical_category_display="Fixadores",
    )
    stock_supplier = StockCatalogSupplier(
        name="Fornecedor Teste A",
        normalized_name="fornecedor teste a",
        email="fornecedora@teste.com",
        active=True,
    )
    db.add(catalog_item)
    db.add(stock_supplier)
    db.flush()

    offer = StockCatalogOffer(
        item_id=catalog_item.id,
        supplier_id=stock_supplier.id,
        import_run_id=import_run.id,
        source_sheet="Materiais",
        source_row=10,
        price=12.5,
        unit="un",
        contact_email="fornecedora@teste.com",
        is_current=True,
    )
    db.add(offer)
    db.commit()

    create_res = client.post("/api/v1/purchases/quotes", json={
        "title": "Cotacao PR2",
        "description": "Fluxo assistido",
        "origin_type": "manual",
    })
    assert create_res.status_code == 201
    quote = create_res.json()
    quote_id = quote["id"]
    assert quote["purchase_request_id"]
    assert quote["status"] == "DRAFT"

    add_item_res = client.post(f"/api/v1/purchases/quotes/{quote_id}/items", json={
        "stock_catalog_item_id": str(catalog_item.id),
        "free_text_description": catalog_item.display_name,
        "quantity": 5,
        "unit_of_measure": "un",
        "specifications": catalog_item.specification_text,
        "source_type": "stock_catalog",
        "source_ref_id": str(catalog_item.id),
        "source_confidence": "high",
        "match_status": "confirmed",
        "source_snapshot_json": {
            "display_name": catalog_item.display_name,
            "internal_code": catalog_item.internal_code,
            "specification_text": catalog_item.specification_text,
        },
    })
    assert add_item_res.status_code == 201
    detail_res = client.get(f"/api/v1/purchases/quotes/{quote_id}")
    assert detail_res.status_code == 200
    quote = detail_res.json()
    assert quote["items"][0]["stock_catalog_item_id"] == str(catalog_item.id)
    assert quote["items"][0]["match_status"] == "confirmed"
    item_id = quote["items"][0]["id"]

    parse_res = client.post(f"/api/v1/purchases/quotes/{quote_id}/parse-list", json={
        "text": '5 un Parafuso Allen inox 1/4"\nsem quantidade item duvidoso',
    })
    assert parse_res.status_code == 200
    parsed = parse_res.json()
    assert parsed[0]["quantity"] == 5
    assert parsed[0]["confidence"] in {"high", "check", "low"}
    assert any(line["match_status"] == "needs_confirmation" for line in parsed)

    suggestions_res = client.get(f"/api/v1/purchases/quotes/{quote_id}/supplier-suggestions")
    assert suggestions_res.status_code == 200
    suggestions = suggestions_res.json()
    known = next(item for item in suggestions if item["supplier_id"] == str(master["supplier_a"].id))
    assert known["coverage_count"] == 1
    assert "tem contato valido" in known["reasons"]

    selection_res = client.post(f"/api/v1/purchases/quotes/{quote_id}/supplier-selection", json={
        "suppliers": [
            {
                "supplier_id": str(master["supplier_a"].id),
                "item_ids": [item_id],
            }
        ]
    })
    assert selection_res.status_code == 200
    assert db.query(PurchaseRFQSupplierItem).count() == 1

    previews_res = client.get(f"/api/v1/purchases/quotes/{quote_id}/email-previews")
    assert previews_res.status_code == 200
    previews = previews_res.json()
    assert len(previews) == 1
    preview = previews[0]
    assert preview["sender_email"] == "compras@portal.example"
    assert preview["bcc_enabled"] is True
    assert preview["content_hash"]
    assert "Parafuso Allen" in preview["body_html"]
    assert "12.5" not in preview["body_html"]

    accounts_res = client.get("/api/v1/purchases/sender-accounts")
    assert accounts_res.status_code == 200
    accounts = accounts_res.json()
    assert {account["email"] for account in accounts} == {"compras@portal.example", "compras@empresa-parceira.example"}
    assert all(account["bcc_default_enabled"] is True for account in accounts)
    assert all(account["is_configured"] is False for account in accounts)

    stock_res = client.post(f"/api/v1/purchases/stock-items/{catalog_item.id}/quote-draft")
    assert stock_res.status_code == 201
    stock_quote = stock_res.json()
    assert stock_quote["quote_id"]
    assert stock_quote["quote_id"] == quote_id
    assert stock_quote["action_url"].startswith("/purchases?quote=")
    assert stock_quote["existing_quote"] is True

    repeated_stock_res = client.post(f"/api/v1/purchases/stock-items/{catalog_item.id}/quote-draft")
    assert repeated_stock_res.status_code == 201
    repeated_stock_quote = repeated_stock_res.json()
    assert repeated_stock_quote["quote_id"] == stock_quote["quote_id"]
    assert repeated_stock_quote["existing_quote"] is True
    assert repeated_stock_quote["message"] == "Ja existe uma cotacao em andamento para este item."


def test_external_search_provider_and_endpoints(client: TestClient, db: Session):
    login_admin(client)
    
    # 1. Testa a rota external-search (vai usar o MockProductSearchProvider por estar em ambiente pytest)
    res = client.get("/api/v1/purchases/external-search?q=memoria+ram")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert len(data["results"]) >= 2
    assert "cheapest_id" in data["classifications"]
    
    # Valida tags atribuídas
    tags = [r.get("tags") for r in data["results"] if r.get("tags")]
    assert len(tags) > 0
    assert any("Menor Preço" in t for t in tags)

    # 2. Testa importação de URL de produto seguro e controle de SSRF
    import_link_payload = {"url": "https://www.amazon.com.br/dp/B09D8PPYF8"}
    res_link = client.post("/api/v1/purchases/needs/import-link", json=import_link_payload)
    assert res_link.status_code == 200
    data_link = res_link.json()
    assert data_link["status"] == "success"
    assert data_link["can_create_request"] is True
    assert data_link["suggested_request"]["items"][0]["classification"] == "EXTERNAL"

    # Testa bloqueio de SSRF (localhost)
    bad_link_payload = {"url": "http://localhost:8000/something"}
    res_bad = client.post("/api/v1/purchases/needs/import-link", json=bad_link_payload)
    assert res_bad.status_code == 400
    assert "bloqueado" in res_bad.json()["detail"].lower()


def test_purchase_option_selection_and_workflow(client: TestClient, db: Session, setup_master_data):
    login_admin(client)
    master = setup_master_data

    # Cria corrida de importação e catalog_item para teste no SQLite
    import_run = StockCatalogImportRun(
        source_type="COMPRAS_NOVA",
        source_path="sanitized.xlsx",
        source_filename="sanitized.xlsx",
        source_hash=uuid.uuid4().hex,
        status="SUCCESS",
    )
    db.add(import_run)
    db.flush()

    catalog_item = StockCatalogItem(
        import_run_id=import_run.id,
        source_sheet="Materiais",
        display_name='Cabo de Rede Cat6',
        base_name="Cabo de Rede",
        normalized_name="cabo de rede cat6",
        active=True,
        identity_hash=uuid.uuid4().hex
    )
    db.add(catalog_item)
    db.commit()

    # 1. Cria necessidade de compras mista
    req_res = client.post("/api/v1/purchases/needs", json={
        "title": "Manutenção PC Operador Demo",
        "items": [
            {
                "free_text_description": "Memória RAM DDR5 16GB",
                "quantity": 1,
                "classification": "EXTERNAL",
                "estimated_unit_price": 1500.0
            },
            {
                "stock_catalog_item_id": str(catalog_item.id),
                "free_text_description": "Cabo de rede",
                "quantity": 2,
                "classification": "INTERNAL",
                "estimated_unit_price": 10.0
            }
        ],
    })
    assert req_res.status_code == 201
    req_id = req_res.json()["id"]
    item_id = req_res.json()["items"][0]["id"]
    internal_item_id = req_res.json()["items"][1]["id"]

    # 2. Adiciona uma opção para o item externo
    option_payload = {
        "source_type": "EXTERNAL_MARKET",
        "store_name": "Kabum",
        "title": "Memória RAM DDR5 Corsair 16GB",
        "unit_price": 1450.0,
        "shipping_price": 20.0,
        "total_price": 1470.0,
        "delivery_estimate": "3 dias",
        "availability": True
    }
    opt_res = client.post(f"/api/v1/purchases/items/{item_id}/options", json=option_payload)
    assert opt_res.status_code == 201
    option_id = opt_res.json()["id"]

    # 3. Lista as opções do item
    list_res = client.get(f"/api/v1/purchases/items/{item_id}/options")
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1
    assert list_res.json()[0]["title"] == "Memória RAM DDR5 Corsair 16GB"

    # 4. Seleciona a opção
    sel_res = client.post(f"/api/v1/purchases/items/{item_id}/options/{option_id}/select")
    assert sel_res.status_code == 200
    assert sel_res.json()["selected_option_id"] == option_id
    assert sel_res.json()["estimated_unit_price"] == 1470.0

    # 5. Envia para Aprovação (Fase 14)
    submit_res = client.post(f"/api/v1/purchases/requests/{req_id}/send-to-approval")
    assert submit_res.status_code == 200
    approval_id = submit_res.json()["approval_id"]

    # 6. Aprova a solicitação com a opção decidida (Fase 14)
    decision_payload = {
        "reason": "Aprovado com a opção selecionada",
        "result_payload": {
            "items": [
                {
                    "item_id": str(item_id),
                    "decision": "APPROVED",
                    "selected_option_id": str(option_id),
                    "quantity": 1
                },
                {
                    "item_id": str(internal_item_id),
                    "decision": "APPROVED",
                    "quantity": 2
                }
            ]
        }
    }
    dec_res = client.post(f"/api/v1/approvals/{approval_id}/approve", json=decision_payload)
    assert dec_res.status_code == 200

    # Verifica se a requisição passou para APPROVED no banco de dados
    req_db = db.query(PurchaseRequest).filter(PurchaseRequest.id == uuid.UUID(req_id)).first()
    assert req_db.status == "APPROVED"
    assert req_db.items[0].approval_status == "APPROVED"
    assert str(req_db.items[0].selected_option_id) == option_id

    # 7. Registra Pedido de Compra (Fase 15)
    order_payload = {
        "final_value": 1490.0,
        "shipping_price": 20.0,
        "order_number": "PED-998877",
        "payment_method": "Boleto",
        "notes": "Compra efetuada com sucesso"
    }
    order_res = client.post(f"/api/v1/purchases/needs/{req_id}/place-order", json=order_payload)
    assert order_res.status_code == 200
    assert order_res.json()["status"] == "ORDERED"

    # 8. Registra Recebimento / Entrega e Entrada no Estoque (Fase 16)
    receive_payload = {
        "items": [
            {
                "item_id": str(item_id),
                "quantity_received": 1.0,
                "is_damaged": False,
                "save_in_catalog": True
            },
            {
                "item_id": str(internal_item_id),
                "quantity_received": 2.0,
                "is_damaged": False,
                "save_in_catalog": False
            }
        ],
        "notes": "Tudo entregue sem avarias"
    }
    rec_res = client.post(f"/api/v1/purchases/needs/{req_id}/receive-delivery", json=receive_payload)
    assert rec_res.status_code == 200
    assert rec_res.json()["status"] == "DELIVERED"
    
    # Valida que o item externo agora tem um stock_catalog_item_id
    db.refresh(req_db)
    assert req_db.items[0].stock_catalog_item_id is not None


def test_purchase_need_patch_updates_ambiguous_item_classification(client: TestClient, db: Session):
    login_admin(client)

    req_res = client.post("/api/v1/purchases/needs", json={
        "title": "Compra ambigua",
        "items": [{
            "free_text_description": "cabo pp 3x2,5",
            "quantity": 1,
            "classification": "AMBIGUOUS",
            "match_status": "needs_confirmation",
        }],
    })
    assert req_res.status_code == 201
    req_id = req_res.json()["id"]
    item_id = req_res.json()["items"][0]["id"]

    patch_res = client.patch(f"/api/v1/purchases/needs/{req_id}", json={
        "items": [{
            "id": item_id,
            "classification": "EXTERNAL",
            "match_status": "confirmed",
            "free_text_description": "Cabo PP 3x2,5",
        }]
    })

    assert patch_res.status_code == 200
    patched_item = patch_res.json()["items"][0]
    assert patched_item["classification"] == "EXTERNAL"
    assert patched_item["match_status"] == "confirmed"


def test_send_to_approval_carries_purchase_options_contract(client: TestClient, db: Session):
    from app.models.approval import Approval

    login_admin(client)

    req_res = client.post("/api/v1/purchases/needs", json={
        "title": "Compra externa com opcoes",
        "items": [{
            "free_text_description": "Memoria RAM DDR4",
            "quantity": 1,
            "classification": "EXTERNAL",
            "estimated_unit_price": 1500.0,
        }],
    })
    assert req_res.status_code == 201
    req_id = req_res.json()["id"]
    item_id = req_res.json()["items"][0]["id"]

    opt_res = client.post(f"/api/v1/purchases/items/{item_id}/options", json={
        "source_type": "EXTERNAL_MARKET",
        "store_name": "Fornecedor teste",
        "title": "Memoria RAM DDR4 16GB",
        "unit_price": 1450.0,
        "shipping_price": 30.0,
        "total_price": 1480.0,
    })
    assert opt_res.status_code == 201
    option_id = opt_res.json()["id"]
    assert client.post(f"/api/v1/purchases/items/{item_id}/options/{option_id}/select").status_code == 200

    submit_res = client.post(f"/api/v1/purchases/requests/{req_id}/send-to-approval")
    assert submit_res.status_code == 200
    approval_id = submit_res.json()["approval_id"]

    approval = db.query(Approval).filter(Approval.id == approval_id).first()
    assert approval is not None
    assert approval.action_payload["request_type"] == "purchase_options"
    assert approval.action_payload["return_url"] == f"/purchases?request={req_id}"
    assert approval.action_payload["items"][0]["selected_option_id"] == option_id
    assert approval.action_payload["items"][0]["options"][0]["title"] == "Memoria RAM DDR4 16GB"
