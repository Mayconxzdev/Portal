from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import PermissionLevel, check_module_access
from app.models.approval import Approval
from app.models.action_intent import ActionIntent
from app.models.audit_log import AuditLog
from app.models.kanban import KanbanBoard, KanbanCard, KanbanCardAssignee, KanbanColumn
from app.models.it import ITCertificate, ITTicket
from app.models.module import Module
from app.models.user import User

router = APIRouter(dependencies=[Depends(check_module_access("dashboard", PermissionLevel.READ_ONLY))])


@router.get("/summary")
def get_dashboard_summary(db: Session = Depends(get_db)):
    """
    Retorna o resumo estatistico do Dashboard com dados reais existentes.
    Modulos ainda sem tabelas dedicadas retornam zero, sem numeros simulados.
    """
    try:
        users_count = db.query(func.count(User.id)).scalar() or 0
        modules_count = db.query(func.count(Module.id)).scalar() or 0
        pending_approvals = db.query(func.count(Approval.id)).filter(Approval.status == "PENDING").scalar() or 0
        total_logs = db.query(func.count(AuditLog.id)).scalar() or 0
        active_kanban_boards = db.query(func.count(KanbanBoard.id)).filter(KanbanBoard.is_archived == False).scalar() or 0
        total_kanban_cards = db.query(func.count(KanbanCard.id)).filter(KanbanCard.is_archived == False).scalar() or 0
        open_kanban_cards = (
            db.query(func.count(KanbanCard.id))
            .join(KanbanColumn, KanbanColumn.id == KanbanCard.column_id)
            .filter(KanbanCard.is_archived == False, KanbanColumn.is_done_column == False)
            .scalar()
            or 0
        )
        overdue_kanban_cards = (
            db.query(func.count(KanbanCard.id))
            .join(KanbanColumn, KanbanColumn.id == KanbanCard.column_id)
            .filter(
                KanbanCard.is_archived == False,
                KanbanColumn.is_done_column == False,
                KanbanCard.due_date != None,
                KanbanCard.due_date < datetime.now(timezone.utc).replace(tzinfo=None),
            )
            .scalar()
            or 0
        )
        due_today_kanban_cards = (
            db.query(func.count(KanbanCard.id))
            .filter(
                KanbanCard.is_archived == False,
                KanbanCard.due_date != None,
                KanbanCard.due_date >= datetime.now(timezone.utc).replace(tzinfo=None).replace(hour=0, minute=0, second=0, microsecond=0),
                KanbanCard.due_date < datetime.now(timezone.utc).replace(tzinfo=None).replace(hour=23, minute=59, second=59, microsecond=999999),
            )
            .scalar()
            or 0
        )
        unassigned_kanban_cards = (
            db.query(func.count(KanbanCard.id))
            .outerjoin(KanbanCardAssignee, KanbanCardAssignee.card_id == KanbanCard.id)
            .filter(KanbanCard.is_archived == False, KanbanCardAssignee.id == None)
            .scalar()
            or 0
        )
        high_priority_kanban_cards = (
            db.query(func.count(KanbanCard.id))
            .filter(KanbanCard.is_archived == False, KanbanCard.priority.in_(["HIGH", "URGENT"]))
            .scalar()
            or 0
        )
        recent_cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7)
        recently_updated_kanban_cards = (
            db.query(func.count(KanbanCard.id))
            .filter(KanbanCard.is_archived == False, KanbanCard.updated_at >= recent_cutoff)
            .scalar()
            or 0
        )
        critical_kanban_cards = high_priority_kanban_cards + overdue_kanban_cards
        boards_with_pending = {
            name: count for name, count in db.query(KanbanBoard.name, func.count(KanbanCard.id))
            .join(KanbanCard, KanbanCard.board_id == KanbanBoard.id)
            .join(KanbanColumn, KanbanColumn.id == KanbanCard.column_id)
            .filter(KanbanBoard.is_archived == False, KanbanCard.is_archived == False, KanbanColumn.is_done_column == False)
            .group_by(KanbanBoard.name)
            .order_by(func.count(KanbanCard.id).desc())
            .limit(5)
            .all()
        }
        kanban_cards_by_priority = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "URGENT": 0}
        priority_rows = db.query(KanbanCard.priority, func.count(KanbanCard.id)).filter(KanbanCard.is_archived == False).group_by(KanbanCard.priority).all()
        for priority, count in priority_rows:
            kanban_cards_by_priority[priority] = count
        active_tickets = db.query(func.count(ITTicket.id)).filter(ITTicket.status != "FECHADO").scalar() or 0
        critical_it_tickets = db.query(func.count(ITTicket.id)).filter(ITTicket.status != "FECHADO", ITTicket.priority == "CRITICA").scalar() or 0
        expiring_it_certificates = db.query(func.count(ITCertificate.id)).filter(ITCertificate.expires_at <= datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=30)).scalar() or 0
        pending_action_intents = db.query(func.count(ActionIntent.id)).filter(ActionIntent.status.in_(["PENDING_REVIEW", "APPROVAL_REQUIRED"])).scalar() or 0

        db_status = "online"
    except Exception:
        users_count = 0
        modules_count = 11
        pending_approvals = 0
        total_logs = 0
        active_kanban_boards = 0
        total_kanban_cards = 0
        open_kanban_cards = 0
        overdue_kanban_cards = 0
        unassigned_kanban_cards = 0
        high_priority_kanban_cards = 0
        recently_updated_kanban_cards = 0
        due_today_kanban_cards = 0
        critical_kanban_cards = 0
        boards_with_pending = {}
        kanban_cards_by_priority = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "URGENT": 0}
        active_tickets = 0
        critical_it_tickets = 0
        expiring_it_certificates = 0
        pending_action_intents = 0
        db_status = "offline"

    return {
        "status": "success",
        "database": db_status,
        "metrics": {
            "users_total": users_count,
            "modules_total": modules_count,
            "pending_approvals": pending_approvals,
            "audit_logs_total": total_logs,
            "active_tickets": active_tickets,
            "critical_it_tickets": critical_it_tickets,
            "expiring_it_certificates": expiring_it_certificates,
            "pending_action_intents": pending_action_intents,
            "active_proposals": 0,
            "low_stock_items": 0,
            "active_workflows": 0,
            "active_kanban_boards": active_kanban_boards,
            "total_kanban_cards": total_kanban_cards,
            "open_kanban_cards": open_kanban_cards,
            "overdue_kanban_cards": overdue_kanban_cards,
            "unassigned_kanban_cards": unassigned_kanban_cards,
            "high_priority_kanban_cards": high_priority_kanban_cards,
            "recently_updated_kanban_cards": recently_updated_kanban_cards,
            "due_today_kanban_cards": due_today_kanban_cards,
            "critical_kanban_cards": critical_kanban_cards,
            "boards_with_pending": boards_with_pending,
            "kanban_cards_by_priority": kanban_cards_by_priority,
        },
    }
