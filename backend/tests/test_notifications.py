from fastapi import status
from sqlalchemy.orm import Session

from app.core.events import emit_event
from app.core.security import create_access_token, get_password_hash
from app.models.action_intent import ActionIntent
from app.models.notification import Notification, NotificationDelivery
from app.models.role import Role
from app.models.user import User
from app.modules.notifications import service


def auth_headers(username: str) -> dict[str, str]:
    token = create_access_token(subject=username)
    return {"Authorization": f"Bearer {token}"}


def ensure_manager_users(db: Session) -> tuple[User, User]:
    manager_role = db.query(Role).filter(Role.name == "MANAGER").first()
    if not manager_role:
        manager_role = Role(name="MANAGER", description="Gestor")
        db.add(manager_role)
        db.flush()

    manager_a = db.query(User).filter(User.username == "vesper_manager_a").first()
    if not manager_a:
        manager_a = User(
            username="vesper_manager_a",
            email="manager_a@portal.example",
            hashed_password=get_password_hash("managera"),
            is_active=True,
            role_id=manager_role.id,
        )
        db.add(manager_a)

    manager_b = db.query(User).filter(User.username == "vesper_manager_b").first()
    if not manager_b:
        manager_b = User(
            username="vesper_manager_b",
            email="manager_b@portal.example",
            hashed_password=get_password_hash("managerb"),
            is_active=True,
            role_id=manager_role.id,
        )
        db.add(manager_b)

    db.commit()
    db.refresh(manager_a)
    db.refresh(manager_b)
    return manager_a, manager_b


def test_create_notification_service_creates_delivery_for_user(db: Session):
    notif = service.create_notification(
        db=db,
        user_id=1,
        role_target=None,
        module="automations",
        event_type="test.event",
        title="Teste notificacao",
        message="Mensagem de teste",
        severity="INFO",
    )
    db.commit()

    deliveries = db.query(NotificationDelivery).filter(NotificationDelivery.notification_id == notif.id).all()
    assert notif.id is not None
    assert notif.status == "UNREAD"
    assert len(deliveries) == 1
    assert deliveries[0].user_id == 1
    assert deliveries[0].status == "UNREAD"


def test_role_target_generates_individual_deliveries(db: Session):
    manager_a, manager_b = ensure_manager_users(db)

    notif = service.create_notification(
        db=db,
        user_id=None,
        role_target="MANAGER",
        module="automations",
        event_type="test.role_target",
        title="Notificacao para gestores",
        message="Mensagem para perfil MANAGER",
    )
    db.commit()

    deliveries = db.query(NotificationDelivery).filter(NotificationDelivery.notification_id == notif.id).all()
    delivery_user_ids = sorted([delivery.user_id for delivery in deliveries])
    assert manager_a.id in delivery_user_ids
    assert manager_b.id in delivery_user_ids


def test_list_notifications_returns_items_and_next_cursor(db: Session, client):
    admin_headers = auth_headers("vesper_admin")
    user_headers = auth_headers("vesper_user")

    service.create_notification(
        db=db,
        user_id=1,
        role_target=None,
        module="automations",
        event_type="test.event",
        title="Admin Notif",
        message="For admin only",
    )
    service.create_notification(
        db=db,
        user_id=2,
        role_target=None,
        module="automations",
        event_type="test.event",
        title="User Notif",
        message="For user only",
    )
    db.commit()

    res_admin = client.get("/api/v1/notifications?limit=20", headers=admin_headers)
    assert res_admin.status_code == status.HTTP_200_OK
    admin_payload = res_admin.json()
    admin_titles = [notification["title"] for notification in admin_payload["items"]]
    assert "Admin Notif" in admin_titles
    assert "User Notif" not in admin_titles
    assert "next_cursor" in admin_payload

    res_user = client.get("/api/v1/notifications?limit=20", headers=user_headers)
    assert res_user.status_code == status.HTTP_200_OK
    user_payload = res_user.json()
    user_titles = [notification["title"] for notification in user_payload["items"]]
    assert "User Notif" in user_titles
    assert "Admin Notif" not in user_titles


