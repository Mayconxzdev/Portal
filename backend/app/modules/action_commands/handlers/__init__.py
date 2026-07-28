from typing import Dict, Any
from sqlalchemy.orm import Session
from app.models.user import User

from app.modules.action_commands.handlers.purchases import handle_purchase_request, handle_rfq
from app.modules.action_commands.handlers.prices import handle_price_confer, handle_price_lookup
from app.modules.action_commands.handlers.it import handle_it_ticket
from app.modules.action_commands.handlers.master_data import handle_supplier_search, handle_item_search

HANDLERS = {
    "purchase.price.confer": handle_price_confer,
    "purchase.price.lookup": handle_price_lookup,
    "purchase.request.create": handle_purchase_request,
    "purchase.rfq.create": handle_rfq,
    "it.ticket.create": handle_it_ticket,
    "master_data.supplier.search": handle_supplier_search,
    "master_data.item.search": handle_item_search,
}

def execute_action_handler(db: Session, action_key: str, data: Dict[str, Any], current_user: User) -> Dict[str, Any]:
    """
    Despacha a execução da ação para o handler correspondente e retorna os metadados do recurso criado.
    """
    if action_key in HANDLERS:
        return HANDLERS[action_key](db, data, current_user)
    
    # Handlers em Preview (Coming Next)
    if action_key in ["proposal.create", "production.op.move", "file.link"]:
        return {
            "created_entity_type": action_key.split(".")[0],
            "created_entity_id": "PREVIEW_UUID",
            "summary": "Esta ação está registrada como Preview/Coming Next e será implementada na próxima PR.",
            "dry_run_success": True
        }
        
    raise ValueError(f"Nenhum handler registrado para a ação {action_key}")
