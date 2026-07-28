from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


TICKET_STATUSES = {"ABERTO", "EM_ATENDIMENTO", "SUSPENSO", "FECHADO"}
TICKET_PRIORITIES = {"BAIXA", "MEDIA", "ALTA", "CRITICA"}
TICKET_CATEGORIES = {
    "INTERNET_REDE", "COMPUTADOR", "IMPRESSORA", "EMAIL", "SISTEMA_SOFTWARE",
    "ACESSO", "EQUIPAMENTO", "CERTIFICADO", "OUTRO",
}
SUSPENSION_REASONS = {"AGUARDANDO_USUARIO", "AGUARDANDO_TERCEIRO", "AGUARDANDO_PECA", "AGUARDANDO_COMPRA", "OUTRO"}


class UserLite(BaseModel):
    id: int
    username: str
    email: str

    model_config = {"from_attributes": True}


class TicketCreate(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    description: str = Field(min_length=3, max_length=8000)
    category: str = "OUTRO"
    priority: Optional[str] = None


class TicketUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=180)
    description: Optional[str] = Field(default=None, min_length=3, max_length=8000)
    category: Optional[str] = None
    assigned_to_user_id: Optional[int] = None


class TicketStatusPayload(BaseModel):
    status: str
    suspension_reason: Optional[str] = None


class TicketPriorityPayload(BaseModel):
    priority: str


class AssignPayload(BaseModel):
    assigned_to_user_id: Optional[int] = None


class CommentCreate(BaseModel):
    comment: str = Field(min_length=1, max_length=5000)
    is_internal: bool = False


class CommentUpdate(BaseModel):
    comment: str = Field(min_length=1, max_length=5000)


class CommentResponse(BaseModel):
    id: int
    ticket_id: int
    user_id: int
    author_name: Optional[str] = None
    comment: str
    is_internal: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChecklistCreate(BaseModel):
    title: str = Field(default="Checklist", min_length=1, max_length=120)


class ChecklistItemCreate(BaseModel):
    text: str = Field(min_length=1, max_length=300)


class ChecklistItemUpdate(BaseModel):
    text: Optional[str] = Field(default=None, min_length=1, max_length=300)
    is_done: Optional[bool] = None


class ChecklistItemResponse(BaseModel):
    id: int
    checklist_id: int
    text: str
    is_done: bool
    position: int
    completed_by_user_id: Optional[int] = None
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ChecklistResponse(BaseModel):
    id: int
    ticket_id: int
    title: str
    category: Optional[str] = None
    position: int
    items: List[ChecklistItemResponse] = []

    model_config = {"from_attributes": True}


class ChecklistTemplateCreate(BaseModel):
    category: str
    title: str
    items: List[str]


class TimeLogResponse(BaseModel):
    id: int
    ticket_id: int
    user_id: int
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    note: Optional[str] = None

    model_config = {"from_attributes": True}


class StopTimePayload(BaseModel):
    note: Optional[str] = Field(default=None, max_length=1000)


