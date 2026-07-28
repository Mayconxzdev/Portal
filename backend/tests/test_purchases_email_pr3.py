import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.master_data import Person, Supplier
from app.models.purchase import PurchaseEmailMessage


def login_admin(client: TestClient) -> None:
    client.post("/api/v1/auth/login", json={"username": "vesper_admin", "password": "admin"})


@pytest.fixture
def supplier_for_email(db: Session):
    person = Person(
        id=uuid.uuid4(),
        type="COMPANY",
        name="FAM Componentes",
        document_type="CNPJ",
        document_number="33333333000133",
        email="cotacao@fornecedor-alfa.example",
        is_active=True,
    )
    db.add(person)
    db.flush()
    supplier = Supplier(
        id=uuid.uuid4(),
        person_id=person.id,
        supplier_code="FAM",
        preferred_contact_email="cotacao@fornecedor-alfa.example",
        status="ACTIVE",
    )
    db.add(supplier)
    db.commit()
    return supplier


def _prepare_quote_with_supplier(client: TestClient, supplier: Supplier) -> tuple[str, str]:
    quote_res = client.post("/api/v1/purchases/quotes", json={
        "title": "Cotacao de teste PR3",
        "description": "Fluxo de e-mail persistido",
        "origin_type": "manual",
    })
    assert quote_res.status_code == 201
    quote_id = quote_res.json()["id"]

    item_res = client.post(f"/api/v1/purchases/quotes/{quote_id}/items", json={
        "free_text_description": "Parafuso Allen inox 1/4",
        "quantity": 5,
        "unit_of_measure": "un",
        "specifications": "Inox, cabeca cilindrica",
        "source_type": "manual",
        "source_confidence": "high",
        "match_status": "confirmed",
    })
    assert item_res.status_code == 201
    item_id = item_res.json()["id"]

    selection_res = client.post(f"/api/v1/purchases/quotes/{quote_id}/supplier-selection", json={
        "suppliers": [{
            "supplier_id": str(supplier.id),
            "item_ids": [item_id],
        }],
    })
    assert selection_res.status_code == 200
    return quote_id, item_id


def test_pr3_sender_accounts_are_safe_and_seeded(client: TestClient):
    login_admin(client)

    res = client.get("/api/v1/purchases/sender-accounts")

    assert res.status_code == 200
    accounts = res.json()
    assert {account["email"] for account in accounts} == {
        "compras@portal.example",
        "compras@empresa-parceira.example",
    }
    assert all(account["bcc_default_enabled"] is True for account in accounts)
    assert all(account["has_secret"] is False for account in accounts)
    assert all(account["is_configured"] is False for account in accounts)
    assert all("secret_ref" not in account for account in accounts)
    assert all(account["secret_ref_masked"].startswith("vault://") for account in accounts)


def test_pr3_email_message_persistence_edit_bcc_and_fake_send(
    client: TestClient,
    db: Session,
    supplier_for_email: Supplier,
):
    login_admin(client)
    quote_id, _ = _prepare_quote_with_supplier(client, supplier_for_email)

    preview_res = client.get(f"/api/v1/purchases/quotes/{quote_id}/email-previews")
    assert preview_res.status_code == 200
    previews = preview_res.json()
    assert len(previews) == 1
    preview = previews[0]

    assert preview["message_id"]
    assert preview["sender_email"] == "compras@portal.example"
    assert preview["account_status"] == "not_configured"
    assert preview["bcc_enabled"] is True
    assert preview["bcc"] == "compras@portal.example"
    assert preview["bcc_source"] == "account_default"
    assert preview["idempotency_key"]
    assert "Cotação" in preview["subject"]
    assert "PR3" not in preview["subject"]
    assert "Parafuso Allen" in preview["body_html"]
    assert "Compras Vesper" in preview["signature_html"]
    assert "preco anterior" not in preview["body_html"].lower()
    assert db.query(PurchaseEmailMessage).count() == 1

    message_id = preview["message_id"]
    original_hash = preview["content_hash"]
    bcc_res = client.patch(f"/api/v1/purchases/email-messages/{message_id}", json={
        "bcc_enabled": False,
    })
    assert bcc_res.status_code == 200
    bcc_data = bcc_res.json()
    assert bcc_data["bcc_enabled"] is False
    assert bcc_data["bcc"] is None
    assert bcc_data["bcc_source"] == "user_override"

    edited_res = client.patch(f"/api/v1/purchases/email-messages/{message_id}", json={
        "body_html": "<p>Ola FAM Componentes,</p><p>Mensagem ajustada.</p>",
    })
    assert edited_res.status_code == 200
    edited = edited_res.json()
    assert edited["content_hash"] != original_hash
    assert "Mensagem ajustada" in edited["body_html"]

    send_res = client.post(f"/api/v1/purchases/email-messages/{edited['message_id']}/send")
    assert send_res.status_code == 200
    sent = send_res.json()
    assert sent["duplicate_blocked"] is False
    assert sent["message"]["status"] == "sent"
    assert sent["message"]["provider_message_id"].startswith("fake-")
    assert "Nenhum e-mail real foi enviado" in sent["human_message"]

    duplicate_res = client.post(f"/api/v1/purchases/email-messages/{edited['message_id']}/send")
    assert duplicate_res.status_code == 200
    duplicate = duplicate_res.json()
    assert duplicate["duplicate_blocked"] is True
    assert "bloqueou um envio duplicado" in duplicate["human_message"]
