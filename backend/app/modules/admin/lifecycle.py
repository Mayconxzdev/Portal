from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.admin_lifecycle import (
    UserOffboardingCase,
    UserOffboardingTask,
    UserSession,
    UserTemporaryAccess,
    UserTemporarySubstitution,
)
from app.models.approval import Approval
from app.models.it import (
    ITAccessRecord,
    ITAsset,
    ITCertificate,
    ITCorporateEmail,
    ITCredential,
    ITNASFolder,
    ITNote,
    ITTicket,
)
from app.models.kanban import KanbanCard, KanbanCardAssignee
from app.models.role import Role
from app.models.user import User
from app.models.user_module_access import UserModuleAccess


OPEN_IT_TICKET_STATUSES = {"ABERTO", "EM_ANDAMENTO", "PENDENTE", "SUSPENSO"}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def active_session_filter(query):
    return query.filter(UserSession.revoked_at.is_(None), UserSession.expires_at > utcnow())


def ensure_not_last_active_admin(db: Session, target: User) -> None:
    if not target.role or target.role.name != "ADMIN" or not target.is_active:
        return

    active_admins = db.query(User).join(Role).filter(
        Role.name == "ADMIN",
        User.is_active.is_(True),
    ).count()
    if active_admins <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Operacao negada. Nao e permitido desligar o unico administrador ativo do sistema.",
        )


