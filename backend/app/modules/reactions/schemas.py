import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, model_validator
from app.modules.action_intents.schemas import mask_payload

class ReactionRuleBase(BaseModel):
    name: str
    description: Optional[str] = None
    event_type: str
    module: str
    enabled: bool = True
    priority: int = 0
    condition_json: Dict[str, Any] = {}
    action_type: str
    action_payload: Dict[str, Any] = {}
    cooldown_seconds: Optional[int] = None
    max_runs_per_hour: Optional[int] = None
    tenant_id: Optional[str] = None

class ReactionRuleCreate(ReactionRuleBase):
    pass

class ReactionRuleToggleEnabled(BaseModel):
    enabled: bool

class ReactionRuleRead(ReactionRuleBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    created_by_user_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def mask_sensitive_fields(self) -> "ReactionRuleRead":
        if self.action_payload:
            self.action_payload = mask_payload(self.action_payload)
        return self


class ReactionRuleRunRead(BaseModel):
    id: uuid.UUID
    rule_id: uuid.UUID
    event_id: uuid.UUID
    status: str
    condition_result: bool
    action_result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    executed_at: Optional[datetime] = None
    correlation_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def mask_sensitive_fields(self) -> "ReactionRuleRunRead":
        if self.action_result:
            self.action_result = mask_payload(self.action_result)
        return self
