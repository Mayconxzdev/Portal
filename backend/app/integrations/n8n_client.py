import hmac
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict

import requests
from pydantic import BaseModel
from app.core.config import settings
from app.models.event_log import EventLog

logger = logging.getLogger("vesper.integrations.n8n")

class N8NDispatchResult(BaseModel):
    success: bool
    status_code: Optional[int] = None
    error_message: Optional[str] = None

# Mapeamento estático inicial de tipos de evento para paths de webhook no n8n
N8N_WEBHOOK_MAP: Dict[str, str] = {
    "approval.created": "/webhook/portal/events/approval-created"
}

def send_event_to_n8n(event: EventLog, webhook_path: str) -> N8NDispatchResult:
    """
    Realiza o envio seguro de um evento para o webhook do n8n utilizando HTTP POST.
    Gera cabeçalhos de assinatura HMAC SHA-256 e provê suporte a retentativas em lote.
    """
    base_url = settings.N8N_BASE_URL.rstrip("/")
    url = f"{base_url}/{webhook_path.lstrip('/')}"
    
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Monta o payload do POST com o envelope padronizado do evento
    body_dict = {
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
        "created_at": event.created_at.isoformat() if event.created_at else timestamp
    }
    
    # 1. Serialização estável (JSON Canônico)
    raw_body_json_canonico = json.dumps(body_dict, sort_keys=True, separators=(",", ":"))
    
    # 2. Criação do HMAC SHA-256 sobre timestamp + event_id + raw_body
    base_string = f"{timestamp}.{str(event.id)}.{raw_body_json_canonico}"
    secret_key = (settings.N8N_WEBHOOK_SECRET or "vesper_n8n_local_secret").encode("utf-8")
    signature = hmac.new(
        secret_key,
        base_string.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    
    # 3. Cabeçalhos obrigatórios
    headers = {
        "Content-Type": "application/json",
        "X-Vesper-Event-Id": str(event.id),
        "X-Vesper-Event-Type": event.event_type,
        "X-Vesper-Timestamp": timestamp,
        "X-Vesper-Signature": signature,
        "X-Vesper-Signature-Version": "v1",
        "X-Idempotency-Key": str(event.id)
    }
    if event.correlation_id:
        headers["X-Vesper-Correlation-Id"] = str(event.correlation_id)
        
    attempts = 0
    max_attempts = settings.N8N_WEBHOOK_MAX_ATTEMPTS
    timeout = settings.N8N_WEBHOOK_TIMEOUT_SECONDS
    
    last_err = None
    status_code = None
    
    while attempts < max_attempts:
        attempts += 1
        try:
            logger.debug(f"[N8N CLIENT] Tentativa {attempts} de {max_attempts} para enviar evento {event.id} para {url}")
            response = requests.post(url, data=raw_body_json_canonico, headers=headers, timeout=timeout)
            status_code = response.status_code
            if response.status_code in (200, 201, 202):
                return N8NDispatchResult(success=True, status_code=status_code)
            else:
                last_err = f"HTTP {response.status_code}: {response.text[:200]}"
                logger.warning(f"[N8N CLIENT - TRY FAILED] Tentativa {attempts} falhou com status {status_code}. Erro: {last_err}")
        except requests.RequestException as req_err:
            last_err = str(req_err)
            logger.warning(f"[N8N CLIENT - TRY ERROR] Tentativa {attempts} falhou com erro de conexao: {last_err}")
            
    return N8NDispatchResult(success=False, status_code=status_code, error_message=last_err)

def dispatch_event_to_n8n_bridge(event: EventLog) -> Optional[N8NDispatchResult]:
    """
    Despacha o evento para a ponte do n8n se o event_type estiver permitido
    na allowlist e mapeado para um webhook path.
    """
    if not settings.N8N_WEBHOOK_BRIDGE_ENABLED:
        logger.debug("[N8N BRIDGE] Ponte n8n desativada (N8N_WEBHOOK_BRIDGE_ENABLED=False).")
        return None
        
    allowed_types = settings.allowed_event_types
    if event.event_type not in allowed_types:
        logger.debug(f"[N8N BRIDGE] Evento '{event.event_type}' nao esta na allowlist.")
        return None
        
    webhook_path = N8N_WEBHOOK_MAP.get(event.event_type)
    if not webhook_path:
        logger.warning(f"[N8N BRIDGE] Evento '{event.event_type}' esta na allowlist, mas nao possui webhook mapeado em N8N_WEBHOOK_MAP.")
        return None
        
    logger.info(f"[N8N BRIDGE] Iniciando despacho do evento {event.id} ({event.event_type}) para n8n...")
    result = send_event_to_n8n(event, webhook_path)
    
    if result.success:
        logger.info(f"[N8N BRIDGE - SUCCESS] Evento {event.id} enviado para n8n com sucesso (Status: {result.status_code}).")
    else:
        logger.warning(f"[N8N BRIDGE - FAILED] Falha ao enviar evento {event.id} para n8n. Erro: {result.error_message}")
        
    return result
