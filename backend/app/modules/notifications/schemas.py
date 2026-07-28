import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    user_id: Optional[int] = None
    role_target: Optional[str] = None
    module: str
    event_type: str
    title: str
    message: str
    severity: str
    status: str
    source_type: Optional[str] = None
    source_id: Optional[str] = None
    action_url: Optional[str] = None
    created_at: datetime
    read_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    correlation_id: Optional[str] = None
    tenant_id: Optional[str] = None

class NotificationListRead(BaseModel):
    items: list[NotificationRead]
    next_cursor: Optional[str] = None

class NotificationUnreadCountRead(BaseModel):
    count: int
