import pytest
from fastapi import status
from app.core.events import emit_event, EventStatus
from app.models.event_log import EventLog
from app.models.user import User

def test_emit_event_saves_to_db_as_pending(db):
    # Cria usuario de teste para associar ao evento
    user = db.query(User).filter(User.username == "vesper_admin").first()
    
    # Emite evento
    event = emit_event(
        db=db,
        event_type="test.event.emitted",
        aggregate_type="test_aggregate",
        aggregate_id="123",
        module="test_module",
        payload={"key": "value"},
        actor_user_id=user.id if user else None
    )
    
    # Confirma gravacao no banco na mesma transacao
    db.commit()
    
    # Recupera o evento e verifica os campos
    db_event = db.query(EventLog).filter(EventLog.id == event.id).first()
    assert db_event is not None
    assert db_event.event_type == "test.event.emitted"
    assert db_event.aggregate_type == "test_aggregate"
    assert db_event.aggregate_id == "123"
    assert db_event.module == "test_module"
    assert db_event.payload == {"key": "value"}
    assert db_event.status == EventStatus.PENDING
    assert db_event.attempts == 0
    assert db_event.last_error is None

def test_events_recent_endpoint_requires_admin(client):
    # Usuario anonimo deve ser bloqueado
    response = client.get("/api/v1/events/recent")
    assert response.status_code in {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN}

def test_events_recent_endpoint_admin_access(client, db):
    # Realiza login do admin
    login_res = client.post("/api/v1/auth/login", json={
        "username": "vesper_admin",
        "password": "admin"
    })
    assert login_res.status_code == status.HTTP_200_OK
    
    # Emite um evento para listar
    emit_event(
        db=db,
        event_type="auth.user.logged_in",
        aggregate_type="user",
        aggregate_id="1",
        module="auth",
        payload={"username": "vesper_admin", "password": "sensitivesecret"},
        actor_user_id=1
    )
    db.commit()
    
    # Busca eventos recentes como admin
    response = client.get("/api/v1/events/recent")
    assert response.status_code == status.HTTP_200_OK
    events = response.json()
    assert len(events) >= 1
    
    # Garante que dados sensiveis (password) foram mascarados no payload retornado
    target_event = next(e for e in events if e["event_type"] == "auth.user.logged_in")
    assert target_event["payload"]["password"] == "******"

def test_events_recent_filters(client, db):
    # Realiza login
    client.post("/api/v1/auth/login", json={
        "username": "vesper_admin",
        "password": "admin"
    })
    
    # Emite dois eventos diferentes
    emit_event(
        db=db,
        event_type="test.filter.type_a",
        aggregate_type="a",
        aggregate_id="1",
        module="module_a",
        payload={}
    )
    emit_event(
        db=db,
        event_type="test.filter.type_b",
        aggregate_type="b",
        aggregate_id="2",
        module="module_b",
        payload={}
    )
    db.commit()
    
    # Filtra por module
    res_module = client.get("/api/v1/events/recent?module=module_a")
    assert res_module.status_code == status.HTTP_200_OK
    events_mod = res_module.json()
    assert all(e["module"] == "module_a" for e in events_mod)
    
    # Filtra por status PENDING
    res_status = client.get("/api/v1/events/recent?status=PENDING")
    assert res_status.status_code == status.HTTP_200_OK
    events_stat = res_status.json()
    assert all(e["status"] == "PENDING" for e in events_stat)

from unittest.mock import patch, MagicMock
import unittest.mock

@patch("app.core.events.redis.Redis")
def test_dispatch_marks_dispatched_on_success(mock_redis_class, db):
    mock_redis = MagicMock()
    mock_redis_class.return_value = mock_redis
    mock_redis.ping.return_value = True
    
    event = emit_event(
        db=db,
        event_type="test.dispatch.success",
        aggregate_type="test",
        aggregate_id="123",
        module="test",
        payload={"foo": "bar"}
    )
    db.commit()
    
    assert event.status == EventStatus.PENDING
    assert event.attempts == 0
    
    mock_redis.publish.reset_mock()
    
    from app.core.events import dispatch_pending_events
    result = dispatch_pending_events(db)
    
    assert result.processed == 1
    assert result.dispatched == 1
    assert result.failed == 0
    
    db.refresh(event)
    assert event.status == EventStatus.DISPATCHED
    assert event.attempts == 1
    assert event.dispatched_at is not None
    assert event.last_error is None
    
    assert mock_redis.publish.call_count == 2
    mock_redis.publish.assert_any_call("events.test.dispatch.success", unittest.mock.ANY)
    mock_redis.publish.assert_any_call("module.test", unittest.mock.ANY)


