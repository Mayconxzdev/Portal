import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.ws import manager
from app.models.action_intent import ActionIntent
from app.models.action_intent_execution import ActionIntentExecution
from app.models.event_log import EventLog
from app.models.notification import Notification, NotificationDelivery
from app.models.user import User

logger = logging.getLogger("vesper.notifications")

try:
    import redis
except ImportError:
    redis = None

SENSITIVE_KEYS = {
    "password",
    "token",
    "secret",
    "hashed_password",
    "key",
    "vault",
    "vault_key",
    "access_token",
    "api_key",
    "authorization",
}

ALLOWED_ACTION_PATHS = {
    "/approvals",
    "/stock",
    "/purchases",
    "/dashboard",
    "/automations",
    "/chat",
    "/files",
    "/kanban",
    "/it",
    "/proposals",
    "/admin",
    "/legacy-import",
}


def _safe_action_url(action_url: Optional[str]) -> Optional[str]:
    if not action_url:
        return None
    if not action_url.startswith("/") or action_url.startswith("//"):
        return None
    path = action_url.split("?", 1)[0].rstrip("/") or "/"
    if path not in ALLOWED_ACTION_PATHS:
        return None
    if any(token in action_url.lower() for token in ("http://", "https://", "\\", "%5c")):
        return None
    return action_url[:500]


def _build_dedup_key(
    user_id: Optional[int],
    role_target: Optional[str],
    event_type: str,
    severity: str,
    source_type: Optional[str],
    source_id: Optional[str],
    dedup_key: Optional[str],
) -> Optional[str]:
    if dedup_key:
        return dedup_key[:500]
    if not source_type or not source_id:
        return None
    recipient_scope = f"user:{user_id}" if user_id is not None else f"role:{role_target or 'none'}"
    return "|".join([
        recipient_scope,
        event_type,
        source_type,
        str(source_id),
        severity,
    ])[:500]

ACTION_INTENT_NOTIFICATION_EVENTS = {
    "automation.action_intent.created",
    "automation.action_intent.reviewed",
    "automation.action_intent.rejected",
    "automation.action_intent.execution.succeeded",
    "automation.action_intent.execution.blocked",
    "automation.action_intent.execution.failed",
    # Eventos de Kanban
    "kanban.card.created",
    "kanban.card.moved",
    "kanban.card.assigned",
    "kanban.card.completed",
    "kanban.card.comment.created",
    # Eventos de TI
    "it.ticket.created",
    "it.ticket.status_changed",
    "it.ticket.assigned",
    "it.ticket.resolved",
    "it.access.requested",
    # Eventos de Chat
    "chat.message.mentioned",
    # Eventos de Aprovações
    "approval.created",
    "approval.approved",
    "approval.rejected",
    "approval.comment.created",
    # Eventos de Compras
    "purchase.request.created",
    "purchase.request.updated",
    "purchase.rfq.created",
    "purchase.rfq.ready_for_review",
    "purchase.rfq.supplier.added",
    "purchase.rfq.draft_generated",
    "purchase.quote_response.created",
    "purchase.comparison.generated",
    "purchase.action_intent.requested",
    # Eventos de Rastreabilidade de Preços de Compras
    "purchase.price.evidence.created",
    "purchase.price.history.created",
    "purchase.price.suggestion.created",
    "purchase.price.suggestion.approved",
    "purchase.price.suggestion.rejected",
    "purchase.price.reference.created",
    "purchase.price.reference.updated",
    # Eventos de Importacao Legada
    "legacy.import.batch.created",
    "legacy.import.batch.completed",
    "legacy.import.row.reviewed",
    "legacy.import.duplicate.detected",
    "legacy.import.ready_for_review",
    "legacy.import.failed",
}


def mask_sensitive_payload(value: Any) -> Any:
    if isinstance(value, dict):
        masked: dict[str, Any] = {}
        for key, inner_value in value.items():
            key_lower = str(key).lower()
            if any(sensitive_key in key_lower for sensitive_key in SENSITIVE_KEYS):
                masked[key] = "******"
            else:
                masked[key] = mask_sensitive_payload(inner_value)
        return masked
    if isinstance(value, list):
        return [mask_sensitive_payload(item) for item in value]
    return value


def _role_targets_for_user(user_role: str) -> list[str]:
    if user_role == "ADMIN":
        return ["ADMIN", "MANAGER"]
    if user_role == "MANAGER":
        return ["MANAGER"]
    return [user_role]


def _role_matches_target(user_role: str, role_target: str) -> bool:
    return role_target in _role_targets_for_user(user_role)


def _notification_is_visible_legacy(notification: Notification, user_id: int, user_role: str) -> bool:
    if notification.user_id == user_id:
        return True
    if notification.user_id is not None or not notification.role_target:
        return False
    return _role_matches_target(user_role, notification.role_target)


def _notification_to_public(
    notification: Notification,
    delivery: Optional[NotificationDelivery],
) -> dict[str, Any]:
    status = delivery.status if delivery else notification.status
    read_at = delivery.read_at if delivery else notification.read_at
    archived_at = delivery.archived_at if delivery else None
    return {
        "id": notification.id,
        "user_id": notification.user_id,
        "role_target": notification.role_target,
        "module": notification.module,
        "event_type": notification.event_type,
        "title": notification.title,
        "message": notification.message,
        "severity": notification.severity,
        "status": status,
        "source_type": notification.source_type,
        "source_id": notification.source_id,
        "action_url": notification.action_url,
        "created_at": notification.created_at,
        "read_at": read_at,
        "archived_at": archived_at,
        "expires_at": notification.expires_at,
        "correlation_id": notification.correlation_id,
        "tenant_id": notification.tenant_id,
    }


