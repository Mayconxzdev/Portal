from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class ApprovalCommentCreate(BaseModel):
    comment: str

class ApprovalCommentResponse(BaseModel):
    id: int
    approval_id: int
    user_id: int
    username: Optional[str] = None
    comment: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ApprovalDecisionCreate(BaseModel):
    decision: str  # APPROVED, REJECTED
    reason: Optional[str] = None

class ApprovalApprovePayload(BaseModel):
    reason: Optional[str] = None
    result_payload: Optional[Dict[str, Any]] = None

class ApprovalRejectPayload(BaseModel):
    reason: Optional[str] = None
    result_payload: Optional[Dict[str, Any]] = None

class ApprovalDecisionResponse(BaseModel):
    id: int
    approval_id: int
    decided_by_user_id: int
    username: Optional[str] = None
    decision: str
    reason: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ApprovalCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = None
    module_slug: str
    risk_level: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL
    action_type: str
    action_payload: Dict[str, Any] = Field(default_factory=dict)
    expires_at: Optional[datetime] = None

class ApprovalResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    module_slug: str
    requester_user_id: int
    requester_username: Optional[str] = None
    approver_user_id: Optional[int]
    approver_username: Optional[str] = None
    status: str
    risk_level: str
    action_type: str
    action_payload: Dict[str, Any]
    result_payload: Optional[Dict[str, Any]]
    expires_at: Optional[datetime]
    decided_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    comments: List[ApprovalCommentResponse] = []
    decisions: List[ApprovalDecisionResponse] = []

    model_config = ConfigDict(from_attributes=True)

class ApprovalSummaryResponse(BaseModel):
    total_pending: int
    my_requests_pending: int
    waiting_my_decision: int
    approved_recent: int
    rejected_recent: int
    by_risk: Dict[str, int]
    by_module: Dict[str, int]