@patch("app.core.events.redis.Redis")
def test_dispatch_marks_failed_on_redis_error(mock_redis_class, db):
    mock_redis = MagicMock()
    mock_redis_class.return_value = mock_redis
    mock_redis.ping.return_value = True
    mock_redis.publish.side_effect = Exception("Redis connection lost")
    
    event = emit_event(
        db=db,
        event_type="test.dispatch.failed",
        aggregate_type="test",
        aggregate_id="123",
        module="test",
        payload={"foo": "bar"}
    )
    db.commit()
    
    from app.core.events import dispatch_pending_events
    result = dispatch_pending_events(db)
    
    assert result.processed == 1
    assert result.dispatched == 0
    assert result.failed == 1
    
    db.refresh(event)
    assert event.status == EventStatus.FAILED
    assert event.attempts == 1
    assert event.dispatched_at is None
    assert event.last_error == "Redis connection lost"

@patch("app.core.events.redis.Redis")
def test_dispatch_failed_on_redis_ping_error(mock_redis_class, db):
    mock_redis_class.side_effect = Exception("Redis server down")
    
    event = emit_event(
        db=db,
        event_type="test.dispatch.ping_failed",
        aggregate_type="test",
        aggregate_id="123",
        module="test",
        payload={"foo": "bar"}
    )
    db.commit()
    
    from app.core.events import dispatch_pending_events
    result = dispatch_pending_events(db)
    
    assert result.failed == 1
    db.refresh(event)
    assert event.status == EventStatus.FAILED
    assert event.attempts == 1
    assert "Redis client unavailable" in event.last_error

def test_dispatch_retry_failed_events(db):
    event = emit_event(
        db=db,
        event_type="test.retry.failed",
        aggregate_type="test",
        aggregate_id="123",
        module="test",
        payload={"foo": "bar"}
    )
    event.status = EventStatus.FAILED
    event.attempts = 4
    db.commit()
    
    with patch("app.core.events.redis.Redis") as mock_redis_class:
        mock_redis_class.side_effect = Exception("Still failing")
        from app.core.events import dispatch_pending_events
        result = dispatch_pending_events(db)
        
        assert result.processed == 1
        assert result.failed == 1
        
        db.refresh(event)
        assert event.attempts == 5
        assert event.status == EventStatus.FAILED
        
    with patch("app.core.events.redis.Redis") as mock_redis_class:
        from app.core.events import dispatch_pending_events
        result = dispatch_pending_events(db)
        
        assert result.processed == 0

def test_dispatch_endpoint_requires_admin(client):
    response = client.post("/api/v1/events/dispatch")
    assert response.status_code in {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN}

@patch("app.core.events.redis.Redis")
def test_dispatch_endpoint_success(mock_redis_class, client, db):
    mock_redis = MagicMock()
    mock_redis_class.return_value = mock_redis
    mock_redis.ping.return_value = True
    
    login_res = client.post("/api/v1/auth/login", json={
        "username": "vesper_admin",
        "password": "admin"
    })
    assert login_res.status_code == status.HTTP_200_OK
    
    emit_event(
        db=db,
        event_type="test.endpoint.dispatch",
        aggregate_type="test",
        aggregate_id="123",
        module="test",
        payload={}
    )
    db.commit()
    
    response = client.post("/api/v1/events/dispatch?limit=10")
    assert response.status_code == status.HTTP_200_OK
    res_data = response.json()
    assert res_data["processed"] >= 1
    assert res_data["dispatched"] >= 1
    assert res_data["failed"] == 0

def test_scheduler_default_settings():
    from app.core.config import settings
    assert settings.EVENT_DISPATCHER_ENABLED is False
    assert settings.EVENT_DISPATCHER_INTERVAL_SECONDS == 5
    assert settings.EVENT_DISPATCHER_BATCH_SIZE == 50
    assert settings.EVENT_DISPATCHER_MAX_ATTEMPTS == 5

def test_scheduler_does_not_start_when_disabled():
    import asyncio
    from app.core.config import settings
    from app.core.events import start_event_dispatcher_scheduler
    import app.core.events
    
    async def run_test():
        with patch.object(settings, "EVENT_DISPATCHER_ENABLED", False):
            await start_event_dispatcher_scheduler()
            assert app.core.events._dispatcher_task is None

    asyncio.run(run_test())

