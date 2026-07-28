"""
Modelos do módulo de Compras do Portal Vesper.
Gerencia fornecedores, requisições de compra, cotações, RFQs e comparativos.
"""
import uuid
from sqlalchemy import (
    Integer, String, DateTime, ForeignKey, Text, Boolean, Numeric, JSON, UUID,
    UniqueConstraint,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from app.core.database import Base

# Importa de master_data para manter o cadastro mestre unificado
from app.models.master_data import Supplier, ProductItem, Service


# ---------------------------------------------------------------------------
# Requisição de Compra
# ---------------------------------------------------------------------------

class PurchaseRequest(Base):
    """
    Requisição de compra criada por um usuário.
    Status: DRAFT → REQUESTED → RFQ_PREPARING → RFQ_SENT → QUOTES_RECEIVED → COMPARING → APPROVAL_REQUIRED → APPROVED → REJECTED → CANCELLED
    """
    __tablename__ = "purchase_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    justification: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    requester_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(30), default="DRAFT", index=True, nullable=False
    )
    priority: Mapped[str] = mapped_column(
        String(20), default="NORMAL", nullable=False
    )  # LOW, NORMAL, HIGH, URGENT
    urgency: Mapped[str] = mapped_column(
        String(20), default="NORMAL", nullable=False
    )  # Para retrocompatibilidade com legados
    
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    estimated_total: Mapped[Optional[float]] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    approved_total: Mapped[Optional[float]] = mapped_column(
        Numeric(12, 2), nullable=True
    )

    needed_by: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    origin_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    origin_ref_id: Mapped[Optional[str]] = mapped_column(String(120), nullable=True, index=True)
    origin_snapshot_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True
    )

    # Vinculo com o módulo de aprovações
    approval_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("approvals.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Cotação vencedora selecionada (UUID)
    selected_quotation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relacionamentos
    requester = relationship("User", foreign_keys=[requester_user_id])
    approval = relationship("Approval", foreign_keys=[approval_id])
    items: Mapped[List["PurchaseRequestItem"]] = relationship(
        "PurchaseRequestItem", back_populates="purchase_request", cascade="all, delete-orphan"
    )
    quotations: Mapped[List["Quotation"]] = relationship(
        "Quotation", back_populates="purchase_request", cascade="all, delete-orphan"
    )
    rfqs: Mapped[List["PurchaseRFQ"]] = relationship(
        "PurchaseRFQ", back_populates="purchase_request", cascade="all, delete-orphan"
    )
    activities: Mapped[List["PurchaseActivity"]] = relationship(
        "PurchaseActivity", back_populates="purchase_request", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# Itens da Requisição
# ---------------------------------------------------------------------------

class PurchaseRequestItem(Base):
    """Item individual dentro de uma requisição de compra."""
    __tablename__ = "purchase_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    purchase_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_requests.id", ondelete="CASCADE"), index=True, nullable=False
    )
    
    # Links com cadastros mestres
    item_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_items.id", ondelete="SET NULL"), nullable=True
    )
    service_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("services.id", ondelete="SET NULL"), nullable=True
    )
    stock_catalog_item_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stock_catalog_items.id", ondelete="SET NULL"), nullable=True, index=True
    )
    free_text_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    quantity: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=1)
    unit_of_measure: Mapped[str] = mapped_column(String(30), default="un", nullable=False)
    specifications: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    estimated_unit_price: Mapped[Optional[float]] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    source_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    source_ref_id: Mapped[Optional[str]] = mapped_column(String(120), nullable=True, index=True)
    source_confidence: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    match_status: Mapped[str] = mapped_column(String(40), default="confirmed", nullable=False, index=True)
    source_snapshot_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True
    )

    # Novos campos de status e classificação por item
    normalized_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    destination: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    budget_limit: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    classification: Mapped[Optional[str]] = mapped_column(String(30), default="EXTERNAL", nullable=True) # INTERNAL, EXTERNAL, AMBIGUOUS
    classification_confidence: Mapped[Optional[float]] = mapped_column(Numeric(8, 4), nullable=True)
    selected_option_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approval_status: Mapped[str] = mapped_column(String(30), default="PENDING", nullable=False)
    purchasing_status: Mapped[str] = mapped_column(String(30), default="PENDING", nullable=False)
    delivery_status: Mapped[str] = mapped_column(String(30), default="PENDING", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relacionamentos
    purchase_request: Mapped["PurchaseRequest"] = relationship(
        "PurchaseRequest", back_populates="items"
    )
    product_item: Mapped[Optional["ProductItem"]] = relationship("ProductItem")
    service: Mapped[Optional["Service"]] = relationship("Service")
    stock_catalog_item: Mapped[Optional["StockCatalogItem"]] = relationship("StockCatalogItem")
    quotation_items: Mapped[List["QuotationItem"]] = relationship(
        "QuotationItem", back_populates="purchase_item", cascade="all, delete-orphan"
    )
    options: Mapped[List["PurchaseItemOption"]] = relationship(
        "PurchaseItemOption", back_populates="purchase_item", cascade="all, delete-orphan"
    )

    # Aliases de retrocompatibilidade para o compras antigo
    @property
    def description(self) -> str:
        return self.free_text_description or ""

    @property
    def unit(self) -> str:
        return self.unit_of_measure

    @property
    def notes(self) -> Optional[str]:
        return self.specifications


class PurchaseItemOption(Base):
    """
    Opção de fornecimento ou mercado externo capturada para um item de compra.
    """
    __tablename__ = "purchase_item_options"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    purchase_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_items.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # INTERNAL_SUPPLIER, EXTERNAL_MARKET, MANUAL_LINK, CART_IMPORT, MANUAL_ENTRY
    supplier_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    store_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    seller_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    brand: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    product_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    shipping_price: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    total_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    delivery_estimate: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    availability: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    rating: Mapped[Optional[float]] = mapped_column(Numeric(3, 2), nullable=True)
    review_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    specifications: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    raw_source_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True
    )
    status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)  # ex: PENDING, APPROVED, REJECTED
    selected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    search_session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_search_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    canonical_product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_canonical_products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    source_rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    compatibility_score: Mapped[Optional[float]] = mapped_column(Numeric(8, 4), nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Numeric(8, 4), nullable=True)
    evidence_level: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    shipping_destination: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    invoice_available: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    payment_summary: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    warranty_summary: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    captured_method: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    verification_status: Mapped[str] = mapped_column(String(40), default="DISCOVERED", nullable=False, index=True)
    verification_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relacionamentos
    purchase_item: Mapped["PurchaseRequestItem"] = relationship(
        "PurchaseRequestItem", back_populates="options"
    )
    supplier = relationship("Supplier")
    search_session: Mapped[Optional["PurchaseSearchSession"]] = relationship(
        "PurchaseSearchSession", back_populates="options"
    )
    canonical_product: Mapped[Optional["PurchaseCanonicalProduct"]] = relationship(
        "PurchaseCanonicalProduct", back_populates="options"
    )
    price_conditions: Mapped[List["PurchaseOfferPriceCondition"]] = relationship(
        "PurchaseOfferPriceCondition", back_populates="option", cascade="all, delete-orphan"
    )


