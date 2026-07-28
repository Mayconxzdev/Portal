from typing import Dict, Any
from sqlalchemy.orm import Session
from app.models.user import User
from app.modules.it.service import ITService
from app.modules.it.schemas import TicketCreate

def handle_it_ticket(db: Session, data: Dict[str, Any], current_user: User) -> Dict[str, Any]:
    description = data.get("description", "").strip()
    if not description:
        raise ValueError("Descrição do chamado é obrigatória")

    # Determina categoria padrão
    raw_cat = data.get("category", "OUTRO").upper()
    category = "OUTRO"
    if "HARDWARE" in raw_cat or "COMPUTADOR" in raw_cat:
        category = "COMPUTADOR"
    elif "SOFTWARE" in raw_cat or "SISTEMA" in raw_cat:
        category = "SISTEMA_SOFTWARE"
    elif "REDE" in raw_cat or "INTERNET" in raw_cat:
        category = "INTERNET_REDE"
    elif "ACESSO" in raw_cat:
        category = "ACESSO"

    title = data.get("title", "").strip()
    if not title:
        title = f"Chamado: {description[:50]}..." if len(description) > 50 else f"Chamado: {description}"

    payload = TicketCreate(
        title=title,
        description=description,
        category=category,
        priority=data.get("priority", "MEDIA")
    )

    ticket = ITService.create_ticket(db, payload, current_user)
    
    return {
        "created_entity_type": "it_ticket",
        "created_entity_id": str(ticket.id),
        "ticket_number": ticket.ticket_number,
        "summary": f"Chamado de TI #{ticket.ticket_number} foi aberto com sucesso para {current_user.username}."
    }
