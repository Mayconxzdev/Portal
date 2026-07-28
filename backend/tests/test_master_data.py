import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.master_data import Person, Customer, Supplier, ProductItem, Service
from app.models.event_log import EventLog

# Helpers de autenticação
def login_admin(client: TestClient):
    client.post("/api/v1/auth/login", json={"username": "vesper_admin", "password": "admin"})

def login_user(client: TestClient):
    client.post("/api/v1/auth/login", json={"username": "vesper_user", "password": "userpass"})

def logout(client: TestClient):
    client.cookies.clear()


def test_create_person_individual_and_company(client: TestClient, db: Session):
    login_admin(client)
    
    # Criação de Pessoa Física
    pf_payload = {
        "type": "INDIVIDUAL",
        "name": "Maria Silva",
        "legal_name": "Maria Silva Ltda",
        "document_type": "CPF",
        "document_number": "123.456.789-00",
        "email": "maria@silva.com",
        "phone": "(11) 99999-9999",
        "notes": "Cliente pf teste",
        "is_active": True,
        "addresses": [
            {
                "type": "MAIN",
                "street": "Rua das Flores",
                "number": "123",
                "complement": "Apt 12",
                "district": "Centro",
                "city": "São Paulo",
                "state": "SP",
                "zip_code": "01001-000",
                "country": "Brasil"
            }
        ],
        "contacts": [
            {
                "name": "João",
                "role": "Parceiro",
                "email": "joao@silva.com",
                "phone": "(11) 98888-8888",
                "is_primary": True
            }
        ]
    }
    
    response = client.post("/api/v1/master-data/people", json=pf_payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Maria Silva"
    assert data["document_number"] == "12345678900"  # Normalizado!
    assert data["email"] == "maria@silva.com"
    assert len(data["addresses"]) == 1
    assert len(data["contacts"]) == 1
    
    # Criação de Pessoa Jurídica
    pj_payload = {
        "type": "COMPANY",
        "name": "Vesper Corp",
        "legal_name": "Vesper Empreendimentos S.A.",
        "document_type": "CNPJ",
        "document_number": "12.345.678/0001-99",
        "email": "CONTATO@portal.example",  # Lowercase test
        "phone": "(11) 3333-3333",
        "is_active": True,
        "addresses": [],
        "contacts": []
    }
    
    response2 = client.post("/api/v1/master-data/people", json=pj_payload)
    assert response2.status_code == 201
    data2 = response2.json()
    assert data2["name"] == "Vesper Corp"
    assert data2["document_number"] == "12345678000199"  # Normalizado!
    assert data2["email"] == "contato@portal.example"  # Normalizado para lower!


def test_create_person_duplicate_document(client: TestClient, db: Session):
    login_admin(client)
    
    payload = {
        "type": "INDIVIDUAL",
        "name": "Pedro Santos",
        "document_type": "CPF",
        "document_number": "111.222.333-44",
        "email": "pedro@santos.com",
        "addresses": [],
        "contacts": []
    }
    
    response = client.post("/api/v1/master-data/people", json=payload)
    assert response.status_code == 201
    
    # Tenta cadastrar o mesmo CPF (com pontuação diferente)
    payload_dup = {
        "type": "INDIVIDUAL",
        "name": "Pedro Santos Duplicado",
        "document_type": "CPF",
        "document_number": "11122233344",  # Sem pontuação
        "email": "pedro2@santos.com",
        "addresses": [],
        "contacts": []
    }
    
    response_dup = client.post("/api/v1/master-data/people", json=payload_dup)
    assert response_dup.status_code == 409
    assert "documento informado" in response_dup.json()["detail"]


def test_customer_creation_and_unicity(client: TestClient, db: Session):
    login_admin(client)
    
    # 1. Cria a Pessoa
    p_response = client.post("/api/v1/master-data/people", json={
        "type": "INDIVIDUAL",
        "name": "Renato Santos",
        "document_number": "99988877766",
        "addresses": [],
        "contacts": []
    })
    person_id = p_response.json()["id"]
    
    # 2. Cria o Cliente
    c_response = client.post("/api/v1/master-data/customers", json={
        "person_id": person_id,
        "customer_code": "CLI-Renato",
        "status": "ACTIVE",
        "default_payment_terms": "30 dias"
    })
    assert c_response.status_code == 201
    assert c_response.json()["customer_code"] == "CLI-Renato"
    assert c_response.json()["person"]["name"] == "Renato Santos"
    
    # 3. Tenta criar outro cliente para a mesma pessoa
    c_response_dup = client.post("/api/v1/master-data/customers", json={
        "person_id": person_id,
        "customer_code": "CLI-Renato-2"
    })
    assert c_response_dup.status_code == 409
    assert "papel de cliente cadastrado" in c_response_dup.json()["detail"]


def test_supplier_creation_and_unicity(client: TestClient, db: Session):
    login_admin(client)
    
    # 1. Cria a Pessoa
    p_response = client.post("/api/v1/master-data/people", json={
        "type": "COMPANY",
        "name": "Madeira S.A.",
        "document_number": "88777666000155",
        "addresses": [],
        "contacts": []
    })
    person_id = p_response.json()["id"]
    
    # 2. Cria o Fornecedor
    s_response = client.post("/api/v1/master-data/suppliers", json={
        "person_id": person_id,
        "supplier_code": "FOR-Madeira",
        "categories": ["Insumos", "Madeiras"],
        "preferred_contact_email": "vendas@madeira.com",
        "rating": 4.5
    })
    assert s_response.status_code == 201
    assert s_response.json()["supplier_code"] == "FOR-Madeira"
    assert "Madeiras" in s_response.json()["person"]["supplier"]["categories"]
    
    # 3. Tenta criar outro fornecedor para a mesma pessoa
    s_response_dup = client.post("/api/v1/master-data/suppliers", json={
        "person_id": person_id,
        "supplier_code": "FOR-Madeira-2"
    })
    assert s_response_dup.status_code == 409
    assert "papel de fornecedor cadastrado" in s_response_dup.json()["detail"]


def test_product_item_creation_and_unicity(client: TestClient, db: Session):
    login_admin(client)
    
    payload = {
        "sku": "PARAFUSO-A32",
        "name": "Parafuso Aço 3/2 polegadas",
        "item_type": "RAW_MATERIAL",
        "unit_of_measure": "un",
        "category": "Ferragens",
        "ncm": "73181500",
        "barcode": "7891234567890"
    }
    
    response = client.post("/api/v1/master-data/items", json=payload)
    assert response.status_code == 201
    assert response.json()["sku"] == "PARAFUSO-A32"
    
    # Tenta criar SKU duplicado
    response_dup = client.post("/api/v1/master-data/items", json={
        "sku": "PARAFUSO-A32",
        "name": "Outro Parafuso",
        "item_type": "CONSUMABLE"
    })
    assert response_dup.status_code == 409
    assert "SKU" in response_dup.json()["detail"]


def test_service_creation_and_unicity(client: TestClient, db: Session):
    login_admin(client)
    
    payload = {
        "code": "MANUTENCAO-PREV",
        "name": "Serviço de Manutenção Preventiva",
        "category": "TI",
        "default_price": 150.00
    }
    
    response = client.post("/api/v1/master-data/services", json=payload)
    assert response.status_code == 201
    assert response.json()["code"] == "MANUTENCAO-PREV"
    
    # Tenta criar Código duplicado
    response_dup = client.post("/api/v1/master-data/services", json={
        "code": "MANUTENCAO-PREV",
        "name": "Outra Manutenção"
    })
    assert response_dup.status_code == 409
    assert "codigo" in response_dup.json()["detail"]


def test_permissions_gate_master_data(client: TestClient, db: Session):
    # Teste de usuário anônimo
    logout(client)
    res_anon = client.post("/api/v1/master-data/people", json={
        "type": "INDIVIDUAL", "name": "Anonimo", "addresses": [], "contacts": []
    })
    assert res_anon.status_code == 401
    
    # Teste de usuário sem permissão (vesper_user com role USER)
    login_user(client)
    res_user = client.post("/api/v1/master-data/people", json={
        "type": "INDIVIDUAL", "name": "User Comum", "addresses": [], "contacts": []
    })
    assert res_user.status_code == 403
    
    # Usuário comum deve conseguir ler a listagem
    res_list = client.get("/api/v1/master-data/people")
    assert res_list.status_code == 200
    assert isinstance(res_list.json(), list)


def test_events_emission_master_data(client: TestClient, db: Session):
    login_admin(client)
    
    # Cria uma pessoa para disparar o evento
    p_response = client.post("/api/v1/master-data/people", json={
        "type": "INDIVIDUAL",
        "name": "Carlos Evento",
        "document_number": "55566677788",
        "addresses": [],
        "contacts": []
    })
    person_id = p_response.json()["id"]
    
    # Verifica no banco de dados se o evento foi gravado na tabela event_logs
    event = db.query(EventLog).filter(EventLog.event_type == "master_data.person.created").first()
    assert event is not None
    assert event.payload["id"] == person_id
    assert "Carlos Evento" in event.payload["name"]
