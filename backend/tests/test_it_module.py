from io import BytesIO

from fastapi import status

from app.models.audit_log import AuditLog
from app.models.it import ITCredential, ITTicket
from app.models.module import Module
from app.models.user import User
from app.models.user_module_access import UserModuleAccess


def login(client, username, password):
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == status.HTTP_200_OK
    return response.json()["access_token"]


def grant_module(db, username, module_code="it", level="MANAGER"):
    user = db.query(User).filter(User.username == username).first()
    module = db.query(Module).filter(Module.code == module_code).first()
    access = db.query(UserModuleAccess).filter(UserModuleAccess.user_id == user.id, UserModuleAccess.module_id == module.id).first()
    if access:
        access.permission_level = level
    else:
        db.add(UserModuleAccess(user_id=user.id, module_id=module.id, permission_level=level))
    db.commit()
    return user


def test_common_user_can_create_ticket_without_it_module_access_and_priority_is_media(client, db):
    token = login(client, "vesper_user", "userpass")
    response = client.post(
        "/api/v1/it/tickets",
        json={
            "title": "Computador sem internet",
            "description": "A internet parou no meu computador.",
            "category": "INTERNET_REDE",
            "priority": "CRITICA",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["ticket_number"].startswith("TI-")
    assert data["priority"] == "MEDIA"
    assert db.query(ITTicket).filter(ITTicket.ticket_number == data["ticket_number"]).first() is not None


def test_common_user_does_not_see_internal_comment(client, db):
    user_token = login(client, "vesper_user", "userpass")
    user_headers = {"Authorization": f"Bearer {user_token}"}
    ticket = client.post(
        "/api/v1/it/tickets",
        json={"title": "Erro no e-mail", "description": "Nao consigo abrir.", "category": "EMAIL"},
        headers=user_headers,
    ).json()

    admin_token = login(client, "vesper_admin", "admin")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    internal = client.post(
        f"/api/v1/it/tickets/{ticket['id']}/comments",
        json={"comment": "Comentario tecnico interno", "is_internal": True},
        headers=admin_headers,
    )
    assert internal.status_code == status.HTTP_201_CREATED

    public = client.post(
        f"/api/v1/it/tickets/{ticket['id']}/comments",
        json={"comment": "Atualizacao publica", "is_internal": False},
        headers=admin_headers,
    )
    assert public.status_code == status.HTTP_201_CREATED

    response = client.get(f"/api/v1/it/tickets/{ticket['id']}/comments", headers=user_headers)
    assert response.status_code == status.HTTP_200_OK
    comments = response.json()
    assert len(comments) == 1
    assert comments[0]["comment"] == "Atualizacao publica"


def test_time_log_blocks_duplicate_timer(client, db):
    token = login(client, "vesper_admin", "admin")
    headers = {"Authorization": f"Bearer {token}"}
    ticket = client.post(
        "/api/v1/it/tickets",
        json={"title": "Notebook lento", "description": "Travando muito.", "category": "COMPUTADOR"},
        headers=headers,
    ).json()

    first = client.post(f"/api/v1/it/tickets/{ticket['id']}/time/start", headers=headers)
    assert first.status_code == status.HTTP_200_OK
    duplicate = client.post(f"/api/v1/it/tickets/{ticket['id']}/time/start", headers=headers)
    assert duplicate.status_code == status.HTTP_400_BAD_REQUEST

    stopped = client.post(f"/api/v1/it/tickets/{ticket['id']}/time/stop", json={"note": "Teste"}, headers=headers)
    assert stopped.status_code == status.HTTP_200_OK
    assert stopped.json()["duration_seconds"] >= 0


def test_attachment_upload_blocks_dangerous_extension(client, db):
    token = login(client, "vesper_user", "userpass")
    headers = {"Authorization": f"Bearer {token}"}
    ticket = client.post(
        "/api/v1/it/tickets",
        json={"title": "Print do erro", "description": "Segue anexo.", "category": "SISTEMA_SOFTWARE"},
        headers=headers,
    ).json()

    ok = client.post(
        f"/api/v1/it/tickets/{ticket['id']}/attachments",
        files={"upload": ("erro.png", BytesIO(b"fake image"), "image/png")},
        headers=headers,
    )
    assert ok.status_code == status.HTTP_201_CREATED

    blocked = client.post(
        f"/api/v1/it/tickets/{ticket['id']}/attachments",
        files={"upload": ("virus.exe", BytesIO(b"bad"), "application/octet-stream")},
        headers=headers,
    )
    assert blocked.status_code == status.HTTP_400_BAD_REQUEST


def test_credential_vault_encrypts_and_does_not_return_secret_in_list(client, db):
    token = login(client, "vesper_admin", "admin")
    headers = {"Authorization": f"Bearer {token}"}
    create = client.post(
        "/api/v1/it/credentials",
        json={"title": "Roteador laboratorio", "system_name": "Rede", "username": "admin", "secret": "senha_fake_dev"},
        headers=headers,
    )
    assert create.status_code == status.HTTP_201_CREATED
    assert "secret" not in create.json()

    row = db.query(ITCredential).filter(ITCredential.title == "Roteador laboratorio").first()
    assert row is not None
    assert "senha_fake_dev" not in row.secret_encrypted

    listed = client.get("/api/v1/it/credentials", headers=headers)
    assert listed.status_code == status.HTTP_200_OK
    assert "secret" not in listed.json()[0]

    revealed = client.post(f"/api/v1/it/credentials/{row.id}/reveal", headers=headers)
    assert revealed.status_code == status.HTTP_200_OK
    assert revealed.json()["secret"] == "senha_fake_dev"
    audit = db.query(AuditLog).filter(AuditLog.action == "it.credential.revealed").first()
    assert audit is not None
    assert "senha_fake_dev" not in str(audit.details)


def test_ticket_queue_filters_and_reports_are_staff_only(client, db):
    admin_token = login(client, "vesper_admin", "admin")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    user_token = login(client, "vesper_user", "userpass")
    user_headers = {"Authorization": f"Bearer {user_token}"}

    first = client.post(
        "/api/v1/it/tickets",
        json={"title": "Impressora sem toner", "description": "Trocar toner.", "category": "IMPRESSORA"},
        headers=admin_headers,
    ).json()
    second = client.post(
        "/api/v1/it/tickets",
        json={"title": "Certificado vencendo", "description": "Renovar certificado.", "category": "CERTIFICADO"},
        headers=admin_headers,
    ).json()
    client.post(f"/api/v1/it/tickets/{second['id']}/priority", json={"priority": "CRITICA"}, headers=admin_headers)
    client.post(f"/api/v1/it/tickets/{second['id']}/assign", json={}, headers=admin_headers)

    filtered = client.get("/api/v1/it/tickets?category=CERTIFICADO&priority=CRITICA&assigned_to_me=true", headers=admin_headers)
    assert filtered.status_code == status.HTTP_200_OK
    assert [row["id"] for row in filtered.json()] == [second["id"]]

    by_number = client.get(f"/api/v1/it/tickets?ticket_number={first['ticket_number']}", headers=admin_headers)
    assert by_number.status_code == status.HTTP_200_OK
    assert any(row["id"] == first["id"] for row in by_number.json())

    denied = client.get("/api/v1/it/reports/summary", headers=user_headers)
    assert denied.status_code == status.HTTP_403_FORBIDDEN

    report = client.get("/api/v1/it/reports/tickets-by-category", headers=admin_headers)
    assert report.status_code == status.HTTP_200_OK
    categories = {row["category"]: row["count"] for row in report.json()}
    assert categories["CERTIFICADO"] >= 1


def test_it_event_payload_does_not_include_internal_comment_or_secret(client, db, monkeypatch):
    from app.modules.it import events

    sent_payloads = []

    def fake_schedule(user_id, payload):
        sent_payloads.append(payload)

    monkeypatch.setattr(events, "_schedule_send", fake_schedule)
    monkeypatch.setattr("app.modules.it.service.emit_it_event", events.emit_it_event)

    user_token = login(client, "vesper_user", "userpass")
    user_headers = {"Authorization": f"Bearer {user_token}"}
    ticket = client.post(
        "/api/v1/it/tickets",
        json={"title": "Sistema com erro", "description": "Erro ao salvar.", "category": "SISTEMA_SOFTWARE"},
        headers=user_headers,
    ).json()

    admin_token = login(client, "vesper_admin", "admin")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.post(
        f"/api/v1/it/tickets/{ticket['id']}/comments",
        json={"comment": "Senha fake: segredo-nao-pode-vazar", "is_internal": True},
        headers=admin_headers,
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert sent_payloads
    payload_text = str(sent_payloads[-1])
    assert "segredo-nao-pode-vazar" not in payload_text
    assert "Senha fake" not in payload_text
