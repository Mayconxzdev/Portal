import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.legacy_import import LegacyImportBatch, LegacyImportRow, LegacyDuplicateCandidate, LegacyImportDecision
from app.models.master_data import Person, ProductItem
from app.models.event_log import EventLog
from app.models.notification import Notification

# Helpers de autenticação
def login_admin(client: TestClient):
    client.post("/api/v1/auth/login", json={"username": "vesper_admin", "password": "admin"})

def login_user(client: TestClient):
    client.post("/api/v1/auth/login", json={"username": "vesper_user", "password": "userpass"})

def logout(client: TestClient):
    client.cookies.clear()


def test_permissions_gate_legacy_import(client: TestClient):
    # Teste de usuário anônimo
    logout(client)
    res_anon = client.get("/api/v1/legacy-import/batches")
    assert res_anon.status_code == 401
    
    # Teste de usuário comum (bloqueado, recurso restrito a ADMIN/MANAGER)
    login_user(client)
    res_user = client.get("/api/v1/legacy-import/batches")
    assert res_user.status_code == 403
    
    # Usuário admin com acesso
    login_admin(client)
    res_admin = client.get("/api/v1/legacy-import/batches")
    assert res_admin.status_code == 200
    assert isinstance(res_admin.json(), list)


def test_create_import_batch(client: TestClient, db: Session):
    login_admin(client)
    
    payload = {
        "source_app": "COMPRASAPP2",
        "source_name": "Planilha de Compras Nova",
        "source_path_masked": "K:\\--- Apps\\ComprasApp2\\Compras Nova .xlsx",
        "module_target": "purchases",
        "notes": "Importacao de teste"
    }
    
    response = client.post("/api/v1/legacy-import/batches", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["source_app"] == "COMPRASAPP2"
    assert data["status"] == "DISCOVERED"
    assert "id" in data
    
    # Verifica emissao do evento
    event = db.query(EventLog).filter(EventLog.event_type == "legacy.import.batch.created").first()
    assert event is not None
    assert event.payload["batch_id"] == data["id"]


def test_upload_rows_sanitization_and_normalization(client: TestClient, db: Session):
    login_admin(client)
    
    # Cria o lote
    b_res = client.post("/api/v1/legacy-import/batches", json={
        "source_app": "HELPDESK",
        "source_name": "Base de TI",
        "source_path_masked": "K:\\--- Apps\\Helpdesk\\Helpdesk.db",
        "module_target": "it"
    })
    batch_id = b_res.json()["id"]

    # Envia linhas contendo dados sensiveis, caminhos e precos desalinhados
    rows_payload = {
        "rows": [
            {
                "source_table_or_sheet": "Configuracoes",
                "source_row_id": "cred_1",
                "entity_target": "CREDENTIAL_METADATA",
                "raw_data_json": {
                    "name": "Servidor SMTP",
                    "username": "smtp_usr",
                    "password": "senha_super_secreta_123", # Chave sensivel
                    "token": "token_secreto_abc", # Outra chave sensivel
                    "local_path": "K:\\--- Apps\\Helpdesk\\config\\smtp.json" # Caminho a mascarar
                },
                "confidence_score": 1.0
            },
            {
                "source_table_or_sheet": "Itens Antigos",
                "source_row_id": "item_1",
                "entity_target": "PRODUCT_ITEM",
                "raw_data_json": {
                    "sku": "chapa-inox-304", # Para normalizar para maiusculas
                    "name": "Chapa Inox",
                    "preco": "R$ 1.250,50" # Para normalizar para float
                },
                "confidence_score": 0.8
            }
        ]
    }

    response = client.post(f"/api/v1/legacy-import/batches/{batch_id}/rows", json=rows_payload)
    assert response.status_code == 201
    rows_data = response.json()
    assert len(rows_data) == 2
    
    # 1. Verifica Sanitização de segredos e caminhos no primeiro registro
    r1 = rows_data[0]
    assert r1["raw_data_json"]["password"] == "******"
    assert r1["raw_data_json"]["token"] == "******"
    assert r1["raw_data_json"]["local_path"] == "K:\\...\\smtp.json"
    
    # 2. Verifica Normalização de SKUs e Preços no segundo registro
    r2 = rows_data[1]
    assert r2["normalized_data_json"]["sku"] == "CHAPA-INOX-304"
    assert r2["normalized_data_json"]["preco"] == 1250.50


def test_duplicate_detection_against_master_data(client: TestClient, db: Session):
    login_admin(client)
    
    # 1. Cadastra Pessoa e Produto oficiais no Master Data para colidir
    p_official = Person(
        type="COMPANY",
        name="Distribuidora Vesper Ferramentas",
        document_number="98765432000100",
        email="compras@fornecedor-ferramentas.example",
        is_active=True
    )
    db.add(p_official)
    
    prod_official = ProductItem(
        sku="PERFIL-ACO-1020-U",
        name="Perfil Aco U",
        item_type="RAW_MATERIAL",
        is_active=True
    )
    db.add(prod_official)
    db.commit()

    # 2. Cria o Batch de staging
    b_res = client.post("/api/v1/legacy-import/batches", json={
        "source_app": "COMPRASAPP2",
        "source_name": "Planilha",
        "source_path_masked": "Planilha.xlsx",
        "module_target": "purchases"
    })
    batch_id = b_res.json()["id"]

    # 3. Envia linha com o mesmo CNPJ do fornecedor e SKU do produto
    rows_payload = {
        "rows": [
            {
                "source_row_id": "sup_dup",
                "entity_target": "SUPPLIER",
                "raw_data_json": {
                    "name": "Distribuidora Vesper Ferramentas Legada",
                    "cnpj": "98.765.432/0001-00" # Mesmo CNPJ
                }
            },
            {
                "source_row_id": "item_dup",
                "entity_target": "PRODUCT_ITEM",
                "raw_data_json": {
                    "sku": "PERFIL-ACO-1020-U" # Mesmo SKU
                }
            }
        ]
    }

    response = client.post(f"/api/v1/legacy-import/batches/{batch_id}/rows", json=rows_payload)
    assert response.status_code == 201
    rows_data = response.json()
    
    # Ambos devem ser detectados como duplicados
    assert rows_data[0]["status"] == "DUPLICATE_CANDIDATE"
    assert rows_data[0]["detected_duplicates_json"]["candidates"][0]["match_type"] == "DOCUMENT"
    assert rows_data[0]["detected_duplicates_json"]["candidates"][0]["score"] == 1.0

    assert rows_data[1]["status"] == "DUPLICATE_CANDIDATE"
    assert rows_data[1]["detected_duplicates_json"]["candidates"][0]["match_type"] == "SKU"
    
    # Verifica se os registros candidatos foram persistidos
    cands = db.query(LegacyDuplicateCandidate).all()
    assert len(cands) >= 2


def test_record_revision_decision(client: TestClient, db: Session):
    login_admin(client)
    
    # 1. Cria batch e row
    b_res = client.post("/api/v1/legacy-import/batches", json={
        "source_app": "COMPRASAPP2", "source_name": "Planilha", "source_path_masked": "P.xlsx", "module_target": "purchases"
    })
    batch_id = b_res.json()["id"]

    r_res = client.post(f"/api/v1/legacy-import/batches/{batch_id}/rows", json={
        "rows": [
            {
                "source_row_id": "item_123",
                "entity_target": "PRODUCT_ITEM",
                "raw_data_json": {"sku": "SKU-NOVO", "name": "Item Inedito"}
            }
        ]
    })
    row_id = r_res.json()[0]["id"]

    # 2. Grava decisao ACCEPT
    dec_res = client.post(f"/api/v1/legacy-import/rows/{row_id}/decision", json={
        "decision": "ACCEPT",
        "reason": "Cadastro limpo e homologado."
    })
    assert dec_res.status_code == 201
    assert dec_res.json()["decision"] == "ACCEPT"
    
    # 3. Verifica se a linha mudou o status para READY
    row = db.query(LegacyImportRow).filter(LegacyImportRow.id == uuid.UUID(row_id)).first()
    assert row.status == "READY"
    
    # 4. Verifica que NAO criou dados na tabela oficial de produtos (sem promocao automatica)
    item_official = db.query(ProductItem).filter(ProductItem.sku == "SKU-NOVO").first()
    assert item_official is None


def test_notifications_generation(client: TestClient, db: Session):
    login_admin(client)
    
    # Dispara criacao de batch e linhas que devem gerar notificacoes
    # (ready_for_review e duplicate.detected)
    b_res = client.post("/api/v1/legacy-import/batches", json={
        "source_app": "COMPRASAPP2", "source_name": "Lote Notif", "source_path_masked": "L.xlsx", "module_target": "purchases"
    })
    batch_id = b_res.json()["id"]

    # Insere linhas
    client.post(f"/api/v1/legacy-import/batches/{batch_id}/rows", json={
        "rows": [
            {
                "source_row_id": "row_1",
                "entity_target": "PRODUCT_ITEM",
                "raw_data_json": {"sku": "SKU-NOTIF", "name": "Item"}
            }
        ]
    })

    # Notificacao de lote pronto para revisao gerada para gerentes
    notif = db.query(Notification).filter(
        Notification.event_type == "legacy.import.ready_for_review"
    ).first()
    assert notif is not None
    assert "Lote de importacao pronto para revisao" in notif.title
    assert "Lote Notif" in notif.message
