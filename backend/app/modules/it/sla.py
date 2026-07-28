from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.it import ITSlaPolicy, ITTicket


SLA_COUNTING_STATUSES = {"ABERTO", "EM_ATENDIMENTO"}
SLA_PAUSED_STATUSES = {"SUSPENSO"}
SLA_DONE_STATUSES = {"FECHADO"}


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def find_policy(db: Session, category: str, priority: str) -> Optional[ITSlaPolicy]:
    return (
        db.query(ITSlaPolicy)
        .filter(ITSlaPolicy.is_active == True, ITSlaPolicy.category == category, ITSlaPolicy.priority == priority)
        .first()
        or db.query(ITSlaPolicy)
        .filter(ITSlaPolicy.is_active == True, ITSlaPolicy.category == None, ITSlaPolicy.priority == priority)
        .first()
    )


def apply_sla(db: Session, ticket: ITTicket) -> None:
    if ticket.status in SLA_DONE_STATUSES:
        return
    policy = find_policy(db, ticket.category, ticket.priority)
    if not policy:
        return
    ticket.sla_policy_id = policy.id
    if not ticket.due_at:
        ticket.due_at = ticket.created_at + timedelta(minutes=policy.resolution_minutes)


def sla_state(ticket: ITTicket) -> dict:
    if not ticket.due_at:
        return {"state": "sem_sla", "minutes_remaining": None, "overdue": False}
    if ticket.status in SLA_PAUSED_STATUSES:
        return {"state": "pausado", "minutes_remaining": None, "overdue": False}
    if ticket.status in SLA_DONE_STATUSES:
        return {"state": "encerrado", "minutes_remaining": None, "overdue": False}
    remaining = int((ticket.due_at - now_utc().replace(tzinfo=None)).total_seconds() // 60)
    return {"state": "contando", "minutes_remaining": remaining, "overdue": remaining < 0}
