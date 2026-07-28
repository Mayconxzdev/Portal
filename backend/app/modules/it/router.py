from typing import List, Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import get_current_user
from app.models.user import User
from app.modules.it.schemas import (
    AccessCatalogPayload,
    AccessRequestPayload,
    AssetPayload,
    AssignPayload,
    AttachmentResponse,
    CertificatePayload,
    ChecklistCreate,
    ChecklistItemCreate,
    ChecklistItemResponse,
    ChecklistItemUpdate,
    ChecklistResponse,
    ChecklistTemplateCreate,
    CommentCreate,
    CommentResponse,
    CommentUpdate,
    CreateKanbanCardPayload,
    CredentialCreate,
    CredentialResponse,
    CredentialSecretResponse,
    CredentialUpdate,
    GenericStatusPayload,
    MaintenancePayload,
    NetworkItemPayload,
    SlaPolicyCreate,
    SlaPolicyUpdate,
    StopTimePayload,
    SummaryResponse,
    TicketCreate,
    TicketPriorityPayload,
    TicketResponse,
    TicketStatusPayload,
    TicketUpdate,
    TimeLogResponse,
    ITPeoplePayload,
    AssetCustomFieldPayload,
    CorporateEmailPayload,
    NASFolderPayload,
    ITNotePayload,
    PcSpecsImportPayload,
    PcSpecsConfirmPayload,
    ImportCSVConfirmPayload,
)
from app.modules.it.service import ITService


router = APIRouter()


