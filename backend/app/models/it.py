import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


json_type = JSON().with_variant(postgresql.JSONB, "postgresql")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ITTicket(Base):
    __tablename__ = "it_tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ticket_number: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    requester_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False)
    assigned_to_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="ABERTO", index=True, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default="MEDIA", index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(40), default="OUTRO", index=True, nullable=False)
    suspension_reason: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    sla_policy_id: Mapped[Optional[int]] = mapped_column(ForeignKey("it_sla_policies.id", ondelete="SET NULL"), nullable=True)
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True, nullable=True)
    first_response_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    kanban_card_id: Mapped[Optional[int]] = mapped_column(ForeignKey("kanban_cards.id", ondelete="SET NULL"), index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    requester: Mapped["User"] = relationship("User", foreign_keys=[requester_user_id])
    assignee: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assigned_to_user_id])
    sla_policy: Mapped[Optional["ITSlaPolicy"]] = relationship("ITSlaPolicy")
    kanban_card: Mapped[Optional["KanbanCard"]] = relationship("KanbanCard")
    comments: Mapped[List["ITTicketComment"]] = relationship("ITTicketComment", back_populates="ticket", cascade="all, delete-orphan")
    checklists: Mapped[List["ITTicketChecklist"]] = relationship("ITTicketChecklist", back_populates="ticket", cascade="all, delete-orphan")
    time_logs: Mapped[List["ITTicketTimeLog"]] = relationship("ITTicketTimeLog", back_populates="ticket", cascade="all, delete-orphan")
    attachments: Mapped[List["ITTicketAttachment"]] = relationship("ITTicketAttachment", back_populates="ticket", cascade="all, delete-orphan")


class ITTicketComment(Base):
    __tablename__ = "it_ticket_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("it_tickets.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    ticket: Mapped["ITTicket"] = relationship("ITTicket", back_populates="comments")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])


class ITTicketChecklist(Base):
    __tablename__ = "it_ticket_checklists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("it_tickets.id", ondelete="CASCADE"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    ticket: Mapped["ITTicket"] = relationship("ITTicket", back_populates="checklists")
    items: Mapped[List["ITTicketChecklistItem"]] = relationship("ITTicketChecklistItem", back_populates="checklist", cascade="all, delete-orphan")


class ITTicketChecklistItem(Base):
    __tablename__ = "it_ticket_checklist_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    checklist_id: Mapped[int] = mapped_column(ForeignKey("it_ticket_checklists.id", ondelete="CASCADE"), index=True, nullable=False)
    text: Mapped[str] = mapped_column(String, nullable=False)
    is_done: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    completed_by_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    checklist: Mapped["ITTicketChecklist"] = relationship("ITTicketChecklist", back_populates="items")


class ITChecklistTemplate(Base):
    __tablename__ = "it_checklist_templates"
    __table_args__ = (UniqueConstraint("category", "title", name="uq_it_checklist_template_category_title"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    category: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    items: Mapped[List[str]] = mapped_column(json_type, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class ITTicketTimeLog(Base):
    __tablename__ = "it_ticket_time_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("it_tickets.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    ticket: Mapped["ITTicket"] = relationship("ITTicket", back_populates="time_logs")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])


class ITTicketAttachment(Base):
    __tablename__ = "it_ticket_attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("it_tickets.id", ondelete="CASCADE"), index=True, nullable=False)
    comment_id: Mapped[Optional[int]] = mapped_column(ForeignKey("it_ticket_comments.id", ondelete="SET NULL"), nullable=True)
    file_id: Mapped[int] = mapped_column(ForeignKey("files.id", ondelete="CASCADE"), nullable=False)
    uploaded_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    ticket: Mapped["ITTicket"] = relationship("ITTicket", back_populates="attachments")
    file: Mapped["File"] = relationship("File")


class ITSlaPolicy(Base):
    __tablename__ = "it_sla_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    priority: Mapped[str] = mapped_column(String(20), default="MEDIA", index=True, nullable=False)
    response_minutes: Mapped[int] = mapped_column(Integer, default=240, nullable=False)
    resolution_minutes: Mapped[int] = mapped_column(Integer, default=1440, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class ITAsset(Base):
    __tablename__ = "it_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    asset_tag: Mapped[Optional[str]] = mapped_column(String, unique=True, index=True, nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    asset_type: Mapped[str] = mapped_column(String(30), default="OUTRO", index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="DISPONIVEL", index=True, nullable=False)
    assigned_to_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    serial_number: Mapped[Optional[str]] = mapped_column(String, unique=True, index=True, nullable=True)
    manufacturer: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    purchase_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    warranty_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    # Campos tecnicos avancados
    hostname: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    processor: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    ram: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    motherboard: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    gpu: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    network_card: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    power_supply: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    cabinet: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    monitor: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    mouse: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    mouse_pad: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    keyboard: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    storage: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    peripherals: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    ramal: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    network_point: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    sector: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    it_responsible: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_collection_source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    last_collection_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    custom_fields: Mapped[Optional[Dict[str, Any]]] = mapped_column(json_type, nullable=True, default=dict)

    assigned_to: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assigned_to_user_id])