def test_scheduler_starts_and_stops_when_enabled():
    import asyncio
    from app.core.config import settings
    from app.core.events import start_event_dispatcher_scheduler, stop_event_dispatcher_scheduler
    import app.core.events
    
    async def run_test():
        with patch.object(settings, "EVENT_DISPATCHER_ENABLED", True):
            with patch("app.core.events._dispatcher_loop") as mock_loop:
                await start_event_dispatcher_scheduler()
                assert app.core.events._dispatcher_task is not None
                await stop_event_dispatcher_scheduler()
                assert app.core.events._dispatcher_task is None
                
    asyncio.run(run_test())

def test_scheduler_loop_concurrency_prevention():
    import asyncio
    from app.core.events import _dispatcher_loop
    import app.core.events
    
    async def run_test():
        app.core.events._dispatcher_running = True
        app.core.events._dispatcher_should_run = True
        
        from app.core.config import settings
        with patch.object(settings, "EVENT_DISPATCHER_INTERVAL_SECONDS", 0.01):
            with patch("app.core.events.dispatch_pending_events") as mock_dispatch:
                task = asyncio.create_task(_dispatcher_loop())
                await asyncio.sleep(0.03)
                app.core.events._dispatcher_should_run = False
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                
                mock_dispatch.assert_not_called()
                
        app.core.events._dispatcher_running = False
        app.core.events._dispatcher_should_run = True

    asyncio.run(run_test())

def test_dispatch_applies_postgresql_lock(db):
    original_query = db.query
    
    class MockQuery:
        def __init__(self, query_obj):
            self.query_obj = query_obj
            self.with_for_update_called = False
            
        def filter(self, *args, **kwargs):
            self.query_obj = self.query_obj.filter(*args, **kwargs)
            return self
            
        def order_by(self, *args, **kwargs):
            self.query_obj = self.query_obj.order_by(*args, **kwargs)
            return self
            
        def with_for_update(self, **kwargs):
            self.with_for_update_called = True
            assert kwargs.get("skip_locked") is True
            self.query_obj = self.query_obj.with_for_update(**kwargs)
            return self
            
        def limit(self, limit):
            self.query_obj = self.query_obj.limit(limit)
            return self
            
        def all(self):
            return self.query_obj.all()
            
    mock_query_wrapper = None
    
    def mock_query(*args, **kwargs):
        nonlocal mock_query_wrapper
        q = original_query(*args, **kwargs)
        mock_query_wrapper = MockQuery(q)
        return mock_query_wrapper
        
    db.query = mock_query
    
    mock_dialect = MagicMock()
    mock_dialect.name = "postgresql"
    
    with patch.object(db, "get_bind") as mock_get_bind:
        mock_get_bind.return_value.dialect = mock_dialect
        
        from app.core.events import dispatch_pending_events
        result = dispatch_pending_events(db)
        
        assert mock_query_wrapper is not None
        assert mock_query_wrapper.with_for_update_called is True
        
    db.query = original_query

def test_dispatch_sequential_calls_do_not_redispatch(db):
    event = emit_event(
        db=db,
        event_type="test.dispatch.sequential",
        aggregate_type="test",
        aggregate_id="123",
        module="test",
        payload={}
    )
    db.commit()
    
    with patch("app.core.events.redis.Redis") as mock_redis_class:
        mock_redis = MagicMock()
        mock_redis_class.return_value = mock_redis
        mock_redis.ping.return_value = True
        
        from app.core.events import dispatch_pending_events
        res1 = dispatch_pending_events(db)
        assert res1.processed == 1
        assert res1.dispatched == 1
        
        res2 = dispatch_pending_events(db)
        assert res2.processed == 0

def test_emit_event_known_event_valid_payload_success(db):
    payload = {
        "username": "jose.silva",
        "email": "jose@portal.example",
        "role": "analista",
        "ip_address": "192.168.1.10"
    }
    from app.core.config import settings
    with patch.object(settings, "EVENT_PAYLOAD_VALIDATION_MODE", "strict"):
        event = emit_event(
            db=db,
            event_type="auth.user.logged_in",
            aggregate_type="user",
            aggregate_id="10",
            module="auth",
            payload=payload
        )
        db.commit()
        db_event = db.query(EventLog).filter(EventLog.id == event.id).first()
        assert db_event is not None
        assert db_event.payload == payload
        assert db_event.metadata_json.get("payload_schema_version") == 1

def test_emit_event_approval_created_valid_payload_success(db):
    payload = {
        "approval_id": 42,
        "title": "Aprovacao de Compra TI",
        "module_slug": "purchasing",
        "risk_level": "high",
        "action_type": "approve_purchase"
    }
    from app.core.config import settings
    with patch.object(settings, "EVENT_PAYLOAD_VALIDATION_MODE", "strict"):
        event = emit_event(
            db=db,
            event_type="approval.created",
            aggregate_type="approval",
            aggregate_id="42",
            module="approvals",
            payload=payload
        )
        db.commit()
        db_event = db.query(EventLog).filter(EventLog.id == event.id).first()
        assert db_event is not None
        assert db_event.payload == payload

