import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.master_data import Person, Supplier
from app.models.purchase import (
    PurchaseEmailAttachment,
    PurchaseEmailInboundMessage,
    PurchaseMonitoredAccount,
    PurchasePriceHistory,
    PurchaseResponseCandidate,
    PurchaseResponseExtractedField,
    PurchaseResponseExtraction,
)


def login_admin(client: TestClient) -> None:
    client.post("/api/v1/auth/login", json={"username": "vesper_admin", "password": "admin"})


@pytest.fixture
def supplier_for_extraction(db: Session):
    person = Person(
        id=uuid.uuid4(),
        type="COMPANY",
        name="FAM Componentes",
        document_type="CNPJ",
        document_number="55555555000155",
        email="cotacao@fornecedor-alfa.example",
        is_active=True,
    )
    db.add(person)
    db.flush()
    supplier = Supplier(
        id=uuid.uuid4(),
        person_id=person.id,
        supplier_code="FAM-PR5",
        preferred_contact_email="cotacao@fornecedor-alfa.example",
        status="ACTIVE",
    )
    db.add(supplier)
    db.commit()
    return supplier


def _create_quote(client: TestClient, supplier: Supplier) -> str:
    quote_res = client.post("/api/v1/purchases/quotes", json={
        "title": "Cotacao com extracao",
        "origin_type": "manual",
    })
    assert quote_res.status_code == 201
    quote_id = quote_res.json()["id"]
    item_res = client.post(f"/api/v1/purchases/quotes/{quote_id}/items", json={
        "free_text_description": "Cabo PP 3x2,5",
        "quantity": 10,
        "unit_of_measure": "m",
        "source_type": "manual",
        "source_confidence": "high",
        "match_status": "confirmed",
    })
    assert item_res.status_code == 201
    selection_res = client.post(f"/api/v1/purchases/quotes/{quote_id}/supplier-selection", json={
        "suppliers": [{
            "supplier_id": str(supplier.id),
            "item_ids": [item_res.json()["id"]],
        }]
    })
    assert selection_res.status_code == 200
    return quote_id