def build_offboarding_impact(db: Session, target_user_id: int) -> Dict[str, Any]:
    target = db.query(User).filter(User.id == target_user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")

    active_sessions = active_session_filter(
        db.query(UserSession).filter(UserSession.user_id == target_user_id)
    ).count()
    active_temp_access = db.query(UserTemporaryAccess).filter(
        UserTemporaryAccess.target_user_id == target_user_id,
        UserTemporaryAccess.status == "ACTIVE",
        UserTemporaryAccess.revoked_at.is_(None),
        UserTemporaryAccess.expires_at > utcnow(),
    ).count()
    active_substitutions = db.query(UserTemporarySubstitution).filter(
        UserTemporarySubstitution.status == "ACTIVE",
        UserTemporarySubstitution.expires_at > utcnow(),
        (
            (UserTemporarySubstitution.replaced_user_id == target_user_id)
            | (UserTemporarySubstitution.substitute_user_id == target_user_id)
        ),
    ).count()
    module_accesses = db.query(UserModuleAccess).filter(
        UserModuleAccess.user_id == target_user_id,
        UserModuleAccess.permission_level != "NO_ACCESS",
    ).count()
    kanban_direct_cards = db.query(KanbanCard).filter(
        KanbanCard.assigned_to_user_id == target_user_id,
        KanbanCard.is_archived.is_(False),
    ).count()
    kanban_assignee_links = db.query(KanbanCardAssignee).filter(
        KanbanCardAssignee.user_id == target_user_id,
    ).count()
    pending_approvals = db.query(Approval).filter(
        Approval.status == "PENDING",
        (
            (Approval.requester_user_id == target_user_id)
            | (Approval.approver_user_id == target_user_id)
        ),
    ).count()
    it_tickets = db.query(ITTicket).filter(
        ITTicket.status.in_(OPEN_IT_TICKET_STATUSES),
        (
            (ITTicket.requester_user_id == target_user_id)
            | (ITTicket.assigned_to_user_id == target_user_id)
        ),
    ).count()
    assets = db.query(ITAsset).filter(ITAsset.assigned_to_user_id == target_user_id).count()
    corporate_emails = db.query(ITCorporateEmail).filter(
        ITCorporateEmail.user_id == target_user_id,
        ITCorporateEmail.status != "INATIVO",
    ).count()
    nas_folders = db.query(ITNASFolder).filter(ITNASFolder.user_id == target_user_id).count()
    access_records = db.query(ITAccessRecord).filter(
        ITAccessRecord.user_id == target_user_id,
        ITAccessRecord.status == "ACTIVE",
    ).count()
    credentials = db.query(ITCredential).filter(
        ITCredential.owner_user_id == target_user_id,
        ITCredential.is_active.is_(True),
    ).count()
    certificates = db.query(ITCertificate).filter(
        ITCertificate.responsible_user_id == target_user_id,
        ITCertificate.status != "EXPIRADO",
    ).count()
    notes = db.query(ITNote).filter(
        ITNote.responsible_user_id == target_user_id,
        ITNote.is_archived.is_(False),
    ).count()

    items = [
        {
            "key": "sessions",
            "label": "Sessoes ativas",
            "count": active_sessions,
            "action": "Revogar sessoes ativas na confirmacao",
            "can_auto_apply": True,
        },
        {
            "key": "temporary_access",
            "label": "Acessos temporarios ativos",
            "count": active_temp_access,
            "action": "Revogar acessos temporarios na confirmacao",
            "can_auto_apply": True,
        },
        {
            "key": "substitutions",
            "label": "Substituicoes temporarias",
            "count": active_substitutions,
            "action": "Encerrar substituicoes ativas envolvendo o usuario",
            "can_auto_apply": True,
        },
        {
            "key": "module_accesses",
            "label": "Permissoes de modulo",
            "count": module_accesses,
            "action": "Preservar historico e bloquear login ao inativar usuario",
            "can_auto_apply": True,
        },
        {
            "key": "kanban",
            "label": "Cartoes Kanban vinculados",
            "count": kanban_direct_cards + kanban_assignee_links,
            "action": "Transferir responsavel direto quando houver substituto; revisar demais vinculos",
            "can_auto_apply": True,
        },
        {
            "key": "approvals",
            "label": "Aprovacoes pendentes",
            "count": pending_approvals,
            "action": "Criar tarefa de revisao humana; aprovacao nao e transferida automaticamente",
            "can_auto_apply": False,
        },
        {
            "key": "it_tickets",
            "label": "Chamados de TI abertos",
            "count": it_tickets,
            "action": "Transferir responsavel quando houver substituto; revisar solicitacoes abertas",
            "can_auto_apply": True,
        },
        {
            "key": "it_assets",
            "label": "Ativos de TI",
            "count": assets,
            "action": "Transferir custodia quando houver substituto; revisar devolucao fisica",
            "can_auto_apply": True,
        },
        {
            "key": "corporate_emails",
            "label": "E-mails corporativos",
            "count": corporate_emails,
            "action": "Criar tarefa de TI para bloqueio, alias ou redirecionamento",
            "can_auto_apply": False,
        },
        {
            "key": "nas",
            "label": "Pastas NAS",
            "count": nas_folders,
            "action": "Criar tarefa de revisao de permissao NAS",
            "can_auto_apply": False,
        },
        {
            "key": "access_records",
            "label": "Registros de acesso externos",
            "count": access_records,
            "action": "Criar tarefa para revogacao em sistemas externos",
            "can_auto_apply": False,
        },
        {
            "key": "credentials",
            "label": "Credenciais sob responsabilidade",
            "count": credentials,
            "action": "Criar tarefa de revisao do cofre sem expor segredo",
            "can_auto_apply": False,
        },
        {
            "key": "certificates",
            "label": "Certificados sob responsabilidade",
            "count": certificates,
            "action": "Criar tarefa para redistribuir responsabilidade",
            "can_auto_apply": False,
        },
        {
            "key": "notes",
            "label": "Notas de TI responsaveis",
            "count": notes,
            "action": "Transferir responsavel quando houver substituto",
            "can_auto_apply": True,
        },
    ]

    return {
        "target_user": {
            "id": target.id,
            "username": target.username,
            "full_name": target.full_name,
            "email": target.email,
            "is_active": target.is_active,
        },
        "items": items,
        "requires_human_review": any(item["count"] > 0 and not item["can_auto_apply"] for item in items),
        "generated_at": utcnow().isoformat(),
    }


def create_offboarding_tasks(db: Session, case: UserOffboardingCase) -> None:
    for item in case.impact_snapshot.get("items", []):
        if item.get("count", 0) <= 0:
            continue
        task = UserOffboardingTask(
            case_id=case.id,
            module=str(item["key"]),
            title=f"{item['label']} ({item['count']})",
            description=item["action"],
            requires_human_review=not bool(item.get("can_auto_apply")),
            payload=item,
        )
        db.add(task)


def confirm_offboarding_case(db: Session, case: UserOffboardingCase, admin_user: User) -> Dict[str, int]:
    if case.status == "CONFIRMED":
        raise HTTPException(status_code=400, detail="Desligamento ja confirmado")

    target = db.query(User).filter(User.id == case.target_user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")
    ensure_not_last_active_admin(db, target)

    now = utcnow()
    counts = {
        "sessions_revoked": 0,
        "temporary_access_revoked": 0,
        "substitutions_closed": 0,
        "kanban_cards_transferred": 0,
        "it_tickets_transferred": 0,
        "it_assets_transferred": 0,
        "it_notes_transferred": 0,
    }

    for session in active_session_filter(db.query(UserSession).filter(UserSession.user_id == target.id)).all():
        session.revoked_at = now
        session.revoked_by_user_id = admin_user.id
        session.revocation_reason = f"Desligamento administrativo #{case.id}"
        counts["sessions_revoked"] += 1

    for access in db.query(UserTemporaryAccess).filter(
        UserTemporaryAccess.target_user_id == target.id,
        UserTemporaryAccess.status == "ACTIVE",
        UserTemporaryAccess.revoked_at.is_(None),
    ).all():
        access.status = "REVOKED"
        access.revoked_at = now
        access.revoked_by_user_id = admin_user.id
        access.revocation_reason = f"Desligamento administrativo #{case.id}"
        counts["temporary_access_revoked"] += 1

    for substitution in db.query(UserTemporarySubstitution).filter(
        UserTemporarySubstitution.status == "ACTIVE",
        (
            (UserTemporarySubstitution.replaced_user_id == target.id)
            | (UserTemporarySubstitution.substitute_user_id == target.id)
        ),
    ).all():
        substitution.status = "ENDED"
        substitution.ended_at = now
        counts["substitutions_closed"] += 1

    if case.replacement_user_id:
        counts["kanban_cards_transferred"] = db.query(KanbanCard).filter(
            KanbanCard.assigned_to_user_id == target.id,
            KanbanCard.is_archived.is_(False),
        ).update({"assigned_to_user_id": case.replacement_user_id}, synchronize_session=False)
        counts["it_tickets_transferred"] = db.query(ITTicket).filter(
            ITTicket.assigned_to_user_id == target.id,
            ITTicket.status.in_(OPEN_IT_TICKET_STATUSES),
        ).update({"assigned_to_user_id": case.replacement_user_id}, synchronize_session=False)
        counts["it_assets_transferred"] = db.query(ITAsset).filter(
            ITAsset.assigned_to_user_id == target.id,
        ).update({"assigned_to_user_id": case.replacement_user_id}, synchronize_session=False)
        counts["it_notes_transferred"] = db.query(ITNote).filter(
            ITNote.responsible_user_id == target.id,
            ITNote.is_archived.is_(False),
        ).update({"responsible_user_id": case.replacement_user_id}, synchronize_session=False)

    target.is_active = False
    target.updated_at = now
    case.status = "CONFIRMED"
    case.confirmed_by_user_id = admin_user.id
    case.confirmed_at = now
    case.updated_at = now
    return counts


def sweep_expired_temporary_records(db: Session) -> Dict[str, int]:
    now = utcnow()
    counts = {"expired_accesses": 0, "expired_substitutions": 0}
    
    # 1. Temporary access sweep
    expired_accesses = db.query(UserTemporaryAccess).filter(
        UserTemporaryAccess.status == "ACTIVE",
        UserTemporaryAccess.expires_at <= now,
    ).all()
    
    for access in expired_accesses:
        access.status = "EXPIRED"
        access.updated_at = now
        counts["expired_accesses"] += 1
        
        from app.core.audit import log_action
        log_action(
            db=db,
            user_id=None,
            action="admin.temporary_access.expired",
            module="admin",
            details={
                "temporary_access_id": access.id,
                "target_user_id": access.target_user_id,
                "module_code": access.module.code,
                "permission_level": access.permission_level,
                "expires_at": access.expires_at.isoformat()
            },
            commit=False
        )
        
        from app.core.events import emit_event
        emit_event(
            db=db,
            event_type="admin.temporary_access.expired",
            aggregate_type="temporary_access",
            aggregate_id=str(access.id),
            module="admin",
            payload={
                "target_user_id": access.target_user_id,
                "module_code": access.module.code,
                "permission_level": access.permission_level
            },
            actor_user_id=None
        )

    # 2. Temporary substitutions sweep
    expired_substitutions = db.query(UserTemporarySubstitution).filter(
        UserTemporarySubstitution.status == "ACTIVE",
        UserTemporarySubstitution.expires_at <= now,
    ).all()
    
    for substitution in expired_substitutions:
        substitution.status = "EXPIRED"
        substitution.updated_at = now
        counts["expired_substitutions"] += 1
        
        from app.core.audit import log_action
        log_action(
            db=db,
            user_id=None,
            action="admin.temporary_substitution.expired",
            module="admin",
            details={
                "substitution_id": substitution.id,
                "replaced_user_id": substitution.replaced_user_id,
                "substitute_user_id": substitution.substitute_user_id,
                "expires_at": substitution.expires_at.isoformat()
            },
            commit=False
        )
        
        from app.core.events import emit_event
        emit_event(
            db=db,
            event_type="admin.temporary_substitution.expired",
            aggregate_type="temporary_substitution",
            aggregate_id=str(substitution.id),
            module="admin",
            payload={
                "replaced_user_id": substitution.replaced_user_id,
                "substitute_user_id": substitution.substitute_user_id
            },
            actor_user_id=None
        )
        
    if counts["expired_accesses"] > 0 or counts["expired_substitutions"] > 0:
        db.commit()
        
    return counts

