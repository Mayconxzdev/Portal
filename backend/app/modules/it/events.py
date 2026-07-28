import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set

from sqlalchemy.orm import Session

from app.core.ws import manager
from app.models.it import ITTicket
from app.models.user import User
from app.modules.it.permissions import is_it_staff


def _schedule_send(user_id: int, payload: Dict[str, Any]) -> None:
    async def _send() -> None:
        await manager.send_to_user(user_id, payload)

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if loop.is_running():
        loop.create_task(_send())
    else:
        loop.run_until_complete(_send())


def emit_it_event(
    db: Session,
    *,
    event: str,
    actor: Optional[User] = None,
    ticket: Optional[ITTicket] = None,
    entity_type: str = "ticket",
    entity_id: Optional[int] = None,
    message: str = "",
    internal: bool = False,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """Emit a sanitized TI event to connected users.

    The payload intentionally excludes comments, file paths and credential
    secrets. Internal ticket events are sent only to TI staff.
    """
    payload: Dict[str, Any] = {
        "event": event,
        "entity_type": entity_type,
        "entity_id": entity_id or (ticket.id if ticket else None),
        "ticket_id": ticket.id if ticket else None,
        "message": message,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if actor:
        payload["actor_user_id"] = actor.id
    if extra:
        for key, value in extra.items():
            if key in {"secret", "secret_encrypted", "comment", "path", "storage_key"}:
                continue
            payload[key] = value

    # Integracao com o Event Engine global do Portal
    if event in {"it.ticket.created", "it.ticket.assigned", "it.ticket.status_changed"} and ticket:
        from app.core.events import emit_event
        
        actor_id = actor.id if actor else None
        
        if event == "it.ticket.created":
            emit_event(
                db=db,
                event_type="it.ticket.created",
                aggregate_type="it_ticket",
                aggregate_id=str(ticket.id),
                module="it",
                payload={
                    "ticket_id": ticket.id,
                    "ticket_number": ticket.ticket_number,
                    "title": ticket.title,
                    "category": ticket.category,
                    "assigned_tech_id": ticket.assigned_to_user_id
                },
                actor_user_id=actor_id
            )
            
        elif event == "it.ticket.assigned":
            emit_event(
                db=db,
                event_type="it.ticket.assigned",
                aggregate_type="it_ticket",
                aggregate_id=str(ticket.id),
                module="it",
                payload={
                    "ticket_id": ticket.id,
                    "ticket_number": ticket.ticket_number,
                    "title": ticket.title,
                    "assigned_tech_id": ticket.assigned_to_user_id or actor_id or 0,
                    "assigned_by_id": actor_id or 0
                },
                actor_user_id=actor_id
            )
            
        elif event == "it.ticket.status_changed":
            old_status = "ABERTO"
            if extra and "old_status" in extra:
                old_status = extra["old_status"]
            elif ticket.status == "FECHADO":
                old_status = "EM_ATENDIMENTO"
                
            emit_event(
                db=db,
                event_type="it.ticket.status_changed",
                aggregate_type="it_ticket",
                aggregate_id=str(ticket.id),
                module="it",
                payload={
                    "ticket_id": ticket.id,
                    "ticket_number": ticket.ticket_number,
                    "title": ticket.title,
                    "old_status": old_status,
                    "new_status": ticket.status,
                    "requester_id": ticket.requester_user_id
                },
                actor_user_id=actor_id
            )
            
            # Se for resolvido/fechado, emite tambem it.ticket.resolved
            if ticket.status == "FECHADO":
                emit_event(
                    db=db,
                    event_type="it.ticket.resolved",
                    aggregate_type="it_ticket",
                    aggregate_id=str(ticket.id),
                    module="it",
                    payload={
                        "ticket_id": ticket.id,
                        "ticket_number": ticket.ticket_number,
                        "title": ticket.title,
                        "requester_id": ticket.requester_user_id,
                        "resolved_by_id": actor_id or 0
                    },
                    actor_user_id=actor_id
                )

    recipients: Set[int] = set()
    if ticket and not internal:
        recipients.add(ticket.requester_user_id)

    for user in db.query(User).filter(User.is_active == True).all():
        if is_it_staff(db, user):
            recipients.add(user.id)

    for user_id in recipients:
        _schedule_send(user_id, {"type": "it_event", "data": payload})
