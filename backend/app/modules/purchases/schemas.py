"""
Schemas Pydantic para o módulo de Compras do Portal Vesper.
Validações de entrada e formatação de saída para a API REST.
"""
import uuid
from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal


# ---------------------------------------------------------------------------
# Fornecedores
# ---------------------------------------------------------------------------

class SupplierCreate(BaseModel):
    """Payload para criação de fornecedor."""
    company_name: str = Field(..., min_length=2, max_length=255)
    trade_name: Optional[str] = None
    cnpj: Optional[str] = Field(None, max_length=20)
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    category: Optional[str] = None
    notes: Optional[str] = None


class SupplierUpdate(BaseModel):
    """Payload para atualização de fornecedor."""
    company_name: Optional[str] = Field(None, min_length=2, max_length=255)
    trade_name: Optional[str] = None
    cnpj: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    category: Optional[str] = None
    notes: Optional[str] = None


class SupplierResponse(BaseModel):
    """Resposta padrão de fornecedor."""
    id: uuid.UUID
    company_name: str
    trade_name: Optional[str] = None
    cnpj: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    category: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Itens da Requisição
# ---------------------------------------------------------------------------

class PurchaseItemCreate(BaseModel):
    """Payload para criação de item da requisição."""
    item_id: Optional[uuid.UUID] = None
    service_id: Optional[uuid.UUID] = None
    stock_catalog_item_id: Optional[uuid.UUID] = None
    free_text_description: Optional[str] = None
    quantity: float = Field(default=1, gt=0)
    unit_of_measure: str = Field(default="un", max_length=30)
    specifications: Optional[str] = None
    estimated_unit_price: Optional[float] = Field(None, ge=0)
    source_type: Optional[str] = None
    source_ref_id: Optional[str] = None
    source_confidence: Optional[str] = None
    match_status: str = "confirmed"
    source_snapshot_json: Optional[Dict[str, Any]] = None
    
    # Novos campos de status e classificação por item
    normalized_name: Optional[str] = None
    destination: Optional[str] = None
    department: Optional[str] = None
    budget_limit: Optional[float] = None
    classification: Optional[str] = "EXTERNAL"
    classification_confidence: Optional[float] = None
    requires_approval: bool = False

    # Retrocompatibilidade
    description: Optional[str] = None
    unit: Optional[str] = None
    notes: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def reconcile_legacy_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Mapeia descrição legada se free_text_description estiver vazia
            if "description" in data and not data.get("free_text_description") and not data.get("item_id") and not data.get("service_id"):
                data["free_text_description"] = data["description"]
            # Mapeia unidade legada
            if "unit" in data and not data.get("unit_of_measure"):
                data["unit_of_measure"] = data["unit"]
            # Mapeia observações legadas
            if "notes" in data and not data.get("specifications"):
                data["specifications"] = data["notes"]
        return data


class PurchaseItemUpdate(BaseModel):
    item_id: Optional[uuid.UUID] = None
    service_id: Optional[uuid.UUID] = None
    stock_catalog_item_id: Optional[uuid.UUID] = None
    free_text_description: Optional[str] = None
    quantity: Optional[float] = Field(None, gt=0)
    unit_of_measure: Optional[str] = Field(None, max_length=30)
    specifications: Optional[str] = None
    estimated_unit_price: Optional[float] = Field(None, ge=0)
    source_type: Optional[str] = None
    source_ref_id: Optional[str] = None
    source_confidence: Optional[str] = None
    match_status: Optional[str] = None
    source_snapshot_json: Optional[Dict[str, Any]] = None
    normalized_name: Optional[str] = None
    destination: Optional[str] = None
    department: Optional[str] = None
    budget_limit: Optional[float] = Field(None, ge=0)
    classification: Optional[str] = None
    classification_confidence: Optional[float] = Field(None, ge=0)
    requires_approval: Optional[bool] = None
    description: Optional[str] = None
    unit: Optional[str] = None
    notes: Optional[str] = None


class PurchaseOfferPriceConditionResponse(BaseModel):
    id: uuid.UUID
    option_id: uuid.UUID
    condition_type: str
    amount: float
    currency: str = "BRL"
    installments: Optional[int] = None
    installment_amount: Optional[float] = None
    discount_percent: Optional[float] = None
    is_recommended: bool = False
    source_label: Optional[str] = None
    evidence_status: str = "estimated"
    captured_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PurchaseItemOptionResponse(BaseModel):
    id: uuid.UUID
    purchase_item_id: uuid.UUID
    source_type: str
    supplier_id: Optional[uuid.UUID] = None
    store_name: Optional[str] = None
    seller_name: Optional[str] = None
    title: str
    brand: Optional[str] = None
    model: Optional[str] = None
    image_url: Optional[str] = None
    product_url: Optional[str] = None
    unit_price: float
    shipping_price: Optional[float] = None
    total_price: float
    delivery_estimate: Optional[str] = None
    availability: bool = True
    rating: Optional[float] = None
    review_count: Optional[int] = None
    specifications: Optional[str] = None
    captured_at: datetime
    raw_source_metadata: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    selected: bool = False
    rejection_reason: Optional[str] = None
    search_session_id: Optional[uuid.UUID] = None
    canonical_product_id: Optional[uuid.UUID] = None
    source_domain: Optional[str] = None
    source_rank: Optional[int] = None
    compatibility_score: Optional[float] = None
    confidence_score: Optional[float] = None
    evidence_level: Optional[str] = None
    shipping_destination: Optional[str] = None
    invoice_available: Optional[bool] = None
    payment_summary: Optional[str] = None
    warranty_summary: Optional[str] = None
    captured_method: Optional[str] = None
    verification_status: str = "DISCOVERED"
    verification_summary: Optional[str] = None
    price_conditions: List[PurchaseOfferPriceConditionResponse] = []

    model_config = ConfigDict(from_attributes=True)


class PurchaseItemOptionCreate(BaseModel):
    source_type: str
    supplier_id: Optional[uuid.UUID] = None
    store_name: Optional[str] = None
    seller_name: Optional[str] = None
    title: str
    brand: Optional[str] = None
    model: Optional[str] = None
    image_url: Optional[str] = None
    product_url: Optional[str] = None
    unit_price: float
    shipping_price: Optional[float] = None
    total_price: float
    delivery_estimate: Optional[str] = None
    availability: bool = True
    rating: Optional[float] = None
    review_count: Optional[int] = None
    specifications: Optional[str] = None
    raw_source_metadata: Optional[Dict[str, Any]] = None
    search_session_id: Optional[uuid.UUID] = None
    canonical_product_id: Optional[uuid.UUID] = None
    source_domain: Optional[str] = None
    source_rank: Optional[int] = None
    compatibility_score: Optional[float] = None
    confidence_score: Optional[float] = None
    evidence_level: Optional[str] = None
    shipping_destination: Optional[str] = None
    invoice_available: Optional[bool] = None
    payment_summary: Optional[str] = None
    warranty_summary: Optional[str] = None
    captured_method: Optional[str] = None
    verification_status: Optional[str] = None
    verification_summary: Optional[str] = None