def _notification_ws_payload(notification: Notification, delivery: NotificationDelivery) -> dict[str, Any]:
    return {
        "type": "notification",
        "data": {
            "id": str(notification.id),
            "user_id": notification.user_id,
            "role_target": notification.role_target,
            "module": notification.module,
            "event_type": notification.event_type,
            "title": notification.title,
            "message": notification.message,
            "severity": notification.severity,
            "status": delivery.status,
            "source_type": notification.source_type,
            "source_id": notification.source_id,
            "action_url": notification.action_url,
            "created_at": notification.created_at.isoformat(),
            "read_at": delivery.read_at.isoformat() if delivery.read_at else None,
        },
    }


def _publish_notification_fanout_best_effort(user_id: int, payload: dict[str, Any]) -> None:
    if not settings.NOTIFICATIONS_REDIS_FANOUT_ENABLED:
        return
    if redis is None:
        return
    try:
        r = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            socket_connect_timeout=1.0,
        )
        r.publish(f"notifications.user.{user_id}", json.dumps(payload))
    except Exception as exc:
        logger.warning("Failed to publish notification fan-out over Redis: %s", exc)


def _push_notification_best_effort(notification: Notification, deliveries: list[NotificationDelivery]) -> None:
    async def send() -> None:
        for delivery in deliveries:
            payload = _notification_ws_payload(notification, delivery)
            await manager.send_to_user(delivery.user_id, payload)
            _publish_notification_fanout_best_effort(delivery.user_id, payload)

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        loop.create_task(send())
        return

    try:
        temp_loop = asyncio.new_event_loop()
        temp_loop.run_until_complete(send())
        temp_loop.close()
    except Exception as exc:
        logger.warning("Failed to push notification over WebSocket: %s", exc)


def _create_delivery_if_missing(
    db: Session,
    notification: Notification,
    user_id: int,
) -> NotificationDelivery:
    delivery = db.query(NotificationDelivery).filter(
        NotificationDelivery.notification_id == notification.id,
        NotificationDelivery.user_id == user_id,
    ).first()
    if delivery:
        return delivery
    delivery = NotificationDelivery(
        notification_id=notification.id,
        user_id=user_id,
        status="UNREAD",
        delivered_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        tenant_id=notification.tenant_id,
    )
    db.add(delivery)
    db.flush()
    return delivery


def _resolve_recipient_user_ids(
    db: Session,
    user_id: Optional[int],
    role_target: Optional[str],
) -> list[int]:
    if user_id is not None:
        return [user_id]
    if not role_target:
        return []
    users = db.query(User).filter(User.is_active == True).all()
    recipient_ids: list[int] = []
    for user in users:
        role_name = user.role.name if user.role else "USER"
        if _role_matches_target(role_name, role_target):
            recipient_ids.append(user.id)
    return recipient_ids


def create_notification(
    db: Session,
    user_id: Optional[int],
    role_target: Optional[str],
    module: str,
    event_type: str,
    title: str,
    message: str,
    severity: str = "INFO",
    source_type: Optional[str] = None,
    source_id: Optional[str] = None,
    action_url: Optional[str] = None,
    payload_json: Optional[dict[str, Any]] = None,
    correlation_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    dedup_key: Optional[str] = None,
) -> Notification:
    resolved_dedup_key = _build_dedup_key(
        user_id=user_id,
        role_target=role_target,
        event_type=event_type,
        severity=severity,
        source_type=source_type,
        source_id=source_id,
        dedup_key=dedup_key,
    )
    if resolved_dedup_key:
        existing = db.query(Notification).filter(Notification.dedup_key == resolved_dedup_key).first()
        if existing:
            recipient_user_ids = _resolve_recipient_user_ids(db, user_id=user_id, role_target=role_target)
            deliveries = [
                _create_delivery_if_missing(db, existing, recipient_user_id)
                for recipient_user_id in recipient_user_ids
            ]
            if deliveries:
                _push_notification_best_effort(existing, deliveries)
            return existing

    notification = Notification(
        user_id=user_id,
        role_target=role_target,
        module=module,
        event_type=event_type,
        title=title,
        message=message,
        severity=severity,
        status="UNREAD",
        source_type=source_type,
        source_id=source_id,
        dedup_key=resolved_dedup_key,
        action_url=_safe_action_url(action_url),
        payload_json=mask_sensitive_payload(payload_json) if payload_json else None,
        created_at=datetime.now(timezone.utc),
        correlation_id=correlation_id,
        tenant_id=tenant_id,
    )
    db.add(notification)
    db.flush()

    deliveries: list[NotificationDelivery] = []
    recipient_user_ids = _resolve_recipient_user_ids(db, user_id=user_id, role_target=role_target)
    for recipient_user_id in recipient_user_ids:
        deliveries.append(_create_delivery_if_missing(db, notification, recipient_user_id))

    _push_notification_best_effort(notification, deliveries)
    return notification


def create_notification_for_user(
    db: Session,
    user_id: int,
    module: str,
    event_type: str,
    title: str,
    message: str,
    severity: str = "INFO",
    **kwargs: Any,
) -> Notification:
    return create_notification(
        db=db,
        user_id=user_id,
        role_target=None,
        module=module,
        event_type=event_type,
        title=title,
        message=message,
        severity=severity,
        **kwargs,
    )


