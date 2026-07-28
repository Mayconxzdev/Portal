from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import case, exists, func, or_
from sqlalchemy.orm import Session

from app.models.it import (
    ITAccessCatalog,
    ITAccessRequest,
    ITActivity,
    ITAsset,
    ITAssetCustomField,
    ITCertificate,
    ITChecklistTemplate,
    ITChangeLog,
    ITCorporateEmail,
    ITCredential,
    ITMaintenanceRecord,
    ITNASFolder,
    ITNetworkItem,
    ITNote,
    ITSlaPolicy,
    ITTicket,
    ITTicketAttachment,
    ITTicketChecklist,
    ITTicketChecklistItem,
    ITTicketComment,
    ITTicketKanbanLink,
    ITTicketTimeLog,
)
from app.models.kanban import KanbanBoard, KanbanCard, KanbanColumn
from app.models.user import User
from app.modules.it.activity import record_it_activity
from app.modules.it.attachments import UPLOAD_DIR, save_upload_file
from app.modules.it.credentials import decrypt_secret, encrypt_secret
from app.modules.it.events import emit_it_event
from app.modules.it.permissions import is_it_staff, require_it_admin, require_it_staff
from app.modules.it.schemas import (
    AccessCatalogPayload,
    AccessRequestPayload,
    AssetPayload,
    AssignPayload,
    CertificatePayload,
    ChecklistCreate,
    ChecklistItemCreate,
    ChecklistItemUpdate,
    CommentCreate,
    CommentUpdate,
    CreateKanbanCardPayload,
    CredentialCreate,
    CredentialUpdate,
    MaintenancePayload,
    NetworkItemPayload,
    SUSPENSION_REASONS,
    SlaPolicyCreate,
    SlaPolicyUpdate,
    StopTimePayload,
    TICKET_CATEGORIES,
    TICKET_PRIORITIES,
    TICKET_STATUSES,
    TicketCreate,
    TicketPriorityPayload,
    TicketStatusPayload,
    TicketUpdate,
    PcSpecsConfirmPayload,
    ImportCSVConfirmPayload,
)
from app.modules.it.sla import apply_sla, sla_state


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def naive_now() -> datetime:
    return utcnow().replace(tzinfo=None)