class PurchaseSearchSession(Base):
    """Pesquisa progressiva e persistente para um item de compra."""
    __tablename__ = "purchase_search_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    purchase_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_requests.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    purchase_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_items.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    query: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[str] = mapped_column(String(80), default="general_external", index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="queued", index=True, nullable=False)
    progress_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_step: Mapped[str] = mapped_column(String(120), default="interpretando necessidade", nullable=False)
    destination: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    shipping_postal_code: Mapped[str] = mapped_column(String(20), default="21043-030", nullable=False)
    budget_limit: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    planner_summary: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True
    )
    recommendation_summary: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True
    )
    missing_questions: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    purchase_request: Mapped["PurchaseRequest"] = relationship("PurchaseRequest")
    purchase_item: Mapped["PurchaseRequestItem"] = relationship("PurchaseRequestItem")
    created_by = relationship("User")
    tasks: Mapped[List["PurchaseResearchTask"]] = relationship(
        "PurchaseResearchTask", back_populates="search_session", cascade="all, delete-orphan"
    )
    sources: Mapped[List["PurchaseSearchSource"]] = relationship(
        "PurchaseSearchSource", back_populates="search_session", cascade="all, delete-orphan"
    )
    canonical_products: Mapped[List["PurchaseCanonicalProduct"]] = relationship(
        "PurchaseCanonicalProduct", back_populates="search_session", cascade="all, delete-orphan"
    )
    options: Mapped[List["PurchaseItemOption"]] = relationship(
        "PurchaseItemOption", back_populates="search_session"
    )


class PurchaseResearchTask(Base):
    """Subtarefa planejada pelo motor de pesquisa de compras."""
    __tablename__ = "purchase_research_tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    search_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_search_sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    task_type: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    criteria: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(40), default="pending", index=True, nullable=False)
    result_summary: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    search_session: Mapped["PurchaseSearchSession"] = relationship(
        "PurchaseSearchSession", back_populates="tasks"
    )


class PurchaseSearchSource(Base):
    """Fonte consultada durante uma pesquisa de compras."""
    __tablename__ = "purchase_search_sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    search_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_search_sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    source_label: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="pending", index=True, nullable=False)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    result_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence_summary: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    search_session: Mapped["PurchaseSearchSession"] = relationship(
        "PurchaseSearchSession", back_populates="sources"
    )


