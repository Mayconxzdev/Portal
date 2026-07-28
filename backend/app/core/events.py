import json
import logging
from datetime import datetime, timezone
import uuid
import asyncio

from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from app.models.event_log import EventLog
from app.core.config import settings

from app.core.event_contracts import validate_event_payload

logger = logging.getLogger("vesper.events")

# Tenta importar redis (best effort)
try:
    import redis
except ImportError:
    redis = None

class EventStatus:
    PENDING = "PENDING"
    DISPATCHED = "DISPATCHED"
    FAILED = "FAILED"

class EventLogCreate(BaseModel):
    event_type: str
    aggregate_type: str
    aggregate_id: str
    module: str
    payload: Dict[str, Any] = {}
    metadata_json: Dict[str, Any] = {}
    actor_user_id: Optional[int] = None
    correlation_id: Optional[str] = None
    tenant_id: Optional[str] = None

class EventLogRead(BaseModel):
    id: uuid.UUID
    event_type: str
    aggregate_type: str
    aggregate_id: str
    actor_user_id: Optional[int] = None
    module: str
    payload: Dict[str, Any]
    metadata_json: Dict[str, Any]
    status: str
    attempts: int
    last_error: Optional[str] = None
    created_at: datetime
    dispatched_at: Optional[datetime] = None
    correlation_id: Optional[str] = None
    tenant_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class DispatchResult(BaseModel):
    processed: int
    dispatched: int
    failed: int

def emit_event(
    db: Session,
    event_type: str,
    aggregate_type: str,
    aggregate_id: str,
    module: str,
    payload: Dict[str, Any],
    actor_user_id: Optional[int] = None,
    metadata_json: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None,
    tenant_id: Optional[str] = None
) -> EventLog:
    """
    Registra um evento na tabela outbox (event_logs) e tenta publicar no Redis (best-effort).
    A gravação no banco ocorre na transação ativa associada ao 'db' (Outbox pattern).
    Qualquer falha ao publicar no Redis ou carregar a biblioteca não impede a conclusão
    ou faz com que a transação principal sofra rollback.
    """
    # Valida o payload com base no tipo do evento (contrato/schema)
    validated_payload = validate_event_payload(event_type, payload)

    # Injeta a versao do schema nos metadados
    local_metadata = (metadata_json or {}).copy()
    local_metadata["payload_schema_version"] = 1

    event = EventLog(
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=str(aggregate_id),
        actor_user_id=actor_user_id,
        module=module,
        payload=validated_payload,
        metadata_json=local_metadata,
        status=EventStatus.PENDING,
        attempts=0,
        correlation_id=correlation_id,
        tenant_id=tenant_id
    )
    db.add(event)
    db.flush()  # Persiste temporariamente na transação ativa para gerar o ID e created_at

    # Tenta gerar notificações persistentes de forma integrada (Transactional Outbox)
    try:
        from app.modules.notifications.service import handle_event_notifications
        handle_event_notifications(db, event)
    except Exception as e:
        logger.warning(f"[EVENT NOTIFICATION FAILED] Erro ao processar notificacao do evento: {e}")

    # Publicação best-effort no Redis Pub/Sub
    if redis is not None:
        try:
            r = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                socket_connect_timeout=1.0
            )
            event_data = {
                "id": str(event.id),
                "event_type": event.event_type,
                "aggregate_type": event.aggregate_type,
                "aggregate_id": event.aggregate_id,
                "actor_user_id": event.actor_user_id,
                "module": event.module,
                "payload": event.payload,
                "metadata_json": event.metadata_json,
                "correlation_id": event.correlation_id,
                "tenant_id": event.tenant_id,
                "created_at": event.created_at.isoformat()
            }
            channel = f"events:{event.module}"
            r.publish(channel, json.dumps(event_data))
            logger.info(f"[EVENT EMITTED - REDIS] Canal: {channel} | Tipo: {event.event_type} | ID: {event.id}")
        except Exception as e:
            logger.warning(f"[EVENT EMITTED - REDIS FAILED] Falha ao publicar no Redis Pub/Sub: {e}")
    else:
        logger.debug("[EVENT EMITTED - NO REDIS] Biblioteca redis-py indisponivel.")

    logger.info(f"[EVENT EMITTED - DATABASE] Tipo: {event.event_type} | ID: {event.id} | Status: PENDING")
    return event

def dispatch_event(event_name: str, payload: dict) -> None:
    """
    Mantem compatibilidade com chamadas legadas que apenas logavam o evento.
    """
    logger.info(f"[EVENT DISPATCHED LEGACY] Nome: {event_name} | Payload: {payload}")

