import uuid
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# ---------------------------------------------------------------------------
# Endereços (PersonAddress)
# ---------------------------------------------------------------------------

class PersonAddressBase(BaseModel):
    type: str = Field("MAIN", description="Tipo do endereco: BILLING | SHIPPING | MAIN | OTHER")
    street: str = Field(..., max_length=255)
    number: str = Field(..., max_length=50)
    complement: Optional[str] = Field(None, max_length=255)
    district: str = Field(..., max_length=100)
    city: str = Field(..., max_length=100)
    state: str = Field(..., max_length=50)
    zip_code: str = Field(..., max_length=30)
    country: str = Field("Brasil", max_length=100)

class PersonAddressCreate(PersonAddressBase):
    pass

class PersonAddressUpdate(BaseModel):
    type: Optional[str] = None
    street: Optional[str] = None
    number: Optional[str] = None
    complement: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None

class PersonAddressRead(PersonAddressBase):
    id: uuid.UUID
    person_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Contatos (PersonContact)
# ---------------------------------------------------------------------------

class PersonContactBase(BaseModel):
    name: str = Field(..., max_length=255)
    role: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    whatsapp: Optional[str] = Field(None, max_length=50)
    is_primary: bool = False

class PersonContactCreate(PersonContactBase):
    pass

class PersonContactUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    whatsapp: Optional[str] = None
    is_primary: Optional[bool] = None

class PersonContactRead(PersonContactBase):
    id: uuid.UUID
    person_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Pessoas (Person)
# ---------------------------------------------------------------------------

class PersonBase(BaseModel):
    type: str = Field(..., description="INDIVIDUAL | COMPANY")
    name: str = Field(..., min_length=2, max_length=255)
    legal_name: Optional[str] = Field(None, max_length=255)
    document_type: Optional[str] = Field(None, description="CPF | CNPJ | OTHER")
    document_number: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None
    is_active: bool = True
    tenant_id: Optional[str] = Field(None, max_length=50)

class PersonCreate(PersonBase):
    addresses: List[PersonAddressCreate] = []
    contacts: List[PersonContactCreate] = []

class PersonUpdate(BaseModel):
    type: Optional[str] = None
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    legal_name: Optional[str] = None
    document_type: Optional[str] = None
    document_number: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None
    tenant_id: Optional[str] = None

class CustomerNestedRead(BaseModel):
    id: uuid.UUID
    customer_code: Optional[str] = None
    status: str
    default_payment_terms: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SupplierNestedRead(BaseModel):
    id: uuid.UUID
    supplier_code: Optional[str] = None
    categories: Optional[List[str]] = None
    preferred_contact_email: Optional[str] = None
    rating: Optional[float] = None
    status: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PersonRead(PersonBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    addresses: List[PersonAddressRead] = []
    contacts: List[PersonContactRead] = []
    customer: Optional[CustomerNestedRead] = None
    supplier: Optional[SupplierNestedRead] = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Clientes (Customer)
# ---------------------------------------------------------------------------

class CustomerBase(BaseModel):
    person_id: uuid.UUID
    customer_code: Optional[str] = Field(None, max_length=50)
    status: str = Field("ACTIVE", description="ACTIVE | INACTIVE | BLOCKED")
    default_payment_terms: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None

class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(BaseModel):
    customer_code: Optional[str] = None
    status: Optional[str] = None
    default_payment_terms: Optional[str] = None
    notes: Optional[str] = None

class CustomerRead(CustomerBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    person: PersonRead

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Fornecedores (Supplier)
# ---------------------------------------------------------------------------

class SupplierBase(BaseModel):
    person_id: uuid.UUID
    supplier_code: Optional[str] = Field(None, max_length=50)
    categories: Optional[List[str]] = None
    preferred_contact_email: Optional[str] = Field(None, max_length=255)
    rating: Optional[float] = Field(None, ge=0, le=5)
    status: str = Field("ACTIVE", description="ACTIVE | INACTIVE | BLOCKED")
    notes: Optional[str] = None

class SupplierCreate(SupplierBase):
    pass

class SupplierUpdate(BaseModel):
    supplier_code: Optional[str] = None
    categories: Optional[List[str]] = None
    preferred_contact_email: Optional[str] = None
    rating: Optional[float] = None
    status: Optional[str] = None
    notes: Optional[str] = None

class SupplierRead(SupplierBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    person: PersonRead

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Famílias de Produtos (ProductFamily)
# ---------------------------------------------------------------------------

class ProductFamilyBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None

class ProductFamilyCreate(ProductFamilyBase):
    pass

class ProductFamilyRead(ProductFamilyBase):
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Produtos / Itens (ProductItem)
# ---------------------------------------------------------------------------

class ProductItemBase(BaseModel):
    sku: str = Field(..., min_length=2, max_length=100)
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    item_type: str = Field(..., description="RAW_MATERIAL | FINISHED_GOOD | CONSUMABLE | SERVICE_ITEM | OTHER")
    unit_of_measure: str = Field("un", max_length=30)
    category: Optional[str] = Field(None, max_length=100)
    ncm: Optional[str] = Field(None, max_length=20)
    barcode: Optional[str] = Field(None, max_length=50)
    is_active: bool = True
    family_id: Optional[uuid.UUID] = None
    canonical_key: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None

class ProductItemCreate(ProductItemBase):
    pass

class ProductItemUpdate(BaseModel):
    sku: Optional[str] = Field(None, min_length=2, max_length=100)
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    item_type: Optional[str] = None
    unit_of_measure: Optional[str] = None
    category: Optional[str] = None
    ncm: Optional[str] = None
    barcode: Optional[str] = None
    is_active: Optional[bool] = None
    family_id: Optional[uuid.UUID] = None
    canonical_key: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None

class ProductItemRead(ProductItemBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    family: Optional[ProductFamilyRead] = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Fila de Deduplicação de Produtos (ProductDeduplicationQueue)
# ---------------------------------------------------------------------------

class ProductDeduplicationRead(BaseModel):
    id: uuid.UUID
    item_a_id: uuid.UUID
    item_b_id: uuid.UUID
    relation_type: str
    similarity_score: float
    status: str
    notes: Optional[str] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None
    resolved_by_user_id: Optional[int] = None
    item_a: Optional[ProductItemRead] = None
    item_b: Optional[ProductItemRead] = None

    model_config = ConfigDict(from_attributes=True)

class ProductDeduplicationResolve(BaseModel):
    decision: str = Field(..., description="APPROVED_MERGE | REJECTED | RESOLVED")
    notes: Optional[str] = None



# ---------------------------------------------------------------------------
# Serviços (Service)
# ---------------------------------------------------------------------------

class ServiceBase(BaseModel):
    code: str = Field(..., min_length=2, max_length=100)
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    default_price: Optional[float] = Field(None, ge=0)
    is_active: bool = True

class ServiceCreate(ServiceBase):
    pass

class ServiceUpdate(BaseModel):
    code: Optional[str] = Field(None, min_length=2, max_length=100)
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = None
    default_price: Optional[float] = None
    is_active: Optional[bool] = None

class ServiceRead(ServiceBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
