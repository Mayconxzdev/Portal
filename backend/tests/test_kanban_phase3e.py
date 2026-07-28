import io
import uuid

from fastapi import status
from openpyxl import Workbook

from app.models.audit_log import AuditLog
from app.models.module import Module
from app.models.role import Role
from app.models.user import User
from app.models.user_module_access import UserModuleAccess


def login(client, username="vesper_admin", password="admin"):
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == status.HTTP_200_OK
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def grant_module(db, username, level="NORMAL"):
    user = db.query(User).filter(User.username == username).first()
    module = db.query(Module).filter(Module.code == "kanban").first()
    access = db.query(UserModuleAccess).filter(UserModuleAccess.user_id == user.id, UserModuleAccess.module_id == module.id).first()
    if access:
        access.permission_level = level
    else:
        db.add(UserModuleAccess(user_id=user.id, module_id=module.id, permission_level=level))
    db.commit()
    return user


def create_board(client, preset="generic"):
    headers = login(client)
    slug = f"fase3e-{uuid.uuid4().hex[:8]}"
    response = client.post("/api/v1/kanban/boards", json={"name": f"Fase 3E {slug}", "slug": slug, "preset": preset}, headers=headers)
    assert response.status_code == status.HTTP_201_CREATED, response.text
    return headers, response.json()


def test_board_gets_default_views_and_view_crud(client, db):
    headers, board = create_board(client)
    views = client.get(f"/api/v1/kanban/boards/{board['id']}/views", headers=headers)
    assert views.status_code == status.HTTP_200_OK
    assert {item["view_type"] for item in views.json()} >= {"BOARD", "LIST", "TV_LIST"}

    created = client.post(
        f"/api/v1/kanban/boards/{board['id']}/views",
        json={"name": "Lista de testes", "view_type": "LIST", "density": "DENSE", "visible_columns": ["title", "priority"]},
        headers=headers,
    )
    assert created.status_code == status.HTTP_201_CREATED
    view_id = created.json()["id"]

    updated = client.patch(f"/api/v1/kanban/board-views/{view_id}", json={"name": "Lista revisada"}, headers=headers)
    assert updated.status_code == status.HTTP_200_OK
    assert updated.json()["name"] == "Lista revisada"

    duplicated = client.post(f"/api/v1/kanban/board-views/{view_id}/duplicate", headers=headers)
    assert duplicated.status_code == status.HTTP_200_OK

    defaulted = client.post(f"/api/v1/kanban/board-views/{view_id}/set-default", headers=headers)
    assert defaulted.status_code == status.HTTP_200_OK
    assert defaulted.json()["is_default"] is True

    assert db.query(AuditLog).filter(AuditLog.action == "kanban.view.updated").first() is not None


def test_list_data_production_preset_and_duplicate_card(client):
    headers, board = create_board(client, preset="producao")
    assert any(field["key"] == "op" for field in board["custom_fields"])
    list_data = client.get(f"/api/v1/kanban/boards/{board['id']}/list-data", headers=headers)
    assert list_data.status_code == status.HTTP_200_OK
    assert "op" in list_data.json()["visible_columns"]

    card = client.post(
        f"/api/v1/kanban/boards/{board['id']}/cards",
        json={"column_id": board["columns"][0]["id"], "title": "OP teste", "custom_fields": {"op": "3001"}},
        headers=headers,
    )
    assert card.status_code == status.HTTP_201_CREATED
    duplicate = client.post(f"/api/v1/kanban/cards/{card.json()['id']}/duplicate", json={"copy_custom_fields": True}, headers=headers)
    assert duplicate.status_code == status.HTTP_200_OK
    assert duplicate.json()["custom_fields"]["op"] == "3001"

    blocked_delete = client.delete(f"/api/v1/kanban/cards/{card.json()['id']}", headers=headers)
    assert blocked_delete.status_code == status.HTTP_409_CONFLICT


