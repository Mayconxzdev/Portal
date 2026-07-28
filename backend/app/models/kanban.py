from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint, BigInteger
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


json_type = JSON().with_variant(postgresql.JSONB, "postgresql")


class KanbanBoard(Base):
    __tablename__ = "kanban_boards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    module_origin: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    icon: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    columns: Mapped[List["KanbanColumn"]] = relationship("KanbanColumn", back_populates="board", cascade="all, delete-orphan")
    cards: Mapped[List["KanbanCard"]] = relationship("KanbanCard", back_populates="board", cascade="all, delete-orphan")
    permissions: Mapped[List["KanbanBoardPermission"]] = relationship("KanbanBoardPermission", back_populates="board", cascade="all, delete-orphan")
    custom_fields: Mapped[List["KanbanCustomField"]] = relationship("KanbanCustomField", back_populates="board", cascade="all, delete-orphan")
    labels: Mapped[List["KanbanLabel"]] = relationship("KanbanLabel", back_populates="board", cascade="all, delete-orphan")
    tv_views: Mapped[List["KanbanTVView"]] = relationship("KanbanTVView", back_populates="board", cascade="all, delete-orphan")
    views: Mapped[List["KanbanBoardView"]] = relationship("KanbanBoardView", back_populates="board", cascade="all, delete-orphan")


class KanbanBoardPermission(Base):
    __tablename__ = "kanban_board_permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    board_id: Mapped[int] = mapped_column(ForeignKey("kanban_boards.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True)
    role_id: Mapped[Optional[int]] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), index=True, nullable=True)
    access_level: Mapped[str] = mapped_column(String, nullable=False, default="READ_ONLY")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    board: Mapped["KanbanBoard"] = relationship("KanbanBoard", back_populates="permissions")


class KanbanColumn(Base):
    __tablename__ = "kanban_columns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    board_id: Mapped[int] = mapped_column(ForeignKey("kanban_boards.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    color: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    wip_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_done_column: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    board: Mapped["KanbanBoard"] = relationship("KanbanBoard", back_populates="columns")
    cards: Mapped[List["KanbanCard"]] = relationship("KanbanCard", back_populates="column")


