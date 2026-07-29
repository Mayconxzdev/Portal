import os

os.environ.setdefault("ENVIRONMENT", "testing")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import Engine
from app.main import app
from app.core.database import Base, get_db
from app.models.role import Role
from app.models.module import Module
from app.models.user import User
from app.models.user_module_access import UserModuleAccess
from app.core.security import get_password_hash

# Habilita suporte a chaves estrangeiras no SQLite em memória
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    except Exception:
        pass

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class _NoopRedisForTests:
    """Avoid external Redis I/O when a test did not explicitly provide a double.

    Event publishing is best-effort in the application. Letting the default client
    attempt a TCP connection during tests turns every emitted event into a one-second
    network wait when Redis is not running locally, and makes CI depend on external
    infrastructure. Tests that need Redis failures or call assertions patch
    ``app.core.events.redis.Redis`` with their own mock.
    """

    def __init__(self, *args, **kwargs):
        pass

    def ping(self):
        return True

    def publish(self, *args, **kwargs):
        return 1


@pytest.fixture(autouse=True)
def prevent_external_redis_connections(monkeypatch):
    """Keep the test suite hermetic unless a test opts into a Redis mock."""
    import app.core.events as events_module

    if events_module.redis is not None:
        monkeypatch.setattr(events_module.redis, "Redis", _NoopRedisForTests)

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    # Cria todas as tabelas na inicialização da suite de testes
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    try:
        # 1. Criar Papéis
        admin_role = Role(name="ADMIN", description="Administrador Geral")
        user_role = Role(name="USER", description="Usuário Comum")
        db.add(admin_role)
        db.add(user_role)
        db.commit()
        
        # 2. Criar Módulos de Teste
        modules = [
            Module(name="Dashboard", code="dashboard", is_active=True, is_restricted=False),
            Module(name="Kanban", code="kanban", is_active=True, is_restricted=False),
            Module(name="TI", code="it", is_active=True, is_restricted=False),
            Module(name="Administração", code="admin", is_active=True, is_restricted=True),
            Module(name="Aprovações", code="approvals", is_active=True, is_restricted=False)
        ]
        db.add_all(modules)
        db.commit()
        
        # 3. Criar Usuários para testes
        admin_user = User(
            username="vesper_admin",
            email="admin@portal.example",
            hashed_password=get_password_hash("admin"),
            is_active=True,
            role_id=admin_role.id
        )
        common_user = User(
            username="vesper_user",
            email="user@portal.example",
            hashed_password=get_password_hash("userpass"),
            is_active=True,
            role_id=user_role.id
        )
        inactive_user = User(
            username="vesper_inactive",
            email="inactive@portal.example",
            hashed_password=get_password_hash("inactivepass"),
            is_active=False,
            role_id=user_role.id
        )
        db.add(admin_user)
        db.add(common_user)
        db.add(inactive_user)
        db.commit()
        
        # 4. Configurar permissões padrão para o usuário comum
        access_dash = UserModuleAccess(
            user_id=common_user.id,
            module_id=modules[0].id, # Dashboard
            permission_level="NORMAL"
        )
        access_kanban = UserModuleAccess(
            user_id=common_user.id,
            module_id=modules[1].id, # Kanban
            permission_level="NO_ACCESS"
        )
        access_admin = UserModuleAccess(
            user_id=common_user.id,
            module_id=modules[3].id, # Administração
            permission_level="NO_ACCESS"
        )
        access_approvals = UserModuleAccess(
            user_id=common_user.id,
            module_id=modules[4].id, # Aprovações
            permission_level="NORMAL"
        )
        db.add(access_dash)
        db.add(access_kanban)
        db.add(access_admin)
        db.add(access_approvals)
        db.commit()
        
    finally:
        db.close()
        
    yield
    # Limpa o banco no término da suite
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db():
    # Mantém os testes isolados por transação
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db):
    # Sobrescreve a dependência get_db oficial para usar a transação isolada de teste
    def override_get_db():
        try:
            yield db
        finally:
            pass
            
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
