from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
import logging

logger = logging.getLogger("vesper.health")
router = APIRouter()

@router.get("/health", status_code=status.HTTP_200_OK)
def advanced_health(db: Session = Depends(get_db)):
    """
    Verificação de saúde avançada (Readiness Probe).
    Testa ativamente as conexões com o PostgreSQL.
    """
    postgres_status = "offline"
    try:
        # Testa consulta rápida no PostgreSQL
        db.execute(text("SELECT 1"))
        postgres_status = "online"
    except Exception as e:
        logger.error(f"Falha de conexão com o banco de dados no healthcheck: {str(e)}")
        
    return {
        "status": "online" if postgres_status == "online" else "degraded",
        "services": {
            "api": "online",
            "postgres": postgres_status,
            "redis": "online"  # Placeholder para próxima fase
        }
    }

