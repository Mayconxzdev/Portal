from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


ACCESS_LEVELS = {"NO_ACCESS", "READ_ONLY", "NORMAL", "MANAGER", "ADMIN"}
CARD_PRIORITIES = {"LOW", "MEDIUM", "HIGH", "URGENT"}
FIELD_TYPES = {"TEXT", "NUMBER", "DATE", "SELECT", "MULTI_SELECT", "BOOLEAN", "USER", "URL"}
VIEW_TYPES = {"BOARD", "LIST", "TV_BOARD", "TV_LIST", "PRODUCTION_LIST", "PRODUCTION_BOARD"}
DENSITIES = {"COMFORTABLE", "COMPACT", "DENSE"}


class BoardCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    slug: Optional[str] = None
    description: Optional[str] = None
    module_origin: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    preset: Optional[str] = None
    default_view_type: Optional[str] = None


class BoardUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    description: Optional[str] = None
    module_origin: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None


class BoardPermissionResponse(BaseModel):
    id: int
    board_id: int
    user_id: Optional[int]
    role_id: Optional[int]
    access_level: str
    username: Optional[str] = None
    user_email: Optional[str] = None
    role_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ColumnCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)
    color: Optional[str] = None
    wip_limit: Optional[int] = None
    is_done_column: bool = False


class ColumnUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=80)
    color: Optional[str] = None
    wip_limit: Optional[int] = None
    is_done_column: Optional[bool] = None


class ColumnReorderItem(BaseModel):
    column_id: int
    position: int


class ColumnReorderPayload(BaseModel):
    columns: List[ColumnReorderItem]


class CustomFieldCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)
    key: str = Field(..., min_length=2, max_length=80)
    field_type: str
    options: Optional[Dict[str, Any]] = None
    is_required: bool = False
    position: Optional[int] = None
    display: Optional[Dict[str, Any]] = None


class CustomFieldUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=80)
    key: Optional[str] = Field(default=None, min_length=2, max_length=80)
    field_type: Optional[str] = None
    options: Optional[Dict[str, Any]] = None
    is_required: Optional[bool] = None
    is_active: Optional[bool] = None
    position: Optional[int] = None
    display: Optional[Dict[str, Any]] = None


class CustomFieldResponse(BaseModel):
    id: int
    board_id: int
    name: str
    key: str
    field_type: str
    options: Optional[Dict[str, Any]]
    is_required: bool
    is_active: bool
    position: int

    model_config = ConfigDict(from_attributes=True)


class CardCreate(BaseModel):
    column_id: int
    title: str = Field(..., min_length=2, max_length=160)
    description: Optional[str] = None
    priority: str = "MEDIUM"
    status: Optional[str] = None
    due_date: Optional[datetime] = None
    assigned_to_user_id: Optional[int] = None
    custom_fields: Optional[Dict[str, Any]] = None


class CardUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=2, max_length=160)
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[datetime] = None
    assigned_to_user_id: Optional[int] = None
    custom_fields: Optional[Dict[str, Any]] = None


class CardMovePayload(BaseModel):
    column_id: Optional[int] = None
    position: Optional[int] = None
    to_column_id: Optional[int] = None
    new_position: Optional[int] = None


class CardDuplicatePayload(BaseModel):
    title: Optional[str] = Field(default=None, min_length=2, max_length=160)
    column_id: Optional[int] = None
    copy_checklist: bool = True
    copy_labels: bool = True
    copy_assignees: bool = True
    copy_custom_fields: bool = True
    copy_comments: bool = False
    copy_attachments: bool = False


class BoardDuplicatePayload(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    slug: Optional[str] = None
    copy_cards: bool = True
    copy_labels: bool = True
    copy_custom_fields: bool = True
    copy_views: bool = True


class UserMiniResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    role_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class LabelCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=60)
    color: str = "#64748b"


class LabelUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=60)
    color: Optional[str] = None
    is_active: Optional[bool] = None


class LabelResponse(BaseModel):
    id: int
    board_id: int
    name: str
    color: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class CardAssigneeResponse(BaseModel):
    id: int
    card_id: int
    user_id: int
    assigned_by_user_id: int
    created_at: datetime
    user: Optional[UserMiniResponse] = None

    model_config = ConfigDict(from_attributes=True)