def _create_candidate(db: Session, quote_id: str, supplier: Supplier, *, with_text: bool = True) -> PurchaseResponseCandidate:
    monitored = PurchaseMonitoredAccount(
        id=uuid.uuid4(),
        account_email="compras@portal.example",
        folder="INBOX",
        status="not_configured",
        imap_enabled=False,
        has_secret=False,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(monitored)
    db.flush()
    inbound = PurchaseEmailInboundMessage(
        id=uuid.uuid4(),
        monitored_account_id=monitored.id,
        account_email="compras@portal.example",
        folder="INBOX",
        imap_uid=str(uuid.uuid4()),
        message_id=f"<{uuid.uuid4()}@fornecedor-alfa.example>",
        from_email="cotacao@fornecedor-alfa.example",
        from_name="FAM Componentes",
        to_json=["compras@portal.example"],
        cc_json=[],
        subject="Re: Cotacao COT-SANDBOX-123456",
        normalized_subject="cotacao cot-sandbox-123456",
        body_text=(
            "Preco unitario R$ 12,50. Prazo de entrega 4 dias. "
            "Pagamento boleto 28 dias. Disponivel para envio imediato."
        ) if with_text else "",
        received_at=datetime.now(timezone.utc),
        content_hash=uuid.uuid4().hex,
        idempotency_key=uuid.uuid4().hex,
        status="response_to_review",
        classification_status="confirmed_by_user",
        linked_quote_id=uuid.UUID(quote_id),
        linked_supplier_id=supplier.id,
        confidence_score=90,
        confidence_level="high",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(inbound)
    db.flush()
    if with_text:
        db.add(PurchaseEmailAttachment(
            inbound_message_id=inbound.id,
            filename="cotacao.pdf",
            safe_filename="cotacao.pdf",
            content_type="application/pdf",
            detected_content_type="application/pdf",
            size_bytes=2048,
            sha256=uuid.uuid4().hex,
            scan_status="pending_review",
            text_preview="Frete CIF incluso. Validade da proposta 10 dias.",
            created_at=datetime.now(timezone.utc),
        ))
    candidate = PurchaseResponseCandidate(
        id=uuid.uuid4(),
        inbound_message_id=inbound.id,
        quote_id=uuid.UUID(quote_id),
        rfq_id=uuid.UUID(quote_id),
        supplier_id=supplier.id,
        candidate_status="needs_review",
        confidence_score=90,
        confidence_level="high",
        match_reasons_json=["vinculo manual feito pelo responsavel"],
        risk_flags_json=[],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(candidate)
    db.commit()
    return candidate


def test_pr5_extracts_fields_with_evidence_without_updating_prices(
    client: TestClient,
    db: Session,
    supplier_for_extraction: Supplier,
):
    login_admin(client)
    quote_id = _create_quote(client, supplier_for_extraction)
    candidate = _create_candidate(db, quote_id, supplier_for_extraction)
    price_history_count = db.query(PurchasePriceHistory).count()

    res = client.post(f"/api/v1/purchases/response-candidates/{candidate.id}/extract")

    assert res.status_code == 200
    extraction = res.json()
    assert extraction["status"] == "needs_review"
    field_names = {field["field_name"] for field in extraction["fields"]}
    assert {"unit_price", "delivery_days", "freight", "payment_terms", "validity", "availability"}.issubset(field_names)
    unit_price = next(field for field in extraction["fields"] if field["field_name"] == "unit_price")
    assert unit_price["normalized_value"] == "12.50"
    assert unit_price["confidence_level"] == "high"
    assert unit_price["evidences"][0]["snippet"]
    freight = next(field for field in extraction["fields"] if field["field_name"] == "freight")
    assert freight["source_label"] == "cotacao.pdf"
    assert db.query(PurchasePriceHistory).count() == price_history_count


def test_pr5_review_records_human_decisions_and_keeps_data_reviewable(
    client: TestClient,
    db: Session,
    supplier_for_extraction: Supplier,
):
    login_admin(client)
    quote_id = _create_quote(client, supplier_for_extraction)
    candidate = _create_candidate(db, quote_id, supplier_for_extraction)
    extraction_res = client.post(f"/api/v1/purchases/response-candidates/{candidate.id}/extract")
    extraction = extraction_res.json()
    unit_price = next(field for field in extraction["fields"] if field["field_name"] == "unit_price")
    delivery = next(field for field in extraction["fields"] if field["field_name"] == "delivery_days")

    review_res = client.post(f"/api/v1/purchases/response-extractions/{extraction['id']}/review", json={
        "decisions": [
            {"field_id": unit_price["id"], "decision": "correct", "reviewed_value": "12.75"},
            {"field_id": delivery["id"], "decision": "accept"},
        ]
    })

    assert review_res.status_code == 200
    assert "Nenhum preco ou comparativo foi atualizado automaticamente" in review_res.json()["human_message"]
    db_extraction = db.query(PurchaseResponseExtraction).filter(PurchaseResponseExtraction.id == uuid.UUID(extraction["id"])).first()
    assert db_extraction.status == "reviewed"
    corrected = db.query(PurchaseResponseExtractedField).filter(PurchaseResponseExtractedField.id == uuid.UUID(unit_price["id"])).first()
    assert corrected.review_status == "corrected"
    assert corrected.normalized_value == "12.75"


def test_pr5_empty_response_requires_manual_review(
    client: TestClient,
    db: Session,
    supplier_for_extraction: Supplier,
):
    login_admin(client)
    quote_id = _create_quote(client, supplier_for_extraction)
    candidate = _create_candidate(db, quote_id, supplier_for_extraction, with_text=False)

    res = client.post(f"/api/v1/purchases/response-candidates/{candidate.id}/extract")

    assert res.status_code == 200
    extraction = res.json()
    assert extraction["status"] == "needs_manual_review"
    assert extraction["fields"] == []
    assert extraction["confidence_summary"] == "low"
