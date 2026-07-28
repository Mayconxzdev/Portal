import pytest
import uuid
import openpyxl
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta

from app.models.master_data import Person, ProductFamily, Supplier, ProductItem
from app.models.purchase import (
    PurchasePriceEvidence,
    PurchasePriceHistory,
    PurchasePriceReference,
    PurchaseSupplierPriceOffer,
    PurchasePriceUpdateSuggestion,
)
from app.models.event_log import EventLog
from app.models.notification import Notification
from app.models.module import Module
from app.models.user_module_access import UserModuleAccess
from app.models.user import User

# Helpers de autenticação
def login_admin(client: TestClient):
    client.post("/api/v1/auth/login", json={"username": "vesper_admin", "password": "admin"})

def login_user(client: TestClient):
    client.post("/api/v1/auth/login", json={"username": "vesper_user", "password": "userpass"})

def logout(client: TestClient):
    client.cookies.clear()

@pytest.fixture
def setup_price_test_data(db: Session):
    """Cria cadastros mestres e garante o módulo compras configurado para os testes de rastreabilidade."""
    # 1. Garante que o módulo compras exista no banco de testes
    purchases_module = db.query(Module).filter(Module.code == "purchases").first()
    if not purchases_module:
        purchases_module = Module(name="Compras", code="purchases", is_active=True, is_restricted=False)
        db.add(purchases_module)
        db.flush()

    # 2. Configura acesso do vesper_user para NORMAL em compras
    user_common = db.query(User).filter(User.username == "vesper_user").first()
    if user_common:
        # Remove acesso antigo se houver
        db.query(UserModuleAccess).filter(
            UserModuleAccess.user_id == user_common.id,
            UserModuleAccess.module_id == purchases_module.id
        ).delete()
        
        access = UserModuleAccess(
            user_id=user_common.id,
            module_id=purchases_module.id,
            permission_level="NORMAL"
        )
        db.add(access)

    # 3. Cria Fornecedor
    person = Person(
        id=uuid.uuid4(),
        type="COMPANY",
        name="Distribuidora de Parafusos Ltda",
        document_type="CNPJ",
        document_number="33333333000133",
        email="vendas@parafusos.com",
        is_active=True
    )
    db.add(person)
    db.flush()
    
    supplier = Supplier(
        id=uuid.uuid4(),
        person_id=person.id,
        supplier_code="DIST-PAR",
        preferred_contact_email="vendas@parafusos.com",
        status="ACTIVE"
    )
    db.add(supplier)
    
    # 4. Produto
    product = ProductItem(
        id=uuid.uuid4(),
        sku="PAR-SEXT-M8",
        name="Parafuso Sextavado M8",
        item_type="RAW_MATERIAL",
        unit_of_measure="cento",
        is_active=True
    )
    db.add(product)
    
    db.commit()
    
    return {
        "supplier": supplier,
        "product": product
    }


