import uuid
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, Numeric, JSON, UUID
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from app.core.database import Base

class Person(Base):
    """Cadastro central de pessoas físicas e jurídicas do Portal Vesper."""
    __tablename__ = "people"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # INDIVIDUAL | COMPANY
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    legal_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    document_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # CPF | CNPJ | OTHER
    document_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, unique=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    tenant_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relacionamentos de papéis (1-para-1)
    customer: Mapped[Optional["Customer"]] = relationship(
        "Customer",
        back_populates="person",
        uselist=False,
        cascade="all, delete-orphan"
    )
    supplier: Mapped[Optional["Supplier"]] = relationship(
        "Supplier",
        back_populates="person",
        uselist=False,
        cascade="all, delete-orphan"
    )

    # Relacionamentos múltiplos (1-para-N)
    addresses: Mapped[List["PersonAddress"]] = relationship(
        "PersonAddress",
        back_populates="person",
        cascade="all, delete-orphan"
    )
    contacts: Mapped[List["PersonContact"]] = relationship(
        "PersonContact",
        back_populates="person",
        cascade="all, delete-orphan"
    )


class Customer(Base):
    """Papel de Cliente vinculado a uma Pessoa no Portal Vesper."""
    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("people.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False
    )
    customer_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE", index=True)  # ACTIVE | INACTIVE | BLOCKED
    default_payment_terms: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relacionamento de volta para Pessoa
    person: Mapped["Person"] = relationship("Person", back_populates="customer")


class Supplier(Base):
    """Papel de Fornecedor vinculado a uma Pessoa no Portal Vesper."""
    __tablename__ = "suppliers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("people.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False
    )
    supplier_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, unique=True, index=True)
    categories: Mapped[Optional[List[str]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        nullable=True
    )
    preferred_contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    rating: Mapped[Optional[float]] = mapped_column(Numeric(3, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE", index=True)  # ACTIVE | INACTIVE | BLOCKED
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relacionamentos
    person: Mapped["Person"] = relationship("Person", back_populates="supplier")
    quotations: Mapped[List["Quotation"]] = relationship(
        "Quotation",
        back_populates="supplier",
        cascade="all, delete-orphan"
    )

    # Propriedades de compatibilidade para o módulo de Compras antigo
    @property
    def company_name(self) -> str:
        return self.person.name if self.person else ""

    @property
    def trade_name(self) -> Optional[str]:
        return self.person.legal_name if self.person else None

    @property
    def cnpj(self) -> Optional[str]:
        return self.person.document_number if self.person else None

    @property
    def contact_name(self) -> Optional[str]:
        return self.person.contacts[0].name if self.person and self.person.contacts else None

    @property
    def email(self) -> Optional[str]:
        return self.person.email if self.person else None

    @property
    def phone(self) -> Optional[str]:
        return self.person.phone if self.person else None

    @property
    def address(self) -> Optional[str]:
        if self.person and self.person.addresses:
            addr = self.person.addresses[0]
            comp = f" - {addr.complement}" if addr.complement else ""
            return f"{addr.street}, {addr.number}{comp}, {addr.district}, {addr.city}/{addr.state}"
        return None

    @property
    def category(self) -> Optional[str]:
        return self.categories[0] if self.categories else None

    @property
    def is_active(self) -> bool:
        return self.status == "ACTIVE"


class ProductFamily(Base):
    """Família de produtos que agrupa variações e itens compráveis parecidos."""
    __tablename__ = "product_families"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )

    products: Mapped[List["ProductItem"]] = relationship(
        "ProductItem", back_populates="family", cascade="all, delete-orphan"
    )


class ProductItem(Base):
    """Cadastro central único de insumos, materiais e produtos acabados."""
    __tablename__ = "product_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    sku: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    item_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )  # RAW_MATERIAL | FINISHED_GOOD | CONSUMABLE | SERVICE_ITEM | OTHER
    unit_of_measure: Mapped[str] = mapped_column(String(30), default="un", nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ncm: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    barcode: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    # Novas colunas para suportar famílias de produtos e chaves canônicas com atributos
    family_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_families.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    canonical_key: Mapped[Optional[str]] = mapped_column(
        String(500), unique=True, index=True, nullable=True
    )
    attributes: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relacionamento de volta para Família
    family: Mapped[Optional["ProductFamily"]] = relationship(
        "ProductFamily", back_populates="products"
    )



class Service(Base):
    """Cadastro de serviços faturáveis ou subcontratados."""
    __tablename__ = "services"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    default_price: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class PersonAddress(Base):
    """Endereços múltiplos associados a uma Pessoa."""
    __tablename__ = "person_addresses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("people.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    type: Mapped[str] = mapped_column(String(50), default="MAIN")  # BILLING | SHIPPING | MAIN | OTHER
    street: Mapped[str] = mapped_column(String(255), nullable=False)
    number: Mapped[str] = mapped_column(String(50), nullable=False)
    complement: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    district: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(50), nullable=False)
    zip_code: Mapped[str] = mapped_column(String(30), nullable=False)
    country: Mapped[str] = mapped_column(String(100), default="Brasil")

    # Relacionamento de volta para Pessoa
    person: Mapped["Person"] = relationship("Person", back_populates="addresses")


class PersonContact(Base):
    """Contatos telefônicos e eletrônicos associados a uma Pessoa."""
    __tablename__ = "person_contacts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("people.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    whatsapp: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relacionamento de volta para Pessoa
    person: Mapped["Person"] = relationship("Person", back_populates="contacts")


class ProductDeduplicationQueue(Base):
    """Fila de deduplicação e revisão de possíveis duplicados ou variações suspeitas no catálogo."""
    __tablename__ = "product_deduplication_queue"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    item_a_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    item_b_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    relation_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # POSSIBLE_DUPLICATE | SAME_VARIANT | SAME_FAMILY_DIFF_VARIANT | NEEDS_REVISION
    similarity_score: Mapped[float] = mapped_column(
        Numeric(5, 4), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(30), default="PENDING", index=True, nullable=False
    )  # PENDING | APPROVED_MERGE | REJECTED | RESOLVED
    
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    resolved_by_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relacionamentos
    item_a: Mapped["ProductItem"] = relationship("ProductItem", foreign_keys=[item_a_id])
    item_b: Mapped["ProductItem"] = relationship("ProductItem", foreign_keys=[item_b_id])
    resolved_by = relationship("User", foreign_keys=[resolved_by_user_id])

