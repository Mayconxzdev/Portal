import re
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from fastapi import HTTPException, status

from app.models.master_data import Person, Customer, Supplier, ProductItem, Service, PersonAddress, PersonContact, ProductFamily, ProductDeduplicationQueue
from app.models.user import User
from app.core.events import emit_event

class MasterDataService:

    # Helper de normalização de documentos (CPF/CNPJ)
    @staticmethod
    def normalize_document(doc: Optional[str]) -> Optional[str]:
        if not doc:
            return None
        return re.sub(r"\D", "", doc)

    # Helper de normalização de e-mails
    @staticmethod
    def normalize_email(email: Optional[str]) -> Optional[str]:
        if not email:
            return None
        return email.strip().lower()

    # ---------------------------------------------------------------------------
    # Pessoa (Person) CRUD
    # ---------------------------------------------------------------------------

    @classmethod
    def list_people(
        cls,
        db: Session,
        search: Optional[str] = None,
        person_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Person]:
        query = db.query(Person)
        
        if search:
            normalized_search = cls.normalize_document(search)
            if normalized_search and len(normalized_search) >= 3:
                query = query.filter(
                    or_(
                        Person.name.ilike(f"%{search}%"),
                        Person.legal_name.ilike(f"%{search}%"),
                        Person.document_number.like(f"%{normalized_search}%"),
                        Person.email.ilike(f"%{search}%")
                    )
                )
            else:
                query = query.filter(
                    or_(
                        Person.name.ilike(f"%{search}%"),
                        Person.legal_name.ilike(f"%{search}%"),
                        Person.email.ilike(f"%{search}%")
                    )
                )

        if person_type:
            query = query.filter(Person.type == person_type.upper())
        if is_active is not None:
            query = query.filter(Person.is_active == is_active)

        return query.order_by(Person.name.asc()).offset(offset).limit(limit).all()

    @classmethod
    def get_person(cls, db: Session, person_id: uuid.UUID) -> Person:
        person = db.query(Person).filter(Person.id == person_id).first()
        if not person:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pessoa nao encontrada."
            )
        return person

    @classmethod
    def create_person(cls, db: Session, payload: Any, current_user: User) -> Person:
        # Normalização e validação de documento único
        doc_num = cls.normalize_document(payload.document_number)
        if doc_num:
            existing = db.query(Person).filter(Person.document_number == doc_num).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Ja existe uma pessoa cadastrada com o documento informado ({doc_num})."
                )

        # Normaliza e-mail
        email = cls.normalize_email(payload.email)

        # Cria Pessoa base
        person = Person(
            type=payload.type.upper(),
            name=payload.name.strip(),
            legal_name=payload.legal_name.strip() if payload.legal_name else None,
            document_type=payload.document_type.upper() if payload.document_type else None,
            document_number=doc_num,
            email=email,
            phone=payload.phone.strip() if payload.phone else None,
            notes=payload.notes,
            is_active=payload.is_active,
            tenant_id=payload.tenant_id
        )
        db.add(person)
        db.flush()  # Gera o id da pessoa no banco

        # Adiciona endereços
        for addr in payload.addresses:
            address = PersonAddress(
                person_id=person.id,
                type=addr.type.upper(),
                street=addr.street.strip(),
                number=addr.number.strip(),
                complement=addr.complement.strip() if addr.complement else None,
                district=addr.district.strip(),
                city=addr.city.strip(),
                state=addr.state.strip(),
                zip_code=addr.zip_code.strip(),
                country=addr.country.strip()
            )
            db.add(address)

        # Adiciona contatos
        for cont in payload.contacts:
            contact = PersonContact(
                person_id=person.id,
                name=cont.name.strip(),
                role=cont.role.strip() if cont.role else None,
                email=cls.normalize_email(cont.email),
                phone=cont.phone.strip() if cont.phone else None,
                whatsapp=cont.whatsapp.strip() if cont.whatsapp else None,
                is_primary=cont.is_primary
            )
            db.add(contact)

        db.commit()
        db.refresh(person)

        # Emitir evento
        emit_event(
            db=db,
            event_type="master_data.person.created",
            aggregate_type="person",
            aggregate_id=str(person.id),
            module="master_data",
            payload={
                "id": str(person.id),
                "type": person.type,
                "name": person.name,
                "document_number": f"***.{person.document_number[-3:]}" if person.document_number else None,
                "actor_user_id": current_user.id,
                "action_url": f"/admin/master-data/people/{person.id}",
                "summary": f"Pessoa '{person.name}' cadastrada com sucesso por {current_user.username}."
            },
            actor_user_id=current_user.id
        )

        return person

    @classmethod
    def update_person(cls, db: Session, person_id: uuid.UUID, payload: Any, current_user: User) -> Person:
        person = cls.get_person(db, person_id)

        # Validação de documento único em caso de alteração
        doc_num = cls.normalize_document(payload.document_number)
        if doc_num and doc_num != person.document_number:
            existing = db.query(Person).filter(Person.document_number == doc_num).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Ja existe uma pessoa cadastrada com o documento informado ({doc_num})."
                )
            person.document_number = doc_num

        if payload.type:
            person.type = payload.type.upper()
        if payload.name:
            person.name = payload.name.strip()
        if payload.legal_name is not None:
            person.legal_name = payload.legal_name.strip() if payload.legal_name else None
        if payload.document_type:
            person.document_type = payload.document_type.upper()
        if payload.email is not None:
            person.email = cls.normalize_email(payload.email)
        if payload.phone is not None:
            person.phone = payload.phone.strip() if payload.phone else None
        if payload.notes is not None:
            person.notes = payload.notes
        if payload.is_active is not None:
            person.is_active = payload.is_active
        if payload.tenant_id is not None:
            person.tenant_id = payload.tenant_id

        person.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(person)

        # Emitir evento
        emit_event(
            db=db,
            event_type="master_data.person.updated",
            aggregate_type="person",
            aggregate_id=str(person.id),
            module="master_data",
            payload={
                "id": str(person.id),
                "type": person.type,
                "name": person.name,
                "document_number": f"***.{person.document_number[-3:]}" if person.document_number else None,
                "actor_user_id": current_user.id,
                "action_url": f"/admin/master-data/people/{person.id}",
                "summary": f"Pessoa '{person.name}' atualizada com sucesso por {current_user.username}."
            },
            actor_user_id=current_user.id
        )

        return person

    # ---------------------------------------------------------------------------
    # Cliente (Customer) CRUD
    # ---------------------------------------------------------------------------

    @classmethod
    def list_customers(
        cls,
        db: Session,
        search: Optional[str] = None,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Customer]:
        query = db.query(Customer).join(Person)
        
        if search:
            normalized_doc = cls.normalize_document(search)
            if normalized_doc and len(normalized_doc) >= 3:
                query = query.filter(
                    or_(
                        Customer.customer_code.ilike(f"%{search}%"),
                        Person.name.ilike(f"%{search}%"),
                        Person.legal_name.ilike(f"%{search}%"),
                        Person.document_number.like(f"%{normalized_doc}%")
                    )
                )
            else:
                query = query.filter(
                    or_(
                        Customer.customer_code.ilike(f"%{search}%"),
                        Person.name.ilike(f"%{search}%"),
                        Person.legal_name.ilike(f"%{search}%")
                    )
                )

        if status_filter:
            query = query.filter(Customer.status == status_filter.upper())

        return query.order_by(Person.name.asc()).offset(offset).limit(limit).all()

    @classmethod
    def get_customer(cls, db: Session, customer_id: uuid.UUID) -> Customer:
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente nao encontrado."
            )
        return customer

    @classmethod
    def create_customer(cls, db: Session, payload: Any, current_user: User) -> Customer:
        # Garante que a Pessoa existe
        person = cls.get_person(db, payload.person_id)

        # Validação: apenas um Cliente por Pessoa
        existing = db.query(Customer).filter(Customer.person_id == payload.person_id).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Esta pessoa ja possui o papel de cliente cadastrado."
            )

        # Validação de código de cliente único se informado
        if payload.customer_code:
            code_existing = db.query(Customer).filter(Customer.customer_code == payload.customer_code).first()
            if code_existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Ja existe um cliente cadastrado com o codigo '{payload.customer_code}'."
                )

        customer = Customer(
            person_id=payload.person_id,
            customer_code=payload.customer_code.strip() if payload.customer_code else None,
            status=payload.status.upper(),
            default_payment_terms=payload.default_payment_terms.strip() if payload.default_payment_terms else None,
            notes=payload.notes
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)

        # Emitir evento
        emit_event(
            db=db,
            event_type="master_data.customer.created",
            aggregate_type="customer",
            aggregate_id=str(customer.id),
            module="master_data",
            payload={
                "id": str(customer.id),
                "person_id": str(customer.person_id),
                "name": person.name,
                "customer_code": customer.customer_code,
                "status": customer.status,
                "actor_user_id": current_user.id,
                "action_url": f"/admin/master-data/customers/{customer.id}",
                "summary": f"Cliente '{person.name}' cadastrado com sucesso por {current_user.username}."
            },
            actor_user_id=current_user.id
        )

        return customer

    @classmethod
    def update_customer(cls, db: Session, customer_id: uuid.UUID, payload: Any, current_user: User) -> Customer:
        customer = cls.get_customer(db, customer_id)

        # Validação de código de cliente único se alterado
        if payload.customer_code and payload.customer_code != customer.customer_code:
            code_existing = db.query(Customer).filter(Customer.customer_code == payload.customer_code).first()
            if code_existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Ja existe um cliente cadastrado com o codigo '{payload.customer_code}'."
                )
            customer.customer_code = payload.customer_code.strip()

        if payload.status:
            customer.status = payload.status.upper()
        if payload.default_payment_terms is not None:
            customer.default_payment_terms = payload.default_payment_terms.strip() if payload.default_payment_terms else None
        if payload.notes is not None:
            customer.notes = payload.notes

        customer.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(customer)

        # Emitir evento
        emit_event(
            db=db,
            event_type="master_data.customer.updated",
            aggregate_type="customer",
            aggregate_id=str(customer.id),
            module="master_data",
            payload={
                "id": str(customer.id),
                "person_id": str(customer.person_id),
                "name": customer.person.name,
                "customer_code": customer.customer_code,
                "status": customer.status,
                "actor_user_id": current_user.id,
                "action_url": f"/admin/master-data/customers/{customer.id}",
                "summary": f"Cliente '{customer.person.name}' atualizado com sucesso por {current_user.username}."
            },
            actor_user_id=current_user.id
        )

        return customer

    # ---------------------------------------------------------------------------
    # Fornecedor (Supplier) CRUD
    # ---------------------------------------------------------------------------

    @classmethod
    def list_suppliers(
        cls,
        db: Session,
        search: Optional[str] = None,
        status_filter: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Supplier]:
        query = db.query(Supplier).join(Person)
        
        if search:
            normalized_doc = cls.normalize_document(search)
            if normalized_doc and len(normalized_doc) >= 3:
                query = query.filter(
                    or_(
                        Supplier.supplier_code.ilike(f"%{search}%"),
                        Person.name.ilike(f"%{search}%"),
                        Person.legal_name.ilike(f"%{search}%"),
                        Person.document_number.like(f"%{normalized_doc}%")
                    )
                )
            else:
                query = query.filter(
                    or_(
                        Supplier.supplier_code.ilike(f"%{search}%"),
                        Person.name.ilike(f"%{search}%"),
                        Person.legal_name.ilike(f"%{search}%")
                    )
                )

        if status_filter:
            query = query.filter(Supplier.status == status_filter.upper())
        
        # Filtro de categoria no JSON
        if category:
            query = query.filter(Supplier.categories.like(f"%{category}%"))

        return query.order_by(Person.name.asc()).offset(offset).limit(limit).all()

    @classmethod
    def get_supplier(cls, db: Session, supplier_id: uuid.UUID) -> Supplier:
        supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
        if not supplier:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Fornecedor nao encontrado."
            )
        return supplier

    @classmethod
    def create_supplier(cls, db: Session, payload: Any, current_user: User) -> Supplier:
        # Garante que a Pessoa existe
        person = cls.get_person(db, payload.person_id)

        # Validação: apenas um Fornecedor por Pessoa
        existing = db.query(Supplier).filter(Supplier.person_id == payload.person_id).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Esta pessoa ja possui o papel de fornecedor cadastrado."
            )

        # Validação de código de fornecedor único se informado
        if payload.supplier_code:
            code_existing = db.query(Supplier).filter(Supplier.supplier_code == payload.supplier_code).first()
            if code_existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Ja existe um fornecedor cadastrado com o codigo '{payload.supplier_code}'."
                )

        supplier = Supplier(
            person_id=payload.person_id,
            supplier_code=payload.supplier_code.strip() if payload.supplier_code else None,
            categories=payload.categories,
            preferred_contact_email=cls.normalize_email(payload.preferred_contact_email),
            rating=payload.rating,
            status=payload.status.upper(),
            notes=payload.notes
        )
        db.add(supplier)
        db.commit()
        db.refresh(supplier)

        # Emitir evento
        emit_event(
            db=db,
            event_type="master_data.supplier.created",
            aggregate_type="supplier",
            aggregate_id=str(supplier.id),
            module="master_data",
            payload={
                "id": str(supplier.id),
                "person_id": str(supplier.person_id),
                "name": person.name,
                "supplier_code": supplier.supplier_code,
                "status": supplier.status,
                "actor_user_id": current_user.id,
                "action_url": f"/admin/master-data/suppliers/{supplier.id}",
                "summary": f"Fornecedor '{person.name}' cadastrado com sucesso por {current_user.username}."
            },
            actor_user_id=current_user.id
        )

        return supplier

    @classmethod
    def update_supplier(cls, db: Session, supplier_id: uuid.UUID, payload: Any, current_user: User) -> Supplier:
        supplier = cls.get_supplier(db, supplier_id)

        # Validação de código de fornecedor único se alterado
        if payload.supplier_code and payload.supplier_code != supplier.supplier_code:
            code_existing = db.query(Supplier).filter(Supplier.supplier_code == payload.supplier_code).first()
            if code_existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Ja existe um fornecedor cadastrado com o codigo '{payload.supplier_code}'."
                )
            supplier.supplier_code = payload.supplier_code.strip()

        if payload.categories is not None:
            supplier.categories = payload.categories
        if payload.preferred_contact_email is not None:
            supplier.preferred_contact_email = cls.normalize_email(payload.preferred_contact_email)
        if payload.rating is not None:
            supplier.rating = payload.rating
        if payload.status:
            supplier.status = payload.status.upper()
        if payload.notes is not None:
            supplier.notes = payload.notes

        supplier.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(supplier)

        # Emitir evento
        emit_event(
            db=db,
            event_type="master_data.supplier.updated",
            aggregate_type="supplier",
            aggregate_id=str(supplier.id),
            module="master_data",
            payload={
                "id": str(supplier.id),
                "person_id": str(supplier.person_id),
                "name": supplier.person.name,
                "supplier_code": supplier.supplier_code,
                "status": supplier.status,
                "actor_user_id": current_user.id,
                "action_url": f"/admin/master-data/suppliers/{supplier.id}",
                "summary": f"Fornecedor '{supplier.person.name}' atualizado com sucesso por {current_user.username}."
            },
            actor_user_id=current_user.id
        )

        return supplier

    # ---------------------------------------------------------------------------
    # Produto / Item (ProductItem) CRUD
    # ---------------------------------------------------------------------------

    @classmethod
    def list_items(
        cls,
        db: Session,
        search: Optional[str] = None,
        item_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ProductItem]:
        query = db.query(ProductItem)

        if search:
            query = query.filter(
                or_(
                    ProductItem.sku.ilike(f"%{search}%"),
                    ProductItem.name.ilike(f"%{search}%"),
                    ProductItem.barcode.ilike(f"%{search}%")
                )
            )

        if item_type:
            query = query.filter(ProductItem.item_type == item_type.upper())
        if is_active is not None:
            query = query.filter(ProductItem.is_active == is_active)

        return query.order_by(ProductItem.sku.asc()).offset(offset).limit(limit).all()

    @classmethod
    def get_item(cls, db: Session, item_id: uuid.UUID) -> ProductItem:
        item = db.query(ProductItem).filter(ProductItem.id == item_id).first()
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Produto/Item nao encontrado."
            )
        return item

    @classmethod
    def create_item(cls, db: Session, payload: Any, current_user: User) -> ProductItem:
        # SKU único
        sku = payload.sku.strip()
        existing = db.query(ProductItem).filter(ProductItem.sku == sku).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ja existe um produto cadastrado com o SKU '{sku}'."
            )

        item = ProductItem(
            sku=sku,
            name=payload.name.strip(),
            description=payload.description.strip() if payload.description else None,
            item_type=payload.item_type.upper(),
            unit_of_measure=payload.unit_of_measure.strip(),
            category=payload.category.strip() if payload.category else None,
            ncm=payload.ncm.strip() if payload.ncm else None,
            barcode=payload.barcode.strip() if payload.barcode else None,
            is_active=payload.is_active
        )
        db.add(item)
        db.commit()
        db.refresh(item)

        # Emitir evento
        emit_event(
            db=db,
            event_type="master_data.item.created",
            aggregate_type="item",
            aggregate_id=str(item.id),
            module="master_data",
            payload={
                "id": str(item.id),
                "sku": item.sku,
                "name": item.name,
                "item_type": item.item_type,
                "is_active": item.is_active,
                "actor_user_id": current_user.id,
                "action_url": f"/admin/master-data/items/{item.id}",
                "summary": f"Produto '{item.name}' (SKU: {item.sku}) cadastrado com sucesso por {current_user.username}."
            },
            actor_user_id=current_user.id
        )

        return item

    @classmethod
    def update_item(cls, db: Session, item_id: uuid.UUID, payload: Any, current_user: User) -> ProductItem:
        item = cls.get_item(db, item_id)

        # SKU único em alteração
        if payload.sku and payload.sku != item.sku:
            sku = payload.sku.strip()
            existing = db.query(ProductItem).filter(ProductItem.sku == sku).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Ja existe um produto cadastrado com o SKU '{sku}'."
                )
            item.sku = sku

        if payload.name:
            item.name = payload.name.strip()
        if payload.description is not None:
            item.description = payload.description.strip() if payload.description else None
        if payload.item_type:
            item.item_type = payload.item_type.upper()
        if payload.unit_of_measure:
            item.unit_of_measure = payload.unit_of_measure.strip()
        if payload.category is not None:
            item.category = payload.category.strip() if payload.category else None
        if payload.ncm is not None:
            item.ncm = payload.ncm.strip() if payload.ncm else None
        if payload.barcode is not None:
            item.barcode = payload.barcode.strip() if payload.barcode else None
        if payload.is_active is not None:
            item.is_active = payload.is_active

        item.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(item)

        # Emitir evento
        emit_event(
            db=db,
            event_type="master_data.item.updated",
            aggregate_type="item",
            aggregate_id=str(item.id),
            module="master_data",
            payload={
                "id": str(item.id),
                "sku": item.sku,
                "name": item.name,
                "item_type": item.item_type,
                "is_active": item.is_active,
                "actor_user_id": current_user.id,
                "action_url": f"/admin/master-data/items/{item.id}",
                "summary": f"Produto '{item.name}' (SKU: {item.sku}) atualizado com sucesso por {current_user.username}."
            },
            actor_user_id=current_user.id
        )

        return item

    # ---------------------------------------------------------------------------
    # Serviço (Service) CRUD
    # ---------------------------------------------------------------------------

    @classmethod
    def list_services(
        cls,
        db: Session,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Service]:
        query = db.query(Service)

        if search:
            query = query.filter(
                or_(
                    Service.code.ilike(f"%{search}%"),
                    Service.name.ilike(f"%{search}%")
                )
            )

        if is_active is not None:
            query = query.filter(Service.is_active == is_active)

        return query.order_by(Service.code.asc()).offset(offset).limit(limit).all()

    @classmethod
    def get_service(cls, db: Session, service_id: uuid.UUID) -> Service:
        service = db.query(Service).filter(Service.id == service_id).first()
        if not service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Servico nao encontrado."
            )
        return service

    @classmethod
    def create_service(cls, db: Session, payload: Any, current_user: User) -> Service:
        # Code único
        code = payload.code.strip()
        existing = db.query(Service).filter(Service.code == code).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ja existe um servico cadastrado com o codigo '{code}'."
            )

        service = Service(
            code=code,
            name=payload.name.strip(),
            description=payload.description.strip() if payload.description else None,
            category=payload.category.strip() if payload.category else None,
            default_price=payload.default_price,
            is_active=payload.is_active
        )
        db.add(service)
        db.commit()
        db.refresh(service)

        # Emitir evento
        emit_event(
            db=db,
            event_type="master_data.service.created",
            aggregate_type="service",
            aggregate_id=str(service.id),
            module="master_data",
            payload={
                "id": str(service.id),
                "code": service.code,
                "name": service.name,
                "is_active": service.is_active,
                "actor_user_id": current_user.id,
                "action_url": f"/admin/master-data/services/{service.id}",
                "summary": f"Servico '{service.name}' (Codigo: {service.code}) cadastrado com sucesso por {current_user.username}."
            },
            actor_user_id=current_user.id
        )

        return service

    @classmethod
    def update_service(cls, db: Session, service_id: uuid.UUID, payload: Any, current_user: User) -> Service:
        service = cls.get_service(db, service_id)

        # Code único em alteração
        if payload.code and payload.code != service.code:
            code = payload.code.strip()
            existing = db.query(Service).filter(Service.code == code).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Ja existe um servico cadastrado com o codigo '{code}'."
                )
            service.code = code

        if payload.name:
            service.name = payload.name.strip()
        if payload.description is not None:
            service.description = payload.description.strip() if payload.description else None
        if payload.category is not None:
            service.category = payload.category.strip() if payload.category else None
        if payload.default_price is not None:
            service.default_price = payload.default_price
        if payload.is_active is not None:
            service.is_active = payload.is_active

        service.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(service)

        # Emitir evento
        emit_event(
            db=db,
            event_type="master_data.service.updated",
            aggregate_type="service",
            aggregate_id=str(service.id),
            module="master_data",
            payload={
                "id": str(service.id),
                "code": service.code,
                "name": service.name,
                "is_active": service.is_active,
                "actor_user_id": current_user.id,
                "action_url": f"/admin/master-data/services/{service.id}",
                "summary": f"Servico '{service.name}' (Codigo: {service.code}) atualizado com sucesso por {current_user.username}."
            },
            actor_user_id=current_user.id
        )

        return service

    # ---------------------------------------------------------------------------
    # Famílias de Produtos e Deduplicação
    # ---------------------------------------------------------------------------

    @classmethod
    def list_families(
        cls,
        db: Session,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ProductFamily]:
        query = db.query(ProductFamily)
        if search:
            query = query.filter(ProductFamily.name.ilike(f"%{search}%"))
        return query.order_by(ProductFamily.name.asc()).offset(offset).limit(limit).all()

    @classmethod
    def get_family(cls, db: Session, family_id: uuid.UUID) -> ProductFamily:
        family = db.query(ProductFamily).filter(ProductFamily.id == family_id).first()
        if not family:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Família de produtos não encontrada."
            )
        return family

    @classmethod
    def list_deduplication(
        cls,
        db: Session,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ProductDeduplicationQueue]:
        query = db.query(ProductDeduplicationQueue)
        if status_filter:
            query = query.filter(ProductDeduplicationQueue.status == status_filter.upper())
        return query.order_by(ProductDeduplicationQueue.similarity_score.desc()).offset(offset).limit(limit).all()

    @classmethod
    def resolve_deduplication(
        cls,
        db: Session,
        deduplication_id: uuid.UUID,
        payload: Any,
        current_user: User
    ) -> ProductDeduplicationQueue:
        entry = db.query(ProductDeduplicationQueue).filter(ProductDeduplicationQueue.id == deduplication_id).first()
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Registro de deduplicação não encontrado."
            )
        
        decision = payload.decision.upper() # APPROVED_MERGE | REJECTED | RESOLVED
        entry.status = decision
        entry.notes = payload.notes
        entry.resolved_at = datetime.now(timezone.utc)
        entry.resolved_by_user_id = current_user.id
        
        if decision == "APPROVED_MERGE":
            # Mesclar item_b em item_a
            item_a = entry.item_a
            item_b = entry.item_b
            if item_a and item_b:
                item_b.is_active = False
                item_b.family_id = item_a.family_id
                item_b.description = f"Mesclado com o item {item_a.sku} em {entry.resolved_at}. " + (item_b.description or "")
                
                from app.models.purchase import PurchasePriceReference
                ref_a = db.query(PurchasePriceReference).filter(PurchasePriceReference.product_item_id == item_a.id, PurchasePriceReference.is_active == True).first()
                ref_b = db.query(PurchasePriceReference).filter(PurchasePriceReference.product_item_id == item_b.id, PurchasePriceReference.is_active == True).first()
                if ref_b and not ref_a:
                    new_ref = PurchasePriceReference(
                        product_item_id=item_a.id,
                        supplier_id=ref_b.supplier_id,
                        current_unit_price=ref_b.current_unit_price,
                        currency=ref_b.currency,
                        unit_of_measure=ref_b.unit_of_measure,
                        approved_by_user_id=current_user.id,
                        notes=f"Herdado por mesclagem do item {item_b.sku}"
                    )
                    db.add(new_ref)
                    ref_b.is_active = False
        
        db.commit()
        db.refresh(entry)
        
        emit_event(
            db=db,
            event_type="master_data.deduplication.resolved",
            aggregate_type="deduplication",
            aggregate_id=str(entry.id),
            module="master_data",
            payload={
                "id": str(entry.id),
                "decision": entry.status,
                "item_a_id": str(entry.item_a_id),
                "item_b_id": str(entry.item_b_id),
                "actor_user_id": current_user.id,
                "summary": f"Deduplicação resolvida como '{entry.status}' por {current_user.username}."
            },
            actor_user_id=current_user.id
        )
        return entry

    @classmethod
    def update_item_price(
        cls,
        db: Session,
        item_id: uuid.UUID,
        new_price: float,
        current_user: User
    ) -> Any:
        item = cls.get_item(db, item_id)
        
        from app.models.purchase import PurchasePriceEvidence, PurchasePriceHistory, PurchasePriceReference
        
        evidence = PurchasePriceEvidence(
            source_type="MANUAL_ENTRY",
            product_item_id=item.id,
            unit_price=new_price,
            quantity=1.0,
            total_amount=new_price,
            currency="BRL",
            unit_of_measure=item.unit_of_measure,
            created_by_user_id=current_user.id,
            notes="Atualização de preço direta no catálogo"
        )
        db.add(evidence)
        db.flush()
        
        history = PurchasePriceHistory(
            product_item_id=item.id,
            evidence_id=evidence.id,
            unit_price=new_price,
            quantity=1.0,
            total_amount=new_price,
            currency="BRL",
            unit_of_measure=item.unit_of_measure,
            source_type="MANUAL_ENTRY",
            created_by_user_id=current_user.id
        )
        db.add(history)
        db.flush()
        
        ref = db.query(PurchasePriceReference).filter(
            PurchasePriceReference.product_item_id == item.id,
            PurchasePriceReference.is_active == True
        ).first()
        
        if ref:
            ref.current_unit_price = new_price
            ref.source_history_id = history.id
            ref.source_evidence_id = evidence.id
            ref.approved_by_user_id = current_user.id
            ref.approved_at = datetime.now(timezone.utc)
            ref.updated_at = datetime.now(timezone.utc)
        else:
            ref = PurchasePriceReference(
                product_item_id=item.id,
                current_unit_price=new_price,
                currency="BRL",
                unit_of_measure=item.unit_of_measure,
                source_history_id=history.id,
                source_evidence_id=evidence.id,
                approved_by_user_id=current_user.id,
                approved_at=datetime.now(timezone.utc),
                is_active=True
            )
            db.add(ref)
            
        db.commit()
        
        emit_event(
            db=db,
            event_type="purchase.price.updated",
            aggregate_type="item",
            aggregate_id=str(item.id),
            module="purchases",
            payload={
                "item_id": str(item.id),
                "sku": item.sku,
                "name": item.name,
                "new_price": float(new_price),
                "actor_user_id": current_user.id,
                "summary": f"Preço de referência do item '{item.name}' atualizado para R$ {new_price:.2f} por {current_user.username}."
            },
            actor_user_id=current_user.id
        )
        
        return {
            "item_id": item.id,
            "sku": item.sku,
            "name": item.name,
            "new_price": new_price,
            "reference_id": ref.id
        }

    @classmethod
    def initialize_catalog_families(cls, db: Session) -> dict:
        items = db.query(ProductItem).all()
        families_map = {}
        
        def deduce_family_name(name: str, category: Optional[str]) -> str:
            name_upper = name.upper()
            if "TUBO PVC" in name_upper:
                return "Tubo PVC"
            elif "TUBO TRAMAPLAS" in name_upper:
                return "Tubo Tramaplas"
            elif "TUBO" in name_upper:
                if "GALVANIZADO" in name_upper:
                    return "Tubo Galvanizado"
                elif "INOX" in name_upper:
                    return "Tubo Inox"
                elif "CARBONO" in name_upper:
                    return "Tubo de Aço Carbono"
                return "Tubo"
            elif "REDU" in name_upper and "EXC" in name_upper:
                return "Redução Excêntrica ESC"
            elif "TAMBOR" in name_upper:
                if "FIBRA" in name_upper:
                    return "Tambor em Fibra de Vidro"
                return "Tambor"
            elif "BOBINA PL" in name_upper or ("BOBINA" in name_upper and "BOLHA" in name_upper):
                return "Bobina de Plástico Bolha"
            elif "BOBINA" in name_upper:
                return "Bobina Plástica"
            elif "CHAPA GALV" in name_upper or "CH. GALV" in name_upper:
                return "Chapa Galvanizada"
            elif "CHAPA INOX" in name_upper or "CH. INOX" in name_upper:
                return "Chapa Inox"
            elif "CHAPA" in name_upper or "CH." in name_upper:
                return "Chapa"
            elif "CANTONEIRA" in name_upper:
                return "Cantoneira"
            elif "FILTRO" in name_upper:
                return "Filtro"
            elif "PARAFUSO" in name_upper:
                return "Parafuso"
            elif "COLA" in name_upper:
                return "Cola"
            elif "MOTOR" in name_upper:
                return "Motor"
            elif "CORREIA" in name_upper:
                return "Correia"
            elif "ADESIVO" in name_upper:
                return "Adesivo"
            elif "ETIQUETA" in name_upper:
                return "Etiqueta"
            elif "PLAQUETA" in name_upper or "PLACA DADOS" in name_upper:
                return "Plaqueta de Identificação"
            elif "PORTA EMBLEMA" in name_upper or "EMBLEMA" in name_upper:
                return "Emblema Corporativo"
            
            for sep in [" - ", " – ", " — ", " : ", " | "]:
                if sep in name:
                    parts = name.split(sep, 1)
                    if len(parts[0].strip()) > 3:
                        return parts[0].strip()
            
            if category and category.strip() and category.strip().upper() not in ["OUTROS", "GERAL", "DIVERSOS", "PVC", "EMBALAGEM"]:
                return category.strip()
                
            words = [w for w in name.split() if w]
            if len(words) >= 2:
                return f"{words[0]} {words[1]}"
            elif len(words) == 1:
                return words[0]
            return "Geral"

        def extract_attributes(name: str, family_name: str) -> dict:
            details = name
            family_lower = family_name.lower()
            name_lower = name.lower()
            
            if name_lower.startswith(family_lower):
                details = name[len(family_name):].strip()
            else:
                for sep in [" - ", " – ", " — ", " : ", " | "]:
                    if sep in name:
                        parts = name.split(sep, 1)
                        if len(parts) == 2:
                            details = parts[1].strip()
                            break
            
            details = re.sub(r"^[\s\-—–:|]+", "", details).strip()
            if not details:
                details = "Padrão"
                
            attributes = {
                "variation_name": details,
                "medida": None,
                "espessura": None,
                "cor": None,
                "peso": None,
                "comprimento": None,
            }
            
            thickness_match = re.search(r"(\d+[\.,]\d+)\s*mm", details, re.IGNORECASE)
            dim_parts = re.split(r"\s+[xX]\s+", details)
            if len(dim_parts) >= 2:
                attributes["medida"] = dim_parts[0].strip()
                attributes["espessura"] = dim_parts[1].strip()
            else:
                mm_matches = re.findall(r"\b\d+(?:[\.,]\d+)?\s*(?:mm|mm\b)", details, re.IGNORECASE)
                if mm_matches:
                    attributes["medida"] = mm_matches[0]
                    if len(mm_matches) > 1:
                        attributes["espessura"] = mm_matches[1]
                        
                inch_match = re.search(r"\b\d+(?:[\.,/]\d+)?\"", details)
                if inch_match:
                    attributes["medida"] = inch_match.group(0)
                    
            color_match = re.search(r"\b(preto|preta|cinza|branco|branca|azul|verde|amarelo|vermelho|inox)\b", details, re.IGNORECASE)
            if color_match:
                attributes["cor"] = color_match.group(1).capitalize()
                
            weight_match = re.search(r"(\d+(?:[\.,]\d+)?)\s*(?:kg|kg\.|g|gramas)", details, re.IGNORECASE)
            if weight_match:
                attributes["peso"] = weight_match.group(0)
                
            len_match = re.search(r"(\d+(?:[\.,]\d+)?)\s*(?:mt|m|metros|mt\b)", details, re.IGNORECASE)
            if len_match:
                attributes["comprimento"] = len_match.group(0)
                
            return attributes

        from difflib import SequenceMatcher
        def string_similarity(a: str, b: str) -> float:
            return SequenceMatcher(None, a.lower(), b.lower()).ratio()

        families_created = 0
        items_updated = 0
        duplicates_flagged = 0
        
        existing_families = db.query(ProductFamily).all()
        for f in existing_families:
            families_map[f.name.upper()] = f

        assigned_canonical_keys = set()
        existing_keys = db.query(ProductItem.canonical_key).filter(ProductItem.canonical_key != None).all()
        for (k,) in existing_keys:
            assigned_canonical_keys.add(k.upper())

        for item in items:
            if item.family_id and item.canonical_key:
                continue
                
            family_name = deduce_family_name(item.name, item.category)
            family_key = family_name.upper()
            
            if family_key in families_map:
                family = families_map[family_key]
            else:
                family = ProductFamily(
                    name=family_name,
                    description=f"Família deduzida automaticamente de {item.name}"
                )
                db.add(family)
                db.flush()
                families_map[family_key] = family
                families_created += 1
                
            item.family_id = family.id
            attrs = extract_attributes(item.name, family_name)
            item.attributes = attrs
            
            raw_canonical = f"{family_name.upper()} | {attrs['variation_name'].upper()}"
            raw_canonical_key = raw_canonical.upper()
            
            if raw_canonical_key in assigned_canonical_keys:
                item.canonical_key = f"{raw_canonical} - DUP-{item.sku}"
                assigned_canonical_keys.add(item.canonical_key.upper())
                
                existing_item = db.query(ProductItem).filter(ProductItem.canonical_key == raw_canonical).first()
                if not existing_item:
                    for prev_item in items:
                        if prev_item.canonical_key == raw_canonical:
                            existing_item = prev_item
                            break
                            
                if existing_item:
                    dup_entry = ProductDeduplicationQueue(
                        item_a_id=existing_item.id,
                        item_b_id=item.id,
                        relation_type="POSSIBLE_DUPLICATE",
                        similarity_score=1.0,
                        status="PENDING",
                        notes="Chave canônica idêntica gerada durante inicialização"
                    )
                    db.add(dup_entry)
                    duplicates_flagged += 1
            else:
                item.canonical_key = raw_canonical
                assigned_canonical_keys.add(raw_canonical_key)
                
            items_updated += 1
            
        db.commit()
        
        for fam in db.query(ProductFamily).all():
            fam_products = [p for p in fam.products if p.is_active]
            for i in range(len(fam_products)):
                for j in range(i + 1, len(fam_products)):
                    item_a = fam_products[i]
                    item_b = fam_products[j]
                    
                    exists = db.query(ProductDeduplicationQueue).filter(
                        or_(
                            and_(ProductDeduplicationQueue.item_a_id == item_a.id, ProductDeduplicationQueue.item_b_id == item_b.id),
                            and_(ProductDeduplicationQueue.item_a_id == item_b.id, ProductDeduplicationQueue.item_b_id == item_a.id)
                        )
                    ).first()
                    
                    if exists:
                        continue
                        
                    score = string_similarity(item_a.name, item_b.name)
                    if score >= 0.85:
                        dup_entry = ProductDeduplicationQueue(
                            item_a_id=item_a.id,
                            item_b_id=item_b.id,
                            relation_type="POSSIBLE_DUPLICATE",
                            similarity_score=score,
                            status="PENDING",
                            notes=f"Similaridade de nome alta ({score*100:.1f}%) na família {fam.name}"
                        )
                        db.add(dup_entry)
                        duplicates_flagged += 1
                        
        db.commit()
        return {
            "families_created": families_created,
            "items_classified": items_updated,
            "duplicates_flagged": duplicates_flagged
        }

