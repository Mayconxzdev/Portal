from datetime import datetime, timedelta, timezone

from fastapi import status

from app.models.admin_lifecycle import UserSession, UserTemporaryAccess
from app.models.user import User


def _login(client, username: str, password: str) -> str:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == status.HTTP_200_OK
    return response.json()["access_token"]


def _login_admin(client) -> str:
    return _login(client, "vesper_admin", "admin")


def test_admin_can_revoke_user_session_and_token_stops_working(client, db):
    user_token = _login(client, "vesper_user", "userpass")
    client.cookies.clear()
    _login_admin(client)

    user = db.query(User).filter(User.username == "vesper_user").first()
    response = client.get(f"/api/v1/admin/users/{user.id}/sessions")
    assert response.status_code == status.HTTP_200_OK
    sessions = response.json()
    assert len(sessions) == 1
    assert sessions[0]["is_active"] is True

    revoke = client.post(
        f"/api/v1/admin/users/{user.id}/sessions/{sessions[0]['id']}/revoke",
        json={"reason": "Teste de revogacao"},
    )
    assert revoke.status_code == status.HTTP_200_OK
    assert revoke.json()["is_active"] is False

    client.cookies.clear()
    blocked = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {user_token}"})
    assert blocked.status_code == status.HTTP_401_UNAUTHORIZED


def test_temporary_access_grants_and_revokes_module_permission(client, db):
    _login_admin(client)
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()

    create = client.post(
        "/api/v1/admin/users/2/temporary-access",
        json={
            "module_id": 2,
            "permission_level": "NORMAL",
            "reason": "Cobertura temporaria de teste",
            "expires_at": expires_at,
        },
    )
    assert create.status_code == status.HTTP_200_OK
    access = create.json()
    assert access["is_effective"] is True
    assert access["module_code"] == "kanban"

    client.cookies.clear()
    _login(client, "vesper_user", "userpass")
    allowed = client.get("/api/v1/kanban")
    assert allowed.status_code == status.HTTP_200_OK

    client.cookies.clear()
    _login_admin(client)
    revoke = client.post(
        f"/api/v1/admin/users/2/temporary-access/{access['id']}/revoke",
        json={"reason": "Fim da cobertura"},
    )
    assert revoke.status_code == status.HTTP_200_OK
    assert revoke.json()["status"] == "REVOKED"

    client.cookies.clear()
    _login(client, "vesper_user", "userpass")
    blocked = client.get("/api/v1/kanban")
    assert blocked.status_code == status.HTTP_403_FORBIDDEN


def test_offboarding_confirms_disable_user_and_revoke_active_records(client, db):
    user_token = _login(client, "vesper_user", "userpass")
    client.cookies.clear()
    _login_admin(client)

    expires_at = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    access_response = client.post(
        "/api/v1/admin/users/2/temporary-access",
        json={
            "module_id": 1,
            "permission_level": "NORMAL",
            "reason": "Acesso temporario antes do desligamento",
            "expires_at": expires_at,
        },
    )
    assert access_response.status_code == status.HTTP_200_OK

    impact = client.get("/api/v1/admin/users/2/offboarding/impact")
    assert impact.status_code == status.HTTP_200_OK
    assert any(item["key"] == "sessions" and item["count"] >= 1 for item in impact.json()["items"])

    created = client.post(
        "/api/v1/admin/users/2/offboarding",
        json={"reason": "Desligamento de teste"},
    )
    assert created.status_code == status.HTTP_200_OK
    case_id = created.json()["id"]

    confirmed = client.post(f"/api/v1/admin/offboarding/{case_id}/confirm")
    assert confirmed.status_code == status.HTTP_200_OK
    counts = confirmed.json()["applied_counts"]
    assert counts["sessions_revoked"] >= 1
    assert counts["temporary_access_revoked"] >= 1

    user = db.query(User).filter(User.id == 2).first()
    assert user.is_active is False
    assert db.query(UserSession).filter(UserSession.user_id == 2, UserSession.revoked_at.is_(None)).count() == 0
    assert db.query(UserTemporaryAccess).filter(
        UserTemporaryAccess.target_user_id == 2,
        UserTemporaryAccess.status == "ACTIVE",
    ).count() == 0

    client.cookies.clear()
    blocked = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {user_token}"})
    assert blocked.status_code in {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN}