def test_emit_event_known_event_invalid_payload_fails_in_strict(db):
    invalid_payload = {
        "username": "jose.silva",
    }
    from app.core.config import settings
    with patch.object(settings, "EVENT_PAYLOAD_VALIDATION_MODE", "strict"):
        with pytest.raises(ValueError) as excinfo:
            emit_event(
                db=db,
                event_type="auth.user.logged_in",
                aggregate_type="user",
                aggregate_id="10",
                module="auth",
                payload=invalid_payload
            )
        assert "[CONTRATO EVENTO] Payload invalido para tipo 'auth.user.logged_in'" in str(excinfo.value)

def test_emit_event_known_event_invalid_payload_warn_mode_success(db):
    invalid_payload = {
        "username": "jose.silva"
    }
    from app.core.config import settings
    with patch.object(settings, "EVENT_PAYLOAD_VALIDATION_MODE", "warn"):
        with patch("app.core.event_contracts.logger.warning") as mock_warn:
            event = emit_event(
                db=db,
                event_type="auth.user.logged_in",
                aggregate_type="user",
                aggregate_id="10",
                module="auth",
                payload=invalid_payload
            )
            db.commit()
            
            mock_warn.assert_called_once()
            assert "[CONTRATO EVENTO] Payload invalido para tipo 'auth.user.logged_in'" in mock_warn.call_args[0][0]
            
            db_event = db.query(EventLog).filter(EventLog.id == event.id).first()
            assert db_event is not None
            assert db_event.payload == invalid_payload

def test_emit_event_unknown_event_warn_mode_success(db):
    payload = {"custom": "data"}
    from app.core.config import settings
    with patch.object(settings, "EVENT_PAYLOAD_VALIDATION_MODE", "warn"):
        with patch("app.core.event_contracts.logger.warning") as mock_warn:
            event = emit_event(
                db=db,
                event_type="unregistered.custom.event",
                aggregate_type="custom",
                aggregate_id="99",
                module="custom_mod",
                payload=payload
            )
            db.commit()
            
            mock_warn.assert_called_once()
            assert "Evento desconhecido 'unregistered.custom.event'" in mock_warn.call_args[0][0]
            
            db_event = db.query(EventLog).filter(EventLog.id == event.id).first()
            assert db_event is not None
            assert db_event.payload == payload

def test_emit_event_unknown_event_strict_mode_fails(db):
    payload = {"custom": "data"}
    from app.core.config import settings
    with patch.object(settings, "EVENT_PAYLOAD_VALIDATION_MODE", "strict"):
        with pytest.raises(ValueError) as excinfo:
            emit_event(
                db=db,
                event_type="unregistered.custom.event",
                aggregate_type="custom",
                aggregate_id="99",
                module="custom_mod",
                payload=payload
            )
        assert "Evento desconhecido 'unregistered.custom.event'" in str(excinfo.value)

def test_emit_event_validation_mode_off(db):
    invalid_payload = {"username": "jose.silva"}
    from app.core.config import settings
    with patch.object(settings, "EVENT_PAYLOAD_VALIDATION_MODE", "off"):
        with patch("app.core.event_contracts.logger.warning") as mock_warn:
            event = emit_event(
                db=db,
                event_type="auth.user.logged_in",
                aggregate_type="user",
                aggregate_id="10",
                module="auth",
                payload=invalid_payload
            )
            db.commit()
            mock_warn.assert_not_called()
            
            db_event = db.query(EventLog).filter(EventLog.id == event.id).first()
            assert db_event is not None
            assert db_event.payload == invalid_payload

def test_emit_event_sensitive_data_masked_in_validation_error(db):
    invalid_payload = {
        "username": "jose.silva",
        "password": "supersecretpassword123",
        "token": "secrettoken123",
        "secret": "my-secret-key",
        "hashed_password": "somehashedstring"
    }
    from app.core.config import settings
    with patch.object(settings, "EVENT_PAYLOAD_VALIDATION_MODE", "strict"):
        with pytest.raises(ValueError) as excinfo:
            emit_event(
                db=db,
                event_type="auth.user.logged_in",
                aggregate_type="user",
                aggregate_id="10",
                module="auth",
                payload=invalid_payload
            )
        error_msg = str(excinfo.value)
        assert "[CONTRATO EVENTO] Payload invalido para tipo 'auth.user.logged_in'" in error_msg
        assert "supersecretpassword123" not in error_msg
        assert "secrettoken123" not in error_msg
        assert "my-secret-key" not in error_msg
        assert "somehashedstring" not in error_msg
        assert "******" in error_msg


