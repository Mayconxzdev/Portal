import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, Numeric, JSON, UUID, Integer
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class StockCatalogImportRun(Base):
    __tablename__ = "stock_catalog_import_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # COMPRAS_NOVA | CYBERSUL
    source_path: Mapped[str] = mapped_column(String(500), nullable=False)
    source_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="RUNNING", index=True)  # RUNNING | SUCCESS | FAILED
    started_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    total_items: Mapped[int] = mapped_column(Integer, default=0)
    total_offers: Mapped[int] = mapped_column(Integer, default=0)
    total_errors: Mapped[int] = mapped_column(Integer, default=0)
    total_review: Mapped[int] = mapped_column(Integer, default=0)
    triggered_by_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True
    )

    tree_nodes: Mapped[List["StockCatalogTreeNode"]] = relationship("StockCatalogTreeNode", back_populates="import_run", cascade="all, delete-orphan")
    items: Mapped[List["StockCatalogItem"]] = relationship("StockCatalogItem", back_populates="import_run", cascade="all, delete-orphan")


class StockCatalogSource(Base):
    __tablename__ = "stock_catalog_sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class StockCatalogTreeNode(Base):
    __tablename__ = "stock_catalog_tree_nodes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    import_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("stock_catalog_import_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # COMPRAS_NOVA
    source_sheet: Mapped[str] = mapped_column(String(100), nullable=False)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("stock_catalog_tree_nodes.id", ondelete="CASCADE"), nullable=True, index=True)
    node_type: Mapped[str] = mapped_column(String(50), nullable=False)  # sheet | family | product | variation | spec | offer_group
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    path: Mapped[str] = mapped_column(String(1000), nullable=False)
    depth: Mapped[int] = mapped_column(Integer, default=0)
    position: Mapped[int] = mapped_column(Integer, default=0)
    start_row: Mapped[int] = mapped_column(Integer, default=0)
    end_row: Mapped[int] = mapped_column(Integer, default=0)
    style_signature: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    confidence: Mapped[float] = mapped_column(Numeric(5, 4), default=1.0)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    canonical_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    canonical_category_display: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    canonical_parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    is_visible_to_common_user: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True
    )

    import_run: Mapped["StockCatalogImportRun"] = relationship("StockCatalogImportRun", back_populates="tree_nodes")
    parent = relationship("StockCatalogTreeNode", remote_side=[id], backref="children")


class StockCatalogItem(Base):
    __tablename__ = "stock_catalog_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    import_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("stock_catalog_import_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    source_sheet: Mapped[str] = mapped_column(String(100), nullable=False)
    family_node_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("stock_catalog_tree_nodes.id", ondelete="SET NULL"), nullable=True, index=True)
    product_node_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("stock_catalog_tree_nodes.id", ondelete="SET NULL"), nullable=True, index=True)
    variation_node_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("stock_catalog_tree_nodes.id", ondelete="SET NULL"), nullable=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    base_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    variation_label: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    normalized_measure: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    canonical_measure_key: Mapped[Optional[str]] = mapped_column(String(160), nullable=True, index=True)
    measure_display: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    measure_kind: Mapped[Optional[str]] = mapped_column(String(40), nullable=True, index=True)
    measure_aliases_json: Mapped[Optional[List[str]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True
    )
    canonical_identity_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, index=True)
    specification_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    identity_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    internal_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    cybersul_product_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("stock_catalog_cybersul_products.id", ondelete="SET NULL"), nullable=True, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    quality_status: Mapped[str] = mapped_column(String(50), default="READY", index=True)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    review_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    canonical_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    canonical_category_display: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    visibility_scope: Mapped[str] = mapped_column(String(50), default="COMMON", index=True)
    review_type: Mapped[str] = mapped_column(String(50), default="none", index=True)
    is_operational: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_searchable_common: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_tree_visible_common: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_offer_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_category_only: Mapped[bool] = mapped_column(Boolean, default=False)
    is_parser_junk: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    import_run: Mapped["StockCatalogImportRun"] = relationship("StockCatalogImportRun", back_populates="items")
    family_node = relationship("StockCatalogTreeNode", foreign_keys=[family_node_id])
    product_node = relationship("StockCatalogTreeNode", foreign_keys=[product_node_id])
    variation_node = relationship("StockCatalogTreeNode", foreign_keys=[variation_node_id])
    cybersul_product = relationship("StockCatalogCybersulProduct", back_populates="catalog_items")
    specs: Mapped[List["StockCatalogItemSpec"]] = relationship("StockCatalogItemSpec", back_populates="item", cascade="all, delete-orphan")
    offers: Mapped[List["StockCatalogOffer"]] = relationship("StockCatalogOffer", back_populates="item", cascade="all, delete-orphan")
    price_history: Mapped[List["StockCatalogPriceHistory"]] = relationship("StockCatalogPriceHistory", back_populates="item", cascade="all, delete-orphan")
    links: Mapped[List["StockCatalogLink"]] = relationship("StockCatalogLink", back_populates="catalog_item", cascade="all, delete-orphan")
    search_indexes: Mapped[List["StockCatalogSearchIndex"]] = relationship("StockCatalogSearchIndex", back_populates="item", cascade="all, delete-orphan")
    review_queue: Mapped[List["StockCatalogReviewQueue"]] = relationship("StockCatalogReviewQueue", back_populates="item", cascade="all, delete-orphan")
    alerts: Mapped[List["StockCatalogAlert"]] = relationship("StockCatalogAlert", back_populates="item", cascade="all, delete-orphan")


