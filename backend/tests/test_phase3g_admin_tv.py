from fastapi import status

from app.models.audit_log import AuditLog
from app.models.kanban import KanbanBoardPermission
from app.models.module import Module
from app.models.user import User
from app.models.user_module_access import UserModuleAccess


def login(client, username="vesper_admin", password="admin"):
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


def create_board(client, name="Fase 3G"):
    headers = login(client)
    response = client.post("/api/v1/kanban/boards", json={"name": name, "slug": name.lower().replace(" ", "-")}, headers=headers)
    assert response.status_code == status.HTTP_201_CREATED
    return response.json(), headers


def test_admin_bulk_board_permissions_and_audit(client, db):
    board, headers = create_board(client)
    user = grant_module(db, "vesper_user", "READ_ONLY")

    users = client.get("/api/v1/admin/users/search?q=vesper", headers=headers)
    assert users.status_code == status.HTTP_200_OK
    assert any(item["username"] == "vesper_user" for item in users.json())

    boards = client.get("/api/v1/admin/kanban/boards", headers=headers)
    assert boards.status_code == status.HTTP_200_OK
    assert any(item["id"] == board["id"] for item in boards.json())

    saved = client.put(
        "/api/v1/admin/kanban/board-permissions/bulk",
        json={"user_id": user.id, "permissions": [{"board_id": board["id"], "access_level": "READ_ONLY"}]},
        headers=headers,
    )
    assert saved.status_code == status.HTTP_200_OK
    assert any(item["board_id"] == board["id"] and item["access_level"] == "READ_ONLY" for item in saved.json()["permissions"])
    assert db.query(AuditLog).filter(AuditLog.action.in_(["admin.kanban_access.granted", "admin.kanban_access.bulk_updated"])).first() is not None

    matrix = client.get(f"/api/v1/admin/kanban/board-permissions?user_id={user.id}", headers=headers)
    assert matrix.status_code == status.HTTP_200_OK
    assert matrix.json()["username"] == "vesper_user"


def test_board_permission_management_is_not_available_to_non_admin_manager(client, db):
    board, headers = create_board(client)
    user = grant_module(db, "vesper_user", "MANAGER")
    db.add(KanbanBoardPermission(board_id=board["id"], user_id=user.id, access_level="MANAGER"))
    db.commit()
    user_headers = login(client, "vesper_user", "userpass")
    blocked = client.post(
        f"/api/v1/kanban/boards/{board['id']}/permissions",
        json={"user_id": user.id, "access_level": "READ_ONLY"},
        headers=user_headers,
    )
    assert blocked.status_code == status.HTTP_403_FORBIDDEN


def test_tv_config_extended_options_are_persisted_and_returned(client):
    board, headers = create_board(client, "TV 3G")
    payload = {
        "layout_type": "PRODUCTION_LIST",
        "display_options": {"show_clock": False, "show_board_name": False, "show_exit_button": False},
        "kpi_options": {"show_kpis": False, "visible": []},
        "layout_options": {"visible_rows": 16, "density": "factory", "font_scale": "large", "show_ranking": False},
        "external_mode_options": {"layout_type": "PRODUCTION_LIST", "display_options": {"show_clock": False}},
    }
    response = client.patch(f"/api/v1/kanban/boards/{board['id']}/tv-config", json=payload, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["display_options"]["show_clock"] is False
    assert response.json()["layout_options"]["visible_rows"] == 16

    tv_data = client.get(f"/api/v1/kanban/boards/{board['id']}/tv-data", headers=headers)
    assert tv_data.status_code == status.HTTP_200_OK
    assert tv_data.json()["config"]["kpi_options"]["show_kpis"] is False
