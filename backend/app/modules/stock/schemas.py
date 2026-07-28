from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal

# Base Schema
class StockBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

# Summary Schema
class StockCatalogSummary(StockBase):
    total_items: int
    total_suppliers: int
    total_offers: int
    items_without_cybersul_code: int
    items_in_review: int
    low_stock_items: int
    last_import_at: Optional[datetime] = None
    
    # Novos campos positivos
    total_operational_items: Optional[int] = 0
    total_with_supplier: Optional[int] = 0
    total_with_price: Optional[int] = 0

# Import Runs
class StockCatalogImportRunRead(StockBase):
    id: UUID
    source_type: str
    source_path: str
    source_filename: str
    source_hash: str
    status: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    total_rows: int
    total_items: int
    total_offers: int
    total_errors: int
    total_review: int
    triggered_by_user_id: Optional[int] = None
    error_message: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None

# Tree Nodes
class StockCatalogTreeNodeRead(StockBase):
    id: UUID
    import_run_id: UUID
    source_type: str
    source_sheet: str
    parent_id: Optional[UUID] = None
    node_type: str
    title: str
    normalized_title: str
    path: str
    depth: int
    position: int
    start_row: int
    end_row: int
    style_signature: Optional[str] = None
    confidence: float
    needs_review: bool

# Item Specs
class StockCatalogItemSpecRead(StockBase):
    id: UUID
    item_id: UUID
    spec_key: str
    spec_value: str
    normalized_value: str

# Suppliers
class StockCatalogSupplierRead(StockBase):
    id: UUID
    name: str
    normalized_name: str
    document: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    contact_name: Optional[str] = None
    source: str
    active: bool
    metadata_json: Optional[Dict[str, Any]] = None

# Offers
class StockCatalogOfferRead(StockBase):
    id: UUID
    item_id: UUID
    supplier_id: UUID
    supplier_name: Optional[str] = None
    import_run_id: UUID
    source_sheet: str
    source_row: int
    price: Optional[float] = None
    price_raw: Optional[str] = None
    final_value: Optional[float] = None
    final_value_raw: Optional[str] = None
    currency: str
    unit: str
    availability: Optional[str] = None
    delivery_time: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    is_current: bool
    is_consolidated_line: bool
    confidence: float
    needs_review: bool
    created_at: datetime

# Price History
class StockCatalogPriceHistoryRead(StockBase):
    id: UUID
    item_id: Optional[UUID] = None
    supplier_id: Optional[UUID] = None
    supplier_name: Optional[str] = None
    old_price: Optional[float] = None
    new_price: float
    source: str
    source_reference: Optional[str] = None
    changed_by_user_id: Optional[int] = None
    changed_by_username: Optional[str] = None
    changed_by: Optional[str] = None
    changed_at: datetime
    evidence_file_id: Optional[int] = None
    notes: Optional[str] = None

# Cybersul Products
class StockCatalogCybersulProductRead(StockBase):
    id: UUID
    cybersul_code: str
    old_code: Optional[str] = None
    description: str
    normalized_description: str
    complement: Optional[str] = None
    unit: str
    balance_vesper: float
    balance_ventrio: float
    balance_total: float
    cost_price: Optional[float] = None
    supplier_name: Optional[str] = None
    ncm: Optional[str] = None
    group_name: Optional[str] = None
    active: bool
    source_row: int
    import_run_id: UUID
    metadata_json: Optional[Dict[str, Any]] = None

# Links
class StockCatalogLinkRead(StockBase):
    id: UUID
    stock_catalog_item_id: UUID
    cybersul_product_id: UUID
    match_type: str
    confidence: float
    match_reason: Optional[str] = None
    approved_by_user_id: Optional[int] = None
    approved_at: Optional[datetime] = None
    needs_review: bool
    cybersul_code: Optional[str] = None
    cybersul_description: Optional[str] = None

# Items
class StockCatalogItemRead(StockBase):
    id: UUID
    import_run_id: UUID
    source_sheet: str
    family_node_id: Optional[UUID] = None
    product_node_id: Optional[UUID] = None
    variation_node_id: Optional[UUID] = None
    display_name: str
    base_name: str
    normalized_name: str
    variation_label: Optional[str] = None
    normalized_measure: Optional[str] = None
    canonical_measure_key: Optional[str] = None
    measure_display: Optional[str] = None
    measure_kind: Optional[str] = None
    measure_aliases_json: Optional[List[str]] = None
    canonical_identity_key: Optional[str] = None
    specification_text: Optional[str] = None
    identity_hash: str
    internal_code: Optional[str] = None
    cybersul_product_id: Optional[UUID] = None
    active: bool
    quality_status: str
    needs_review: bool
    review_reason: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    
    # Relações serializadas
    specs: Optional[List[StockCatalogItemSpecRead]] = None
    offers: Optional[List[StockCatalogOfferRead]] = None
    cybersul_code: Optional[str] = None
    cybersul_description: Optional[str] = None
    family_path: Optional[str] = None
    offer_count: Optional[int] = 0
    has_price: Optional[bool] = False
    primary_supplier: Optional[str] = None
    primary_price: Optional[float] = None

# Review Queue
class StockCatalogReviewQueueRead(StockBase):
    id: UUID
    item_id: UUID
    item_display_name: Optional[str] = None
    import_run_id: UUID
    review_type: str
    severity: str
    title: str
    description: str
    raw_context_json: Optional[Dict[str, Any]] = None
    status: str
    resolved_by_user_id: Optional[int] = None
    resolved_at: Optional[datetime] = None

# Alerts
class StockCatalogAlertRead(StockBase):
    id: UUID
    item_id: UUID
    item_display_name: Optional[str] = None
    alert_type: str
    severity: str
    title: str
    description: str
    status: str
    created_at: datetime
    resolved_at: Optional[datetime] = None

# Price Update Input
class PriceUpdateInput(BaseModel):
    supplier_id: UUID
    new_price: float
    notes: Optional[str] = None

# Price Update Preview Response
class PriceUpdatePreview(BaseModel):
    item_id: UUID
    item_display_name: str
    supplier_id: UUID
    supplier_name: str
    old_price: Optional[float] = None
    new_price: float
    difference_amount: float
    difference_percent: float
    notes: Optional[str] = None
    updated_at: Optional[str] = None
    message: Optional[str] = None