def test_n8n_bridge_disabled_does_not_send(db):
    from app.core.config import settings
    from app.integrations.n8n_client import dispatch_event_to_n8n_bridge
    
    event = emit_event(
        db=db,
        event_type="approval.created",
        aggregate_type="approval",
        aggregate_id="101",
        module="approvals",
        payload={
            "approval_id": 101,
            "title": "Teste n8n bridge",
            "module_slug": "ti",
            "risk_level": "low",
            "action_type": "test"
        }
    )
    db.commit()
    
    with patch.object(settings, "N8N_WEBHOOK_BRIDGE_ENABLED", False):
        with patch.object(settings, "N8N_ALLOWED_EVENT_TYPES", "approval.created"):
            with patch("requests.post") as mock_post:
                res = dispatch_event_to_n8n_bridge(event)
                assert res is None
                mock_post.assert_not_called()

def test_n8n_bridge_event_not_allowed_does_not_send(db):
    from app.core.config import settings
    from app.integrations.n8n_client import dispatch_event_to_n8n_bridge
    
    event = emit_event(
        db=db,
        event_type="approval.created",
        aggregate_type="approval",
        aggregate_id="101",
        module="approvals",
        payload={
            "approval_id": 101,
            "title": "Teste n8n bridge",
            "module_slug": "ti",
            "risk_level": "low",
            "action_type": "test"
        }
    )
    db.commit()
    
    with patch.object(settings, "N8N_WEBHOOK_BRIDGE_ENABLED", True):
        with patch.object(settings, "N8N_ALLOWED_EVENT_TYPES", "other.event.type"):
            with patch("requests.post") as mock_post:
                res = dispatch_event_to_n8n_bridge(event)
                assert res is None
                mock_post.assert_not_called()

def test_n8n_bridge_sends_correct_url_and_headers(db):
    from app.core.config import settings
    from app.integrations.n8n_client import dispatch_event_to_n8n_bridge
    import hmac
    import hashlib
    import json
    
    event = emit_event(
        db=db,
        event_type="approval.created",
        aggregate_type="approval",
        aggregate_id="101",
        module="approvals",
        payload={
            "approval_id": 101,
            "title": "Teste n8n bridge",
            "module_slug": "ti",
            "risk_level": "low",
            "action_type": "test"
        }
    )
    db.commit()
    
    mock_response = MagicMock()
    mock_response.status_code = 202
    
    with patch.object(settings, "N8N_WEBHOOK_BRIDGE_ENABLED", True):
        with patch.object(settings, "N8N_ALLOWED_EVENT_TYPES", "approval.created"):
            with patch.object(settings, "N8N_WEBHOOK_SECRET", "my_secret_key"):
                with patch("requests.post", return_value=mock_response) as mock_post:
                    res = dispatch_event_to_n8n_bridge(event)
                    
                    assert res is not None
                    assert res.success is True
                    assert res.status_code == 202
                    mock_post.assert_called_once()
                    
                    args, kwargs = mock_post.call_args
                    url = args[0]
                    assert url == "http://localhost:5678/webhook/portal/events/approval-created"
                    
                    headers = kwargs["headers"]
                    assert headers["X-Vesper-Event-Id"] == str(event.id)
                    assert headers["X-Vesper-Event-Type"] == "approval.created"
                    assert headers["X-Vesper-Signature-Version"] == "v1"
                    assert headers["X-Idempotency-Key"] == str(event.id)
                    
                    # Verifica a assinatura HMAC
                    timestamp = headers["X-Vesper-Timestamp"]
                    body_data = json.loads(kwargs["data"])
                    raw_body_canonico = json.dumps(body_data, sort_keys=True, separators=(",", ":"))
                    base_string = f"{timestamp}.{str(event.id)}.{raw_body_canonico}"
                    
                    expected_signature = hmac.new(
                        b"my_secret_key",
                        base_string.encode("utf-8"),
                        hashlib.sha256
                    ).hexdigest()
                    
                    assert headers["X-Vesper-Signature"] == expected_signature

def test_n8n_bridge_production_enforce_secret():
    from app.core.config import Settings
    
    with pytest.raises(ValueError) as exc:
        Settings(
            ENVIRONMENT="production",
            JWT_SECRET="strong_non_default_secret_for_jwt_auth_12345",
            N8N_WEBHOOK_BRIDGE_ENABLED=True,
            N8N_WEBHOOK_SECRET=None
        )
    assert "N8N_WEBHOOK_SECRET must be configured" in str(exc.value)

