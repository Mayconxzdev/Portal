import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, model_validator

class ActionIntentStatus(str, Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    EXECUTION_BLOCKED = "EXECUTION_BLOCKED"
    EXECUTED = "EXECUTED"
    FAILED = "FAILED"

class ActionIntentRiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class ActionIntentBase(BaseModel):
    source: str
    source_ref_type: Optional[str] = None
    source_ref_id: Optional[str] = None
    proposed_action: str
    target_module: str
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    title: str
    summary: str
    risk_level: ActionIntentRiskLevel = ActionIntentRiskLevel.MEDIUM
    status: ActionIntentStatus = ActionIntentStatus.PENDING_REVIEW
    action_payload: Dict[str, Any] = Field(default_factory=dict)
    result_payload: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None
    approval_id: Optional[int] = None
    callback_log_id: Optional[uuid.UUID] = None
    event_id: Optional[uuid.UUID] = None
    created_by_user_id: Optional[int] = None
    reviewed_by_user_id: Optional[int] = None
    expires_at: Optional[datetime] = None
    correlation_id: Optional[str] = None
    tenant_id: Optional[str] = None

class ActionIntentCreateInternal(ActionIntentBase):
    pass

def mask_payload(data: Any) -> Any:
    if isinstance(data, dict):
        return {
            k: "******" if k.lower() in {"password", "token", "secret", "hashed_password", "key", "vault", "access_token", "api_key", "authorization"} else mask_payload(v)
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [mask_payload(x) for x in data]
    return data

class ActionIntentRead(ActionIntentBase):
    id: uuid.UUID
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    
    @model_validator(mode="after")
    def mask_sensitive_fields(self) -> "ActionIntentRead":
        if self.action_payload:
            self.action_payload = mask_payload(self.action_payload)
        if self.result_payload:
            self.result_payload = mask_payload(self.result_payload)
        return self

    class Config:
        from_attributes = True

class ActionIntentReject(BaseModel):
    reason: str

class ActionIntentReview(BaseModel):
    reason: Optional[str] = None

class ActionIntentExecuteRequest(BaseModel):
    idempotency_key: Optional[str] = None
    dry_run: bool = False

class ActionIntentExecutionRead(BaseModel):
    id: uuid.UUID
    action_intent_id: uuid.UUID
    executor_key: str
    idempotency_key: str
    status: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    attempts: int
    input_payload: Optional[Dict[str, Any]] = None
    result_payload: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_by_user_id: Optional[int] = None
    correlation_id: Optional[str] = None
    created_at: datetime

    @model_validator(mode="after")
    def mask_sensitive_fields(self) -> "ActionIntentExecutionRead":
        if self.input_payload:
            self.input_payload = mask_payload(self.input_payload)
        if self.result_payload:
            self.result_payload = mask_payload(self.result_payload)
        return self

    class Config:
        from_attributes = True

