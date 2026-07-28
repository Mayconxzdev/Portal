from typing import Any, Dict, Optional
import asyncio

from sqlalchemy.orm import Session

from app.core.audit import log_action
from app.core.events import dispatch_event
from app.core.ws import kanban_manager
from app.models.kanban import KanbanActivity
from app.models.user import User


def record_activity(
    db: Session,
    board_id: int,
    actor: Optional[User],
    action: str,
    card_id: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> KanbanActivity:
    activity = KanbanActivity(
        board_id=board_id,
        card_id=card_id,
        actor_user_id=actor.id if actor else None,
        action=action,
        metadata_json=metadata or {},
    )
    db.add(activity)
    log_action(
        db=db,
        user_id=actor.id if actor else None,
        action=f"kanban.{action}",
        module="kanban",
        details={
            "board_id": board_id,
            "card_id": card_id,
            **(metadata or {}),
        },
        commit=False,
    )
    dispatch_event(f"kanban.{action}", {"board_id": board_id, "card_id": card_id, **(metadata or {})})
    payload = {
        "type": "kanban_event",
        "event": f"kanban.{action}",
        "board_id": board_id,
        "card_id": card_id,
        "data": metadata or {},
    }
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(kanban_manager.broadcast_board(board_id, payload))
    except RuntimeError:
        pass
    return activity
