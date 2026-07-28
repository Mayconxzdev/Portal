import io

from fastapi import status

from app.core.security import get_password_hash
from app.models.kanban import KanbanActivity, KanbanBoardPermission, KanbanCardAttachment, KanbanCardComment
from app.models.module import Module
from app.models.role import Role
from app.models.user import User
from app.models.user_module_access import UserModuleAccess


def login(client, username, password):
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == status.HTTP_200_OK
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def login_token(client, username, password):
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == status.HTTP_200_OK
    return response.json()["access_token"]


def ensure_user(db, username="kanban_reviewer", password="reviewpass"):
    user = db.query(User).filter(User.username == username).first()
    if user:
        return user
    role = db.query(Role).filter(Role.name == "USER").first()
    module = db.query(Module).filter(Module.code == "kanban").first()
    user = User(
        username=username,
        email=f"{username}@portal.example",
        hashed_password=get_password_hash(password),
        is_active=True,
        role_id=role.id,
    )
    db.add(user)
    db.flush()
    db.add(UserModuleAccess(user_id=user.id, module_id=module.id, permission_level="NORMAL"))
    db.commit()
    return user


def create_board_card(client):
    headers = login(client, "vesper_admin", "admin")
    board_resp = client.post("/api/v1/kanban/boards", json={"name": "Avancado", "slug": "avancado"}, headers=headers)
    assert board_resp.status_code == status.HTTP_201_CREATED
    board = board_resp.json()
    card_resp = client.post(
        f"/api/v1/kanban/boards/{board['id']}/cards",
        json={"column_id": board["columns"][0]["id"], "title": "Card avancado", "priority": "HIGH"},
        headers=headers,
    )
    assert card_resp.status_code == status.HTTP_201_CREATED
    return headers, board, card_resp.json()


def test_drag_payload_aliases_and_cross_board_block(client):
    headers, board, card = create_board_card(client)
    move = client.post(
        f"/api/v1/kanban/cards/{card['id']}/move",
        json={"to_column_id": board["columns"][1]["id"], "new_position": 0},
        headers=headers,
    )
    assert move.status_code == status.HTTP_200_OK
    assert move.json()["column_id"] == board["columns"][1]["id"]

    other_board = client.post("/api/v1/kanban/boards", json={"name": "Outro", "slug": "outro"}, headers=headers).json()
    blocked = client.post(
        f"/api/v1/kanban/cards/{card['id']}/move",
        json={"to_column_id": other_board["columns"][0]["id"], "new_position": 0},
        headers=headers,
    )
    assert blocked.status_code == status.HTTP_400_BAD_REQUEST


