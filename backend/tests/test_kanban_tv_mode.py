from datetime import datetime, timedelta

from fastapi import status

from app.models.kanban import KanbanBoardPermission, KanbanCard, KanbanLabel, KanbanCardLabel
from app.models.module import Module
from app.models.user import User
from app.models.user_module_access import UserModuleAccess


def login(client, username, password):
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == status.HTTP_200_OK
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def grant_module(db, username, level="READ_ONLY"):
    user = db.query(User).filter(User.username == username).first()
    module = db.query(Module).filter(Module.code == "kanban").first()
    access = db.query(UserModuleAccess).filter(UserModuleAccess.user_id == user.id, UserModuleAccess.module_id == module.id).first()
    if access:
        access.permission_level = level
    else:
        db.add(UserModuleAccess(user_id=user.id, module_id=module.id, permission_level=level))
    db.commit()
    return user


def make_board(client, db):
    headers = login(client, "vesper_admin", "admin")
    board = client.post("/api/v1/kanban/boards", json={"name": "TV Producao", "slug": "tv-producao"}, headers=headers).json()
    col = board["columns"][0]["id"]
    today = datetime.now()
    urgent = client.post(
        f"/api/v1/kanban/boards/{board['id']}/cards",
        json={"column_id": col, "title": "OP 123 critica", "priority": "URGENT", "due_date": (today - timedelta(days=2)).isoformat()},
        headers=headers,
    ).json()
    normal = client.post(
        f"/api/v1/kanban/boards/{board['id']}/cards",
        json={"column_id": col, "title": "Card normal", "priority": "LOW", "due_date": (today + timedelta(days=3)).isoformat()},
        headers=headers,
    ).json()
    label = KanbanLabel(board_id=board["id"], name="Urgente", color="#ef4444")
    db.add(label)
    db.flush()
    db.add(KanbanCardLabel(card_id=urgent["id"], label_id=label.id))
    db.commit()
    return headers, board, urgent, normal


def test_tv_config_default_edit_and_permission(client, db):
    headers, board, _, _ = make_board(client, db)
    default = client.get(f"/api/v1/kanban/boards/{board['id']}/tv-config", headers=headers)
    assert default.status_code == status.HTTP_200_OK
    assert default.json()["layout_type"] == "COLUMNS"

    updated = client.patch(
        f"/api/v1/kanban/boards/{board['id']}/tv-config",
        json={"layout_type": "PRODUCTION", "refresh_interval_seconds": 45, "show_card_description": True},
        headers=headers,
    )
    assert updated.status_code == status.HTTP_200_OK
    assert updated.json()["layout_type"] == "PRODUCTION"

    user = grant_module(db, "vesper_user", "NORMAL")
    db.add(KanbanBoardPermission(board_id=board["id"], user_id=user.id, access_level="NORMAL"))
    db.commit()
    client.cookies.clear()
    user_headers = login(client, "vesper_user", "userpass")
    blocked = client.patch(f"/api/v1/kanban/boards/{board['id']}/tv-config", json={"layout_type": "URGENCY"}, headers=user_headers)
    assert blocked.status_code == status.HTTP_403_FORBIDDEN


def test_tv_data_metrics_critical_and_snapshot(client, db):
    headers, board, urgent, _ = make_board(client, db)
    metrics = client.get(f"/api/v1/kanban/boards/{board['id']}/metrics", headers=headers)
    assert metrics.status_code == status.HTTP_200_OK
    data = metrics.json()
    assert data["total_active_cards"] == 2
    assert data["cards_by_priority"]["URGENT"] == 1
    assert data["overdue_cards"] == 1
    assert data["unassigned_cards"] == 2

    critical = client.get(f"/api/v1/kanban/boards/{board['id']}/critical-cards", headers=headers)
    assert critical.status_code == status.HTTP_200_OK
    assert critical.json()[0]["id"] == urgent["id"]
    assert critical.json()[0]["urgency_score"] > 0
    assert critical.json()[0]["urgency_reasons"]

    tv_data = client.get(f"/api/v1/kanban/boards/{board['id']}/tv-data", headers=headers)
    assert tv_data.status_code == status.HTTP_200_OK
    assert tv_data.json()["board"]["id"] == board["id"]
    assert "metrics" in tv_data.json()

    snapshot = client.get(f"/api/v1/kanban/boards/{board['id']}/tv-snapshot", headers=headers)
    assert snapshot.status_code == status.HTTP_200_OK

    archived_card = db.query(KanbanCard).filter(KanbanCard.id == urgent["id"]).first()
    archived_card.is_archived = True
    db.commit()
    hidden = client.get(f"/api/v1/kanban/boards/{board['id']}/tv-data", headers=headers).json()
    assert all(card["id"] != urgent["id"] for card in hidden["cards"])


def test_global_search_and_quick_card_respect_permissions(client, db):
    headers, board, _, _ = make_board(client, db)
    search = client.get("/api/v1/search/global?q=TV", headers=headers)
    assert search.status_code == status.HTTP_200_OK
    assert any(item["type"] == "board" for item in search.json()["results"])

    preview = client.post("/api/v1/kanban/quick-card", json={"text": "producao: Card rapido prioridade alta"}, headers=headers)
    assert preview.status_code == status.HTTP_200_OK
    assert preview.json()["requires_confirmation"] is True

    created = client.post("/api/v1/kanban/quick-card", json={"text": "card: Card rapido prioridade alta", "board_id": board["id"], "confirm": True}, headers=headers)
    assert created.status_code == status.HTTP_200_OK
    assert created.json()["card"]["title"] == "Card rapido prioridade alta"

    user_headers = login(client, "vesper_user", "userpass")
    denied = client.get("/api/v1/search/global?q=TV", headers=user_headers)
    assert denied.status_code == status.HTTP_200_OK
    assert all(item.get("id") != board["id"] for item in denied.json()["results"] if item["type"] == "board")