def create_notification_for_role(
    db: Session,
    role_target: str,
    module: str,
    event_type: str,
    title: str,
    message: str,
    severity: str = "INFO",
    **kwargs: Any,
) -> Notification:
    return create_notification(
        db=db,
        user_id=None,
        role_target=role_target,
        module=module,
        event_type=event_type,
        title=title,
        message=message,
        severity=severity,
        **kwargs,
    )


def _build_cursor(created_at: datetime, notification_id: uuid.UUID) -> str:
    return f"{created_at.isoformat()}|{notification_id}"


def _parse_cursor(cursor: Optional[str]) -> tuple[Optional[datetime], Optional[uuid.UUID]]:
    if not cursor:
        return None, None
    try:
        created_raw, id_raw = cursor.split("|", 1)
        created_at = datetime.fromisoformat(created_raw)
        notification_id = uuid.UUID(id_raw)
        return created_at, notification_id
    except Exception:
        return None, None


def list_notifications(
    db: Session,
    user_id: int,
    user_role: str,
    unread_only: bool = False,
    status_filter: Optional[str] = None,
    module: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 20,
    cursor: Optional[str] = None,
) -> tuple[list[dict[str, Any]], Optional[str]]:
    safe_limit = min(max(limit, 1), 100)
    role_targets = _role_targets_for_user(user_role)

    delivery_join = and_(
        NotificationDelivery.notification_id == Notification.id,
        NotificationDelivery.user_id == user_id,
    )

    query = db.query(Notification, NotificationDelivery).outerjoin(
        NotificationDelivery,
        delivery_join,
    ).filter(
        or_(
            NotificationDelivery.id.isnot(None),
            and_(
                NotificationDelivery.id.is_(None),
                or_(
                    Notification.user_id == user_id,
                    and_(
                        Notification.user_id.is_(None),
                        Notification.role_target.in_(role_targets),
                    ),
                ),
            ),
        )
    )

    if unread_only:
        query = query.filter(
            or_(
                and_(NotificationDelivery.id.isnot(None), NotificationDelivery.status == "UNREAD"),
                and_(NotificationDelivery.id.is_(None), Notification.status == "UNREAD"),
            )
        )
    if status_filter:
        normalized_status = status_filter.upper()
        query = query.filter(
            or_(
                and_(NotificationDelivery.id.isnot(None), NotificationDelivery.status == normalized_status),
                and_(NotificationDelivery.id.is_(None), Notification.status == normalized_status),
            )
        )
    if module:
        query = query.filter(Notification.module == module)
    if severity:
        query = query.filter(Notification.severity == severity)

    cursor_created_at, cursor_id = _parse_cursor(cursor)
    if cursor_created_at and cursor_id:
        query = query.filter(
            or_(
                Notification.created_at < cursor_created_at,
                and_(
                    Notification.created_at == cursor_created_at,
                    Notification.id < cursor_id,
                ),
            )
        )

    rows = query.order_by(Notification.created_at.desc(), Notification.id.desc()).limit(safe_limit + 1).all()

    has_next = len(rows) > safe_limit
    visible_rows = rows[:safe_limit]
    items = [_notification_to_public(notification, delivery) for notification, delivery in visible_rows]

    next_cursor: Optional[str] = None
    if has_next and visible_rows:
        last_notification, _last_delivery = visible_rows[-1]
        next_cursor = _build_cursor(last_notification.created_at, last_notification.id)

    return items, next_cursor


def mark_notification_read(
    db: Session,
    notification_id: uuid.UUID,
    user_id: int,
    user_role: str,
) -> Optional[dict[str, Any]]:
    delivery = db.query(NotificationDelivery).filter(
        NotificationDelivery.notification_id == notification_id,
        NotificationDelivery.user_id == user_id,
    ).first()
    if delivery:
        if delivery.status != "READ":
            delivery.status = "READ"
            delivery.read_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(delivery)
        notification = db.query(Notification).filter(Notification.id == notification_id).first()
        if not notification:
            return None
        return _notification_to_public(notification, delivery)

    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notification:
        return None

    has_any_delivery = db.query(NotificationDelivery.id).filter(
        NotificationDelivery.notification_id == notification_id,
    ).first() is not None
    if has_any_delivery:
        return None

    if not _notification_is_visible_legacy(notification, user_id, user_role):
        return None

    notification.status = "READ"
    notification.read_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(notification)
    return _notification_to_public(notification, None)


def mark_notification_unread(
    db: Session,
    notification_id: uuid.UUID,
    user_id: int,
    user_role: str,
) -> Optional[dict[str, Any]]:
    delivery = db.query(NotificationDelivery).filter(
        NotificationDelivery.notification_id == notification_id,
        NotificationDelivery.user_id == user_id,
    ).first()
    if delivery:
        if delivery.status != "UNREAD" or delivery.read_at is not None or delivery.archived_at is not None:
            delivery.status = "UNREAD"
            delivery.read_at = None
            delivery.archived_at = None
            db.commit()
            db.refresh(delivery)
        notification = db.query(Notification).filter(Notification.id == notification_id).first()
        if not notification:
            return None
        return _notification_to_public(notification, delivery)

    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notification:
        return None

    has_any_delivery = db.query(NotificationDelivery.id).filter(
        NotificationDelivery.notification_id == notification_id,
    ).first() is not None
    if has_any_delivery:
        return None

    if not _notification_is_visible_legacy(notification, user_id, user_role):
        return None

    notification.status = "UNREAD"
    notification.read_at = None
    db.commit()
    db.refresh(notification)
    return _notification_to_public(notification, None)