def test_create_price_evidence_as_normal_user(client: TestClient, db: Session, setup_price_test_data):
    """Garante que um comprador (user comum com acesso NORMAL) consegue registrar uma evidência de preço."""
    login_user(client)
    master = setup_price_test_data

    payload = {
        "source_type": "BOLETO",
        "supplier_id": str(master["supplier"].id),
        "product_item_id": str(master["product"].id),
        "document_number": "NF-8921",
        "document_date": datetime.now(timezone.utc).isoformat(),
        "unit_price": 45.50,
        "quantity": 10.0,
        "total_amount": 455.00,
        "currency": "BRL",
        "unit_of_measure": "cento",
        "payment_terms": "30 dias",
        "notes": "Compra de parafusos para manutenção emergencial."
    }

    response = client.post("/api/v1/purchases/prices/evidences", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["source_type"] == "BOLETO"
    assert data["document_number"] == "NF-8921"
    assert float(data["unit_price"]) == 45.50
    assert float(data["total_amount"]) == 455.00
    
    # Valida que UUIDs de usuário não estão expostos de forma crua no payload retornado (padrão de interface)
    assert "created_by_user_id" in data
    
    # 1. Verifica se a evidência foi salva no DB
    evidence_id = uuid.UUID(data["id"])
    evidence_db = db.query(PurchasePriceEvidence).filter(PurchasePriceEvidence.id == evidence_id).first()
    assert evidence_db is not None
    assert evidence_db.unit_price == 45.50

    # 2. Verifica se o registro de histórico imutável foi gerado
    history_db = db.query(PurchasePriceHistory).filter(PurchasePriceHistory.evidence_id == evidence_id).first()
    assert history_db is not None
    assert history_db.unit_price == 45.50

    # 3. Verifica se a sugestão de reajuste foi gerada e é classificada como NEW_REFERENCE (pois não havia preço de referência antigo)
    suggestion_db = db.query(PurchasePriceUpdateSuggestion).filter(PurchasePriceUpdateSuggestion.evidence_id == evidence_id).first()
    assert suggestion_db is not None
    assert suggestion_db.status == "PENDING"
    assert suggestion_db.old_unit_price is None
    assert suggestion_db.pct_variation is None
    assert suggestion_db.variation_direction == "NEW_REFERENCE"

    # 4. Verifica se os eventos foram emitidos no banco
    events = db.query(EventLog).filter(EventLog.aggregate_id == str(evidence_id)).all()
    # Devemos ter pelo menos o evento do evidence.created
    assert len(events) >= 1
    event_types = [e.event_type for e in events]
    assert "purchase.price.evidence.created" in event_types

    # E o da sugestão
    suggestion_event = db.query(EventLog).filter(
        EventLog.event_type == "purchase.price.suggestion.created",
        EventLog.aggregate_id == str(suggestion_db.id)
    ).first()
    assert suggestion_event is not None


def test_approve_price_suggestion_flow(client: TestClient, db: Session, setup_price_test_data):
    """Testa o fluxo completo: criar evidência -> gerar sugestão -> aprovar (como Admin/Manager) -> atualizar referência."""
    master = setup_price_test_data
    
    # 1. Registra a evidência inicial (preço base de R$ 40.00)
    login_user(client)
    payload_base = {
        "source_type": "MANUAL_ENTRY",
        "supplier_id": str(master["supplier"].id),
        "product_item_id": str(master["product"].id),
        "unit_price": 40.00,
        "quantity": 1.0,
        "total_amount": 40.00,
        "currency": "BRL",
        "notes": "Preço inicial acordado"
    }
    res_base = client.post("/api/v1/purchases/prices/evidences", json=payload_base)
    assert res_base.status_code == 201
    
    # 2. Como a aprovação é necessária, o preço de referência ativo ainda NÃO deve existir
    ref_base = db.query(PurchasePriceReference).filter(
        PurchasePriceReference.product_item_id == master["product"].id,
        PurchasePriceReference.supplier_id == master["supplier"].id,
        PurchasePriceReference.is_active == True
    ).first()
    assert ref_base is None

    # 3. Vamos aprovar a sugestão inicial usando o usuário Admin
    login_admin(client)
    suggestion_base = db.query(PurchasePriceUpdateSuggestion).filter(
        PurchasePriceUpdateSuggestion.product_item_id == master["product"].id,
        PurchasePriceUpdateSuggestion.status == "PENDING"
    ).first()
    assert suggestion_base is not None
    
    res_approve_base = client.post(
        f"/api/v1/purchases/prices/suggestions/{suggestion_base.id}/approve",
        json={"review_notes": "Preço base homologado"}
    )
    assert res_approve_base.status_code == 200
    assert res_approve_base.json()["status"] == "APPROVED"

    # 4. Agora o preço de referência ativo deve existir e ser R$ 40.00
    ref_active = db.query(PurchasePriceReference).filter(
        PurchasePriceReference.product_item_id == master["product"].id,
        PurchasePriceReference.supplier_id == master["supplier"].id,
        PurchasePriceReference.is_active == True
    ).first()
    assert ref_active is not None
    assert float(ref_active.current_unit_price) == 40.00

    # 5. Registra novo valor (R$ 46.00, variação de +15%)
    login_user(client)
    payload_new = {
        "source_type": "NF",
        "supplier_id": str(master["supplier"].id),
        "product_item_id": str(master["product"].id),
        "document_number": "NF-9090",
        "unit_price": 46.00,
        "quantity": 10.0,
        "total_amount": 460.00,
        "notes": "Compra faturada com aumento"
    }
    res_new = client.post("/api/v1/purchases/prices/evidences", json=payload_new)
    assert res_new.status_code == 201
    
    # 6. Como é PENDING, o preço ativo ainda deve ser R$ 40.00
    db.expire_all()
    ref_active_2 = db.query(PurchasePriceReference).filter(
        PurchasePriceReference.product_item_id == master["product"].id,
        PurchasePriceReference.supplier_id == master["supplier"].id,
        PurchasePriceReference.is_active == True
    ).first()
    assert float(ref_active_2.current_unit_price) == 40.00

    # 7. Verifica se a nova sugestão de reajuste calculou a variação corretamente: ((46 - 40) / 40) * 100 = 15%
    suggestion_new = db.query(PurchasePriceUpdateSuggestion).filter(
        PurchasePriceUpdateSuggestion.product_item_id == master["product"].id,
        PurchasePriceUpdateSuggestion.status == "PENDING"
    ).first()
    assert suggestion_new is not None
    assert float(suggestion_new.old_unit_price) == 40.00
    assert float(suggestion_new.new_unit_price) == 46.00
    assert float(suggestion_new.pct_variation) == 15.00
    assert suggestion_new.variation_direction == "INCREASE"

    # 8. Como a variação foi de 15% (acima do limite configurado de 10%), uma notificação para o MANAGER deve ter sido gerada.
    notif = db.query(Notification).filter(
        Notification.event_type == "purchase.price.suggestion.created",
        Notification.role_target == "MANAGER"
    ).order_by(Notification.created_at.desc()).first()
    assert notif is not None
    assert "variação" in notif.message.lower() or "reajuste" in notif.message.lower()

    # 9. Aprova a nova sugestão de aumento (R$ 46.00)
    login_admin(client)
    res_approve_new = client.post(
        f"/api/v1/purchases/prices/suggestions/{suggestion_new.id}/approve",
        json={"review_notes": "Aprovado aumento devido ao preço do aço."}
    )
    assert res_approve_new.status_code == 200

    # 10. Preço ativo de referência agora deve ser R$ 46.00, e o antigo deve estar inativo
    ref_new_active = db.query(PurchasePriceReference).filter(
        PurchasePriceReference.product_item_id == master["product"].id,
        PurchasePriceReference.supplier_id == master["supplier"].id,
        PurchasePriceReference.is_active == True
    ).first()
    assert ref_new_active is not None
    assert float(ref_new_active.current_unit_price) == 46.00

    ref_old_inactive = db.query(PurchasePriceReference).filter(
        PurchasePriceReference.product_item_id == master["product"].id,
        PurchasePriceReference.supplier_id == master["supplier"].id,
        PurchasePriceReference.is_active == False
    ).all()
    # Deve conter a referência antiga de R$ 40.00
    assert len(ref_old_inactive) >= 1
    assert any(float(r.current_unit_price) == 40.00 for r in ref_old_inactive)


def test_reject_price_suggestion_flow(client: TestClient, db: Session, setup_price_test_data):
    """Garante que a rejeição de uma sugestão não altera o preço de referência ativo, mas registra o motivo."""
    master = setup_price_test_data
    
    # 1. Cria preço inicial de referência (R$ 50.00) já aprovado para o teste
    admin_user = db.query(User).filter(User.username == "vesper_admin").first()
    ref_base = PurchasePriceReference(
        product_item_id=master["product"].id,
        supplier_id=master["supplier"].id,
        current_unit_price=50.00,
        currency="BRL",
        is_active=True,
        approved_by_user_id=admin_user.id,
        approved_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db.add(ref_base)
    db.commit()

    # 2. Lança evidência com valor muito alto (R$ 80.00, +60%)
    login_user(client)
    payload_high = {
        "source_type": "NF",
        "supplier_id": str(master["supplier"].id),
        "product_item_id": str(master["product"].id),
        "unit_price": 80.00,
        "quantity": 1.0,
        "total_amount": 80.00,
        "notes": "Cobrança indevida"
    }
    client.post("/api/v1/purchases/prices/evidences", json=payload_high)

    suggestion = db.query(PurchasePriceUpdateSuggestion).filter(
        PurchasePriceUpdateSuggestion.product_item_id == master["product"].id,
        PurchasePriceUpdateSuggestion.status == "PENDING"
    ).first()
    assert suggestion is not None
    assert float(suggestion.pct_variation) == 60.00

    # 3. Rejeita a sugestão de reajuste informando o motivo
    login_admin(client)
    res_reject = client.post(
        f"/api/v1/purchases/prices/suggestions/{suggestion.id}/reject",
        json={"review_notes": "Preço muito acima da média de mercado. Rejeitado."}
    )
    assert res_reject.status_code == 200
    assert res_reject.json()["status"] == "REJECTED"
    assert res_reject.json()["review_notes"] == "Preço muito acima da média de mercado. Rejeitado."

    # 4. Preço de referência ativo deve continuar sendo R$ 50.00
    ref_active = db.query(PurchasePriceReference).filter(
        PurchasePriceReference.product_item_id == master["product"].id,
        PurchasePriceReference.supplier_id == master["supplier"].id,
        PurchasePriceReference.is_active == True
    ).first()
    assert ref_active is not None
    assert float(ref_active.current_unit_price) == 50.00


def test_permission_gates_price_actions(client: TestClient, db: Session, setup_price_test_data):
    """Garante que usuários sem permissão (ou nível inadequado) sejam bloqueados de criar e aprovar sugestões."""
    master = setup_price_test_data
    
    # 1. Usuário comum (vesper_user) tenta aprovar ou rejeitar uma sugestão
    # Primeiro criamos a sugestão
    login_admin(client)
    payload = {
        "source_type": "MANUAL_ENTRY",
        "supplier_id": str(master["supplier"].id),
        "product_item_id": str(master["product"].id),
        "unit_price": 30.00,
        "notes": "Tentativa de reajuste"
    }
    client.post("/api/v1/purchases/prices/evidences", json=payload)
    
    suggestion = db.query(PurchasePriceUpdateSuggestion).filter(
        PurchasePriceUpdateSuggestion.product_item_id == master["product"].id,
        PurchasePriceUpdateSuggestion.status == "PENDING"
    ).first()
    assert suggestion is not None

    # Agora fazemos login com o usuário comum que possui nível NORMAL
    login_user(client)
    
    # Tenta aprovar
    res_approve = client.post(
        f"/api/v1/purchases/prices/suggestions/{suggestion.id}/approve",
        json={"review_notes": "Tentativa de aprovação por usuário sem permissão"}
    )
    assert res_approve.status_code == 403
    
    # Tenta rejeitar
    res_reject = client.post(
        f"/api/v1/purchases/prices/suggestions/{suggestion.id}/reject",
        json={"review_notes": "Tentativa de rejeição por usuário sem permissão"}
    )
    assert res_reject.status_code == 403

    # Tenta obter referências de preços e histórico (deve permitir leitura para NORMAL)
    res_refs = client.get("/api/v1/purchases/prices/references")
    assert res_refs.status_code == 200
    
    res_history = client.get("/api/v1/purchases/prices/history")
    assert res_history.status_code == 200


def test_price_evidence_blocks_future_sources_services_and_zero_price(client: TestClient, setup_price_test_data):
    """Garante que a PR manual nao prometa integraÃ§Ãµes futuras nem aceite preÃ§o invÃ¡lido."""
    login_admin(client)
    master = setup_price_test_data

    base_payload = {
        "source_type": "MANUAL_ENTRY",
        "supplier_id": str(master["supplier"].id),
        "product_item_id": str(master["product"].id),
        "unit_price": 10.00,
        "quantity": 1.0,
        "total_amount": 10.00,
    }

    imported_payload = {**base_payload, "source_type": "IMPORTED_XLSX"}
    res_imported = client.post("/api/v1/purchases/prices/evidences", json=imported_payload)
    assert res_imported.status_code == 400

    service_payload = {**base_payload, "service_id": str(uuid.uuid4())}
    res_service = client.post("/api/v1/purchases/prices/evidences", json=service_payload)
    assert res_service.status_code == 400

    zero_payload = {**base_payload, "unit_price": 0}
    res_zero = client.post("/api/v1/purchases/prices/evidences", json=zero_payload)
    assert res_zero.status_code == 400


def test_price_traceability_read_requires_purchases_access(client: TestClient, db: Session, setup_price_test_data):
    """Garante que usuÃ¡rio autenticado sem acesso ao mÃ³dulo nÃ£o consulta rastreabilidade de Compras."""
    purchases_module = db.query(Module).filter(Module.code == "purchases").first()
    user_common = db.query(User).filter(User.username == "vesper_user").first()
    assert purchases_module is not None
    assert user_common is not None

    db.query(UserModuleAccess).filter(
        UserModuleAccess.user_id == user_common.id,
        UserModuleAccess.module_id == purchases_module.id,
    ).delete()
    db.add(UserModuleAccess(
        user_id=user_common.id,
        module_id=purchases_module.id,
        permission_level="NO_ACCESS",
    ))
    db.commit()

    login_user(client)

    assert client.get("/api/v1/purchases/prices/references").status_code == 403
    assert client.get("/api/v1/purchases/prices/history").status_code == 403
    assert client.get("/api/v1/purchases/prices/suggestions").status_code == 403
    assert client.get(f"/api/v1/purchases/prices/items/{setup_price_test_data['product'].id}/timeline").status_code == 403


def test_products_prices_search_returns_family_with_variations(client: TestClient, db: Session, setup_price_test_data):
    """Busca por familia deve retornar a familia e variacoes compraveis sem misturar itens parecidos."""
    login_user(client)
    family = ProductFamily(name="CHAPA GALVANIZADA", description="Familia real de chapas galvanizadas")
    db.add(family)
    db.flush()
    item_a = ProductItem(
        id=uuid.uuid4(),
        sku="CH-GALV-316-3X12",
        name="Ch. Galv. 3/16 - 4,75 mm | 3 x 1,2 m | 136,8 kg/m",
        item_type="RAW_MATERIAL",
        unit_of_measure="un",
        family_id=family.id,
        attributes={"variation_name": "3/16 - 4,75 mm | 3 x 1,2 m | 136,8 kg/m", "medida": "3 x 1,2 m"},
        is_active=True,
    )
    item_b = ProductItem(
        id=uuid.uuid4(),
        sku="CH-GALV-316-6X12",
        name="Ch. Galv. 3/16 - 4,75 mm | 6 x 1,2 m | 273,6 kg/m",
        item_type="RAW_MATERIAL",
        unit_of_measure="un",
        family_id=family.id,
        attributes={"variation_name": "3/16 - 4,75 mm | 6 x 1,2 m | 273,6 kg/m", "medida": "6 x 1,2 m"},
        is_active=True,
    )
    db.add_all([item_a, item_b])
    db.commit()

    response = client.get("/api/v1/purchases/products-prices?search=chapa galvanizada")
    assert response.status_code == 200
    data = response.json()
    family_row = next(row for row in data["items"] if row["family_name"] == "CHAPA GALVANIZADA")
    variation_names = {row["variation_name"] for row in family_row["variations"]}
    assert "3/16 - 4,75 mm | 3 x 1,2 m | 136,8 kg/m" in variation_names
    assert "3/16 - 4,75 mm | 6 x 1,2 m | 273,6 kg/m" in variation_names


def test_update_product_variation_price_changes_only_selected_variation(client: TestClient, db: Session, setup_price_test_data):
    """Atualizar preco deve alterar somente a variacao escolhida e criar historico dela."""
    login_user(client)
    family = ProductFamily(name="CANTONEIRA", description="Familia real de cantoneiras")
    db.add(family)
    db.flush()
    item_a = ProductItem(
        id=uuid.uuid4(),
        sku="CANT-14-316",
        name='Cantoneira 1/4" x 3/16"',
        item_type="RAW_MATERIAL",
        unit_of_measure="barra",
        family_id=family.id,
        attributes={"variation_name": '1/4" x 3/16"'},
        is_active=True,
    )
    item_b = ProductItem(
        id=uuid.uuid4(),
        sku="CANT-34-18",
        name='Cantoneira 3/4" x 1/8"',
        item_type="RAW_MATERIAL",
        unit_of_measure="barra",
        family_id=family.id,
        attributes={"variation_name": '3/4" x 1/8"'},
        is_active=True,
    )
    db.add_all([item_a, item_b])
    db.flush()
    db.add(PurchasePriceReference(
        product_item_id=item_a.id,
        current_unit_price=10,
        currency="BRL",
        unit_of_measure="barra",
        approved_by_user_id=1,
        is_active=True,
    ))
    db.add(PurchasePriceReference(
        product_item_id=item_b.id,
        current_unit_price=20,
        currency="BRL",
        unit_of_measure="barra",
        approved_by_user_id=1,
        is_active=True,
    ))
    db.commit()

    response = client.post(
        f"/api/v1/purchases/products-prices/items/{item_a.id}/price",
        json={"new_price": 12.5, "document_number": "NF-TESTE", "notes": "Ajuste real"},
    )
    assert response.status_code == 200
    data = response.json()
    assert float(data["old_price"]) == 10.0
    assert float(data["new_price"]) == 12.5

    ref_a = db.query(PurchasePriceReference).filter(
        PurchasePriceReference.product_item_id == item_a.id,
        PurchasePriceReference.is_active == True,
    ).first()
    ref_b = db.query(PurchasePriceReference).filter(
        PurchasePriceReference.product_item_id == item_b.id,
        PurchasePriceReference.is_active == True,
    ).first()
    assert float(ref_a.current_unit_price) == 12.5
    assert float(ref_b.current_unit_price) == 20.0

    history_a = db.query(PurchasePriceHistory).filter(PurchasePriceHistory.product_item_id == item_a.id).all()
    history_b = db.query(PurchasePriceHistory).filter(PurchasePriceHistory.product_item_id == item_b.id).all()
    assert len(history_a) == 1
    assert history_a[0].source_id == "NF-TESTE"
    assert history_b == []


def test_product_variation_price_update_requires_purchases_write_access(client: TestClient, db: Session, setup_price_test_data):
    """Usuario sem permissao de escrita em Compras nao atualiza preco de variacao."""
    purchases_module = db.query(Module).filter(Module.code == "purchases").first()
    user_common = db.query(User).filter(User.username == "vesper_user").first()
    db.query(UserModuleAccess).filter(
        UserModuleAccess.user_id == user_common.id,
        UserModuleAccess.module_id == purchases_module.id,
    ).delete()
    db.add(UserModuleAccess(
        user_id=user_common.id,
        module_id=purchases_module.id,
        permission_level="READ_ONLY",
    ))
    db.commit()
    login_user(client)

    response = client.post(
        f"/api/v1/purchases/products-prices/items/{setup_price_test_data['product'].id}/price",
        json={"new_price": 99.9},
    )
    assert response.status_code == 403


def _create_compras_xlsx_fixture(path):
    wb = openpyxl.Workbook()
    ws_index = wb.active
    ws_index.title = "ÍNDICE "
    ws_index["A1"] = "Apoio de navegação"
    ws_empty = wb.create_sheet("Planilha1")
    ws = wb.create_sheet("Chapas")
    ws.append(["CÓDIGO", " Material / Descrição ", "Preço", "IPI", "Reajuste", "Valor Final", "Peso", "Fornecedor", "Atualizado em", "Empresa", "Contato", "Contato"])
    ws.append(["", "CHAPA GALVANIZADA", "", "", "", "", "", "", "", "", "Email", "Telefone"])
    ws.append(["", "Ch. Galv. 3/16", "", "", "", "", "136,8 kg/m", "", "", "CALINOX", "vendas@fornecedor-inox.example", "(21) 99999-0000"])
    ws.append(["CH-G-316", "Ch. Galv. 3/16 - 4,75 mm | 3 x 1,2 m", 100, 0, 0, 120, "136,8 kg/m", "CALINOX", "03/06/2026", "Calinox", "vendas@fornecedor-inox.example", "(21) 99999-0000"])
    ws.append(["CH-G-316-ALT", "", "", "", "", 121, "", "SERFER", "", "Serfer", "", ""])
    hel = wb.create_sheet("Hélice FM")
    hel.append(["Código", "Diâmetro Ø mm", "CV", "Polo", "Pás", "Vazão", "Pressão", "Pintura", "Preço", "IPI", "Reajuste", "Valor Final", "Fabricante", "Código do fabricante", "Contato", "Telefone"])
    hel.append(["HEL-500", "500", "1/2", "4", "6", "1000", "20", "Azul", 500, 0, 0, 550, "Fibrametal", "FM-500", "hel@fibra.com", "(11) 1111-2222"])
    wb.save(path)


def test_xlsx_reconciliation_reads_block_sheet_and_helice_layout(client: TestClient, db: Session, setup_price_test_data, tmp_path, monkeypatch):
    xlsx_path = tmp_path / "Compras Nova.xlsx"
    _create_compras_xlsx_fixture(xlsx_path)
    monkeypatch.setenv("PURCHASES_XLSX_PATH", str(xlsx_path))
    login_user(client)

    response = client.get("/api/v1/purchases/xlsx-reconciliation")
    assert response.status_code == 200
    data = response.json()
    assert "ÍNDICE " in data["sheets_ignored"]
    assert "Planilha1" in data["sheets_ignored"]
    assert data["layouts"]["metais_blocos"] == 1
    assert data["layouts"]["helices"] == 1
    assert data["summary"]["suppliers_found"] >= 1
    assert data["summary"]["suppliers_with_email"] >= 1
    assert data["summary"]["suppliers_with_phone"] >= 1
    assert data["summary"]["prices_using_final_value"] >= 2
    assert any(item["family"] == "CHAPA GALVANIZADA" for item in data["items"])
    assert any(item["family"] == "HÉLICE FIBRAMETAL" for item in data["items"])


def test_xlsx_reconciliation_compares_price_and_updates_only_selected_variation(client: TestClient, db: Session, setup_price_test_data, tmp_path, monkeypatch):
    xlsx_path = tmp_path / "Compras Nova.xlsx"
    _create_compras_xlsx_fixture(xlsx_path)
    monkeypatch.setenv("PURCHASES_XLSX_PATH", str(xlsx_path))
    login_user(client)

    family = ProductFamily(name="CHAPA GALVANIZADA")
    db.add(family)
    db.flush()
    supplier_person = Person(type="COMPANY", name="CALINOX", email="vendas@fornecedor-inox.example", is_active=True)
    db.add(supplier_person)
    db.flush()
    supplier = Supplier(person_id=supplier_person.id, supplier_code="CALINOX", preferred_contact_email="vendas@fornecedor-inox.example", status="ACTIVE")
    db.add(supplier)
    db.flush()
    item_a = ProductItem(
        sku="CH-G-316",
        name="Ch. Galv. 3/16 - 4,75 mm | 3 x 1,2 m",
        item_type="RAW_MATERIAL",
        unit_of_measure="chapa",
        category="Chapas",
        family_id=family.id,
        canonical_key="chapa galvanizada ch. galv. 3/16 - 4,75 mm | 3 x 1,2 m chapa",
        is_active=True,
    )
    item_b = ProductItem(
        sku="CH-G-316-6M",
        name="Ch. Galv. 3/16 - 4,75 mm | 6 x 1,2 m",
        item_type="RAW_MATERIAL",
        unit_of_measure="chapa",
        category="Chapas",
        family_id=family.id,
        is_active=True,
    )
    db.add_all([item_a, item_b])
    db.flush()
    ref_a = PurchasePriceReference(product_item_id=item_a.id, supplier_id=supplier.id, current_unit_price=100, currency="BRL", unit_of_measure="chapa", approved_by_user_id=1, is_active=True)
    ref_b = PurchasePriceReference(product_item_id=item_b.id, supplier_id=supplier.id, current_unit_price=300, currency="BRL", unit_of_measure="chapa", approved_by_user_id=1, is_active=True)
    db.add_all([ref_a, ref_b])
    db.commit()

    response = client.get("/api/v1/purchases/xlsx-reconciliation")
    assert response.status_code == 200
    data = response.json()
    row = next(item for item in data["items"] if "3 x 1,2 m" in item["variation"])
    assert row["spreadsheet_price"] == 100
    assert row["portal_price"] == 100

    update = client.post("/api/v1/purchases/xlsx-reconciliation/update-price", json={
        "row_key": row["row_key"],
        "product_item_id": row["portal_item_id"],
        "supplier_id": str(supplier.id),
        "spreadsheet_price": 100,
    })
    assert update.status_code == 200
    db.refresh(ref_b)
    still_b = db.query(PurchasePriceReference).filter(PurchasePriceReference.product_item_id == item_b.id, PurchasePriceReference.is_active == True).first()
    assert float(still_b.current_unit_price) == 300.0


def test_xlsx_reconciliation_requires_purchases_access(client: TestClient, db: Session, setup_price_test_data, tmp_path, monkeypatch):
    xlsx_path = tmp_path / "Compras Nova.xlsx"
    _create_compras_xlsx_fixture(xlsx_path)
    monkeypatch.setenv("PURCHASES_XLSX_PATH", str(xlsx_path))
    purchases_module = db.query(Module).filter(Module.code == "purchases").first()
    user_common = db.query(User).filter(User.username == "vesper_user").first()
    db.query(UserModuleAccess).filter(UserModuleAccess.user_id == user_common.id, UserModuleAccess.module_id == purchases_module.id).delete()
    db.add(UserModuleAccess(user_id=user_common.id, module_id=purchases_module.id, permission_level="NO_ACCESS"))
    db.commit()

    logout(client)
    login_user(client)
    response = client.get("/api/v1/purchases/xlsx-reconciliation")
    assert response.status_code == 403


def _create_smart_catalog_xlsx_fixture(path):
    wb = openpyxl.Workbook()
    wb.active.title = "ÍNDICE"
    wb.active["A1"] = "Apoio"
    ws = wb.create_sheet("Arame e Tela")
    ws.append(["CÓDIGO", "Material / Descrição", "Preço", "IPI", "Reajuste", "Valor Final", "Peso", "Fornecedor", "Atualizado em", "Empresa", "Contato Email", "Contato Telefone"])
    ws.append(["", "ARAME BTC", "", "", "", "", "", "", "", "", "", ""])
    ws.append(["AR-BTC-12", "Arame BTC 12", 10, 0, 0, 12, "1 kg/m", "TENAX", "01/06/2026", "Tenax", "vendas@tenax.com.br", "(11) 1111-1111"])
    ws.append(["AR-BTC-12", "Arame BTC 12", 11, 0, 0, 13, "1 kg/m", "CALINOX", "02/06/2026", "Calinox", "compras@fornecedor-inox.example", "(21) 2222-2222"])
    ws.append(["", "1 kg/m", "", "", "", "", "", "", "", "", "", ""])
    hel = wb.create_sheet("Hélice FM")
    hel.append(["Código", "Diâmetro Ø mm", "CV", "Polo", "Pás", "Vazão", "Pressão", "Pintura", "Preço", "IPI", "Reajuste", "Valor Final", "Fabricante", "Código do fabricante", "Contato Email", "Telefone"])
    hel.append(["HEL-200", "200", "0,25", "4", "4", "500", "10", "Natural", 200, 0, 0, 220, "Fibrametal", "FM-200", "hel@fibra.com.br", "(11) 3333-3333"])
    wb.save(path)


def test_smart_catalog_sync_groups_supplier_offers_without_creating_product_per_supplier(client: TestClient, db: Session, setup_price_test_data, tmp_path, monkeypatch):
    xlsx_path = tmp_path / "Compras Nova.xlsx"
    _create_smart_catalog_xlsx_fixture(xlsx_path)
    monkeypatch.setenv("PURCHASES_XLSX_PATH", str(xlsx_path))
    login_user(client)

    sync = client.post("/api/v1/purchases/catalog/sync-from-xlsx")
    assert sync.status_code == 200
    data = sync.json()
    assert data["summary"]["supplier_offers_count"] >= 3

    search = client.get("/api/v1/purchases/catalog/families?search=arame bct")
    assert search.status_code == 200
    families = search.json()["items"]
    assert any("ARAME" in row["family_name"] for row in families)

    family_id = next(row["family_id"] for row in families if "ARAME" in row["family_name"])
    variations = client.get(f"/api/v1/purchases/catalog/families/{family_id}/variations")
    assert variations.status_code == 200
    variation_rows = variations.json()["variations"]
    assert len(variation_rows) == 1
    item_id = variation_rows[0]["id"]

    offers = client.get(f"/api/v1/purchases/catalog/items/{item_id}/supplier-offers")
    assert offers.status_code == 200
    offer_rows = offers.json()["items"]
    assert {row["supplier_name"] for row in offer_rows} >= {"TENAX", "CALINOX"}

    product_count = db.query(ProductItem).filter(ProductItem.name.ilike("%Arame BTC 12%")).count()
    assert product_count == 1
    offer_count = db.query(PurchaseSupplierPriceOffer).filter(PurchaseSupplierPriceOffer.product_item_id == uuid.UUID(item_id)).count()
    assert offer_count == 2


def test_smart_catalog_offer_update_changes_only_selected_supplier_and_company_price(client: TestClient, db: Session, setup_price_test_data, tmp_path, monkeypatch):
    xlsx_path = tmp_path / "Compras Nova.xlsx"
    _create_smart_catalog_xlsx_fixture(xlsx_path)
    monkeypatch.setenv("PURCHASES_XLSX_PATH", str(xlsx_path))
    login_user(client)
    client.post("/api/v1/purchases/catalog/sync-from-xlsx")

    family_response = client.get("/api/v1/purchases/catalog/families?search=arame btc")
    family_id = family_response.json()["items"][0]["family_id"]
    item_id = client.get(f"/api/v1/purchases/catalog/families/{family_id}/variations").json()["variations"][0]["id"]
    offers = client.get(f"/api/v1/purchases/catalog/items/{item_id}/supplier-offers").json()["items"]
    tenax_offer = next(row for row in offers if row["supplier_name"] == "TENAX")
    calinox_offer = next(row for row in offers if row["supplier_name"] == "CALINOX")

    response = client.post(
        f"/api/v1/purchases/catalog/items/{item_id}/supplier-offers/{tenax_offer['id']}/update-price",
        json={"new_price": 15.5, "notes": "Resposta atualizada do fornecedor"},
    )
    assert response.status_code == 200
    assert float(response.json()["new_price"]) == 15.5

    item_uuid = uuid.UUID(item_id)
    tenax_uuid = uuid.UUID(tenax_offer["supplier_id"])
    calinox_uuid = uuid.UUID(calinox_offer["supplier_id"])
    tenax_ref = db.query(PurchasePriceReference).filter(
        PurchasePriceReference.product_item_id == item_uuid,
        PurchasePriceReference.supplier_id == tenax_uuid,
        PurchasePriceReference.is_active == True,
    ).first()
    company_ref = db.query(PurchasePriceReference).filter(
        PurchasePriceReference.product_item_id == item_uuid,
        PurchasePriceReference.supplier_id == None,
        PurchasePriceReference.is_active == True,
    ).first()
    calinox_ref = db.query(PurchasePriceReference).filter(
        PurchasePriceReference.product_item_id == item_uuid,
        PurchasePriceReference.supplier_id == calinox_uuid,
        PurchasePriceReference.is_active == True,
    ).first()
    assert float(tenax_ref.current_unit_price) == 15.5
    assert float(company_ref.current_unit_price) == 15.5
    assert float(calinox_ref.current_unit_price) == 11.0
    assert db.query(PurchasePriceHistory).filter(PurchasePriceHistory.product_item_id == item_uuid).count() >= 2