def test_user_cannot_mark_delivery_of_other_user(db: Session, client):
    admin_headers = auth_headers("vesper_admin")
    user_headers = auth_headers("vesper_user")

    notif = service.create_notification(
        db=db,
        user_id=2,
        role_target=None,
        module="automations",
        event_type="test.event",
        title="Somente usuario",
        message="Nao pode ser lida por admin",
    )
    db.commit()

    res_admin = client.post(f"/api/v1/notifications/{notif.id}/read", headers=admin_headers)
    assert res_admin.status_code == status.HTTP_404_NOT_FOUND

    res_user = client.post(f"/api/v1/notifications/{notif.id}/read", headers=user_headers)
    assert res_user.status_code == status.HTTP_200_OK
    assert res_user.json()["status"] == "READ"


def test_mark_read_affects_only_current_user(db: Session, client):
    manager_a, manager_b = ensure_manager_users(db)
    headers_a = auth_headers(manager_a.username)

    notif = service.create_notification(
        db=db,
        user_id=None,
        role_target="MANAGER",
        module="automations",
        event_type="test.read.isolated",
        title="Leitura isolada",
        message="Cada gestor tem seu estado",
    )
    db.commit()

    delivery_a = db.query(NotificationDelivery).filter(
        NotificationDelivery.notification_id == notif.id,
        NotificationDelivery.user_id == manager_a.id,
    ).first()
    delivery_b = db.query(NotificationDelivery).filter(
        NotificationDelivery.notification_id == notif.id,
        NotificationDelivery.user_id == manager_b.id,
    ).first()
    assert delivery_a is not None
    assert delivery_b is not None
    assert delivery_a.status == "UNREAD"
    assert delivery_b.status == "UNREAD"

    read_res = client.post(f"/api/v1/notifications/{notif.id}/read", headers=headers_a)
    assert read_res.status_code == status.HTTP_200_OK

    db.refresh(delivery_a)
    db.refresh(delivery_b)
    assert delivery_a.status == "READ"
    assert delivery_b.status == "UNREAD"


def test_read_all_affects_only_current_user(db: Session, client):
    manager_a, manager_b = ensure_manager_users(db)
    headers_a = auth_headers(manager_a.username)

    service.create_notification(
        db=db,
        user_id=None,
        role_target="MANAGER",
        module="automations",
        event_type="test.read_all.1",
        title="Lote 1",
        message="Primeira",
    )
    service.create_notification(
        db=db,
        user_id=None,
        role_target="MANAGER",
        module="automations",
        event_type="test.read_all.2",
        title="Lote 2",
        message="Segunda",
    )
    db.commit()

    res = client.post("/api/v1/notifications/read-all", headers=headers_a)
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["marked_count"] >= 2

    manager_a_unread = db.query(NotificationDelivery).filter(
        NotificationDelivery.user_id == manager_a.id,
        NotificationDelivery.status == "UNREAD",
    ).count()
    manager_b_unread = db.query(NotificationDelivery).filter(
        NotificationDelivery.user_id == manager_b.id,
        NotificationDelivery.status == "UNREAD",
    ).count()
    assert manager_a_unread == 0
    assert manager_b_unread >= 2


def test_unread_count_endpoint_returns_real_count(db: Session, client):
    manager_a, _ = ensure_manager_users(db)
    headers_a = auth_headers(manager_a.username)

    service.create_notification(
        db=db,
        user_id=manager_a.id,
        role_target=None,
        module="automations",
        event_type="test.unread.direct",
        title="Direta",
        message="Direta",
    )
    service.create_notification(
        db=db,
        user_id=None,
        role_target="MANAGER",
        module="automations",
        event_type="test.unread.role",
        title="Role",
        message="Role",
    )
    db.commit()

    res = client.get("/api/v1/notifications/unread-count", headers=headers_a)
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["count"] >= 2