def test_deactivating_user_via_patch_revokes_sessions_and_temp_access(client, db):
    user_token = _login(client, "vesper_user", "userpass")
    client.cookies.clear()
    _login_admin(client)

    expires_at = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    client.post(
        "/api/v1/admin/users/2/temporary-access",
        json={
            "module_id": 1,
            "permission_level": "NORMAL",
            "reason": "Acesso temporario de teste",
            "expires_at": expires_at,
        },
    )

    response = client.patch(
        "/api/v1/admin/users/2",
        json={"is_active": False}
    )
    assert response.status_code == status.HTTP_200_OK

    assert db.query(UserSession).filter(UserSession.user_id == 2, UserSession.revoked_at.is_(None)).count() == 0
    assert db.query(UserTemporaryAccess).filter(
        UserTemporaryAccess.target_user_id == 2,
        UserTemporaryAccess.status == "ACTIVE",
    ).count() == 0

    client.cookies.clear()
    blocked = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {user_token}"})
    assert blocked.status_code in {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN}


def test_sweep_expires_temporary_access_and_substitution(client, db):
    _login_admin(client)
    expired_time = (datetime.now(timezone.utc) - timedelta(hours=1))
    
    from app.models.admin_lifecycle import UserTemporaryAccess, UserTemporarySubstitution
    access = UserTemporaryAccess(
        target_user_id=2,
        module_id=1,
        permission_level="NORMAL",
        reason="Acesso vencido",
        starts_at=expired_time - timedelta(hours=2),
        expires_at=expired_time,
        status="ACTIVE",
        created_by_user_id=1,
    )
    db.add(access)
    
    sub = UserTemporarySubstitution(
        replaced_user_id=1,
        substitute_user_id=2,
        reason="Substituicao vencida",
        starts_at=expired_time - timedelta(hours=2),
        expires_at=expired_time,
        status="ACTIVE",
        created_by_user_id=1,
    )
    db.add(sub)
    db.commit()
    
    sweep = client.post("/api/v1/admin/temporary-access/sweep")
    assert sweep.status_code == status.HTTP_200_OK
    data = sweep.json()
    assert data["applied_counts"]["expired_accesses"] >= 1
    assert data["applied_counts"]["expired_substitutions"] >= 1
    
    db.refresh(access)
    db.refresh(sub)
    assert access.status == "EXPIRED"
    assert sub.status == "EXPIRED"


def test_offboarding_task_management_and_cancel(client, db):
    _login_admin(client)
    
    created = client.post(
        "/api/v1/admin/users/2/offboarding",
        json={"reason": "Desligamento para teste de tarefas"},
    )
    assert created.status_code == status.HTTP_200_OK
    case = created.json()
    assert case["status"] == "DRAFT"
    
    if case["tasks"]:
        task_id = case["tasks"][0]["id"]
        res = client.post(f"/api/v1/admin/offboarding/tasks/{task_id}/complete")
        assert res.status_code == status.HTTP_200_OK
        assert res.json()["task_status"] == "COMPLETED"
        
        res_fail = client.post(f"/api/v1/admin/offboarding/tasks/{task_id}/fail")
        assert res_fail.status_code == status.HTTP_200_OK
        assert res_fail.json()["task_status"] == "FAILED"
        
    res_cancel = client.post(f"/api/v1/admin/offboarding/{case['id']}/cancel")
    assert res_cancel.status_code == status.HTTP_200_OK
    assert res_cancel.json()["case_status"] == "CANCELLED"