@router.get("/tickets", response_model=List[TicketResponse])
def list_tickets(
    mine: bool = Query(False),
    status_filter: Optional[str] = Query(None, alias="status"),
    q: Optional[str] = None,
    ticket_number: Optional[str] = None,
    requester_user_id: Optional[int] = None,
    assigned_to_user_id: Optional[int] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    sla_state: Optional[str] = None,
    unassigned: bool = False,
    assigned_to_me: bool = False,
    created_today: bool = False,
    recently_updated: bool = False,
    has_attachments: Optional[bool] = None,
    has_kanban_card: Optional[bool] = None,
    missing_kanban_card: Optional[bool] = None,
    sort_by: str = "recentes",
    sort_dir: str = "desc",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ITService.list_tickets(
        db,
        current_user,
        mine=mine,
        status_filter=status_filter,
        q=q,
        ticket_number=ticket_number,
        requester_user_id=requester_user_id,
        assigned_to_user_id=assigned_to_user_id,
        category=category,
        priority=priority,
        sla_state_filter=sla_state,
        unassigned=unassigned,
        assigned_to_me=assigned_to_me,
        created_today=created_today,
        recently_updated=recently_updated,
        has_attachments=has_attachments,
        has_kanban_card=has_kanban_card,
        missing_kanban_card=missing_kanban_card,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


@router.post("/tickets", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
def create_ticket(payload: TicketCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.create_ticket(db, payload, current_user)


@router.get("/tickets/{ticket_id}", response_model=TicketResponse)
def get_ticket(ticket_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.get_ticket(db, ticket_id, current_user)


@router.patch("/tickets/{ticket_id}", response_model=TicketResponse)
def update_ticket(ticket_id: int, payload: TicketUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.update_ticket(db, ticket_id, payload, current_user)


@router.post("/tickets/{ticket_id}/assign", response_model=TicketResponse)
def assign_ticket(ticket_id: int, payload: AssignPayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.assign_ticket(db, ticket_id, payload, current_user)


@router.post("/tickets/{ticket_id}/status", response_model=TicketResponse)
def set_status(ticket_id: int, payload: TicketStatusPayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.set_status(db, ticket_id, payload, current_user)


@router.post("/tickets/{ticket_id}/priority", response_model=TicketResponse)
def set_priority(ticket_id: int, payload: TicketPriorityPayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.set_priority(db, ticket_id, payload, current_user)


@router.post("/tickets/{ticket_id}/close", response_model=TicketResponse)
def close_ticket(ticket_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.set_status(db, ticket_id, TicketStatusPayload(status="FECHADO"), current_user)


@router.post("/tickets/{ticket_id}/suspend", response_model=TicketResponse)
def suspend_ticket(ticket_id: int, payload: TicketStatusPayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    payload.status = "SUSPENSO"
    return ITService.set_status(db, ticket_id, payload, current_user)


@router.post("/tickets/{ticket_id}/resume", response_model=TicketResponse)
def resume_ticket(ticket_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.set_status(db, ticket_id, TicketStatusPayload(status="EM_ATENDIMENTO"), current_user)


@router.get("/tickets/{ticket_id}/comments", response_model=List[CommentResponse])
def list_comments(ticket_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.list_comments(db, ticket_id, current_user)


@router.post("/tickets/{ticket_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
def add_comment(ticket_id: int, payload: CommentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.add_comment(db, ticket_id, payload, current_user)


@router.patch("/ticket-comments/{comment_id}", response_model=CommentResponse)
def update_comment(comment_id: int, payload: CommentUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.update_comment(db, comment_id, payload, current_user)


@router.delete("/ticket-comments/{comment_id}")
def delete_comment(comment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.delete_comment(db, comment_id, current_user)


@router.get("/tickets/{ticket_id}/checklists", response_model=List[ChecklistResponse])
def list_checklists(ticket_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.list_checklists(db, ticket_id, current_user)


@router.post("/tickets/{ticket_id}/checklists", response_model=ChecklistResponse, status_code=status.HTTP_201_CREATED)
def create_checklist(ticket_id: int, payload: ChecklistCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.create_checklist(db, ticket_id, payload, current_user)


@router.post("/checklists/{checklist_id}/items", response_model=ChecklistItemResponse, status_code=status.HTTP_201_CREATED)
def add_checklist_item(checklist_id: int, payload: ChecklistItemCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.add_checklist_item(db, checklist_id, payload, current_user)


@router.patch("/checklist-items/{item_id}", response_model=ChecklistItemResponse)
def update_checklist_item(item_id: int, payload: ChecklistItemUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.update_checklist_item(db, item_id, payload, current_user)


@router.delete("/checklist-items/{item_id}")
def delete_checklist_item(item_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.delete_checklist_item(db, item_id, current_user)


@router.get("/checklist-templates")
def list_templates(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.modules.it.permissions import require_it_staff
    from app.models.it import ITChecklistTemplate
    require_it_staff(db, current_user)
    return db.query(ITChecklistTemplate).filter(ITChecklistTemplate.is_active == True).all()


@router.post("/checklist-templates", status_code=status.HTTP_201_CREATED)
def create_template(payload: ChecklistTemplateCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.modules.it.permissions import require_it_staff
    from app.models.it import ITChecklistTemplate
    require_it_staff(db, current_user)
    template = ITChecklistTemplate(**payload.model_dump())
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.patch("/checklist-templates/{template_id}")
def update_template(template_id: int, payload: ChecklistTemplateCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.modules.it.permissions import require_it_staff
    from app.models.it import ITChecklistTemplate
    require_it_staff(db, current_user)
    template = db.query(ITChecklistTemplate).filter(ITChecklistTemplate.id == template_id).first()
    if not template:
        return {"status": "not_found"}
    template.category = payload.category
    template.title = payload.title
    template.items = payload.items
    db.commit()
    return template


@router.post("/tickets/{ticket_id}/time/start", response_model=TimeLogResponse)
def start_time(ticket_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.start_time(db, ticket_id, current_user)


@router.post("/tickets/{ticket_id}/time/stop", response_model=TimeLogResponse)
def stop_time(ticket_id: int, payload: StopTimePayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.stop_time(db, ticket_id, payload, current_user)


@router.get("/tickets/{ticket_id}/time-logs", response_model=List[TimeLogResponse])
def list_time_logs(ticket_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.list_time_logs(db, ticket_id, current_user)


@router.get("/tickets/{ticket_id}/attachments", response_model=List[AttachmentResponse])
def list_attachments(ticket_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.list_attachments(db, ticket_id, current_user)


@router.post("/tickets/{ticket_id}/attachments", response_model=AttachmentResponse, status_code=status.HTTP_201_CREATED)
def upload_attachment(ticket_id: int, upload: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.upload_attachment(db, ticket_id, upload, current_user)


@router.post("/tickets/{ticket_id}/attachments/paste", response_model=AttachmentResponse, status_code=status.HTTP_201_CREATED)
def upload_paste_attachment(ticket_id: int, upload: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.upload_attachment(db, ticket_id, upload, current_user)


@router.get("/ticket-attachments/{attachment_id}/download")
def download_attachment(attachment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.download_attachment(db, attachment_id, current_user)


@router.delete("/ticket-attachments/{attachment_id}")
def delete_attachment(attachment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.delete_attachment(db, attachment_id, current_user)


@router.get("/sla-policies")
def list_sla_policies(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.list_sla_policies(db, current_user)


@router.post("/sla-policies", status_code=status.HTTP_201_CREATED)
def create_sla_policy(payload: SlaPolicyCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.create_sla_policy(db, payload, current_user)


@router.patch("/sla-policies/{sla_id}")
def update_sla_policy(sla_id: int, payload: SlaPolicyUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.update_sla_policy(db, sla_id, payload, current_user)


@router.get("/sla-summary")
def sla_summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.summary(db, current_user)


@router.get("/assets")
def list_assets(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.list_assets(db, current_user)


@router.post("/assets", status_code=status.HTTP_201_CREATED)
def create_asset(payload: AssetPayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.create_asset(db, payload, current_user)


@router.get("/assets/{asset_id}")
def get_asset(asset_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return next((asset for asset in ITService.list_assets(db, current_user) if asset.id == asset_id), None)


@router.patch("/assets/{asset_id}")
def update_asset(asset_id: int, payload: AssetPayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.update_asset(db, asset_id, payload, current_user)


@router.post("/assets/{asset_id}/retire")
def retire_asset(asset_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.retire_asset(db, asset_id, current_user)


@router.get("/assets/{asset_id}/history")
def asset_history(asset_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.modules.it.permissions import require_it_staff
    from app.models.it import ITActivity
    require_it_staff(db, current_user)
    return db.query(ITActivity).filter(ITActivity.asset_id == asset_id).order_by(ITActivity.created_at.desc()).all()


@router.get("/access-catalog")
def list_access_catalog(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.list_catalog(db, current_user)


@router.post("/access-catalog", status_code=status.HTTP_201_CREATED)
def create_access_catalog(payload: AccessCatalogPayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.create_catalog(db, payload, current_user)


@router.patch("/access-catalog/{catalog_id}")
def update_access_catalog(catalog_id: int, payload: AccessCatalogPayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.modules.it.permissions import require_it_staff
    from app.models.it import ITAccessCatalog
    require_it_staff(db, current_user)
    row = db.query(ITAccessCatalog).filter(ITAccessCatalog.id == catalog_id).first()
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    return row


@router.get("/access-requests")
def list_access_requests(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.list_access_requests(db, current_user)


@router.post("/access-requests", status_code=status.HTTP_201_CREATED)
def create_access_request(payload: AccessRequestPayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.create_access_request(db, payload, current_user)


@router.get("/access-requests/{request_id}")
def get_access_request(request_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return next((row for row in ITService.list_access_requests(db, current_user) if row.id == request_id), None)


@router.patch("/access-requests/{request_id}")
def update_access_request(request_id: int, payload: GenericStatusPayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.modules.it.permissions import require_it_staff
    from app.models.it import ITAccessRequest
    require_it_staff(db, current_user)
    row = db.query(ITAccessRequest).filter(ITAccessRequest.id == request_id).first()
    row.status = payload.status
    db.commit()
    return row


@router.post("/access-requests/{request_id}/complete")
def complete_access_request(request_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return update_access_request(request_id, GenericStatusPayload(status="CONCLUIDA"), db, current_user)


@router.post("/access-requests/{request_id}/cancel")
def cancel_access_request(request_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return update_access_request(request_id, GenericStatusPayload(status="CANCELADA"), db, current_user)


@router.get("/credentials", response_model=List[CredentialResponse])
def list_credentials(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.list_credentials(db, current_user)


@router.post("/credentials", response_model=CredentialResponse, status_code=status.HTTP_201_CREATED)
def create_credential(payload: CredentialCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.create_credential(db, payload, current_user)


@router.get("/credentials/{credential_id}", response_model=CredentialResponse)
def get_credential(credential_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return next((row for row in ITService.list_credentials(db, current_user) if row.id == credential_id), None)


@router.patch("/credentials/{credential_id}", response_model=CredentialResponse)
def update_credential(credential_id: int, payload: CredentialUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.update_credential(db, credential_id, payload, current_user)


@router.post("/credentials/{credential_id}/reveal", response_model=CredentialSecretResponse)
def reveal_credential(credential_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.reveal_credential(db, credential_id, current_user, copied=False)


@router.post("/credentials/{credential_id}/copy", response_model=CredentialSecretResponse)
def copy_credential(credential_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.reveal_credential(db, credential_id, current_user, copied=True)


@router.post("/credentials/{credential_id}/disable")
def disable_credential(credential_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.disable_credential(db, credential_id, current_user)


@router.delete("/credentials/{credential_id}")
def delete_credential(credential_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.delete_credential(db, credential_id, current_user)


@router.get("/certificates")
def list_certificates(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.list_certificates(db, current_user)


@router.post("/certificates", status_code=status.HTTP_201_CREATED)
def create_certificate(payload: CertificatePayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.create_certificate(db, payload, current_user)


@router.get("/certificates/expiring")
def expiring_certificates(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return [cert for cert in ITService.list_certificates(db, current_user) if cert.status in {"VENCENDO", "VENCIDO"}]


@router.get("/certificates/{certificate_id}")
def get_certificate(certificate_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return next((row for row in ITService.list_certificates(db, current_user) if row.id == certificate_id), None)


@router.patch("/certificates/{certificate_id}")
def update_certificate(certificate_id: int, payload: CertificatePayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.modules.it.permissions import require_it_staff
    from app.models.it import ITCertificate
    require_it_staff(db, current_user)
    row = db.query(ITCertificate).filter(ITCertificate.id == certificate_id).first()
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    return row


@router.post("/certificates/{certificate_id}/create-ticket", response_model=TicketResponse)
def certificate_ticket(certificate_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    cert = get_certificate(certificate_id, db, current_user)
    return ITService.create_ticket(db, TicketCreate(title=f"Renovar certificado {cert.name}", description=f"Certificado de {cert.domain_or_system} vence em {cert.expires_at}.", category="CERTIFICADO"), current_user)


@router.get("/network-items")
def list_network_items(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.list_network_items(db, current_user)


@router.post("/network-items", status_code=status.HTTP_201_CREATED)
def create_network_item(payload: NetworkItemPayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.create_network_item(db, payload, current_user)


@router.get("/network-items/{item_id}")
def get_network_item(item_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return next((row for row in ITService.list_network_items(db, current_user) if row.id == item_id), None)


@router.patch("/network-items/{item_id}")
def update_network_item(item_id: int, payload: NetworkItemPayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.modules.it.permissions import require_it_staff
    from app.models.it import ITNetworkItem
    require_it_staff(db, current_user)
    row = db.query(ITNetworkItem).filter(ITNetworkItem.id == item_id).first()
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    return row


@router.get("/maintenance-records")
def list_maintenance(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.list_maintenance(db, current_user)


@router.post("/maintenance-records", status_code=status.HTTP_201_CREATED)
def create_maintenance(payload: MaintenancePayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.create_maintenance(db, payload, current_user)


@router.patch("/maintenance-records/{record_id}")
def update_maintenance(record_id: int, payload: MaintenancePayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.modules.it.permissions import require_it_staff
    from app.models.it import ITMaintenanceRecord
    require_it_staff(db, current_user)
    row = db.query(ITMaintenanceRecord).filter(ITMaintenanceRecord.id == record_id).first()
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    return row


@router.post("/tickets/{ticket_id}/create-kanban-card")
def create_kanban_card(ticket_id: int, payload: CreateKanbanCardPayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.create_kanban_card(db, ticket_id, payload, current_user)


@router.get("/tickets/{ticket_id}/kanban-link")
def get_kanban_link(ticket_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.get_kanban_link(db, ticket_id, current_user)


@router.get("/summary", response_model=SummaryResponse)
def summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.summary(db, current_user)


@router.get("/activity")
def activity(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.activity(db, current_user)


@router.get("/reports/summary")
def report_summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.report_summary(db, current_user)


@router.get("/reports/tickets-by-category")
def report_tickets_by_category(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.report_tickets_by_category(db, current_user)


@router.get("/reports/tickets-by-status")
def report_tickets_by_status(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.report_tickets_by_status(db, current_user)


@router.get("/reports/sla")
def report_sla(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.report_sla(db, current_user)


@router.get("/reports/technician-time")
def report_technician_time(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.report_technician_time(db, current_user)


@router.get("/reports/assets")
def report_assets(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.report_assets(db, current_user)


@router.get("/reports/certificates")
def report_certificates(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.report_certificates(db, current_user)


# === ENDPOINTS FASE 5.2 ===

@router.get("/overview")
def get_overview(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {
        "summary": ITService.summary(db, current_user),
        "recent_activity": ITService.activity(db, current_user)[:10]
    }


# --- PESSOAS E ESTAÇÕES ---
@router.get("/people")
def list_people(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.list_people(db, current_user)


@router.post("/people", status_code=status.HTTP_201_CREATED)
def create_person(payload: ITPeoplePayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.create_person(db, payload, current_user)


@router.patch("/people/{person_id}")
def update_person(person_id: int, payload: ITPeoplePayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.update_person(db, person_id, payload, current_user)


@router.post("/people/{person_id}/archive")
def archive_person(person_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.archive_person(db, person_id, current_user)


# --- CAMPOS PERSONALIZADOS ---
@router.get("/asset-fields")
def list_custom_fields(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.list_custom_fields(db, current_user)


@router.post("/asset-fields", status_code=status.HTTP_201_CREATED)
def create_custom_field(payload: AssetCustomFieldPayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.create_custom_field(db, payload, current_user)


@router.patch("/asset-fields/{field_id}")
def update_custom_field(field_id: int, payload: AssetCustomFieldPayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.update_custom_field(db, field_id, payload, current_user)


@router.post("/asset-fields/{field_id}/disable")
def disable_custom_field(field_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.disable_custom_field(db, field_id, current_user)


# --- E-MAILS CORPORATIVOS ---
@router.get("/corporate-emails")
def list_corporate_emails(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.list_corporate_emails(db, current_user)


@router.post("/corporate-emails", status_code=status.HTTP_201_CREATED)
def create_corporate_email(payload: CorporateEmailPayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.create_corporate_email(db, payload, current_user)


@router.patch("/corporate-emails/{email_id}")
def update_corporate_email(email_id: int, payload: CorporateEmailPayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.update_corporate_email(db, email_id, payload, current_user)


# --- NAS / QNAP ---
@router.get("/nas")
def list_nas_folders(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.list_nas_folders(db, current_user)


@router.post("/nas", status_code=status.HTTP_201_CREATED)
def create_nas_folder(payload: NASFolderPayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.create_nas_folder(db, payload, current_user)


@router.patch("/nas/{folder_id}")
def update_nas_folder(folder_id: int, payload: NASFolderPayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.update_nas_folder(db, folder_id, payload, current_user)


# --- NOTAS (STICKY NOTES) ---
@router.get("/notes")
def list_notes(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.list_notes(db, current_user)


@router.post("/notes", status_code=status.HTTP_201_CREATED)
def create_note(payload: ITNotePayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.create_note(db, payload, current_user)


@router.patch("/notes/{note_id}")
def update_note(note_id: int, payload: ITNotePayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.update_note(db, note_id, payload, current_user)


@router.post("/notes/{note_id}/archive")
def archive_note(note_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    note_payload = ITNotePayload(content="", is_archived=True)
    return ITService.update_note(db, note_id, note_payload, current_user)


# --- AUDITORIA E CHANGE LOG ---
@router.get("/change-log")
def get_change_log(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.get_change_logs(db, current_user)


# --- PREVIEW E CONFIRMAÇÃO DE SPECS ---
@router.post("/assets/specs/preview")
def preview_specs(payload: PcSpecsImportPayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.preview_specs(db, payload.model_dump(), current_user)


@router.post("/assets/specs/confirm")
def confirm_specs(payload: PcSpecsConfirmPayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.confirm_specs(db, payload, current_user)


@router.post("/assets/import/preview")
def import_csv_preview(payload: List[AssetPayload], db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Retorna uma simulação simples de preview comparando os itens enviados
    from app.modules.it.permissions import require_it_staff
    require_it_staff(db, current_user)
    return {"assets": payload, "total": len(payload)}


@router.post("/assets/import/confirm")
def import_csv_confirm(payload: ImportCSVConfirmPayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.import_csv_confirm(db, payload, current_user)


# --- EXPORTAÇÃO CSV DE RELATÓRIOS ---
@router.get("/reports/export-csv")
def export_csv_report(entity: str = Query("assets"), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.modules.it.permissions import require_it_staff
    from fastapi.responses import StreamingResponse
    import csv
    from io import StringIO
    
    require_it_staff(db, current_user)
    output = StringIO()
    writer = csv.writer(output)
    
    if entity == "assets":
        assets = ITService.list_assets(db, current_user)
        writer.writerow(["ID", "Patrimonio", "Nome", "Tipo", "Status", "Hostname", "Serial Number", "IP Address", "Setor"])
        for a in assets:
            writer.writerow([a.id, a.asset_tag, a.name, a.asset_type, a.status, a.hostname, a.serial_number, a.ip_address, a.sector])
            
    elif entity == "tickets":
        # Retorna todos os chamados
        from app.models.it import ITTicket
        tickets = db.query(ITTicket).all()
        writer.writerow(["ID", "Numero", "Titulo", "Status", "Prioridade", "Categoria", "Data Criacao"])
        for t in tickets:
            writer.writerow([t.id, t.ticket_number, t.title, t.status, t.priority, t.category, t.created_at])
            
    elif entity == "certificates":
        certs = ITService.list_certificates(db, current_user)
        writer.writerow(["ID", "Nome", "Dominio/Sistema", "Emissor", "Vencimento", "Status"])
        for c in certs:
            writer.writerow([c.id, c.name, c.domain_or_system, c.issuer, c.expires_at, c.status])
            
    else:
        writer.writerow(["Erro", "Entidade desconhecida para exportacao."])
        
    output.seek(0)
    filename = f"report-{entity}.csv"
    return StreamingResponse(
        output, 
        media_type="text/csv", 
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/")
def it_root(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {"status": "success", "module": "it", "summary": ITService.summary(db, current_user)}


@router.delete("/corporate-emails/{email_id}")
def delete_corporate_email(email_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.delete_corporate_email(db, email_id, current_user)


@router.delete("/nas/{folder_id}")
def delete_nas_folder(folder_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.delete_nas_folder(db, folder_id, current_user)


@router.delete("/certificates/{certificate_id}")
def delete_certificate(certificate_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.delete_certificate(db, certificate_id, current_user)


@router.delete("/network-items/{item_id}")
def delete_network_item(item_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.delete_network_item(db, item_id, current_user)


@router.delete("/maintenance-records/{record_id}")
def delete_maintenance_record(record_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.delete_maintenance_record(db, record_id, current_user)


@router.delete("/notes/{note_id}")
def delete_note(note_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.delete_note(db, note_id, current_user)