class PurchaseResearchSessionCreate(BaseModel):
    query: Optional[str] = Field(None, max_length=500)
    destination: Optional[str] = Field(None, max_length=255)
    shipping_postal_code: str = Field(default="21043-030", max_length=20)
    budget_limit: Optional[float] = Field(None, ge=0)
    run_immediately: bool = True


class PurchaseResearchSessionResponse(BaseModel):
    id: str
    purchase_request_id: str
    purchase_item_id: str
    query: str
    category: str
    status: str
    progress_percent: int
    current_step: str
    destination: Optional[str] = None
    shipping_postal_code: str
    budget_limit: Optional[float] = None
    planner_summary: Dict[str, Any] = Field(default_factory=dict)
    recommendation_summary: Dict[str, Any] = Field(default_factory=dict)
    missing_questions: List[Dict[str, Any]] = Field(default_factory=list)
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    tasks: List[Dict[str, Any]] = Field(default_factory=list)
    canonical_products: List[Dict[str, Any]] = Field(default_factory=list)
    options: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class PurchaseRecommendationResponse(BaseModel):
    summary: str
    highlights: Dict[str, Any] = Field(default_factory=dict)
    why: List[str] = Field(default_factory=list)
    pending: List[Dict[str, Any]] = Field(default_factory=list)


class PurchaseItemApprovalPayload(BaseModel):
    option_id: Optional[uuid.UUID] = None
    justification: Optional[str] = None
    quantity: Optional[float] = Field(None, gt=0)
    alternatives: List[Dict[str, Any]] = Field(default_factory=list)


class PrepareSupplierRFQPayload(BaseModel):
    supplier_ids: List[uuid.UUID] = Field(default_factory=list)
    sender_account_id: Optional[uuid.UUID] = None
    homologation_mode: bool = False


class PrepareSupplierRFQResponse(BaseModel):
    rfq_id: uuid.UUID
    request_id: uuid.UUID
    item_id: uuid.UUID
    supplier_count: int
    homologation_mode: bool = False
    message: str


class PurchaseSuggestionResponse(BaseModel):
    id: Optional[str] = None
    label: str
    kind: str
    subtitle: Optional[str] = None
    confidence: float = 0
    stock_catalog_item_id: Optional[uuid.UUID] = None
    source: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PurchaseAnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=12000)
    context: Optional[str] = Field(None, max_length=80)
    idempotency_key: Optional[str] = Field(None, max_length=128)


class PurchaseInterpretedDraftItemResponse(BaseModel):
    id: uuid.UUID
    draft_id: uuid.UUID
    position: int
    item_type: str
    description: str
    quantity: float
    unit_of_measure: str
    budget_limit: Optional[float] = None
    destination: Optional[str] = None
    department: Optional[str] = None
    confidence_score: Optional[float] = None
    classification_reason: Optional[str] = None
    stock_catalog_item_id: Optional[uuid.UUID] = None
    missing_question_json: Optional[Dict[str, Any]] = None
    metadata_json: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class PurchaseAnalyzeResponse(BaseModel):
    draft_id: uuid.UUID
    status: str
    raw_input: str
    analysis_summary: Dict[str, Any] = Field(default_factory=dict)
    items: List[PurchaseInterpretedDraftItemResponse] = []


class PurchaseItemSplitPayload(BaseModel):
    first_quantity: float = Field(..., gt=0)
    second_description: Optional[str] = None
    second_quantity: Optional[float] = Field(None, gt=0)


class PurchaseItemsMergePayload(BaseModel):
    item_ids: List[uuid.UUID] = Field(..., min_length=2)
    description: Optional[str] = None


class PurchaseIdempotencyLookupResponse(BaseModel):
    status: str
    request: Optional["PurchaseRequestResponse"] = None
    error_message: Optional[str] = None


class PurchaseItemResponse(BaseModel):
    """Resposta padrão de item da requisição."""
    id: uuid.UUID
    purchase_request_id: uuid.UUID
    item_id: Optional[uuid.UUID] = None
    service_id: Optional[uuid.UUID] = None
    stock_catalog_item_id: Optional[uuid.UUID] = None
    free_text_description: Optional[str] = None
    quantity: float
    unit_of_measure: str
    specifications: Optional[str] = None
    estimated_unit_price: Optional[float] = None
    source_type: Optional[str] = None
    source_ref_id: Optional[str] = None
    source_confidence: Optional[str] = None
    match_status: str = "confirmed"
    source_snapshot_json: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    # Novos campos de status e classificação por item
    normalized_name: Optional[str] = None
    destination: Optional[str] = None
    department: Optional[str] = None
    budget_limit: Optional[float] = None
    classification: Optional[str] = "EXTERNAL"
    classification_confidence: Optional[float] = None
    selected_option_id: Optional[uuid.UUID] = None
    requires_approval: bool = False
    approval_status: str = "PENDING"
    purchasing_status: str = "PENDING"
    delivery_status: str = "PENDING"
    options: List[PurchaseItemOptionResponse] = []

    # Retrocompatibilidade
    description: str = ""
    unit: str = "un"
    notes: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def populate_legacy_fields(cls, data: Any) -> Any:
        # Se for um objeto ORM ou dict
        if not isinstance(data, dict):
            # Para objetos ORM com atributos
            desc = getattr(data, "free_text_description", None) or ""
            unit_val = getattr(data, "unit_of_measure", None) or "un"
            notes_val = getattr(data, "specifications", None)
            
            # Se tiver item_id/service_id e product_item/service preenchidos, podemos usar o nome como descrição de fallback
            p_item = getattr(data, "product_item", None)
            srv = getattr(data, "service", None)
            if p_item and not desc:
                desc = getattr(p_item, "name", "")
            elif srv and not desc:
                desc = getattr(srv, "name", "")
                
            return {
                "id": getattr(data, "id", None),
                "purchase_request_id": getattr(data, "purchase_request_id", None),
                "item_id": getattr(data, "item_id", None),
                "service_id": getattr(data, "service_id", None),
                "stock_catalog_item_id": getattr(data, "stock_catalog_item_id", None),
                "free_text_description": getattr(data, "free_text_description", None),
                "quantity": getattr(data, "quantity", 0),
                "unit_of_measure": unit_val,
                "specifications": notes_val,
                "estimated_unit_price": getattr(data, "estimated_unit_price", None),
                "source_type": getattr(data, "source_type", None),
                "source_ref_id": getattr(data, "source_ref_id", None),
                "source_confidence": getattr(data, "source_confidence", None),
                "match_status": getattr(data, "match_status", "confirmed") or "confirmed",
                "source_snapshot_json": getattr(data, "source_snapshot_json", None),
                "created_at": getattr(data, "created_at", None),
                "normalized_name": getattr(data, "normalized_name", None),
                "destination": getattr(data, "destination", None),
                "department": getattr(data, "department", None),
                "budget_limit": getattr(data, "budget_limit", None),
                "classification": getattr(data, "classification", "EXTERNAL") or "EXTERNAL",
                "classification_confidence": getattr(data, "classification_confidence", None),
                "selected_option_id": getattr(data, "selected_option_id", None),
                "requires_approval": getattr(data, "requires_approval", False),
                "approval_status": getattr(data, "approval_status", "PENDING") or "PENDING",
                "purchasing_status": getattr(data, "purchasing_status", "PENDING") or "PENDING",
                "delivery_status": getattr(data, "delivery_status", "PENDING") or "PENDING",
                "options": getattr(data, "options", []) or [],
                "description": desc,
                "unit": unit_val,
                "notes": notes_val
            }
        else:
            desc = data.get("free_text_description") or ""
            data["description"] = desc
            data["unit"] = data.get("unit_of_measure") or "un"
            data["notes"] = data.get("specifications")
            if "classification" not in data:
                data["classification"] = "EXTERNAL"
            if "requires_approval" not in data:
                data["requires_approval"] = False
            if "approval_status" not in data:
                data["approval_status"] = "PENDING"
            if "purchasing_status" not in data:
                data["purchasing_status"] = "PENDING"
            if "delivery_status" not in data:
                data["delivery_status"] = "PENDING"
            if "options" not in data:
                data["options"] = []
        return data

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Requisição de Compra
# ---------------------------------------------------------------------------

