import uuid
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import get_current_user
from app.models.user import User
from app.modules.master_data.service import MasterDataService
from app.modules.master_data.schemas import (
    PersonCreate, PersonUpdate, PersonRead,
    CustomerCreate, CustomerUpdate, CustomerRead,
    SupplierCreate, SupplierUpdate, SupplierRead,
    ProductItemCreate, ProductItemUpdate, ProductItemRead,
    ServiceCreate, ServiceUpdate, ServiceRead,
    ProductFamilyRead, ProductDeduplicationRead, ProductDeduplicationResolve
)

router = APIRouter()

# Dependência auxiliar para restringir gravação a administradores ou gerentes
def require_admin_or_manager(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.role or current_user.role.name not in ("ADMIN", "MANAGER"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Recurso restrito a administradores ou gerentes."
        )
    return current_user


# ---------------------------------------------------------------------------
# Pessoas (People)
# ---------------------------------------------------------------------------

@router.get("/people", response_model=List[PersonRead])
def list_people(
    search: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retorna a lista de pessoas cadastradas."""
    return MasterDataService.list_people(db, search, type, is_active, limit, offset)


@router.get("/people/{id}", response_model=PersonRead)
def get_person(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Busca detalhes de uma pessoa pelo ID."""
    return MasterDataService.get_person(db, id)


@router.post("/people", response_model=PersonRead, status_code=status.HTTP_201_CREATED)
def create_person(
    payload: PersonCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """Cadastra uma nova pessoa. Restrito a ADMIN/MANAGER."""
    return MasterDataService.create_person(db, payload, current_user)


@router.patch("/people/{id}", response_model=PersonRead)
def update_person(
    id: uuid.UUID,
    payload: PersonUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """Atualiza os dados de uma pessoa. Restrito a ADMIN/MANAGER."""
    return MasterDataService.update_person(db, id, payload, current_user)


# ---------------------------------------------------------------------------
# Clientes (Customers)
# ---------------------------------------------------------------------------

@router.get("/customers", response_model=List[CustomerRead])
def list_customers(
    search: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retorna a lista de clientes cadastrados."""
    return MasterDataService.list_customers(db, search, status_filter, limit, offset)


@router.get("/customers/{id}", response_model=CustomerRead)
def get_customer(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Busca detalhes de um cliente pelo ID."""
    return MasterDataService.get_customer(db, id)


@router.post("/customers", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
def create_customer(
    payload: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """Cadastra um novo cliente vinculado a uma Pessoa. Restrito a ADMIN/MANAGER."""
    return MasterDataService.create_customer(db, payload, current_user)


@router.patch("/customers/{id}", response_model=CustomerRead)
def update_customer(
    id: uuid.UUID,
    payload: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """Atualiza as informações de um cliente. Restrito a ADMIN/MANAGER."""
    return MasterDataService.update_customer(db, id, payload, current_user)


# ---------------------------------------------------------------------------
# Fornecedores (Suppliers)
# ---------------------------------------------------------------------------

@router.get("/suppliers", response_model=List[SupplierRead])
def list_suppliers(
    search: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    category: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retorna a lista de fornecedores cadastrados."""
    return MasterDataService.list_suppliers(db, search, status_filter, category, limit, offset)


@router.get("/suppliers/{id}", response_model=SupplierRead)
def get_supplier(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Busca detalhes de um fornecedor pelo ID."""
    return MasterDataService.get_supplier(db, id)


@router.post("/suppliers", response_model=SupplierRead, status_code=status.HTTP_201_CREATED)
def create_supplier(
    payload: SupplierCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """Cadastra um novo fornecedor vinculado a uma Pessoa. Restrito a ADMIN/MANAGER."""
    return MasterDataService.create_supplier(db, payload, current_user)


@router.patch("/suppliers/{id}", response_model=SupplierRead)
def update_supplier(
    id: uuid.UUID,
    payload: SupplierUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """Atualiza as informações de um fornecedor. Restrito a ADMIN/MANAGER."""
    return MasterDataService.update_supplier(db, id, payload, current_user)


# ---------------------------------------------------------------------------
# Produtos / Itens (ProductItems)
# ---------------------------------------------------------------------------

@router.get("/items", response_model=List[ProductItemRead])
def list_items(
    search: Optional[str] = Query(None),
    item_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retorna a lista de produtos/itens cadastrados."""
    return MasterDataService.list_items(db, search, item_type, is_active, limit, offset)


@router.get("/items/{id}", response_model=ProductItemRead)
def get_item(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Busca detalhes de um produto/item pelo ID."""
    return MasterDataService.get_item(db, id)


@router.post("/items", response_model=ProductItemRead, status_code=status.HTTP_201_CREATED)
def create_item(
    payload: ProductItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """Cadastra um novo produto/item. Restrito a ADMIN/MANAGER."""
    return MasterDataService.create_item(db, payload, current_user)


@router.patch("/items/{id}", response_model=ProductItemRead)
def update_item(
    id: uuid.UUID,
    payload: ProductItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """Atualiza as informações de um produto/item. Restrito a ADMIN/MANAGER."""
    return MasterDataService.update_item(db, id, payload, current_user)


# ---------------------------------------------------------------------------
# Serviços (Services)
# ---------------------------------------------------------------------------

@router.get("/services", response_model=List[ServiceRead])
def list_services(
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retorna a lista de serviços cadastrados."""
    return MasterDataService.list_services(db, search, is_active, limit, offset)


@router.get("/services/{id}", response_model=ServiceRead)
def get_service(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Busca detalhes de um serviço pelo ID."""
    return MasterDataService.get_service(db, id)


@router.post("/services", response_model=ServiceRead, status_code=status.HTTP_201_CREATED)
def create_service(
    payload: ServiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """Cadastra um novo serviço. Restrito a ADMIN/MANAGER."""
    return MasterDataService.create_service(db, payload, current_user)


@router.patch("/services/{id}", response_model=ServiceRead)
def update_service(
    id: uuid.UUID,
    payload: ServiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """Atualiza as informações de um serviço. Restrito a ADMIN/MANAGER."""
    return MasterDataService.update_service(db, id, payload, current_user)


# ---------------------------------------------------------------------------
# Famílias de Produtos e Deduplicação (Catalog Pack)
# ---------------------------------------------------------------------------

@router.post("/items/initialize-families", status_code=status.HTTP_200_OK)
def initialize_catalog_families(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """Executa a rotina inteligente de classificação do catálogo. Restrito a ADMIN/MANAGER."""
    return MasterDataService.initialize_catalog_families(db)


@router.get("/families", response_model=List[ProductFamilyRead])
def list_families(
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lista todas as famílias de produtos cadastradas."""
    return MasterDataService.list_families(db, search, limit, offset)


@router.get("/families/{id}", response_model=Any)
def get_family_details(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retorna detalhes da família de produtos e suas variações/itens."""
    family = MasterDataService.get_family(db, id)
    products = [p for p in family.products if p.is_active]
    return {
        "id": family.id,
        "name": family.name,
        "description": family.description,
        "created_at": family.created_at,
        "products": products
    }


@router.get("/deduplication", response_model=List[ProductDeduplicationRead])
def list_deduplication(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """Retorna a fila de revisão de possíveis duplicados. Restrito a ADMIN/MANAGER."""
    return MasterDataService.list_deduplication(db, status_filter, limit, offset)


@router.post("/deduplication/{id}/resolve", response_model=ProductDeduplicationRead)
def resolve_deduplication(
    id: uuid.UUID,
    payload: ProductDeduplicationResolve,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """Resolve uma suspeita de duplicado na fila de revisão. Restrito a ADMIN/MANAGER."""
    return MasterDataService.resolve_deduplication(db, id, payload, current_user)


@router.post("/items/{id}/update-price")
def update_item_price(
    id: uuid.UUID,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Atualiza o preço de referência ativo de uma variação (item de produto)."""
    if "new_price" not in payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O campo 'new_price' é obrigatório."
        )
    try:
        new_price = float(payload["new_price"])
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Preço inválido."
        )
    return MasterDataService.update_item_price(db, id, new_price, current_user)
