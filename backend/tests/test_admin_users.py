from fastapi import status
from app.models.user import User
from app.models.audit_log import AuditLog


def _login_admin(client):
    response = client.post("/api/v1/auth/login", json={"username": "vesper_admin", "password": "admin"})
    assert response.status_code == status.HTTP_200_OK


def test_admin_create_user_duplicate_email_has_human_message(client):
    _login_admin(client)

    response = client.post(
        "/api/v1/admin/users",
        json={
            "username": "novo.usuario",
            "email": "user@portal.example",
            "password": "senha123",
            "role_id": 2,
            "is_active": True,
            "module_permissions": [],
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Este e-mail ja esta cadastrado."
    assert "[object Object]" not in response.text


def test_admin_create_user_without_email_and_short_password_is_allowed(client):
    _login_admin(client)

    response = client.post(
        "/api/v1/admin/users",
        json={
            "username": "senha.curta",
            "full_name": "Usuario Senha Curta",
            "department": "Administracao",
            "job_title": "Assistente",
            "password": "123",
            "role_id": 2,
            "is_active": True,
            "must_change_password": True,
            "module_permissions": [],
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert "[object Object]" not in response.text
    data = response.json()
    assert data["email"] is None
    assert data["full_name"] == "Usuario Senha Curta"
    assert data["department"] == "Administracao"
    assert data["job_title"] == "Assistente"
    assert data["must_change_password"] is True


def test_admin_create_user_rejects_blank_password(client):
    _login_admin(client)

    response = client.post(
        "/api/v1/admin/users",
        json={
            "username": "senha.vazia",
            "full_name": "Usuario Sem Senha",
            "department": "TI",
            "password": "   ",
            "role_id": 2,
            "is_active": True,
            "module_permissions": [],
        },
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "senha temporaria" in response.text


def test_admin_create_user_stores_password_hash(client, db):
    _login_admin(client)

    response = client.post(
        "/api/v1/admin/users",
        json={
            "username": "hash.seguro",
            "full_name": "Usuario Hash Seguro",
            "department": "Compras",
            "password": "123",
            "role_id": 2,
            "is_active": True,
            "module_permissions": [],
        },
    )

    assert response.status_code == status.HTTP_200_OK
    user = db.query(User).filter(User.username == "hash.seguro").first()
    assert user is not None
    assert user.hashed_password != "123"
    assert user.hashed_password


def test_admin_update_password_is_write_only_and_audited_without_secret(client, db):
    _login_admin(client)

    create_response = client.post(
        "/api/v1/admin/users",
        json={
            "username": "senha.writeonly",
            "full_name": "Usuario Senha Write Only",
            "password": "senha-inicial",
            "role_id": 2,
            "is_active": True,
            "must_change_password": True,
            "module_permissions": [],
        },
    )
    assert create_response.status_code == status.HTTP_200_OK
    user_id = create_response.json()["id"]
    user = db.query(User).filter(User.id == user_id).first()
    assert user is not None
    initial_hash = user.hashed_password

    update_response = client.patch(
        f"/api/v1/admin/users/{user_id}",
        json={"password": "nova-senha-123", "must_change_password": True},
    )
    assert update_response.status_code == status.HTTP_200_OK
    response_text = update_response.text.lower()
    assert '"password"' not in response_text
    assert "plain_password" not in response_text
    assert "current_password" not in response_text
    assert "hashed_password" not in response_text
    assert "nova-senha-123" not in response_text
    assert "senha-inicial" not in response_text

    db.refresh(user)
    assert user.hashed_password != initial_hash
    assert user.hashed_password != "nova-senha-123"

    old_login = client.post("/api/v1/auth/login", json={"username": "senha.writeonly", "password": "senha-inicial"})
    assert old_login.status_code == status.HTTP_401_UNAUTHORIZED
    new_login = client.post("/api/v1/auth/login", json={"username": "senha.writeonly", "password": "nova-senha-123"})
    assert new_login.status_code == status.HTTP_200_OK

    audit = (
        db.query(AuditLog)
        .filter(AuditLog.module == "admin", AuditLog.action == "UPDATE_USER")
        .order_by(AuditLog.created_at.desc())
        .first()
    )
    assert audit is not None
    audit_text = str(audit.details).lower()
    assert "nova-senha-123" not in audit_text
    assert "senha-inicial" not in audit_text
    assert "hashed_password" not in audit_text


def test_admin_delete_user_success(client, db):
    _login_admin(client)
    
    res_create = client.post(
        "/api/v1/admin/users",
        json={
            "username": "usuario.deletavel",
            "email": "deletavel@portal.example",
            "password": "senha123",
            "role_id": 2,
            "is_active": True,
            "module_permissions": [],
        },
    )
    assert res_create.status_code == 200
    user_id = res_create.json()["id"]
    
    res_delete = client.delete(f"/api/v1/admin/users/{user_id}")
    assert res_delete.status_code == 204
    
    assert db.query(User).filter(User.id == user_id).first() is None


def test_admin_delete_self_fails(client, db):
    _login_admin(client)
    
    admin_user = db.query(User).filter(User.username == "vesper_admin").first()
    assert admin_user is not None
    
    response = client.delete(f"/api/v1/admin/users/{admin_user.id}")
    assert response.status_code == 400
    assert "sua propria conta" in response.json()["detail"]


def test_admin_delete_messias_fails(client, db):
    _login_admin(client)
    
    messias_user = db.query(User).filter(User.username == "MESSIAS").first()
    if not messias_user:
        from app.models.role import Role
        user_role = db.query(Role).filter(Role.id == 2).first()
        messias_user = User(
            username="MESSIAS",
            email="messias@portal.example",
            hashed_password="...",
            role_id=user_role.id if user_role else None
        )
        db.add(messias_user)
        db.commit()
        db.refresh(messias_user)
        
    response = client.delete(f"/api/v1/admin/users/{messias_user.id}")
    assert response.status_code == 400
    assert "super-usuario MESSIAS" in response.json()["detail"]