class PurchaseRequestCreate(BaseModel):
    """Payload para criação de requisição de compra."""
    idempotency_key: Optional[str] = Field(None, max_length=128)
    client_request_id: Optional[str] = Field(None, max_length=128)
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    justification: Optional[str] = None
    priority: str = Field(default="NORMAL")  # LOW, NORMAL, HIGH, URGENT
    urgency: str = Field(default="NORMAL")   # Retrocompatibilidade
    category: Optional[str] = None
    department: Optional[str] = None
    needed_by: Optional[datetime] = None
    origin_type: Optional[str] = None
    origin_ref_id: Optional[str] = None
    origin_snapshot_json: Optional[Dict[str, Any]] = None
    items: List[PurchaseItemCreate] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def reconcile_urgency_priority(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Mantém prioridade e urgência sincronizadas
            if "urgency" in data and "priority" not in data:
                data["priority"] = data["urgency"]
            elif "priority" in data and "urgency" not in data:
                data["urgency"] = data["priority"]
        return data


class PurchaseRequestUpdate(BaseModel):
    """Payload para atualização de requisição (apenas DRAFT)."""
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    justification: Optional[str] = None
    priority: Optional[str] = None
    urgency: Optional[str] = None
    category: Optional[str] = None
    department: Optional[str] = None
    needed_by: Optional[datetime] = None
    items: Optional[List["PurchaseRequestItemUpdate"]] = None


class PurchaseRequestItemUpdate(BaseModel):
    """Atualizacao pontual de item durante a revisao da compra."""
    id: uuid.UUID
    stock_catalog_item_id: Optional[uuid.UUID] = None
    free_text_description: Optional[str] = None
    quantity: Optional[float] = Field(None, gt=0)
    unit_of_measure: Optional[str] = Field(None, max_length=30)
    specifications: Optional[str] = None
    estimated_unit_price: Optional[float] = Field(None, ge=0)
    match_status: Optional[str] = None
    normalized_name: Optional[str] = None
    destination: Optional[str] = None
    department: Optional[str] = None
    budget_limit: Optional[float] = Field(None, ge=0)
    classification: Optional[str] = None
    classification_confidence: Optional[float] = Field(None, ge=0)
    requires_approval: Optional[bool] = None


PurchaseRequestUpdate.model_rebuild()


class PurchaseNeedParseTextPayload(BaseModel):
    """Texto colado pelo usuario para montar uma necessidade de compra sem gravar ainda."""
    text: str = Field(..., min_length=1, max_length=12000)


class PurchaseNeedImportLinkPayload(BaseModel):
    """Link informado pelo usuario. O Portal valida, mas nao faz scraping fragil."""
    url: str = Field(..., min_length=8, max_length=2048)
    notes: Optional[str] = Field(None, max_length=2000)


class PurchaseNeedImportCartPayload(BaseModel):
    """Link de carrinho externo. A importacao automatica depende de contrato real."""
    url: str = Field(..., min_length=8, max_length=2048)
    notes: Optional[str] = Field(None, max_length=2000)


class PurchaseNeedImportPreviewResponse(BaseModel):
    source_type: str
    source_url: str
    source_domain: str
    status: str
    title: str
    message: str
    can_create_request: bool = False
    suggested_request: Optional[PurchaseRequestCreate] = None


class PurchaseRequestResponse(BaseModel):
    """Resposta padrão de requisição de compra."""
    id: uuid.UUID
    title: str
    description: Optional[str] = None
    justification: Optional[str] = None
    requester_user_id: int
    requester_username: Optional[str] = None
    status: str
    priority: str = "NORMAL"
    urgency: str = "NORMAL"
    category: Optional[str] = None
    department: Optional[str] = None
    estimated_total: Optional[float] = None
    approved_total: Optional[float] = None
    needed_by: Optional[datetime] = None
    origin_type: Optional[str] = None
    origin_ref_id: Optional[str] = None
    origin_snapshot_json: Optional[Dict[str, Any]] = None
    approval_id: Optional[int] = None
    selected_quotation_id: Optional[uuid.UUID] = None
    items: List[PurchaseItemResponse] = []
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="before")
    @classmethod
    def extract_username(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            req = getattr(data, "requester", None)
            if req:
                setattr(data, "requester_username", getattr(req, "username", None))
        return data

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Itens da Cotação (Legado)
# ---------------------------------------------------------------------------

class QuotationItemCreate(BaseModel):
    """Payload para item da cotação."""
    purchase_item_id: uuid.UUID
    quoted_unit_price: float = Field(..., ge=0)
    delivery_days: Optional[int] = None
    notes: Optional[str] = None


class QuotationItemResponse(BaseModel):
    """Resposta padrão de item da cotação."""
    id: int
    quotation_id: int
    purchase_item_id: uuid.UUID
    quoted_unit_price: float
    delivery_days: Optional[int] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Cotação (Legado)
# ---------------------------------------------------------------------------

class QuotationCreate(BaseModel):
    """Payload para criação de cotação de fornecedor."""
    supplier_id: uuid.UUID
    payment_terms: Optional[str] = None
    delivery_days: Optional[int] = None
    valid_until: Optional[datetime] = None
    notes: Optional[str] = None
    items: List[QuotationItemCreate] = Field(default_factory=list)


class QuotationResponse(BaseModel):
    """Resposta padrão de cotação."""
    id: int
    purchase_request_id: uuid.UUID
    supplier_id: uuid.UUID
    supplier_name: Optional[str] = None
    status: str
    total_value: Optional[float] = None
    payment_terms: Optional[str] = None
    delivery_days: Optional[int] = None
    valid_until: Optional[datetime] = None
    notes: Optional[str] = None
    registered_by_user_id: int
    registered_by_username: Optional[str] = None
    items: List[QuotationItemResponse] = []
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="before")
    @classmethod
    def populate_names(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            sup = getattr(data, "supplier", None)
            if sup and getattr(sup, "person", None):
                setattr(data, "supplier_name", sup.person.name)
            reg = getattr(data, "registered_by", None)
            if reg:
                setattr(data, "registered_by_username", getattr(reg, "username", None))
        return data

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Atividades
# ---------------------------------------------------------------------------

class PurchaseActivityResponse(BaseModel):
    """Resposta de atividade/evento do módulo de Compras."""
    id: int
    purchase_request_id: uuid.UUID
    user_id: Optional[int] = None
    username: Optional[str] = None
    action: str
    details: Optional[Dict[str, Any]] = None
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def extract_username(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            usr = getattr(data, "user", None)
            if usr:
                setattr(data, "username", getattr(usr, "username", None))
        return data

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# RFQ Inteligente (PurchaseRFQ)
# ---------------------------------------------------------------------------

class PurchaseRFQCreate(BaseModel):
    """Payload para criação de RFQ."""
    title: str = Field(..., min_length=3, max_length=255)
    deadline: Optional[datetime] = None
    message_template: Optional[str] = None


class PurchaseRFQResponse(BaseModel):
    """Resposta contendo os dados da RFQ."""
    id: uuid.UUID
    purchase_request_id: uuid.UUID
    title: str
    status: str
    deadline: Optional[datetime] = None
    message_template: Optional[str] = None
    created_by_user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Fornecedores da RFQ (PurchaseRFQSupplier)
# ---------------------------------------------------------------------------

class PurchaseRFQSupplierCreate(BaseModel):
    """Payload para adicionar fornecedor a RFQ."""
    supplier_id: uuid.UUID
    contact_email: Optional[str] = None


class PurchaseRFQSupplierResponse(BaseModel):
    """Resposta com fornecedor associado a RFQ."""
    id: uuid.UUID
    rfq_id: uuid.UUID
    supplier_id: uuid.UUID
    supplier_name: Optional[str] = None
    contact_email: Optional[str] = None
    status: str
    message_subject: Optional[str] = None
    message_body: Optional[str] = None
    sent_at: Optional[datetime] = None
    response_received_at: Optional[datetime] = None
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def populate_supplier_name(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            sup = getattr(data, "supplier", None)
            if sup and getattr(sup, "person", None):
                setattr(data, "supplier_name", sup.person.name)
        return data

    model_config = ConfigDict(from_attributes=True)


class RFQDraftResponse(BaseModel):
    """Visualização de rascunhos de RFQ por fornecedor."""
    supplier_id: uuid.UUID
    supplier_name: str
    contact_email: Optional[str] = None
    subject: str
    body: str


class PurchaseQuoteCreate(BaseModel):
    """Cria uma cotacao operacional com conteiner e RFQ em rascunho."""
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    origin_type: str = "manual"
    origin_ref_id: Optional[str] = None
    origin_snapshot_json: Optional[Dict[str, Any]] = None


class PurchaseQuoteUpdate(BaseModel):
    """Atualiza dados simples da cotacao operacional."""
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = None


class PurchaseQuoteItemCreate(PurchaseItemCreate):
    """Adiciona item ao rascunho da cotacao."""
    pass


class PurchaseQuoteParseListPayload(BaseModel):
    text: str = Field(..., min_length=1)


class PurchaseQuoteParsedLine(BaseModel):
    raw_text: str
    description: str
    quantity: float = 1
    unit_of_measure: str = "un"
    confidence: str = "low"
    match_status: str = "needs_confirmation"
    purchase_type: str = "external"
    classification_message: Optional[str] = None
    match_score: float = 0
    suggested_stock_catalog_item_id: Optional[uuid.UUID] = None
    suggested_display_name: Optional[str] = None
    suggested_specification: Optional[str] = None
    destination: Optional[str] = None
    department: Optional[str] = None
    budget_limit: Optional[float] = None
    normalized_name: Optional[str] = None


class PurchaseQuoteSupplierSelection(BaseModel):
    supplier_id: uuid.UUID
    contact_email: Optional[str] = None
    item_ids: List[uuid.UUID] = Field(default_factory=list)


class PurchaseQuoteSupplierSelectionPayload(BaseModel):
    suppliers: List[PurchaseQuoteSupplierSelection] = Field(default_factory=list)


class PurchaseQuoteSupplierSuggestion(BaseModel):
    supplier_id: Optional[uuid.UUID] = None
    supplier_name: str
    contact_email: Optional[str] = None
    coverage_count: int = 0
    total_items: int = 0
    confidence: str = "check"
    status: str = "known"
    reasons: List[str] = Field(default_factory=list)
    item_ids: List[uuid.UUID] = Field(default_factory=list)


class PurchaseSenderAccountResponse(BaseModel):
    id: str
    company: Optional[str] = None
    email: str
    display_name: str
    status: str = "not_configured"
    bcc_default_enabled: bool = True
    default_bcc: Optional[str] = None
    secret_ref_masked: Optional[str] = None
    has_secret: bool = False
    is_configured: bool = False
    provider: str = "smtp"
    sent_folder: Optional[str] = None
    monitored_folder: Optional[str] = None
    last_test_at: Optional[datetime] = None
    last_error: Optional[str] = None


class PurchaseSenderAccountCreate(BaseModel):
    id: str = Field(..., max_length=80)
    company: str = Field(..., max_length=80)
    email: str = Field(..., max_length=255)
    display_name: str = Field(..., max_length=255)
    status: str = "not_configured"
    bcc_default_enabled: bool = True
    default_bcc: Optional[str] = None
    secret_ref: Optional[str] = None
    has_secret: bool = False


class PurchaseSenderAccountUpdate(BaseModel):
    company: Optional[str] = Field(None, max_length=80)
    email: Optional[str] = Field(None, max_length=255)
    display_name: Optional[str] = Field(None, max_length=255)
    status: Optional[str] = None
    bcc_default_enabled: Optional[bool] = None
    default_bcc: Optional[str] = None
    secret_ref: Optional[str] = None
    has_secret: Optional[bool] = None
    sent_folder: Optional[str] = None
    monitored_folder: Optional[str] = None


class PurchaseQuoteEmailPreviewItem(BaseModel):
    purchase_item_id: uuid.UUID
    description: str
    specifications: Optional[str] = None
    quantity: float
    unit_of_measure: str
    notes: Optional[str] = None


class PurchaseQuoteEmailPreview(BaseModel):
    message_id: uuid.UUID
    rfq_supplier_id: uuid.UUID
    supplier_id: uuid.UUID
    supplier_name: str
    to_email: Optional[str] = None
    sender_account_id: str
    sender_email: str
    sender_name: Optional[str] = None
    account_status: str = "not_configured"
    can_send: bool = False
    blocked_reason: Optional[str] = None
    bcc_enabled: bool = True
    bcc: Optional[str] = None
    bcc_source: str = "account_default"
    subject: str
    body_html: str
    body_text: Optional[str] = None
    signature_html: Optional[str] = None
    content_hash: str
    idempotency_key: str
    status: str = "draft"
    environment: str = "development"
    provider_message_id: Optional[str] = None
    human_status: Optional[str] = None
    pdf_optional_available: bool = False
    pdf_status: str = "not_configured"
    pdf_message: str = "PDF opcional sera ativado apos configurar o gerador de documentos."
    items: List[PurchaseQuoteEmailPreviewItem] = Field(default_factory=list)


class PurchaseEmailMessageUpdate(BaseModel):
    sender_account_id: Optional[str] = None
    to_email: Optional[str] = None
    subject: Optional[str] = None
    body_html: Optional[str] = None
    body_text: Optional[str] = None
    bcc_enabled: Optional[bool] = None
    bcc: Optional[str] = None


class PurchaseEmailMessageResponse(PurchaseQuoteEmailPreview):
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class PurchaseEmailSendResponse(BaseModel):
    message: PurchaseEmailMessageResponse
    duplicate_blocked: bool = False
    human_message: str


class PurchaseMonitoringCallbackAttachment(BaseModel):
    filename: Optional[str] = None
    content_type: Optional[str] = None
    size_bytes: int = Field(default=0, ge=0)
    sha256: Optional[str] = None
    storage_key: Optional[str] = None
    text_preview: Optional[str] = None


class PurchaseMonitoringEmailCallbackPayload(BaseModel):
    account_email: str
    folder: str = "INBOX"
    imap_uid: Optional[str] = None
    message_id: Optional[str] = None
    in_reply_to: Optional[str] = None
    references: List[str] = Field(default_factory=list)
    from_email: str
    from_name: Optional[str] = None
    to: List[str] = Field(default_factory=list)
    cc: List[str] = Field(default_factory=list)
    subject: Optional[str] = None
    received_at: datetime
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    attachments: List[PurchaseMonitoringCallbackAttachment] = Field(default_factory=list)
    raw_headers: Dict[str, Any] = Field(default_factory=dict)


class PurchaseMonitoringCallbackResponse(BaseModel):
    status: str
    duplicate: bool = False
    inbound_message_id: Optional[uuid.UUID] = None
    candidate_ids: List[uuid.UUID] = Field(default_factory=list)
    human_message: str


class PurchaseEmailAttachmentResponse(BaseModel):
    id: uuid.UUID
    inbound_message_id: uuid.UUID
    filename: Optional[str] = None
    safe_filename: str
    content_type: Optional[str] = None
    detected_content_type: Optional[str] = None
    size_bytes: int
    sha256: Optional[str] = None
    storage_key: Optional[str] = None
    scan_status: str
    blocked_reason: Optional[str] = None
    text_preview: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PurchaseInboundMessageResponse(BaseModel):
    id: uuid.UUID
    account_email: str
    folder: str
    imap_uid: Optional[str] = None
    message_id: Optional[str] = None
    in_reply_to: Optional[str] = None
    references: List[str] = Field(default_factory=list)
    from_email: str
    from_name: Optional[str] = None
    to: List[str] = Field(default_factory=list)
    cc: List[str] = Field(default_factory=list)
    subject: Optional[str] = None
    body_text: Optional[str] = None
    body_html_sanitized: Optional[str] = None
    received_at: datetime
    status: str
    classification_status: str
    linked_quote_id: Optional[uuid.UUID] = None
    linked_supplier_id: Optional[uuid.UUID] = None
    confidence_score: Optional[float] = None
    confidence_level: Optional[str] = None
    attachments: List[PurchaseEmailAttachmentResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class PurchaseResponseCandidateResponse(BaseModel):
    id: uuid.UUID
    inbound_message_id: uuid.UUID
    quote_id: Optional[uuid.UUID] = None
    rfq_id: Optional[uuid.UUID] = None
    supplier_id: Optional[uuid.UUID] = None
    supplier_name: Optional[str] = None
    quote_title: Optional[str] = None
    quote_code: Optional[str] = None
    from_email: str
    from_name: Optional[str] = None
    subject: Optional[str] = None
    body_text: Optional[str] = None
    received_at: datetime
    candidate_status: str
    confidence_score: float
    confidence_level: str
    match_reasons: List[str] = Field(default_factory=list)
    risk_flags: List[str] = Field(default_factory=list)
    attachments: List[PurchaseEmailAttachmentResponse] = Field(default_factory=list)
    human_status: str
    created_at: datetime
    updated_at: datetime


class PurchaseInboundLinkPayload(BaseModel):
    quote_id: uuid.UUID
    supplier_id: Optional[uuid.UUID] = None


class PurchaseResponseCandidateDecisionResponse(BaseModel):
    candidate: PurchaseResponseCandidateResponse
    human_message: str


class PurchaseResponseEvidenceResponse(BaseModel):
    id: uuid.UUID
    extraction_id: uuid.UUID
    field_id: Optional[uuid.UUID] = None
    attachment_id: Optional[uuid.UUID] = None
    source_type: str
    source_label: Optional[str] = None
    snippet: str
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    page_number: Optional[int] = None
    row_number: Optional[int] = None
    confidence_level: str
    created_at: datetime


class PurchaseResponseExtractedFieldResponse(BaseModel):
    id: uuid.UUID
    extraction_id: uuid.UUID
    field_name: str
    label: str
    raw_value: Optional[str] = None
    normalized_value: Optional[str] = None
    value_type: str
    confidence_level: str
    confidence_score: float
    review_status: str
    source_type: str
    source_label: Optional[str] = None
    evidences: List[PurchaseResponseEvidenceResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class PurchaseResponseExtractionResponse(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    inbound_message_id: uuid.UUID
    quote_id: Optional[uuid.UUID] = None
    supplier_id: Optional[uuid.UUID] = None
    status: str
    extractor_version: str
    confidence_summary: str
    fields: List[PurchaseResponseExtractedFieldResponse] = Field(default_factory=list)
    evidences: List[PurchaseResponseEvidenceResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    reviewed_at: Optional[datetime] = None


class PurchaseResponseFieldDecision(BaseModel):
    field_id: uuid.UUID
    decision: str = Field(..., pattern="^(accept|correct|reject)$")
    reviewed_value: Optional[str] = None
    note: Optional[str] = None


class PurchaseResponseExtractionReviewPayload(BaseModel):
    decisions: List[PurchaseResponseFieldDecision] = Field(default_factory=list)


class PurchaseResponseExtractionReviewResponse(BaseModel):
    extraction: PurchaseResponseExtractionResponse
    human_message: str


class PurchaseQuoteDetailResponse(BaseModel):
    id: uuid.UUID
    purchase_request_id: uuid.UUID
    title: str
    description: Optional[str] = None
    status: str
    origin_type: Optional[str] = None
    origin_ref_id: Optional[str] = None
    origin_snapshot_json: Optional[Dict[str, Any]] = None
    items: List[PurchaseItemResponse] = Field(default_factory=list)
    suppliers: List[PurchaseRFQSupplierResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Resposta de Cotação de Fornecedor (PurchaseQuoteResponse)
# ---------------------------------------------------------------------------

class PurchaseQuoteLineCreate(BaseModel):
    """Linha individual de cotação a ser criada."""
    request_item_id: Optional[uuid.UUID] = None
    description: str = Field(..., max_length=500)
    quantity: float = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)
    delivery_days: Optional[int] = None
    notes: Optional[str] = None


class PurchaseQuoteResponseCreate(BaseModel):
    """Payload para registrar cotação recebida."""
    rfq_supplier_id: Optional[uuid.UUID] = None
    supplier_id: uuid.UUID
    total_amount: Optional[float] = None
    currency: str = "BRL"
    delivery_days: Optional[int] = None
    payment_terms: Optional[str] = None
    validity_date: Optional[datetime] = None
    raw_text: Optional[str] = None
    attachment_file_id: Optional[str] = None
    parsed_json: Optional[Dict[str, Any]] = None
    lines: List[PurchaseQuoteLineCreate] = Field(default_factory=list)


class PurchaseQuoteLineResponse(BaseModel):
    """Linha de cotação respondida."""
    id: uuid.UUID
    quote_response_id: uuid.UUID
    request_item_id: Optional[uuid.UUID] = None
    description: str
    quantity: float
    unit_price: float
    total_price: float
    delivery_days: Optional[int] = None
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PurchaseQuoteResponseResponse(BaseModel):
    """Resposta com dados da cotação registrada."""
    id: uuid.UUID
    rfq_supplier_id: Optional[uuid.UUID] = None
    supplier_id: uuid.UUID
    supplier_name: Optional[str] = None
    total_amount: Optional[float] = None
    currency: str
    delivery_days: Optional[int] = None
    payment_terms: Optional[str] = None
    validity_date: Optional[datetime] = None
    raw_text: Optional[str] = None
    attachment_file_id: Optional[str] = None
    parsed_json: Optional[Dict[str, Any]] = None
    status: str
    created_at: datetime
    lines: List[PurchaseQuoteLineResponse] = []

    @model_validator(mode="before")
    @classmethod
    def populate_supplier_name(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            sup = getattr(data, "supplier", None)
            if sup and getattr(sup, "person", None):
                setattr(data, "supplier_name", sup.person.name)
        return data

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Comparativo de Cotações (PurchaseComparison)
# ---------------------------------------------------------------------------

class CompareItemOffer(BaseModel):
    """Detalhes da oferta de um fornecedor para determinado item."""
    supplier_id: uuid.UUID
    supplier_name: str
    unit_price: float
    total_price: float
    delivery_days: Optional[int] = None
    notes: Optional[str] = None


class CompareItemRow(BaseModel):
    """Linha do comparativo agrupando ofertas por item solicitado."""
    request_item_id: Optional[uuid.UUID]
    description: str
    requested_quantity: float
    offers: List[CompareItemOffer] = []


class CompareSupplierSummary(BaseModel):
    """Resumo consolidado das ofertas de cada fornecedor."""
    supplier_id: uuid.UUID
    supplier_name: str
    total_amount: float
    quote_response_id: Optional[uuid.UUID] = None
    average_delivery_days: Optional[float] = None
    payment_terms: Optional[str] = None
    is_best_price: bool = False
    is_best_delivery: bool = False


class PurchaseComparisonResponse(BaseModel):
    """Estrutura detalhada do comparativo de cotações side-by-side."""
    rfq_id: uuid.UUID
    best_supplier_id: Optional[uuid.UUID] = None
    best_supplier_name: Optional[str] = None
    recommendation_summary: Optional[str] = None
    created_at: datetime
    items_comparison: List[CompareItemRow] = []
    suppliers_summary: List[CompareSupplierSummary] = []

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Métricas / Dashboard
# ---------------------------------------------------------------------------

class PurchasesSummaryResponse(BaseModel):
    """Métricas resumidas do módulo de Compras para o Dashboard."""
    total_requests: int = 0
    drafts: int = 0
    pending_approval: int = 0
    approved: int = 0
    quoting: int = 0
    ordered: int = 0
    delivered: int = 0
    cancelled: int = 0
    total_suppliers: int = 0
    active_suppliers: int = 0
    total_quotations_pending: int = 0
    estimated_value_open: float = 0.0


class PurchaseAttentionItemResponse(BaseModel):
    """Item operacional que exige alguma acao do responsavel por Compras."""
    id: str
    type: str
    title: str
    description: str
    severity: str = "info"
    status: str
    quote_id: Optional[uuid.UUID] = None
    request_id: Optional[uuid.UUID] = None
    supplier_id: Optional[uuid.UUID] = None
    supplier_name: Optional[str] = None
    action_label: str
    updated_at: Optional[datetime] = None


class PurchaseStatusGroupResponse(BaseModel):
    """Agrupamento simples para a Central de Compras."""
    key: str
    label: str
    count: int = 0


class PurchaseOngoingQuoteResponse(BaseModel):
    """Linha compacta de cotacao em andamento."""
    request_id: uuid.UUID
    title: str
    status: str
    status_label: str
    stage: str
    items_count: int = 0
    suppliers_count: int = 0
    responses_count: int = 0
    coverage_label: str = "Sem fornecedores"
    next_action: str = "Abrir"
    responsible: Optional[str] = None
    updated_at: datetime


class PurchasesOverviewResponse(BaseModel):
    """Visao operacional da Central de Compras."""
    summary: PurchasesSummaryResponse
    queue_counts: Dict[str, int] = Field(default_factory=dict)
    status_groups: List[PurchaseStatusGroupResponse] = Field(default_factory=list)
    attention: List[PurchaseAttentionItemResponse] = Field(default_factory=list)
    ongoing_quotes: List[PurchaseOngoingQuoteResponse] = Field(default_factory=list)


# Detalhe com RFQs e Comparativo
class PurchaseRequestDetailResponse(PurchaseRequestResponse):
    """Resposta detalhada com cotações e atividades."""
    quotations: List[QuotationResponse] = []
    activities: List[PurchaseActivityResponse] = []
    rfqs: List[PurchaseRFQResponse] = []


# Reconstruir referências forward para modelos com referências cruzadas
PurchaseRequestDetailResponse.model_rebuild()


# ---------------------------------------------------------------------------
# Rastreabilidade de Preços de Compra (Price Traceability)
# ---------------------------------------------------------------------------

class PurchasePriceEvidenceCreate(BaseModel):
    """Payload para lançamento manual de evidência de preço."""
    source_type: str = Field(..., min_length=1, max_length=50) # BOLETO, NF, RFQ_RESPONSE, EMAIL, MANUAL_ENTRY, IMPORTED_XLSX, CYBERSUL
    supplier_id: Optional[uuid.UUID] = None
    product_item_id: Optional[uuid.UUID] = None
    service_id: Optional[uuid.UUID] = None
    document_number: Optional[str] = Field(None, max_length=100)
    document_date: Optional[datetime] = None
    unit_price: Optional[Decimal] = Field(None, ge=0)
    quantity: Optional[Decimal] = Field(None, ge=0)
    total_amount: Optional[Decimal] = Field(None, ge=0)
    currency: str = Field(default="BRL", max_length=10)
    unit_of_measure: Optional[str] = Field(None, max_length=30)
    payment_terms: Optional[str] = Field(None, max_length=255)
    due_date: Optional[datetime] = None
    file_id: Optional[str] = Field(None, max_length=100)
    raw_summary: Optional[str] = None
    notes: Optional[str] = None


class PurchasePriceEvidenceResponse(BaseModel):
    """Resposta de evidência cadastrada."""
    id: uuid.UUID
    source_type: str
    supplier_id: Optional[uuid.UUID] = None
    supplier_name: Optional[str] = None
    product_item_id: Optional[uuid.UUID] = None
    product_item_name: Optional[str] = None
    service_id: Optional[uuid.UUID] = None
    document_number: Optional[str] = None
    document_date: Optional[datetime] = None
    unit_price: Optional[Decimal] = None
    quantity: Optional[Decimal] = None
    total_amount: Optional[Decimal] = None
    currency: str
    unit_of_measure: Optional[str] = None
    payment_terms: Optional[str] = None
    due_date: Optional[datetime] = None
    file_id: Optional[str] = None
    raw_summary: Optional[str] = None
    notes: Optional[str] = None
    created_by_user_id: int
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def populate_names(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            sup = getattr(data, "supplier", None)
            if sup and getattr(sup, "person", None):
                setattr(data, "supplier_name", sup.person.name)
            prod = getattr(data, "product_item", None)
            if prod:
                setattr(data, "product_item_name", getattr(prod, "name", None))
        return data

    model_config = ConfigDict(from_attributes=True)


class PurchasePriceHistoryResponse(BaseModel):
    """Resposta de registro histórico imutável."""
    id: uuid.UUID
    product_item_id: uuid.UUID
    product_item_name: Optional[str] = None
    supplier_id: Optional[uuid.UUID] = None
    supplier_name: Optional[str] = None
    evidence_id: Optional[uuid.UUID] = None
    rfq_id: Optional[uuid.UUID] = None
    quote_response_id: Optional[uuid.UUID] = None
    unit_price: Decimal
    quantity: Optional[Decimal] = None
    total_amount: Optional[Decimal] = None
    currency: str
    unit_of_measure: Optional[str] = None
    observed_at: datetime
    source_type: str
    source_id: Optional[str] = None
    created_by_user_id: int
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def populate_names(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            sup = getattr(data, "supplier", None)
            if sup and getattr(sup, "person", None):
                setattr(data, "supplier_name", sup.person.name)
            prod = getattr(data, "product_item", None)
            if prod:
                setattr(data, "product_item_name", getattr(prod, "name", None))
        return data

    model_config = ConfigDict(from_attributes=True)


class PurchasePriceReferenceResponse(BaseModel):
    """Resposta de preço de referência homologado."""
    id: uuid.UUID
    product_item_id: uuid.UUID
    product_item_name: Optional[str] = None
    supplier_id: Optional[uuid.UUID] = None
    supplier_name: Optional[str] = None
    current_unit_price: Decimal
    currency: str
    unit_of_measure: Optional[str] = None
    source_history_id: Optional[uuid.UUID] = None
    source_evidence_id: Optional[uuid.UUID] = None
    approved_by_user_id: int
    approved_at: datetime
    notes: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="before")
    @classmethod
    def populate_names(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            sup = getattr(data, "supplier", None)
            if sup and getattr(sup, "person", None):
                setattr(data, "supplier_name", sup.person.name)
            prod = getattr(data, "product_item", None)
            if prod:
                setattr(data, "product_item_name", getattr(prod, "name", None))
        return data

    model_config = ConfigDict(from_attributes=True)


class PurchasePriceSuggestionResponse(BaseModel):
    """Resposta de sugestão de atualização de preço na fila."""
    id: uuid.UUID
    product_item_id: uuid.UUID
    product_item_name: Optional[str] = None
    supplier_id: Optional[uuid.UUID] = None
    supplier_name: Optional[str] = None
    evidence_id: uuid.UUID
    evidence_source_type: Optional[str] = None
    evidence_document_number: Optional[str] = None
    history_id: Optional[uuid.UUID] = None
    reference_id: Optional[uuid.UUID] = None
    old_unit_price: Optional[Decimal] = None
    new_unit_price: Decimal
    pct_variation: Optional[Decimal] = None
    variation_direction: str
    status: str
    reason: Optional[str] = None
    review_notes: Optional[str] = None
    created_by_user_id: int
    created_by_username: Optional[str] = None
    reviewed_by_user_id: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def populate_names(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            sup = getattr(data, "supplier", None)
            if sup and getattr(sup, "person", None):
                setattr(data, "supplier_name", sup.person.name)
            prod = getattr(data, "product_item", None)
            if prod:
                setattr(data, "product_item_name", getattr(prod, "name", None))
            cre = getattr(data, "created_by", None)
            if cre:
                setattr(data, "created_by_username", getattr(cre, "username", None))
            ev = getattr(data, "evidence", None)
            if ev:
                setattr(data, "evidence_source_type", getattr(ev, "source_type", None))
                setattr(data, "evidence_document_number", getattr(ev, "document_number", None))
        return data

    model_config = ConfigDict(from_attributes=True)


class PurchasePriceSuggestionReview(BaseModel):
    """Payload para aprovação/rejeição de sugestão."""
    review_notes: Optional[str] = None


class PurchaseProductPriceVariationResponse(BaseModel):
    """Variacao compravel de uma familia, com preco atual isolado por item."""
    id: uuid.UUID
    family_id: Optional[uuid.UUID] = None
    family_name: str
    name: str
    short_name: str
    variation_name: str
    attributes: Dict[str, Any] = Field(default_factory=dict)
    unit_of_measure: str
    category: Optional[str] = None
    current_price: Optional[Decimal] = None
    currency: str = "BRL"
    supplier_id: Optional[uuid.UUID] = None
    supplier_name: Optional[str] = None
    last_updated_at: Optional[datetime] = None
    history_count: int = 0
    suppliers_count: int = 0
    description: Optional[str] = None
    situation: Optional[str] = None
    needs_review: bool = False
    technical_details: Dict[str, Any] = Field(default_factory=dict)


class PurchaseProductPriceFamilyResponse(BaseModel):
    """Familia de produtos com resumo e variacoes carregadas sob demanda."""
    family_id: Optional[uuid.UUID] = None
    family_name: str
    description: Optional[str] = None
    category: Optional[str] = None
    variations_count: int = 0
    suppliers_count: int = 0
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None
    last_updated_at: Optional[datetime] = None
    variations: List[PurchaseProductPriceVariationResponse] = Field(default_factory=list)


class PurchaseProductsPricesSummaryResponse(BaseModel):
    """Metricas humanas para Produtos e Precos."""
    products_count: int = 0
    families_count: int = 0
    variations_count: int = 0
    catalog_rows_count: int = 0
    supplier_offers_count: int = 0
    current_prices_count: int = 0
    recently_updated_count: int = 0
    needs_review_count: int = 0
    suppliers_without_email_count: int = 0
    last_sync_at: Optional[datetime] = None
    last_sync_status: Optional[str] = None


class PurchaseProductsPricesResponse(BaseModel):
    """Resposta paginada da tela Produtos e Precos."""
    items: List[PurchaseProductPriceFamilyResponse] = Field(default_factory=list)
    total_variations: int = 0
    limit: int
    offset: int
    has_more: bool = False
    summary: PurchaseProductsPricesSummaryResponse


class PurchaseProductPriceUpdatePayload(BaseModel):
    """Atualizacao manual e auditada do preco de uma variacao."""
    new_price: Decimal = Field(..., gt=0)
    supplier_id: Optional[uuid.UUID] = None
    document_number: Optional[str] = Field(None, max_length=100)
    document_date: Optional[datetime] = None
    payment_terms: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None
    evidence_file_id: Optional[str] = Field(None, max_length=100)


class PurchaseProductPriceUpdateResponse(BaseModel):
    """Retorno da atualizacao direta de preco por variacao."""
    item_id: uuid.UUID
    family_name: str
    variation_name: str
    old_price: Optional[Decimal] = None
    new_price: Decimal
    difference_amount: Optional[Decimal] = None
    difference_percent: Optional[Decimal] = None
    supplier_id: Optional[uuid.UUID] = None
    supplier_name: Optional[str] = None
    history_id: Optional[uuid.UUID] = None
    reference_id: uuid.UUID
    updated_at: datetime


class PurchaseCatalogSummaryResponse(BaseModel):
    families_count: int = 0
    variations_count: int = 0
    catalog_rows_count: int = 0
    supplier_offers_count: int = 0
    current_prices_count: int = 0
    needs_review_count: int = 0
    suppliers_without_email_count: int = 0
    last_sync_at: Optional[datetime] = None
    last_sync_status: str = "not_synced"


class PurchaseCatalogSyncResponse(BaseModel):
    status: str
    message: str
    run_id: Optional[uuid.UUID] = None
    source_path: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)
    summary: PurchaseCatalogSummaryResponse


class PurchaseSupplierOfferResponse(BaseModel):
    id: uuid.UUID
    product_item_id: uuid.UUID
    supplier_id: Optional[uuid.UUID] = None
    supplier_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    raw_price: Optional[float] = None
    final_value: Optional[float] = None
    current_price: Optional[float] = None
    currency: str = "BRL"
    unit: str = "un"
    observed_at: Optional[str] = None
    is_current_supplier: bool = False
    is_consolidated: bool = False
    status: str = "Pronto"
    source_row_key: Optional[str] = None
    updated_at: Optional[datetime] = None


class PurchaseSupplierOffersResponse(BaseModel):
    items: List[PurchaseSupplierOfferResponse] = Field(default_factory=list)
    total: int = 0


class PurchaseCatalogItemDetailResponse(PurchaseProductPriceVariationResponse):
    offers: List[PurchaseSupplierOfferResponse] = Field(default_factory=list)
    catalog_rows: List[Dict[str, Any]] = Field(default_factory=list)


class PurchaseSupplierOfferUpdatePayload(BaseModel):
    new_price: Decimal = Field(..., gt=0)
    document_number: Optional[str] = Field(None, max_length=100)
    document_date: Optional[datetime] = None
    payment_terms: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None


class PurchaseXlsxReconciliationSummaryResponse(BaseModel):
    sheets_read: int = 0
    suppliers_found: int = 0
    suppliers_with_email: int = 0
    suppliers_with_phone: int = 0
    suppliers_in_portal: int = 0
    suppliers_missing: int = 0
    products_found: int = 0
    families_found: int = 0
    variations_found: int = 0
    ambiguous_items: int = 0
    prices_detected: int = 0
    prices_using_final_value: int = 0
    prices_matching_portal: int = 0
    prices_divergent: int = 0
    needs_review: int = 0
    suppliers_without_email: int = 0


class PurchaseXlsxReconciliationItemResponse(BaseModel):
    row_key: str
    sheet: str
    row_number: int
    category: str
    family: str
    subfamily: Optional[str] = None
    variation: str
    display_name: str
    supplier_name: Optional[str] = None
    company_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    spreadsheet_price: Optional[float] = None
    raw_price: Optional[float] = None
    final_value: Optional[float] = None
    portal_price: Optional[float] = None
    difference_amount: Optional[float] = None
    difference_percent: Optional[float] = None
    price_type: str
    unit: str
    updated_at: Optional[str] = None
    situation: str
    issues: List[str] = Field(default_factory=list)
    portal_item_id: Optional[uuid.UUID] = None
    portal_supplier_id: Optional[uuid.UUID] = None
    portal_item_name: Optional[str] = None
    portal_supplier_name: Optional[str] = None
    ready_for_quote: bool = False
    technical_details: Optional[Dict[str, Any]] = None


class PurchaseXlsxReconciliationResponse(BaseModel):
    source_path: str
    file_updated_at: Optional[str] = None
    sheets_read: List[str] = Field(default_factory=list)
    sheets_ignored: List[str] = Field(default_factory=list)
    layouts: Dict[str, int] = Field(default_factory=dict)
    summary: PurchaseXlsxReconciliationSummaryResponse
    items: List[PurchaseXlsxReconciliationItemResponse] = Field(default_factory=list)
    total: int
    limit: int
    offset: int
    has_more: bool = False


class PurchaseXlsxUpdatePricePayload(BaseModel):
    row_key: str
    product_item_id: uuid.UUID
    supplier_id: Optional[uuid.UUID] = None
    spreadsheet_price: Decimal = Field(..., gt=0)
    document_number: Optional[str] = None
    notes: Optional[str] = None


class PurchaseXlsxSupplierContactPayload(BaseModel):
    supplier_id: uuid.UUID
    email: Optional[str] = None
    phone: Optional[str] = None


class PurchaseXlsxExportResponse(BaseModel):
    path: str
    rows: int


class ChooseSupplierPayload(BaseModel):
    """Payload para escolha da proposta/fornecedor vencedor da RFQ."""
    quote_response_id: uuid.UUID


class PurchasePlaceOrderPayload(BaseModel):
    final_value: Decimal = Field(..., gt=0)
    shipping_price: Optional[Decimal] = Field(None, ge=0)
    order_number: Optional[str] = Field(None, max_length=100)
    delivery_estimate: Optional[datetime] = None
    payment_method: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class PurchaseOrderCreate(PurchasePlaceOrderPayload):
    request_id: uuid.UUID


class PurchaseReceiveItemPayload(BaseModel):
    item_id: uuid.UUID
    quantity_received: float = Field(..., ge=0)
    is_damaged: bool = False
    deviation_notes: Optional[str] = None
    save_in_catalog: bool = False


class PurchaseReceiveDeliveryPayload(BaseModel):
    items: List[PurchaseReceiveItemPayload]
    notes: Optional[str] = None


class PurchaseDeliveryCreate(PurchaseReceiveDeliveryPayload):
    request_id: uuid.UUID


PurchaseIdempotencyLookupResponse.model_rebuild()
