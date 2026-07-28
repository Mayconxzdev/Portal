import hmac
import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.config import settings
from app.core.database import get_db
from app.models.event_log import EventLog
from app.models.automation_callback_log import AutomationCallbackLog

logger = logging.getLogger("vesper.api.integrations")

router = APIRouter()

class N8NCallbackPayload(BaseModel):
    event_id: uuid.UUID
    event_type: str
    workflow_id: Optional[str] = None
    workflow_name: Optional[str] = None
    execution_id: Optional[str] = None
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    correlation_id: Optional[str] = None


def mask_sensitive_payload(data: Any) -> Any:
    """
    Substitui recursivamente valores de chaves sensíveis por asteriscos para evitar
    vazamento de credenciais, tokens ou senhas nos logs e respostas.
    """
    if isinstance(data, dict):
        return {
            k: "******" if k.lower() in {"password", "token", "secret", "hashed_password", "key", "vault", "access_token"} else mask_sensitive_payload(v)
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [mask_sensitive_payload(x) for x in data]
    return data


def is_sensitive_action(payload: N8NCallbackPayload) -> bool:
    """
    Verifica se a requisição do callback n8n solicita qualquer ação sensível
    que deva ser bloqueada e tratada de forma manual (requires_manual_action).
    """
    if payload.status == "action_requested":
        return True
        
    sensitive_keywords = {
        "action", "decision", "approve", "reject", "delete", "update",
        "stock", "purchase", "proposal", "credential", "permission", "file", "approval"
    }
    
    if payload.result:
        for k, v in payload.result.items():
            if k.lower() in sensitive_keywords:
                return True
            if isinstance(v, str) and any(kw in v.lower() for kw in sensitive_keywords):
                return True
                
    return False


@router.post("/n8n/callbacks")
async def n8n_callback(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Endpoint Inbound Gateway seguro para receber callbacks/respostas do n8n de volta.
    Valida a assinatura HMAC SHA-256, proteção contra replay attack, idempotência e permissão.
    """
    # 1. Verificar se callbacks estão ativados
    if not settings.N8N_CALLBACKS_ENABLED:
        logger.warning("Callback received but N8N_CALLBACKS_ENABLED is False.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="n8n callbacks are disabled"
        )

    # 2. Validação de Headers Obrigatórios
    x_event_id = request.headers.get("X-Vesper-Event-Id")
    x_callback_type = request.headers.get("X-Vesper-Callback-Type")
    x_timestamp = request.headers.get("X-Vesper-Timestamp")
    x_signature = request.headers.get("X-Vesper-Signature")
    x_sig_version = request.headers.get("X-Vesper-Signature-Version")
    x_idempotency_key = request.headers.get("X-Idempotency-Key")

    if not all([x_event_id, x_callback_type, x_timestamp, x_signature, x_sig_version, x_idempotency_key]):
        logger.warning("Callback rejected due to missing security headers.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required security headers"
        )

    if x_sig_version != "v1":
        logger.warning(f"Callback rejected: Unsupported signature version '{x_sig_version}'")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported signature version"
        )

    # 3. Proteção contra Replay Attack
    try:
        clean_timestamp = x_timestamp.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_timestamp)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    except Exception:
        logger.warning(f"Callback rejected: Invalid timestamp format '{x_timestamp}'")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid X-Vesper-Timestamp format"
        )

    now = datetime.now(timezone.utc)
    elapsed = abs((now - dt).total_seconds())
    if elapsed > settings.N8N_CALLBACK_MAX_AGE_SECONDS:
        logger.warning(f"Callback request expired. Timestamp: {x_timestamp}, Server: {now.isoformat()}, Age: {elapsed}s")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Request expired or timestamp out of bounds"
        )

    # 4. Obter o corpo e calcular a assinatura HMAC SHA-256
    try:
        body_bytes = await request.body()
        body_str = body_bytes.decode("utf-8")
        body_dict = json.loads(body_str) if body_str else {}
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON body"
        )

    # Serialização canônica estável
    raw_body_json_canonico = json.dumps(body_dict, sort_keys=True, separators=(",", ":"))
    
    # Validação do HMAC
    base_string = f"{x_timestamp}.{x_idempotency_key}.{raw_body_json_canonico}"
    secret_key = (settings.N8N_WEBHOOK_SECRET or "vesper_n8n_local_secret").encode("utf-8")
    computed_sig = hmac.new(
        secret_key,
        base_string.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(computed_sig, x_signature):
        logger.warning("Callback rejected: Invalid HMAC signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid HMAC signature"
        )

    # 5. Validação de Idempotência
    existing_log = db.query(AutomationCallbackLog).filter(
        AutomationCallbackLog.idempotency_key == x_idempotency_key
    ).first()
    if existing_log:
        logger.info(f"Duplicate callback ignored for idempotency key: {x_idempotency_key}")
        return {"status": "duplicate_ignored"}

    # 6. Validação do allowlist do X-Vesper-Callback-Type
    allowed_types = settings.allowed_callback_types
    if allowed_types and x_callback_type not in allowed_types:
        logger.warning(f"Callback type '{x_callback_type}' not allowed by config: {allowed_types}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Callback type not allowed"
        )

    # 7. Validação do payload com Pydantic
    try:
        payload = N8NCallbackPayload(**body_dict)
    except Exception as e:
        logger.warning(f"Callback rejected: Payload validation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid payload format: {str(e)}"
        )

    # 8. Validação de Regras de Negócio / Existência de Evento
    event = db.query(EventLog).filter(EventLog.id == payload.event_id).first()
    if not event:
        logger.warning(f"Callback rejected: Event ID {payload.event_id} not found.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    if event.event_type != payload.event_type:
        logger.warning(f"Callback rejected: Event type mismatch. Payload: {payload.event_type}, Database: {event.event_type}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Event type mismatch"
        )

    # 9. Tratamento de Ação Sensível
    callback_type = payload.status
    if is_sensitive_action(payload):
        callback_type = "requires_manual_action"
        logger.warning(
            f"Sensitive action requested by n8n callback. Event: {payload.event_id}. "
            f"Action was blocked. Saved as 'requires_manual_action'."
        )

    # 10. Gravação do log do callback
    masked_body = mask_sensitive_payload(body_dict)
    logger.info(f"Persisting callback log for event {payload.event_id} with type {callback_type}. Content: {masked_body}")

    callback_log = AutomationCallbackLog(
        id=uuid.uuid4(),
        event_id=payload.event_id,
        event_type=payload.event_type,
        workflow_id=payload.workflow_id,
        workflow_name=payload.workflow_name,
        execution_id=payload.execution_id,
        callback_type=callback_type,
        payload=body_dict, # O banco salva o payload bruto real
        error=payload.error,
        idempotency_key=x_idempotency_key,
        signature_valid=True,
        received_at=datetime.now(timezone.utc),
        processed_at=datetime.now(timezone.utc) if callback_type != "requires_manual_action" else None,
        created_by="n8n"
    )

    db.add(callback_log)
    db.commit()
    db.refresh(callback_log)

    # 11. Criação do ActionIntent se for uma ação sensível
    if callback_type == "requires_manual_action":
        try:
            from app.modules.action_intents.schemas import ActionIntentCreateInternal
            from app.modules.action_intents.service import create_action_intent
            
            res_dict = payload.result or {}
            proposed_act = res_dict.get("action") or payload.status or "unknown_action"
            t_module = res_dict.get("target_module") or res_dict.get("module") or event.module or "unknown"
            t_type = res_dict.get("target_type") or event.aggregate_type
            t_id = str(res_dict.get("target_id") or res_dict.get("approval_id") or event.aggregate_id or "")
            
            app_id = None
            if "approval_id" in res_dict:
                try:
                    candidate_id = int(res_dict["approval_id"])
                    from app.models.approval import Approval
                    if db.query(Approval).filter(Approval.id == candidate_id).first():
                        app_id = candidate_id
                except Exception:
                    pass
                    
            intent_create = ActionIntentCreateInternal(
                source="n8n",
                source_ref_type="automation_callback_log",
                source_ref_id=str(callback_log.id),
                proposed_action=proposed_act,
                target_module=t_module,
                target_type=t_type,
                target_id=t_id,
                title=f"Ação proposta por automação: {proposed_act}",
                summary=f"Callback do workflow '{payload.workflow_name or 'desconhecido'}' solicitou a ação '{proposed_act}'.",
                action_payload=res_dict,
                callback_log_id=callback_log.id,
                event_id=payload.event_id,
                approval_id=app_id,
                correlation_id=payload.correlation_id or event.correlation_id,
                tenant_id=event.tenant_id
            )
            action_intent = create_action_intent(db, intent_create)
            callback_log.action_intent_id = str(action_intent.id)
            db.commit()
        except Exception as intent_err:
            logger.error(f"Error creating ActionIntent from sensitive callback: {intent_err}", exc_info=True)

    return {
        "status": "success",
        "callback_id": str(callback_log.id),
        "callback_type": callback_log.callback_type,
        "processed_at": callback_log.processed_at.isoformat() if callback_log.processed_at else None
    }
