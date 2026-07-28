import logging
from sqlalchemy.orm import Session
from typing import Any, Dict, Optional
from datetime import datetime, timezone

logger = logging.getLogger("vesper.audit")

def log_action(
    db: Session,
    user_id: Optional[int],
    action: str,
    module: str,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = "127.0.0.1",
    commit: bool = True
) -> None:
    """
    Registra uma ação realizada no sistema na tabela de logs de auditoria.
    Se commit=True, executa o db.commit() imediatamente (útil para auditorias isoladas).
    Se commit=False, apenas adiciona o objeto à sessão, delegando o commit ao fluxo principal.
    """
    from app.models.audit_log import AuditLog
    
    try:
        audit_entry = AuditLog(
            user_id=user_id,
            action=action,
            module=module,
            details=details or {},
            ip_address=ip_address,
            created_at=datetime.now(timezone.utc)
        )
        db.add(audit_entry)
        if commit:
            db.commit()
        logger.info(f"Audit log criado: Usuário {user_id} - Ação: {action} no módulo {module}")
    except Exception as e:
        logger.error(f"Erro ao salvar log de auditoria no banco: {str(e)}")
        if commit:
            db.rollback()