class PurchaseCanonicalProduct(Base):
    """Produto canônico agrupando ofertas equivalentes."""
    __tablename__ = "purchase_canonical_products"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    search_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_search_sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    brand: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    normalized_key: Mapped[str] = mapped_column(String(300), index=True, nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    compatibility_score: Mapped[Optional[float]] = mapped_column(Numeric(8, 4), nullable=True)
    recommendation_label: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    risk_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    search_session: Mapped["PurchaseSearchSession"] = relationship(
        "PurchaseSearchSession", back_populates="canonical_products"
    )
    options: Mapped[List["PurchaseItemOption"]] = relationship(
        "PurchaseItemOption", back_populates="canonical_product"
    )


class PurchaseOfferFieldEvidence(Base):
    """Evidência por campo de uma oferta."""
    __tablename__ = "purchase_offer_field_evidence"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    option_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_item_options.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    search_session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_search_sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    field_name: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    field_status: Mapped[str] = mapped_column(String(40), default="unavailable", index=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    method: Mapped[str] = mapped_column(String(80), nullable=False)
    confidence: Mapped[Optional[float]] = mapped_column(Numeric(8, 4), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    snapshot_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    captured_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    option: Mapped["PurchaseItemOption"] = relationship("PurchaseItemOption")


# Mantém alias para compatibilidade com importações antigas
class PurchaseRequestIdempotencyKey(Base):
    """Controle de criacao idempotente para evitar compras duplicadas por timeout ou duplo clique."""
    __tablename__ = "purchase_request_idempotency_keys"
    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_purchase_request_idempotency_user_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    purchase_request_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_requests.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    payload_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="started", index=True, nullable=False)
    response_snapshot_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user = relationship("User")
    purchase_request: Mapped[Optional["PurchaseRequest"]] = relationship("PurchaseRequest")


class PurchaseInterpretedDraft(Base):
    """Rascunho de interpretacao revisavel antes de criar a compra definitiva."""
    __tablename__ = "purchase_interpreted_drafts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    raw_input: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="reviewing", index=True, nullable=False)
    analysis_summary: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    created_by = relationship("User")
    items: Mapped[List["PurchaseInterpretedDraftItem"]] = relationship(
        "PurchaseInterpretedDraftItem", back_populates="draft", cascade="all, delete-orphan"
    )


class PurchaseInterpretedDraftItem(Base):
    """Item interpretado dentro de um rascunho de nova compra."""
    __tablename__ = "purchase_interpreted_draft_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    draft_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_interpreted_drafts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    item_type: Mapped[str] = mapped_column(String(30), default="external", index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(10, 2), default=1, nullable=False)
    unit_of_measure: Mapped[str] = mapped_column(String(30), default="un", nullable=False)
    budget_limit: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    destination: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Numeric(8, 4), nullable=True)
    classification_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stock_catalog_item_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stock_catalog_items.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    missing_question_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True
    )
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    draft: Mapped["PurchaseInterpretedDraft"] = relationship("PurchaseInterpretedDraft", back_populates="items")
    stock_catalog_item: Mapped[Optional["StockCatalogItem"]] = relationship("StockCatalogItem")


class PurchaseResearchJob(Base):
    """Rastreamento persistente do job assincrono de pesquisa."""
    __tablename__ = "purchase_research_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    search_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_search_sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    queue_name: Mapped[str] = mapped_column(String(80), default="purchases_research", nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="queued", index=True, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    search_session: Mapped["PurchaseSearchSession"] = relationship("PurchaseSearchSession")


class PurchaseOfferPriceCondition(Base):
    """Condicoes de preco capturadas para uma oferta, como Pix, boleto ou parcelado."""
    __tablename__ = "purchase_offer_price_conditions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    option_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_item_options.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    condition_type: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="BRL", nullable=False)
    installments: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    installment_amount: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    discount_percent: Mapped[Optional[float]] = mapped_column(Numeric(8, 4), nullable=True)
    is_recommended: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source_label: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    evidence_status: Mapped[str] = mapped_column(String(40), default="estimated", nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    option: Mapped["PurchaseItemOption"] = relationship("PurchaseItemOption", back_populates="price_conditions")


PurchaseItem = PurchaseRequestItem


# ---------------------------------------------------------------------------
# Cotação de Fornecedor (Legado)
# ---------------------------------------------------------------------------

class Quotation(Base):
    """
    Cotação recebida de um fornecedor para uma requisição de compra (Legado).
    """
    __tablename__ = "quotations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    purchase_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_requests.id", ondelete="CASCADE"), index=True, nullable=False
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="CASCADE"), index=True, nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(20), default="PENDING", index=True, nullable=False
    )

    total_value: Mapped[Optional[float]] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    payment_terms: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    delivery_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    valid_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    registered_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relacionamentos
    purchase_request: Mapped["PurchaseRequest"] = relationship(
        "PurchaseRequest", back_populates="quotations"
    )
    supplier: Mapped["Supplier"] = relationship(
        "Supplier", back_populates="quotations"
    )
    registered_by = relationship("User", foreign_keys=[registered_by_user_id])
    items: Mapped[List["QuotationItem"]] = relationship(
        "QuotationItem", back_populates="quotation", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# Itens da Cotação (Legado)
# ---------------------------------------------------------------------------

class QuotationItem(Base):
    """Item individual dentro de uma cotação (Legado)."""
    __tablename__ = "quotation_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    quotation_id: Mapped[int] = mapped_column(
        ForeignKey("quotations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    purchase_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_items.id", ondelete="CASCADE"), index=True, nullable=False
    )

    quoted_unit_price: Mapped[float] = mapped_column(
        Numeric(12, 2), nullable=False
    )
    delivery_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # Relacionamentos
    quotation: Mapped["Quotation"] = relationship(
        "Quotation", back_populates="items"
    )
    purchase_item: Mapped["PurchaseRequestItem"] = relationship(
        "PurchaseRequestItem", back_populates="quotation_items"
    )


# ---------------------------------------------------------------------------
# Log de Atividades
# ---------------------------------------------------------------------------

