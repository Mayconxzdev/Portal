import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.purchase import PurchaseRequest

def login_admin(client: TestClient):
    client.post("/api/v1/auth/login", json={"username": "vesper_admin", "password": "admin"})

def login_user(client: TestClient):
    client.post("/api/v1/auth/login", json={"username": "vesper_user", "password": "userpass"})

def logout(client: TestClient):
    client.cookies.clear()


def test_purge_test_data_permissions_and_cascade(client: TestClient, db: Session):
    # 1. Usuário comum não pode acessar o preview/purge (HTTP 403)
    login_user(client)
    
    resp_prev = client.post("/api/v1/purchases/admin/test-data/preview")
    assert resp_prev.status_code == 403
    
    resp_purge = client.post("/api/v1/purchases/admin/test-data/purge")
    assert resp_purge.status_code == 403
    
    logout(client)
    
    # 2. Insere dados de teste e dados reais no banco para simular o cenário
    # Criamos uma requisição de teste 'segura'
    req_test_safe = PurchaseRequest(
        title="Compra de teste [TEST]",
        description="Esta é uma compra de teste para limpar.",
        requester_user_id=1,
        status="DRAFT"
    )
    
    # Criamos uma requisição de teste 'bloqueada' (status APPROVED)
    req_test_locked = PurchaseRequest(
        title="Compra de teste aprovada [TEST]",
        description="Esta é de teste mas já foi aprovada e não pode sumir.",
        requester_user_id=1,
        status="APPROVED"
    )
    
    # Criamos uma requisição real legítima (não deve ser afetada)
    req_real = PurchaseRequest(
        title="Compra de monitores real para TI",
        description="Não apague isso.",
        requester_user_id=1,
        status="DRAFT"
    )
    
    db.add_all([req_test_safe, req_test_locked, req_real])
    db.commit()
    
    # Guarda os IDs
    safe_id = req_test_safe.id
    locked_id = req_test_locked.id
    real_id = req_real.id
    
    # 3. Testa como Administrador
    login_admin(client)
    
    # Preview
    resp_prev = client.post("/api/v1/purchases/admin/test-data/preview")
    assert resp_prev.status_code == 200
    prev_data = resp_prev.json()
    
    assert prev_data["summary"]["safe_to_delete_count"] >= 1
    assert prev_data["summary"]["locked_count"] >= 1
    
    # Verifica que o safe está no safe_requests e locked no locked_requests
    safe_list = [r["id"] for r in prev_data["safe_requests"]]
    locked_list = [r["id"] for r in prev_data["locked_requests"]]
    
    assert str(safe_id) in safe_list
    assert str(locked_id) in locked_list
    assert str(real_id) not in safe_list
    assert str(real_id) not in locked_list
    
    # Purge
    resp_purge = client.post("/api/v1/purchases/admin/test-data/purge")
    assert resp_purge.status_code == 200
    purge_data = resp_purge.json()
    
    assert purge_data["purged_requests_count"] >= 1
    
    # 4. Verifica no banco o resultado físico
    db.expire_all()
    
    # O safe deve ter sido apagado fisicamente
    assert db.query(PurchaseRequest).filter(PurchaseRequest.id == safe_id).first() is None
    # O locked e o real devem continuar no banco
    assert db.query(PurchaseRequest).filter(PurchaseRequest.id == locked_id).first() is not None
    assert db.query(PurchaseRequest).filter(PurchaseRequest.id == real_id).first() is not None
    
    # Limpeza final dos registros criados pelo teste
    r_locked = db.query(PurchaseRequest).filter(PurchaseRequest.id == locked_id).first()
    r_real = db.query(PurchaseRequest).filter(PurchaseRequest.id == real_id).first()
    if r_locked:
        db.delete(r_locked)
    if r_real:
        db.delete(r_real)
    db.commit()