class ChecklistItemCreate(BaseModel):
    text: str = Field(..., min_length=1, max_length=500)


class ChecklistItemUpdate(BaseModel):
    text: Optional[str] = Field(default=None, min_length=1, max_length=500)
    is_done: Optional[bool] = None
    position: Optional[int] = None


class ChecklistItemReorderItem(BaseModel):
    item_id: int
    position: int


class ChecklistItemReorderPayload(BaseModel):
    items: List[ChecklistItemReorderItem]


class ChecklistCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)


class ChecklistUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=120)
    position: Optional[int] = None


class ChecklistItemResponse(BaseModel):
    id: int
    checklist_id: int
    text: str
    is_done: bool
    position: int
    created_by_user_id: int
    completed_by_user_id: Optional[int]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChecklistResponse(BaseModel):
    id: int
    card_id: int
    title: str
    position: int
    created_by_user_id: int
    created_at: datetime
    updated_at: datetime
    items: List[ChecklistItemResponse] = []

    model_config = ConfigDict(from_attributes=True)


class CommentCreate(BaseModel):
    comment: str = Field(..., min_length=1, max_length=5000)


class CommentUpdate(BaseModel):
    comment: str = Field(..., min_length=1, max_length=5000)


class CommentResponse(BaseModel):
    id: int
    card_id: int
    user_id: int
    comment: str
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]
    edited_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class FileResponse(BaseModel):
    id: int
    original_filename: str
    content_type: str
    size_bytes: int
    storage_provider: str
    checksum_sha256: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AttachmentResponse(BaseModel):
    id: int
    card_id: int
    file_id: int
    uploaded_by_user_id: int
    created_at: datetime
    deleted_at: Optional[datetime]
    file: Optional[FileResponse] = None

    model_config = ConfigDict(from_attributes=True)


class BoardViewCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    view_type: str = "BOARD"
    is_default: bool = False
    density: str = "COMFORTABLE"
    visible_columns: Optional[List[str]] = None
    column_order: Optional[List[str]] = None
    column_widths: Optional[Dict[str, Any]] = None
    filters: Optional[Dict[str, Any]] = None
    sort_by: Optional[str] = None
    group_by: Optional[str] = None
    color_rules: Optional[Dict[str, Any]] = None
    font_scale: Optional[str] = None
    auto_scroll: bool = False
    auto_scroll_seconds: Optional[int] = Field(default=None, ge=1, le=3600)


class BoardViewUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    view_type: Optional[str] = None
    is_default: Optional[bool] = None
    density: Optional[str] = None
    visible_columns: Optional[List[str]] = None
    column_order: Optional[List[str]] = None
    column_widths: Optional[Dict[str, Any]] = None
    filters: Optional[Dict[str, Any]] = None
    sort_by: Optional[str] = None
    group_by: Optional[str] = None
    color_rules: Optional[Dict[str, Any]] = None
    font_scale: Optional[str] = None
    auto_scroll: Optional[bool] = None
    auto_scroll_seconds: Optional[int] = Field(default=None, ge=1, le=3600)


class BoardViewResponse(BaseModel):
    id: int
    board_id: int
    name: str
    view_type: str
    is_default: bool
    density: str
    visible_columns: Optional[List[str]]
    column_order: Optional[List[str]]
    column_widths: Optional[Dict[str, Any]]
    filters: Optional[Dict[str, Any]]
    sort_by: Optional[str]
    group_by: Optional[str]
    color_rules: Optional[Dict[str, Any]]
    font_scale: Optional[str]
    auto_scroll: bool
    auto_scroll_seconds: Optional[int]
    created_by_user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BoardPermissionUpsert(BaseModel):
    user_id: Optional[int] = None
    role_id: Optional[int] = None
    access_level: str


class BoardImportPreviewResponse(BaseModel):
    import_id: str
    filename: str
    headers: List[str]
    rows: List[Dict[str, Any]]
    total_rows: int