class PurchaseActivity(Base):
    """Registro de atividades e eventos do módulo de Compras."""
    __tablename__ = "purchase_activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    purchase_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_requests.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    details: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )

    # Relacionamentos
    purchase_request: Mapped["PurchaseRequest"] = relationship(
        "PurchaseRequest", back_populates="activities"
    )
    user = relationship("User", foreign_keys=[user_id])


# ---------------------------------------------------------------------------
# RFQ Inteligente (PurchaseRFQ)
# ---------------------------------------------------------------------------

class PurchaseRFQ(Base):
    """
    Representa o processo de RFQ (Request for Quote) gerado a partir de uma requisição.
    """
    __tablename__ = "purchase_rfqs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    purchase_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_requests.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="DRAFT", index=True, nullable=False
    )  # DRAFT, READY_FOR_REVIEW, PENDING_APPROVAL, APPROVED_TO_SEND, SENT, RESPONSES_RECEIVED, CLOSED, CANCELLED
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    message_template: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relacionamentos
    purchase_request: Mapped["PurchaseRequest"] = relationship(
        "PurchaseRequest", back_populates="rfqs"
    )
    created_by = relationship("User")
    rfq_suppliers: Mapped[List["PurchaseRFQSupplier"]] = relationship(
        "PurchaseRFQSupplier", back_populates="rfq", cascade="all, delete-orphan"
    )
    comparison: Mapped[Optional["PurchaseComparison"]] = relationship(
        "PurchaseComparison", back_populates="rfq", uselist=False, cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# Fornecedores da RFQ (PurchaseRFQSupplier)
# ---------------------------------------------------------------------------

class PurchaseRFQSupplier(Base):
    """
    Associação de Fornecedores convidados a cotar em uma RFQ.
    """
    __tablename__ = "purchase_rfq_suppliers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    rfq_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_rfqs.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default="DRAFT", index=True, nullable=False
    )  # DRAFT, READY, SENT, RESPONDED, DECLINED, FAILED
    message_subject: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    message_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    response_received_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # Relacionamentos
    rfq: Mapped["PurchaseRFQ"] = relationship("PurchaseRFQ", back_populates="rfq_suppliers")
    supplier: Mapped["Supplier"] = relationship("Supplier")
    quote_responses: Mapped[List["PurchaseQuoteResponse"]] = relationship(
        "PurchaseQuoteResponse", back_populates="rfq_supplier", cascade="all, delete-orphan"
    )
    item_links: Mapped[List["PurchaseRFQSupplierItem"]] = relationship(
        "PurchaseRFQSupplierItem", back_populates="rfq_supplier", cascade="all, delete-orphan"
    )


class PurchaseRFQSupplierItem(Base):
    """Distribuicao de quais itens da cotacao cada fornecedor recebera."""
    __tablename__ = "purchase_rfq_supplier_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    rfq_supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_rfq_suppliers.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    purchase_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_items.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    rfq_supplier: Mapped["PurchaseRFQSupplier"] = relationship(
        "PurchaseRFQSupplier", back_populates="item_links"
    )
    purchase_item: Mapped["PurchaseRequestItem"] = relationship("PurchaseRequestItem")


# ---------------------------------------------------------------------------
# Resposta de Cotação de Fornecedor (PurchaseQuoteResponse)
# ---------------------------------------------------------------------------

class PurchaseSenderAccount(Base):
    """Conta remetente permitida para cotacoes de Compras."""
    __tablename__ = "purchase_sender_accounts"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    company: Mapped[str] = mapped_column(String(80), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="not_configured", index=True, nullable=False)
    bcc_default_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    default_bcc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    smtp_config_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True
    )
    imap_config_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True
    )
    secret_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    has_secret: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    permissions_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True
    )
    sent_folder: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    monitored_folder: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_test_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    signatures: Mapped[List["PurchaseSenderSignature"]] = relationship(
        "PurchaseSenderSignature", back_populates="account", cascade="all, delete-orphan"
    )
    email_messages: Mapped[List["PurchaseEmailMessage"]] = relationship(
        "PurchaseEmailMessage", back_populates="sender_account"
    )