def test_unread_count_uses_delivery_status_not_global_notification_status(db: Session, client):
    manager_a, manager_b = ensure_manager_users(db)
    headers_a = auth_headers(manager_a.username)

    notif = service.create_notification(
        db=db,
        user_id=None,
        role_target="MANAGER",
        module="approvals",
        event_type="test.badge.regression",
        title="Badge nao deve voltar",
        message="A entrega do usuario ja foi lida.",
    )
    db.commit()

    delivery_a = db.query(NotificationDelivery).filter(
        NotificationDelivery.notification_id == notif.id,
        NotificationDelivery.user_id == manager_a.id,
    ).one()
    delivery_b = db.query(NotificationDelivery).filter(
        NotificationDelivery.notification_id == notif.id,
        NotificationDelivery.user_id == manager_b.id,
    ).one()

    delivery_a.status = "READ"
    delivery_a.read_at = delivery_a.delivered_at
    notif.status = "UNREAD"
    db.commit()

    count_res = client.get("/api/v1/notifications/unread-count", headers=headers_a)
    assert count_res.status_code == status.HTTP_200_OK
    assert count_res.json()["count"] == 0

    list_res = client.get("/api/v1/notifications?unread_only=true", headers=headers_a)
    assert list_res.status_code == status.HTTP_200_OK
    assert all(item["id"] != str(notif.id) for item in list_res.json()["items"])

    db.refresh(delivery_b)
    assert delivery_b.status == "UNREAD"


def test_unread_and_archive_are_scoped_to_current_user(db: Session, client):
    manager_a, manager_b = ensure_manager_users(db)
    headers_a = auth_headers(manager_a.username)

    notif = service.create_notification(
        db=db,
        user_id=None,
        role_target="MANAGER",
        module="purchases",
        event_type="test.archive.scoped",
        title="Arquivamento isolado",
        message="Somente a entrega do usuario atual muda.",
    )
    db.commit()

    read_res = client.post(f"/api/v1/notifications/{notif.id}/read", headers=headers_a)
    assert read_res.status_code == status.HTTP_200_OK
    assert read_res.json()["status"] == "READ"

    unread_res = client.post(f"/api/v1/notifications/{notif.id}/unread", headers=headers_a)
    assert unread_res.status_code == status.HTTP_200_OK
    assert unread_res.json()["status"] == "UNREAD"

    archive_res = client.post(f"/api/v1/notifications/{notif.id}/archive", headers=headers_a)
    assert archive_res.status_code == status.HTTP_200_OK
    assert archive_res.json()["status"] == "ARCHIVED"
    assert archive_res.json()["archived_at"] is not None

    delivery_b = db.query(NotificationDelivery).filter(
        NotificationDelivery.notification_id == notif.id,
        NotificationDelivery.user_id == manager_b.id,
    ).one()
    assert delivery_b.status == "UNREAD"


def test_notification_pagination_cursor_is_stable(db: Session, client):
    user_headers = auth_headers("vesper_user")

    for idx in range(3):
        service.create_notification(
            db=db,
            user_id=2,
            role_target=None,
            module="automations",
            event_type=f"test.page.{idx}",
            title=f"Pagina {idx}",
            message=f"Mensagem {idx}",
        )
    db.commit()

    page1 = client.get("/api/v1/notifications?limit=2", headers=user_headers)
    assert page1.status_code == status.HTTP_200_OK
    payload1 = page1.json()
    assert len(payload1["items"]) == 2
    assert payload1["next_cursor"] is not None

    page2 = client.get(
        f"/api/v1/notifications?limit=2&cursor={payload1['next_cursor']}",
        headers=user_headers,
    )
    assert page2.status_code == status.HTTP_200_OK
    payload2 = page2.json()
    ids_page1 = {item["id"] for item in payload1["items"]}
    ids_page2 = {item["id"] for item in payload2["items"]}
    assert ids_page1.isdisjoint(ids_page2)


def test_event_engine_generates_notification(db: Session):
    intent = ActionIntent(
        source="system",
        proposed_action="update_stock",
        target_module="stock",
        title="Atualiza estoque teste",
        summary="resumo",
        risk_level="HIGH",
        status="PENDING_REVIEW",
        action_payload={"item_id": 1},
    )
    db.add(intent)
    db.flush()

    emit_event(
        db=db,
        event_type="automation.action_intent.created",
        aggregate_type="action_intent",
        aggregate_id=str(intent.id),
        module="automations",
        payload={
            "id": str(intent.id),
            "proposed_action": intent.proposed_action,
            "risk_level": intent.risk_level,
            "status": intent.status,
        },
    )
    db.flush()

    notif = db.query(Notification).filter(Notification.source_id == str(intent.id)).first()
    assert notif is not None
    assert notif.title == "Acao sugerida pendente"
    assert "atualizacao de estoque" in notif.message
    assert notif.severity == "WARNING"
    assert notif.role_target == "MANAGER"


