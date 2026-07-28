import uuid
from typing import Dict, Any
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.master_data import ProductItem
from app.modules.purchases.service import PurchasesService
from app.modules.purchases.schemas import PurchaseRequestCreate, PurchaseItemCreate

def handle_purchase_request(db: Session, data: Dict[str, Any], current_user: User) -> Dict[str, Any]:
    product_item_id = data.get("product_item_id")
    quantity = data.get("quantity", 1)
    notes = data.get("notes") or "Solicitado via Universal Action Layer."

    if not product_item_id:
        raise ValueError("Item / SKU do produto é obrigatório.")

    # Se for string, converte para UUID
    if isinstance(product_item_id, str):
        try:
            product_uuid = uuid.UUID(product_item_id)
        except ValueError:
            raise ValueError("ID do produto inválido.")
    else:
        product_uuid = product_item_id

    item = db.query(ProductItem).filter(ProductItem.id == product_uuid).first()
    if not item:
        raise ValueError("Item não encontrado no catálogo do Master Data.")

    payload = PurchaseRequestCreate(
        title=f"Requisição de {item.name}",
        description=notes,
        justification="Abastecimento operacional via Camada Universal de Ações",
        priority="NORMAL",
        items=[
            PurchaseItemCreate(
                item_id=product_uuid,
                quantity=float(quantity),
                unit_of_measure=item.unit_of_measure or "un",
                specifications=notes
            )
        ]
    )

    req = PurchasesService.create_purchase_request(db, payload, current_user)
    
    return {
        "created_entity_type": "purchase_request",
        "created_entity_id": str(req.id),
        "summary": f"Requisição de compra de {item.name} (Qtd: {quantity}) criada com sucesso com status DRAFT."
    }

def handle_rfq(db: Session, data: Dict[str, Any], current_user: User) -> Dict[str, Any]:
    product_item_id = data.get("product_item_id")
    if not product_item_id:
        raise ValueError("Item / SKU do produto é obrigatório para RFQ.")

    # Cria requisição de compras aprovada de antemão para poder criar a RFQ
    req_res = handle_purchase_request(db, data, current_user)
    req_uuid = uuid.UUID(req_res["created_entity_id"])
    
    # Força aprovação temporária para viabilizar RFQ
    req = PurchasesService.get_purchase_request(db, req_uuid, current_user)
    req.status = "APPROVED"
    db.commit()

    class RFQMockPayload:
        title = f"RFQ de Cotação - {req.title}"
        deadline = None
        message_template = "Prezado fornecedor, solicitamos proposta comercial para os itens listados..."

    rfq = PurchasesService.create_rfq(db, req_uuid, RFQMockPayload(), current_user)

    return {
        "created_entity_type": "purchase_rfq",
        "created_entity_id": str(rfq.id),
        "summary": f"Processo de RFQ criado com status DRAFT a partir da requisição vinculada #{req.id}."
    }