def test_checklist_comment_label_assignee_and_search(client, db):
    headers, board, card = create_board_card(client)
    reviewer = ensure_user(db)
    db.add(KanbanBoardPermission(board_id=board["id"], user_id=reviewer.id, access_level="NORMAL"))
    db.commit()

    checklist = client.post(f"/api/v1/kanban/cards/{card['id']}/checklists", json={"title": "Entrega"}, headers=headers)
    assert checklist.status_code == status.HTTP_201_CREATED
    item = client.post(f"/api/v1/kanban/checklists/{checklist.json()['id']}/items", json={"text": "Conferir pedido"}, headers=headers)
    assert item.status_code == status.HTTP_201_CREATED
    checked = client.patch(f"/api/v1/kanban/checklist-items/{item.json()['id']}", json={"is_done": True}, headers=headers)
    assert checked.status_code == status.HTTP_200_OK
    unchecked = client.patch(f"/api/v1/kanban/checklist-items/{item.json()['id']}", json={"is_done": False}, headers=headers)
    assert unchecked.status_code == status.HTTP_200_OK

    comment = client.post(f"/api/v1/kanban/cards/{card['id']}/comments", json={"comment": "Primeiro comentario"}, headers=headers)
    assert comment.status_code == status.HTTP_201_CREATED
    reviewer_headers = login(client, "kanban_reviewer", "reviewpass")
    blocked = client.patch(f"/api/v1/kanban/card-comments/{comment.json()['id']}", json={"comment": "Nao pode"}, headers=reviewer_headers)
    assert blocked.status_code == status.HTTP_403_FORBIDDEN
    client.cookies.clear()
    moderated = client.patch(f"/api/v1/kanban/card-comments/{comment.json()['id']}", json={"comment": "Moderado"}, headers=headers)
    assert moderated.status_code == status.HTTP_200_OK, moderated.text
    deleted = client.delete(f"/api/v1/kanban/card-comments/{comment.json()['id']}", headers=headers)
    assert deleted.status_code == status.HTTP_200_OK
    assert db.query(KanbanCardComment).filter(KanbanCardComment.id == comment.json()["id"]).first().deleted_at is not None

    label = client.post(f"/api/v1/kanban/boards/{board['id']}/labels", json={"name": "Urgente", "color": "#ef4444"}, headers=headers)
    assert label.status_code == status.HTTP_201_CREATED
    applied = client.post(f"/api/v1/kanban/cards/{card['id']}/labels/{label.json()['id']}", headers=headers)
    assert applied.status_code == status.HTTP_200_OK
    assert applied.json()["labels"][0]["name"] == "Urgente"

    assigned = client.post(f"/api/v1/kanban/cards/{card['id']}/assignees/{reviewer.id}", headers=headers)
    assert assigned.status_code == status.HTTP_200_OK
    assert assigned.json()["assigned_to_user_id"] == reviewer.id

    search = client.get(f"/api/v1/kanban/boards/{board['id']}/cards/search?priority=HIGH&label_id={label.json()['id']}&assigned_to_me=true", headers=reviewer_headers)
    assert search.status_code == status.HTTP_200_OK
    assert len(search.json()) == 1

    assert db.query(KanbanActivity).filter(KanbanActivity.action == "checklist_item.checked").first() is not None


def test_attachments_validation_download_and_remove(client, db):
    headers, _, card = create_board_card(client)
    upload = client.post(
        f"/api/v1/kanban/cards/{card['id']}/attachments",
        files={"upload": ("nota.txt", io.BytesIO(b"conteudo"), "text/plain")},
        headers=headers,
    )
    assert upload.status_code == status.HTTP_201_CREATED
    attachment_id = upload.json()["id"]

    download = client.get(f"/api/v1/kanban/card-attachments/{attachment_id}/download", headers=headers)
    assert download.status_code == status.HTTP_200_OK
    assert download.content == b"conteudo"

    bad_ext = client.post(
        f"/api/v1/kanban/cards/{card['id']}/attachments",
        files={"upload": ("script.exe", io.BytesIO(b"x"), "application/octet-stream")},
        headers=headers,
    )
    assert bad_ext.status_code == status.HTTP_400_BAD_REQUEST

    too_large = client.post(
        f"/api/v1/kanban/cards/{card['id']}/attachments",
        files={"upload": ("grande.txt", io.BytesIO(b"x" * (10 * 1024 * 1024 + 1)), "text/plain")},
        headers=headers,
    )
    assert too_large.status_code == status.HTTP_400_BAD_REQUEST

    removed = client.delete(f"/api/v1/kanban/card-attachments/{attachment_id}", headers=headers)
    assert removed.status_code == status.HTTP_200_OK
    assert db.query(KanbanCardAttachment).filter(KanbanCardAttachment.id == attachment_id).first().deleted_at is not None


def test_kanban_websocket_requires_auth_and_accepts_authorized_board(client):
    headers, board, _ = create_board_card(client)
    try:
        with client.websocket_connect(f"/api/v1/ws/kanban?board_id={board['id']}"):
            raise AssertionError("websocket sem token nao deveria conectar")
    except Exception:
        pass

    token = headers["Authorization"].replace("Bearer ", "")
    with client.websocket_connect(f"/api/v1/ws/kanban?board_id={board['id']}&token={token}") as websocket:
        websocket.send_text("ping")
        assert websocket.receive_text() == "pong"
