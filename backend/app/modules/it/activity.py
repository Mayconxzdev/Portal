from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.core.audit import log_action
from app.models.it import ITActivity
from app.models.user import User


SENSITIVE_KEYS = {"secret", "password", "senha", "token", "secret_encrypted"}


def clean_metadata(metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    safe = {}
    for key, value in (metadata or {}).items():
        if key.lower() in SENSITIVE_KEYS:
            safe[key] = "[redacted]"
        else:
            safe[key] = value
    return safe


def record_it_activity(
    db: Session,
    actor: Optional[User],
    action: str,
    *,
    ticket_id: Optional[int] = None,
    asset_id: Optional[int] = None,
    credential_id: Optional[int] = None,
    certificate_id: Optional[int] = None,
    network_item_id: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
    audit: bool = True,
) -> None:
    safe_metadata = clean_metadata(metadata)
    db.add(
        ITActivity(
            actor_user_id=actor.id if actor else None,
            action=action,
            ticket_id=ticket_id,
            asset_id=asset_id,
            credential_id=credential_id,
            certificate_id=certificate_id,
            network_item_id=network_item_id,
            metadata_json=safe_metadata,
        )
    )
    if audit:
        log_action(
            db=db,
            user_id=actor.id if actor else None,
            action=f"it.{action}",
            module="it",
            details=safe_metadata,
            commit=False,
        )