class ITAccessCatalog(Base):
    __tablename__ = "it_access_catalog"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    system_name: Mapped[str] = mapped_column(String, index=True, nullable=False)
    access_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    owner_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    responsible_team: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    how_to_request: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class ITAccessRequest(Base):
    __tablename__ = "it_access_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    requester_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False)
    target_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False)
    system_name: Mapped[str] = mapped_column(String, nullable=False)
    access_type: Mapped[str] = mapped_column(String, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="ABERTA", index=True, nullable=False)
    ticket_id: Mapped[Optional[int]] = mapped_column(ForeignKey("it_tickets.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class ITCredential(Base):
    __tablename__ = "it_credentials_vault"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    system_name: Mapped[str] = mapped_column(String, index=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    secret_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    secret_hint: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    owner_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    visibility_level: Mapped[str] = mapped_column(String(30), default="IT_MANAGER", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    updated_by_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    last_revealed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_revealed_by_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class ITCertificate(Base):
    __tablename__ = "it_certificates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    domain_or_system: Mapped[str] = mapped_column(String, nullable=False)
    issuer: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    provider: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=False)
    responsible_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="VALIDO", index=True, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class ITNetworkItem(Base):
    __tablename__ = "it_network_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    item_type: Mapped[str] = mapped_column(String(30), default="OUTRO", index=True, nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="ATIVO", index=True, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class ITMaintenanceRecord(Base):
    __tablename__ = "it_maintenance_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    asset_id: Mapped[Optional[int]] = mapped_column(ForeignKey("it_assets.id", ondelete="SET NULL"), nullable=True)
    network_item_id: Mapped[Optional[int]] = mapped_column(ForeignKey("it_network_items.id", ondelete="SET NULL"), nullable=True)
    ticket_id: Mapped[Optional[int]] = mapped_column(ForeignKey("it_tickets.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    performed_by_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="AGENDADA", index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class ITTicketKanbanLink(Base):
    __tablename__ = "it_ticket_kanban_links"
    __table_args__ = (UniqueConstraint("ticket_id", "kanban_card_id", name="uq_it_ticket_kanban_link"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("it_tickets.id", ondelete="CASCADE"), index=True, nullable=False)
    kanban_card_id: Mapped[int] = mapped_column(ForeignKey("kanban_cards.id", ondelete="CASCADE"), index=True, nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class ITActivity(Base):
    __tablename__ = "it_activity"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ticket_id: Mapped[Optional[int]] = mapped_column(ForeignKey("it_tickets.id", ondelete="CASCADE"), index=True, nullable=True)
    asset_id: Mapped[Optional[int]] = mapped_column(ForeignKey("it_assets.id", ondelete="SET NULL"), nullable=True)
    credential_id: Mapped[Optional[int]] = mapped_column(ForeignKey("it_credentials_vault.id", ondelete="SET NULL"), nullable=True)
    certificate_id: Mapped[Optional[int]] = mapped_column(ForeignKey("it_certificates.id", ondelete="SET NULL"), nullable=True)
    network_item_id: Mapped[Optional[int]] = mapped_column(ForeignKey("it_network_items.id", ondelete="SET NULL"), nullable=True)
    actor_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True)
    action: Mapped[str] = mapped_column(String, index=True, nullable=False)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column("metadata", json_type, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True, nullable=False)


# Compatibilidade temporaria com referencias antigas do placeholder da TI.
ITEquipment = ITAsset


class ITAssetCustomField(Base):
    __tablename__ = "it_asset_custom_fields"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    field_type: Mapped[str] = mapped_column(String(30), default="TEXT", nullable=False)  # TEXT, NUMBER, DATE, SELECT, BOOLEAN
    options: Mapped[Optional[List[str]]] = mapped_column(json_type, nullable=True, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class ITCorporateEmail(Base):
    __tablename__ = "it_corporate_emails"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email_address: Mapped[str] = mapped_column(String(180), unique=True, index=True, nullable=False)
    login: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    server_config: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recommended_client: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="ATIVO", nullable=False)
    credential_id: Mapped[Optional[int]] = mapped_column(ForeignKey("it_credentials_vault.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    user: Mapped[Optional["User"]] = relationship("User")
    credential: Mapped[Optional["ITCredential"]] = relationship("ITCredential")


class ITNASFolder(Base):
    __tablename__ = "it_nas_folders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    network_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    drive_letter: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    permission_level: Mapped[str] = mapped_column(String(30), default="LEITURA", nullable=False)  # LEITURA, ESCRITA, ADMIN
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    user: Mapped[Optional["User"]] = relationship("User")


class ITNote(Base):
    __tablename__ = "it_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    color: Mapped[str] = mapped_column(String(30), default="yellow", nullable=False)
    tags: Mapped[Optional[List[str]]] = mapped_column(json_type, nullable=True, default=list)
    responsible_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    responsible: Mapped[Optional["User"]] = relationship("User", foreign_keys=[responsible_user_id])
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by_user_id])


class ITChangeLog(Base):
    __tablename__ = "it_change_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # CREATE, UPDATE, DELETE, REVEAL, COPY
    field_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    old_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    new_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    origin: Mapped[str] = mapped_column(String(30), default="MANUAL", nullable=False)  # MANUAL, TAURI_DESKTOP, POWERSHELL_JSON, CSV_XLSX, SYSTEM
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    user: Mapped["User"] = relationship("User")


class ITSystem(Base):
    __tablename__ = "it_systems"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class ITAccessRecord(Base):
    __tablename__ = "it_access_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    person_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("people.id", ondelete="SET NULL"), nullable=True)
    legacy_user_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    system_id: Mapped[Optional[int]] = mapped_column(ForeignKey("it_systems.id", ondelete="SET NULL"), nullable=True)
    system_name: Mapped[str] = mapped_column(String(100), nullable=False)
    access_profile: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", nullable=False)
    origin: Mapped[str] = mapped_column(String(50), nullable=False)  # PORTAL, COMPRAS, HELPDESK, TI_ROUTINES, etc.
    has_secret: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[user_id])
    person: Mapped[Optional["Person"]] = relationship("Person", foreign_keys=[person_id])
    system: Mapped[Optional["ITSystem"]] = relationship("ITSystem", foreign_keys=[system_id])

