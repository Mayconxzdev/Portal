from fastapi import status

# 1. Testes de Healthcheck
def test_simple_health(client):
    """
    Testa o endpoint de liveness probe raiz /health.
    """
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "online"
    assert "service" in data

def test_security_headers_are_applied(client):
    """
    Garante headers basicos de hardening nas respostas HTTP da API.
    """
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]

def test_advanced_health(client):
    """
    Testa o endpoint de readiness probe /api/v1/health.
    """
    response = client.get("/api/v1/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] in ["online", "degraded"]
    assert "services" in data
    assert data["services"]["api"] == "online"
    assert "postgres" in data["services"]

# 2. Testes de Login
def test_login_valid_admin(client):
    """
    Testa a autenticação com credenciais válidas do usuário vesper_admin.
    """
    login_data = {
        "username": "vesper_admin",
        "password": "admin"
    }
    response = client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "success"
    assert "access_token" in data
    assert data["user"]["username"] == "vesper_admin"
    assert data["user"]["role"] == "ADMIN"
    
    # Verifica se o cookie HttpOnly 'access_token' foi definido
    assert "access_token" in client.cookies

def test_login_valid_user(client):
    """
    Testa a autenticação com credenciais válidas de um usuário comum (vesper_user).
    """
    login_data = {
        "username": "vesper_user",
        "password": "userpass"
    }
    response = client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "success"
    assert data["user"]["username"] == "vesper_user"
    assert data["user"]["role"] == "USER"
    # O dashboard deve estar NORMAL, e o admin NO_ACCESS
    assert data["user"]["module_permissions"]["dashboard"] == "NORMAL"
    assert data["user"]["module_permissions"]["admin"] == "NO_ACCESS"

def test_login_invalid_credentials(client):
    """
    Testa falha de login com credenciais incorretas.
    """
    login_data = {
        "username": "vesper_admin",
        "password": "wrong_password"
    }
    response = client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "detail" in response.json()

def test_login_rate_limit_blocks_repeated_failures(client):
    """
    Bloqueia repetidas tentativas invalidas por par IP/usuario.
    """
    login_data = {
        "username": "rate_limit_probe",
        "password": "wrong_password"
    }
    for _ in range(5):
        response = client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    blocked = client.post("/api/v1/auth/login", json=login_data)
    assert blocked.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert "Muitas tentativas" in blocked.json()["detail"]

def test_login_inactive_user(client):
    """
    Testa bloqueio de login para usuário desativado.
    """
    login_data = {
        "username": "vesper_inactive",
        "password": "inactivepass"
    }
    response = client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "Contate o administrador" in response.json()["detail"]

# 3. Testes de Perfil (/auth/me)
def test_get_me_unauthenticated(client):
    """
    Testa o bloqueio ao endpoint /auth/me se o usuário não estiver autenticado.
    """
    response = client.get("/api/v1/auth/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_get_me_authenticated(client):
    """
    Testa o endpoint /auth/me após uma autenticação bem-sucedida (usando cookies automáticos).
    """
    # Efetua login
    login_response = client.post("/api/v1/auth/login", json={
        "username": "vesper_user",
        "password": "userpass"
    })
    assert login_response.status_code == status.HTTP_200_OK
    
    # Faz requisição para o endpoint /me. O TestClient enviará os cookies salvos automaticamente.
    response = client.get("/api/v1/auth/me")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["username"] == "vesper_user"
    assert data["role"] == "USER"
    assert data["module_permissions"]["dashboard"] == "NORMAL"

def test_get_me_bearer_token(client):
    """
    Testa a autenticação usando o cabeçalho Authorization Bearer Token (importante para Tauri/n8n).
    """
    # 1. Limpa cookies para garantir que a autenticação virá unicamente do Header
    client.cookies.clear()
    
    # 2. Loga para conseguir o token
    login_response = client.post("/api/v1/auth/login", json={
        "username": "vesper_user",
        "password": "userpass"
    })
    token = login_response.json()["access_token"]
    
    # 3. Limpa os cookies que o TestClient armazena automaticamente
    client.cookies.clear()
    
    # 4. Tenta acessar com header
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["username"] == "vesper_user"

# 4. Testes de Permissões de Módulo e Rotas Protegidas
def test_module_access_granted(client):
    """
    Testa o acesso permitido a um módulo em que o usuário possui a permissão necessária.
    No conftest, vesper_user possui acesso NORMAL ao modulo dashboard.
    """
    client.post("/api/v1/auth/login", json={
        "username": "vesper_user",
        "password": "userpass"
    })
    
    # Tenta acessar o dashboard summary (requer NORMAL ou superior em dashboard)
    response = client.get("/api/v1/dashboard/summary")
    # O endpoint dashboard/summary pode retornar um status ok
    assert response.status_code == status.HTTP_200_OK

def test_module_access_denied(client):
    """
    Testa se o backend barra acessos a módulos em que o usuário tem NO_ACCESS.
    O vesper_user possui NO_ACCESS ao módulo kanban e admin.
    """
    client.post("/api/v1/auth/login", json={
        "username": "vesper_user",
        "password": "userpass"
    })
    
    # Tenta acessar o kanban (deve dar erro 403 Forbidden se houver rota protegida)
    # Como as rotas específicas dependem do check_module_access, vamos chamar o endpoint raiz do kanban
    # Se a rota der 403, validamos a segurança.
    response = client.get("/api/v1/kanban")
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "Acesso negado ao módulo" in response.json()["detail"]

# 5. Testes de Administração Geral
def test_admin_list_users_allowed(client):
    """
    Testa se um administrador consegue listar os usuários em /api/v1/admin/users.
    """
    client.post("/api/v1/auth/login", json={
        "username": "vesper_admin",
        "password": "admin"
    })
    
    response = client.get("/api/v1/admin/users")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 3 # Deve listar pelo menos os 3 usuários criados no conftest

def test_admin_list_users_denied_to_user(client):
    """
    Testa se um usuário comum é impedido de acessar endpoints administrativos.
    """
    client.post("/api/v1/auth/login", json={
        "username": "vesper_user",
        "password": "userpass"
    })
    
    response = client.get("/api/v1/admin/users")
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "recurso restrito a administradores" in response.json()["detail"].lower()

def test_admin_logout(client):
    """
    Testa o fluxo de logout, limpando cookies e encerrando a sessão.
    """
    # Loga
    client.post("/api/v1/auth/login", json={
        "username": "vesper_user",
        "password": "userpass"
    })
    
    # Verifica que está logado
    assert "access_token" in client.cookies
    
    # Faz logout
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == status.HTTP_200_OK
    
    # Verifica se limpou o cookie de acesso
    assert "access_token" not in client.cookies
    
    # Tenta obter dados do me (deve ser barrado)
    response_me = client.get("/api/v1/auth/me")
    assert response_me.status_code == status.HTTP_401_UNAUTHORIZED