def dispatch_pending_events(db: Session, limit: int = 50) -> DispatchResult:
    """
    Busca eventos PENDING ou FAILED elegiveis (attempts < 5) ordenados por data ascendente,
    publica no Redis Pub/Sub nos canais padronizados e atualiza status no banco.
    """
    query = db.query(EventLog).filter(
        EventLog.status.in_([EventStatus.PENDING, EventStatus.FAILED]),
        EventLog.attempts < settings.EVENT_DISPATCHER_MAX_ATTEMPTS
    ).order_by(EventLog.created_at.asc())
    
    # Aplica lock transacional (SELECT FOR UPDATE SKIP LOCKED) apenas no PostgreSQL
    try:
        if db.get_bind().dialect.name == "postgresql":
            query = query.with_for_update(skip_locked=True)
    except Exception as dialect_err:
        logger.warning(f"[DISPATCHER] Nao foi possivel determinar o dialect do banco: {dialect_err}")
        
    events = query.limit(limit).all()

    
    processed = 0
    dispatched = 0
    failed = 0
    
    if not events:
        return DispatchResult(processed=0, dispatched=0, failed=0)
        
    r = None
    redis_available = False
    if redis is not None:
        try:
            r = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                socket_connect_timeout=1.0
            )
            r.ping()
            redis_available = True
        except Exception as e:
            logger.warning(f"[DISPATCHER] Falha ao conectar ao Redis para dispatch: {e}")

    for event in events:
        processed += 1
        event.attempts += 1
        
        if not redis_available or r is None:
            event.status = EventStatus.FAILED
            event.last_error = "Redis client unavailable or connection error"
            failed += 1
            continue
            
        try:
            event_data = {
                "id": str(event.id),
                "event_type": event.event_type,
                "aggregate_type": event.aggregate_type,
                "aggregate_id": event.aggregate_id,
                "actor_user_id": event.actor_user_id,
                "module": event.module,
                "payload": event.payload,
                "metadata_json": event.metadata_json,
                "correlation_id": event.correlation_id,
                "tenant_id": event.tenant_id,
                "created_at": event.created_at.isoformat()
            }
            payload_str = json.dumps(event_data)
            
            # Publica nos canais padronizados:
            # 1. events.<event_type>
            # 2. module.<module>
            r.publish(f"events.{event.event_type}", payload_str)
            r.publish(f"module.{event.module}", payload_str)
            
            event.status = EventStatus.DISPATCHED
            event.dispatched_at = datetime.now(timezone.utc)
            event.last_error = None
            dispatched += 1

            # Processa reacoes do Reaction Engine para o evento
            try:
                from app.modules.reactions.service import process_reactions_for_event
                process_reactions_for_event(event, db)
            except Exception as reaction_err:
                logger.error(f"[DISPATCHER] Falha inesperada ao processar reacoes para o evento {event.id}: {reaction_err}")

            # Acoplamento best-effort da ponte n8n se habilitada
            if settings.N8N_WEBHOOK_BRIDGE_ENABLED:
                try:
                    from app.integrations.n8n_client import dispatch_event_to_n8n_bridge
                    dispatch_event_to_n8n_bridge(event)
                except Exception as n8n_err:
                    logger.error(f"[DISPATCHER] Falha inesperada ao tentar enviar evento {event.id} para ponte n8n: {n8n_err}")
        except Exception as e:
            event.status = EventStatus.FAILED
            event.last_error = str(e)
            failed += 1
            logger.error(f"[DISPATCHER] Erro ao despachar evento {event.id}: {e}")

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"[DISPATCHER] Erro de banco ao salvar lote de dispatch: {e}")
        raise e

    return DispatchResult(processed=processed, dispatched=dispatched, failed=failed)

# Globals para gerenciamento do scheduler automático
_dispatcher_running = False
_dispatcher_task: Optional[asyncio.Task] = None
_dispatcher_should_run = True

async def start_event_dispatcher_scheduler():
    """
    Inicia o loop periódico do dispatcher em background.
    """
    global _dispatcher_task, _dispatcher_should_run
    if not settings.EVENT_DISPATCHER_ENABLED:
        logger.info("[SCHEDULER] Dispatcher automático desativado por configuração (EVENT_DISPATCHER_ENABLED=False).")
        return
        
    _dispatcher_should_run = True
    _dispatcher_task = asyncio.create_task(_dispatcher_loop())
    logger.info(f"[SCHEDULER] Dispatcher automático iniciado. Intervalo: {settings.EVENT_DISPATCHER_INTERVAL_SECONDS}s.")

async def stop_event_dispatcher_scheduler():
    """
    Finaliza limpo o loop periódico do dispatcher.
    """
    global _dispatcher_task, _dispatcher_should_run
    logger.info("[SCHEDULER] Parando dispatcher automático...")
    _dispatcher_should_run = False
    if _dispatcher_task:
        _dispatcher_task.cancel()
        try:
            await _dispatcher_task
        except asyncio.CancelledError:
            pass
        _dispatcher_task = None
    logger.info("[SCHEDULER] Dispatcher automático parado com sucesso.")

async def _dispatcher_loop():
    """
    Loop periódico de execução do dispatcher usando asyncio.
    """
    global _dispatcher_running, _dispatcher_should_run
    from app.core.database import SessionLocal
    
    while _dispatcher_should_run:
        try:
            await asyncio.sleep(settings.EVENT_DISPATCHER_INTERVAL_SECONDS)
            
            if not _dispatcher_should_run:
                break
                
            if _dispatcher_running:
                logger.debug("[SCHEDULER] Rodada anterior ainda em execução. Pulando esta execução.")
                continue
                
            _dispatcher_running = True
            logger.info("[SCHEDULER] Iniciando rodada automatica de dispatch.")
            
            db = SessionLocal()
            try:
                result = dispatch_pending_events(db, limit=settings.EVENT_DISPATCHER_BATCH_SIZE)
                if result.processed > 0:
                    logger.info(f"[SCHEDULER] Rodada concluída: processados={result.processed}, despachados={result.dispatched}, falhos={result.failed}")
                else:
                    logger.debug("[SCHEDULER] Sem eventos pendentes para processar.")
            except Exception as db_err:
                logger.error(f"[SCHEDULER] Erro durante processamento do lote: {db_err}")
            finally:
                db.close()
                _dispatcher_running = False
                
        except asyncio.CancelledError:
            break
        except Exception as e:
            _dispatcher_running = False
            logger.error(f"[SCHEDULER] Erro inesperado no loop do dispatcher: {e}")


