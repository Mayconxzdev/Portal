from fastapi import status

from app.models.audit_log import AuditLog
from app.models.kanban import KanbanActivity, KanbanBoardPermission
from app.models.module import Module
from app.models.user import User
from app.models.user_module_access import UserModuleAccess


def login(client, username, password):
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == status.HTTP_200_OK
    return response.json()["access_token"]


def grant_module(db, username, module_code="kanban", level="NORMAL"):
    user = db.query(User).filter(User.username == username).first()
    module = db.query(Module).filter(Module.code == module_code).first()
    access = db.query(UserModuleAccess).filter(
        UserModuleAccess.user_id == user.id,
        UserModuleAccess.module_id == module.id,
    ).first()
    if access:
        access.permission_level = level
    else:
        access = UserModuleAccess(user_id=user.id, module_id=module.id, permission_level=level)
        db.add(access)
    db.commit()
    return user


def create_board_as_admin(client):
    admin_token = login(client, "vesper_admin", "admin")
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.post("/api/v1/kanban/boards", json={"name": "Operacao", "slug": "operacao"}, headers=headers)
    assert response.status_code == status.HTTP_201_CREATED
    return response.json(), headers


def test_create_board_requires_login(client):
    response = client.post("/api/v1/kanban/boards", json={"name": "Sem login"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_create_board_blocks_user_without_module_permission(client):
    token = login(client, "vesper_user", "userpass")
    response = client.post(
        "/api/v1/kanban/boards",
        json={"name": "Bloqueado"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_create_board_creator_becomes_admin_and_default_columns(client, db):
    board, _ = create_board_as_admin(client)
    assert board["access_level"] == "ADMIN"
    assert [column["name"] for column in board["columns"]] == ["A Fazer", "Em andamento", "Concluido"]
    permission = db.query(KanbanBoardPermission).filter(
        KanbanBoardPermission.board_id == board["id"],
        KanbanBoardPermission.access_level == "ADMIN",
    ).first()
    assert permission is not None


def test_list_only_accessible_boards(client, db):
    board, admin_headers = create_board_as_admin(client)
    grant_module(db, "vesper_user", "kanban", "READ_ONLY")
    user_token = login(client, "vesper_user", "userpass")
    user_headers = {"Authorization": f"Bearer {user_token}"}
    response = client.get("/api/v1/kanban/boards", headers=user_headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []

    user = db.query(User).filter(User.username == "vesper_user").first()
    db.add(KanbanBoardPermission(board_id=board["id"], user_id=user.id, access_level="READ_ONLY"))
    db.commit()
    response = client.get("/api/v1/kanban/boards", headers=user_headers)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == board["id"]


def test_columns_cards_custom_fields_activity_and_archive_flow(client, db):
    board, admin_headers = create_board_as_admin(client)
    board_id = board["id"]
    create_column = client.post(
        f"/api/v1/kanban/boards/{board_id}/columns",
        json={"name": "Validacao"},
        headers=admin_headers,
    )
    assert create_column.status_code == status.HTTP_201_CREATED
    new_column_id = create_column.json()["id"]

    reorder = client.post(
        f"/api/v1/kanban/boards/{board_id}/columns/reorder",
        json={"columns": [{"column_id": new_column_id, "position": 0}, {"column_id": board["columns"][0]["id"], "position": 1}]},
        headers=admin_headers,
    )
    assert reorder.status_code == status.HTTP_200_OK

    field_resp = client.post(
        f"/api/v1/kanban/boards/{board_id}/custom-fields",
        json={"name": "Cliente Teste", "key": "cliente_teste", "field_type": "TEXT", "is_required": True},
        headers=admin_headers,
    )
    assert field_resp.status_code == status.HTTP_201_CREATED
    field_id = field_resp.json()["id"]

    card_resp = client.post(
        f"/api/v1/kanban/boards/{board_id}/cards",
        json={
            "column_id": board["columns"][0]["id"],
            "title": "Separar pedido",
            "priority": "HIGH",
            "custom_fields": {"cliente_teste": "Vesper"},
        },
        headers=admin_headers,
    )
    assert card_resp.status_code == status.HTTP_201_CREATED
    card_id = card_resp.json()["id"]
    assert card_resp.json()["custom_fields"]["cliente_teste"] == "Vesper"

    move_same = client.post(
        f"/api/v1/kanban/cards/{card_id}/move",
        json={"column_id": board["columns"][0]["id"], "position": 0},
        headers=admin_headers,
    )
    assert move_same.status_code == status.HTTP_200_OK
    move_other = client.post(
        f"/api/v1/kanban/cards/{card_id}/move",
        json={"column_id": new_column_id, "position": 0},
        headers=admin_headers,
    )
    assert move_other.status_code == status.HTTP_200_OK
    assert move_other.json()["column_id"] == new_column_id

    activity = client.get(f"/api/v1/kanban/boards/{board_id}/activity", headers=admin_headers)
    assert activity.status_code == status.HTTP_200_OK
    assert any(item["action"] == "card.moved" for item in activity.json())

    archive_card = client.post(f"/api/v1/kanban/cards/{card_id}/archive", headers=admin_headers)
    assert archive_card.status_code == status.HTTP_200_OK
    assert archive_card.json()["is_archived"] is True
    restore_card = client.post(f"/api/v1/kanban/cards/{card_id}/restore", headers=admin_headers)
    assert restore_card.status_code == status.HTTP_200_OK
    assert restore_card.json()["is_archived"] is False

    delete_field = client.delete(f"/api/v1/kanban/custom-fields/{field_id}", headers=admin_headers)
    assert delete_field.status_code == status.HTTP_200_OK
    assert delete_field.json()["action"] == "custom_field.disabled"

    archive_board = client.post(f"/api/v1/kanban/boards/{board_id}/archive", headers=admin_headers)
    assert archive_board.status_code == status.HTTP_200_OK
    assert archive_board.json()["is_archived"] is True
    restore_board = client.post(f"/api/v1/kanban/boards/{board_id}/restore", headers=admin_headers)
    assert restore_board.status_code == status.HTTP_200_OK
    assert restore_board.json()["is_archived"] is False

    assert db.query(KanbanActivity).filter(KanbanActivity.board_id == board_id).count() > 0
    assert db.query(AuditLog).filter(AuditLog.action == "kanban.card.created").first() is not None


def test_read_only_user_cannot_edit_card(client, db):
    board, admin_headers = create_board_as_admin(client)
    board_id = board["id"]
    card_resp = client.post(
        f"/api/v1/kanban/boards/{board_id}/cards",
        json={"column_id": board["columns"][0]["id"], "title": "Card restrito"},
        headers=admin_headers,
    )
    card_id = card_resp.json()["id"]

    user = grant_module(db, "vesper_user", "kanban", "READ_ONLY")
    db.add(KanbanBoardPermission(board_id=board_id, user_id=user.id, access_level="READ_ONLY"))
    db.commit()
    user_token = login(client, "vesper_user", "userpass")
    user_headers = {"Authorization": f"Bearer {user_token}"}
    update_resp = client.patch(
        f"/api/v1/kanban/cards/{card_id}",
        json={"title": "Nao autorizado"},
        headers=user_headers,
    )
    assert update_resp.status_code == status.HTTP_403_FORBIDDEN


def test_kanban_summary(client):
    board, admin_headers = create_board_as_admin(client)
    response = client.get("/api/v1/kanban/summary", headers=admin_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["active_boards"] >= 1
    assert "cards_by_priority" in data