class StockCatalogItemSpec(Base):
    __tablename__ = "stock_catalog_item_specs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("stock_catalog_items.id", ondelete="CASCADE"), nullable=False, index=True)
    spec_key: Mapped[str] = mapped_column(String(100), nullable=False)
    spec_value: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_value: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    item: Mapped["StockCatalogItem"] = relationship("StockCatalogItem", back_populates="specs")


class StockCatalogSupplier(Base):
    __tablename__ = "stock_catalog_suppliers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    document: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    contact_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="XLSX_IMPORT")
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True
    )

    offers: Mapped[List["StockCatalogOffer"]] = relationship("StockCatalogOffer", back_populates="supplier")
    price_history: Mapped[List["StockCatalogPriceHistory"]] = relationship("StockCatalogPriceHistory", back_populates="supplier")


class StockCatalogOffer(Base):
    __tablename__ = "stock_catalog_offers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("stock_catalog_items.id", ondelete="CASCADE"), nullable=False, index=True)
    supplier_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("stock_catalog_suppliers.id", ondelete="CASCADE"), nullable=False, index=True)
    import_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("stock_catalog_import_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    source_sheet: Mapped[str] = mapped_column(String(100), nullable=False)
    source_row: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[Optional[float]] = mapped_column(Numeric(12, 4), nullable=True)
    price_raw: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    final_value: Mapped[Optional[float]] = mapped_column(Numeric(12, 4), nullable=True)
    final_value_raw: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="BRL")
    unit: Mapped[str] = mapped_column(String(30), default="un")
    availability: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    delivery_time: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_consolidated_line: Mapped[bool] = mapped_column(Boolean, default=False)
    confidence: Mapped[float] = mapped_column(Numeric(5, 4), default=1.0)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    item: Mapped["StockCatalogItem"] = relationship("StockCatalogItem", back_populates="offers")
    supplier: Mapped["StockCatalogSupplier"] = relationship("StockCatalogSupplier", back_populates="offers")
    import_run = relationship("StockCatalogImportRun")


class StockCatalogPriceHistory(Base):
    __tablename__ = "stock_catalog_price_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("stock_catalog_items.id", ondelete="CASCADE"), nullable=False, index=True)
    supplier_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("stock_catalog_suppliers.id", ondelete="CASCADE"), nullable=False, index=True)
    old_price: Mapped[Optional[float]] = mapped_column(Numeric(12, 4), nullable=True)
    new_price: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="MANUAL")  # MANUAL | IMPORT_XLSX
    source_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    changed_by_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    evidence_file_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("files.id", ondelete="SET NULL"), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    item: Mapped["StockCatalogItem"] = relationship("StockCatalogItem", back_populates="price_history")
    supplier: Mapped["StockCatalogSupplier"] = relationship("StockCatalogSupplier", back_populates="price_history")
    changed_by = relationship("User")


