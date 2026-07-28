import uuid
from typing import Dict, Any
from sqlalchemy.orm import Session
from decimal import Decimal
from app.models.user import User
from app.models.master_data import ProductItem, Supplier
from app.modules.purchases.service import PurchasesService
from app.modules.purchases.schemas import PurchasePriceEvidenceCreate

def handle_price_confer(db: Session, data: Dict[str, Any], current_user: User) -> Dict[str, Any]:
    supplier_id = data.get("supplier_id")
    product_item_id = data.get("product_item_id")
    unit_price = data.get("unit_price")
    quantity = data.get("quantity") or 1.0
    document_number = data.get("document_number") or "CONFERÊNCIA"
    notes = data.get("notes") or "Lançado via Camada Universal de Ações."

    if not product_item_id:
        raise ValueError("Item / SKU do produto é obrigatório para registrar preço.")
    if not unit_price:
        raise ValueError("Preço unitário é obrigatório.")

    # Converte strings para UUID
    sup_uuid = None
    if supplier_id:
        if isinstance(supplier_id, str):
            sup_uuid = uuid.UUID(supplier_id)
        else:
            sup_uuid = supplier_id

    if isinstance(product_item_id, str):
        prod_uuid = uuid.UUID(product_item_id)
    else:
        prod_uuid = product_item_id

    product = db.query(ProductItem).filter(ProductItem.id == prod_uuid).first()
    if not product:
        raise ValueError("Produto não encontrado no Master Data.")

    if sup_uuid:
        supplier = db.query(Supplier).filter(Supplier.id == sup_uuid).first()
        if not supplier:
            raise ValueError("Fornecedor não encontrado no Master Data.")

    payload = PurchasePriceEvidenceCreate(
        source_type="MANUAL_ENTRY",
        supplier_id=sup_uuid,
        product_item_id=prod_uuid,
        unit_price=Decimal(str(unit_price)),
        quantity=Decimal(str(quantity)),
        total_amount=Decimal(str(float(unit_price) * float(quantity))),
        document_number=document_number,
        notes=notes,
        unit_of_measure=product.unit_of_measure or "un"
    )

    evidence = PurchasesService.create_price_evidence(db, payload, current_user)

    # Busca a sugestão de reajuste criada automaticamente no banco
    # (vimos que create_price_evidence cria a sugestão)
    # Retorna o ID da evidência como o ID da entidade criada
    return {
        "created_entity_type": "purchase_price_evidence",
        "created_entity_id": str(evidence.id),
        "summary": f"Evidência de preço criada com sucesso (Valor: R$ {unit_price:.2f}). A sugestão de reajuste correspondente foi adicionada à Fila de Aprovações."
    }

def handle_price_lookup(db: Session, data: Dict[str, Any], current_user: User) -> Dict[str, Any]:
    product_item_id = data.get("product_item_id")
    if not product_item_id:
        raise ValueError("Item / SKU do produto é obrigatório para consulta.")

    if isinstance(product_item_id, str):
        prod_uuid = uuid.UUID(product_item_id)
    else:
        prod_uuid = product_item_id

    product = db.query(ProductItem).filter(ProductItem.id == prod_uuid).first()
    if not product:
        raise ValueError("Produto não encontrado no Master Data.")

    history = PurchasesService.get_item_price_timeline(db, prod_uuid, current_user)
    
    results = []
    for h in history:
        results.append({
            "observed_at": h.observed_at.isoformat() if h.observed_at else None,
            "unit_price": float(h.unit_price),
            "supplier_name": (h.supplier.person.name if h.supplier.person else h.supplier.company_name) if h.supplier else "Geral"
        })

    return {
        "created_entity_type": "purchase_price_history",
        "created_entity_id": "LOOKUP",
        "history": results,
        "summary": f"Encontrei {len(results)} registros de preços anteriores para {product.name}."
    }