def test_inactive_custom_field_stays_configurable_but_hidden_from_operational_views(client):
    headers, board = create_board(client, preset="producao")
    op_field = next(field for field in board["custom_fields"] if field["key"] == "op")
    card = client.post(
        f"/api/v1/kanban/boards/{board['id']}/cards",
        json={"column_id": board["columns"][0]["id"], "title": "Campo oculto", "custom_fields": {"op": "777"}},
        headers=headers,
    )
    assert card.status_code == status.HTTP_201_CREATED

    disabled = client.patch(f"/api/v1/kanban/custom-fields/{op_field['id']}", json={"is_active": False}, headers=headers)
    assert disabled.status_code == status.HTTP_200_OK
    assert disabled.json()["is_active"] is False

    detail = client.get(f"/api/v1/kanban/boards/{board['id']}", headers=headers)
    assert detail.status_code == status.HTTP_200_OK
    assert "op" not in {field["key"] for field in detail.json()["custom_fields"]}

    configurable = client.get(f"/api/v1/kanban/boards/{board['id']}/custom-fields", headers=headers)
    assert configurable.status_code == status.HTTP_200_OK
    assert any(field["key"] == "op" and field["is_active"] is False for field in configurable.json())

    list_data = client.get(f"/api/v1/kanban/boards/{board['id']}/list-data", headers=headers)
    assert list_data.status_code == status.HTTP_200_OK
    assert "op" not in list_data.json()["visible_columns"]
    assert "op" not in list_data.json()["cards"][0]["custom_fields"]

    tv_data = client.get(f"/api/v1/kanban/boards/{board['id']}/tv-data", headers=headers)
    assert tv_data.status_code == status.HTTP_200_OK
    assert "op" not in tv_data.json()["production_fields"]
    assert "op" not in tv_data.json()["cards"][0]["custom_fields"]

    reactivated = client.patch(f"/api/v1/kanban/custom-fields/{op_field['id']}", json={"is_active": True}, headers=headers)
    assert reactivated.status_code == status.HTTP_200_OK
    assert reactivated.json()["is_active"] is True


def test_inactive_label_can_be_listed_for_configuration(client):
    headers, board = create_board(client)
    label = client.post(
        f"/api/v1/kanban/boards/{board['id']}/labels",
        json={"name": "Aguardando", "color": "#f59e0b"},
        headers=headers,
    )
    assert label.status_code == status.HTTP_201_CREATED

    disabled = client.patch(f"/api/v1/kanban/labels/{label.json()['id']}", json={"is_active": False}, headers=headers)
    assert disabled.status_code == status.HTTP_200_OK

    active_only = client.get(f"/api/v1/kanban/boards/{board['id']}/labels", headers=headers)
    assert active_only.status_code == status.HTTP_200_OK
    assert all(item["id"] != label.json()["id"] for item in active_only.json())

    configurable = client.get(f"/api/v1/kanban/boards/{board['id']}/labels?include_inactive=true", headers=headers)
    assert configurable.status_code == status.HTTP_200_OK
    assert any(item["id"] == label.json()["id"] and item["is_active"] is False for item in configurable.json())


def test_column_restore_delete_empty_and_block_with_cards(client, db):
    headers, board = create_board(client)
    column = client.post(f"/api/v1/kanban/boards/{board['id']}/columns", json={"name": "Temporaria"}, headers=headers).json()
    archived = client.post(f"/api/v1/kanban/columns/{column['id']}/archive", headers=headers)
    assert archived.status_code == status.HTTP_200_OK
    restored = client.post(f"/api/v1/kanban/columns/{column['id']}/restore", headers=headers)
    assert restored.status_code == status.HTTP_200_OK
    deleted = client.delete(f"/api/v1/kanban/columns/{column['id']}", headers=headers)
    assert deleted.status_code == status.HTTP_200_OK

    with_card = board["columns"][0]["id"]
    client.post(f"/api/v1/kanban/boards/{board['id']}/cards", json={"column_id": with_card, "title": "Nao apaga"}, headers=headers)
    blocked = client.delete(f"/api/v1/kanban/columns/{with_card}", headers=headers)
    assert blocked.status_code == status.HTTP_409_CONFLICT