class StockCatalogCybersulProduct(Base):
    __tablename__ = "stock_catalog_cybersul_products"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cybersul_code: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    old_code: Mapped[Optional[str]] = mapped_column(String(100), index=True, nullable=True)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    normalized_description: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    complement: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    unit: Mapped[str] = mapped_column(String(30), default="un")
    balance_vesper: Mapped[float] = mapped_column(Numeric(12, 4), default=0.0)
    balance_ventrio: Mapped[float] = mapped_column(Numeric(12, 4), default=0.0)
    balance_total: Mapped[float] = mapped_column(Numeric(12, 4), default=0.0)
    cost_price: Mapped[Optional[float]] = mapped_column(Numeric(12, 4), nullable=True)
    supplier_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ncm: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    group_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    source_row: Mapped[int] = mapped_column(Integer, nullable=False)
    import_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("stock_catalog_import_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True
    )

    catalog_items: Mapped[List["StockCatalogItem"]] = relationship("StockCatalogItem", back_populates="cybersul_product")
    links: Mapped[List["StockCatalogLink"]] = relationship("StockCatalogLink", back_populates="cybersul_product", cascade="all, delete-orphan")


class StockCatalogLink(Base):
    __tablename__ = "stock_catalog_links"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stock_catalog_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("stock_catalog_items.id", ondelete="CASCADE"), nullable=False, index=True)
    cybersul_product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("stock_catalog_cybersul_products.id", ondelete="CASCADE"), nullable=False, index=True)
    match_type: Mapped[str] = mapped_column(String(50), nullable=False)  # EXACT | FUZZY | ALIAS | MANUAL
    confidence: Mapped[float] = mapped_column(Numeric(5, 4), default=1.0)
    match_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    approved_by_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    catalog_item: Mapped["StockCatalogItem"] = relationship("StockCatalogItem", back_populates="links")
    cybersul_product: Mapped["StockCatalogCybersulProduct"] = relationship("StockCatalogCybersulProduct", back_populates="links")
    approved_by = relationship("User")


class StockCatalogSearchIndex(Base):
    __tablename__ = "stock_catalog_search_index"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("stock_catalog_items.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    search_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_search_text: Mapped[str] = mapped_column(Text, nullable=False)
    tokens_json: Mapped[Optional[List[str]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True
    )
    supplier_names: Mapped[Optional[List[str]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True
    )
    cybersul_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    source_sheet: Mapped[str] = mapped_column(String(100), nullable=False)
    family_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    last_price: Mapped[Optional[float]] = mapped_column(Numeric(12, 4), nullable=True)
    last_supplier: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    item: Mapped["StockCatalogItem"] = relationship("StockCatalogItem", back_populates="search_indexes")


class StockCatalogReviewQueue(Base):
    __tablename__ = "stock_catalog_review_queue"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("stock_catalog_items.id", ondelete="CASCADE"), nullable=False, index=True)
    import_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("stock_catalog_import_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    review_type: Mapped[str] = mapped_column(String(50), nullable=False)  # AMBIGUOUS_VARIATION | MISSING_SUPPLIER | MISSING_EMAIL | DIVERGENT_PRICE | CYBERSUL_MATCH
    severity: Mapped[str] = mapped_column(String(30), default="MEDIUM")  # LOW | MEDIUM | HIGH | CRITICAL
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Text] = mapped_column(Text, nullable=False)
    raw_context_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(30), default="PENDING", index=True)  # PENDING | RESOLVED | IGNORED
    resolved_by_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    item: Mapped["StockCatalogItem"] = relationship("StockCatalogItem", back_populates="review_queue")
    import_run = relationship("StockCatalogImportRun")
    resolved_by = relationship("User")


class StockCatalogAlert(Base):
    __tablename__ = "stock_catalog_alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("stock_catalog_items.id", ondelete="CASCADE"), nullable=False, index=True)
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)  # LOW_STOCK | PRICE_SPIKE | SUPPLIER_INACTIVE
    severity: Mapped[str] = mapped_column(String(30), default="MEDIUM")  # INFO | MEDIUM | HIGH
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Text] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", index=True)  # ACTIVE | RESOLVED | ACKNOWLEDGED
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    item: Mapped["StockCatalogItem"] = relationship("StockCatalogItem", back_populates="alerts")