def test_sensitive_payload_masking_in_notification(db: Session):
    notif = service.create_notification(
        db=db,
        user_id=1,
        role_target=None,
        module="automations",
        event_type="test.sensitive",
        title="Test Sensitive",
        message="Testing masking",
        payload_json={
            "password": "my_super_secret_password",
            "safe_field": 123,
            "nested": {"access_token": "token_value"},
            "items": [{"api_key": "key_value"}],
        },
    )
    db.commit()
    db.refresh(notif)
    assert notif.payload_json["password"] == "******"
    assert notif.payload_json["safe_field"] == 123
    assert notif.payload_json["nested"]["access_token"] == "******"
    assert notif.payload_json["items"][0]["api_key"] == "******"


def test_notification_api_does_not_return_raw_payload(db: Session, client):
    admin_headers = auth_headers("vesper_admin")
    notif = service.create_notification(
        db=db,
        user_id=1,
        role_target=None,
        module="automations",
        event_type="test.sensitive",
        title="Sem payload cru",
        message="Contrato publico nao deve expor JSON tecnico.",
        payload_json={"password": "secret", "safe_field": "visible only in db"},
    )
    db.commit()

    res = client.get("/api/v1/notifications", headers=admin_headers)
    assert res.status_code == status.HTTP_200_OK
    matching = [item for item in res.json()["items"] if item["id"] == str(notif.id)]
    assert matching
    assert "payload_json" not in matching[0]


def test_notification_action_url_rejects_external_or_unknown_routes(db: Session):
    external = service.create_notification(
        db=db,
        user_id=1,
        role_target=None,
        module="approvals",
        event_type="test.action_url.external",
        title="Externo bloqueado",
        message="Nao deve persistir URL externa.",
        action_url="https://evil.example/approvals?approval=1",
    )
    unknown = service.create_notification(
        db=db,
        user_id=1,
        role_target=None,
        module="approvals",
        event_type="test.action_url.unknown",
        title="Rota bloqueada",
        message="Nao deve persistir rota desconhecida.",
        action_url="/external-admin?approval=1",
    )
    internal = service.create_notification(
        db=db,
        user_id=1,
        role_target=None,
        module="approvals",
        event_type="test.action_url.internal",
        title="Rota interna",
        message="Deve persistir rota interna conhecida.",
        action_url="/approvals?approval=1",
    )
    db.commit()

    assert external.action_url is None
    assert unknown.action_url is None
    assert internal.action_url == "/approvals?approval=1"


def test_notification_dedup_key_is_scoped_by_recipient(db: Session):
    first = service.create_notification(
        db=db,
        user_id=1,
        role_target=None,
        module="stock",
        event_type="stock.low_detected",
        title="Estoque baixo",
        message="Item precisa de atencao.",
        severity="WARNING",
        source_type="stock_item",
        source_id="item-123",
    )
    second = service.create_notification(
        db=db,
        user_id=1,
        role_target=None,
        module="stock",
        event_type="stock.low_detected",
        title="Estoque baixo duplicado",
        message="Nao deve criar outra notificacao.",
        severity="WARNING",
        source_type="stock_item",
        source_id="item-123",
    )
    other_user = service.create_notification(
        db=db,
        user_id=2,
        role_target=None,
        module="stock",
        event_type="stock.low_detected",
        title="Estoque baixo para outro usuario",
        message="Outro usuario pode receber o mesmo evento.",
        severity="WARNING",
        source_type="stock_item",
        source_id="item-123",
    )
    db.commit()

    assert second.id == first.id
    assert other_user.id != first.id
    assert first.dedup_key.startswith("user:1|")
    assert other_user.dedup_key.startswith("user:2|")
    assert db.query(Notification).filter(Notification.event_type == "stock.low_detected").count() == 2