class PurchaseSenderSignature(Base):
    """Assinatura HTML/texto versionada por conta remetente."""
    __tablename__ = "purchase_sender_signatures"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[str] = mapped_column(
        String(80),
        ForeignKey("purchase_sender_accounts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    signature_name: Mapped[str] = mapped_column(String(120), nullable=False)
    html_content: Mapped[str] = mapped_column(Text, nullable=False)
    text_content: Mapped[str] = mapped_column(Text, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    account: Mapped["PurchaseSenderAccount"] = relationship(
        "PurchaseSenderAccount", back_populates="signatures"
    )
    updated_by_user = relationship("User", foreign_keys=[updated_by])


class PurchaseEmailMessage(Base):
    """Mensagem de e-mail persistida antes de envio para fornecedor."""
    __tablename__ = "purchase_email_messages"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_purchase_email_messages_idempotency_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quote_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_rfqs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    rfq_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    rfq_supplier_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_rfq_suppliers.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    supplier_contact_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    sender_account_id: Mapped[str] = mapped_column(
        String(80),
        ForeignKey("purchase_sender_accounts.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    from_email: Mapped[str] = mapped_column(String(255), nullable=False)
    from_name: Mapped[str] = mapped_column(String(255), nullable=False)
    to_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    cc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bcc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bcc_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    bcc_source: Mapped[str] = mapped_column(String(40), default="account_default", nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body_html: Mapped[str] = mapped_column(Text, nullable=False)
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    signature_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft", index=True, nullable=False)
    environment: Mapped[str] = mapped_column(String(40), default="development", index=True, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    message_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    provider_message_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    smtp_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    prepared_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    failed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    quote: Mapped["PurchaseRFQ"] = relationship("PurchaseRFQ")
    rfq_supplier: Mapped[Optional["PurchaseRFQSupplier"]] = relationship("PurchaseRFQSupplier")
    supplier: Mapped["Supplier"] = relationship("Supplier")
    sender_account: Mapped["PurchaseSenderAccount"] = relationship(
        "PurchaseSenderAccount", back_populates="email_messages"
    )
    created_by_user = relationship("User", foreign_keys=[created_by])
    updated_by_user = relationship("User", foreign_keys=[updated_by])


class PurchaseMonitoredAccount(Base):
    """Conta de e-mail monitorada para respostas de cotacao."""
    __tablename__ = "purchase_monitored_accounts"
    __table_args__ = (
        UniqueConstraint("account_email", "folder", name="uq_purchase_monitored_account_folder"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sender_account_id: Mapped[Optional[str]] = mapped_column(
        String(80),
        ForeignKey("purchase_sender_accounts.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    account_email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(40), default="imap", nullable=False)
    folder: Mapped[str] = mapped_column(String(255), default="INBOX", nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="not_configured", index=True, nullable=False)
    imap_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    secret_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    has_secret: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_success_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_error_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    sender_account: Mapped[Optional["PurchaseSenderAccount"]] = relationship("PurchaseSenderAccount")
    inbound_messages: Mapped[List["PurchaseEmailInboundMessage"]] = relationship(
        "PurchaseEmailInboundMessage", back_populates="monitored_account", cascade="all, delete-orphan"
    )


class PurchaseEmailInboundMessage(Base):
    """Mensagem recebida pelo monitoramento IMAP/n8n de Compras."""
    __tablename__ = "purchase_email_inbound_messages"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_purchase_inbound_messages_idempotency_key"),
        UniqueConstraint("account_email", "folder", "imap_uid", name="uq_purchase_inbound_messages_imap_uid"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    monitored_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_monitored_accounts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    account_email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    folder: Mapped[str] = mapped_column(String(255), default="INBOX", nullable=False)
    imap_uid: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    message_id: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    in_reply_to: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    references_json: Mapped[Optional[List[str]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True
    )
    from_email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    from_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    to_json: Mapped[Optional[List[str]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True
    )
    cc_json: Mapped[Optional[List[str]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True
    )
    subject: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    normalized_subject: Mapped[Optional[str]] = mapped_column(String(500), index=True, nullable=True)
    body_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    body_html_sanitized: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_headers_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True
    )
    received_at: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="received", index=True, nullable=False)
    classification_status: Mapped[str] = mapped_column(String(60), default="pending", index=True, nullable=False)
    linked_quote_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_rfqs.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    linked_supplier_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    confidence_score: Mapped[Optional[float]] = mapped_column(Numeric(8, 4), nullable=True)
    confidence_level: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    monitored_account: Mapped["PurchaseMonitoredAccount"] = relationship(
        "PurchaseMonitoredAccount", back_populates="inbound_messages"
    )
    linked_quote: Mapped[Optional["PurchaseRFQ"]] = relationship("PurchaseRFQ")
    linked_supplier: Mapped[Optional["Supplier"]] = relationship("Supplier")
    attachments: Mapped[List["PurchaseEmailAttachment"]] = relationship(
        "PurchaseEmailAttachment", back_populates="inbound_message", cascade="all, delete-orphan"
    )
    response_candidates: Mapped[List["PurchaseResponseCandidate"]] = relationship(
        "PurchaseResponseCandidate", back_populates="inbound_message", cascade="all, delete-orphan"
    )


class PurchaseEmailAttachment(Base):
    """Anexo recebido por e-mail, armazenado como metadado seguro."""
    __tablename__ = "purchase_email_attachments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inbound_message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_email_inbound_messages.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    filename: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    safe_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    detected_content_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sha256: Mapped[Optional[str]] = mapped_column(String(128), index=True, nullable=True)
    storage_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    scan_status: Mapped[str] = mapped_column(String(40), default="pending", index=True, nullable=False)
    blocked_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    text_preview: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    inbound_message: Mapped["PurchaseEmailInboundMessage"] = relationship(
        "PurchaseEmailInboundMessage", back_populates="attachments"
    )


class PurchaseResponseCandidate(Base):
    """Possivel vinculo entre uma mensagem recebida e uma cotacao."""
    __tablename__ = "purchase_response_candidates"
    __table_args__ = (
        UniqueConstraint("inbound_message_id", "quote_id", "supplier_id", name="uq_purchase_response_candidate_match"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inbound_message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_email_inbound_messages.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    quote_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_rfqs.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    rfq_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), index=True, nullable=True)
    supplier_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    candidate_status: Mapped[str] = mapped_column(String(50), default="needs_review", index=True, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Numeric(8, 4), default=0, nullable=False)
    confidence_level: Mapped[str] = mapped_column(String(20), default="low", index=True, nullable=False)
    match_reasons_json: Mapped[Optional[List[str]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True
    )
    risk_flags_json: Mapped[Optional[List[str]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True
    )
    user_decision: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    decided_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    inbound_message: Mapped["PurchaseEmailInboundMessage"] = relationship(
        "PurchaseEmailInboundMessage", back_populates="response_candidates"
    )
    quote: Mapped[Optional["PurchaseRFQ"]] = relationship("PurchaseRFQ")
    supplier: Mapped[Optional["Supplier"]] = relationship("Supplier")
    decided_by_user = relationship("User", foreign_keys=[decided_by])


class PurchaseMonitoringEvent(Base):
    """Evento auditavel recebido pelo gateway de monitoramento de Compras."""
    __tablename__ = "purchase_monitoring_events"
    __table_args__ = (
        UniqueConstraint("webhook_id", name="uq_purchase_monitoring_events_webhook_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    account_email: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(80), index=True, nullable=True)
    webhook_id: Mapped[str] = mapped_column(String(160), nullable=False)
    payload_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="received", index=True, nullable=False)
    error_code: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    inbound_message_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_email_inbound_messages.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True, nullable=False
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    inbound_message: Mapped[Optional["PurchaseEmailInboundMessage"]] = relationship("PurchaseEmailInboundMessage")


class PurchaseResponseExtraction(Base):
    """Rodada de extracao assistida sobre uma resposta recebida."""
    __tablename__ = "purchase_response_extractions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_response_candidates.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    inbound_message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_email_inbound_messages.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    quote_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_rfqs.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    supplier_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(50), default="needs_review", index=True, nullable=False)
    extractor_version: Mapped[str] = mapped_column(String(40), default="deterministic-v1", nullable=False)
    confidence_summary: Mapped[str] = mapped_column(String(20), default="check", nullable=False)
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    candidate: Mapped["PurchaseResponseCandidate"] = relationship("PurchaseResponseCandidate")
    inbound_message: Mapped["PurchaseEmailInboundMessage"] = relationship("PurchaseEmailInboundMessage")
    quote: Mapped[Optional["PurchaseRFQ"]] = relationship("PurchaseRFQ")
    supplier: Mapped[Optional["Supplier"]] = relationship("Supplier")
    fields: Mapped[List["PurchaseResponseExtractedField"]] = relationship(
        "PurchaseResponseExtractedField", back_populates="extraction", cascade="all, delete-orphan"
    )
    evidences: Mapped[List["PurchaseResponseEvidence"]] = relationship(
        "PurchaseResponseEvidence", back_populates="extraction", cascade="all, delete-orphan"
    )
    decisions: Mapped[List["PurchaseResponseReviewDecision"]] = relationship(
        "PurchaseResponseReviewDecision", back_populates="extraction", cascade="all, delete-orphan"
    )


class PurchaseResponseExtractedField(Base):
    """Campo sugerido pela extracao assistida."""
    __tablename__ = "purchase_response_extracted_fields"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    extraction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_response_extractions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    field_name: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    raw_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    normalized_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    value_type: Mapped[str] = mapped_column(String(40), default="text", nullable=False)
    confidence_level: Mapped[str] = mapped_column(String(20), default="check", index=True, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Numeric(8, 4), default=0, nullable=False)
    review_status: Mapped[str] = mapped_column(String(40), default="pending", index=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), default="email_body", nullable=False)
    source_label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    extraction: Mapped["PurchaseResponseExtraction"] = relationship(
        "PurchaseResponseExtraction", back_populates="fields"
    )
    evidences: Mapped[List["PurchaseResponseEvidence"]] = relationship(
        "PurchaseResponseEvidence", back_populates="field", cascade="all, delete-orphan"
    )


class PurchaseResponseEvidence(Base):
    """Evidencia exata que originou um campo extraido."""
    __tablename__ = "purchase_response_evidences"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    extraction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_response_extractions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    field_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_response_extracted_fields.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    attachment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_email_attachments.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source_label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    snippet: Mapped[str] = mapped_column(Text, nullable=False)
    char_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    char_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    row_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    confidence_level: Mapped[str] = mapped_column(String(20), default="check", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    extraction: Mapped["PurchaseResponseExtraction"] = relationship(
        "PurchaseResponseExtraction", back_populates="evidences"
    )
    field: Mapped[Optional["PurchaseResponseExtractedField"]] = relationship(
        "PurchaseResponseExtractedField", back_populates="evidences"
    )
    attachment: Mapped[Optional["PurchaseEmailAttachment"]] = relationship("PurchaseEmailAttachment")


class PurchaseResponseReviewDecision(Base):
    """Decisao humana sobre campo extraido."""
    __tablename__ = "purchase_response_review_decisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    extraction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_response_extractions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    field_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_response_extracted_fields.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    decision: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    previous_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewer_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True, nullable=False
    )

    extraction: Mapped["PurchaseResponseExtraction"] = relationship(
        "PurchaseResponseExtraction", back_populates="decisions"
    )
    field: Mapped[Optional["PurchaseResponseExtractedField"]] = relationship("PurchaseResponseExtractedField")
    reviewer = relationship("User", foreign_keys=[reviewer_user_id])


class PurchaseQuoteResponse(Base):
    """
    Proposta/Cotação recebida de um fornecedor para a RFQ.
    """
    __tablename__ = "purchase_quote_responses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    rfq_supplier_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_rfq_suppliers.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    total_amount: Mapped[Optional[float]] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    currency: Mapped[str] = mapped_column(String(10), default="BRL", nullable=False)
    delivery_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    payment_terms: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    validity_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attachment_file_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    parsed_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(50), default="RECEIVED", index=True, nullable=False
    )  # RECEIVED, PARSED, NEEDS_REVIEW, ACCEPTED, REJECTED

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # Relacionamentos
    rfq_supplier: Mapped[Optional["PurchaseRFQSupplier"]] = relationship(
        "PurchaseRFQSupplier", back_populates="quote_responses"
    )
    supplier: Mapped["Supplier"] = relationship("Supplier")
    lines: Mapped[List["PurchaseQuoteLine"]] = relationship(
        "PurchaseQuoteLine", back_populates="quote_response", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# Linha de Resposta de Cotação (PurchaseQuoteLine)
# ---------------------------------------------------------------------------

class PurchaseQuoteLine(Base):
    """
    Linha individual da proposta detalhando valor por item solicitado.
    """
    __tablename__ = "purchase_quote_lines"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    quote_response_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_quote_responses.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    request_item_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_items.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    total_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    delivery_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relacionamentos
    quote_response: Mapped["PurchaseQuoteResponse"] = relationship("PurchaseQuoteResponse", back_populates="lines")
    request_item: Mapped[Optional["PurchaseRequestItem"]] = relationship("PurchaseRequestItem")


# ---------------------------------------------------------------------------
# Análise Comparativa (PurchaseComparison)
# ---------------------------------------------------------------------------

class PurchaseComparison(Base):
    """
    Relatório comparativo de preços/prazos gerado pela API para apoiar decisão.
    """
    __tablename__ = "purchase_comparisons"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    rfq_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_rfqs.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False
    )
    best_supplier_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="SET NULL"),
        nullable=True
    )
    recommendation_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # Relacionamentos
    rfq: Mapped["PurchaseRFQ"] = relationship("PurchaseRFQ", back_populates="comparison")
    best_supplier: Mapped[Optional["Supplier"]] = relationship("Supplier")


# ---------------------------------------------------------------------------
# Rastreabilidade de Preços de Compra (Price Traceability)
# ---------------------------------------------------------------------------

class PurchasePriceEvidence(Base):
    """
    Representa o documento/comprovante de faturamento ou cotação como origem do valor.
    """
    __tablename__ = "purchase_price_evidences"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # BOLETO, NF, RFQ_RESPONSE, EMAIL, MANUAL_ENTRY, IMPORTED_XLSX, CYBERSUL
    
    supplier_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    product_item_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_items.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    service_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("services.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    document_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    document_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    unit_price: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    quantity: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    total_amount: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="BRL", nullable=False)
    unit_of_measure: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    payment_terms: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    file_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    raw_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
    tenant_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Relacionamentos
    supplier: Mapped[Optional["Supplier"]] = relationship("Supplier")
    product_item: Mapped[Optional["ProductItem"]] = relationship("ProductItem")
    service: Mapped[Optional["Service"]] = relationship("Service")
    created_by = relationship("User")


class PurchasePriceHistory(Base):
    """
    Log cronológico imutável de todos os preços de compra observados para itens e serviços.
    """
    __tablename__ = "purchase_price_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    product_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_items.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    supplier_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="SET NULL"),
        index=True,
        nullable=True
    )
    evidence_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_price_evidences.id", ondelete="SET NULL"),
        index=True,
        nullable=True
    )
    rfq_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_rfqs.id", ondelete="SET NULL"),
        index=True,
        nullable=True
    )
    quote_response_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_quote_responses.id", ondelete="SET NULL"),
        index=True,
        nullable=True
    )

    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    quantity: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    total_amount: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="BRL", nullable=False)
    unit_of_measure: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    
    observed_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    created_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
    
    invalidated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    invalidated_by_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    invalidation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Relacionamentos
    product_item: Mapped["ProductItem"] = relationship("ProductItem")
    supplier: Mapped[Optional["Supplier"]] = relationship("Supplier")
    evidence: Mapped[Optional["PurchasePriceEvidence"]] = relationship("PurchasePriceEvidence")
    rfq: Mapped[Optional["PurchaseRFQ"]] = relationship("PurchaseRFQ")
    quote_response: Mapped[Optional["PurchaseQuoteResponse"]] = relationship("PurchaseQuoteResponse")
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    invalidated_by = relationship("User", foreign_keys=[invalidated_by_user_id])


class PurchasePriceReference(Base):
    """
    Preço de referência oficial atual e ativo para estimativas de custos de compras.
    """
    __tablename__ = "purchase_price_references"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    product_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_items.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    supplier_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="SET NULL"),
        index=True,
        nullable=True
    )

    current_unit_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="BRL", nullable=False)
    unit_of_measure: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    
    source_history_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_price_history.id", ondelete="SET NULL"),
        nullable=True
    )
    source_evidence_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_price_evidences.id", ondelete="SET NULL"),
        nullable=True
    )

    approved_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    approved_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    tenant_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Relacionamentos
    product_item: Mapped["ProductItem"] = relationship("ProductItem")
    supplier: Mapped[Optional["Supplier"]] = relationship("Supplier")
    source_history: Mapped[Optional["PurchasePriceHistory"]] = relationship("PurchasePriceHistory")
    source_evidence: Mapped[Optional["PurchasePriceEvidence"]] = relationship("PurchasePriceEvidence")
    approved_by = relationship("User")


class PurchasePriceUpdateSuggestion(Base):
    """
    Fila de sugestões geradas automaticamente ao detectar variações de preços para aprovação.
    """
    __tablename__ = "purchase_price_update_suggestions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    product_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_items.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    supplier_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="SET NULL"),
        index=True,
        nullable=True
    )
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_price_evidences.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    history_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_price_history.id", ondelete="SET NULL"),
        index=True,
        nullable=True
    )
    reference_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_price_references.id", ondelete="SET NULL"),
        index=True,
        nullable=True
    )

    old_unit_price: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    new_unit_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    pct_variation: Mapped[Optional[float]] = mapped_column(Numeric(8, 4), nullable=True)
    variation_direction: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # INCREASE, DECREASE, SAME, NEW_REFERENCE
    status: Mapped[str] = mapped_column(
        String(30), default="PENDING", index=True, nullable=False
    )  # PENDING, APPROVED, REJECTED, CANCELLED
    
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    reviewed_by_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
    tenant_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Relacionamentos
    product_item: Mapped["ProductItem"] = relationship("ProductItem")
    supplier: Mapped[Optional["Supplier"]] = relationship("Supplier")
    evidence: Mapped["PurchasePriceEvidence"] = relationship("PurchasePriceEvidence")
    history: Mapped[Optional["PurchasePriceHistory"]] = relationship("PurchasePriceHistory")
    reference: Mapped[Optional["PurchasePriceReference"]] = relationship("PurchasePriceReference")
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_user_id])