def archive_notification(
    db: Session,
    notification_id: uuid.UUID,
    user_id: int,
    user_role: str,
) -> Optional[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    delivery = db.query(NotificationDelivery).filter(
        NotificationDelivery.notification_id == notification_id,
        NotificationDelivery.user_id == user_id,
    ).first()
    if delivery:
        if delivery.status != "ARCHIVED" or delivery.archived_at is None:
            delivery.status = "ARCHIVED"
            delivery.read_at = delivery.read_at or now
            delivery.archived_at = now
            db.commit()
            db.refresh(delivery)
        notification = db.query(Notification).filter(Notification.id == notification_id).first()
        if not notification:
            return None
        return _notification_to_public(notification, delivery)

    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notification:
        return None

    has_any_delivery = db.query(NotificationDelivery.id).filter(
        NotificationDelivery.notification_id == notification_id,
    ).first() is not None
    if has_any_delivery:
        return None

    if not _notification_is_visible_legacy(notification, user_id, user_role):
        return None

    notification.status = "ARCHIVED"
    notification.read_at = notification.read_at or now
    db.commit()
    db.refresh(notification)
    return _notification_to_public(notification, None)


def mark_all_read(db: Session, user_id: int, user_role: str) -> int:
    now = datetime.now(timezone.utc)

    delivery_rows = db.query(NotificationDelivery).filter(
        NotificationDelivery.user_id == user_id,
        NotificationDelivery.status == "UNREAD",
    ).all()
    for delivery in delivery_rows:
        delivery.status = "READ"
        delivery.read_at = now

    role_targets = _role_targets_for_user(user_role)
    legacy_rows = db.query(Notification).outerjoin(
        NotificationDelivery,
        NotificationDelivery.notification_id == Notification.id,
    ).filter(
        Notification.status == "UNREAD",
        or_(
            Notification.user_id == user_id,
            and_(Notification.user_id.is_(None), Notification.role_target.in_(role_targets)),
        ),
        NotificationDelivery.id.is_(None),
    ).all()

    for notification in legacy_rows:
        notification.status = "READ"
        notification.read_at = now

    db.commit()
    return len(delivery_rows) + len(legacy_rows)


def unread_count(db: Session, user_id: int, user_role: str) -> int:
    delivery_count = db.query(func.count(NotificationDelivery.id)).filter(
        NotificationDelivery.user_id == user_id,
        NotificationDelivery.status == "UNREAD",
    ).scalar() or 0

    role_targets = _role_targets_for_user(user_role)
    legacy_count = db.query(func.count(Notification.id)).outerjoin(
        NotificationDelivery,
        NotificationDelivery.notification_id == Notification.id,
    ).filter(
        Notification.status == "UNREAD",
        or_(
            Notification.user_id == user_id,
            and_(Notification.user_id.is_(None), Notification.role_target.in_(role_targets)),
        ),
        NotificationDelivery.id.is_(None),
    ).scalar() or 0

    return int(delivery_count + legacy_count)


def _translate_action(action: str) -> str:
    actions = {
        "approve_approval": "aprovacao automatica",
        "update_stock": "atualizacao de estoque",
        "create_purchase_order": "pedido de compra",
        "delete_file": "exclusao de arquivo",
        "reveal_secret": "acesso a segredo",
        "change_permission": "alteracao de permissao",
        "notify": "notificacao",
        "create_draft": "rascunho",
        "classify": "classificacao",
        "summarize": "resumo",
        "suggest": "sugestao",
    }
    return actions.get(action.lower(), action.replace("_", " ").lower())


def _resolve_action_intent_context(
    db: Session,
    event: EventLog,
) -> tuple[Optional[str], str, str, Optional[int]]:
    action_intent_id: Optional[str] = None
    proposed_action = "acao"
    risk_level = "MEDIUM"
    creator_id: Optional[int] = event.actor_user_id

    if event.aggregate_type == "action_intent":
        action_intent_id = event.aggregate_id
        intent = db.query(ActionIntent).filter(ActionIntent.id == uuid.UUID(action_intent_id)).first()
    elif event.aggregate_type == "action_intent_execution":
        execution = db.query(ActionIntentExecution).filter(
            ActionIntentExecution.id == uuid.UUID(event.aggregate_id)
        ).first()
        intent = None
        if execution:
            action_intent_id = str(execution.action_intent_id)
            intent = db.query(ActionIntent).filter(ActionIntent.id == execution.action_intent_id).first()
    else:
        intent = None

    if intent:
        proposed_action = intent.proposed_action
        risk_level = intent.risk_level
        creator_id = intent.created_by_user_id or creator_id

    return action_intent_id, proposed_action, risk_level, creator_id


def handle_event_notifications(db: Session, event: EventLog) -> Optional[Notification]:
    if event.event_type not in ACTION_INTENT_NOTIFICATION_EVENTS:
        return None

    # Lógica para os eventos legados de automacao
    if event.event_type.startswith("automation.action_intent."):
        action_intent_id, proposed_action, risk_level, creator_id = _resolve_action_intent_context(
            db,
            event,
        )
        action_name = _translate_action(proposed_action)

        title = ""
        message = ""
        severity = "INFO"
        user_id = None
        role_target = None

        if event.event_type == "automation.action_intent.created":
            title = "Acao sugerida pendente"
            message = f"Uma nova sugestao de {action_name} precisa de revisao."
            severity = "WARNING" if risk_level in ("HIGH", "CRITICAL") else "INFO"
            role_target = "MANAGER"
        elif event.event_type == "automation.action_intent.reviewed":
            title = "Acao sugerida revisada"
            message = f"A sugestao de {action_name} foi revisada e liberada para proxima etapa."
            severity = "SUCCESS"
            user_id = creator_id
        elif event.event_type == "automation.action_intent.rejected":
            title = "Acao sugerida rejeitada"
            message = f"A sugestao de {action_name} foi rejeitada."
            severity = "WARNING"
            user_id = creator_id
        elif event.event_type == "automation.action_intent.execution.succeeded":
            title = "Execucao concluida"
            message = f"A acao segura de {action_name} foi concluida."
            severity = "SUCCESS"
            user_id = creator_id
        elif event.event_type == "automation.action_intent.execution.failed":
            title = "Falha na execucao"
            message = f"A execucao de {action_name} falhou e precisa de verificacao."
            severity = "ERROR"
            role_target = "MANAGER"
        elif event.event_type == "automation.action_intent.execution.blocked":
            title = "Execucao bloqueada"
            message = f"A execucao de {action_name} foi bloqueada por regra de seguranca."
            severity = "CRITICAL"
            role_target = "MANAGER"

        if not title or not message:
            return None

        if not user_id and not role_target:
            role_target = "MANAGER"

        return create_notification(
            db=db,
            user_id=user_id,
            role_target=role_target,
            module="automations",
            event_type=event.event_type,
            title=title,
            message=message,
            severity=severity,
            source_type="action_intent",
            source_id=action_intent_id,
            action_url="/automations",
            payload_json=event.payload,
            correlation_id=event.correlation_id,
            tenant_id=event.tenant_id,
        )

    # Eventos de Kanban
    elif event.event_type.startswith("kanban."):
        card_id = event.payload.get("card_id")
        board_id = event.payload.get("board_id")
        card_title = event.payload.get("title") or "Card"
        action_url = f"/kanban?board_id={board_id}&card_id={card_id}" if board_id and card_id else "/kanban"
        
        if event.event_type == "kanban.card.created":
            assigned_to = event.payload.get("assigned_to_user_id")
            if assigned_to and assigned_to != event.actor_user_id:
                return create_notification(
                    db=db,
                    user_id=assigned_to,
                    role_target=None,
                    module="kanban",
                    event_type=event.event_type,
                    title="Card atribuido",
                    message=f"Voce foi atribuido ao card '{card_title}'.",
                    severity="INFO",
                    source_type="kanban_card",
                    source_id=str(card_id) if card_id else None,
                    action_url=action_url,
                    payload_json=event.payload,
                    correlation_id=event.correlation_id,
                    tenant_id=event.tenant_id
                )
                
        elif event.event_type == "kanban.card.assigned":
            assigned_user = event.payload.get("assigned_user_id")
            if assigned_user and assigned_user != event.actor_user_id:
                return create_notification(
                    db=db,
                    user_id=assigned_user,
                    role_target=None,
                    module="kanban",
                    event_type=event.event_type,
                    title="Card atribuido",
                    message=f"Voce foi designado como responsavel pelo card '{card_title}'.",
                    severity="INFO",
                    source_type="kanban_card",
                    source_id=str(card_id) if card_id else None,
                    action_url=action_url,
                    payload_json=event.payload,
                    correlation_id=event.correlation_id,
                    tenant_id=event.tenant_id
                )
                
        elif event.event_type == "kanban.card.moved":
            assigned_ids = event.payload.get("assigned_to_user_ids") or []
            moved_by = event.actor_user_id
            last_notif = None
            for u_id in assigned_ids:
                if u_id != moved_by:
                    last_notif = create_notification(
                        db=db,
                        user_id=u_id,
                        role_target=None,
                        module="kanban",
                        event_type=event.event_type,
                        title="Card movido",
                        message=f"O card '{card_title}' foi movido para '{event.payload.get('to_column_name')}'.",
                        severity="INFO",
                        source_type="kanban_card",
                        source_id=str(card_id) if card_id else None,
                        action_url=action_url,
                        payload_json=event.payload,
                        correlation_id=event.correlation_id,
                        tenant_id=event.tenant_id
                    )
            return last_notif
            
        elif event.event_type == "kanban.card.completed":
            assigned_ids = event.payload.get("assigned_to_user_ids") or []
            completed_by = event.actor_user_id
            last_notif = None
            for u_id in assigned_ids:
                if u_id != completed_by:
                    last_notif = create_notification(
                        db=db,
                        user_id=u_id,
                        role_target=None,
                        module="kanban",
                        event_type=event.event_type,
                        title="Card concluido",
                        message=f"O card '{card_title}' foi concluido.",
                        severity="SUCCESS",
                        source_type="kanban_card",
                        source_id=str(card_id) if card_id else None,
                        action_url=action_url,
                        payload_json=event.payload,
                        correlation_id=event.correlation_id,
                        tenant_id=event.tenant_id
                    )
            return last_notif
            
        elif event.event_type == "kanban.card.comment.created":
            assigned_ids = event.payload.get("assigned_to_user_ids") or []
            author_id = event.actor_user_id
            last_notif = None
            for u_id in assigned_ids:
                if u_id != author_id:
                    last_notif = create_notification(
                        db=db,
                        user_id=u_id,
                        role_target=None,
                        module="kanban",
                        event_type=event.event_type,
                        title="Comentario no card",
                        message=f"Novo comentario no card '{card_title}'.",
                        severity="INFO",
                        source_type="kanban_card",
                        source_id=str(card_id) if card_id else None,
                        action_url=action_url,
                        payload_json=event.payload,
                        correlation_id=event.correlation_id,
                        tenant_id=event.tenant_id
                    )
            return last_notif

    # Eventos de TI (it)
    elif event.event_type.startswith("it."):
        ticket_id = event.payload.get("ticket_id")
        action_url = f"/it?ticket_id={ticket_id}" if ticket_id else "/it"
        
        if event.event_type == "it.ticket.created":
            tech_id = event.payload.get("assigned_tech_id")
            if tech_id:
                return create_notification(
                    db=db,
                    user_id=tech_id,
                    role_target=None,
                    module="it",
                    event_type=event.event_type,
                    title="Chamado atribuido",
                    message=f"O chamado {event.payload.get('ticket_number')} foi atribuido a voce.",
                    severity="INFO",
                    source_type="it_ticket",
                    source_id=str(ticket_id) if ticket_id else None,
                    action_url=action_url,
                    payload_json=event.payload,
                    correlation_id=event.correlation_id,
                    tenant_id=event.tenant_id
                )
            else:
                return create_notification(
                    db=db,
                    user_id=None,
                    role_target="MANAGER",
                    module="it",
                    event_type=event.event_type,
                    title="Novo chamado criado",
                    message=f"Chamado {event.payload.get('ticket_number')} criado: '{event.payload.get('title')}'.",
                    severity="INFO",
                    source_type="it_ticket",
                    source_id=str(ticket_id) if ticket_id else None,
                    action_url=action_url,
                    payload_json=event.payload,
                    correlation_id=event.correlation_id,
                    tenant_id=event.tenant_id
                )
                
        elif event.event_type == "it.ticket.assigned":
            tech_id = event.payload.get("assigned_tech_id")
            if tech_id and tech_id != event.actor_user_id:
                return create_notification(
                    db=db,
                    user_id=tech_id,
                    role_target=None,
                    module="it",
                    event_type=event.event_type,
                    title="Chamado atribuido",
                    message=f"O chamado {event.payload.get('ticket_number')} foi atribuido a voce.",
                    severity="INFO",
                    source_type="it_ticket",
                    source_id=str(ticket_id) if ticket_id else None,
                    action_url=action_url,
                    payload_json=event.payload,
                    correlation_id=event.correlation_id,
                    tenant_id=event.tenant_id
                )
                
        elif event.event_type == "it.ticket.status_changed":
            req_id = event.payload.get("requester_id")
            if req_id and req_id != event.actor_user_id:
                return create_notification(
                    db=db,
                    user_id=req_id,
                    role_target=None,
                    module="it",
                    event_type=event.event_type,
                    title="Status do chamado alterado",
                    message=f"O chamado {event.payload.get('ticket_number')} mudou para '{event.payload.get('new_status')}'.",
                    severity="INFO",
                    source_type="it_ticket",
                    source_id=str(ticket_id) if ticket_id else None,
                    action_url=action_url,
                    payload_json=event.payload,
                    correlation_id=event.correlation_id,
                    tenant_id=event.tenant_id
                )
                
        elif event.event_type == "it.ticket.resolved":
            req_id = event.payload.get("requester_id")
            if req_id:
                return create_notification(
                    db=db,
                    user_id=req_id,
                    role_target=None,
                    module="it",
                    event_type=event.event_type,
                    title="Chamado resolvido",
                    message=f"O chamado {event.payload.get('ticket_number')} foi resolvido.",
                    severity="SUCCESS",
                    source_type="it_ticket",
                    source_id=str(ticket_id) if ticket_id else None,
                    action_url=action_url,
                    payload_json=event.payload,
                    correlation_id=event.correlation_id,
                    tenant_id=event.tenant_id
                )
                
        elif event.event_type == "it.access.requested":
            return create_notification(
                db=db,
                user_id=None,
                role_target="MANAGER",
                module="it",
                event_type=event.event_type,
                title="Solicitacao de acesso",
                message=f"Nova solicitacao de acesso para o sistema '{event.payload.get('system_name')}'.",
                severity="WARNING",
                source_type="it_access_request",
                source_id=str(event.payload.get("request_id")),
                action_url="/it",
                payload_json=event.payload,
                correlation_id=event.correlation_id,
                tenant_id=event.tenant_id
            )

    # Eventos de Chat
    elif event.event_type == "chat.message.mentioned":
        mentioned = event.payload.get("mentioned_user_id")
        if mentioned and mentioned != event.actor_user_id:
            return create_notification(
                db=db,
                user_id=mentioned,
                role_target=None,
                module="chat",
                event_type=event.event_type,
                title="Mencao no chat",
                message=f"Voce foi mencionado no chat: '{event.payload.get('body_preview') or 'mensagem'}'.",
                severity="INFO",
                source_type="chat_message",
                source_id=str(event.payload.get("message_id")),
                action_url=f"/chat?conversation_id={event.payload.get('conversation_id')}&message_id={event.payload.get('message_id')}",
                payload_json=event.payload,
                correlation_id=event.correlation_id,
                tenant_id=event.tenant_id
            )

    # Eventos de Aprovações (approvals)
    elif event.event_type.startswith("approval."):
        approval_id = event.payload.get("approval_id")
        action_url = f"/approvals?approval_id={approval_id}" if approval_id else "/approvals"
        
        if event.event_type == "approval.created":
            return create_notification(
                db=db,
                user_id=None,
                role_target="MANAGER",
                module="approvals",
                event_type=event.event_type,
                title="Nova aprovacao pendente",
                message=f"A solicitacao '{event.payload.get('title')}' aguarda sua decisao.",
                severity="WARNING",
                source_type="approval",
                source_id=str(approval_id) if approval_id else None,
                action_url=action_url,
                payload_json=event.payload,
                correlation_id=event.correlation_id,
                tenant_id=event.tenant_id
            )
            
        elif event.event_type == "approval.approved":
            req_id = event.payload.get("requester_user_id")
            if req_id:
                return create_notification(
                    db=db,
                    user_id=req_id,
                    role_target=None,
                    module="approvals",
                    event_type=event.event_type,
                    title="Solicitacao aprovada",
                    message=f"Sua solicitacao '{event.payload.get('title')}' foi aprovada.",
                    severity="SUCCESS",
                    source_type="approval",
                    source_id=str(approval_id) if approval_id else None,
                    action_url=action_url,
                    payload_json=event.payload,
                    correlation_id=event.correlation_id,
                    tenant_id=event.tenant_id
                )
                
        elif event.event_type == "approval.rejected":
            req_id = event.payload.get("requester_user_id")
            if req_id:
                reason = event.payload.get("reason")
                reason_msg = f" Motivo: {reason}." if reason else ""
                return create_notification(
                    db=db,
                    user_id=req_id,
                    role_target=None,
                    module="approvals",
                    event_type=event.event_type,
                    title="Solicitacao rejeitada",
                    message=f"Sua solicitacao '{event.payload.get('title')}' foi rejeitada.{reason_msg}",
                    severity="ERROR",
                    source_type="approval",
                    source_id=str(approval_id) if approval_id else None,
                    action_url=action_url,
                    payload_json=event.payload,
                    correlation_id=event.correlation_id,
                    tenant_id=event.tenant_id
                )
                
        elif event.event_type == "approval.comment.created":
            req_id = event.payload.get("requester_user_id")
            author_id = event.payload.get("author_user_id")
            
            user_target = None
            role_target = None
            
            if author_id != req_id:
                user_target = req_id
            else:
                role_target = "MANAGER"
                
            return create_notification(
                db=db,
                user_id=user_target,
                role_target=role_target,
                module="approvals",
                event_type=event.event_type,
                title="Novo comentario na aprovacao",
                message=f"Novo comentario na aprovacao '{event.payload.get('title')}'.",
                severity="INFO",
                source_type="approval",
                source_id=str(approval_id) if approval_id else None,
                action_url=action_url,
                payload_json=event.payload,
                correlation_id=event.correlation_id,
                tenant_id=event.tenant_id
            )

    # Eventos de Compras (purchases)
    elif event.event_type.startswith("purchase."):
        if event.event_type in {"purchase.rfq.supplier.added", "purchase.rfq.draft_generated"}:
            return None

        # Extrai dados do payload
        req_id = event.payload.get("requester_user_id")
        rfq_id = event.payload.get("rfq_id")
        request_id = event.payload.get("id") or event.payload.get("request_id")
        title = event.payload.get("title") or "Requisicao de Compra"
        status = event.payload.get("status")
        supplier_name = event.payload.get("supplier_name") or "Fornecedor"
        total_amount = event.payload.get("total_amount")

        action_url = event.payload.get("action_url") or "/purchases"
        severity = "INFO"
        role_target = None
        user_id = None
        notif_title = ""
        message = ""

        source_type = "purchase_request"
        source_id = str(request_id) if request_id else None

        if event.event_type == "purchase.request.created":
            notif_title = "Nova requisicao de compra"
            message = f"Uma nova requisicao de compra '{title}' foi criada e aguarda processamento."
            role_target = "MANAGER"
        elif event.event_type == "purchase.request.updated":
            notif_title = "Requisicao de compra atualizada"
            message = f"A requisicao '{title}' foi atualizada."
            user_id = req_id
        elif event.event_type == "purchase.rfq.created":
            notif_title = "RFQ Criada"
            message = f"Uma nova RFQ '{title}' foi criada."
            role_target = "MANAGER"
        elif event.event_type == "purchase.rfq.ready_for_review":
            notif_title = "RFQ Pronta para Revisao"
            message = f"A RFQ '{title}' esta pronta para revisao de envio."
            role_target = "MANAGER"
        elif event.event_type == "purchase.quote_response.created":
            notif_title = "Resposta de cotacao recebida"
            amount_str = f" no valor de BRL {total_amount:.2f}" if total_amount is not None else ""
            message = f"Cotacao recebida de '{supplier_name}'{amount_str}."
            role_target = "MANAGER"
        elif event.event_type == "purchase.comparison.generated":
            notif_title = "Comparativo gerado"
            message = "O comparativo de cotacoes para a RFQ foi gerado com sucesso."
            role_target = "MANAGER"
        elif event.event_type == "purchase.action_intent.requested":
            notif_title = "Envio de RFQ solicitado"
            message = "Solicitacao de envio de RFQ pendente de revisao."
            role_target = "MANAGER"
        
        # Rastreabilidade de preços de compras
        elif event.event_type == "purchase.price.suggestion.created":
            pct_var = event.payload.get("pct_variation")
            new_price = event.payload.get("new_unit_price")
            suggestion_id = event.payload.get("id")
            
            notif_title = "Nova sugestão de reajuste de preço"
            var_str = f"{pct_var:.2f}%" if pct_var is not None else "Nova Referência"
            message = f"Nova sugestão de preço pendente. Valor proposto: BRL {new_price:.2f} (Variação: {var_str})."
            role_target = "MANAGER"
            action_url = f"/purchases?tab=price_history&suggestion_id={suggestion_id}"
            source_type = "purchase_price_suggestion"
            source_id = str(suggestion_id) if suggestion_id else None
            
            # Verifica se a variação excede o limite configurado
            limit = getattr(settings, "PURCHASE_PRICE_VARIATION_ALERT_PERCENT", 10.0)
            if pct_var is not None and abs(pct_var) >= limit:
                severity = "WARNING"
                notif_title = "ALERTA: Variação alta de preço de compra"
                message = f"Alerta de flutuação de preço detectado! Proposta com variação de {var_str} (Acima de {limit}%)."
                
        elif event.event_type == "purchase.price.suggestion.approved":
            notif_title = "Sugestão de preço aprovada"
            new_price = event.payload.get("new_unit_price")
            suggestion_id = event.payload.get("id")
            message = f"Sua sugestão de reajuste de preço foi aprovada. Novo preço de referência: BRL {new_price:.2f}."
            user_id = event.payload.get("created_by_user_id")
            severity = "INFO"
            source_type = "purchase_price_suggestion"
            source_id = str(suggestion_id) if suggestion_id else None
            
        elif event.event_type == "purchase.price.suggestion.rejected":
            notif_title = "Sugestão de preço rejeitada"
            suggestion_id = event.payload.get("id")
            reason = event.payload.get("reason")
            reason_str = f" Motivo: {reason}" if reason else ""
            message = f"Sua sugestão de reajuste de preço foi rejeitada.{reason_str}"
            user_id = event.payload.get("created_by_user_id")
            severity = "WARNING"
            source_type = "purchase_price_suggestion"
            source_id = str(suggestion_id) if suggestion_id else None

        if notif_title and message:
            return create_notification(
                db=db,
                user_id=user_id,
                role_target=role_target or "MANAGER",
                module="purchases",
                event_type=event.event_type,
                title=notif_title,
                message=message,
                severity=severity,
                source_type=source_type,
                source_id=source_id,
                action_url=action_url,
                payload_json=event.payload,
                correlation_id=event.correlation_id,
                tenant_id=event.tenant_id
            )

    # Eventos de Importacao Legada (legacy.import)
    elif event.event_type.startswith("legacy.import."):
        batch_id = event.payload.get("batch_id")
        source_app = event.payload.get("source_app") or "Legado"
        source_name = event.payload.get("source_name") or "Lote"
        
        action_url = f"/admin/legacy-import?batch_id={batch_id}" if batch_id else "/admin/legacy-import"
        severity = "INFO"
        role_target = None
        user_id = None
        notif_title = ""
        message = ""
        
        source_type = "legacy_import_batch"
        source_id = str(batch_id) if batch_id else None
        
        if event.event_type == "legacy.import.batch.created":
            notif_title = "Lote de importacao registrado"
            message = f"O lote '{source_name}' ({source_app}) foi registrado na area de staging."
            role_target = "MANAGER"
        elif event.event_type == "legacy.import.ready_for_review":
            notif_title = "Lote de importacao pronto para revisao"
            message = f"O lote '{source_name}' ({source_app}) esta pronto para revisao com total de {event.payload.get('total_rows', 0)} linhas."
            role_target = "MANAGER"
            severity = "WARNING"
        elif event.event_type == "legacy.import.duplicate.detected":
            row_id = event.payload.get("row_id")
            notif_title = "Duplicidade detectada no staging legado"
            message = f"Duplicidade em staging ({event.payload.get('entity_target')}) detectada. Match por {event.payload.get('match_type')}."
            role_target = "MANAGER"
            action_url = f"/admin/legacy-import?row_id={row_id}" if row_id else action_url
            source_type = "legacy_import_row"
            source_id = str(row_id) if row_id else source_id
        elif event.event_type == "legacy.import.failed":
            notif_title = "Erro na importacao legada"
            message = f"Falha critica no processamento de staging: {event.payload.get('error_message')}"
            role_target = "ADMIN"
            severity = "ERROR"
        elif event.event_type == "legacy.import.batch.completed":
            notif_title = "Lote de importacao concluido"
            message = f"O lote '{source_name}' ({source_app}) foi concluido com sucesso."
            user_id = event.payload.get("actor_user_id")
            severity = "SUCCESS"
        elif event.event_type == "legacy.import.row.reviewed":
            row_id = event.payload.get("row_id")
            notif_title = "Linha legada revisada"
            message = f"Linha {event.payload.get('entity_target')} revisada com decisao: {event.payload.get('decision')}."
            user_id = event.payload.get("actor_user_id")
            action_url = f"/admin/legacy-import?row_id={row_id}" if row_id else action_url
            source_type = "legacy_import_row"
            source_id = str(row_id) if row_id else source_id

        if notif_title and message:
            return create_notification(
                db=db,
                user_id=user_id,
                role_target=role_target,
                module="admin",
                event_type=event.event_type,
                title=notif_title,
                message=message,
                severity=severity,
                source_type=source_type,
                source_id=source_id,
                action_url=action_url,
                payload_json=event.payload,
                correlation_id=event.correlation_id,
                tenant_id=event.tenant_id
            )

    return None