class ITService:
    @staticmethod
    def _next_ticket_number(db: Session) -> str:
        max_id = db.query(func.max(ITTicket.id)).scalar() or 0
        return f"TI-{max_id + 1:06d}"

    @staticmethod
    def _validate_category(category: str) -> str:
        if category not in TICKET_CATEGORIES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Categoria invalida.")
        return category

    @staticmethod
    def _validate_priority(priority: str) -> str:
        if priority not in TICKET_PRIORITIES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Prioridade invalida.")
        return priority

    @staticmethod
    def decorate_ticket(db: Session, ticket: ITTicket, current_user: User) -> ITTicket:
        staff = is_it_staff(db, current_user)
        ticket.requester_name = ticket.requester.username if ticket.requester else None
        ticket.assignee_name = ticket.assignee.username if ticket.assignee else None
        ticket.sla = sla_state(ticket)
        ticket.total_time_seconds = sum(log.duration_seconds or 0 for log in ticket.time_logs)
        ticket.comments = [
            comment
            for comment in ticket.comments
            if not comment.deleted_at and (staff or not comment.is_internal)
        ]
        for comment in ticket.comments:
            comment.author_name = comment.user.username if comment.user else None
        for attachment in ticket.attachments:
            if attachment.file:
                attachment.filename = attachment.file.original_filename
                attachment.content_type = attachment.file.content_type
                attachment.size_bytes = attachment.file.size_bytes
        return ticket

    @staticmethod
    def can_view_ticket(db: Session, ticket: ITTicket, current_user: User) -> bool:
        return ticket.requester_user_id == current_user.id or is_it_staff(db, current_user)

    @staticmethod
    def get_ticket(db: Session, ticket_id: int, current_user: User) -> ITTicket:
        ticket = db.query(ITTicket).filter(ITTicket.id == ticket_id).first()
        if not ticket:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chamado nao encontrado.")
        if not ITService.can_view_ticket(db, ticket, current_user):
            record_it_activity(db, current_user, "access.denied", ticket_id=ticket.id, metadata={"reason": "ticket_forbidden"})
            db.commit()
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Voce nao tem acesso a este chamado.")
        return ITService.decorate_ticket(db, ticket, current_user)

    @staticmethod
    def list_tickets(
        db: Session,
        current_user: User,
        *,
        mine: bool = False,
        status_filter: Optional[str] = None,
        q: Optional[str] = None,
        ticket_number: Optional[str] = None,
        requester_user_id: Optional[int] = None,
        assigned_to_user_id: Optional[int] = None,
        category: Optional[str] = None,
        priority: Optional[str] = None,
        sla_state_filter: Optional[str] = None,
        unassigned: bool = False,
        assigned_to_me: bool = False,
        created_today: bool = False,
        recently_updated: bool = False,
        has_attachments: Optional[bool] = None,
        has_kanban_card: Optional[bool] = None,
        missing_kanban_card: Optional[bool] = None,
        sort_by: str = "recentes",
        sort_dir: str = "desc",
    ) -> List[ITTicket]:
        query = db.query(ITTicket)
        if mine or not is_it_staff(db, current_user):
            query = query.filter(ITTicket.requester_user_id == current_user.id)
        if status_filter:
            query = query.filter(ITTicket.status == status_filter)
        if q:
            like = f"%{q}%"
            query = query.filter(or_(ITTicket.title.ilike(like), ITTicket.ticket_number.ilike(like), ITTicket.description.ilike(like)))
        if ticket_number:
            query = query.filter(ITTicket.ticket_number.ilike(f"%{ticket_number}%"))
        if requester_user_id:
            query = query.filter(ITTicket.requester_user_id == requester_user_id)
        if assigned_to_user_id:
            query = query.filter(ITTicket.assigned_to_user_id == assigned_to_user_id)
        if category:
            query = query.filter(ITTicket.category == category)
        if priority:
            query = query.filter(ITTicket.priority == priority)
        if unassigned:
            query = query.filter(ITTicket.assigned_to_user_id == None)
        if assigned_to_me:
            query = query.filter(ITTicket.assigned_to_user_id == current_user.id)
        if created_today:
            today_start = datetime.combine(naive_now().date(), datetime.min.time())
            query = query.filter(ITTicket.created_at >= today_start)
        if recently_updated:
            query = query.filter(ITTicket.updated_at >= naive_now() - timedelta(hours=24))
        if sla_state_filter:
            now = naive_now()
            if sla_state_filter == "overdue":
                query = query.filter(ITTicket.due_at != None, ITTicket.due_at < now, ITTicket.status.notin_(["FECHADO", "SUSPENSO"]))
            elif sla_state_filter == "due_today":
                tomorrow = datetime.combine(now.date() + timedelta(days=1), datetime.min.time())
                query = query.filter(ITTicket.due_at != None, ITTicket.due_at >= now, ITTicket.due_at < tomorrow, ITTicket.status.notin_(["FECHADO", "SUSPENSO"]))
            elif sla_state_filter == "suspended":
                query = query.filter(ITTicket.status == "SUSPENSO")
        if has_attachments is not None:
            attachment_exists = exists().where(ITTicketAttachment.ticket_id == ITTicket.id).where(ITTicketAttachment.deleted_at == None)
            query = query.filter(attachment_exists if has_attachments else ~attachment_exists)
        if has_kanban_card:
            query = query.filter(ITTicket.kanban_card_id != None)
        if missing_kanban_card:
            query = query.filter(ITTicket.kanban_card_id == None)

        priority_order = case(
            (ITTicket.priority == "CRITICA", 4),
            (ITTicket.priority == "ALTA", 3),
            (ITTicket.priority == "MEDIA", 2),
            (ITTicket.priority == "BAIXA", 1),
            else_=0,
        )
        sort_map = {
            "recentes": ITTicket.created_at,
            "antigos": ITTicket.created_at,
            "created_at": ITTicket.created_at,
            "priority": priority_order,
            "prioridade": priority_order,
            "sla": ITTicket.due_at,
            "due_at": ITTicket.due_at,
            "updated_at": ITTicket.updated_at,
            "atualizacao": ITTicket.updated_at,
            "requester": ITTicket.requester_user_id,
            "solicitante": ITTicket.requester_user_id,
            "assignee": ITTicket.assigned_to_user_id,
            "responsavel": ITTicket.assigned_to_user_id,
        }
        sort_column = sort_map.get(sort_by, ITTicket.created_at)
        descending = sort_dir != "asc"
        if sort_by == "antigos":
            descending = False
        query = query.order_by(sort_column.desc().nullslast() if descending else sort_column.asc().nullslast())
        tickets = query.limit(200).all()
        return [ITService.decorate_ticket(db, ticket, current_user) for ticket in tickets]

    @staticmethod
    def create_ticket(db: Session, payload: TicketCreate, current_user: User) -> ITTicket:
        category = ITService._validate_category(payload.category)
        priority = "MEDIA"
        if payload.priority and is_it_staff(db, current_user):
            priority = ITService._validate_priority(payload.priority)
        ticket = ITTicket(
            ticket_number=ITService._next_ticket_number(db),
            title=payload.title.strip(),
            description=payload.description.strip(),
            requester_user_id=current_user.id,
            status="ABERTO",
            priority=priority,
            category=category,
        )
        db.add(ticket)
        db.flush()
        apply_sla(db, ticket)
        ITService._create_checklist_from_template(db, ticket, current_user)
        record_it_activity(db, current_user, "ticket.created", ticket_id=ticket.id, metadata={"ticket_number": ticket.ticket_number, "category": category})
        db.commit()
        db.refresh(ticket)
        emit_it_event(db, event="it.ticket.created", actor=current_user, ticket=ticket, message=f"Chamado {ticket.ticket_number} criado.")
        return ITService.decorate_ticket(db, ticket, current_user)

    @staticmethod
    def _create_checklist_from_template(db: Session, ticket: ITTicket, current_user: User) -> None:
        template = db.query(ITChecklistTemplate).filter(
            ITChecklistTemplate.category == ticket.category,
            ITChecklistTemplate.is_active == True,
        ).order_by(ITChecklistTemplate.id).first()
        if not template:
            return
        checklist = ITTicketChecklist(
            ticket_id=ticket.id,
            title=template.title,
            category=ticket.category,
            position=0,
            created_by_user_id=current_user.id,
        )
        db.add(checklist)
        db.flush()
        for index, text in enumerate(template.items or []):
            db.add(ITTicketChecklistItem(
                checklist_id=checklist.id,
                text=text,
                position=index,
                created_by_user_id=current_user.id,
            ))

    @staticmethod
    def update_ticket(db: Session, ticket_id: int, payload: TicketUpdate, current_user: User) -> ITTicket:
        ticket = ITService.get_ticket(db, ticket_id, current_user)
        if ticket.status == "FECHADO":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chamado fechado nao pode ser reaberto ou alterado.")
        if ticket.requester_user_id != current_user.id:
            require_it_staff(db, current_user)
        data = payload.model_dump(exclude_unset=True)
        if "assigned_to_user_id" in data:
            require_it_staff(db, current_user)
        for key, value in data.items():
            setattr(ticket, key, value)
        if payload.category:
            ITService._validate_category(payload.category)
        record_it_activity(db, current_user, "ticket.updated", ticket_id=ticket.id, metadata={"fields": list(data.keys())})
        db.commit()
        db.refresh(ticket)
        emit_it_event(db, event="it.ticket.updated", actor=current_user, ticket=ticket, message=f"Chamado {ticket.ticket_number} atualizado.", extra={"fields": list(data.keys())})
        return ITService.decorate_ticket(db, ticket, current_user)

    @staticmethod
    def assign_ticket(db: Session, ticket_id: int, payload: AssignPayload, current_user: User) -> ITTicket:
        require_it_staff(db, current_user)
        ticket = ITService.get_ticket(db, ticket_id, current_user)
        ticket.assigned_to_user_id = payload.assigned_to_user_id or current_user.id
        if not ticket.first_response_at:
            ticket.first_response_at = naive_now()
        if ticket.status == "ABERTO":
            ticket.status = "EM_ATENDIMENTO"
        record_it_activity(db, current_user, "ticket.assigned", ticket_id=ticket.id, metadata={"assigned_to_user_id": ticket.assigned_to_user_id})
        db.commit()
        db.refresh(ticket)
        emit_it_event(db, event="it.ticket.assigned", actor=current_user, ticket=ticket, message=f"Chamado {ticket.ticket_number} atribuido.")
        return ITService.decorate_ticket(db, ticket, current_user)

    @staticmethod
    def set_status(db: Session, ticket_id: int, payload: TicketStatusPayload, current_user: User) -> ITTicket:
        require_it_staff(db, current_user)
        ticket = ITService.get_ticket(db, ticket_id, current_user)
        if ticket.status == "FECHADO":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chamado fechado nao pode ser reaberto.")
        if payload.status not in TICKET_STATUSES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Status invalido.")
        if payload.status == "SUSPENSO":
            if payload.suspension_reason not in SUSPENSION_REASONS:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Motivo de suspensao obrigatorio.")
            ticket.suspension_reason = payload.suspension_reason
        elif payload.status != "SUSPENSO":
            ticket.suspension_reason = None
        ticket.status = payload.status
        if payload.status == "FECHADO":
            ticket.resolved_at = naive_now()
            ticket.closed_at = naive_now()
        record_it_activity(db, current_user, "ticket.status_changed", ticket_id=ticket.id, metadata={"status": ticket.status, "suspension_reason": ticket.suspension_reason})
        db.commit()
        db.refresh(ticket)
        emit_it_event(db, event="it.ticket.status_changed", actor=current_user, ticket=ticket, message=f"Status do chamado {ticket.ticket_number} alterado para {ticket.status}.", extra={"status": ticket.status})
        return ITService.decorate_ticket(db, ticket, current_user)

    @staticmethod
    def set_priority(db: Session, ticket_id: int, payload: TicketPriorityPayload, current_user: User) -> ITTicket:
        require_it_staff(db, current_user)
        ticket = ITService.get_ticket(db, ticket_id, current_user)
        ticket.priority = ITService._validate_priority(payload.priority)
        apply_sla(db, ticket)
        record_it_activity(db, current_user, "ticket.updated", ticket_id=ticket.id, metadata={"priority": ticket.priority})
        db.commit()
        db.refresh(ticket)
        emit_it_event(db, event="it.ticket.priority_changed", actor=current_user, ticket=ticket, message=f"Prioridade do chamado {ticket.ticket_number} alterada.", extra={"priority": ticket.priority})
        return ITService.decorate_ticket(db, ticket, current_user)

    @staticmethod
    def add_comment(db: Session, ticket_id: int, payload: CommentCreate, current_user: User) -> ITTicketComment:
        ticket = ITService.get_ticket(db, ticket_id, current_user)
        if payload.is_internal:
            require_it_staff(db, current_user)
        comment = ITTicketComment(ticket_id=ticket.id, user_id=current_user.id, comment=payload.comment.strip(), is_internal=payload.is_internal)
        db.add(comment)
        db.flush()
        record_it_activity(db, current_user, "ticket.internal_comment.created" if payload.is_internal else "ticket.comment.created", ticket_id=ticket.id, metadata={"comment_id": comment.id})
        db.commit()
        db.refresh(comment)
        emit_it_event(
            db,
            event="it.ticket.internal_comment.created" if payload.is_internal else "it.ticket.comment.created",
            actor=current_user,
            ticket=ticket,
            message=f"Novo comentario no chamado {ticket.ticket_number}.",
            internal=payload.is_internal,
            extra={"comment_id": comment.id},
        )
        return comment

    @staticmethod
    def list_comments(db: Session, ticket_id: int, current_user: User) -> List[ITTicketComment]:
        ITService.get_ticket(db, ticket_id, current_user)
        query = db.query(ITTicketComment).filter(ITTicketComment.ticket_id == ticket_id, ITTicketComment.deleted_at == None)
        staff = is_it_staff(db, current_user)
        if not staff:
            query = query.filter(ITTicketComment.is_internal == False)
        comments = query.order_by(ITTicketComment.created_at).all()
        if not staff:
            comments = [comment for comment in comments if not comment.is_internal]
        for comment in comments:
            comment.author_name = comment.user.username if comment.user else None
        return comments

    @staticmethod
    def update_comment(db: Session, comment_id: int, payload: CommentUpdate, current_user: User) -> ITTicketComment:
        comment = db.query(ITTicketComment).filter(ITTicketComment.id == comment_id, ITTicketComment.deleted_at == None).first()
        if not comment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comentario nao encontrado.")
        ITService.get_ticket(db, comment.ticket_id, current_user)
        if comment.user_id != current_user.id and not is_it_staff(db, current_user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissao para editar este comentario.")
        if comment.is_internal:
            require_it_staff(db, current_user)
        comment.comment = payload.comment.strip()
        record_it_activity(db, current_user, "ticket.comment.updated", ticket_id=comment.ticket_id, metadata={"comment_id": comment.id})
        db.commit()
        db.refresh(comment)
        return comment

    @staticmethod
    def delete_comment(db: Session, comment_id: int, current_user: User) -> Dict[str, str]:
        comment = db.query(ITTicketComment).filter(ITTicketComment.id == comment_id, ITTicketComment.deleted_at == None).first()
        if not comment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comentario nao encontrado.")
        ITService.get_ticket(db, comment.ticket_id, current_user)
        if comment.user_id != current_user.id and not is_it_staff(db, current_user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissao para remover este comentario.")
        comment.deleted_at = naive_now()
        record_it_activity(db, current_user, "ticket.comment.deleted", ticket_id=comment.ticket_id, metadata={"comment_id": comment.id})
        db.commit()
        return {"status": "success"}

    @staticmethod
    def list_checklists(db: Session, ticket_id: int, current_user: User) -> List[ITTicketChecklist]:
        ITService.get_ticket(db, ticket_id, current_user)
        return db.query(ITTicketChecklist).filter(ITTicketChecklist.ticket_id == ticket_id).order_by(ITTicketChecklist.position).all()

    @staticmethod
    def create_checklist(db: Session, ticket_id: int, payload: ChecklistCreate, current_user: User) -> ITTicketChecklist:
        require_it_staff(db, current_user)
        ticket = ITService.get_ticket(db, ticket_id, current_user)
        position = db.query(func.count(ITTicketChecklist.id)).filter(ITTicketChecklist.ticket_id == ticket.id).scalar() or 0
        checklist = ITTicketChecklist(ticket_id=ticket.id, title=payload.title, position=position, created_by_user_id=current_user.id)
        db.add(checklist)
        record_it_activity(db, current_user, "checklist.created", ticket_id=ticket.id, metadata={"title": payload.title})
        db.commit()
        db.refresh(checklist)
        return checklist

    @staticmethod
    def add_checklist_item(db: Session, checklist_id: int, payload: ChecklistItemCreate, current_user: User) -> ITTicketChecklistItem:
        require_it_staff(db, current_user)
        checklist = db.query(ITTicketChecklist).filter(ITTicketChecklist.id == checklist_id).first()
        if not checklist:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checklist nao encontrado.")
        ITService.get_ticket(db, checklist.ticket_id, current_user)
        position = db.query(func.count(ITTicketChecklistItem.id)).filter(ITTicketChecklistItem.checklist_id == checklist.id).scalar() or 0
        item = ITTicketChecklistItem(checklist_id=checklist.id, text=payload.text, position=position, created_by_user_id=current_user.id)
        db.add(item)
        record_it_activity(db, current_user, "checklist.item.created", ticket_id=checklist.ticket_id, metadata={"text": payload.text})
        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def update_checklist_item(db: Session, item_id: int, payload: ChecklistItemUpdate, current_user: User) -> ITTicketChecklistItem:
        require_it_staff(db, current_user)
        item = db.query(ITTicketChecklistItem).filter(ITTicketChecklistItem.id == item_id).first()
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item nao encontrado.")
        ITService.get_ticket(db, item.checklist.ticket_id, current_user)
        if payload.text is not None:
            item.text = payload.text
        if payload.is_done is not None:
            item.is_done = payload.is_done
            item.completed_by_user_id = current_user.id if payload.is_done else None
            item.completed_at = naive_now() if payload.is_done else None
        record_it_activity(db, current_user, "checklist.item.checked" if item.is_done else "checklist.item.unchecked", ticket_id=item.checklist.ticket_id, metadata={"item_id": item.id})
        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def delete_checklist_item(db: Session, item_id: int, current_user: User) -> Dict[str, str]:
        require_it_staff(db, current_user)
        item = db.query(ITTicketChecklistItem).filter(ITTicketChecklistItem.id == item_id).first()
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item nao encontrado.")
        ticket_id = item.checklist.ticket_id
        db.delete(item)
        record_it_activity(db, current_user, "checklist.item.deleted", ticket_id=ticket_id, metadata={"item_id": item_id})
        db.commit()
        return {"status": "success"}

    @staticmethod
    def start_time(db: Session, ticket_id: int, current_user: User) -> ITTicketTimeLog:
        require_it_staff(db, current_user)
        ticket = ITService.get_ticket(db, ticket_id, current_user)
        open_log = db.query(ITTicketTimeLog).filter(ITTicketTimeLog.ticket_id == ticket.id, ITTicketTimeLog.user_id == current_user.id, ITTicketTimeLog.ended_at == None).first()
        if open_log:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ja existe um atendimento em andamento para este chamado.")
        log = ITTicketTimeLog(ticket_id=ticket.id, user_id=current_user.id, started_at=naive_now())
        db.add(log)
        record_it_activity(db, current_user, "time.started", ticket_id=ticket.id)
        db.commit()
        db.refresh(log)
        emit_it_event(db, event="it.ticket.time.started", actor=current_user, ticket=ticket, message=f"Atendimento iniciado no chamado {ticket.ticket_number}.")
        return log

    @staticmethod
    def stop_time(db: Session, ticket_id: int, payload: StopTimePayload, current_user: User) -> ITTicketTimeLog:
        require_it_staff(db, current_user)
        ticket = ITService.get_ticket(db, ticket_id, current_user)
        log = db.query(ITTicketTimeLog).filter(ITTicketTimeLog.ticket_id == ticket.id, ITTicketTimeLog.user_id == current_user.id, ITTicketTimeLog.ended_at == None).first()
        if not log:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhum atendimento em andamento.")
        log.ended_at = naive_now()
        log.duration_seconds = int((log.ended_at - log.started_at).total_seconds())
        log.note = payload.note
        record_it_activity(db, current_user, "time.stopped", ticket_id=ticket.id, metadata={"duration_seconds": log.duration_seconds})
        db.commit()
        db.refresh(log)
        emit_it_event(db, event="it.ticket.time.stopped", actor=current_user, ticket=ticket, message=f"Atendimento pausado no chamado {ticket.ticket_number}.", extra={"duration_seconds": log.duration_seconds})
        return log

    @staticmethod
    def list_time_logs(db: Session, ticket_id: int, current_user: User) -> List[ITTicketTimeLog]:
        require_it_staff(db, current_user)
        ITService.get_ticket(db, ticket_id, current_user)
        return db.query(ITTicketTimeLog).filter(ITTicketTimeLog.ticket_id == ticket_id).order_by(ITTicketTimeLog.started_at.desc()).all()

    @staticmethod
    def upload_attachment(db: Session, ticket_id: int, upload: UploadFile, current_user: User, comment_id: Optional[int] = None) -> ITTicketAttachment:
        ticket = ITService.get_ticket(db, ticket_id, current_user)
        file_row = save_upload_file(db, upload, current_user, entity_type="it_ticket", entity_id=ticket.id)
        attachment = ITTicketAttachment(ticket_id=ticket.id, comment_id=comment_id, file_id=file_row.id, uploaded_by_user_id=current_user.id)
        db.add(attachment)
        db.flush()
        record_it_activity(db, current_user, "ticket.attachment.uploaded", ticket_id=ticket.id, metadata={"filename": file_row.original_filename, "attachment_id": attachment.id})
        db.commit()
        db.refresh(attachment)
        emit_it_event(db, event="it.ticket.attachment.created", actor=current_user, ticket=ticket, message=f"Anexo adicionado ao chamado {ticket.ticket_number}.", extra={"attachment_id": attachment.id, "filename": file_row.original_filename})
        attachment.filename = file_row.original_filename
        attachment.content_type = file_row.content_type
        attachment.size_bytes = file_row.size_bytes
        return attachment

    @staticmethod
    def list_attachments(db: Session, ticket_id: int, current_user: User) -> List[ITTicketAttachment]:
        ITService.get_ticket(db, ticket_id, current_user)
        attachments = db.query(ITTicketAttachment).filter(ITTicketAttachment.ticket_id == ticket_id, ITTicketAttachment.deleted_at == None).order_by(ITTicketAttachment.created_at.desc()).all()
        for attachment in attachments:
            if attachment.file:
                attachment.filename = attachment.file.original_filename
                attachment.content_type = attachment.file.content_type
                attachment.size_bytes = attachment.file.size_bytes
        return attachments

    @staticmethod
    def download_attachment(db: Session, attachment_id: int, current_user: User) -> FileResponse:
        attachment = db.query(ITTicketAttachment).filter(ITTicketAttachment.id == attachment_id, ITTicketAttachment.deleted_at == None).first()
        if not attachment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Anexo nao encontrado.")
        ITService.get_ticket(db, attachment.ticket_id, current_user)
        path = UPLOAD_DIR / attachment.file.storage_key
        if not path.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo fisico nao encontrado.")
        record_it_activity(db, current_user, "ticket.attachment.downloaded", ticket_id=attachment.ticket_id, metadata={"attachment_id": attachment.id})
        db.commit()
        return FileResponse(path, media_type=attachment.file.content_type, filename=attachment.file.original_filename)

    @staticmethod
    def delete_attachment(db: Session, attachment_id: int, current_user: User) -> Dict[str, str]:
        attachment = db.query(ITTicketAttachment).filter(ITTicketAttachment.id == attachment_id, ITTicketAttachment.deleted_at == None).first()
        if not attachment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Anexo nao encontrado.")
        ITService.get_ticket(db, attachment.ticket_id, current_user)
        if attachment.uploaded_by_user_id != current_user.id:
            require_it_staff(db, current_user)
        attachment.deleted_at = naive_now()
        attachment.file.deleted_at = naive_now()
        record_it_activity(db, current_user, "ticket.attachment.deleted", ticket_id=attachment.ticket_id, metadata={"attachment_id": attachment.id})
        db.commit()
        return {"status": "success"}

    @staticmethod
    def list_sla_policies(db: Session, current_user: User) -> List[ITSlaPolicy]:
        require_it_staff(db, current_user)
        return db.query(ITSlaPolicy).order_by(ITSlaPolicy.priority, ITSlaPolicy.category).all()

    @staticmethod
    def create_sla_policy(db: Session, payload: SlaPolicyCreate, current_user: User) -> ITSlaPolicy:
        require_it_admin(db, current_user)
        policy = ITSlaPolicy(**payload.model_dump())
        db.add(policy)
        record_it_activity(db, current_user, "sla_policy.created", metadata={"name": policy.name})
        db.commit()
        db.refresh(policy)
        return policy

    @staticmethod
    def update_sla_policy(db: Session, sla_id: int, payload: SlaPolicyUpdate, current_user: User) -> ITSlaPolicy:
        require_it_admin(db, current_user)
        policy = db.query(ITSlaPolicy).filter(ITSlaPolicy.id == sla_id).first()
        if not policy:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Politica nao encontrada.")
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(policy, key, value)
        record_it_activity(db, current_user, "sla_policy.updated", metadata={"sla_id": sla_id})
        db.commit()
        db.refresh(policy)
        return policy

    @staticmethod
    def create_asset(db: Session, payload: AssetPayload, current_user: User) -> ITAsset:
        require_it_staff(db, current_user)
        if payload.asset_tag and db.query(ITAsset).filter(ITAsset.asset_tag == payload.asset_tag).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Patrimonio ja cadastrado.")
        if payload.serial_number and db.query(ITAsset).filter(ITAsset.serial_number == payload.serial_number).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Serial ja cadastrado.")
        asset = ITAsset(**payload.model_dump())
        db.add(asset)
        db.flush()
        record_it_activity(db, current_user, "asset.created", asset_id=asset.id, metadata={"name": asset.name})
        db.commit()
        db.refresh(asset)
        return asset

    @staticmethod
    def list_assets(db: Session, current_user: User) -> List[ITAsset]:
        require_it_staff(db, current_user)
        return db.query(ITAsset).order_by(ITAsset.name).all()

    @staticmethod
    def update_asset(db: Session, asset_id: int, payload: AssetPayload, current_user: User) -> ITAsset:
        require_it_staff(db, current_user)
        asset = db.query(ITAsset).filter(ITAsset.id == asset_id).first()
        if not asset:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipamento nao encontrado.")
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(asset, key, value)
        record_it_activity(db, current_user, "asset.updated", asset_id=asset.id)
        db.commit()
        db.refresh(asset)
        emit_it_event(db, event="it.asset.updated", actor=current_user, entity_type="asset", entity_id=asset.id, message=f"Equipamento {asset.name} atualizado.")
        return asset

    @staticmethod
    def retire_asset(db: Session, asset_id: int, current_user: User) -> ITAsset:
        require_it_staff(db, current_user)
        asset = db.query(ITAsset).filter(ITAsset.id == asset_id).first()
        if not asset:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipamento nao encontrado.")
        asset.status = "APOSENTADO"
        record_it_activity(db, current_user, "asset.retired", asset_id=asset.id)
        db.commit()
        db.refresh(asset)
        return asset

    @staticmethod
    def list_catalog(db: Session, current_user: User) -> List[ITAccessCatalog]:
        require_it_staff(db, current_user)
        return db.query(ITAccessCatalog).filter(ITAccessCatalog.is_active == True).order_by(ITAccessCatalog.system_name).all()

    @staticmethod
    def create_catalog(db: Session, payload: AccessCatalogPayload, current_user: User) -> ITAccessCatalog:
        require_it_staff(db, current_user)
        row = ITAccessCatalog(**payload.model_dump())
        db.add(row)
        db.flush()
        record_it_activity(db, current_user, "access_catalog.created", metadata={"system_name": row.system_name})
        db.commit()
        db.refresh(row)
        return row

    @staticmethod
    def create_access_request(db: Session, payload: AccessRequestPayload, current_user: User) -> ITAccessRequest:
        target_user_id = payload.target_user_id or current_user.id
        if target_user_id != current_user.id and not is_it_staff(db, current_user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissao para solicitar acesso para outro usuario.")
        row = ITAccessRequest(
            requester_user_id=current_user.id,
            target_user_id=target_user_id,
            system_name=payload.system_name,
            access_type=payload.access_type,
            reason=payload.reason,
        )
        db.add(row)
        db.flush()
        record_it_activity(db, current_user, "access_request.created", metadata={"system_name": row.system_name, "access_request_id": row.id})
        
        from app.core.events import emit_event
        emit_event(
            db=db,
            event_type="it.access.requested",
            aggregate_type="it_access_request",
            aggregate_id=str(row.id),
            module="it",
            payload={
                "request_id": row.id,
                "title": f"Solicitacao de acesso ao sistema {row.system_name}",
                "requester_id": current_user.id,
                "system_name": row.system_name
            },
            actor_user_id=current_user.id
        )
        
        db.commit()
        db.refresh(row)
        return row

    @staticmethod
    def list_access_requests(db: Session, current_user: User) -> List[ITAccessRequest]:
        query = db.query(ITAccessRequest)
        if not is_it_staff(db, current_user):
            query = query.filter(ITAccessRequest.requester_user_id == current_user.id)
        return query.order_by(ITAccessRequest.created_at.desc()).all()

    @staticmethod
    def list_credentials(db: Session, current_user: User) -> List[ITCredential]:
        require_it_staff(db, current_user)
        return db.query(ITCredential).filter(ITCredential.is_active == True).order_by(ITCredential.system_name, ITCredential.title).all()

    @staticmethod
    def create_credential(db: Session, payload: CredentialCreate, current_user: User) -> ITCredential:
        require_it_admin(db, current_user)
        data = payload.model_dump()
        secret = data.pop("secret")
        row = ITCredential(**data, secret_encrypted=encrypt_secret(secret), created_by_user_id=current_user.id)
        db.add(row)
        db.flush()
        record_it_activity(db, current_user, "credential.created", credential_id=row.id, metadata={"title": row.title, "system_name": row.system_name})
        db.commit()
        db.refresh(row)
        return row

    @staticmethod
    def update_credential(db: Session, credential_id: int, payload: CredentialUpdate, current_user: User) -> ITCredential:
        require_it_admin(db, current_user)
        row = db.query(ITCredential).filter(ITCredential.id == credential_id).first()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credencial nao encontrada.")
        data = payload.model_dump(exclude_unset=True)
        if "secret" in data:
            row.secret_encrypted = encrypt_secret(data.pop("secret"))
        for key, value in data.items():
            setattr(row, key, value)
        row.updated_by_user_id = current_user.id
        record_it_activity(db, current_user, "credential.updated", credential_id=row.id, metadata={"fields": list(data.keys())})
        db.commit()
        db.refresh(row)
        return row

    @staticmethod
    def reveal_credential(db: Session, credential_id: int, current_user: User, *, copied: bool = False) -> Dict[str, Any]:
        require_it_admin(db, current_user)
        row = db.query(ITCredential).filter(ITCredential.id == credential_id, ITCredential.is_active == True).first()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credencial nao encontrada.")
        row.last_revealed_at = naive_now()
        row.last_revealed_by_user_id = current_user.id
        action = "credential.copied" if copied else "credential.revealed"
        record_it_activity(db, current_user, action, credential_id=row.id, metadata={"credential_id": row.id, "system_name": row.system_name})
        secret = decrypt_secret(row.secret_encrypted)
        db.commit()
        emit_it_event(db, event="it.credential.revealed" if not copied else "it.credential.copied", actor=current_user, entity_type="credential", entity_id=row.id, message=f"Credencial {row.title} acessada.")
        try:
            from app.models.user import User
            from app.modules.notifications.service import create_notification_for_user

            recipients = db.query(User).filter(User.is_active == True).all()
            for recipient in recipients:
                role_name = recipient.role.name if recipient.role else ""
                if role_name in {"ADMIN", "MESSIAS"}:
                    create_notification_for_user(
                        db=db,
                        user_id=recipient.id,
                        module="it",
                        event_type="vault.secret.revealed",
                        title="Credencial revelada no Cofre",
                        message=f"{current_user.username} acessou uma credencial do sistema {row.system_name}.",
                        severity="WARNING",
                        source_type="it_credential",
                        source_id=str(row.id),
                        payload_json={
                            "credential_id": row.id,
                            "system_name": row.system_name,
                            "actor_user_id": current_user.id,
                            "copied": copied,
                            "contains_secret": False,
                        },
                    )
        except Exception:
            pass
        db.commit()
        return {"id": row.id, "secret": secret}

    @staticmethod
    def disable_credential(db: Session, credential_id: int, current_user: User) -> Dict[str, str]:
        require_it_admin(db, current_user)
        row = db.query(ITCredential).filter(ITCredential.id == credential_id).first()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credencial nao encontrada.")
        row.is_active = False
        record_it_activity(db, current_user, "credential.disabled", credential_id=row.id, metadata={"credential_id": row.id})
        db.commit()
        return {"status": "success"}

    @staticmethod
    def delete_credential(db: Session, credential_id: int, current_user: User) -> Dict[str, str]:
        require_it_admin(db, current_user)
        row = db.query(ITCredential).filter(ITCredential.id == credential_id).first()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credencial nao encontrada.")
        db.delete(row)
        record_it_activity(db, current_user, "credential.deleted", credential_id=credential_id, metadata={"credential_id": credential_id})
        db.commit()
        return {"status": "success"}

    @staticmethod
    def _certificate_status(expires_at: datetime) -> str:
        days = (expires_at - naive_now()).days
        if days < 0:
            return "VENCIDO"
        if days <= 30:
            return "VENCENDO"
        return "VALIDO"

    @staticmethod
    def list_certificates(db: Session, current_user: User) -> List[ITCertificate]:
        require_it_staff(db, current_user)
        certs = db.query(ITCertificate).order_by(ITCertificate.expires_at).all()
        for cert in certs:
            cert.status = ITService._certificate_status(cert.expires_at)
        db.commit()
        return certs

    @staticmethod
    def create_certificate(db: Session, payload: CertificatePayload, current_user: User) -> ITCertificate:
        require_it_staff(db, current_user)
        row = ITCertificate(**payload.model_dump(), status=ITService._certificate_status(payload.expires_at))
        db.add(row)
        db.flush()
        record_it_activity(db, current_user, "certificate.created", certificate_id=row.id, metadata={"name": row.name})
        db.commit()
        db.refresh(row)
        return row

    @staticmethod
    def list_network_items(db: Session, current_user: User) -> List[ITNetworkItem]:
        require_it_staff(db, current_user)
        return db.query(ITNetworkItem).order_by(ITNetworkItem.name).all()

    @staticmethod
    def create_network_item(db: Session, payload: NetworkItemPayload, current_user: User) -> ITNetworkItem:
        require_it_staff(db, current_user)
        row = ITNetworkItem(**payload.model_dump())
        db.add(row)
        db.flush()
        record_it_activity(db, current_user, "network_item.created", network_item_id=row.id, metadata={"name": row.name})
        db.commit()
        db.refresh(row)
        return row

    @staticmethod
    def list_maintenance(db: Session, current_user: User) -> List[ITMaintenanceRecord]:
        require_it_staff(db, current_user)
        return db.query(ITMaintenanceRecord).order_by(ITMaintenanceRecord.created_at.desc()).all()

    @staticmethod
    def create_maintenance(db: Session, payload: MaintenancePayload, current_user: User) -> ITMaintenanceRecord:
        require_it_staff(db, current_user)
        row = ITMaintenanceRecord(**payload.model_dump())
        db.add(row)
        db.flush()
        record_it_activity(db, current_user, "maintenance.created", ticket_id=row.ticket_id, asset_id=row.asset_id, network_item_id=row.network_item_id, metadata={"title": row.title})
        db.commit()
        db.refresh(row)
        emit_it_event(db, event="it.maintenance.updated", actor=current_user, entity_type="maintenance", entity_id=row.id, message=f"Manutencao {row.title} criada.")
        return row

    @staticmethod
    def create_kanban_card(db: Session, ticket_id: int, payload: CreateKanbanCardPayload, current_user: User) -> Dict[str, Any]:
        require_it_staff(db, current_user)
        ticket = ITService.get_ticket(db, ticket_id, current_user)
        if ticket.kanban_card_id and not payload.allow_duplicate:
            return {"status": "already_linked", "kanban_card_id": ticket.kanban_card_id}
        board = None
        if payload.board_id:
            board = db.query(KanbanBoard).filter(KanbanBoard.id == payload.board_id, KanbanBoard.is_archived == False).first()
        else:
            board = db.query(KanbanBoard).filter(KanbanBoard.slug == "ti", KanbanBoard.is_archived == False).first()
        if not board:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Board TI nao encontrado.")
        column = None
        if payload.column_id:
            column = db.query(KanbanColumn).filter(KanbanColumn.id == payload.column_id, KanbanColumn.board_id == board.id, KanbanColumn.is_archived == False).first()
        else:
            column = db.query(KanbanColumn).filter(KanbanColumn.board_id == board.id, KanbanColumn.is_archived == False).order_by(KanbanColumn.position).first()
        if not column:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Coluna invalida para card de TI.")
        position = db.query(func.count(KanbanCard.id)).filter(KanbanCard.column_id == column.id, KanbanCard.is_archived == False).scalar() or 0
        card = KanbanCard(
            board_id=board.id,
            column_id=column.id,
            title=f"[{ticket.ticket_number}] {ticket.title}",
            description=f"Chamado: {ticket.ticket_number}\nCategoria: {ticket.category}\nSolicitante: {ticket.requester.username if ticket.requester else ticket.requester_user_id}\nStatus: {ticket.status}\n\n{ticket.description}",
            priority={"BAIXA": "LOW", "MEDIA": "MEDIUM", "ALTA": "HIGH", "CRITICA": "URGENT"}.get(ticket.priority, "MEDIUM"),
            position=position,
            created_by_user_id=current_user.id,
        )
        db.add(card)
        db.flush()
        db.add(ITTicketKanbanLink(ticket_id=ticket.id, kanban_card_id=card.id, created_by_user_id=current_user.id))
        if not ticket.kanban_card_id:
            ticket.kanban_card_id = card.id
        record_it_activity(db, current_user, "ticket.kanban_card.created", ticket_id=ticket.id, metadata={"kanban_card_id": card.id, "board_id": board.id})
        db.commit()
        emit_it_event(db, event="it.ticket.kanban_link.created", actor=current_user, ticket=ticket, message=f"Card Kanban criado para {ticket.ticket_number}.", extra={"kanban_card_id": card.id, "board_id": board.id})
        return {"status": "created", "kanban_card_id": card.id, "board_id": board.id}

    @staticmethod
    def get_kanban_link(db: Session, ticket_id: int, current_user: User) -> Dict[str, Any]:
        ticket = ITService.get_ticket(db, ticket_id, current_user)
        return {"ticket_id": ticket.id, "kanban_card_id": ticket.kanban_card_id}

    @staticmethod
    def summary(db: Session, current_user: User) -> Dict[str, int]:
        staff = is_it_staff(db, current_user)
        base = db.query(ITTicket)
        mine = db.query(ITTicket).filter(ITTicket.requester_user_id == current_user.id)
        visible = base if staff else mine
        today = naive_now().date()
        expiring = db.query(ITCertificate).filter(ITCertificate.expires_at <= naive_now() + timedelta(days=30)).count() if staff else 0
        return {
            "open_tickets": visible.filter(ITTicket.status == "ABERTO").count(),
            "in_progress_tickets": visible.filter(ITTicket.status == "EM_ATENDIMENTO").count(),
            "suspended_tickets": visible.filter(ITTicket.status == "SUSPENSO").count(),
            "closed_today": visible.filter(ITTicket.status == "FECHADO", func.date(ITTicket.closed_at) == today).count(),
            "overdue_tickets": visible.filter(ITTicket.due_at != None, ITTicket.due_at < naive_now(), ITTicket.status != "FECHADO").count(),
            "critical_tickets": visible.filter(ITTicket.priority == "CRITICA", ITTicket.status != "FECHADO").count(),
            "expiring_certificates": expiring,
            "assets_in_maintenance": db.query(ITAsset).filter(ITAsset.status == "MANUTENCAO").count() if staff else 0,
            "my_tickets": mine.filter(ITTicket.status != "FECHADO").count(),
            "assigned_to_me": base.filter(ITTicket.assigned_to_user_id == current_user.id, ITTicket.status != "FECHADO").count() if staff else 0,
        }

    @staticmethod
    def activity(db: Session, current_user: User) -> List[ITActivity]:
        require_it_staff(db, current_user)
        return db.query(ITActivity).order_by(ITActivity.created_at.desc()).limit(100).all()

    @staticmethod
    def report_summary(db: Session, current_user: User) -> Dict[str, int]:
        require_it_staff(db, current_user)
        return ITService.summary(db, current_user)

    @staticmethod
    def report_tickets_by_category(db: Session, current_user: User) -> List[Dict[str, Any]]:
        require_it_staff(db, current_user)
        rows = db.query(ITTicket.category, func.count(ITTicket.id)).group_by(ITTicket.category).order_by(ITTicket.category).all()
        return [{"category": category, "count": count} for category, count in rows]

    @staticmethod
    def report_tickets_by_status(db: Session, current_user: User) -> List[Dict[str, Any]]:
        require_it_staff(db, current_user)
        rows = db.query(ITTicket.status, func.count(ITTicket.id)).group_by(ITTicket.status).order_by(ITTicket.status).all()
        return [{"status": status_value, "count": count} for status_value, count in rows]

    @staticmethod
    def report_sla(db: Session, current_user: User) -> Dict[str, int]:
        require_it_staff(db, current_user)
        now = naive_now()
        today_end = datetime.combine(now.date() + timedelta(days=1), datetime.min.time())
        active = db.query(ITTicket).filter(ITTicket.status.notin_(["FECHADO", "SUSPENSO"]))
        return {
            "overdue": active.filter(ITTicket.due_at != None, ITTicket.due_at < now).count(),
            "due_today": active.filter(ITTicket.due_at != None, ITTicket.due_at >= now, ITTicket.due_at < today_end).count(),
            "without_due_date": active.filter(ITTicket.due_at == None).count(),
            "suspended": db.query(ITTicket).filter(ITTicket.status == "SUSPENSO").count(),
        }

    @staticmethod
    def report_technician_time(db: Session, current_user: User) -> List[Dict[str, Any]]:
        require_it_staff(db, current_user)
        rows = (
            db.query(User.username, func.coalesce(func.sum(ITTicketTimeLog.duration_seconds), 0))
            .join(ITTicketTimeLog, ITTicketTimeLog.user_id == User.id)
            .group_by(User.username)
            .order_by(User.username)
            .all()
        )
        return [{"technician": username, "duration_seconds": int(duration or 0)} for username, duration in rows]

    @staticmethod
    def report_assets(db: Session, current_user: User) -> List[Dict[str, Any]]:
        require_it_staff(db, current_user)
        rows = db.query(ITAsset.status, func.count(ITAsset.id)).group_by(ITAsset.status).order_by(ITAsset.status).all()
        return [{"status": status_value, "count": count} for status_value, count in rows]

    @staticmethod
    def report_certificates(db: Session, current_user: User) -> Dict[str, int]:
        require_it_staff(db, current_user)
        now = naive_now()
        return {
            "valid": db.query(ITCertificate).filter(ITCertificate.expires_at > now + timedelta(days=30)).count(),
            "expiring": db.query(ITCertificate).filter(ITCertificate.expires_at <= now + timedelta(days=30), ITCertificate.expires_at >= now).count(),
            "expired": db.query(ITCertificate).filter(ITCertificate.expires_at < now).count(),
        }

    # === NOVOS MÉTODOS FASE 5.2 ===

    @staticmethod
    def list_people(db: Session, current_user: User) -> List[Dict[str, Any]]:
        require_it_staff(db, current_user)
        users = db.query(User).filter(User.is_active == True).all()
        result = []
        for u in users:
            # Busca computador principal do usuário
            asset = db.query(ITAsset).filter(
                ITAsset.assigned_to_user_id == u.id, 
                ITAsset.asset_type.in_(["PC", "NOTEBOOK"])
            ).first()
            
            result.append({
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "role_id": u.role_id,
                "role_name": u.role.name if u.role else None,
                "is_active": u.is_active,
                "ramal": asset.ramal if asset else None,
                "ip_address": asset.ip_address if asset else None,
                "network_point": asset.network_point if asset else None,
                "sector": asset.sector if asset else None,
                "it_responsible": asset.it_responsible if asset else None,
                "asset_id": asset.id if asset else None,
                "asset_name": asset.name if asset else None,
                "asset_tag": asset.asset_tag if asset else None,
            })
        return result

    @staticmethod
    def create_person(db: Session, payload: Any, current_user: User) -> User:
        require_it_admin(db, current_user)
        from app.models.user import User
        from app.core.security import get_password_hash
        
        # Cria o usuário do sistema
        hashed_pass = get_password_hash("vesper123") # Senha padrão inicial
        u = User(
            username=payload.username.strip(),
            email=payload.email.strip(),
            hashed_password=hashed_pass,
            role_id=payload.role_id,
            is_active=True
        )
        db.add(u)
        db.flush()
        
        # Se informou dados de TI, cria um ativo de PC padrão para ele
        if any([payload.ramal, payload.ip_address, payload.network_point, payload.sector]):
            asset = ITAsset(
                name=f"Computador de {u.username}",
                asset_type="PC",
                status="EM_USO",
                assigned_to_user_id=u.id,
                ramal=payload.ramal,
                ip_address=payload.ip_address,
                network_point=payload.network_point,
                sector=payload.sector,
                it_responsible=payload.it_responsible
            )
            db.add(asset)
            db.flush()
            ITService.log_change(db, current_user.id, "ITAsset", asset.id, "CREATE", new_data=asset.__dict__)
            
        db.commit()
        db.refresh(u)
        return u

    @staticmethod
    def update_person(db: Session, person_id: int, payload: Any, current_user: User) -> Dict[str, Any]:
        require_it_admin(db, current_user)
        u = db.query(User).filter(User.id == person_id).first()
        if not u:
            raise HTTPException(status_code=404, detail="Usuário não encontrado.")
            
        u.username = payload.username
        u.email = payload.email
        if payload.role_id:
            u.role_id = payload.role_id
        u.is_active = payload.is_active
        db.flush()

        # Atualiza ou cria o ativo de PC associado
        asset = db.query(ITAsset).filter(
            ITAsset.assigned_to_user_id == u.id, 
            ITAsset.asset_type.in_(["PC", "NOTEBOOK"])
        ).first()
        
        if not asset:
            asset = ITAsset(
                name=f"Computador de {u.username}",
                asset_type="PC",
                status="EM_USO",
                assigned_to_user_id=u.id
            )
            db.add(asset)
            db.flush()
            
        old_data = asset.__dict__.copy()
        asset.ramal = payload.ramal
        asset.ip_address = payload.ip_address
        asset.network_point = payload.network_point
        asset.sector = payload.sector
        asset.it_responsible = payload.it_responsible
        db.flush()
        
        ITService.log_change(db, current_user.id, "ITAsset", asset.id, "UPDATE", old_data=old_data, new_data=asset.__dict__)
        db.commit()
        db.refresh(u)
        
        return {"status": "success"}

    @staticmethod
    def archive_person(db: Session, person_id: int, current_user: User) -> Dict[str, str]:
        require_it_admin(db, current_user)
        u = db.query(User).filter(User.id == person_id).first()
        if not u:
            raise HTTPException(status_code=404, detail="Usuário não encontrado.")
        u.is_active = False
        db.commit()
        return {"status": "success"}

    # --- CAMPOS PERSONALIZADOS DE ATIVOS ---
    @staticmethod
    def list_custom_fields(db: Session, current_user: User) -> List[ITAssetCustomField]:
        require_it_staff(db, current_user)
        return db.query(ITAssetCustomField).filter(ITAssetCustomField.is_active == True).all()

    @staticmethod
    def create_custom_field(db: Session, payload: Any, current_user: User) -> ITAssetCustomField:
        require_it_admin(db, current_user)
        field = ITAssetCustomField(
            name=payload.name.strip(),
            field_type=payload.field_type,
            options=payload.options or []
        )
        db.add(field)
        db.commit()
        db.refresh(field)
        return field

    @staticmethod
    def update_custom_field(db: Session, field_id: int, payload: Any, current_user: User) -> ITAssetCustomField:
        require_it_admin(db, current_user)
        field = db.query(ITAssetCustomField).filter(ITAssetCustomField.id == field_id).first()
        if not field:
            raise HTTPException(status_code=404, detail="Campo não encontrado.")
        field.name = payload.name
        field.field_type = payload.field_type
        field.options = payload.options or []
        db.commit()
        db.refresh(field)
        return field

    @staticmethod
    def disable_custom_field(db: Session, field_id: int, current_user: User) -> Dict[str, str]:
        require_it_admin(db, current_user)
        field = db.query(ITAssetCustomField).filter(ITAssetCustomField.id == field_id).first()
        if not field:
            raise HTTPException(status_code=404, detail="Campo não encontrado.")
        field.is_active = False
        db.commit()
        return {"status": "success"}

    # --- E-MAILS CORPORATIVOS ---
    @staticmethod
    def list_corporate_emails(db: Session, current_user: User) -> List[ITCorporateEmail]:
        require_it_staff(db, current_user)
        return db.query(ITCorporateEmail).order_by(ITCorporateEmail.email_address).all()

    @staticmethod
    def create_corporate_email(db: Session, payload: Any, current_user: User) -> ITCorporateEmail:
        require_it_staff(db, current_user)
        email = ITCorporateEmail(
            email_address=payload.email_address.strip(),
            login=payload.login,
            user_id=payload.user_id,
            server_config=payload.server_config,
            recommended_client=payload.recommended_client,
            status=payload.status,
            credential_id=payload.credential_id
        )
        db.add(email)
        db.flush()
        ITService.log_change(db, current_user.id, "ITCorporateEmail", email.id, "CREATE", new_data=email.__dict__)
        db.commit()
        db.refresh(email)
        return email

    @staticmethod
    def update_corporate_email(db: Session, email_id: int, payload: Any, current_user: User) -> ITCorporateEmail:
        require_it_staff(db, current_user)
        email = db.query(ITCorporateEmail).filter(ITCorporateEmail.id == email_id).first()
        if not email:
            raise HTTPException(status_code=404, detail="E-mail não encontrado.")
        
        old_data = email.__dict__.copy()
        email.email_address = payload.email_address
        email.login = payload.login
        email.user_id = payload.user_id
        email.server_config = payload.server_config
        email.recommended_client = payload.recommended_client
        email.status = payload.status
        email.credential_id = payload.credential_id
        db.flush()
        
        ITService.log_change(db, current_user.id, "ITCorporateEmail", email.id, "UPDATE", old_data=old_data, new_data=email.__dict__)
        db.commit()
        db.refresh(email)
        return email

    # --- PASTAS NAS / QNAP ---
    @staticmethod
    def list_nas_folders(db: Session, current_user: User) -> List[ITNASFolder]:
        require_it_staff(db, current_user)
        return db.query(ITNASFolder).order_by(ITNASFolder.name).all()

    @staticmethod
    def create_nas_folder(db: Session, payload: Any, current_user: User) -> ITNASFolder:
        require_it_staff(db, current_user)
        folder = ITNASFolder(
            name=payload.name.strip(),
            network_path=payload.network_path,
            drive_letter=payload.drive_letter,
            user_id=payload.user_id,
            permission_level=payload.permission_level,
            notes=payload.notes
        )
        db.add(folder)
        db.flush()
        ITService.log_change(db, current_user.id, "ITNASFolder", folder.id, "CREATE", new_data=folder.__dict__)
        db.commit()
        db.refresh(folder)
        return folder

    @staticmethod
    def update_nas_folder(db: Session, folder_id: int, payload: Any, current_user: User) -> ITNASFolder:
        require_it_staff(db, current_user)
        folder = db.query(ITNASFolder).filter(ITNASFolder.id == folder_id).first()
        if not folder:
            raise HTTPException(status_code=404, detail="Pasta NAS não encontrada.")
            
        old_data = folder.__dict__.copy()
        folder.name = payload.name
        folder.network_path = payload.network_path
        folder.drive_letter = payload.drive_letter
        folder.user_id = payload.user_id
        folder.permission_level = payload.permission_level
        folder.notes = payload.notes
        db.flush()
        
        ITService.log_change(db, current_user.id, "ITNASFolder", folder.id, "UPDATE", old_data=old_data, new_data=folder.__dict__)
        db.commit()
        db.refresh(folder)
        return folder

    # --- NOTAS (STICKY NOTES) ---
    @staticmethod
    def list_notes(db: Session, current_user: User) -> List[ITNote]:
        # Notas podem ser vistas por toda a equipe de TI, e usuários comuns veem as que criaram ou atribuídas a eles
        staff = is_it_staff(db, current_user)
        query = db.query(ITNote).filter(ITNote.is_archived == False)
        if not staff:
            query = query.filter((ITNote.created_by_user_id == current_user.id) | (ITNote.responsible_user_id == current_user.id))
        return query.order_by(ITNote.is_pinned.desc(), ITNote.updated_at.desc()).all()

    @staticmethod
    def create_note(db: Session, payload: Any, current_user: User) -> ITNote:
        note = ITNote(
            title=payload.title,
            content=payload.content,
            color=payload.color or "yellow",
            tags=payload.tags or [],
            responsible_user_id=payload.responsible_user_id,
            is_pinned=payload.is_pinned,
            created_by_user_id=current_user.id
        )
        db.add(note)
        db.commit()
        db.refresh(note)
        return note

    @staticmethod
    def update_note(db: Session, note_id: int, payload: Any, current_user: User) -> ITNote:
        note = db.query(ITNote).filter(ITNote.id == note_id).first()
        if not note:
            raise HTTPException(status_code=404, detail="Nota não encontrada.")
        # Só o criador ou técnico pode editar
        if note.created_by_user_id != current_user.id and not is_it_staff(db, current_user):
            raise HTTPException(status_code=403, detail="Sem permissão para editar esta nota.")
        
        note.title = payload.title
        note.content = payload.content
        note.color = payload.color
        note.tags = payload.tags or []
        note.responsible_user_id = payload.responsible_user_id
        note.is_pinned = payload.is_pinned
        note.is_archived = payload.is_archived
        db.commit()
        db.refresh(note)
        return note

    # --- AUDITORIA ISO 9001 ---
    @staticmethod
    def get_change_logs(db: Session, current_user: User) -> List[ITChangeLog]:
        require_it_staff(db, current_user)
        return db.query(ITChangeLog).order_by(ITChangeLog.created_at.desc()).limit(200).all()

    @staticmethod
    def log_change(db: Session, user_id: int, entity_type: str, entity_id: int, action: str, old_data: Optional[dict] = None, new_data: Optional[dict] = None, reason: Optional[str] = None, origin: str = "MANUAL", ip_address: Optional[str] = None):
        from app.models.it import ITChangeLog
        old_data = old_data or {}
        new_data = new_data or {}
        
        # Mapeamento de chaves para auditar
        keys_to_audit = [
            "name", "serial_number", "asset_tag", "status", "assigned_to_user_id", "location",
            "hostname", "processor", "ram", "motherboard", "gpu", "storage", "ip_address", "ramal",
            "email_address", "login", "server_config", "credential_id", "drive_letter", "permission_level"
        ]
        
        for key in keys_to_audit:
            old_val = old_data.get(key)
            new_val = new_data.get(key)
            if old_val == new_val or (old_val is None and new_val is None):
                continue
                
            # Mascara credenciais/valores sensíveis
            if "credential" in key or "secret" in key:
                old_val_str = "[VALOR PROTEGIDO]" if old_val else None
                new_val_str = "[VALOR PROTEGIDO]" if new_val else None
            else:
                old_val_str = str(old_val) if old_val is not None else None
                new_val_str = str(new_val) if new_val is not None else None
                
            log = ITChangeLog(
                entity_type=entity_type,
                entity_id=entity_id,
                action=action,
                field_name=key,
                old_value=old_val_str,
                new_value=new_val_str,
                reason=reason,
                origin=origin,
                ip_address=ip_address,
                user_id=user_id
            )
            db.add(log)
        db.flush()

    # --- COLETA E IMPORTAÇÃO DE SPECS ---
    @staticmethod
    def preview_specs(db: Session, data: dict, current_user: User) -> Dict[str, Any]:
        require_it_staff(db, current_user)
        serial = data.get("serial_number")
        hostname = data.get("hostname")
        
        # Tenta achar ativo existente
        asset = None
        if serial:
            asset = db.query(ITAsset).filter(ITAsset.serial_number == serial).first()
        if not asset and hostname:
            asset = db.query(ITAsset).filter(ITAsset.hostname == hostname).first()
            
        diffs = []
        fields_to_compare = {
            "hostname": "Hostname",
            "processor": "Processador",
            "ram_total": "Memória RAM",
            "motherboard": "Placa-Mãe",
            "gpu": "Placa de Vídeo",
            "storage": "Armazenamento (SSD/HD)",
            "ip_address": "Endereço IP",
            "manufacturer": "Fabricante",
            "model": "Modelo"
        }
        
        for key, label in fields_to_compare.items():
            db_key = "ram" if key == "ram_total" else key
            current_val = getattr(asset, db_key) if asset else None
            incoming_val = data.get(key)
            if incoming_val and current_val != incoming_val:
                diffs.append({
                    "field": db_key,
                    "label": label,
                    "current": current_val,
                    "collected": incoming_val
                })
                
        return {
            "asset_found": asset is not None,
            "asset": {
                "id": asset.id,
                "name": asset.name,
                "asset_tag": asset.asset_tag,
                "serial_number": asset.serial_number
            } if asset else None,
            "diffs": diffs,
            "collected_data": data
        }

    @staticmethod
    def confirm_specs(db: Session, payload: PcSpecsConfirmPayload, current_user: User, origin: str = "TAURI_DESKTOP") -> ITAsset:
        require_it_staff(db, current_user)
        asset = None
        if payload.asset_id:
            asset = db.query(ITAsset).filter(ITAsset.id == payload.asset_id).first()
            
        if not asset:
            # Cria um ativo novo
            asset = ITAsset(
                name=f"Computador {payload.hostname}",
                asset_type="PC",
                status="DISPONIVEL",
                serial_number=payload.serial_number,
                hostname=payload.hostname
            )
            db.add(asset)
            db.flush()
            ITService.log_change(db, current_user.id, "ITAsset", asset.id, "CREATE", new_data=asset.__dict__, origin=origin)
            
        old_data = asset.__dict__.copy()
        
        # Aplica apenas os campos autorizados pelo técnico
        for field in payload.apply_fields:
            val = getattr(payload, field, None)
            if val is not None:
                setattr(asset, field, val)
                
        asset.last_collection_source = origin
        asset.last_collection_at = naive_now()
        db.flush()
        
        ITService.log_change(db, current_user.id, "ITAsset", asset.id, "UPDATE", old_data=old_data, new_data=asset.__dict__, origin=origin)
        db.commit()
        db.refresh(asset)
        return asset

    @staticmethod
    def import_csv_confirm(db: Session, payload: ImportCSVConfirmPayload, current_user: User) -> Dict[str, Any]:
        require_it_staff(db, current_user)
        created = 0
        updated = 0
        for item in payload.assets:
            # Procura por patrimônio ou serial
            asset = None
            if item.asset_tag:
                asset = db.query(ITAsset).filter(ITAsset.asset_tag == item.asset_tag).first()
            if not asset and item.serial_number:
                asset = db.query(ITAsset).filter(ITAsset.serial_number == item.serial_number).first()
                
            if asset:
                if payload.update_existing:
                    old_data = asset.__dict__.copy()
                    for key, val in item.model_dump(exclude_unset=True).items():
                        if val is not None:
                            setattr(asset, key, val)
                    db.flush()
                    ITService.log_change(db, current_user.id, "ITAsset", asset.id, "UPDATE", old_data=old_data, new_data=asset.__dict__, origin="CSV_XLSX")
                    updated += 1
            else:
                asset = ITAsset(**item.model_dump(exclude_unset=True))
                db.add(asset)
                db.flush()
                ITService.log_change(db, current_user.id, "ITAsset", asset.id, "CREATE", new_data=asset.__dict__, origin="CSV_XLSX")
                created += 1
                
        db.commit()
        return {"created": created, "updated": updated}

    @staticmethod
    def delete_corporate_email(db: Session, email_id: int, current_user: User) -> Dict[str, str]:
        from app.modules.it.permissions import require_it_staff
        from app.models.it import ITCorporateEmail
        require_it_staff(db, current_user)
        row = db.query(ITCorporateEmail).filter(ITCorporateEmail.id == email_id).first()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="E-mail corporativo não encontrado.")
        db.delete(row)
        record_it_activity(db, current_user, "corporate_email.deleted", metadata={"email_id": email_id, "email_address": row.email_address})
        db.commit()
        return {"status": "success"}

    @staticmethod
    def delete_nas_folder(db: Session, folder_id: int, current_user: User) -> Dict[str, str]:
        from app.modules.it.permissions import require_it_staff
        from app.models.it import ITNASFolder
        require_it_staff(db, current_user)
        row = db.query(ITNASFolder).filter(ITNASFolder.id == folder_id).first()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pasta NAS não encontrada.")
        db.delete(row)
        record_it_activity(db, current_user, "nas_folder.deleted", metadata={"folder_id": folder_id, "name": row.name})
        db.commit()
        return {"status": "success"}

    @staticmethod
    def delete_certificate(db: Session, certificate_id: int, current_user: User) -> Dict[str, str]:
        from app.modules.it.permissions import require_it_staff
        from app.models.it import ITCertificate
        require_it_staff(db, current_user)
        row = db.query(ITCertificate).filter(ITCertificate.id == certificate_id).first()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificado não encontrado.")
        db.delete(row)
        record_it_activity(db, current_user, "certificate.deleted", metadata={"certificate_id": certificate_id, "name": row.name})
        db.commit()
        return {"status": "success"}

    @staticmethod
    def delete_network_item(db: Session, item_id: int, current_user: User) -> Dict[str, str]:
        from app.modules.it.permissions import require_it_staff
        from app.models.it import ITNetworkItem
        require_it_staff(db, current_user)
        row = db.query(ITNetworkItem).filter(ITNetworkItem.id == item_id).first()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipamento de rede não encontrado.")
        db.delete(row)
        record_it_activity(db, current_user, "network_item.deleted", metadata={"item_id": item_id, "name": row.name})
        db.commit()
        return {"status": "success"}

    @staticmethod
    def delete_maintenance_record(db: Session, record_id: int, current_user: User) -> Dict[str, str]:
        from app.modules.it.permissions import require_it_staff
        from app.models.it import ITMaintenanceRecord
        require_it_staff(db, current_user)
        row = db.query(ITMaintenanceRecord).filter(ITMaintenanceRecord.id == record_id).first()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registro de manutenção não encontrado.")
        db.delete(row)
        record_it_activity(db, current_user, "maintenance.deleted", metadata={"record_id": record_id, "title": row.title})
        db.commit()
        return {"status": "success"}

    @staticmethod
    def delete_note(db: Session, note_id: int, current_user: User) -> Dict[str, str]:
        from app.models.it import ITNote
        row = db.query(ITNote).filter(ITNote.id == note_id).first()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nota não encontrada.")
        from app.modules.it.permissions import is_it_staff
        # Só o criador ou equipe de TI pode deletar
        if row.created_by_user_id != current_user.id and not is_it_staff(db, current_user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para remover esta nota.")
        db.delete(row)
        db.commit()
        return {"status": "success"}