class AttachmentResponse(BaseModel):
    id: int
    ticket_id: int
    comment_id: Optional[int] = None
    file_id: int
    filename: Optional[str] = None
    content_type: Optional[str] = None
    size_bytes: Optional[int] = None
    uploaded_by_user_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class TicketResponse(BaseModel):
    id: int
    ticket_number: str
    title: str
    description: str
    requester_user_id: int
    requester_name: Optional[str] = None
    assigned_to_user_id: Optional[int] = None
    assignee_name: Optional[str] = None
    status: str
    priority: str
    category: str
    suspension_reason: Optional[str] = None
    due_at: Optional[datetime] = None
    first_response_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    kanban_card_id: Optional[int] = None
    sla: Dict[str, Any] = {}
    total_time_seconds: int = 0
    comments: List[CommentResponse] = []
    checklists: List[ChecklistResponse] = []
    attachments: List[AttachmentResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SlaPolicyCreate(BaseModel):
    name: str
    category: Optional[str] = None
    priority: str = "MEDIA"
    response_minutes: int = 240
    resolution_minutes: int = 1440
    is_active: bool = True


class SlaPolicyUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    response_minutes: Optional[int] = None
    resolution_minutes: Optional[int] = None
    is_active: Optional[bool] = None


class AssetPayload(BaseModel):
    asset_tag: Optional[str] = None
    name: str
    asset_type: str = "OUTRO"
    status: str = "DISPONIVEL"
    assigned_to_user_id: Optional[int] = None
    location: Optional[str] = None
    serial_number: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    purchase_date: Optional[datetime] = None
    warranty_until: Optional[datetime] = None
    notes: Optional[str] = None

    # Campos técnicos avançados
    hostname: Optional[str] = None
    processor: Optional[str] = None
    ram: Optional[str] = None
    motherboard: Optional[str] = None
    gpu: Optional[str] = None
    network_card: Optional[str] = None
    power_supply: Optional[str] = None
    cabinet: Optional[str] = None
    monitor: Optional[str] = None
    mouse: Optional[str] = None
    mouse_pad: Optional[str] = None
    keyboard: Optional[str] = None
    storage: Optional[str] = None
    peripherals: Optional[str] = None
    ip_address: Optional[str] = None
    ramal: Optional[str] = None
    network_point: Optional[str] = None
    sector: Optional[str] = None
    it_responsible: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = None


class AccessCatalogPayload(BaseModel):
    system_name: str
    access_type: Optional[str] = None
    url: Optional[str] = None
    owner_user_id: Optional[int] = None
    responsible_team: Optional[str] = None
    description: Optional[str] = None
    how_to_request: Optional[str] = None
    is_active: bool = True


class AccessRequestPayload(BaseModel):
    target_user_id: Optional[int] = None
    system_name: str
    access_type: str
    reason: str


class GenericStatusPayload(BaseModel):
    status: str


class CredentialCreate(BaseModel):
    title: str
    system_name: str
    username: Optional[str] = None
    secret: str = Field(min_length=1)
    secret_hint: Optional[str] = None
    url: Optional[str] = None
    notes: Optional[str] = None
    owner_user_id: Optional[int] = None
    visibility_level: str = "IT_MANAGER"


class CredentialUpdate(BaseModel):
    title: Optional[str] = None
    system_name: Optional[str] = None
    username: Optional[str] = None
    secret: Optional[str] = None
    secret_hint: Optional[str] = None
    url: Optional[str] = None
    notes: Optional[str] = None
    visibility_level: Optional[str] = None
    is_active: Optional[bool] = None


class CredentialResponse(BaseModel):
    id: int
    title: str
    system_name: str
    username: Optional[str] = None
    secret_hint: Optional[str] = None
    url: Optional[str] = None
    visibility_level: str
    is_active: bool
    last_revealed_at: Optional[datetime] = None
    last_revealed_by_user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CredentialSecretResponse(BaseModel):
    id: int
    secret: str


class CertificatePayload(BaseModel):
    name: str
    domain_or_system: str
    issuer: Optional[str] = None
    provider: Optional[str] = None
    expires_at: datetime
    responsible_user_id: Optional[int] = None
    notes: Optional[str] = None


class NetworkItemPayload(BaseModel):
    name: str
    item_type: str = "OUTRO"
    ip_address: Optional[str] = None
    location: Optional[str] = None
    status: str = "ATIVO"
    notes: Optional[str] = None


class MaintenancePayload(BaseModel):
    asset_id: Optional[int] = None
    network_item_id: Optional[int] = None
    ticket_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    performed_by_user_id: Optional[int] = None
    status: str = "AGENDADA"


class CreateKanbanCardPayload(BaseModel):
    board_id: Optional[int] = None
    column_id: Optional[int] = None
    allow_duplicate: bool = False


class SummaryResponse(BaseModel):
    open_tickets: int
    in_progress_tickets: int
    suspended_tickets: int
    closed_today: int
    overdue_tickets: int
    critical_tickets: int
    expiring_certificates: int
    assets_in_maintenance: int
    my_tickets: int
    assigned_to_me: int


# Novos esquemas adicionados na Fase 5.2

class ITPeoplePayload(BaseModel):
    username: str
    email: str
    role_id: Optional[int] = None
    is_active: bool = True
    ramal: Optional[str] = None
    ip_address: Optional[str] = None
    network_point: Optional[str] = None
    sector: Optional[str] = None
    it_responsible: Optional[str] = None


class AssetCustomFieldPayload(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    field_type: str = "TEXT"  # TEXT, NUMBER, DATE, SELECT, BOOLEAN
    options: Optional[List[str]] = []
    is_active: bool = True


class CorporateEmailPayload(BaseModel):
    email_address: str
    login: Optional[str] = None
    user_id: Optional[int] = None
    server_config: Optional[str] = None
    recommended_client: Optional[str] = None
    status: str = "ATIVO"
    credential_id: Optional[int] = None


class NASFolderPayload(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    network_path: Optional[str] = None
    drive_letter: Optional[str] = None
    user_id: Optional[int] = None
    permission_level: str = "LEITURA"  # LEITURA, ESCRITA, ADMIN
    notes: Optional[str] = None


class ITNotePayload(BaseModel):
    title: Optional[str] = None
    content: str
    color: str = "yellow"
    tags: Optional[List[str]] = []
    responsible_user_id: Optional[int] = None
    is_pinned: bool = False
    is_archived: bool = False


class PcSpecsImportPayload(BaseModel):
    hostname: Optional[str] = None
    username: Optional[str] = None
    os: Optional[str] = None
    os_version: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    processor: Optional[str] = None
    ram_total: Optional[str] = None
    motherboard: Optional[str] = None
    gpu: Optional[str] = None
    storage: Optional[str] = None
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None
    domain: Optional[str] = None
    date: Optional[str] = None


class PcSpecsConfirmPayload(BaseModel):
    asset_id: Optional[int] = None  # Se omitido, cria um novo ativo
    hostname: str
    username: Optional[str] = None
    os: Optional[str] = None
    os_version: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    processor: Optional[str] = None
    ram: Optional[str] = None
    motherboard: Optional[str] = None
    gpu: Optional[str] = None
    storage: Optional[str] = None
    ip_address: Optional[str] = None
    ramal: Optional[str] = None
    network_point: Optional[str] = None
    sector: Optional[str] = None
    it_responsible: Optional[str] = None
    apply_fields: List[str]  # Lista de campos a serem aplicados (ex: ["processor", "ram", "motherboard"])


class ImportCSVConfirmPayload(BaseModel):
    assets: List[AssetPayload]
    update_existing: bool = True