def test_n8n_bridge_retry_loop_on_failure(db):
    from app.core.config import settings
    from app.integrations.n8n_client import dispatch_event_to_n8n_bridge
    
    event = emit_event(
        db=db,
        event_type="approval.created",
        aggregate_type="approval",
        aggregate_id="101",
        module="approvals",
        payload={
            "approval_id": 101,
            "title": "Teste n8n bridge",
            "module_slug": "ti",
            "risk_level": "low",
            "action_type": "test"
        }
    )
    db.commit()
    
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    
    with patch.object(settings, "N8N_WEBHOOK_BRIDGE_ENABLED", True):
        with patch.object(settings, "N8N_ALLOWED_EVENT_TYPES", "approval.created"):
            with patch.object(settings, "N8N_WEBHOOK_MAX_ATTEMPTS", 3):
                with patch("requests.post", return_value=mock_response) as mock_post:
                    res = dispatch_event_to_n8n_bridge(event)
                    assert res is not None
                    assert res.success is False
                    assert res.status_code == 500
                    assert mock_post.call_count == 3

def test_n8n_bridge_does_not_break_dispatcher_on_failure(db):
    from app.core.config import settings
    from app.core.events import dispatch_pending_events
    
    event = emit_event(
        db=db,
        event_type="approval.created",
        aggregate_type="approval",
        aggregate_id="101",
        module="approvals",
        payload={
            "approval_id": 101,
            "title": "Teste n8n bridge",
            "module_slug": "ti",
            "risk_level": "low",
            "action_type": "test"
        }
    )
    db.commit()
    
    with patch.object(settings, "N8N_WEBHOOK_BRIDGE_ENABLED", True):
        with patch.object(settings, "N8N_ALLOWED_EVENT_TYPES", "approval.created"):
            with patch("requests.post", side_effect=Exception("Connection refused")):
                with patch("app.core.events.redis.Redis") as mock_redis_class:
                    mock_redis = MagicMock()
                    mock_redis_class.return_value = mock_redis
                    mock_redis.ping.return_value = True
                    
                    result = dispatch_pending_events(db)
                    # O dispatch geral (Redis/banco) deve passar com sucesso mesmo que o n8n falhe
                    assert result.processed == 1
                    assert result.dispatched == 1
                    
                    db.refresh(event)
                    assert event.status == EventStatus.DISPATCHED

def test_manual_send_endpoint_via_client(client, db):
    # Efetua login como admin
    login_res = client.post("/api/v1/auth/login", json={
        "username": "vesper_admin",
        "password": "admin"
    })
    assert login_res.status_code == 200
    
    event = emit_event(
        db=db,
        event_type="approval.created",
        aggregate_type="approval",
        aggregate_id="101",
        module="approvals",
        payload={
            "approval_id": 101,
            "title": "Teste n8n bridge",
            "module_slug": "ti",
            "risk_level": "low",
            "action_type": "test"
        }
    )
    db.commit()
    
    from app.core.config import settings
    mock_res = MagicMock()
    mock_res.status_code = 202
    
    # Endpoint de teste administrativo manual
    with patch.object(settings, "N8N_WEBHOOK_BRIDGE_ENABLED", True):
        with patch.object(settings, "N8N_ALLOWED_EVENT_TYPES", "approval.created"):
            with patch("requests.post", return_value=mock_res):
                response = client.post(f"/api/v1/events/{str(event.id)}/send-to-n8n")
                assert response.status_code == 200
                assert response.json()["status"] == "success"
                assert response.json()["status_code"] == 202

def test_manual_send_endpoint_blocked_for_anonymous(client, db):
    # Requisição anônima deve ser bloqueada
    response = client.post("/api/v1/events/some-uuid/send-to-n8n")
    assert response.status_code in {401, 403}


# Testes do Response Gateway do n8n
from datetime import datetime, timezone, timedelta

def make_callback_headers(
    event_id: str,
    callback_type: str,
    timestamp: str,
    idempotency_key: str,
    body_dict: dict,
    secret: str = "vesper_n8n_local_secret"
):
    import hashlib
    import hmac
    import json
    raw_body = json.dumps(body_dict, sort_keys=True, separators=(",", ":"))
    base_string = f"{timestamp}.{idempotency_key}.{raw_body}"
    sig = hmac.new(secret.encode("utf-8"), base_string.encode("utf-8"), hashlib.sha256).hexdigest()
    return {
        "X-Vesper-Event-Id": event_id,
        "X-Vesper-Callback-Type": callback_type,
        "X-Vesper-Timestamp": timestamp,
        "X-Vesper-Signature": sig,
        "X-Vesper-Signature-Version": "v1",
        "X-Idempotency-Key": idempotency_key
    }

