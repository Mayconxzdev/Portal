from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime

class LegacyPromotionRequest(BaseModel):
    reason: str = Field(..., description="Justificativa do administrador para realizar a promoção")

class PromoteBatchRequest(BaseModel):
    module: str = Field(..., description="Módulo alvo da promoção (ex: MASTER_DATA)")
    reason: str = Field(default="Promoção em lote via painel de dados reais", description="Justificativa")

class PromoteBatchResponse(BaseModel):
    promoted_count: int
    skipped_count: int
    module: str


class LegacyPromotionRowRequest(BaseModel):
    reason: str = Field(..., description="Justificativa para a promoção desta linha específica")

class LegacyPromotionPreviewItem(BaseModel):
    entity_target: str
    to_create: int
    to_link_existing: int
    to_skip_duplicate: int
    total: int

class LegacyPromotionPreview(BaseModel):
    source_app: str
    module_target: str
    summary: List[LegacyPromotionPreviewItem]
    can_promote: bool

class LegacyPromotionStatus(BaseModel):
    batch_id: uuid.UUID
    status: str
    total_rows: int
    processed_rows: int
    promoted_rows: int
    skipped_rows: int
    failed_rows: int
    started_at: datetime
    finished_at: Optional[datetime] = None

class LegacyEntityLinkResponse(BaseModel):
    id: uuid.UUID
    legacy_row_id: Optional[uuid.UUID]
    source_app: str
    entity_target: str
    official_entity_type: str
    official_entity_id: str
    action: str
    created_at: datetime

    class Config:
        from_attributes = True

class SyncPortalAccessResponse(BaseModel):
    status: str
    users_synced: int
    accesses_created: int
    timestamp: datetime

class DashboardMetricItem(BaseModel):
    count: int
    label: str

class RealDataDashboard(BaseModel):
    suppliers_count: int
    customers_count: int
    products_count: int
    services_count: int
    price_history_count: int
    it_access_count: int
    legacy_ops_count: int
    legacy_projects_count: int
    legacy_proposals_count: int
    legacy_files_count: int
    pending_review_count: int
    blocked_duplicates_count: int

class ITAccessRecordRead(BaseModel):
    id: int
    user_id: Optional[int] = None
    person_id: Optional[uuid.UUID] = None
    legacy_user_name: Optional[str] = None
    system_id: Optional[int] = None
    system_name: str
    access_profile: Optional[str] = None
    status: str
    origin: str
    has_secret: bool
    last_updated_at: datetime
    created_at: datetime
    updated_at: datetime
    user_name: Optional[str] = None
    user_email: Optional[str] = None

    class Config:
        from_attributes = True

class LegacyOperationalRecordRead(BaseModel):
    id: uuid.UUID
    legacy_row_id: Optional[uuid.UUID] = None
    source_app: str
    entity_target: str
    title: str
    status: Optional[str] = None
    responsible: Optional[str] = None
    record_date: Optional[datetime] = None
    data_json: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True

class LegacyFileIndexRead(BaseModel):
    id: uuid.UUID
    legacy_row_id: Optional[uuid.UUID] = None
    file_name: str
    file_path_masked: str
    file_type: str
    file_size_bytes: Optional[int] = None
    category: Optional[str] = None
    suggested_module: Optional[str] = None
    tags: Optional[Any] = None
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True
