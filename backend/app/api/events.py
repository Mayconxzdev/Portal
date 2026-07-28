from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.core.permissions import require_admin
from app.models.user import User
from app.models.event_log import EventLog
from app.core.events import EventLogRead, DispatchResult, dispatch_pending_events

router = APIRouter()

@router.get("/recent", response_model=List[EventLogRead])
def get_recent_events(
    status: Optional[str] = Query(None, description="Filtra por status (PENDING, DISPATCHED, FAILED)"),
    event_type: Optional[str] = Query(None, description="Filtra por tipo de evento"),
    module: Optional[str] = Query(None, description="Filtra por modulo emissor"),
    limit: int = Query(50, ge=1, le=100, description="Limite de registros retornados"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Retorna os eventos recentes registrados na tabela outbox (event_logs).
    Apenas administradores tem permissao para acessar esta listagem.
    """
    query = db.query(EventLog)
    
    if status:
        query = query.filter(EventLog.status == status)
    if event_type:
        query = query.filter(EventLog.event_type == event_type)
    if module:
        query = query.filter(EventLog.module == module)
        
    events = query.order_by(EventLog.created_at.desc()).limit(limit).all()
    
    # Mascarar payloads que possam conter dados sensiveis (ex: senhas ou tokens)
    for event in events:
        if "password" in event.payload:
            event.payload = event.payload.copy()
            event.payload["password"] = "******"
        if "access_token" in event.payload:
            event.payload = event.payload.copy()
            event.payload["access_token"] = "******"
            
    return events

@router.post("/dispatch", response_model=DispatchResult)
def manual_dispatch_events(
    limit: int = Query(50, ge=1, le=200, description="Limite de eventos a processar"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Executa manualmente o processamento do outbox, despachando eventos PENDING/FAILED.
    """
    result = dispatch_pending_events(db, limit=limit)
    return result

@router.post("/{event_id}/send-to-n8n")
def manual_send_event_to_n8n(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Despacha manualmente um evento específico para o webhook do n8n.
    """
    from fastapi import HTTPException
    import uuid
    from app.integrations.n8n_client import dispatch_event_to_n8n_bridge
    from app.core.config import settings

    try:
        event_uuid = uuid.UUID(event_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID de evento invalido (deve ser um UUID).")

    event = db.query(EventLog).filter(EventLog.id == event_uuid).first()
    if not event:
        raise HTTPException(status_code=404, detail="Evento nao encontrado.")

    if not settings.N8N_WEBHOOK_BRIDGE_ENABLED:
        raise HTTPException(status_code=400, detail="Ponte n8n desativada (N8N_WEBHOOK_BRIDGE_ENABLED=False).")

    allowed_types = settings.allowed_event_types
    if event.event_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Tipo de evento '{event.event_type}' nao esta na allowlist.")

    result = dispatch_event_to_n8n_bridge(event)
    if not result:
        raise HTTPException(status_code=400, detail="Nao foi possivel despachar o evento para o n8n (sem mapeamento ou erro de execucao).")

    if not result.success:
        raise HTTPException(status_code=502, detail=f"Falha ao enviar para o n8n: {result.error_message}")

    return {"status": "success", "status_code": result.status_code}