class PurchaseXlsxImportRun(Base):
    """
    Controle auditavel de cada sincronizacao read-only da planilha de compras.
    A planilha continua sendo origem de atualizacao; o Portal usa o snapshot.
    """
    __tablename__ = "purchase_xlsx_import_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_modified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    file_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="running", index=True, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    metrics: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        nullable=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_by = relationship("User")


class PurchaseXlsxCatalogRow(Base):
    """
    Linha normalizada da leitura por bloco da planilha.
    Linhas soltas de titulo/contato/peso nao viram produto: enriquecem este snapshot.
    """
    __tablename__ = "purchase_xlsx_catalog_rows"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    import_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_xlsx_import_runs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    row_key: Mapped[str] = mapped_column(String(300), unique=True, index=True, nullable=False)
    sheet: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    parser_type: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    family: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    subfamily: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    group_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    variation: Mapped[str] = mapped_column(String(500), index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(500), nullable=False)
    original_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    code: Mapped[Optional[str]] = mapped_column(String(120), index=True, nullable=True)
    manufacturer: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    manufacturer_code: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    product_item_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_items.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    current_supplier_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    current_price: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    raw_price: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    final_value: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    price_type: Mapped[str] = mapped_column(String(50), default="nao_identificado", nullable=False)
    unit: Mapped[str] = mapped_column(String(30), default="un", nullable=False)
    source_updated_at: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    situation: Mapped[str] = mapped_column(String(80), default="Pronto", index=True, nullable=False)
    issues: Mapped[Optional[List[str]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        nullable=True,
    )
    attributes: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        nullable=True,
    )
    technical_details: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        nullable=True,
    )
    search_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )

    import_run = relationship("PurchaseXlsxImportRun")
    product_item = relationship("ProductItem")
    current_supplier = relationship("Supplier")