def test_callback_disabled_by_default(client, db):
    # N8N_CALLBACKS_ENABLED é falso por padrão.
    event_id = "550e8400-e29b-41d4-a716-446655440000"
    body = {
        "event_id": event_id,
        "event_type": "approval.created",
        "status": "processed"
    }
    timestamp = datetime.now(timezone.utc).isoformat()
    headers = make_callback_headers(event_id, "processed", timestamp, "idem-1", body)
    
    response = client.post("/api/v1/integrations/n8n/callbacks", json=body, headers=headers)
    assert response.status_code == 400
    assert "disabled" in response.json()["detail"]

def test_callback_missing_headers(client):
    body = {
        "event_id": "550e8400-e29b-41d4-a716-446655440000",
        "event_type": "approval.created",
        "status": "processed"
    }
    from app.core.config import settings
    with patch.object(settings, "N8N_CALLBACKS_ENABLED", True):
        response = client.post("/api/v1/integrations/n8n/callbacks", json=body)
        assert response.status_code == 400
        assert "headers" in response.json()["detail"]

def test_callback_invalid_signature(client):
    event_id = "550e8400-e29b-41d4-a716-446655440000"
    body = {
        "event_id": event_id,
        "event_type": "approval.created",
        "status": "processed"
    }
    timestamp = datetime.now(timezone.utc).isoformat()
    headers = make_callback_headers(event_id, "processed", timestamp, "idem-2", body)
    headers["X-Vesper-Signature"] = "wrongsignature123"
    
    from app.core.config import settings
    with patch.object(settings, "N8N_CALLBACKS_ENABLED", True):
        response = client.post("/api/v1/integrations/n8n/callbacks", json=body, headers=headers)
        assert response.status_code == 401
        assert "signature" in response.json()["detail"].lower()

def test_callback_expired_timestamp(client):
    event_id = "550e8400-e29b-41d4-a716-446655440000"
    body = {
        "event_id": event_id,
        "event_type": "approval.created",
        "status": "processed"
    }
    expired_time = datetime.now(timezone.utc) - timedelta(seconds=600)
    timestamp = expired_time.isoformat()
    headers = make_callback_headers(event_id, "processed", timestamp, "idem-3", body)
    
    from app.core.config import settings
    with patch.object(settings, "N8N_CALLBACKS_ENABLED", True):
        response = client.post("/api/v1/integrations/n8n/callbacks", json=body, headers=headers)
        assert response.status_code == 401
        assert "expired" in response.json()["detail"]

def test_callback_event_not_found(client, db):
    event_id = "550e8400-e29b-41d4-a716-446655449999"
    body = {
        "event_id": event_id,
        "event_type": "approval.created",
        "status": "processed"
    }
    timestamp = datetime.now(timezone.utc).isoformat()
    headers = make_callback_headers(event_id, "processed", timestamp, "idem-4", body)
    
    from app.core.config import settings
    with patch.object(settings, "N8N_CALLBACKS_ENABLED", True):
        response = client.post("/api/v1/integrations/n8n/callbacks", json=body, headers=headers)
        assert response.status_code == 404
        assert "Event not found" in response.json()["detail"]

def test_callback_event_type_mismatch(client, db):
    event = emit_event(
        db=db,
        event_type="auth.user.logged_in",
        aggregate_type="user",
        aggregate_id="1",
        module="auth",
        payload={}
    )
    db.commit()
    
    body = {
        "event_id": str(event.id),
        "event_type": "approval.created",
        "status": "processed"
    }
    timestamp = datetime.now(timezone.utc).isoformat()
    headers = make_callback_headers(str(event.id), "processed", timestamp, "idem-5", body)
    
    from app.core.config import settings
    with patch.object(settings, "N8N_CALLBACKS_ENABLED", True):
        response = client.post("/api/v1/integrations/n8n/callbacks", json=body, headers=headers)
        assert response.status_code == 400
        assert "mismatch" in response.json()["detail"]