class BoardImportConfirmPayload(BaseModel):
    import_id: str
    mapping: Dict[str, str]
    duplicate_field: Optional[str] = None
    duplicate_strategy: str = "ignore"
    default_column_id: Optional[int] = None


class TVConfigUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    is_default: Optional[bool] = None
    layout_type: Optional[str] = None
    refresh_interval_seconds: Optional[int] = Field(default=None, ge=10, le=600)
    show_archived: Optional[bool] = None
    show_done_columns: Optional[bool] = None
    show_checklist_progress: Optional[bool] = None
    show_assignees: Optional[bool] = None
    show_labels: Optional[bool] = None
    show_due_date: Optional[bool] = None
    show_card_description: Optional[bool] = None
    group_by: Optional[str] = None
    sort_by: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    visible_custom_fields: Optional[List[str]] = None
    display_options: Optional[Dict[str, Any]] = None
    kpi_options: Optional[Dict[str, Any]] = None
    layout_options: Optional[Dict[str, Any]] = None
    external_mode_options: Optional[Dict[str, Any]] = None


class TVConfigResponse(BaseModel):
    id: Optional[int] = None
    board_id: int
    name: str
    is_default: bool
    layout_type: str
    refresh_interval_seconds: int
    show_archived: bool
    show_done_columns: bool
    show_checklist_progress: bool
    show_assignees: bool
    show_labels: bool
    show_due_date: bool
    show_card_description: bool
    group_by: Optional[str]
    sort_by: Optional[str]
    filters: Optional[Dict[str, Any]]
    visible_custom_fields: Optional[List[str]] = []
    display_options: Optional[Dict[str, Any]] = {}
    kpi_options: Optional[Dict[str, Any]] = {}
    layout_options: Optional[Dict[str, Any]] = {}
    external_mode_options: Optional[Dict[str, Any]] = {}

    model_config = ConfigDict(from_attributes=True)


class QuickCardPayload(BaseModel):
    text: str = Field(..., min_length=2, max_length=300)
    board_id: Optional[int] = None
    column_id: Optional[int] = None
    confirm: bool = False


class CardResponse(BaseModel):
    id: int
    board_id: int
    column_id: int
    title: str
    description: Optional[str]
    position: int
    priority: str
    status: Optional[str]
    due_date: Optional[datetime]
    assigned_to_user_id: Optional[int]
    created_by_user_id: int
    custom_fields: Optional[Dict[str, Any]]
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    labels: List[LabelResponse] = []
    assignees: List[CardAssigneeResponse] = []
    checklist_total: int = 0
    checklist_done: int = 0

    model_config = ConfigDict(from_attributes=True)


class ColumnResponse(BaseModel):
    id: int
    board_id: int
    name: str
    position: int
    color: Optional[str]
    wip_limit: Optional[int]
    is_done_column: bool
    is_archived: bool
    cards: List[CardResponse] = []

    model_config = ConfigDict(from_attributes=True)


class BoardResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str]
    module_origin: Optional[str]
    color: Optional[str]
    icon: Optional[str]
    is_archived: bool
    created_by_user_id: int
    created_at: datetime
    updated_at: datetime
    access_level: Optional[str] = None
    columns: List[ColumnResponse] = []
    custom_fields: List[CustomFieldResponse] = []
    permissions: List[BoardPermissionResponse] = []
    labels: List[LabelResponse] = []
    views: List[BoardViewResponse] = []

    model_config = ConfigDict(from_attributes=True)


class ActivityResponse(BaseModel):
    id: int
    board_id: int
    card_id: Optional[int]
    actor_user_id: Optional[int]
    action: str
    metadata: Optional[Dict[str, Any]] = Field(default=None, validation_alias="metadata_json", serialization_alias="metadata")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KanbanSummaryResponse(BaseModel):
    active_boards: int
    total_cards: int = 0
    open_cards: int
    overdue_cards: int
    assigned_to_me: int = 0
    unassigned_cards: int = 0
    high_priority_cards: int = 0
    recently_updated_cards: int = 0
    cards_by_priority: Dict[str, int]
    cards_by_board: Dict[str, int] = {}
    simple_pending: int
