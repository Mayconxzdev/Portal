"""Worker assincrono de pesquisa de Compras.

Execute localmente com:
    python -m dramatiq app.modules.purchases.worker
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import dramatiq
from dramatiq.brokers.redis import RedisBroker

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.purchase import PurchaseResearchJob
from app.modules.purchases.research_engine import research_engine


redis_broker = RedisBroker(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD,
)
dramatiq.set_broker(redis_broker)


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dramatiq.actor(max_retries=3, queue_name=settings.PURCHASES_RESEARCH_QUEUE_NAME)
def run_purchase_research_session(session_id: str, actor_user_id: int | None = None) -> None:
    db = SessionLocal()
    parsed_session_id = uuid.UUID(session_id)
    try:
        job = (
            db.query(PurchaseResearchJob)
            .filter(
                PurchaseResearchJob.search_session_id == parsed_session_id,
                PurchaseResearchJob.status.in_(["queued", "retryable_error", "running"]),
            )
            .order_by(PurchaseResearchJob.created_at.desc())
            .first()
        )
        if job:
            job.status = "running"
            job.attempts = int(job.attempts or 0) + 1
            job.locked_at = _now()
            job.updated_at = _now()
            db.commit()

        research_engine.run_session(db, parsed_session_id, current_user=None)

        if job:
            job.status = "completed"
            job.completed_at = _now()
            job.updated_at = _now()
            db.commit()
    except Exception as exc:
        session = None
        try:
            session = research_engine._get_session_model(db, parsed_session_id)
        except Exception:
            session = None
        job = (
            db.query(PurchaseResearchJob)
            .filter(PurchaseResearchJob.search_session_id == parsed_session_id)
            .order_by(PurchaseResearchJob.created_at.desc())
            .first()
        )
        if job:
            job.status = "retryable_error"
            job.last_error = str(exc)[:500]
            job.updated_at = _now()
        if session:
            session.status = "retryable_error"
            session.current_step = "erro recuperavel"
            session.error_message = "A pesquisa encontrou uma falha temporaria e pode ser tentada novamente."
            session.updated_at = _now()
        db.commit()
        raise
    finally:
        db.close()