class PurchaseSupplierPriceOffer(Base):
    """
    Oferta/preco observado por fornecedor para uma variacao compravel.
    O fornecedor nunca vira produto; varias ofertas podem apontar para o mesmo ProductItem.
    """
    __tablename__ = "purchase_supplier_price_offers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    catalog_row_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_xlsx_catalog_rows.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    product_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_items.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    supplier_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    supplier_name_snapshot: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    raw_price: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    ipi: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    adjustment: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    final_value: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="BRL", nullable=False)
    unit: Mapped[str] = mapped_column(String(30), default="un", nullable=False)
    observed_at: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    source_row_key: Mapped[Optional[str]] = mapped_column(String(300), index=True, nullable=True)
    is_current_supplier: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    is_consolidated: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="Pronto", index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    catalog_row = relationship("PurchaseXlsxCatalogRow")
    product_item = relationship("ProductItem")
    supplier = relationship("Supplier")


class PurchaseCatalogSearchIndex(Base):
    """
    Texto normalizado e aliases para busca rapida do catalogo operacional.
    """
    __tablename__ = "purchase_catalog_search_index"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    product_item_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_items.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    family_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_families.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    catalog_row_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_xlsx_catalog_rows.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    category: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    family: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    variation: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    supplier_names: Mapped[Optional[List[str]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        nullable=True,
    )
    search_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_search_text: Mapped[str] = mapped_column(Text, nullable=False)
    rank_hint: Mapped[int] = mapped_column(Integer, default=0, index=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    product_item = relationship("ProductItem")
    family_ref = relationship("ProductFamily")
    catalog_row = relationship("PurchaseXlsxCatalogRow")
