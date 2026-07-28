import uuid
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# ---------------------------------------------------------------------------
# Batches (Lotes de Importação)
# ---------------------------------------------------------------------------

class LegacyImportBatchBase(BaseModel):
    source_app: str = Field(..., description="COMPRASAPP2 | PROPOSTASAPP | PRODUCAOAPP | PROJETOAPP | HELPDESK | CYBERSUL | XLSX | CSV | NAS")
    source_name: str = Field(..., description="Nome descritivo da origem do lote, ex: Compras Nova.xlsx")
    source_path_masked: str = Field(..., description="Caminho mascarado do arquivo de origem")
    module_target: str = Field(..., alias="module_target", description="Modulo alvo ex: purchases, it, production, projects, proposals")
    notes: Optional[str] = None
    tenant_id: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)

class LegacyImportBatchCreate(BaseModel):
    source_app: str
    source_name: str
    source_path_masked: str
    module_target: str
    notes: Optional[str] = None
    tenant_id: Optional[str] = None

class LegacyImportBatchRead(BaseModel):
    id: uuid.UUID
    source_app: str
    source_name: str
    source_path_masked: str
    module_target: str
    status: str
    total_rows: int
    valid_rows: int
    duplicate_rows: int
    error_rows: int
    created_by_user_id: Optional[int] = None
    created_at: datetime
    finished_at: Optional[datetime] = None
    notes: Optional[str] = None
    tenant_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Rows (Linhas de Importação)
# ---------------------------------------------------------------------------

class LegacyImportRowCreate(BaseModel):
    source_table_or_sheet: Optional[str] = None
    source_row_id: Optional[str] = None
    entity_target: str = Field(..., description="SUPPLIER | PRODUCT_ITEM | PRICE_HISTORY | PRICE_REFERENCE | CUSTOMER | PROPOSAL | OP | PROJECT_TASK | IT_TICKET | IT_ASSET | FILE | TEMPLATE | CREDENTIAL_METADATA")
    raw_data_json: Dict[str, Any] = Field(default_factory=dict)
    normalized_data_json: Optional[Dict[str, Any]] = None
    issues_json: Optional[Dict[str, Any]] = None
    confidence_score: Optional[float] = None
    status: str = "PENDING_REVIEW"

class LegacyImportRowBulkCreate(BaseModel):
    rows: List[LegacyImportRowCreate]

class LegacyImportRowRead(BaseModel):
    id: uuid.UUID
    batch_id: uuid.UUID
    source_app: str
    source_table_or_sheet: Optional[str] = None
    source_row_id: Optional[str] = None
    module_target: str
    entity_target: str
    raw_data_json: Dict[str, Any]
    normalized_data_json: Dict[str, Any]
    detected_duplicates_json: Optional[Dict[str, Any]] = None
    issues_json: Optional[Dict[str, Any]] = None
    confidence_score: Optional[float] = None
    status: str
    created_at: datetime
    reviewed_by_user_id: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    tenant_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Duplicate Candidates (Candidatos a Duplicado)
# ---------------------------------------------------------------------------

class LegacyDuplicateCandidateRead(BaseModel):
    id: uuid.UUID
    row_id: uuid.UUID
    target_entity_type: str
    target_entity_id: Optional[str] = None
    match_type: str
    score: float
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Decisions (Decisões de Revisão)
# ---------------------------------------------------------------------------

class LegacyImportDecisionCreate(BaseModel):
    decision: str = Field(..., description="ACCEPT | REJECT | MERGE | CREATE_NEW | UPDATE_EXISTING | NEEDS_MORE_INFO")
    reason: Optional[str] = None

class LegacyImportDecisionRead(BaseModel):
    id: uuid.UUID
    row_id: uuid.UUID
    decision: str
    reason: Optional[str] = None
    decided_by_user_id: int
    decided_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Summary (Resumo de Importações)
# ---------------------------------------------------------------------------

class LegacyImportSummary(BaseModel):
    total_batches: int
    total_rows: int
    status_counts: Dict[str, int]
    module_counts: Dict[str, int]