def test_callback_valid_saves_log(client, db):
    event = emit_event(
        db=db,
        event_type="approval.created",
        aggregate_type="approval",
        aggregate_id="99",
        module="approvals",
        payload={}
    )
    db.commit()
    
    body = {
        "event_id": str(event.id),
        "event_type": "approval.created",
        "workflow_id": "wf-123",
        "workflow_name": "Approval Flow",
        "execution_id": "exec-456",
        "status": "processed",
        "result": {"message": "All good"}
    }
    timestamp = datetime.now(timezone.utc).isoformat()
    headers = make_callback_headers(str(event.id), "processed", timestamp, "idem-6", body)
    
    from app.core.config import settings
    from app.models.automation_callback_log import AutomationCallbackLog
    with patch.object(settings, "N8N_CALLBACKS_ENABLED", True):
        response = client.post("/api/v1/integrations/n8n/callbacks", json=body, headers=headers)
        assert response.status_code == 200
        res_json = response.json()
        assert res_json["status"] == "success"
        assert res_json["callback_type"] == "processed"
        assert res_json["processed_at"] is not None
        
        log = db.query(AutomationCallbackLog).filter(
            AutomationCallbackLog.idempotency_key == "idem-6"
        ).first()
        assert log is not None
        assert log.workflow_id == "wf-123"
        assert log.workflow_name == "Approval Flow"
        assert log.execution_id == "exec-456"
        assert log.callback_type == "processed"
        assert log.signature_valid is True

def test_callback_idempotency_key_duplicate(client, db):
    event = emit_event(
        db=db,
        event_type="approval.created",
        aggregate_type="approval",
        aggregate_id="100",
        module="approvals",
        payload={}
    )
    db.commit()
    
    body = {
        "event_id": str(event.id),
        "event_type": "approval.created",
        "status": "processed"
    }
    timestamp = datetime.now(timezone.utc).isoformat()
    headers = make_callback_headers(str(event.id), "processed", timestamp, "idem-7", body)
    
    from app.core.config import settings
    with patch.object(settings, "N8N_CALLBACKS_ENABLED", True):
        res1 = client.post("/api/v1/integrations/n8n/callbacks", json=body, headers=headers)
        assert res1.status_code == 200
        
        res2 = client.post("/api/v1/integrations/n8n/callbacks", json=body, headers=headers)
        assert res2.status_code == 200
        assert res2.json()["status"] == "duplicate_ignored"

def test_callback_sensitive_action_blocked(client, db):
    event = emit_event(
        db=db,
        event_type="approval.created",
        aggregate_type="approval",
        aggregate_id="101",
        module="approvals",
        payload={}
    )
    db.commit()
    
    body = {
        "event_id": str(event.id),
        "event_type": "approval.created",
        "status": "action_requested",
        "result": {
            "action": "approve_approval",
            "approval_id": 123,
            "decision": "approved"
        }
    }
    timestamp = datetime.now(timezone.utc).isoformat()
    headers = make_callback_headers(str(event.id), "action_requested", timestamp, "idem-8", body)
    
    from app.core.config import settings
    from app.models.automation_callback_log import AutomationCallbackLog
    with patch.object(settings, "N8N_CALLBACKS_ENABLED", True):
        response = client.post("/api/v1/integrations/n8n/callbacks", json=body, headers=headers)
        assert response.status_code == 200
        res_json = response.json()
        assert res_json["callback_type"] == "requires_manual_action"
        assert res_json["processed_at"] is None
        
        log = db.query(AutomationCallbackLog).filter(
            AutomationCallbackLog.idempotency_key == "idem-8"
        ).first()
        assert log is not None
        assert log.callback_type == "requires_manual_action"
        assert log.processed_at is None

def test_callback_sensitive_payload_masked():
    from app.api.integrations import mask_sensitive_payload
    payload = {
        "password": "secretpassword",
        "token": "sensitive_token",
        "normal_field": "visible",
        "nested": {
            "access_token": "bearer12345",
            "key": "mysecretkey"
        }
    }
    masked = mask_sensitive_payload(payload)
    assert masked["password"] == "******"
    assert masked["token"] == "******"
    assert masked["normal_field"] == "visible"
    assert masked["nested"]["access_token"] == "******"
    assert masked["nested"]["key"] == "******"

def test_production_enforce_secret_callbacks():
    from app.core.config import Settings
    with patch("app.core.config.Settings.cors_origins", return_value=[]):
        settings = Settings(
            ENVIRONMENT="production",
            N8N_CALLBACKS_ENABLED=False,
            N8N_WEBHOOK_SECRET=None,
            JWT_SECRET="strong_production_jwt_secret_value_123"
        )
        
        with pytest.raises(ValueError) as exc:
            Settings(
                ENVIRONMENT="production",
                N8N_CALLBACKS_ENABLED=True,
                N8N_WEBHOOK_SECRET=None,
                JWT_SECRET="strong_production_jwt_secret_value_123"
            )
        assert "N8N_WEBHOOK_SECRET must be configured" in str(exc.value)



