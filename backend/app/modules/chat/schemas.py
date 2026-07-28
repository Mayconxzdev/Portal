from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class MessageReactionResponse(BaseModel):
    id: int
    user_id: int
    username: str
    emoji: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MentionResponse(BaseModel):
    id: int
    mention_type: str
    target_id: Optional[int] = None
    target_slug: Optional[str] = None
    display_label: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AttachmentResponse(BaseModel):
    id: int
    file_id: int
    original_filename: str
    size_bytes: int
    content_type: str
    attachment_type: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatMessageVersionResponse(BaseModel):
    id: int
    message_id: int
    previous_body: str
    new_body: str
    edited_by_user_id: int
    edited_by_username: str
    edited_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatMessageResponse(BaseModel):
    id: int
    conversation_id: int
    sender_user_id: int
    sender_username: str
    parent_message_id: Optional[int] = None
    message_type: str
    body: Optional[str] = None
    is_edited: bool
    is_deleted: bool
    is_pinned: bool
    is_ephemeral: bool
    expires_at: Optional[datetime] = None
    reply_count: int
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    deleted_by_user_id: Optional[int] = None
    reactions: List[MessageReactionResponse] = []
    mentions: List[MentionResponse] = []
    attachments: List[AttachmentResponse] = []
    edit_history: Optional[List[ChatMessageVersionResponse]] = None  # Visível apenas para o MESSIAS

    model_config = ConfigDict(from_attributes=True)


class ChatConversationMemberResponse(BaseModel):
    id: int
    user_id: int
    username: str
    role: str
    is_muted: bool
    joined_at: datetime
    last_read_message_id: Optional[int] = None
    last_read_at: Optional[datetime] = None
    notification_level: str

    model_config = ConfigDict(from_attributes=True)


class ChatConversationResponse(BaseModel):
    id: int
    type: str
    name: Optional[str] = None
    description: Optional[str] = None
    is_private: bool
    is_archived: bool
    created_by_user_id: int
    owner_user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    archived_at: Optional[datetime] = None
    members: List[ChatConversationMemberResponse] = []
    unread_count: int = 0
    last_message: Optional[ChatMessageResponse] = None

    model_config = ConfigDict(from_attributes=True)


class ChatConversationCreateRequest(BaseModel):
    type: str = Field(..., description="CHANNEL, GROUP, ou DM")
    name: Optional[str] = None
    description: Optional[str] = None
    is_private: bool = False
    member_ids: List[int] = []


class ChatConversationUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_private: Optional[bool] = None


class MentionCreateRequest(BaseModel):
    mention_type: str
    target_id: Optional[int] = None
    target_slug: Optional[str] = None
    display_label: str


class ChatMessageCreateRequest(BaseModel):
    parent_message_id: Optional[int] = None
    message_type: str = "TEXT"
    body: Optional[str] = None
    mentions: List[MentionCreateRequest] = []
    file_ids: List[int] = []
    is_ephemeral: bool = False
    expires_in_seconds: Optional[int] = None
    visibility_mode: Optional[str] = "NORMAL"


class ChatMessageUpdateRequest(BaseModel):
    body: str


class ChatReactionRequest(BaseModel):
    emoji: str


class ChatNotificationSettingResponse(BaseModel):
    id: int
    user_id: int
    conversation_id: Optional[int] = None
    global_level: str
    muted_until: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ChatNotificationSettingUpdateRequest(BaseModel):
    global_level: Optional[str] = None
    muted_until_seconds: Optional[int] = None  # Envia segundos de pausa (ex: 3600 para 1h)


class ChatMessiasAuditResponse(BaseModel):
    id: int
    messias_user_id: int
    messias_username: str
    action: str
    target_user_id: Optional[int] = None
    target_username: Optional[str] = None
    conversation_id: Optional[int] = None
    message_id: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatSearchResponse(BaseModel):
    messages: List[ChatMessageResponse] = []
    conversations: List[ChatConversationResponse] = []


class MentionSearchItemResponse(BaseModel):
    type: str  # USER, CHANNEL, GROUP, MODULE, IT_TICKET, KANBAN_CARD, etc.
    id: Optional[int] = None
    slug: Optional[str] = None
    label: str
    details: Optional[str] = None
    has_access: bool = True