def test_kanban_events_generate_notifications(db: Session):
    # kanban.card.created
    emit_event(
        db=db,
        event_type="kanban.card.created",
        aggregate_type="kanban_card",
        aggregate_id="123",
        module="kanban",
        payload={
            "card_id": 123,
            "board_id": 1,
            "title": "Card de Teste Kanban",
            "assigned_to_user_id": 2,
            "created_by_user_id": 1
        },
        actor_user_id=1
    )
    db.flush()
    notif = db.query(Notification).filter(Notification.event_type == "kanban.card.created").first()
    assert notif is not None
    assert notif.title == "Card atribuido"
    assert "atribuido ao card" in notif.message
    assert notif.user_id == 2

    # kanban.card.moved
    emit_event(
        db=db,
        event_type="kanban.card.moved",
        aggregate_type="kanban_card",
        aggregate_id="123",
        module="kanban",
        payload={
            "card_id": 123,
            "board_id": 1,
            "title": "Card de Teste Kanban",
            "from_column_id": 1,
            "to_column_id": 2,
            "from_column_name": "A Fazer",
            "to_column_name": "Em Andamento",
            "assigned_to_user_ids": [2],
            "moved_by_user_id": 1
        },
        actor_user_id=1
    )
    db.flush()
    notif_moved = db.query(Notification).filter(
        Notification.event_type == "kanban.card.moved",
        Notification.user_id == 2
    ).first()
    assert notif_moved is not None
    assert "movido para" in notif_moved.message


def test_it_events_generate_notifications(db: Session):
    # it.ticket.created
    emit_event(
        db=db,
        event_type="it.ticket.created",
        aggregate_type="it_ticket",
        aggregate_id="10",
        module="it",
        payload={
            "ticket_id": 10,
            "ticket_number": "TI-000010",
            "title": "Problema de Rede",
            "category": "REDE",
            "assigned_tech_id": None
        },
        actor_user_id=2
    )
    db.flush()
    notif = db.query(Notification).filter(Notification.event_type == "it.ticket.created").first()
    assert notif is not None
    assert notif.role_target == "MANAGER"
    assert "TI-000010" in notif.message

    # it.access.requested
    emit_event(
        db=db,
        event_type="it.access.requested",
        aggregate_type="it_access_request",
        aggregate_id="456",
        module="it",
        payload={
            "request_id": 456,
            "title": "Acesso ao Servidor",
            "requester_id": 2,
            "system_name": "Firewall"
        },
        actor_user_id=2
    )
    db.flush()
    notif_access = db.query(Notification).filter(Notification.event_type == "it.access.requested").first()
    assert notif_access is not None
    assert notif_access.role_target == "MANAGER"
    assert "Firewall" in notif_access.message


def test_chat_events_generate_notifications(db: Session):
    # chat.message.mentioned
    emit_event(
        db=db,
        event_type="chat.message.mentioned",
        aggregate_type="chat_message",
        aggregate_id="999",
        module="chat",
        payload={
            "message_id": 999,
            "conversation_id": 1,
            "sender_user_id": 1,
            "mentioned_user_id": 2,
            "body_preview": "Ola @user"
        },
        actor_user_id=1
    )
    db.flush()
    notif = db.query(Notification).filter(Notification.event_type == "chat.message.mentioned").first()
    assert notif is not None
    assert notif.user_id == 2
    assert "Ola @user" in notif.message


def test_approvals_events_generate_notifications(db: Session):
    # approval.approved
    emit_event(
        db=db,
        event_type="approval.approved",
        aggregate_type="approval",
        aggregate_id="5",
        module="approvals",
        payload={
            "approval_id": 5,
            "title": "Pedido de Compra Notebook",
            "requester_user_id": 2,
            "approver_user_id": 1
        },
        actor_user_id=1
    )
    db.flush()
    notif = db.query(Notification).filter(Notification.event_type == "approval.approved").first()
    assert notif is not None
    assert notif.user_id == 2
    assert " Notebook" in notif.message