def test_board_permissions_and_duplicate_board(client, db):
    headers, board = create_board(client)
    user = grant_module(db, "vesper_user", "READ_ONLY")
    permission = client.post(
        f"/api/v1/kanban/boards/{board['id']}/permissions",
        json={"user_id": user.id, "access_level": "READ_ONLY"},
        headers=headers,
    )
    assert permission.status_code == status.HTTP_200_OK
    listed = client.get(f"/api/v1/kanban/boards/{board['id']}/permissions", headers=headers)
    assert any(item["user_id"] == user.id for item in listed.json())

    duplicated = client.post(
        f"/api/v1/kanban/boards/{board['id']}/duplicate",
        json={"name": f"Copia {uuid.uuid4().hex[:6]}", "copy_cards": False},
        headers=headers,
    )
    assert duplicated.status_code == status.HTTP_200_OK
    assert duplicated.json()["access_level"] == "ADMIN"

    blocked_delete = client.delete(f"/api/v1/kanban/boards/{board['id']}", headers=headers)
    assert blocked_delete.status_code == status.HTTP_409_CONFLICT


def test_board_access_human_names_audit_and_scoped_lookup(client, db):
    headers, board = create_board(client)
    user = grant_module(db, "vesper_user", "READ_ONLY")
    role = db.query(Role).filter(Role.name == "MANAGER").first()
    permission = client.post(
        f"/api/v1/kanban/boards/{board['id']}/permissions",
        json={"user_id": user.id, "access_level": "READ_ONLY"},
        headers=headers,
    )
    assert permission.status_code == status.HTTP_200_OK
    assert permission.json()["username"] == "vesper_user"
    assert "user_email" in permission.json()

    updated = client.post(
        f"/api/v1/kanban/boards/{board['id']}/permissions",
        json={"user_id": user.id, "access_level": "NORMAL"},
        headers=headers,
    )
    assert updated.status_code == status.HTTP_200_OK
    assert updated.json()["access_level"] == "NORMAL"

    if role:
        role_permission = client.post(
            f"/api/v1/kanban/boards/{board['id']}/permissions",
            json={"role_id": role.id, "access_level": "READ_ONLY"},
            headers=headers,
        )
        assert role_permission.status_code == status.HTTP_200_OK
        assert role_permission.json()["role_name"] == role.name

    users_lookup = client.get(f"/api/v1/kanban/users?board_id={board['id']}&search=vesper", headers=headers)
    assert users_lookup.status_code == status.HTTP_200_OK
    assert all(item["username"] for item in users_lookup.json())

    user_headers = login(client, "vesper_user", "userpass")
    blocked_lookup = client.get(f"/api/v1/kanban/users?board_id={board['id']}&search=vesper", headers=user_headers)
    assert blocked_lookup.status_code == status.HTTP_403_FORBIDDEN

    admin_headers = login(client)
    delete_response = client.delete(f"/api/v1/kanban/boards/{board['id']}/permissions/{permission.json()['id']}", headers=admin_headers)
    assert delete_response.status_code == status.HTTP_200_OK
    assert db.query(AuditLog).filter(AuditLog.action == "kanban.board_access.granted").first() is not None
    assert db.query(AuditLog).filter(AuditLog.action == "kanban.board_access.updated").first() is not None
    assert db.query(AuditLog).filter(AuditLog.action == "kanban.board_access.removed").first() is not None


def test_import_csv_and_xlsx_preview_confirm(client):
    headers, board = create_board(client, preset="producao")
    csv_data = "OP,Titulo,Cliente\n9001,Card CSV,Cliente CSV\n"
    preview = client.post(
        f"/api/v1/kanban/boards/{board['id']}/import/preview",
        files={"upload": ("cards.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")},
        headers=headers,
    )
    assert preview.status_code == status.HTTP_200_OK
    confirm = client.post(
        f"/api/v1/kanban/boards/{board['id']}/import/confirm",
        json={"import_id": preview.json()["import_id"], "mapping": {"OP": "custom.op", "Titulo": "title", "Cliente": "custom.cliente"}, "duplicate_field": "op"},
        headers=headers,
    )
    assert confirm.status_code == status.HTTP_200_OK
    assert confirm.json()["created"] == 1

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["OP", "Titulo"])
    sheet.append(["9002", "Card XLSX"])
    stream = io.BytesIO()
    workbook.save(stream)
    stream.seek(0)
    xlsx_preview = client.post(
        f"/api/v1/kanban/boards/{board['id']}/import/preview",
        files={"upload": ("cards.xlsx", stream, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=headers,
    )
    assert xlsx_preview.status_code == status.HTTP_200_OK
    assert xlsx_preview.json()["total_rows"] == 1