class KanbanCard(Base):
    __tablename__ = "kanban_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    board_id: Mapped[int] = mapped_column(ForeignKey("kanban_boards.id", ondelete="CASCADE"), index=True, nullable=False)
    column_id: Mapped[int] = mapped_column(ForeignKey("kanban_columns.id", ondelete="RESTRICT"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    priority: Mapped[str] = mapped_column(String, default="MEDIUM", index=True, nullable=False)
    status: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True, nullable=True)
    assigned_to_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    custom_fields: Mapped[Optional[Dict[str, Any]]] = mapped_column(json_type, nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    board: Mapped["KanbanBoard"] = relationship("KanbanBoard", back_populates="cards")
    column: Mapped["KanbanColumn"] = relationship("KanbanColumn", back_populates="cards")
    checklists: Mapped[List["KanbanCardChecklist"]] = relationship("KanbanCardChecklist", back_populates="card", cascade="all, delete-orphan")
    comments: Mapped[List["KanbanCardComment"]] = relationship("KanbanCardComment", back_populates="card", cascade="all, delete-orphan")
    attachments: Mapped[List["KanbanCardAttachment"]] = relationship("KanbanCardAttachment", back_populates="card", cascade="all, delete-orphan")
    label_links: Mapped[List["KanbanCardLabel"]] = relationship("KanbanCardLabel", back_populates="card", cascade="all, delete-orphan")
    assignees: Mapped[List["KanbanCardAssignee"]] = relationship("KanbanCardAssignee", back_populates="card", cascade="all, delete-orphan")


class KanbanCustomField(Base):
    __tablename__ = "kanban_custom_fields"
    __table_args__ = (UniqueConstraint("board_id", "key", name="uq_kanban_custom_field_board_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    board_id: Mapped[int] = mapped_column(ForeignKey("kanban_boards.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    key: Mapped[str] = mapped_column(String, nullable=False)
    field_type: Mapped[str] = mapped_column(String, nullable=False)
    options: Mapped[Optional[Dict[str, Any]]] = mapped_column(json_type, nullable=True)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    board: Mapped["KanbanBoard"] = relationship("KanbanBoard", back_populates="custom_fields")


class KanbanActivity(Base):
    __tablename__ = "kanban_activity"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    board_id: Mapped[int] = mapped_column(ForeignKey("kanban_boards.id", ondelete="CASCADE"), index=True, nullable=False)
    card_id: Mapped[Optional[int]] = mapped_column(ForeignKey("kanban_cards.id", ondelete="CASCADE"), index=True, nullable=True)
    actor_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True)
    action: Mapped[str] = mapped_column(String, nullable=False)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column("metadata", json_type, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), index=True, nullable=False)


class KanbanCardChecklist(Base):
    __tablename__ = "kanban_card_checklists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("kanban_cards.id", ondelete="CASCADE"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    card: Mapped["KanbanCard"] = relationship("KanbanCard", back_populates="checklists")
    items: Mapped[List["KanbanCardChecklistItem"]] = relationship("KanbanCardChecklistItem", back_populates="checklist", cascade="all, delete-orphan")


class KanbanCardChecklistItem(Base):
    __tablename__ = "kanban_card_checklist_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    checklist_id: Mapped[int] = mapped_column(ForeignKey("kanban_card_checklists.id", ondelete="CASCADE"), index=True, nullable=False)
    text: Mapped[str] = mapped_column(String, nullable=False)
    is_done: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    completed_by_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    checklist: Mapped["KanbanCardChecklist"] = relationship("KanbanCardChecklist", back_populates="items")


class KanbanCardComment(Base):
    __tablename__ = "kanban_card_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("kanban_cards.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    comment: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    edited_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    card: Mapped["KanbanCard"] = relationship("KanbanCard", back_populates="comments")


class File(Base):
    __tablename__ = "files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    original_filename: Mapped[str] = mapped_column(String, nullable=False)
    stored_filename: Mapped[str] = mapped_column(String, nullable=False)
    content_type: Mapped[str] = mapped_column(String, nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    storage_provider: Mapped[str] = mapped_column(String, nullable=False, default="local")
    storage_bucket: Mapped[str] = mapped_column(String, nullable=False, default="local")
    storage_key: Mapped[str] = mapped_column(String, nullable=False)
    checksum_sha256: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    uploaded_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class FileModuleLink(Base):
    __tablename__ = "file_module_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    file_id: Mapped[int] = mapped_column(ForeignKey("files.id", ondelete="CASCADE"), index=True, nullable=False)
    module_slug: Mapped[str] = mapped_column(String, nullable=False)
    entity_type: Mapped[str] = mapped_column(String, nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class KanbanCardAttachment(Base):
    __tablename__ = "kanban_card_attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("kanban_cards.id", ondelete="CASCADE"), index=True, nullable=False)
    file_id: Mapped[int] = mapped_column(ForeignKey("files.id", ondelete="CASCADE"), index=True, nullable=False)
    uploaded_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    card: Mapped["KanbanCard"] = relationship("KanbanCard", back_populates="attachments")
    file: Mapped["File"] = relationship("File")


class KanbanLabel(Base):
    __tablename__ = "kanban_labels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    board_id: Mapped[int] = mapped_column(ForeignKey("kanban_boards.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    color: Mapped[str] = mapped_column(String, nullable=False, default="#64748b")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    board: Mapped["KanbanBoard"] = relationship("KanbanBoard", back_populates="labels")
    card_links: Mapped[List["KanbanCardLabel"]] = relationship("KanbanCardLabel", back_populates="label", cascade="all, delete-orphan")


class KanbanCardLabel(Base):
    __tablename__ = "kanban_card_labels"
    __table_args__ = (UniqueConstraint("card_id", "label_id", name="uq_kanban_card_label"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("kanban_cards.id", ondelete="CASCADE"), index=True, nullable=False)
    label_id: Mapped[int] = mapped_column(ForeignKey("kanban_labels.id", ondelete="CASCADE"), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    card: Mapped["KanbanCard"] = relationship("KanbanCard", back_populates="label_links")
    label: Mapped["KanbanLabel"] = relationship("KanbanLabel", back_populates="card_links")


class KanbanCardAssignee(Base):
    __tablename__ = "kanban_card_assignees"
    __table_args__ = (UniqueConstraint("card_id", "user_id", name="uq_kanban_card_assignee"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("kanban_cards.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    assigned_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    card: Mapped["KanbanCard"] = relationship("KanbanCard", back_populates="assignees")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])


class KanbanTVView(Base):
    __tablename__ = "kanban_tv_views"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    board_id: Mapped[int] = mapped_column(ForeignKey("kanban_boards.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False, default="Padrao")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    layout_type: Mapped[str] = mapped_column(String, nullable=False, default="COLUMNS")
    refresh_interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    show_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    show_done_columns: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    show_checklist_progress: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    show_assignees: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    show_labels: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    show_due_date: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    show_card_description: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    group_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    sort_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    filters: Mapped[Optional[Dict[str, Any]]] = mapped_column(json_type, nullable=True)
    visible_custom_fields: Mapped[Optional[List[str]]] = mapped_column(json_type, nullable=True)
    display_options: Mapped[Optional[Dict[str, Any]]] = mapped_column(json_type, nullable=True)
    kpi_options: Mapped[Optional[Dict[str, Any]]] = mapped_column(json_type, nullable=True)
    layout_options: Mapped[Optional[Dict[str, Any]]] = mapped_column(json_type, nullable=True)
    external_mode_options: Mapped[Optional[Dict[str, Any]]] = mapped_column(json_type, nullable=True)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    board: Mapped["KanbanBoard"] = relationship("KanbanBoard", back_populates="tv_views")


class KanbanBoardView(Base):
    __tablename__ = "kanban_board_views"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    board_id: Mapped[int] = mapped_column(ForeignKey("kanban_boards.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    view_type: Mapped[str] = mapped_column(String, nullable=False, default="BOARD")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    density: Mapped[str] = mapped_column(String, nullable=False, default="COMFORTABLE")
    visible_columns: Mapped[Optional[List[str]]] = mapped_column(json_type, nullable=True)
    column_order: Mapped[Optional[List[str]]] = mapped_column(json_type, nullable=True)
    column_widths: Mapped[Optional[Dict[str, Any]]] = mapped_column(json_type, nullable=True)
    filters: Mapped[Optional[Dict[str, Any]]] = mapped_column(json_type, nullable=True)
    sort_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    group_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    color_rules: Mapped[Optional[Dict[str, Any]]] = mapped_column(json_type, nullable=True)
    font_scale: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    auto_scroll: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    auto_scroll_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    board: Mapped["KanbanBoard"] = relationship("KanbanBoard", back_populates="views")
