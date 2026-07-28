import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.master_data import Person, Supplier
from app.models.purchase import (
    PurchaseEmailAttachment,
    PurchaseEmailInboundMessage,
    PurchaseEmailMessage,
    PurchaseMonitoringEvent,
    PurchaseResponseCandidate,
    PurchaseRFQSupplier,
)


def login_admin(client: TestClient) -> None:
    client.post("/api/v1/auth/login", json={"username": "vesper_admin", "password": "admin"})


@pytest.fixture
def supplier_for_monitoring(db: Session):
    person = Person(
        id=uuid.uuid4(),
        type="COMPANY",
        name="FAM Componentes",
        document_type="CNPJ",
        document_number="44444444000144",
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


def _prepare_sent_quote(client: TestClient, supplier: Supplier) -> tuple[str, str, str]:
    quote_res = client.post("/api/v1/purchases/quotes", json={
        "title": "Cotacao monitorada",
        "description": "Resposta recebida por callback",
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

    preview_res = client.get(f"/api/v1/purchases/quotes/{quote_id}/email-previews")
    assert preview_res.status_code == 200
    message_id = preview_res.json()[0]["message_id"]

    send_res = client.post(f"/api/v1/purchases/email-messages/{message_id}/send")
    assert send_res.status_code == 200
    outbound = send_res.json()["message"]
    assert outbound["status"] == "sent"

    return quote_id, message_id, outbound["subject"]


def _signed_headers(raw: bytes, webhook_id: str, *, account: str = "compras@portal.example", timestamp: str | None = None) -> dict[str, str]:
    timestamp = timestamp or datetime.now(timezone.utc).isoformat()
    signature = hmac.new(
        (settings.N8N_WEBHOOK_SECRET or "vesper_n8n_local_secret").encode("utf-8"),
        raw + timestamp.encode("utf-8") + webhook_id.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return {
        "X-Vesper-Webhook-Id": webhook_id,
        "X-Vesper-Timestamp": timestamp,
        "X-Vesper-Signature": signature,
        "X-Vesper-Source": "n8n-imap",
        "X-Vesper-Account": account,
        "Content-Type": "application/json",
    }


def _raw_payload(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _callback_payload(*, imap_uid: str, in_reply_to: str | None = None, subject: str = "Resposta de cotacao") -> dict:
    return {
        "account_email": "compras@portal.example",
        "folder": "INBOX",
        "imap_uid": imap_uid,
        "message_id": f"<reply-{imap_uid}@fornecedor-alfa.example>",
        "in_reply_to": in_reply_to,
        "references": [in_reply_to] if in_reply_to else [],
        "from_email": "cotacao@fornecedor-alfa.example",
        "from_name": "FAM Componentes",
        "to": ["compras@portal.example"],
        "cc": [],
        "subject": subject,
        "received_at": datetime.now(timezone.utc).isoformat(),
        "body_text": "Segue cotacao: Parafuso Allen inox 1/4 por R$ 2,50, prazo 3 dias.",
        "body_html": "<p>Segue cotacao.</p><script>alert('x')</script>",
        "attachments": [{
            "filename": "cotacao.exe",
            "content_type": "application/x-msdownload",
            "size_bytes": 120,
            "sha256": hashlib.sha256(b"unsafe").hexdigest(),
            "storage_key": "sandbox/cotacao.exe",
        }],
        "raw_headers": {"Message-ID": f"<reply-{imap_uid}@fornecedor-alfa.example>"},
    }


def test_pr4_monitoring_callback_links_response_and_blocks_unsafe_attachment(
    client: TestClient,
    db: Session,
    supplier_for_monitoring: Supplier,
):
    login_admin(client)
    quote_id, _, _ = _prepare_sent_quote(client, supplier_for_monitoring)
    outbound_message = db.query(PurchaseEmailMessage).filter(PurchaseEmailMessage.quote_id == uuid.UUID(quote_id)).first()
    assert outbound_message.message_id

    payload = _callback_payload(imap_uid="101", in_reply_to=outbound_message.message_id)
    raw = _raw_payload(payload)
    res = client.post(
        "/api/v1/purchases/monitoring/email/callback",
        content=raw,
        headers=_signed_headers(raw, "webhook-pr4-101"),
    )

    assert res.status_code == 202
    data = res.json()
    assert data["duplicate"] is False
    assert data["candidate_ids"]
    assert data["human_message"] == "Resposta recebida e colocada na fila de revisao."

    inbound = db.query(PurchaseEmailInboundMessage).filter(PurchaseEmailInboundMessage.id == uuid.UUID(data["inbound_message_id"])).first()
    assert inbound.status == "response_to_review"
    assert inbound.classification_status == "linked_high_confidence"
    assert inbound.linked_quote_id == uuid.UUID(quote_id)
    assert "<script>" not in inbound.body_html_sanitized

    candidate = db.query(PurchaseResponseCandidate).filter(PurchaseResponseCandidate.id == uuid.UUID(data["candidate_ids"][0])).first()
    assert candidate.confidence_level == "high"
    assert candidate.candidate_status == "needs_review"
    assert "respondeu ao e-mail enviado" in " ".join(candidate.match_reasons_json)

    attachment = db.query(PurchaseEmailAttachment).filter(PurchaseEmailAttachment.inbound_message_id == inbound.id).first()
    assert attachment.scan_status == "blocked"
    assert "executavel" in attachment.blocked_reason

    queue_res = client.get("/api/v1/purchases/response-candidates")
    assert queue_res.status_code == 200
    queue = queue_res.json()
    assert queue[0]["confidence_level"] == "high"
    assert queue[0]["supplier_name"] == "FAM Componentes"

    confirm_res = client.post(f"/api/v1/purchases/response-candidates/{candidate.id}/confirm")
    assert confirm_res.status_code == 200
    assert "Revise os dados recebidos" in confirm_res.json()["human_message"]
    db.refresh(candidate)
    assert candidate.candidate_status == "confirmed"
    rfq_supplier = db.query(PurchaseRFQSupplier).filter(
        PurchaseRFQSupplier.rfq_id == uuid.UUID(quote_id),
        PurchaseRFQSupplier.supplier_id == supplier_for_monitoring.id,
    ).first()
    assert rfq_supplier.status == "RESPONDED"


def test_pr4_monitoring_callback_replay_and_message_duplicate_are_blocked(
    client: TestClient,
    db: Session,
    supplier_for_monitoring: Supplier,
):
    login_admin(client)
    quote_id, _, _ = _prepare_sent_quote(client, supplier_for_monitoring)
    outbound_message = db.query(PurchaseEmailMessage).filter(PurchaseEmailMessage.quote_id == uuid.UUID(quote_id)).first()
    payload = _callback_payload(imap_uid="202", in_reply_to=outbound_message.message_id)
    raw = _raw_payload(payload)

    first = client.post(
        "/api/v1/purchases/monitoring/email/callback",
        content=raw,
        headers=_signed_headers(raw, "webhook-pr4-202"),
    )
    assert first.status_code == 202

    replay = client.post(
        "/api/v1/purchases/monitoring/email/callback",
        content=raw,
        headers=_signed_headers(raw, "webhook-pr4-202"),
    )
    assert replay.status_code == 409
    assert "repetido" in replay.json()["detail"]

    duplicate = client.post(
        "/api/v1/purchases/monitoring/email/callback",
        content=raw,
        headers=_signed_headers(raw, "webhook-pr4-202-retry"),
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["duplicate"] is True
    assert db.query(PurchaseEmailInboundMessage).filter(PurchaseEmailInboundMessage.imap_uid == "202").count() == 1
    assert db.query(PurchaseMonitoringEvent).filter(PurchaseMonitoringEvent.status == "duplicate").count() == 1


def test_pr4_monitoring_callback_rejects_invalid_signature_and_expired_timestamp(
    client: TestClient,
):
    payload = _callback_payload(imap_uid="303")
    raw = _raw_payload(payload)
    headers = _signed_headers(raw, "webhook-pr4-303")
    headers["X-Vesper-Signature"] = "invalid"

    invalid = client.post("/api/v1/purchases/monitoring/email/callback", content=raw, headers=headers)
    assert invalid.status_code == 401
    assert "Assinatura invalida" in invalid.json()["detail"]

    expired_ts = (datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat()
    expired = client.post(
        "/api/v1/purchases/monitoring/email/callback",
        content=raw,
        headers=_signed_headers(raw, "webhook-pr4-303-expired", timestamp=expired_ts),
    )
    assert expired.status_code == 401
    assert "expirado" in expired.json()["detail"]


def test_pr4_unidentified_response_stays_for_manual_link(
    client: TestClient,
    db: Session,
):
    login_admin(client)
    payload = _callback_payload(imap_uid="404", subject="Preco solicitado")
    payload["from_email"] = "vendas@fornecedor-desconhecido.test"
    payload["from_name"] = "Fornecedor Desconhecido"
    payload["in_reply_to"] = None
    payload["references"] = []
    payload["body_text"] = "Segue preco sem identificador da cotacao."
    raw = _raw_payload(payload)

    res = client.post(
        "/api/v1/purchases/monitoring/email/callback",
        content=raw,
        headers=_signed_headers(raw, "webhook-pr4-404"),
    )

    assert res.status_code == 202
    candidate_id = uuid.UUID(res.json()["candidate_ids"][0])
    candidate = db.query(PurchaseResponseCandidate).filter(PurchaseResponseCandidate.id == candidate_id).first()
    assert candidate.candidate_status == "unidentified"
    assert candidate.confidence_level == "low"
    assert candidate.quote_id is None

    attention = client.get("/api/v1/purchases/attention")
    assert attention.status_code == 200
    assert any(item["type"] == "response_to_review" for item in attention.json())
