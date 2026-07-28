from typing import Dict, Any
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.master_data import Supplier, ProductItem, Person

def handle_supplier_search(db: Session, data: Dict[str, Any], current_user: User) -> Dict[str, Any]:
    query_str = data.get("query", "").strip()
    if not query_str:
        raise ValueError("Termo de pesquisa de fornecedor é obrigatório")

    # Procura por nome ou CNPJ
    results = db.query(Supplier).join(Person).filter(
        (Supplier.name.ilike(f"%{query_str}%")) | 
        (Supplier.supplier_code.ilike(f"%{query_str}%")) |
        (Person.document_number.ilike(f"%{query_str}%"))
    ).limit(5).all()

    items_list = []
    for sup in results:
        items_list.append({
            "id": str(sup.id),
            "name": sup.name,
            "cnpj": sup.person.document_number if sup.person else None,
            "code": sup.supplier_code
        })

    return {
        "created_entity_type": "supplier_search",
        "created_entity_id": "SEARCH",
        "results": items_list,
        "summary": f"Encontrei {len(items_list)} fornecedor(es) correspondente(s) a '{query_str}'."
    }

def handle_item_search(db: Session, data: Dict[str, Any], current_user: User) -> Dict[str, Any]:
    query_str = data.get("query", "").strip()
    if not query_str:
        raise ValueError("Termo de pesquisa de item é obrigatório")

    # Procura por nome ou SKU
    results = db.query(ProductItem).filter(
        (ProductItem.name.ilike(f"%{query_str}%")) | 
        (ProductItem.sku.ilike(f"%{query_str}%"))
    ).limit(5).all()

    items_list = []
    for it in results:
        items_list.append({
            "id": str(it.id),
            "sku": it.sku,
            "name": it.name,
            "category": it.category
        })

    return {
        "created_entity_type": "product_item_search",
        "created_entity_id": "SEARCH",
        "results": items_list,
        "summary": f"Encontrei {len(items_list)} item(ns) correspondente(s) a '{query_str}'."
    }
