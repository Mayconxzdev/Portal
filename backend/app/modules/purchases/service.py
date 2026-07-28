import uuid
import hashlib
import hmac
import html
import json
import mimetypes
import re
import unicodedata
from urllib.parse import urlparse
from sqlalchemy import or_, desc, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status
from datetime import datetime, timezone, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Dict, Any, Iterable
from pydantic import ValidationError

from app.models.purchase import (
    Supplier,
    PurchaseRequest,
    PurchaseRequestItem,
    PurchaseItemOption,
    Quotation,
    PurchaseActivity,
    PurchaseRFQ,
    PurchaseRFQSupplier,
    PurchaseRFQSupplierItem,
    PurchaseSenderAccount,
    PurchaseSenderSignature,
    PurchaseEmailMessage,
    PurchaseMonitoredAccount,
    PurchaseEmailInboundMessage,
    PurchaseEmailAttachment,
    PurchaseResponseCandidate,
    PurchaseMonitoringEvent,
    PurchaseResponseExtraction,
    PurchaseResponseExtractedField,
    PurchaseResponseEvidence,
    PurchaseResponseReviewDecision,
    PurchaseQuoteResponse,
    PurchaseQuoteLine,
    PurchaseComparison,
    PurchasePriceEvidence,
    PurchasePriceHistory,
    PurchasePriceReference,
    PurchasePriceUpdateSuggestion,
    PurchaseSupplierPriceOffer,
    PurchaseRequestIdempotencyKey,
    PurchaseInterpretedDraft,
    PurchaseInterpretedDraftItem,
    PurchaseResearchJob,
)
from app.modules.purchases.schemas import PurchaseMonitoringEmailCallbackPayload
from app.models.user import User
from app.core.config import settings
from app.core.audit import log_action
from app.core.permissions import PermissionLevel, LEVEL_VALUES
from app.modules.approvals.service import ApprovalService
from app.core.ws import manager
from app.core.events import emit_event
from app.models.master_data import Person, ProductFamily, ProductItem, Service
from app.models.stock import StockCatalogItem, StockCatalogOffer, StockCatalogSupplier
from app.modules.stock.service import StockCatalogService
from app.modules.purchases.xlsx_reconciliation import PurchasesXlsxReconciliation, PurchasesXlsxSmartCatalog

async def trigger_dashboard_update():
    """Notifica via WebSocket que o dashboard deve ser atualizado"""
    try:
        await manager.broadcast({
            "type": "approval_notification", # Dashboard escuta esse evento para recarregar
            "data": {"module": "purchases"}
        })
    except Exception as e:
        print(f"Erro ao disparar atualizacao WS: {e}")

PRICE_SOURCE_TYPES_ALLOWED = {"BOLETO", "NF", "RFQ_RESPONSE", "EMAIL", "MANUAL_ENTRY"}
PRICE_VARIATION_EPSILON = Decimal("0.0001")


def _as_decimal(value: Any, *, default: Optional[Decimal] = None) -> Optional[Decimal]:
    if value is None:
        return default
    return Decimal(str(value))


def _money(value: Any) -> Decimal:
    parsed = _as_decimal(value, default=Decimal("0"))
    return (parsed or Decimal("0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _percent(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

class PurchasesService:
    # ---------------------------------------------------------------------------
    # Fornecedores (Suppliers)
    # ---------------------------------------------------------------------------
    @staticmethod
    def list_suppliers(db: Session, active_only: bool = True) -> List[Supplier]:
        from app.models.master_data import Person
        query = db.query(Supplier).join(Person)
        if active_only:
            query = query.filter(Supplier.status == "ACTIVE")
        return query.order_by(Person.name).all()

    @staticmethod
    def create_supplier(db: Session, payload: Any, current_user: User) -> Supplier:
        # Apenas ADMIN ou MANAGER do modulo de compras podem criar fornecedor
        user_level = ApprovalService.get_user_module_level(db, current_user, "purchases")
        is_admin = current_user.role and current_user.role.name == "ADMIN"
        if LEVEL_VALUES[user_level] < LEVEL_VALUES[PermissionLevel.MANAGER] and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissao insuficiente para cadastrar fornecedor (requer MANAGER)."
            )

        from app.models.master_data import Person, Supplier as MasterSupplier
        from app.modules.master_data.service import MasterDataService

        # Evita CNPJ duplicado se informado
        doc_num = MasterDataService.normalize_document(payload.cnpj)
        if doc_num:
            existing = db.query(Person).filter(Person.document_number == doc_num).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Fornecedor com CNPJ {payload.cnpj} já cadastrado."
                )

        # Cria a Pessoa
        person = Person(
            type="COMPANY",
            name=payload.company_name.strip(),
            legal_name=payload.trade_name.strip() if payload.trade_name else None,
            document_type="CNPJ",
            document_number=doc_num,
            email=MasterDataService.normalize_email(payload.email),
            phone=payload.phone.strip() if payload.phone else None,
            notes=payload.notes,
            is_active=True
        )
        db.add(person)
        db.flush()

        # Cria o Fornecedor vinculado
        new_supplier = MasterSupplier(
            person_id=person.id,
            categories=[payload.category] if payload.category else [],
            preferred_contact_email=person.email,
            status="ACTIVE",
            notes=payload.notes
        )
        db.add(new_supplier)
        db.commit()
        db.refresh(new_supplier)

        log_action(
            db=db,
            user_id=current_user.id,
            action="purchases.supplier.created",
            module="purchases",
            details={"supplier_id": str(new_supplier.id), "name": person.name}
        )
        
        # Emite evento do Master Data
        try:
            emit_event(
                db=db,
                event_type="master_data.supplier.created",
                aggregate_type="supplier",
                aggregate_id=str(new_supplier.id),
                module="master-data",
                payload={
                    "id": str(new_supplier.id),
                    "person_id": str(person.id),
                    "name": person.name,
                    "status": new_supplier.status,
                    "actor_user_id": current_user.id,
                    "summary": f"Fornecedor {person.name} cadastrado no sistema."
                },
                actor_user_id=current_user.id
            )
            db.commit()
        except Exception as e:
            print(f"Failed to emit master_data.supplier.created: {e}")
            
        return new_supplier

    @staticmethod
    def update_supplier(db: Session, supplier_id: uuid.UUID, payload: Any, current_user: User) -> Supplier:
        user_level = ApprovalService.get_user_module_level(db, current_user, "purchases")
        is_admin = current_user.role and current_user.role.name == "ADMIN"
        if LEVEL_VALUES[user_level] < LEVEL_VALUES[PermissionLevel.MANAGER] and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissao insuficiente para atualizar fornecedor."
            )

        supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
        if not supplier:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Fornecedor nao encontrado."
            )

        person = supplier.person
        payload_dict = payload.model_dump(exclude_unset=True)
        if "company_name" in payload_dict:
            person.name = payload_dict["company_name"].strip()
        if "trade_name" in payload_dict:
            person.legal_name = payload_dict["trade_name"].strip() if payload_dict["trade_name"] else None
        if "cnpj" in payload_dict:
            from app.modules.master_data.service import MasterDataService
            from app.models.master_data import Person as MasterPerson
            doc_num = MasterDataService.normalize_document(payload_dict["cnpj"])
            if doc_num and doc_num != person.document_number:
                existing = db.query(MasterPerson).filter(MasterPerson.document_number == doc_num).first()
                if existing:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Outra pessoa com CNPJ {payload_dict['cnpj']} já existe."
                    )
                person.document_number = doc_num
        if "email" in payload_dict:
            from app.modules.master_data.service import MasterDataService
            person.email = MasterDataService.normalize_email(payload_dict["email"])
            supplier.preferred_contact_email = person.email
        if "phone" in payload_dict:
            person.phone = payload_dict["phone"].strip() if payload_dict["phone"] else None
        if "category" in payload_dict:
            supplier.categories = [payload_dict["category"]] if payload_dict["category"] else []
        if "notes" in payload_dict:
            person.notes = payload_dict["notes"]
            supplier.notes = payload_dict["notes"]

        supplier.updated_at = datetime.now(timezone.utc)
        person.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(supplier)

        log_action(
            db=db,
            user_id=current_user.id,
            action="purchases.supplier.updated",
            module="purchases",
            details={"supplier_id": str(supplier.id)}
        )

        try:
            emit_event(
                db=db,
                event_type="master_data.supplier.updated",
                aggregate_type="supplier",
                aggregate_id=str(supplier.id),
                module="master-data",
                payload={
                    "id": str(supplier.id),
                    "person_id": str(person.id),
                    "name": person.name,
                    "status": supplier.status,
                    "actor_user_id": current_user.id,
                    "summary": f"Cadastro do fornecedor {person.name} atualizado."
                },
                actor_user_id=current_user.id
            )
            db.commit()
        except Exception as e:
            print(f"Failed to emit master_data.supplier.updated: {e}")

        return supplier

    @staticmethod
    def delete_supplier(db: Session, supplier_id: uuid.UUID, current_user: User) -> Supplier:
        user_level = ApprovalService.get_user_module_level(db, current_user, "purchases")
        is_admin = current_user.role and current_user.role.name == "ADMIN"
        if LEVEL_VALUES[user_level] < LEVEL_VALUES[PermissionLevel.MANAGER] and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissao insuficiente para inativar fornecedor."
            )

        supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
        if not supplier:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Fornecedor nao encontrado."
            )

        supplier.status = "INACTIVE"
        supplier.updated_at = datetime.now(timezone.utc)
        db.commit()

        log_action(
            db=db,
            user_id=current_user.id,
            action="purchases.supplier.deleted",
            module="purchases",
            details={"supplier_id": str(supplier.id)}
        )
        return supplier

    # ---------------------------------------------------------------------------
    # Requisições de Compra (Purchase Requests)
    # ---------------------------------------------------------------------------
    @staticmethod
    def _request_matches_queue_filter(request: PurchaseRequest, queue_filter: Optional[str]) -> bool:
        filter_key = (queue_filter or "all").lower()
        if filter_key == "all":
            return True

        status_upper = (request.status or "").upper()
        items = list(request.items or [])
        has_rfq = bool(getattr(request, "rfqs", None))
        has_required_approval = any(getattr(item, "requires_approval", False) for item in items)
        has_pending_item_approval = any(
            getattr(item, "requires_approval", False)
            and (getattr(item, "approval_status", "PENDING") or "PENDING").upper() not in {"APPROVED", "REJECTED", "NOT_REQUIRED"}
            for item in items
        )

        if filter_key == "attention":
            return (
                status_upper in {"DRAFT", "REQUESTED", "RFQ_PREPARING", "QUOTES_RECEIVED", "COMPARING"}
                or any((getattr(item, "match_status", "") or "").lower() == "needs_confirmation" for item in items)
                or has_pending_item_approval
            )
        if filter_key == "suppliers":
            return status_upper in {"RFQ_PREPARING", "RFQ_SENT", "QUOTES_RECEIVED"} or has_rfq
        if filter_key == "approval":
            return status_upper in {"PENDING_APPROVAL", "APPROVAL_REQUIRED"} or has_pending_item_approval
        if filter_key == "ready":
            return status_upper == "APPROVED" or (
                has_required_approval
                and items
                and all(
                    (not getattr(item, "requires_approval", False))
                    or (getattr(item, "approval_status", "") or "").upper() == "APPROVED"
                    for item in items
                )
                and status_upper not in {"ORDERED", "DELIVERED", "CANCELLED", "REJECTED"}
            )
        if filter_key == "delivery":
            return status_upper in {"ORDERED", "AWAITING_DELIVERY", "PARTIAL_DELIVERY"} or any(
                (getattr(item, "delivery_status", "") or "").upper() in {"AWAITING_DELIVERY", "PARTIALLY_DELIVERED"}
                for item in items
            )
        return True

    @staticmethod
    def _queue_counts(requests: List[PurchaseRequest]) -> Dict[str, int]:
        filters = ("all", "attention", "suppliers", "approval", "ready", "delivery")
        return {
            filter_key: sum(
                1 for request in requests
                if PurchasesService._request_matches_queue_filter(request, filter_key)
            )
            for filter_key in filters
        }

    @staticmethod
    def list_purchase_requests(
        db: Session,
        current_user: User,
        queue_filter: Optional[str] = None,
    ) -> List[PurchaseRequest]:
        query = db.query(PurchaseRequest).options(
            joinedload(PurchaseRequest.requester),
            joinedload(PurchaseRequest.items),
            joinedload(PurchaseRequest.rfqs),
        )
        
        # Usuários comuns veem apenas suas próprias requisições
        user_level = ApprovalService.get_user_module_level(db, current_user, "purchases")
        is_admin = current_user.role and current_user.role.name == "ADMIN"
        if LEVEL_VALUES[user_level] < LEVEL_VALUES[PermissionLevel.MANAGER] and not is_admin:
            query = query.filter(PurchaseRequest.requester_user_id == current_user.id)

        requests = query.order_by(desc(PurchaseRequest.created_at)).all()
        if queue_filter and queue_filter != "all":
            return [
                request for request in requests
                if PurchasesService._request_matches_queue_filter(request, queue_filter)
            ]
        return requests

    @staticmethod
    def _purchase_request_snapshot(request: PurchaseRequest) -> Dict[str, Any]:
        return {
            "id": str(request.id),
            "title": request.title,
            "status": request.status,
            "requester_user_id": request.requester_user_id,
            "estimated_total": float(request.estimated_total or 0.0),
        }

    @staticmethod
    def _payload_hash(payload: Any) -> str:
        if hasattr(payload, "model_dump"):
            data = payload.model_dump(mode="json", exclude_none=True)
        elif isinstance(payload, dict):
            data = dict(payload)
        else:
            data = dict(getattr(payload, "__dict__", {}) or {})
        data.pop("idempotency_key", None)
        data.pop("client_request_id", None)
        raw = json.dumps(data, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _idempotency_value(payload: Any) -> Optional[str]:
        value = getattr(payload, "idempotency_key", None) or getattr(payload, "client_request_id", None)
        value = (value or "").strip()
        return value[:128] if value else None

    @staticmethod
    def get_purchase_request_by_idempotency_key(
        db: Session,
        key: str,
        current_user: User,
    ) -> Dict[str, Any]:
        record = (
            db.query(PurchaseRequestIdempotencyKey)
            .filter(
                PurchaseRequestIdempotencyKey.user_id == current_user.id,
                PurchaseRequestIdempotencyKey.idempotency_key == key,
            )
            .first()
        )
        if not record:
            return {"status": "not_found", "request": None, "error_message": None}
        request = None
        if record.purchase_request_id:
            request = PurchasesService.get_purchase_request(db, record.purchase_request_id, current_user)
        return {
            "status": record.status,
            "request": request,
            "error_message": record.error_message,
        }

    @staticmethod
    def get_purchase_request(db: Session, request_id: uuid.UUID, current_user: User) -> PurchaseRequest:
        request = db.query(PurchaseRequest).filter(PurchaseRequest.id == request_id).options(
            joinedload(PurchaseRequest.requester),
            joinedload(PurchaseRequest.items),
            joinedload(PurchaseRequest.quotations).joinedload(Quotation.supplier),
            joinedload(PurchaseRequest.activities).joinedload(PurchaseActivity.user),
            joinedload(PurchaseRequest.rfqs)
        ).first()

        if not request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Requisicao de compra nao encontrada."
            )

        # Valida visibilidade
        user_level = ApprovalService.get_user_module_level(db, current_user, "purchases")
        is_admin = current_user.role and current_user.role.name == "ADMIN"
        if LEVEL_VALUES[user_level] < LEVEL_VALUES[PermissionLevel.MANAGER] and not is_admin:
            if request.requester_user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Acesso negado a esta requisicao de compra."
                )

        return request

    @staticmethod
    def create_purchase_request(db: Session, payload: Any, current_user: User) -> PurchaseRequest:
        # Qualquer usuário com acesso NORMAL ou superior pode criar
        user_level = ApprovalService.get_user_module_level(db, current_user, "purchases")
        is_admin = current_user.role and current_user.role.name == "ADMIN"
        if LEVEL_VALUES[user_level] < LEVEL_VALUES[PermissionLevel.NORMAL] and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissao insuficiente para criar requisicao de compras."
            )

        idempotency_key = PurchasesService._idempotency_value(payload)
        idem_record = None
        payload_hash = PurchasesService._payload_hash(payload)
        if idempotency_key:
            idem_record = (
                db.query(PurchaseRequestIdempotencyKey)
                .filter(
                    PurchaseRequestIdempotencyKey.user_id == current_user.id,
                    PurchaseRequestIdempotencyKey.idempotency_key == idempotency_key,
                )
                .first()
            )
            if idem_record:
                if idem_record.payload_hash != payload_hash:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Esta chave de criacao ja foi usada com outro conteudo. Atualize a tela e tente novamente.",
                    )
                if idem_record.purchase_request_id:
                    return PurchasesService.get_purchase_request(db, idem_record.purchase_request_id, current_user)
            else:
                idem_record = PurchaseRequestIdempotencyKey(
                    user_id=current_user.id,
                    idempotency_key=idempotency_key,
                    payload_hash=payload_hash,
                    status="started",
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                db.add(idem_record)
                try:
                    db.commit()
                except IntegrityError:
                    db.rollback()
                    existing = (
                        db.query(PurchaseRequestIdempotencyKey)
                        .filter(
                            PurchaseRequestIdempotencyKey.user_id == current_user.id,
                            PurchaseRequestIdempotencyKey.idempotency_key == idempotency_key,
                        )
                        .first()
                    )
                    if existing and existing.purchase_request_id:
                        return PurchasesService.get_purchase_request(db, existing.purchase_request_id, current_user)
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Esta criacao ja esta em andamento. Aguarde alguns segundos e consulte novamente.",
                    )

        priority_val = payload.priority or payload.urgency or "NORMAL"
        new_request = PurchaseRequest(
            title=payload.title,
            description=payload.description,
            justification=payload.justification,
            requester_user_id=current_user.id,
            status="DRAFT",
            priority=priority_val,
            urgency=priority_val,
            category=payload.category,
            department=payload.department,
            needed_by=payload.needed_by,
            origin_type=getattr(payload, "origin_type", None),
            origin_ref_id=getattr(payload, "origin_ref_id", None),
            origin_snapshot_json=getattr(payload, "origin_snapshot_json", None),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        db.add(new_request)
        db.commit()
        db.refresh(new_request)

        estimated_total = 0.0
        for item_data in payload.items:
            # Regra: deve ter item_id, service_id ou free_text_description
            desc_val = item_data.free_text_description or item_data.description
            unit_val = item_data.unit_of_measure or item_data.unit or "un"
            specs_val = item_data.specifications or item_data.notes

            if not item_data.item_id and not item_data.service_id and not desc_val:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Item de requisicao precisa ter item_id, service_id ou free_text_description."
                )

            # Valida cadastros mestres se IDs forem informados
            if item_data.item_id:
                p_item = db.query(ProductItem).filter(ProductItem.id == item_data.item_id, ProductItem.is_active == True).first()
                if not p_item:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Item {item_data.item_id} nao existe ou nao esta ativo no Master Data."
                    )
            if item_data.service_id:
                srv = db.query(Service).filter(Service.id == item_data.service_id, Service.is_active == True).first()
                if not srv:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Servico {item_data.service_id} nao existe ou nao esta ativo no Master Data."
                    )

            item_price = float(item_data.estimated_unit_price or 0.0)
            item_qty = float(item_data.quantity)
            estimated_total += item_price * item_qty

            new_item = PurchaseRequestItem(
                purchase_request_id=new_request.id,
                item_id=item_data.item_id,
                service_id=item_data.service_id,
                stock_catalog_item_id=getattr(item_data, "stock_catalog_item_id", None),
                free_text_description=desc_val,
                quantity=item_qty,
                unit_of_measure=unit_val,
                specifications=specs_val,
                estimated_unit_price=item_price,
                source_type=getattr(item_data, "source_type", None),
                source_ref_id=getattr(item_data, "source_ref_id", None),
                source_confidence=getattr(item_data, "source_confidence", None),
                match_status=getattr(item_data, "match_status", "confirmed") or "confirmed",
                source_snapshot_json=getattr(item_data, "source_snapshot_json", None),
                normalized_name=getattr(item_data, "normalized_name", None) or desc_val,
                destination=getattr(item_data, "destination", None),
                department=getattr(item_data, "department", None),
                budget_limit=getattr(item_data, "budget_limit", None),
                classification=getattr(item_data, "classification", "EXTERNAL") or "EXTERNAL",
                classification_confidence=getattr(item_data, "classification_confidence", None),
                requires_approval=bool(getattr(item_data, "requires_approval", False)),
                approval_status=getattr(item_data, "approval_status", "PENDING") or "PENDING",
                purchasing_status=getattr(item_data, "purchasing_status", "PENDING") or "PENDING",
                delivery_status=getattr(item_data, "delivery_status", "PENDING") or "PENDING",
                created_at=datetime.now(timezone.utc)
            )
            db.add(new_item)

        new_request.estimated_total = estimated_total
        db.commit()
        db.refresh(new_request)

        # Cria atividade
        activity = PurchaseActivity(
            purchase_request_id=new_request.id,
            user_id=current_user.id,
            action="request.created",
            details={"title": new_request.title, "estimated_total": estimated_total},
            created_at=datetime.now(timezone.utc)
        )
        db.add(activity)
        db.commit()

        log_action(
            db=db,
            user_id=current_user.id,
            action="purchases.request.created",
            module="purchases",
            details={"request_id": str(new_request.id), "total": estimated_total}
        )

        # Emite evento do Event Engine
        try:
            emit_event(
                db=db,
                event_type="purchase.request.created",
                aggregate_type="purchase_request",
                aggregate_id=str(new_request.id),
                module="purchases",
                payload={
                    "id": str(new_request.id),
                    "title": new_request.title,
                    "requester_user_id": current_user.id,
                    "status": new_request.status,
                    "action_url": f"/purchases?request={new_request.id}",
                    "summary": f"Nova requisição de compra '{new_request.title}' criada por {current_user.username}."
                },
                actor_user_id=current_user.id
            )
            db.commit()
        except Exception as e:
            print(f"Failed to emit purchase.request.created: {e}")

        if idem_record:
            idem_record.purchase_request_id = new_request.id
            idem_record.status = "completed"
            idem_record.response_snapshot_json = PurchasesService._purchase_request_snapshot(new_request)
            idem_record.updated_at = datetime.now(timezone.utc)
            db.add(idem_record)
            db.commit()
            db.refresh(new_request)

        return new_request

    @staticmethod
    def _purchase_context_mode(context: Optional[str]) -> str:
        value = (context or "").strip().lower()
        if any(token in value for token in {"external", "internet", "online", "market"}):
            return "external"
        if any(token in value for token in {"internal", "portal", "stock", "estoque"}):
            return "internal"
        return "auto"

    @staticmethod
    def _parse_purchase_text_lines(
        db: Session,
        text: str,
        current_user: User,
        context: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        units = {"un", "und", "pc", "pcs", "m", "mt", "kg", "barra", "barras", "cx", "caixa"}
        parsed: List[Dict[str, Any]] = []
        for raw_line in [line.strip() for line in text.splitlines() if line.strip()]:
            # --- 1. Extração de Orçamento (budget_limit) ---
            budget_limit = None
            budget_match = re.search(
                r"(?:ate|at\u00e9|limite|orcamento|or\u00e7amento|valor|maximo|m\u00e1ximo|r\$|rs)\s*(?:r\$|rs)?\s*([\d\s]+(?:[.,]\d+)?)",
                raw_line,
                re.IGNORECASE
            )
            if budget_match:
                try:
                    val_str = budget_match.group(1).replace(" ", "").replace(".", "").replace(",", ".")
                    budget_limit = float(val_str)
                except Exception:
                    pass

            # --- 2. Extração de Destino (destination) ---
            destination = None
            dest_match = re.search(
                r"(?:para\s+o\s+pc\s+do|para\s+o\s+setor|para\s+o|para\s+a|para|entregar\s+em)\s+([a-zA-Z0-9\u00e0-\u00fa\u00c0-\u00da\s\-_]+?)(?:\s+(?:at\u00e9|ate|com|limite|orcamento|or\u00e7amento|r\$|rs)\b|$|,|\.)",
                raw_line,
                re.IGNORECASE
            )
            if dest_match:
                destination = dest_match.group(1).strip()

            # --- 3. Limpeza do texto para obter a descrição do produto ---
            clean_desc = raw_line
            if budget_match:
                clean_desc = clean_desc.replace(budget_match.group(0), "")
            if dest_match:
                clean_desc = clean_desc.replace(dest_match.group(0), "")

            # Limpa múltiplos espaços e pontuações sobressalentes
            clean_desc = re.sub(r"\s+", " ", clean_desc).strip(",. ")

            # --- 4. Extração de Quantidade e Unidade ---
            match = re.match(r"^\s*(?P<qty>\d+(?:[,.]\d+)?)?\s*(?P<unit>[a-zA-Z]+)?\s*(?P<desc>.+?)\s*$", clean_desc)
            qty = 1.0
            unit = "un"
            desc = clean_desc
            if match:
                qty_raw = match.group("qty")
                unit_raw = (match.group("unit") or "").lower()
                if qty_raw:
                    qty = float(qty_raw.replace(",", "."))
                if unit_raw in units:
                    unit = unit_raw
                    desc = match.group("desc").strip()
                elif qty_raw:
                    desc = " ".join(part for part in [unit_raw, match.group("desc").strip()] if part).strip()

            desc = desc.strip(",. ")

            # --- 5. Classificação Interna / Estoque ---
            context_mode = PurchasesService._purchase_context_mode(context)
            matches = []
            if context_mode != "external":
                matches = StockCatalogService.list_items(db, q=desc, suggest=True, current_user=current_user)
            suggestion, match_score, purchase_type, classification_message = PurchasesService._classify_purchase_text_match(desc, matches)
            if context_mode == "external":
                suggestion = None
                match_score = 0.0
                purchase_type = "external"
                classification_message = "Modo Internet selecionado. Vou tratar como compra externa e pesquisar opcoes de mercado depois da revisao."
            elif context_mode == "internal" and purchase_type == "external":
                purchase_type = "ambiguous"
                classification_message = "Modo Dentro do Portal selecionado, mas nao encontrei item interno seguro. Confirme o cadastro interno ou troque para Internet."
            confidence = "low"
            match_status = "needs_confirmation"
            if suggestion:
                if purchase_type == "internal":
                    confidence = "high"
                    match_status = "confirmed"
                else:
                    confidence = "check"

            # Preencher department a partir do destino de forma básica
            department = None
            if destination:
                dept_lower = destination.lower()
                if "ti" in dept_lower or "computador" in dept_lower or "pc" in dept_lower or "dev" in dept_lower:
                    department = "TI"
                elif "producao" in dept_lower or "produ\u00e7\u00e3o" in dept_lower or "fabrica" in dept_lower:
                    department = "PRODUCAO"
                elif "adm" in dept_lower or "financeiro" in dept_lower:
                    department = "ADMINISTRATIVO"

            parsed.append({
                "raw_text": raw_line,
                "description": desc,
                "quantity": qty,
                "unit_of_measure": unit,
                "confidence": confidence,
                "match_status": match_status,
                "purchase_type": purchase_type,
                "classification_message": classification_message,
                "match_score": match_score,
                "suggested_stock_catalog_item_id": suggestion.get("id") if suggestion else None,
                "suggested_display_name": suggestion.get("display_name") if suggestion else None,
                "suggested_specification": (suggestion.get("specification_text") or suggestion.get("measure_display")) if suggestion else None,
                "destination": destination,
                "department": department,
                "budget_limit": budget_limit,
                "normalized_name": suggestion.get("display_name") if suggestion else desc,
            })
        return parsed

    @staticmethod
    def _relevant_purchase_tokens(value: str) -> set[str]:
        stop_words = {
            "de", "da", "do", "das", "dos", "para", "por", "com", "sem", "ate",
            "um", "uma", "un", "und", "pc", "pcs", "m", "mt", "kg", "cx", "caixa",
            "comprar", "cotar", "preciso", "necessario", "orcamento", "r", "rs",
        }
        tokens = set(PurchasesService._normalize_text(value).split())
        return {token for token in tokens if len(token) >= 2 and token not in stop_words and not token.replace(".", "").isdigit()}

    @staticmethod
    def _purchase_text_match_score(description: str, candidate: Dict[str, Any]) -> float:
        query_tokens = PurchasesService._relevant_purchase_tokens(description)
        candidate_text = " ".join(str(candidate.get(field) or "") for field in [
            "display_name",
            "name",
            "description",
            "specification_text",
            "measure_display",
            "variation_label",
            "cybersul_code",
            "internal_code",
            "family_name",
            "category_name",
        ])
        candidate_tokens = PurchasesService._relevant_purchase_tokens(candidate_text)
        if not query_tokens or not candidate_tokens:
            return 0.0
        overlap = query_tokens & candidate_tokens
        overlap_ratio = len(overlap) / len(query_tokens)
        containment_bonus = 0.18 if PurchasesService._normalize_text(description) in PurchasesService._normalize_text(candidate_text) else 0
        strong_overlap_bonus = 0.12 if len(overlap) >= 2 else 0
        return min(1.0, overlap_ratio + containment_bonus + strong_overlap_bonus)

    @staticmethod
    def _classify_purchase_text_match(description: str, matches: List[Dict[str, Any]]) -> tuple[Optional[Dict[str, Any]], float, str, str]:
        if not matches:
            return None, 0.0, "external", "Nenhum item interno compativel foi encontrado. Vou tratar como compra externa."

        scored = sorted(
            ((item, PurchasesService._purchase_text_match_score(description, item)) for item in matches[:8]),
            key=lambda row: row[1],
            reverse=True,
        )
        best, best_score = scored[0]
        second_score = scored[1][1] if len(scored) > 1 else 0.0
        query_tokens = PurchasesService._relevant_purchase_tokens(description)
        best_tokens = PurchasesService._relevant_purchase_tokens(" ".join(str(best.get(field) or "") for field in [
            "display_name", "name", "description", "specification_text", "measure_display", "variation_label"
        ]))
        overlap = query_tokens & best_tokens

        if best_score >= 0.72 and len(overlap) >= 2 and (best_score - second_score) >= 0.10:
            return best, round(best_score, 3), "internal", "Item interno encontrado com alta confianca."
        if best_score >= 0.52 and len(overlap) >= 2:
            return best, round(best_score, 3), "ambiguous", "Encontrei uma possivel correspondencia no Estoque, mas preciso de confirmacao."
        return None, round(best_score, 3), "external", "Nenhum item interno compativel foi encontrado. Vou tratar como compra externa."

    @staticmethod
    def parse_purchase_need_text(db: Session, payload: Any, current_user: User) -> List[Dict[str, Any]]:
        user_level = ApprovalService.get_user_module_level(db, current_user, "purchases")
        is_admin = current_user.role and current_user.role.name == "ADMIN"
        if LEVEL_VALUES[user_level] < LEVEL_VALUES[PermissionLevel.NORMAL] and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissao insuficiente para preparar necessidade de compra."
            )
        return PurchasesService._parse_purchase_text_lines(db, payload.text, current_user)

    @staticmethod
    def suggest_purchases(db: Session, q: str, context: Optional[str], current_user: User) -> List[Dict[str, Any]]:
        query = (q or "").strip()
        if len(query) < 2:
            return []
        user_level = ApprovalService.get_user_module_level(db, current_user, "purchases")
        is_admin = current_user.role and current_user.role.name == "ADMIN"
        if LEVEL_VALUES[user_level] < LEVEL_VALUES[PermissionLevel.NORMAL] and not is_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permissao insuficiente para consultar sugestoes.")

        suggestions: List[Dict[str, Any]] = []
        seen: set[str] = set()

        def add_suggestion(row: Dict[str, Any]) -> None:
            key = f"{row.get('kind')}:{row.get('id') or row.get('label')}"
            if key in seen:
                return
            seen.add(key)
            suggestions.append(row)

        context_mode = PurchasesService._purchase_context_mode(context)

        if context_mode != "external":
            try:
                stock_matches = StockCatalogService.list_items(db, q=query, suggest=True, current_user=current_user)[:6]
            except Exception:
                stock_matches = []
            for item in stock_matches:
                score = PurchasesService._purchase_text_match_score(query, item)
                add_suggestion({
                    "id": item.get("id"),
                    "label": item.get("display_name") or item.get("name") or query,
                    "kind": "stock_item",
                    "subtitle": item.get("specification_text") or item.get("measure_display") or item.get("family_name"),
                    "confidence": round(score, 3),
                    "stock_catalog_item_id": item.get("id"),
                    "source": "Estoque e Catalogo",
                    "metadata": {
                        "cybersul_code": item.get("cybersul_code"),
                        "family_name": item.get("family_name"),
                        "status": item.get("status"),
                    },
                })

            product_matches = (
                db.query(ProductItem)
                .filter(ProductItem.name.ilike(f"%{query}%"))
                .limit(4)
                .all()
            )
            for item in product_matches:
                add_suggestion({
                    "id": str(item.id),
                    "label": item.name,
                    "kind": "master_product",
                    "subtitle": getattr(item, "description", None),
                    "confidence": 0.65,
                    "stock_catalog_item_id": None,
                    "source": "Cadastro de produtos",
                    "metadata": {"sku": getattr(item, "sku", None), "unit_of_measure": getattr(item, "unit_of_measure", None)},
                })

        assets = (
            db.query(ITAsset)
            .filter(or_(ITAsset.name.ilike(f"%{query}%"), ITAsset.hostname.ilike(f"%{query}%")))
            .limit(3)
            .all()
        )
        for asset in assets:
            add_suggestion({
                "id": str(asset.id),
                "label": asset.name or asset.hostname or "Ativo de TI",
                "kind": "it_asset",
                "subtitle": "Destino possivel para compra de TI",
                "confidence": 0.55,
                "stock_catalog_item_id": None,
                "source": "TI e Ativos",
                "metadata": {"hostname": asset.hostname, "processor": asset.processor, "ram": asset.ram},
            })

        history = (
            db.query(PurchaseRequestItem)
            .filter(PurchaseRequestItem.free_text_description.ilike(f"%{query}%"))
            .order_by(desc(PurchaseRequestItem.created_at))
            .limit(4)
            .all()
        )
        for item in history:
            add_suggestion({
                "id": str(item.id),
                "label": item.free_text_description or item.description,
                "kind": "purchase_history",
                "subtitle": "Item ja solicitado anteriormente",
                "confidence": 0.5,
                "stock_catalog_item_id": item.stock_catalog_item_id,
                "source": "Historico de compras",
                "metadata": {"classification": item.classification, "unit_of_measure": item.unit_of_measure},
            })
        if context_mode == "external" and not suggestions:
            add_suggestion({
                "id": None,
                "label": query,
                "kind": "external_query",
                "subtitle": "Compra externa: a pesquisa de mercado comeca depois da revisao.",
                "confidence": 0.45,
                "stock_catalog_item_id": None,
                "source": "Mercado externo",
                "metadata": {"next_step": "research_after_review"},
            })
        return suggestions[:12]

    @staticmethod
    def analyze_purchase_need(db: Session, payload: Any, current_user: User) -> Dict[str, Any]:
        user_level = ApprovalService.get_user_module_level(db, current_user, "purchases")
        is_admin = current_user.role and current_user.role.name == "ADMIN"
        if LEVEL_VALUES[user_level] < LEVEL_VALUES[PermissionLevel.NORMAL] and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissao insuficiente para preparar necessidade de compra."
            )
        lines = PurchasesService._parse_purchase_text_lines(db, payload.text, current_user, getattr(payload, "context", None))
        draft = PurchaseInterpretedDraft(
            created_by_user_id=current_user.id,
            idempotency_key=getattr(payload, "idempotency_key", None),
            raw_input=payload.text,
            context=getattr(payload, "context", None),
            status="reviewing",
            analysis_summary={
                "total_items": len(lines),
                "internal": sum(1 for line in lines if line.get("purchase_type") == "internal"),
                "external": sum(1 for line in lines if line.get("purchase_type") == "external"),
                "ambiguous": sum(1 for line in lines if line.get("purchase_type") == "ambiguous"),
                "message": "Revise os itens interpretados antes de criar a compra.",
            },
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(draft)
        db.flush()

        confidence_map = {"high": 0.9, "check": 0.62, "low": 0.35}
        draft_items: List[PurchaseInterpretedDraftItem] = []
        for index, line in enumerate(lines):
            item_type = (line.get("purchase_type") or "external").lower()
            stock_catalog_item_id = None
            raw_stock_catalog_item_id = line.get("suggested_stock_catalog_item_id")
            if line.get("purchase_type") in {"internal", "ambiguous"} and raw_stock_catalog_item_id:
                try:
                    candidate_stock_catalog_item_id = uuid.UUID(str(raw_stock_catalog_item_id))
                    if db.query(StockCatalogItem.id).filter(StockCatalogItem.id == candidate_stock_catalog_item_id).first():
                        stock_catalog_item_id = candidate_stock_catalog_item_id
                except (TypeError, ValueError):
                    stock_catalog_item_id = None
            missing_question = None
            if item_type == "ambiguous":
                missing_question = {
                    "question": "Este item deve usar o cadastro interno ou uma compra externa?",
                    "reason": line.get("classification_message"),
                    "choices": ["internal", "external"],
                }
            draft_item = PurchaseInterpretedDraftItem(
                draft_id=draft.id,
                position=index,
                item_type=item_type,
                description=line.get("description") or line.get("raw_text") or "Item",
                quantity=line.get("quantity") or 1,
                unit_of_measure=line.get("unit_of_measure") or "un",
                budget_limit=line.get("budget_limit"),
                destination=line.get("destination"),
                department=line.get("department"),
                confidence_score=confidence_map.get(str(line.get("confidence")), float(line.get("match_score") or 0.4)),
                classification_reason=line.get("classification_message"),
                stock_catalog_item_id=stock_catalog_item_id,
                missing_question_json=missing_question,
                metadata_json=line,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            draft_items.append(draft_item)
            db.add(draft_item)
        db.commit()
        db.refresh(draft)
        return {
            "draft_id": draft.id,
            "status": draft.status,
            "raw_input": draft.raw_input,
            "analysis_summary": draft.analysis_summary or {},
            "items": draft_items,
        }

    @staticmethod
    def _validate_purchase_source_url(raw_url: str) -> Dict[str, str]:
        parsed = urlparse(raw_url.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Informe um link http ou https valido."
            )
        if parsed.username or parsed.password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Links com usuario ou senha nao sao aceitos."
            )
        return {"url": parsed._replace(fragment="").geturl(), "domain": parsed.netloc.lower()}

    @staticmethod
    def preview_purchase_need_link(payload: Any, source_type: str = "external_link") -> Dict[str, Any]:
        from app.modules.purchases.search_provider import get_search_provider, CredentialsMissingException, is_safe_url

        # Trata texto colado ou URL
        is_url = payload.url.strip().startswith("http://") or payload.url.strip().startswith("https://")
        if is_url:
            safe = PurchasesService._validate_purchase_source_url(payload.url)
            url_to_fetch = safe["url"]
            domain_val = safe["domain"]
            
            # Valida segurança da URL contra SSRF
            safe_ok, err_msg = is_safe_url(url_to_fetch)
            if not safe_ok:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"URL bloqueada por segurança: {err_msg}"
                )
        else:
            url_to_fetch = payload.url
            domain_val = "carrinho_copiado"

        label = "link informado" if source_type == "external_link" else "carrinho externo"
        provider = get_search_provider()

        try:
            if source_type == "external_link":
                if not is_url:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Para links de produtos, informe uma URL válida."
                    )
                extracted = provider.fetch_product_url(url_to_fetch)
                # Monta a sugestão de request
                suggested = {
                    "title": f"Compra de {extracted.get('title', 'Produto Externo')}",
                    "description": f"Importado de link externo: {payload.url}",
                    "justification": "Necessidade importada via link do produto pelo assistente inteligente.",
                    "priority": "NORMAL",
                    "urgency": "NORMAL",
                    "items": [{
                        "free_text_description": extracted.get("title"),
                        "normalized_name": extracted.get("title"),
                        "unit_of_measure": "un",
                        "quantity": 1.0,
                        "estimated_unit_price": extracted.get("unit_price", 0.0),
                        "specifications": extracted.get("specifications", ""),
                        "source_type": "MANUAL_LINK",
                        "source_ref_id": payload.url,
                        "classification": "EXTERNAL",
                        "classification_confidence": 1.0,
                        "source_snapshot_json": extracted
                    }]
                }
                return {
                    "source_type": source_type,
                    "source_url": url_to_fetch,
                    "source_domain": domain_val,
                    "status": "success",
                    "title": "Compra a partir de link",
                    "message": "Metadados do produto importados com sucesso! Revise e confirme abaixo.",
                    "can_create_request": True,
                    "suggested_request": suggested
                }
            else:
                # Carrinho
                try:
                    items = provider.import_cart(url_to_fetch)
                except ValueError as ve:
                    # Caso de carrinho privado ou formato inválido
                    return {
                        "source_type": source_type,
                        "source_url": url_to_fetch,
                        "source_domain": domain_val,
                        "status": "auth_required",
                        "title": "Acesso ao Carrinho Exigido",
                        "message": (
                            "Este parece ser um carrinho privado que exige login na loja. "
                            "Cole o texto copiado do carrinho na caixa de texto abaixo para importar os itens de forma assistida."
                        ),
                        "can_create_request": False,
                        "suggested_request": None
                    }
                
                if not items:
                    return {
                        "source_type": source_type,
                        "source_url": url_to_fetch,
                        "source_domain": domain_val,
                        "status": "auth_required",
                        "title": "Acesso ao Carrinho Exigido",
                        "message": "Nenhum item público foi extraído. Cole o texto copiado do carrinho para prosseguir de forma assistida.",
                        "can_create_request": False,
                        "suggested_request": None
                    }

                # Mapeia múltiplos itens
                suggested_items = []
                for item in items:
                    suggested_items.append({
                        "free_text_description": item.get("title"),
                        "normalized_name": item.get("title"),
                        "unit_of_measure": "un",
                        "quantity": float(item.get("quantity", 1.0)),
                        "estimated_unit_price": item.get("unit_price", 0.0),
                        "specifications": item.get("specifications", ""),
                        "source_type": "CART_IMPORT",
                        "source_ref_id": payload.url if is_url else "Texto copiado",
                        "classification": "EXTERNAL",
                        "classification_confidence": 1.0,
                        "source_snapshot_json": item
                    })
                
                suggested = {
                    "title": f"Importação de Carrinho - {domain_val}",
                    "description": f"Carrinho importado de {payload.url if is_url else 'texto copiado'}",
                    "justification": "Necessidade importada de carrinho externo.",
                    "priority": "NORMAL",
                    "urgency": "NORMAL",
                    "items": suggested_items
                }
                
                return {
                    "source_type": source_type,
                    "source_url": url_to_fetch,
                    "source_domain": domain_val,
                    "status": "success",
                    "title": "Carrinho Importado",
                    "message": f"Extraímos {len(items)} itens do carrinho. Revise abaixo.",
                    "can_create_request": True,
                    "suggested_request": suggested
                }
        except CredentialsMissingException as e:
            return {
                "source_type": source_type,
                "source_url": url_to_fetch,
                "source_domain": domain_val,
                "status": "credentials_missing",
                "title": "Credenciais Ausentes",
                "message": (
                    f"A busca externa exige credenciais configuradas: {', '.join(e.missing_keys)}. "
                    "Por favor, configure o arquivo .env no servidor do Portal."
                ),
                "can_create_request": False,
                "suggested_request": None
            }
        except Exception as ex:
            return {
                "source_type": source_type,
                "source_url": url_to_fetch,
                "source_domain": domain_val,
                "status": "error",
                "title": "Falha na Importação",
                "message": f"Erro operacional ao analisar o link: {str(ex)}",
                "can_create_request": False,
                "suggested_request": None
            }

    @staticmethod
    def update_purchase_request(db: Session, request_id: uuid.UUID, payload: Any, current_user: User) -> PurchaseRequest:
        request = PurchasesService.get_purchase_request(db, request_id, current_user)
        
        if request.status != "DRAFT":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Apenas requisicoes em DRAFT podem ser editadas."
            )

        payload_dict = payload.model_dump(exclude_unset=True)
        item_updates = payload_dict.pop("items", None) or []
        if "priority" in payload_dict and "urgency" not in payload_dict:
            payload_dict["urgency"] = payload_dict["priority"]
        elif "urgency" in payload_dict and "priority" not in payload_dict:
            payload_dict["priority"] = payload_dict["urgency"]

        for field, value in payload_dict.items():
            setattr(request, field, value)

        if item_updates:
            request_items = {str(item.id): item for item in request.items}
            allowed_item_fields = {
                "stock_catalog_item_id",
                "free_text_description",
                "quantity",
                "unit_of_measure",
                "specifications",
                "estimated_unit_price",
                "match_status",
                "normalized_name",
                "destination",
                "department",
                "budget_limit",
                "classification",
                "classification_confidence",
                "requires_approval",
            }
            for item_update in item_updates:
                item_id = str(item_update.get("id"))
                item = request_items.get(item_id)
                if not item:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Um dos itens informados nao pertence a esta compra."
                    )
                for field, value in item_update.items():
                    if field == "id" or field not in allowed_item_fields:
                        continue
                    if field == "classification" and value:
                        value = str(value).upper()
                    if field == "match_status" and value is None:
                        value = "confirmed"
                    setattr(item, field, value)
                if item.classification in {"EXTERNAL", "INTERNAL"}:
                    item.match_status = "confirmed"
                item.updated_at = datetime.now(timezone.utc)

            request.estimated_total = sum(
                float(item.estimated_unit_price or 0.0) * float(item.quantity or 0.0)
                for item in request.items
            )

        request.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(request)

        log_action(
            db=db,
            user_id=current_user.id,
            action="purchases.request.updated",
            module="purchases",
            details={"request_id": str(request.id)}
        )

        try:
            emit_event(
                db=db,
                event_type="purchase.request.updated",
                aggregate_type="purchase_request",
                aggregate_id=str(request.id),
                module="purchases",
                payload={
                    "id": str(request.id),
                    "title": request.title,
                    "requester_user_id": request.requester_user_id,
                    "status": request.status,
                    "action_url": f"/purchases?request={request.id}",
                    "summary": f"Requisição de compra '{request.title}' foi atualizada."
                },
                actor_user_id=current_user.id
            )
            db.commit()
        except Exception as e:
            print(f"Failed to emit purchase.request.updated: {e}")

        return request

    @staticmethod
    async def send_to_approval(db: Session, request_id: uuid.UUID, current_user: User) -> PurchaseRequest:
        request = PurchasesService.get_purchase_request(db, request_id, current_user)
        if request.status != "DRAFT":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Apenas requisições em rascunho (DRAFT) podem ser enviadas para aprovação."
            )
        
        # Se for menor que R$ 1.000,00, auto-aprova
        if float(request.estimated_total or 0.0) < 1000.0:
            request.status = "APPROVED"
            request.approved_total = request.estimated_total
            request.updated_at = datetime.now(timezone.utc)
            for item in request.items:
                item.approval_status = "APPROVED"
            db.commit()
            
            # Registrar atividade
            activity = PurchaseActivity(
                purchase_request_id=request.id,
                user_id=current_user.id,
                action="request.approved",
                details={"auto_approved": True, "reason": "Valor estimado abaixo de R$ 1.000,00."},
                created_at=datetime.now(timezone.utc)
            )
            db.add(activity)
            db.commit()
            await trigger_dashboard_update()
            return request
        
        # Caso contrário, cria uma solicitação de aprovação na Central de Aprovações
        from app.modules.approvals.service import ApprovalService
        from app.modules.approvals.schemas import ApprovalCreate
        
        approval_items = []
        for item in request.items:
            item_options = []
            for option in getattr(item, "options", []) or []:
                item_options.append({
                    "option_id": str(option.id),
                    "title": option.title,
                    "store_name": option.store_name,
                    "seller_name": option.seller_name,
                    "unit_price": float(option.unit_price or 0.0),
                    "shipping_price": float(option.shipping_price or 0.0),
                    "total_price": float(option.total_price or 0.0),
                    "delivery_estimate": option.delivery_estimate,
                    "product_url": option.product_url,
                    "selected": bool(option.selected),
                })
            selected_option = next((option for option in item_options if option["selected"]), None)
            approval_items.append({
                "item_id": str(item.id),
                "description": item.free_text_description or item.description,
                "quantity": float(item.quantity),
                "unit": item.unit_of_measure or "un",
                "classification": item.classification or "EXTERNAL",
                "budget_limit": float(item.budget_limit) if item.budget_limit is not None else None,
                "estimated_unit_price": float(item.estimated_unit_price or 0.0),
                "selected_option_id": selected_option["option_id"] if selected_option else (str(item.selected_option_id) if item.selected_option_id else None),
                "options": item_options,
            })

        # Cria a solicitação
        approval_payload = ApprovalCreate(
            title=f"Liberação Financeira: {request.title}",
            description=request.description or f"Requisição de compra para {request.title}",
            module_slug="purchases",
            risk_level="MEDIUM",
            action_type="FINANCIAL_RELEASE",
            action_payload={
                "request_type": "purchase_options",
                "request_id": str(request.id),
                "title": request.title,
                "estimated_total": float(request.estimated_total or 0.0),
                "items": approval_items,
                "return_url": f"/purchases?request={request.id}",
            },
            expires_at=(datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        )
        
        approval = ApprovalService.create_approval(db, approval_payload, current_user)
        
        request.status = "PENDING_APPROVAL"
        request.approval_id = approval.id
        request.updated_at = datetime.now(timezone.utc)
        db.commit()
        
        # Registrar atividade
        activity = PurchaseActivity(
            purchase_request_id=request.id,
            user_id=current_user.id,
            action="request.submitted",
            details={"approval_id": approval.id},
            created_at=datetime.now(timezone.utc)
        )
        db.add(activity)
        db.commit()
        await trigger_dashboard_update()
        return request

    @staticmethod
    async def cancel_purchase_request(db: Session, request_id: uuid.UUID, current_user: User) -> PurchaseRequest:
        request = PurchasesService.get_purchase_request(db, request_id, current_user)
        if request.status in ["ORDERED", "DELIVERED", "CANCELLED"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Não é possível cancelar uma requisição com status: {request.status}"
            )
        
        # Cancela aprovação pendente se houver
        if request.status == "PENDING_APPROVAL" and request.approval_id:
            from app.modules.approvals.service import ApprovalService
            try:
                ApprovalService.cancel_approval(db, request.approval_id, current_user)
            except Exception as e:
                print(f"Failed to cancel associated approval {request.approval_id}: {e}")
                
        request.status = "CANCELLED"
        request.updated_at = datetime.now(timezone.utc)
        db.commit()
        
        # Registrar atividade
        activity = PurchaseActivity(
            purchase_request_id=request.id,
            user_id=current_user.id,
            action="request.cancelled",
            details={},
            created_at=datetime.now(timezone.utc)
        )
        db.add(activity)
        db.commit()
        await trigger_dashboard_update()
        return request

    @staticmethod
    def add_item_to_request(db: Session, request_id: uuid.UUID, item_data: Any, current_user: User) -> PurchaseRequestItem:
        request = PurchasesService.get_purchase_request(db, request_id, current_user)
        if request.status not in {"DRAFT", "RFQ_PREPARING"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Apenas cotacoes em preparacao podem ter itens adicionados."
            )

        desc_val = item_data.free_text_description or item_data.description
        unit_val = item_data.unit_of_measure or item_data.unit or "un"
        specs_val = item_data.specifications or item_data.notes

        stock_catalog_item_id = getattr(item_data, "stock_catalog_item_id", None)

        if not item_data.item_id and not item_data.service_id and not stock_catalog_item_id and not desc_val:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Item de requisicao precisa ter item_id, service_id, stock_catalog_item_id ou free_text_description."
            )

        if item_data.item_id:
            p_item = db.query(ProductItem).filter(ProductItem.id == item_data.item_id, ProductItem.is_active == True).first()
            if not p_item:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Item {item_data.item_id} nao existe no Master Data."
                )
        if item_data.service_id:
            srv = db.query(Service).filter(Service.id == item_data.service_id, Service.is_active == True).first()
            if not srv:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Servico {item_data.service_id} nao existe no Master Data."
                )
        if stock_catalog_item_id:
            stock_item = db.query(StockCatalogItem).filter(StockCatalogItem.id == stock_catalog_item_id).first()
            if not stock_item:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Item {stock_catalog_item_id} nao existe no Estoque & Catalogo."
                )

        item_price = float(item_data.estimated_unit_price or 0.0)
        item_qty = float(item_data.quantity)

        new_item = PurchaseRequestItem(
            purchase_request_id=request.id,
            item_id=item_data.item_id,
            service_id=item_data.service_id,
            stock_catalog_item_id=stock_catalog_item_id,
            free_text_description=desc_val,
            quantity=item_qty,
            unit_of_measure=unit_val,
            specifications=specs_val,
            estimated_unit_price=item_price,
            source_type=getattr(item_data, "source_type", None),
            source_ref_id=getattr(item_data, "source_ref_id", None),
            source_confidence=getattr(item_data, "source_confidence", None),
            match_status=getattr(item_data, "match_status", "confirmed") or "confirmed",
            source_snapshot_json=getattr(item_data, "source_snapshot_json", None),
            normalized_name=getattr(item_data, "normalized_name", None) or desc_val,
            destination=getattr(item_data, "destination", None),
            department=getattr(item_data, "department", None),
            budget_limit=getattr(item_data, "budget_limit", None),
            classification=getattr(item_data, "classification", "EXTERNAL") or "EXTERNAL",
            classification_confidence=getattr(item_data, "classification_confidence", None),
            requires_approval=bool(getattr(item_data, "requires_approval", False)),
            approval_status=getattr(item_data, "approval_status", "PENDING") or "PENDING",
            purchasing_status=getattr(item_data, "purchasing_status", "PENDING") or "PENDING",
            delivery_status=getattr(item_data, "delivery_status", "PENDING") or "PENDING",
            created_at=datetime.now(timezone.utc)
        )
        db.add(new_item)
        
        # Atualiza valor total estimativo
        request.estimated_total = float(request.estimated_total or 0.0) + (item_price * item_qty)
        request.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(new_item)

        log_action(
            db=db,
            user_id=current_user.id,
            action="purchases.item.added",
            module="purchases",
            details={"request_id": str(request.id), "item_id": str(new_item.id)}
        )
        return new_item

    @staticmethod
    def _ensure_item_can_be_changed(item: PurchaseRequestItem, request: PurchaseRequest, *, destructive: bool = False) -> None:
        if request.status not in {"DRAFT", "NEEDS_REVIEW"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este item ja saiu da revisao segura. Use cancelar ou arquivar para preservar a auditoria.",
            )
        if destructive and (
            item.requires_approval
            or item.approval_status not in {None, "", "PENDING"}
            or item.purchasing_status not in {None, "", "PENDING"}
            or item.delivery_status not in {None, "", "PENDING"}
            or item.options
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este item ja possui fluxo operacional. Ele nao pode ser apagado sem auditoria; cancele ou arquive a necessidade.",
            )

    @staticmethod
    def update_request_item(db: Session, item_id: uuid.UUID, payload: Any, current_user: User) -> PurchaseRequestItem:
        item = db.query(PurchaseRequestItem).filter(PurchaseRequestItem.id == item_id).first()
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item da requisicao nao encontrado."
            )

        request = PurchasesService.get_purchase_request(db, item.purchase_request_id, current_user)
        PurchasesService._ensure_item_can_be_changed(item, request)

        old_subtotal = float(item.estimated_unit_price or 0.0) * float(item.quantity)
        
        payload_dict = payload.model_dump(exclude_unset=True)
        # Mapeamento retrocompatível
        if "description" in payload_dict and "free_text_description" not in payload_dict:
            payload_dict["free_text_description"] = payload_dict["description"]
        if "unit" in payload_dict and "unit_of_measure" not in payload_dict:
            payload_dict["unit_of_measure"] = payload_dict["unit"]
        if "notes" in payload_dict and "specifications" not in payload_dict:
            payload_dict["specifications"] = payload_dict["notes"]

        for field, value in payload_dict.items():
            if hasattr(item, field):
                setattr(item, field, value)

        new_subtotal = float(item.estimated_unit_price or 0.0) * float(item.quantity)
        
        # Corrige total estimativo da requisição
        request.estimated_total = float(request.estimated_total or 0.0) - old_subtotal + new_subtotal
        request.updated_at = datetime.now(timezone.utc)
        
        db.commit()
        db.refresh(item)

        log_action(
            db=db,
            user_id=current_user.id,
            action="purchases.item.updated",
            module="purchases",
            details={"request_id": str(request.id), "item_id": str(item.id)}
        )
        return item

    @staticmethod
    def delete_request_item(db: Session, item_id: uuid.UUID, current_user: User) -> Dict[str, Any]:
        item = db.query(PurchaseRequestItem).filter(PurchaseRequestItem.id == item_id).first()
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item da requisicao nao encontrado."
            )

        request = PurchasesService.get_purchase_request(db, item.purchase_request_id, current_user)
        PurchasesService._ensure_item_can_be_changed(item, request, destructive=True)

        subtotal = float(item.estimated_unit_price or 0.0) * float(item.quantity)
        request.estimated_total = max(0.0, float(request.estimated_total or 0.0) - subtotal)
        request.updated_at = datetime.now(timezone.utc)
        removed_snapshot = {
            "id": item.id,
            "purchase_request_id": item.purchase_request_id,
            "item_id": item.item_id,
            "service_id": item.service_id,
            "stock_catalog_item_id": item.stock_catalog_item_id,
            "free_text_description": item.free_text_description,
            "quantity": item.quantity,
            "unit_of_measure": item.unit_of_measure,
            "specifications": item.specifications,
            "estimated_unit_price": item.estimated_unit_price,
            "source_type": item.source_type,
            "source_ref_id": item.source_ref_id,
            "source_confidence": item.source_confidence,
            "match_status": item.match_status,
            "source_snapshot_json": item.source_snapshot_json,
            "created_at": item.created_at,
            "normalized_name": item.normalized_name,
            "destination": item.destination,
            "department": item.department,
            "budget_limit": item.budget_limit,
            "classification": item.classification,
            "classification_confidence": item.classification_confidence,
            "selected_option_id": item.selected_option_id,
            "requires_approval": item.requires_approval,
            "approval_status": item.approval_status,
            "purchasing_status": item.purchasing_status,
            "delivery_status": item.delivery_status,
            "options": [],
            "description": item.free_text_description or "",
            "unit": item.unit_of_measure or "un",
            "notes": item.specifications,
        }
        
        db.delete(item)
        db.commit()

        log_action(
            db=db,
            user_id=current_user.id,
            action="purchases.item.deleted",
            module="purchases",
            details={"request_id": str(request.id), "item_id": str(item_id)}
        )
        return removed_snapshot

    @staticmethod
    def split_request_item(db: Session, item_id: uuid.UUID, payload: Any, current_user: User) -> PurchaseRequestItem:
        item = db.query(PurchaseRequestItem).filter(PurchaseRequestItem.id == item_id).first()
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item da requisicao nao encontrado.")
        request = PurchasesService.get_purchase_request(db, item.purchase_request_id, current_user)
        PurchasesService._ensure_item_can_be_changed(item, request)

        first_quantity = float(payload.first_quantity)
        original_quantity = float(item.quantity)
        if first_quantity >= original_quantity:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A primeira quantidade deve ser menor que a quantidade atual.")
        second_quantity = float(getattr(payload, "second_quantity", None) or (original_quantity - first_quantity))
        if second_quantity <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A segunda quantidade precisa ser maior que zero.")

        item.quantity = first_quantity
        new_item = PurchaseRequestItem(
            purchase_request_id=request.id,
            item_id=item.item_id,
            service_id=item.service_id,
            stock_catalog_item_id=item.stock_catalog_item_id,
            free_text_description=getattr(payload, "second_description", None) or item.free_text_description,
            quantity=second_quantity,
            unit_of_measure=item.unit_of_measure,
            specifications=item.specifications,
            estimated_unit_price=item.estimated_unit_price,
            source_type=item.source_type,
            source_ref_id=item.source_ref_id,
            source_confidence=item.source_confidence,
            match_status=item.match_status,
            source_snapshot_json=item.source_snapshot_json,
            normalized_name=item.normalized_name,
            destination=item.destination,
            department=item.department,
            budget_limit=item.budget_limit,
            classification=item.classification,
            classification_confidence=item.classification_confidence,
            requires_approval=False,
            approval_status="PENDING",
            purchasing_status="PENDING",
            delivery_status="PENDING",
            created_at=datetime.now(timezone.utc),
        )
        request.updated_at = datetime.now(timezone.utc)
        db.add(new_item)
        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def merge_request_items(db: Session, payload: Any, current_user: User) -> PurchaseRequestItem:
        item_ids = list(getattr(payload, "item_ids", []) or [])
        if len(item_ids) < 2:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Selecione ao menos dois itens para unir.")
        items = db.query(PurchaseRequestItem).filter(PurchaseRequestItem.id.in_(item_ids)).all()
        if len(items) != len(item_ids):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Um ou mais itens nao foram encontrados.")
        request = PurchasesService.get_purchase_request(db, items[0].purchase_request_id, current_user)
        if any(item.purchase_request_id != request.id for item in items):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="So e possivel unir itens da mesma compra.")
        for item in items:
            PurchasesService._ensure_item_can_be_changed(item, request, destructive=item.id != items[0].id)

        primary = items[0]
        primary.quantity = sum(float(item.quantity or 0) for item in items)
        primary.free_text_description = getattr(payload, "description", None) or primary.free_text_description
        primary.updated_at = datetime.now(timezone.utc)
        for item in items[1:]:
            db.delete(item)
        request.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(primary)
        return primary

    @staticmethod
    def get_request_item(db: Session, item_id: uuid.UUID, current_user: User) -> PurchaseRequestItem:
        item = db.query(PurchaseRequestItem).filter(PurchaseRequestItem.id == item_id).first()
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item da requisicao nao encontrado."
            )
        # Valida visibilidade
        PurchasesService.get_purchase_request(db, item.purchase_request_id, current_user)
        return item

    @staticmethod
    def _sender_account_defaults() -> List[Dict[str, Any]]:
        return [
            {
                "id": "vesper",
                "company": "Vesper",
                "email": "compras@portal.example",
                "display_name": "Compras Vesper",
                "status": "not_configured",
                "default_bcc": "compras@portal.example",
                "secret_ref": "vault://purchases/smtp/vesper",
                "sent_folder": "Enviados/Compras",
                "monitored_folder": "INBOX",
                "signature_name": "Assinatura Compras Vesper",
                "signature_html": "<p>Atenciosamente,<br><strong>Compras Vesper</strong><br>compras@portal.example</p>",
                "signature_text": "Atenciosamente,\nCompras Vesper\ncompras@portal.example",
            },
            {
                "id": "ventrio",
                "company": "Ventrio",
                "email": "compras@empresa-parceira.example",
                "display_name": "Compras Empresa Parceira",
                "status": "not_configured",
                "default_bcc": "compras@empresa-parceira.example",
                "secret_ref": "vault://purchases/smtp/ventrio",
                "sent_folder": "Enviados/Compras",
                "monitored_folder": "INBOX",
                "signature_name": "Assinatura Compras Empresa Parceira",
                "signature_html": "<p>Atenciosamente,<br><strong>Compras Empresa Parceira</strong><br>compras@empresa-parceira.example</p>",
                "signature_text": "Atenciosamente,\nCompras Empresa Parceira\ncompras@empresa-parceira.example",
            },
        ]

    @staticmethod
    def _mask_secret_ref(secret_ref: Optional[str]) -> Optional[str]:
        if not secret_ref:
            return None
        parts = secret_ref.split("/")
        if len(parts) <= 1:
            return "***"
        return "/".join([*parts[:-1], f"***{parts[-1][-3:]}"])

    @staticmethod
    def _ensure_default_sender_accounts(db: Session) -> None:
        changed = False
        for item in PurchasesService._sender_account_defaults():
            account = db.get(PurchaseSenderAccount, item["id"])
            if not account:
                account = PurchaseSenderAccount(
                    id=item["id"],
                    company=item["company"],
                    email=item["email"],
                    display_name=item["display_name"],
                    status=item["status"],
                    bcc_default_enabled=True,
                    default_bcc=item["default_bcc"],
                    secret_ref=item["secret_ref"],
                    has_secret=False,
                    sent_folder=item["sent_folder"],
                    monitored_folder=item["monitored_folder"],
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                db.add(account)
                changed = True
            signature = db.query(PurchaseSenderSignature).filter(
                PurchaseSenderSignature.account_id == item["id"],
                PurchaseSenderSignature.is_default == True,
                PurchaseSenderSignature.is_active == True,
            ).first()
            if not signature:
                db.add(PurchaseSenderSignature(
                    account_id=item["id"],
                    signature_name=item["signature_name"],
                    html_content=item["signature_html"],
                    text_content=item["signature_text"],
                    is_default=True,
                    is_active=True,
                    updated_at=datetime.now(timezone.utc),
                ))
                changed = True
        if changed:
            db.commit()

    @staticmethod
    def _sender_account_payload(account: PurchaseSenderAccount) -> Dict[str, Any]:
        return {
            "id": account.id,
            "company": account.company,
            "email": account.email,
            "display_name": account.display_name,
            "status": account.status,
            "bcc_default_enabled": bool(account.bcc_default_enabled),
            "default_bcc": account.default_bcc,
            "secret_ref_masked": PurchasesService._mask_secret_ref(account.secret_ref),
            "has_secret": bool(account.has_secret),
            "is_configured": bool(account.has_secret and account.status == "configured"),
            "provider": "smtp",
            "sent_folder": account.sent_folder,
            "monitored_folder": account.monitored_folder,
            "last_test_at": account.last_test_at,
            "last_error": account.last_error,
        }

    @staticmethod
    def sender_accounts(db: Session, current_user: Optional[User] = None) -> List[Dict[str, Any]]:
        PurchasesService._ensure_default_sender_accounts(db)
        accounts = db.query(PurchaseSenderAccount).order_by(PurchaseSenderAccount.company).all()
        return [PurchasesService._sender_account_payload(account) for account in accounts]

    @staticmethod
    def get_sender_account(db: Session, account_id: str, current_user: User) -> Dict[str, Any]:
        PurchasesService._ensure_default_sender_accounts(db)
        account = db.get(PurchaseSenderAccount, account_id)
        if not account:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conta remetente nao encontrada.")
        return PurchasesService._sender_account_payload(account)

    @staticmethod
    def _require_sender_account_manager(db: Session, current_user: User) -> None:
        is_admin = bool(current_user.role and current_user.role.name in {"ADMIN", "MESSIAS"})
        user_level = ApprovalService.get_user_module_level(db, current_user, "purchases")
        if not is_admin and LEVEL_VALUES[user_level] < LEVEL_VALUES[PermissionLevel.ADMIN]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Apenas administradores podem configurar contas de Compras.")

    @staticmethod
    def create_sender_account(db: Session, payload: Any, current_user: User) -> Dict[str, Any]:
        PurchasesService._require_sender_account_manager(db, current_user)
        existing = db.get(PurchaseSenderAccount, payload.id)
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Conta remetente ja existe.")
        account = PurchaseSenderAccount(
            id=payload.id,
            company=payload.company,
            email=payload.email,
            display_name=payload.display_name,
            status=payload.status,
            bcc_default_enabled=payload.bcc_default_enabled,
            default_bcc=payload.default_bcc,
            secret_ref=payload.secret_ref,
            has_secret=payload.has_secret,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(account)
        db.commit()
        return PurchasesService._sender_account_payload(account)

    @staticmethod
    def update_sender_account(db: Session, account_id: str, payload: Any, current_user: User) -> Dict[str, Any]:
        PurchasesService._require_sender_account_manager(db, current_user)
        PurchasesService._ensure_default_sender_accounts(db)
        account = db.get(PurchaseSenderAccount, account_id)
        if not account:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conta remetente nao encontrada.")
        data = payload.model_dump(exclude_unset=True)
        for field in [
            "company", "email", "display_name", "status", "bcc_default_enabled",
            "default_bcc", "secret_ref", "has_secret", "sent_folder", "monitored_folder",
        ]:
            if field in data:
                setattr(account, field, data[field])
        account.updated_at = datetime.now(timezone.utc)
        db.commit()
        return PurchasesService._sender_account_payload(account)

    @staticmethod
    def test_sender_account(db: Session, account_id: str, current_user: User) -> Dict[str, Any]:
        PurchasesService._require_sender_account_manager(db, current_user)
        PurchasesService._ensure_default_sender_accounts(db)
        account = db.get(PurchaseSenderAccount, account_id)
        if not account:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conta remetente nao encontrada.")
        account.last_test_at = datetime.now(timezone.utc)
        if not account.has_secret and settings.ENVIRONMENT.lower() != "testing":
            account.status = "not_configured"
            account.last_error = f"A conta {account.email} ainda nao esta configurada no cofre."
            db.commit()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=account.last_error)
        account.last_error = None
        db.commit()
        return PurchasesService._sender_account_payload(account)

    @staticmethod
    def disable_sender_account(db: Session, account_id: str, current_user: User) -> Dict[str, Any]:
        PurchasesService._require_sender_account_manager(db, current_user)
        account = db.get(PurchaseSenderAccount, account_id)
        if not account:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conta remetente nao encontrada.")
        account.status = "disabled"
        account.updated_at = datetime.now(timezone.utc)
        db.commit()
        return PurchasesService._sender_account_payload(account)

    @staticmethod
    def _normalize_text(value: Optional[str]) -> str:
        ascii_value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
        return re.sub(r"[^a-z0-9]+", " ", ascii_value.lower()).strip()

    @staticmethod
    def _json_safe(value: Any) -> Any:
        if isinstance(value, uuid.UUID):
            return str(value)
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, dict):
            return {key: PurchasesService._json_safe(item) for key, item in value.items()}
        if isinstance(value, list):
            return [PurchasesService._json_safe(item) for item in value]
        return value

    @staticmethod
    def _stock_item_snapshot(db: Session, stock_catalog_item_id: uuid.UUID) -> Dict[str, Any]:
        details = StockCatalogService.get_item_details(db, stock_catalog_item_id)
        if not details:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto do catalogo nao encontrado.")
        offers = StockCatalogService.get_item_offers(db, stock_catalog_item_id)
        details["offers"] = offers
        return PurchasesService._json_safe(details)

    @staticmethod
    def _quote_item_description(item: PurchaseRequestItem) -> str:
        if item.free_text_description:
            return item.free_text_description
        if item.stock_catalog_item:
            return item.stock_catalog_item.display_name
        if item.product_item:
            return item.product_item.name
        if item.service:
            return item.service.name
        return "Item sem descricao"

    @staticmethod
    def _quote_detail_payload(rfq: PurchaseRFQ) -> Dict[str, Any]:
        request = rfq.purchase_request
        return {
            "id": rfq.id,
            "purchase_request_id": request.id,
            "title": rfq.title,
            "description": request.description,
            "status": rfq.status,
            "origin_type": request.origin_type,
            "origin_ref_id": request.origin_ref_id,
            "origin_snapshot_json": request.origin_snapshot_json,
            "items": request.items,
            "suppliers": rfq.rfq_suppliers,
            "created_at": rfq.created_at,
            "updated_at": rfq.updated_at,
        }

    @staticmethod
    def create_quote(db: Session, payload: Any, current_user: User) -> Dict[str, Any]:
        user_level = ApprovalService.get_user_module_level(db, current_user, "purchases")
        is_admin = current_user.role and current_user.role.name == "ADMIN"
        if LEVEL_VALUES[user_level] < LEVEL_VALUES[PermissionLevel.NORMAL] and not is_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permissao insuficiente para criar cotacao.")

        request = PurchaseRequest(
            title=payload.title,
            description=payload.description,
            requester_user_id=current_user.id,
            status="RFQ_PREPARING",
            priority="NORMAL",
            urgency="NORMAL",
            origin_type=payload.origin_type,
            origin_ref_id=payload.origin_ref_id,
            origin_snapshot_json=payload.origin_snapshot_json,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(request)
        db.flush()

        rfq = PurchaseRFQ(
            purchase_request_id=request.id,
            title=payload.title,
            status="DRAFT",
            created_by_user_id=current_user.id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(rfq)
        db.flush()

        db.add(PurchaseActivity(
            purchase_request_id=request.id,
            user_id=current_user.id,
            action="quote.created",
            details={"rfq_id": str(rfq.id), "origin_type": payload.origin_type},
            created_at=datetime.now(timezone.utc),
        ))
        db.commit()
        db.refresh(rfq)
        return PurchasesService._quote_detail_payload(PurchasesService.get_rfq(db, rfq.id, current_user))

    @staticmethod
    def get_quote_detail(db: Session, rfq_id: uuid.UUID, current_user: User) -> Dict[str, Any]:
        return PurchasesService._quote_detail_payload(PurchasesService.get_rfq(db, rfq_id, current_user))

    @staticmethod
    def update_quote(db: Session, rfq_id: uuid.UUID, payload: Any, current_user: User) -> Dict[str, Any]:
        rfq = PurchasesService.get_rfq(db, rfq_id, current_user)
        data = payload.model_dump(exclude_unset=True)
        allowed_status = {"DRAFT", "READY_FOR_REVIEW", "CANCELLED"}
        if "title" in data and data["title"]:
            rfq.title = data["title"]
            rfq.purchase_request.title = data["title"]
        if "description" in data:
            rfq.purchase_request.description = data["description"]
        if "status" in data and data["status"]:
            if data["status"] not in allowed_status:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Status nao permitido para edicao da cotacao.")
            rfq.status = data["status"]
        rfq.updated_at = datetime.now(timezone.utc)
        rfq.purchase_request.updated_at = datetime.now(timezone.utc)
        db.commit()
        return PurchasesService._quote_detail_payload(PurchasesService.get_rfq(db, rfq_id, current_user))

    @staticmethod
    def add_quote_item(db: Session, rfq_id: uuid.UUID, payload: Any, current_user: User) -> PurchaseRequestItem:
        rfq = PurchasesService.get_rfq(db, rfq_id, current_user)
        return PurchasesService.add_item_to_request(db, rfq.purchase_request_id, payload, current_user)

    @staticmethod
    def create_quote_from_stock_item(db: Session, stock_catalog_item_id: uuid.UUID, current_user: User) -> Dict[str, Any]:
        open_request_statuses = {
            "DRAFT",
            "REQUESTED",
            "RFQ_PREPARING",
            "RFQ_SENT",
            "QUOTES_RECEIVED",
            "COMPARING",
            "APPROVAL_REQUIRED",
            "APPROVED",
        }
        open_rfq_statuses = {
            "DRAFT",
            "READY_FOR_REVIEW",
            "PENDING_APPROVAL",
            "APPROVED_TO_SEND",
            "SENT",
            "RESPONSES_RECEIVED",
        }
        existing = (
            db.query(PurchaseRFQ)
            .join(PurchaseRequest, PurchaseRequest.id == PurchaseRFQ.purchase_request_id)
            .join(PurchaseRequestItem, PurchaseRequestItem.purchase_request_id == PurchaseRequest.id)
            .filter(
                PurchaseRequestItem.stock_catalog_item_id == stock_catalog_item_id,
                PurchaseRequest.status.in_(open_request_statuses),
                PurchaseRFQ.status.in_(open_rfq_statuses),
            )
            .order_by(desc(PurchaseRFQ.updated_at))
            .first()
        )
        if existing:
            quote = PurchasesService.get_quote_detail(db, existing.id, current_user)
            quote_items = quote.get("items") or []
            first_item = quote_items[0] if quote_items else None
            created_item_id = getattr(first_item, "id", None)
            if created_item_id is None and isinstance(first_item, dict):
                created_item_id = first_item.get("id")
            return {
                **quote,
                "quote_id": quote["id"],
                "request_id": quote["purchase_request_id"],
                "existing_quote": True,
                "created_item_id": created_item_id,
                "action_url": f"/purchases?quote={quote['id']}&step=products",
                "message": "Ja existe uma cotacao em andamento para este item.",
            }

        snapshot = PurchasesService._stock_item_snapshot(db, stock_catalog_item_id)
        title = f"Cotacao - {snapshot.get('display_name') or 'Produto do catalogo'}"
        quote = PurchasesService.create_quote(db, type("Payload", (), {
            "title": title[:255],
            "description": "Cotacao criada a partir do Estoque & Catalogo.",
            "origin_type": "stock_catalog",
            "origin_ref_id": str(stock_catalog_item_id),
            "origin_snapshot_json": snapshot,
        })(), current_user)
        item_payload = type("ItemPayload", (), {
            "item_id": None,
            "service_id": None,
            "stock_catalog_item_id": stock_catalog_item_id,
            "free_text_description": snapshot.get("display_name"),
            "description": snapshot.get("display_name"),
            "quantity": 1,
            "unit_of_measure": snapshot.get("unit") or "un",
            "unit": snapshot.get("unit") or "un",
            "specifications": snapshot.get("specification_text") or snapshot.get("measure_display") or snapshot.get("variation_label"),
            "notes": snapshot.get("specification_text") or snapshot.get("measure_display") or snapshot.get("variation_label"),
            "estimated_unit_price": snapshot.get("current_price"),
            "source_type": "stock_catalog",
            "source_ref_id": str(stock_catalog_item_id),
            "source_confidence": "high",
            "match_status": "confirmed",
            "source_snapshot_json": snapshot,
        })()
        item = PurchasesService.add_quote_item(db, quote["id"], item_payload, current_user)
        quote = PurchasesService.get_quote_detail(db, quote["id"], current_user)
        try:
            emit_event(
                db=db,
                event_type="stock.purchase_requested",
                aggregate_type="stock_catalog_item",
                aggregate_id=str(stock_catalog_item_id),
                module="stock",
                payload={
                    "item_id": str(stock_catalog_item_id),
                    "request_id": str(quote["purchase_request_id"]),
                    "quote_id": str(quote["id"]),
                    "actor_user_id": current_user.id,
                    "action_url": f"/purchases?quote={quote['id']}&step=products",
                    "summary": f"{current_user.username} iniciou uma cotacao a partir do Estoque & Catalogo.",
                },
                actor_user_id=current_user.id,
            )
            db.commit()
        except Exception as exc:
            print(f"Failed to emit stock.purchase_requested: {exc}")
        return {
            **quote,
            "quote_id": quote["id"],
            "request_id": quote["purchase_request_id"],
            "existing_quote": False,
            "created_item_id": item.id,
            "action_url": f"/purchases?quote={quote['id']}&step=products",
            "message": "Cotacao criada em Compras a partir do Estoque & Catalogo.",
        }

    @staticmethod
    def parse_quote_list(db: Session, rfq_id: uuid.UUID, payload: Any, current_user: User) -> List[Dict[str, Any]]:
        PurchasesService.get_rfq(db, rfq_id, current_user)
        units = {"un", "und", "pc", "pcs", "m", "mt", "kg", "barra", "barras", "cx", "caixa"}
        parsed: List[Dict[str, Any]] = []
        for raw_line in [line.strip() for line in payload.text.splitlines() if line.strip()]:
            match = re.match(r"^\s*(?P<qty>\d+(?:[,.]\d+)?)?\s*(?P<unit>[a-zA-ZçÇ]+)?\s*(?P<desc>.+?)\s*$", raw_line)
            qty = 1.0
            unit = "un"
            desc = raw_line
            if match:
                qty_raw = match.group("qty")
                unit_raw = (match.group("unit") or "").lower()
                if qty_raw:
                    qty = float(qty_raw.replace(",", "."))
                if unit_raw in units:
                    unit = unit_raw
                    desc = match.group("desc").strip()
                elif qty_raw:
                    desc = " ".join(part for part in [unit_raw, match.group("desc").strip()] if part).strip()

            matches = StockCatalogService.list_items(db, q=desc, suggest=True, current_user=current_user)
            suggestion = matches[0] if matches else None
            confidence = "low"
            match_status = "needs_confirmation"
            if suggestion:
                normalized_desc = PurchasesService._normalize_text(desc)
                normalized_suggestion = PurchasesService._normalize_text(suggestion.get("display_name"))
                if normalized_desc and normalized_desc in normalized_suggestion:
                    confidence = "high"
                    match_status = "confirmed"
                else:
                    confidence = "check"

            parsed.append({
                "raw_text": raw_line,
                "description": desc,
                "quantity": qty,
                "unit_of_measure": unit,
                "confidence": confidence,
                "match_status": match_status,
                "suggested_stock_catalog_item_id": suggestion.get("id") if suggestion else None,
                "suggested_display_name": suggestion.get("display_name") if suggestion else None,
                "suggested_specification": (suggestion.get("specification_text") or suggestion.get("measure_display")) if suggestion else None,
            })
        return parsed

    @staticmethod
    def supplier_suggestions(db: Session, rfq_id: uuid.UUID, current_user: User) -> List[Dict[str, Any]]:
        rfq = PurchasesService.get_rfq(db, rfq_id, current_user)
        items = list(rfq.purchase_request.items)
        master_suppliers = db.query(Supplier).options(joinedload(Supplier.person)).filter(Supplier.status == "ACTIVE").all()
        by_name = {PurchasesService._normalize_text(s.person.name if s.person else ""): s for s in master_suppliers}
        suggestions: Dict[str, Dict[str, Any]] = {}

        for item in items:
            if not item.stock_catalog_item_id:
                continue
            offers = db.query(StockCatalogOffer).options(joinedload(StockCatalogOffer.supplier)).filter(
                StockCatalogOffer.item_id == item.stock_catalog_item_id,
                StockCatalogOffer.is_current == True,
            ).all()
            for offer in offers:
                stock_supplier = offer.supplier
                key = PurchasesService._normalize_text(stock_supplier.name if stock_supplier else "")
                master_supplier = by_name.get(key)
                suggestion_key = str(master_supplier.id) if master_supplier else f"stock:{stock_supplier.id}"
                row = suggestions.setdefault(suggestion_key, {
                    "supplier_id": master_supplier.id if master_supplier else None,
                    "supplier_name": master_supplier.person.name if master_supplier and master_supplier.person else stock_supplier.name,
                    "contact_email": (master_supplier.preferred_contact_email or master_supplier.person.email) if master_supplier and master_supplier.person else stock_supplier.email,
                    "coverage_count": 0,
                    "total_items": len(items),
                    "confidence": "high" if master_supplier else "check",
                    "status": "known" if master_supplier else "needs_master_data_link",
                    "reasons": set(),
                    "item_ids": [],
                })
                row["coverage_count"] += 1
                row["item_ids"].append(item.id)
                row["reasons"].add("fornece este item")
                if offer.price:
                    row["reasons"].add("tem preco recente")
                if row["contact_email"]:
                    row["reasons"].add("tem contato valido")

        for supplier in master_suppliers:
            if not supplier.preferred_contact_email and not (supplier.person and supplier.person.email):
                continue
            key = str(supplier.id)
            suggestions.setdefault(key, {
                "supplier_id": supplier.id,
                "supplier_name": supplier.person.name if supplier.person else "Fornecedor",
                "contact_email": supplier.preferred_contact_email or (supplier.person.email if supplier.person else None),
                "coverage_count": 0,
                "total_items": len(items),
                "confidence": "check",
                "status": "known",
                "reasons": {"tem contato valido"},
                "item_ids": [],
            })

        rows = list(suggestions.values())
        for row in rows:
            row["reasons"] = sorted(row["reasons"])
        rows.sort(key=lambda row: (row["status"] != "known", -row["coverage_count"], row["supplier_name"]))
        return rows[:8]

    @staticmethod
    def save_supplier_selection(db: Session, rfq_id: uuid.UUID, payload: Any, current_user: User) -> Dict[str, Any]:
        rfq = PurchasesService.get_rfq(db, rfq_id, current_user)
        request_item_ids = {item.id for item in rfq.purchase_request.items}
        saved = []
        for supplier_payload in payload.suppliers:
            supplier = db.query(Supplier).options(joinedload(Supplier.person)).filter(
                Supplier.id == supplier_payload.supplier_id,
                Supplier.status == "ACTIVE",
            ).first()
            if not supplier:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Fornecedor precisa estar aprovado no cadastro mestre.")
            contact_email = supplier_payload.contact_email or supplier.preferred_contact_email or (supplier.person.email if supplier.person else None)
            if not contact_email:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Fornecedor {supplier.person.name if supplier.person else supplier.id} sem e-mail valido.")

            rfq_supplier = db.query(PurchaseRFQSupplier).filter(
                PurchaseRFQSupplier.rfq_id == rfq.id,
                PurchaseRFQSupplier.supplier_id == supplier.id,
            ).first()
            if not rfq_supplier:
                rfq_supplier = PurchaseRFQSupplier(
                    rfq_id=rfq.id,
                    supplier_id=supplier.id,
                    contact_email=contact_email,
                    status="DRAFT",
                    created_at=datetime.now(timezone.utc),
                )
                db.add(rfq_supplier)
                db.flush()
            else:
                rfq_supplier.contact_email = contact_email

            db.query(PurchaseRFQSupplierItem).filter(PurchaseRFQSupplierItem.rfq_supplier_id == rfq_supplier.id).delete()
            for item_id in supplier_payload.item_ids:
                if item_id not in request_item_ids:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Item nao pertence a esta cotacao.")
                db.add(PurchaseRFQSupplierItem(
                    rfq_supplier_id=rfq_supplier.id,
                    purchase_item_id=item_id,
                    created_at=datetime.now(timezone.utc),
                ))
            saved.append(rfq_supplier)

        if saved:
            rfq.status = "READY_FOR_REVIEW"
            rfq.purchase_request.status = "RFQ_PREPARING"
            rfq.updated_at = datetime.now(timezone.utc)
            rfq.purchase_request.updated_at = datetime.now(timezone.utc)
        db.commit()
        return PurchasesService.get_quote_detail(db, rfq_id, current_user)

    @staticmethod
    def _quote_public_code(rfq: PurchaseRFQ) -> str:
        year = (rfq.created_at or datetime.now(timezone.utc)).year
        number = str(rfq.id.int % 1000000).zfill(6)
        if settings.ENVIRONMENT.lower() == "testing":
            return f"COT-SANDBOX-{number}"
        return f"COT-{year}-{number}"

    @staticmethod
    def _default_signature(db: Session, account_id: str) -> Optional[PurchaseSenderSignature]:
        return db.query(PurchaseSenderSignature).filter(
            PurchaseSenderSignature.account_id == account_id,
            PurchaseSenderSignature.is_default == True,
            PurchaseSenderSignature.is_active == True,
        ).first()

    @staticmethod
    def _html_to_text(value: str) -> str:
        text = re.sub(r"<br\s*/?>", "\n", value or "", flags=re.IGNORECASE)
        text = re.sub(r"</(p|div|tr|table|thead|tbody)\s*>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</t[dh]\s*>", "\t", text, flags=re.IGNORECASE)
        text = re.sub(r"<li[^>]*>", "- ", text, flags=re.IGNORECASE)
        text = re.sub(r"</li\s*>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", "", text)
        text = html.unescape(text)
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @staticmethod
    def _email_message_hashes(
        *,
        quote_id: uuid.UUID,
        supplier_id: uuid.UUID,
        sender_account_id: str,
        from_email: str,
        to_email: Optional[str],
        cc: Optional[str],
        bcc: Optional[str],
        bcc_enabled: bool,
        subject: str,
        body_html: str,
        signature_html: Optional[str],
    ) -> tuple[str, str]:
        content_payload = "|".join([
            sender_account_id,
            from_email or "",
            subject or "",
            body_html or "",
            signature_html or "",
        ])
        recipients_payload = "|".join([
            to_email or "",
            cc or "",
            bcc if bcc_enabled else "",
        ])
        content_hash = hashlib.sha256(content_payload.encode("utf-8")).hexdigest()
        recipients_hash = hashlib.sha256(recipients_payload.encode("utf-8")).hexdigest()
        idempotency_key = hashlib.sha256(
            f"{quote_id}|{supplier_id}|{sender_account_id}|{content_hash}|{recipients_hash}|no-attachments".encode("utf-8")
        ).hexdigest()
        return content_hash, idempotency_key

    @staticmethod
    def _email_message_items(rfq_supplier: PurchaseRFQSupplier) -> tuple[List[PurchaseRequestItem], List[Dict[str, Any]]]:
        item_links = list(rfq_supplier.item_links)
        selected_items = [link.purchase_item for link in item_links] or list(rfq_supplier.rfq.purchase_request.items)
        preview_items = []
        for item in selected_items:
            preview_items.append({
                "purchase_item_id": item.id,
                "description": PurchasesService._quote_item_description(item),
                "specifications": item.specifications,
                "quantity": float(item.quantity),
                "unit_of_measure": item.unit_of_measure or "un",
                "notes": None,
            })
        return selected_items, preview_items

    @staticmethod
    def _build_email_body(
        rfq_supplier: PurchaseRFQSupplier,
        account: PurchaseSenderAccount,
        signature: Optional[PurchaseSenderSignature],
    ) -> tuple[str, str, List[Dict[str, Any]]]:
        selected_items, preview_items = PurchasesService._email_message_items(rfq_supplier)
        rows = []
        for item in selected_items:
            rows.append(
                "<tr>"
                f"<td>{html.escape(PurchasesService._quote_item_description(item))}</td>"
                f"<td>{html.escape(item.specifications or '')}</td>"
                f"<td>{float(item.quantity):g}</td>"
                f"<td>{html.escape(item.unit_of_measure or 'un')}</td>"
                f"<td>{html.escape('')}</td>"
                "</tr>"
            )
        supplier_name = rfq_supplier.supplier.person.name if rfq_supplier.supplier and rfq_supplier.supplier.person else "Fornecedor"
        table = (
            "<table style='width:100%;border-collapse:collapse;margin:12px 0;'>"
            "<thead><tr><th>Item</th><th>Especificacao</th><th>Quantidade</th><th>Unidade</th><th>Observacao</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>"
        )
        signature_html = signature.html_content if signature else f"<p>Atenciosamente,<br><strong>{html.escape(account.display_name)}</strong></p>"
        body_html = (
            f"<p>Ola {html.escape(supplier_name)},</p>"
            "<p>Solicitamos cotacao para os itens abaixo.</p>"
            f"{table}"
            "<p>Por favor, informar:</p>"
            "<ul><li>preco;</li><li>prazo;</li><li>frete;</li><li>validade;</li><li>condicao de pagamento.</li></ul>"
            f"{signature_html}"
        )
        return body_html, PurchasesService._html_to_text(body_html), preview_items

    @staticmethod
    def _select_sender_account(db: Session, rfq: PurchaseRFQ) -> PurchaseSenderAccount:
        PurchasesService._ensure_default_sender_accounts(db)
        origin_text = f"{rfq.purchase_request.origin_type or ''} {rfq.purchase_request.origin_snapshot_json or ''}".lower()
        account_id = "ventrio" if "ventrio" in origin_text else "vesper"
        account = db.get(PurchaseSenderAccount, account_id)
        if not account:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Conta remetente padrao nao encontrada.")
        return account

    @staticmethod
    def _prepare_email_message(db: Session, rfq_supplier: PurchaseRFQSupplier, current_user: User) -> PurchaseEmailMessage:
        rfq = rfq_supplier.rfq
        account = PurchasesService._select_sender_account(db, rfq)
        signature = PurchasesService._default_signature(db, account.id)
        body_html, body_text, _ = PurchasesService._build_email_body(rfq_supplier, account, signature)
        quote_code = PurchasesService._quote_public_code(rfq)
        subject = f"[Portal Vesper] Cotação {quote_code}"
        bcc = account.default_bcc if account.bcc_default_enabled else None
        content_hash, idempotency_key = PurchasesService._email_message_hashes(
            quote_id=rfq.id,
            supplier_id=rfq_supplier.supplier_id,
            sender_account_id=account.id,
            from_email=account.email,
            to_email=rfq_supplier.contact_email,
            cc=None,
            bcc=bcc,
            bcc_enabled=bool(account.bcc_default_enabled),
            subject=subject,
            body_html=body_html,
            signature_html=signature.html_content if signature else None,
        )

        same_key = db.query(PurchaseEmailMessage).filter(
            PurchaseEmailMessage.idempotency_key == idempotency_key,
        ).first()
        if same_key:
            return same_key

        message = db.query(PurchaseEmailMessage).filter(
            PurchaseEmailMessage.rfq_supplier_id == rfq_supplier.id,
            PurchaseEmailMessage.status.notin_(["sent", "cancelled", "superseded"]),
        ).order_by(desc(PurchaseEmailMessage.created_at)).first()
        if not message:
            message = PurchaseEmailMessage(
                quote_id=rfq.id,
                rfq_id=rfq.id,
                rfq_supplier_id=rfq_supplier.id,
                supplier_id=rfq_supplier.supplier_id,
                sender_account_id=account.id,
                created_by=current_user.id,
                created_at=datetime.now(timezone.utc),
            )
            db.add(message)

        message.from_email = account.email
        message.from_name = account.display_name
        message.to_email = rfq_supplier.contact_email
        message.cc = None
        message.bcc = bcc
        message.bcc_enabled = bool(account.bcc_default_enabled)
        message.bcc_source = "account_default"
        message.subject = subject
        message.body_html = body_html
        message.body_text = body_text
        message.signature_html = signature.html_content if signature else None
        message.status = "ready" if rfq_supplier.contact_email else "draft"
        message.environment = settings.ENVIRONMENT.lower()
        message.content_hash = content_hash
        message.idempotency_key = idempotency_key
        message.error_code = None
        message.error_message = None
        message.prepared_at = datetime.now(timezone.utc)
        message.updated_by = current_user.id
        message.updated_at = datetime.now(timezone.utc)
        rfq_supplier.message_subject = subject
        rfq_supplier.message_body = body_html
        return message

    @staticmethod
    def _email_message_payload(message: PurchaseEmailMessage) -> Dict[str, Any]:
        account = message.sender_account
        rfq_supplier = message.rfq_supplier
        selected_items: List[Dict[str, Any]] = []
        supplier_name = "Fornecedor"
        if rfq_supplier:
            _, selected_items = PurchasesService._email_message_items(rfq_supplier)
            supplier_name = rfq_supplier.supplier.person.name if rfq_supplier.supplier and rfq_supplier.supplier.person else supplier_name
        env = settings.ENVIRONMENT.lower()
        has_recipient = bool(message.to_email)
        configured_for_real = bool(account and account.has_secret and account.status == "configured")
        can_send = has_recipient and (env == "testing" or configured_for_real)
        blocked_reason = None
        if not has_recipient:
            blocked_reason = "Informe o e-mail do fornecedor antes de enviar."
        elif not configured_for_real and env != "testing":
            blocked_reason = f"A conta {message.from_email} ainda nao esta configurada no cofre."

        human_status = {
            "draft": "Mensagem em preparo.",
            "ready": "Pronta para revisao.",
            "blocked_missing_credentials": "Envio real bloqueado ate configurar a conta.",
            "sent": "Cotacao enviada.",
            "failed": "Falha ao enviar.",
            "superseded": "Mensagem substituida por uma versao mais nova.",
        }.get(message.status, "Mensagem em preparo.")
        if env == "testing" and message.status in {"ready", "draft"} and has_recipient:
            human_status = "Pronta para envio de teste."

        return {
            "message_id": message.id,
            "rfq_supplier_id": message.rfq_supplier_id,
            "supplier_id": message.supplier_id,
            "supplier_name": supplier_name,
            "to_email": message.to_email,
            "sender_account_id": message.sender_account_id,
            "sender_email": message.from_email,
            "sender_name": message.from_name,
            "account_status": account.status if account else "not_configured",
            "can_send": can_send,
            "blocked_reason": blocked_reason,
            "bcc_enabled": bool(message.bcc_enabled),
            "bcc": message.bcc if message.bcc_enabled else None,
            "bcc_source": message.bcc_source,
            "subject": message.subject,
            "body_html": message.body_html,
            "body_text": message.body_text,
            "signature_html": message.signature_html,
            "content_hash": message.content_hash,
            "idempotency_key": message.idempotency_key,
            "status": message.status,
            "environment": message.environment,
            "provider_message_id": message.provider_message_id,
            "human_status": human_status,
            "pdf_optional_available": False,
            "pdf_status": "not_configured",
            "pdf_message": "PDF opcional sera ativado apos configurar o gerador de documentos.",
            "items": selected_items,
            "created_at": message.created_at,
            "updated_at": message.updated_at,
            "sent_at": message.sent_at,
            "failed_at": message.failed_at,
            "error_message": message.error_message,
        }

    @staticmethod
    def email_previews(db: Session, rfq_id: uuid.UUID, current_user: User) -> List[Dict[str, Any]]:
        rfq = PurchasesService.get_rfq(db, rfq_id, current_user)
        for rfq_supplier in rfq.rfq_suppliers:
            PurchasesService._prepare_email_message(db, rfq_supplier, current_user)
        db.commit()
        messages = db.query(PurchaseEmailMessage).options(
            joinedload(PurchaseEmailMessage.sender_account),
            joinedload(PurchaseEmailMessage.rfq_supplier).joinedload(PurchaseRFQSupplier.supplier).joinedload(Supplier.person),
            joinedload(PurchaseEmailMessage.rfq_supplier).joinedload(PurchaseRFQSupplier.item_links).joinedload(PurchaseRFQSupplierItem.purchase_item),
        ).filter(
            PurchaseEmailMessage.quote_id == rfq.id,
            PurchaseEmailMessage.status != "superseded",
        ).order_by(PurchaseEmailMessage.created_at).all()
        return [PurchasesService._email_message_payload(message) for message in messages]

    @staticmethod
    def get_email_messages(db: Session, rfq_id: uuid.UUID, current_user: User) -> List[Dict[str, Any]]:
        PurchasesService.get_rfq(db, rfq_id, current_user)
        return PurchasesService.email_previews(db, rfq_id, current_user)

    @staticmethod
    def get_email_message(db: Session, message_id: uuid.UUID, current_user: User) -> PurchaseEmailMessage:
        message = db.query(PurchaseEmailMessage).options(
            joinedload(PurchaseEmailMessage.sender_account),
            joinedload(PurchaseEmailMessage.rfq_supplier).joinedload(PurchaseRFQSupplier.supplier).joinedload(Supplier.person),
            joinedload(PurchaseEmailMessage.rfq_supplier).joinedload(PurchaseRFQSupplier.item_links).joinedload(PurchaseRFQSupplierItem.purchase_item),
        ).filter(PurchaseEmailMessage.id == message_id).first()
        if not message:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mensagem de cotacao nao encontrada.")
        PurchasesService.get_rfq(db, message.quote_id, current_user)
        return message

    @staticmethod
    def update_email_message(db: Session, message_id: uuid.UUID, payload: Any, current_user: User) -> Dict[str, Any]:
        message = PurchasesService.get_email_message(db, message_id, current_user)
        data = payload.model_dump(exclude_unset=True)
        if message.status == "sent":
            message = PurchaseEmailMessage(
                quote_id=message.quote_id,
                rfq_id=message.rfq_id,
                rfq_supplier_id=message.rfq_supplier_id,
                supplier_id=message.supplier_id,
                supplier_contact_id=message.supplier_contact_id,
                sender_account_id=message.sender_account_id,
                from_email=message.from_email,
                from_name=message.from_name,
                to_email=message.to_email,
                cc=message.cc,
                bcc=message.bcc,
                bcc_enabled=message.bcc_enabled,
                bcc_source=message.bcc_source,
                subject=message.subject,
                body_html=message.body_html,
                body_text=message.body_text,
                signature_html=message.signature_html,
                status="draft",
                environment=settings.ENVIRONMENT.lower(),
                idempotency_key=uuid.uuid4().hex,
                content_hash=uuid.uuid4().hex,
                prepared_at=datetime.now(timezone.utc),
                created_by=current_user.id,
                updated_by=current_user.id,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            db.add(message)
            db.flush()

        if "sender_account_id" in data and data["sender_account_id"]:
            account = db.get(PurchaseSenderAccount, data["sender_account_id"])
            if not account:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conta remetente nao encontrada.")
            signature = PurchasesService._default_signature(db, account.id)
            message.sender_account_id = account.id
            message.from_email = account.email
            message.from_name = account.display_name
            message.signature_html = signature.html_content if signature else None
            if message.bcc_source == "account_default":
                message.bcc_enabled = account.bcc_default_enabled
                message.bcc = account.default_bcc if account.bcc_default_enabled else None

        for field in ["to_email", "subject", "body_html", "body_text"]:
            if field in data and data[field] is not None:
                setattr(message, field, data[field])
        if "bcc_enabled" in data and data["bcc_enabled"] is not None:
            message.bcc_enabled = data["bcc_enabled"]
            message.bcc_source = "user_override"
            if not message.bcc_enabled:
                message.bcc = None
        if "bcc" in data:
            message.bcc = data["bcc"]
            message.bcc_source = "user_override"
        if "body_html" in data and "body_text" not in data:
            message.body_text = PurchasesService._html_to_text(message.body_html)

        content_hash, idempotency_key = PurchasesService._email_message_hashes(
            quote_id=message.quote_id,
            supplier_id=message.supplier_id,
            sender_account_id=message.sender_account_id,
            from_email=message.from_email,
            to_email=message.to_email,
            cc=message.cc,
            bcc=message.bcc,
            bcc_enabled=message.bcc_enabled,
            subject=message.subject,
            body_html=message.body_html,
            signature_html=message.signature_html,
        )
        existing = db.query(PurchaseEmailMessage).filter(
            PurchaseEmailMessage.idempotency_key == idempotency_key,
            PurchaseEmailMessage.id != message.id,
        ).first()
        if existing and existing.status == "sent":
            return PurchasesService._email_message_payload(existing)
        message.content_hash = content_hash
        message.idempotency_key = idempotency_key
        message.status = "ready" if message.to_email else "draft"
        message.error_code = None
        message.error_message = None
        message.prepared_at = datetime.now(timezone.utc)
        message.updated_by = current_user.id
        message.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(message)
        return PurchasesService._email_message_payload(PurchasesService.get_email_message(db, message.id, current_user))

    @staticmethod
    def send_email_message(db: Session, message_id: uuid.UUID, current_user: User, mode: str = "real") -> Dict[str, Any]:
        message = PurchasesService.get_email_message(db, message_id, current_user)
        if message.status == "sent" and mode != "test":
            return {
                "message": PurchasesService._email_message_payload(message),
                "duplicate_blocked": True,
                "human_message": "Essa cotacao ja foi enviada para este fornecedor. O Portal bloqueou um envio duplicado.",
            }
        duplicate = db.query(PurchaseEmailMessage).filter(
            PurchaseEmailMessage.idempotency_key == message.idempotency_key,
            PurchaseEmailMessage.status == "sent",
            PurchaseEmailMessage.id != message.id,
        ).first()
        if duplicate and mode != "test":
            return {
                "message": PurchasesService._email_message_payload(duplicate),
                "duplicate_blocked": True,
                "human_message": "Essa cotacao ja foi enviada para este fornecedor. O Portal bloqueou um envio duplicado.",
            }
        
        is_env_testing = settings.ENVIRONMENT.lower() in {"testing", "test"}
        is_test_send = (mode == "test") or is_env_testing
        
        recipient = message.to_email
        if not recipient:
            message.status = "failed"
            message.error_code = "missing_recipient"
            message.error_message = "Verifique o e-mail do fornecedor antes de enviar."
            message.failed_at = datetime.now(timezone.utc)
            db.commit()
            return {
                "message": PurchasesService._email_message_payload(message),
                "duplicate_blocked": False,
                "human_message": message.error_message,
            }
            
        original_recipient = recipient
        if is_test_send:
            recipient = "projeto3@empresa-parceira.example"
            
        if is_env_testing:
            # Em testes unitários do vitest/pytest, simula sem abrir conexões reais
            message.status = "sent"
            message.provider_message_id = f"fake-{message.id}"
            message.message_id = f"<{message.id}@portal-vesper.test>"
            message.smtp_response = "fake transport: not delivered to real mailbox"
            message.sent_at = datetime.now(timezone.utc)
            message.failed_at = None
            message.error_code = None
            message.error_message = None
            if message.rfq_supplier:
                message.rfq_supplier.status = "SENT"
                message.rfq_supplier.sent_at = message.sent_at
            db.commit()
            return {
                "message": PurchasesService._email_message_payload(PurchasesService.get_email_message(db, message.id, current_user)),
                "duplicate_blocked": False,
                "human_message": "Envio de teste registrado. Nenhum e-mail real foi enviado.",
            }
            
        account = message.sender_account
        if not account.has_secret or account.status != "configured":
            message.status = "blocked_missing_credentials"
            message.error_code = "missing_credentials"
            message.error_message = f"A conta {message.from_email} ainda nao esta configurada no cofre."
            message.failed_at = datetime.now(timezone.utc)
            db.commit()
            return {
                "message": PurchasesService._email_message_payload(message),
                "duplicate_blocked": False,
                "human_message": message.error_message,
            }
            
        from app.models.it import ITCredential
        from app.modules.it.credentials import decrypt_secret
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        system_name = account.secret_ref.replace("vault://", "") if account.secret_ref else None
        if not system_name:
            system_name = f"purchases/smtp/{account.id}"
            
        smtp_credential = db.query(ITCredential).filter(
            ITCredential.system_name == system_name,
            ITCredential.is_active == True
        ).first()
        
        if not smtp_credential:
            smtp_credential = db.query(ITCredential).filter(
                (ITCredential.system_name == "SMTP") | (ITCredential.title == "SMTP"),
                ITCredential.is_active == True
            ).first()
            
        if not smtp_credential:
            message.status = "blocked_missing_credentials"
            message.error_code = "missing_credentials"
            message.error_message = f"Credenciais SMTP para '{system_name}' não encontradas no cofre."
            message.failed_at = datetime.now(timezone.utc)
            db.commit()
            return {
                "message": PurchasesService._email_message_payload(message),
                "duplicate_blocked": False,
                "human_message": message.error_message,
            }
            
        host = "smtp.skymail.net.br"
        port = 465
        if smtp_credential.url:
            if ":" in smtp_credential.url:
                parts = smtp_credential.url.split(":")
                host = parts[0]
                try:
                    port = int(parts[1])
                except ValueError:
                    pass
            else:
                host = smtp_credential.url
                
        try:
            smtp_pass = decrypt_secret(smtp_credential.secret_encrypted)
            smtp_user = smtp_credential.username or account.email
            
            if port == 465:
                server = smtplib.SMTP_SSL(host, port, timeout=15)
            else:
                server = smtplib.SMTP(host, port, timeout=15)
                server.starttls()
                
            server.login(smtp_user, smtp_pass)
            
            body_text = message.body_text or ""
            body_html = message.body_html or ""
            
            if is_test_send:
                notice = "ENVIO DE TESTE — esta mensagem não foi enviada ao fornecedor original.\n"
                notice_html = "<div style='background:#fffbeb;border:1px solid #fef3c7;padding:10px;color:#b45309;font-weight:bold;margin-bottom:15px;'>ENVIO DE TESTE — esta mensagem não foi enviada ao fornecedor original.</div>"
                body_text = notice + body_text
                body_html = notice_html + body_html
                
            msg = MIMEMultipart()
            msg['From'] = smtp_user
            msg['To'] = recipient
            msg['Subject'] = message.subject or "Solicitação de Cotação"
            
            if message.bcc_enabled and message.bcc:
                msg['Bcc'] = message.bcc
                
            msg.attach(MIMEText(body_text, 'plain', 'utf-8'))
            msg.attach(MIMEText(body_html, 'html', 'utf-8'))
            
            recipients = [recipient]
            if message.bcc_enabled and message.bcc:
                recipients.append(message.bcc)
                
            server.sendmail(smtp_user, recipients, msg.as_string())
            server.quit()
            
            if not is_test_send:
                message.status = "sent"
                message.sent_at = datetime.now(timezone.utc)
                if message.rfq_supplier:
                    message.rfq_supplier.status = "SENT"
                    message.rfq_supplier.sent_at = message.sent_at
            
            db.commit()
            
            human_msg = "Cotação enviada com sucesso ao fornecedor." if not is_test_send else f"Envio de teste disparado com sucesso para {recipient}."
            return {
                "message": PurchasesService._email_message_payload(message),
                "duplicate_blocked": False,
                "human_message": human_msg
            }
            
        except Exception as e:
            message.status = "failed"
            message.error_code = "smtp_error"
            message.error_message = f"Erro de SMTP ao enviar e-mail: {str(e)}"
            message.failed_at = datetime.now(timezone.utc)
            db.commit()
            return {
                "message": PurchasesService._email_message_payload(message),
                "duplicate_blocked": False,
                "human_message": message.error_message
            }

    @staticmethod
    def send_quote(db: Session, rfq_id: uuid.UUID, current_user: User) -> List[Dict[str, Any]]:
        previews = PurchasesService.email_previews(db, rfq_id, current_user)
        results = []
        for preview in previews:
            results.append(PurchasesService.send_email_message(db, preview["message_id"], current_user))
        return results

    @staticmethod
    def _monitoring_secret() -> str:
        if settings.N8N_WEBHOOK_SECRET:
            return settings.N8N_WEBHOOK_SECRET
        if settings.ENVIRONMENT.lower() in {"testing", "development", "dev", "local"}:
            return "vesper_n8n_local_secret"
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Configure o segredo do gateway n8n antes de receber respostas de e-mail.",
        )

    @staticmethod
    def _parse_callback_timestamp(value: str) -> datetime:
        try:
            if re.fullmatch(r"\d+(\.\d+)?", value.strip()):
                return datetime.fromtimestamp(float(value), tz=timezone.utc)
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Timestamp do callback invalido.",
            )

    @staticmethod
    def _verify_monitoring_signature(
        *,
        raw_body: bytes,
        webhook_id: str,
        timestamp_value: str,
        signature_value: str,
    ) -> None:
        timestamp_dt = PurchasesService._parse_callback_timestamp(timestamp_value)
        age = abs((datetime.now(timezone.utc) - timestamp_dt).total_seconds())
        if age > settings.N8N_CALLBACK_MAX_AGE_SECONDS:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Callback expirado. Reenvie a partir do monitoramento.",
            )

        supplied = (signature_value or "").strip()
        if supplied.startswith("sha256="):
            supplied = supplied.split("=", 1)[1]
        expected = hmac.new(
            PurchasesService._monitoring_secret().encode("utf-8"),
            raw_body + timestamp_value.encode("utf-8") + webhook_id.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, supplied):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Assinatura invalida no callback de monitoramento.",
            )

    @staticmethod
    def _ensure_default_monitored_accounts(db: Session) -> None:
        PurchasesService._ensure_default_sender_accounts(db)
        changed = False
        for sender in db.query(PurchaseSenderAccount).all():
            folder = sender.monitored_folder or "INBOX"
            monitored = db.query(PurchaseMonitoredAccount).filter(
                PurchaseMonitoredAccount.account_email == sender.email,
                PurchaseMonitoredAccount.folder == folder,
            ).first()
            if not monitored:
                monitored = PurchaseMonitoredAccount(
                    sender_account_id=sender.id,
                    account_email=sender.email,
                    provider="imap",
                    folder=folder,
                    status=sender.status,
                    imap_enabled=bool(sender.has_secret and sender.status == "configured"),
                    secret_ref=sender.secret_ref.replace("/smtp/", "/imap/") if sender.secret_ref else None,
                    has_secret=sender.has_secret,
                    is_active=True,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                db.add(monitored)
                changed = True
            else:
                monitored.sender_account_id = sender.id
                monitored.status = sender.status
                monitored.has_secret = sender.has_secret
                monitored.imap_enabled = bool(sender.has_secret and sender.status == "configured")
                monitored.secret_ref = sender.secret_ref.replace("/smtp/", "/imap/") if sender.secret_ref else monitored.secret_ref
                monitored.updated_at = datetime.now(timezone.utc)
                changed = True
        if changed:
            db.commit()

    @staticmethod
    def _normalize_email(value: Optional[str]) -> str:
        return (value or "").strip().lower()

    @staticmethod
    def _email_domain(value: Optional[str]) -> Optional[str]:
        email_value = PurchasesService._normalize_email(value)
        if "@" not in email_value:
            return None
        return email_value.rsplit("@", 1)[1]

    @staticmethod
    def _normalize_subject(value: Optional[str]) -> str:
        subject = (value or "").strip().lower()
        subject = re.sub(r"^\s*(re|res|fw|fwd)\s*:\s*", "", subject)
        return re.sub(r"\s+", " ", subject)

    @staticmethod
    def _sanitize_inbound_html(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        cleaned = re.sub(r"<\s*(script|style)[^>]*>.*?<\s*/\s*\1\s*>", "", value, flags=re.IGNORECASE | re.DOTALL)
        cleaned = re.sub(r"\son[a-z]+\s*=\s*(['\"]).*?\1", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
        cleaned = re.sub(r"\s(href|src)\s*=\s*(['\"])\s*javascript:.*?\2", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
        return cleaned

    @staticmethod
    def _safe_attachment_name(value: Optional[str]) -> str:
        name = (value or "anexo").replace("\\", "/").split("/")[-1].strip() or "anexo"
        safe = re.sub(r"[^A-Za-z0-9._ -]", "_", name)
        safe = re.sub(r"\s+", " ", safe).strip(" .")
        return safe[:180] or "anexo"

    @staticmethod
    def _attachment_security(filename: Optional[str], content_type: Optional[str]) -> tuple[str, Optional[str], Optional[str]]:
        safe_name = PurchasesService._safe_attachment_name(filename)
        detected_type = mimetypes.guess_type(safe_name)[0] or content_type
        ext = safe_name.lower().rsplit(".", 1)[-1] if "." in safe_name else ""
        blocked_extensions = {
            "exe", "bat", "cmd", "ps1", "vbs", "js", "jse", "scr", "com",
            "msi", "jar", "lnk", "reg", "sh", "dll",
        }
        macro_extensions = {"xlsm", "docm", "pptm"}
        dangerous_types = {
            "application/x-msdownload",
            "application/x-msdos-program",
            "application/x-sh",
            "application/javascript",
        }
        if ext in blocked_extensions or (content_type or "").lower() in dangerous_types:
            return detected_type, "blocked", "Anexo bloqueado por tipo de arquivo executavel ou script."
        if ext in macro_extensions:
            return detected_type, "blocked", "Anexo bloqueado por conter macro. Revise fora do fluxo automatico."
        return detected_type, "pending_review", None

    @staticmethod
    def _monitoring_content_hash(payload: PurchaseMonitoringEmailCallbackPayload) -> str:
        serializable = payload.model_dump(mode="json")
        canonical = json.dumps(serializable, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def _inbound_idempotency_key(payload: PurchaseMonitoringEmailCallbackPayload, content_hash: str) -> str:
        account = PurchasesService._normalize_email(payload.account_email)
        folder = (payload.folder or "INBOX").strip()
        if payload.imap_uid:
            basis = f"imap|{account}|{folder}|{payload.imap_uid}"
        else:
            basis = f"message|{account}|{payload.message_id or ''}|{payload.received_at.isoformat()}|{content_hash}"
        return hashlib.sha256(basis.encode("utf-8")).hexdigest()

    @staticmethod
    def _message_tokens(*values: Optional[str], references: Optional[Iterable[str]] = None) -> List[str]:
        tokens = []
        for value in values:
            if value and value.strip():
                tokens.append(value.strip())
        for value in references or []:
            if value and value.strip():
                tokens.append(value.strip())
        return list(dict.fromkeys(tokens))

    @staticmethod
    def _candidate_level(score: int) -> str:
        if score >= 70:
            return "high"
        if score >= 35:
            return "check"
        return "low"

    @staticmethod
    def _candidate_status_for_level(level: str) -> str:
        if level == "high":
            return "needs_review"
        if level == "check":
            return "suggested"
        return "unidentified"

    @staticmethod
    def _supplier_name(supplier: Optional[Supplier]) -> Optional[str]:
        if supplier and supplier.person:
            return supplier.person.name
        return None

    @staticmethod
    def _candidate_payload(candidate: PurchaseResponseCandidate) -> Dict[str, Any]:
        inbound = candidate.inbound_message
        quote = candidate.quote
        supplier = candidate.supplier
        status_labels = {
            "needs_review": "Resposta recebida para revisar.",
            "suggested": "O Portal encontrou um possivel vinculo. Confira antes de usar.",
            "unidentified": "Resposta recebida, mas ainda sem cotacao identificada.",
            "confirmed": "Resposta vinculada pelo responsavel.",
            "rejected": "Sugestao descartada.",
            "ignored": "Resposta ignorada.",
        }
        return {
            "id": candidate.id,
            "inbound_message_id": candidate.inbound_message_id,
            "quote_id": candidate.quote_id,
            "rfq_id": candidate.rfq_id,
            "supplier_id": candidate.supplier_id,
            "supplier_name": PurchasesService._supplier_name(supplier),
            "quote_title": quote.title if quote else None,
            "quote_code": PurchasesService._quote_public_code(quote) if quote else None,
            "from_email": inbound.from_email,
            "from_name": inbound.from_name,
            "subject": inbound.subject,
            "body_text": inbound.body_text,
            "received_at": inbound.received_at,
            "candidate_status": candidate.candidate_status,
            "confidence_score": float(candidate.confidence_score or 0),
            "confidence_level": candidate.confidence_level,
            "match_reasons": candidate.match_reasons_json or [],
            "risk_flags": candidate.risk_flags_json or [],
            "attachments": [PurchasesService._attachment_payload(att) for att in inbound.attachments],
            "human_status": status_labels.get(candidate.candidate_status, "Resposta recebida."),
            "created_at": candidate.created_at,
            "updated_at": candidate.updated_at,
        }

    @staticmethod
    def _inbound_payload(inbound: PurchaseEmailInboundMessage) -> Dict[str, Any]:
        return {
            "id": inbound.id,
            "account_email": inbound.account_email,
            "folder": inbound.folder,
            "imap_uid": inbound.imap_uid,
            "message_id": inbound.message_id,
            "in_reply_to": inbound.in_reply_to,
            "references": inbound.references_json or [],
            "from_email": inbound.from_email,
            "from_name": inbound.from_name,
            "to": inbound.to_json or [],
            "cc": inbound.cc_json or [],
            "subject": inbound.subject,
            "body_text": inbound.body_text,
            "body_html_sanitized": inbound.body_html_sanitized,
            "received_at": inbound.received_at,
            "status": inbound.status,
            "classification_status": inbound.classification_status,
            "linked_quote_id": inbound.linked_quote_id,
            "linked_supplier_id": inbound.linked_supplier_id,
            "confidence_score": float(inbound.confidence_score) if inbound.confidence_score is not None else None,
            "confidence_level": inbound.confidence_level,
            "attachments": [PurchasesService._attachment_payload(att) for att in inbound.attachments],
            "created_at": inbound.created_at,
            "updated_at": inbound.updated_at,
        }

    @staticmethod
    def _attachment_payload(attachment: PurchaseEmailAttachment) -> Dict[str, Any]:
        return {
            "id": attachment.id,
            "inbound_message_id": attachment.inbound_message_id,
            "filename": attachment.filename,
            "safe_filename": attachment.safe_filename,
            "content_type": attachment.content_type,
            "detected_content_type": attachment.detected_content_type,
            "size_bytes": attachment.size_bytes,
            "sha256": attachment.sha256,
            "storage_key": attachment.storage_key,
            "scan_status": attachment.scan_status,
            "blocked_reason": attachment.blocked_reason,
            "text_preview": attachment.text_preview,
            "created_at": attachment.created_at,
        }

    @staticmethod
    def _find_candidate_matches(
        db: Session,
        inbound: PurchaseEmailInboundMessage,
    ) -> List[Dict[str, Any]]:
        matches: Dict[tuple[Optional[uuid.UUID], Optional[uuid.UUID]], Dict[str, Any]] = {}
        refs = PurchasesService._message_tokens(inbound.in_reply_to, references=inbound.references_json)
        if refs:
            outbound_messages = db.query(PurchaseEmailMessage).options(
                joinedload(PurchaseEmailMessage.rfq_supplier).joinedload(PurchaseRFQSupplier.supplier).joinedload(Supplier.person),
                joinedload(PurchaseEmailMessage.quote),
            ).filter(PurchaseEmailMessage.message_id.in_(refs)).all()
            for outbound in outbound_messages:
                key = (outbound.quote_id, outbound.supplier_id)
                matches[key] = {
                    "quote": outbound.quote,
                    "supplier": outbound.supplier,
                    "score": 80,
                    "reasons": ["respondeu ao e-mail enviado pela cotacao"],
                    "risk_flags": [],
                }

        normalized_subject = inbound.normalized_subject or ""
        body_text = (inbound.body_text or PurchasesService._html_to_text(inbound.body_html_sanitized or "")).lower()
        from_email = PurchasesService._normalize_email(inbound.from_email)
        from_domain = PurchasesService._email_domain(from_email)
        rfqs = db.query(PurchaseRFQ).options(
            joinedload(PurchaseRFQ.purchase_request).joinedload(PurchaseRequest.items),
            joinedload(PurchaseRFQ.rfq_suppliers).joinedload(PurchaseRFQSupplier.supplier).joinedload(Supplier.person),
        ).order_by(desc(PurchaseRFQ.created_at)).limit(200).all()
        for rfq in rfqs:
            quote_code = PurchasesService._quote_public_code(rfq).lower()
            if quote_code.lower() not in normalized_subject.lower() and quote_code.lower() not in body_text:
                continue
            for rfq_supplier in rfq.rfq_suppliers or []:
                supplier = rfq_supplier.supplier
                supplier_email = PurchasesService._normalize_email(
                    rfq_supplier.contact_email
                    or (supplier.preferred_contact_email if supplier else None)
                    or (supplier.person.email if supplier and supplier.person else None)
                )
                supplier_domain = PurchasesService._email_domain(supplier_email)
                score = 45
                reasons = ["assunto ou corpo contem o codigo da cotacao"]
                if supplier_email and supplier_email == from_email:
                    score += 35
                    reasons.append("remetente corresponde ao contato do fornecedor")
                elif supplier_domain and supplier_domain == from_domain:
                    score += 15
                    reasons.append("dominio do remetente corresponde ao fornecedor")
                if inbound.account_email and any(
                    PurchasesService._normalize_email(msg.from_email) == PurchasesService._normalize_email(inbound.account_email)
                    for msg in db.query(PurchaseEmailMessage).filter(PurchaseEmailMessage.quote_id == rfq.id).limit(10).all()
                ):
                    score += 5
                    reasons.append("resposta chegou na conta usada para enviar")
                for item in rfq.purchase_request.items or []:
                    description = PurchasesService._quote_item_description(item).lower()
                    if description and description[:30] in body_text:
                        score += 10
                        reasons.append("corpo menciona item da cotacao")
                        break
                key = (rfq.id, supplier.id if supplier else None)
                previous = matches.get(key)
                if not previous or score > previous["score"]:
                    matches[key] = {
                        "quote": rfq,
                        "supplier": supplier,
                        "score": score,
                        "reasons": reasons,
                        "risk_flags": [],
                    }

        if not matches:
            return [{
                "quote": None,
                "supplier": None,
                "score": 0,
                "reasons": ["nao foi possivel identificar a cotacao automaticamente"],
                "risk_flags": ["requires_manual_link"],
            }]

        values = list(matches.values())
        if len(values) > 1:
            for value in values:
                value["risk_flags"].append("multiple_candidates")
        return values

    @staticmethod
    def _classify_inbound_message(db: Session, inbound: PurchaseEmailInboundMessage) -> List[PurchaseResponseCandidate]:
        created: List[PurchaseResponseCandidate] = []
        matches = PurchasesService._find_candidate_matches(db, inbound)
        for match in matches:
            quote = match["quote"]
            supplier = match["supplier"]
            score = min(int(match["score"]), 100)
            level = PurchasesService._candidate_level(score)
            candidate_status = PurchasesService._candidate_status_for_level(level)
            existing = db.query(PurchaseResponseCandidate).filter(
                PurchaseResponseCandidate.inbound_message_id == inbound.id,
                PurchaseResponseCandidate.quote_id == (quote.id if quote else None),
                PurchaseResponseCandidate.supplier_id == (supplier.id if supplier else None),
            ).first()
            if existing:
                candidate = existing
            else:
                candidate = PurchaseResponseCandidate(
                    inbound_message_id=inbound.id,
                    quote_id=quote.id if quote else None,
                    rfq_id=quote.id if quote else None,
                    supplier_id=supplier.id if supplier else None,
                    created_at=datetime.now(timezone.utc),
                )
                db.add(candidate)
            candidate.candidate_status = candidate_status
            candidate.confidence_score = Decimal(score)
            candidate.confidence_level = level
            candidate.match_reasons_json = match["reasons"]
            candidate.risk_flags_json = match["risk_flags"]
            candidate.updated_at = datetime.now(timezone.utc)
            created.append(candidate)

        best = max(created, key=lambda item: int(item.confidence_score or 0), default=None)
        if best and best.confidence_level == "high" and best.quote_id:
            inbound.linked_quote_id = best.quote_id
            inbound.linked_supplier_id = best.supplier_id
            inbound.confidence_score = best.confidence_score
            inbound.confidence_level = best.confidence_level
            inbound.status = "response_to_review"
            inbound.classification_status = "linked_high_confidence"
        elif best and best.confidence_level == "check":
            inbound.confidence_score = best.confidence_score
            inbound.confidence_level = best.confidence_level
            inbound.status = "needs_manual_link"
            inbound.classification_status = "suggested_link"
        else:
            inbound.confidence_score = Decimal(0)
            inbound.confidence_level = "low"
            inbound.status = "unidentified"
            inbound.classification_status = "unidentified"
        inbound.updated_at = datetime.now(timezone.utc)
        return created

    @staticmethod
    def process_monitoring_email_callback(db: Session, raw_body: bytes, headers: Any) -> tuple[int, Dict[str, Any]]:
        if len(raw_body) > 1_000_000:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Callback de e-mail grande demais. Envie anexos pelo storage e apenas metadados pela API.",
            )

        webhook_id = headers.get("X-Vesper-Webhook-Id") or headers.get("x-vesper-webhook-id")
        timestamp_value = headers.get("X-Vesper-Timestamp") or headers.get("x-vesper-timestamp")
        signature_value = headers.get("X-Vesper-Signature") or headers.get("x-vesper-signature")
        source = headers.get("X-Vesper-Source") or headers.get("x-vesper-source")
        header_account = headers.get("X-Vesper-Account") or headers.get("x-vesper-account")
        missing = [
            name for name, value in {
                "X-Vesper-Webhook-Id": webhook_id,
                "X-Vesper-Timestamp": timestamp_value,
                "X-Vesper-Signature": signature_value,
                "X-Vesper-Source": source,
                "X-Vesper-Account": header_account,
            }.items() if not value
        ]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Callback sem cabecalhos obrigatorios: {', '.join(missing)}.",
            )

        if db.query(PurchaseMonitoringEvent).filter(PurchaseMonitoringEvent.webhook_id == webhook_id).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Callback repetido bloqueado pelo Portal.",
            )

        PurchasesService._verify_monitoring_signature(
            raw_body=raw_body,
            webhook_id=webhook_id,
            timestamp_value=timestamp_value,
            signature_value=signature_value,
        )

        try:
            payload = PurchaseMonitoringEmailCallbackPayload.model_validate_json(raw_body)
        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Payload de e-mail invalido: {exc.errors()[0].get('msg', 'verifique os campos obrigatorios')}.",
            )

        if PurchasesService._normalize_email(payload.account_email) != PurchasesService._normalize_email(header_account):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Conta do cabecalho nao corresponde a conta da mensagem.",
            )

        PurchasesService._ensure_default_monitored_accounts(db)
        monitored = db.query(PurchaseMonitoredAccount).filter(
            PurchaseMonitoredAccount.account_email == PurchasesService._normalize_email(payload.account_email),
            PurchaseMonitoredAccount.folder == (payload.folder or "INBOX"),
            PurchaseMonitoredAccount.is_active == True,
        ).first()
        if not monitored:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Conta de monitoramento ainda nao esta configurada para Compras.",
            )

        content_hash = PurchasesService._monitoring_content_hash(payload)
        idempotency_key = PurchasesService._inbound_idempotency_key(payload, content_hash)
        payload_hash = hashlib.sha256(raw_body).hexdigest()
        existing = db.query(PurchaseEmailInboundMessage).filter(
            PurchaseEmailInboundMessage.idempotency_key == idempotency_key,
        ).first()
        event = PurchaseMonitoringEvent(
            event_type="purchase.email.received",
            account_email=PurchasesService._normalize_email(payload.account_email),
            source=source,
            webhook_id=webhook_id,
            payload_hash=payload_hash,
            status="duplicate" if existing else "processing",
            inbound_message_id=existing.id if existing else None,
            created_at=datetime.now(timezone.utc),
        )
        db.add(event)
        if existing:
            event.processed_at = datetime.now(timezone.utc)
            db.commit()
            return 200, {
                "status": "duplicate",
                "duplicate": True,
                "inbound_message_id": existing.id,
                "candidate_ids": [candidate.id for candidate in existing.response_candidates],
                "human_message": "Mensagem ja registrada anteriormente. O Portal ignorou a duplicidade.",
            }

        inbound = PurchaseEmailInboundMessage(
            monitored_account_id=monitored.id,
            account_email=PurchasesService._normalize_email(payload.account_email),
            folder=payload.folder or "INBOX",
            imap_uid=payload.imap_uid,
            message_id=payload.message_id,
            in_reply_to=payload.in_reply_to,
            references_json=payload.references,
            from_email=PurchasesService._normalize_email(payload.from_email),
            from_name=payload.from_name,
            to_json=payload.to,
            cc_json=payload.cc,
            subject=payload.subject,
            normalized_subject=PurchasesService._normalize_subject(payload.subject),
            body_text=payload.body_text,
            body_html_sanitized=PurchasesService._sanitize_inbound_html(payload.body_html),
            raw_headers_json=payload.raw_headers,
            received_at=payload.received_at,
            content_hash=content_hash,
            idempotency_key=idempotency_key,
            status="received",
            classification_status="pending",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(inbound)
        db.flush()

        for attachment_payload in payload.attachments:
            safe_name = PurchasesService._safe_attachment_name(attachment_payload.filename)
            detected_type, scan_status, blocked_reason = PurchasesService._attachment_security(
                attachment_payload.filename,
                attachment_payload.content_type,
            )
            db.add(PurchaseEmailAttachment(
                inbound_message_id=inbound.id,
                filename=attachment_payload.filename,
                safe_filename=safe_name,
                content_type=attachment_payload.content_type,
                detected_content_type=detected_type,
                size_bytes=attachment_payload.size_bytes,
                sha256=attachment_payload.sha256,
                storage_key=attachment_payload.storage_key,
                scan_status=scan_status,
                blocked_reason=blocked_reason,
                text_preview=attachment_payload.text_preview,
                created_at=datetime.now(timezone.utc),
            ))

        candidates = PurchasesService._classify_inbound_message(db, inbound)
        monitored.last_seen_at = payload.received_at
        monitored.last_success_at = datetime.now(timezone.utc)
        monitored.last_error_at = None
        monitored.last_error_message = None
        event.status = "accepted"
        event.inbound_message_id = inbound.id
        event.processed_at = datetime.now(timezone.utc)
        db.commit()
        return 202, {
            "status": "accepted",
            "duplicate": False,
            "inbound_message_id": inbound.id,
            "candidate_ids": [candidate.id for candidate in candidates],
            "human_message": "Resposta recebida e colocada na fila de revisao.",
        }

    @staticmethod
    def list_response_candidates(
        db: Session,
        current_user: User,
        include_resolved: bool = False,
    ) -> List[Dict[str, Any]]:
        query = db.query(PurchaseResponseCandidate).options(
            joinedload(PurchaseResponseCandidate.inbound_message).joinedload(PurchaseEmailInboundMessage.attachments),
            joinedload(PurchaseResponseCandidate.quote),
            joinedload(PurchaseResponseCandidate.supplier).joinedload(Supplier.person),
        )
        if not include_resolved:
            query = query.filter(PurchaseResponseCandidate.candidate_status.in_(["needs_review", "suggested", "unidentified"]))
        candidates = query.order_by(desc(PurchaseResponseCandidate.created_at)).limit(100).all()
        return [PurchasesService._candidate_payload(candidate) for candidate in candidates]

    @staticmethod
    def get_response_candidate(db: Session, candidate_id: uuid.UUID, current_user: User) -> PurchaseResponseCandidate:
        candidate = db.query(PurchaseResponseCandidate).options(
            joinedload(PurchaseResponseCandidate.inbound_message).joinedload(PurchaseEmailInboundMessage.attachments),
            joinedload(PurchaseResponseCandidate.quote),
            joinedload(PurchaseResponseCandidate.supplier).joinedload(Supplier.person),
        ).filter(PurchaseResponseCandidate.id == candidate_id).first()
        if not candidate:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resposta para revisar nao encontrada.")
        return candidate

    @staticmethod
    def get_inbound_message(db: Session, inbound_message_id: uuid.UUID, current_user: User) -> PurchaseEmailInboundMessage:
        inbound = db.query(PurchaseEmailInboundMessage).options(
            joinedload(PurchaseEmailInboundMessage.attachments),
            joinedload(PurchaseEmailInboundMessage.response_candidates),
        ).filter(PurchaseEmailInboundMessage.id == inbound_message_id).first()
        if not inbound:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mensagem recebida nao encontrada.")
        return inbound

    @staticmethod
    def list_inbound_messages(db: Session, current_user: User) -> List[Dict[str, Any]]:
        inbound_messages = db.query(PurchaseEmailInboundMessage).options(
            joinedload(PurchaseEmailInboundMessage.attachments),
        ).order_by(desc(PurchaseEmailInboundMessage.received_at)).limit(100).all()
        return [PurchasesService._inbound_payload(inbound) for inbound in inbound_messages]

    @staticmethod
    def decide_response_candidate(
        db: Session,
        candidate_id: uuid.UUID,
        decision: str,
        current_user: User,
    ) -> Dict[str, Any]:
        candidate = PurchasesService.get_response_candidate(db, candidate_id, current_user)
        if decision not in {"confirm", "reject", "ignore"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Decisao invalida para resposta.")

        inbound = candidate.inbound_message
        now = datetime.now(timezone.utc)
        candidate.user_decision = decision
        candidate.decided_by = current_user.id
        candidate.decided_at = now
        candidate.updated_at = now
        if decision == "confirm":
            if not candidate.quote_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Vincule a cotacao antes de confirmar esta resposta.",
                )
            candidate.candidate_status = "confirmed"
            inbound.linked_quote_id = candidate.quote_id
            inbound.linked_supplier_id = candidate.supplier_id
            inbound.status = "response_to_review"
            inbound.classification_status = "confirmed_by_user"
            inbound.confidence_level = candidate.confidence_level
            inbound.confidence_score = candidate.confidence_score
            if candidate.quote_id and candidate.supplier_id:
                rfq_supplier = db.query(PurchaseRFQSupplier).filter(
                    PurchaseRFQSupplier.rfq_id == candidate.quote_id,
                    PurchaseRFQSupplier.supplier_id == candidate.supplier_id,
                ).first()
                if rfq_supplier:
                    rfq_supplier.status = "RESPONDED"
                    rfq_supplier.response_received_at = now
            human_message = "Resposta vinculada. Revise os dados recebidos antes de comparar."
        elif decision == "reject":
            candidate.candidate_status = "rejected"
            human_message = "Sugestao descartada. A mensagem continua disponivel para vinculo manual."
        else:
            candidate.candidate_status = "ignored"
            inbound.status = "ignored"
            inbound.classification_status = "ignored_by_user"
            human_message = "Resposta ignorada neste fluxo de cotacao."
        inbound.updated_at = now
        db.commit()
        refreshed = PurchasesService.get_response_candidate(db, candidate.id, current_user)
        return {
            "candidate": PurchasesService._candidate_payload(refreshed),
            "human_message": human_message,
        }

    @staticmethod
    def link_inbound_message(
        db: Session,
        inbound_message_id: uuid.UUID,
        payload: Any,
        current_user: User,
    ) -> Dict[str, Any]:
        inbound = PurchasesService.get_inbound_message(db, inbound_message_id, current_user)
        rfq = PurchasesService.get_rfq(db, payload.quote_id, current_user)
        supplier = db.get(Supplier, payload.supplier_id) if payload.supplier_id else None
        existing = db.query(PurchaseResponseCandidate).filter(
            PurchaseResponseCandidate.inbound_message_id == inbound.id,
            PurchaseResponseCandidate.quote_id == rfq.id,
            PurchaseResponseCandidate.supplier_id == (supplier.id if supplier else None),
        ).first()
        if not existing:
            existing = PurchaseResponseCandidate(
                inbound_message_id=inbound.id,
                quote_id=rfq.id,
                rfq_id=rfq.id,
                supplier_id=supplier.id if supplier else None,
                created_at=datetime.now(timezone.utc),
            )
            db.add(existing)
        existing.candidate_status = "needs_review"
        existing.confidence_score = Decimal(100)
        existing.confidence_level = "high"
        existing.match_reasons_json = ["vinculo manual feito pelo responsavel"]
        existing.risk_flags_json = []
        existing.updated_at = datetime.now(timezone.utc)
        inbound.linked_quote_id = rfq.id
        inbound.linked_supplier_id = supplier.id if supplier else None
        inbound.status = "response_to_review"
        inbound.classification_status = "manual_link"
        inbound.confidence_score = Decimal(100)
        inbound.confidence_level = "high"
        inbound.updated_at = datetime.now(timezone.utc)
        db.commit()
        return PurchasesService._candidate_payload(PurchasesService.get_response_candidate(db, existing.id, current_user))

    @staticmethod
    def list_monitoring_events(db: Session, current_user: User) -> List[Dict[str, Any]]:
        events = db.query(PurchaseMonitoringEvent).order_by(desc(PurchaseMonitoringEvent.created_at)).limit(100).all()
        return [{
            "id": event.id,
            "event_type": event.event_type,
            "account_email": event.account_email,
            "source": event.source,
            "status": event.status,
            "error_code": event.error_code,
            "error_message": event.error_message,
            "inbound_message_id": event.inbound_message_id,
            "created_at": event.created_at,
            "processed_at": event.processed_at,
        } for event in events]

    @staticmethod
    def _money_to_decimal_text(value: str) -> str:
        clean = re.sub(r"[^\d,\.]", "", value or "")
        if "," in clean and "." in clean:
            clean = clean.replace(".", "").replace(",", ".")
        elif "," in clean:
            clean = clean.replace(",", ".")
        return str(_money(clean))

    @staticmethod
    def _evidence_snippet(text: str, start: int, end: int) -> str:
        left = max(0, start - 70)
        right = min(len(text), end + 70)
        return re.sub(r"\s+", " ", text[left:right]).strip()

    @staticmethod
    def _extraction_sources(candidate: PurchaseResponseCandidate) -> List[Dict[str, Any]]:
        inbound = candidate.inbound_message
        sources: List[Dict[str, Any]] = []
        body_text = inbound.body_text or PurchasesService._html_to_text(inbound.body_html_sanitized or "")
        if body_text:
            sources.append({
                "source_type": "email_body",
                "source_label": "Corpo do e-mail",
                "text": body_text,
                "attachment_id": None,
            })
        for attachment in inbound.attachments:
            if attachment.scan_status == "blocked" or not attachment.text_preview:
                continue
            sources.append({
                "source_type": "attachment",
                "source_label": attachment.safe_filename,
                "text": attachment.text_preview,
                "attachment_id": attachment.id,
            })
        return sources

    @staticmethod
    def _extract_response_fields(candidate: PurchaseResponseCandidate) -> List[Dict[str, Any]]:
        patterns = [
            ("unit_price", "Preço unitário", "money", re.compile(r"(?:pre[cç]o\s*(?:unit[aá]rio)?|unit[.]?)\D{0,30}(R?\$?\s*\d[\d\.\,]*)", re.IGNORECASE), "high", 90),
            ("total_price", "Preço total", "money", re.compile(r"(?:total|valor\s*total)\D{0,30}(R?\$?\s*\d[\d\.\,]*)", re.IGNORECASE), "high", 88),
            ("delivery_days", "Prazo", "integer_days", re.compile(r"(?:prazo|entrega)\D{0,25}(\d{1,3})\s*dias?", re.IGNORECASE), "high", 88),
            ("freight", "Frete", "text", re.compile(r"(frete\D{0,45}(?:cif|fob|incluso|incluido|R?\$?\s*\d[\d\.\,]*))", re.IGNORECASE), "check", 74),
            ("payment_terms", "Condição de pagamento", "text", re.compile(r"((?:pagamento|condi[cç][aã]o)\D{0,80})", re.IGNORECASE), "check", 72),
            ("validity", "Validade", "text", re.compile(r"(validade\D{0,45}(?:\d{1,3}\s*dias?|\d{1,2}/\d{1,2}/\d{2,4}))", re.IGNORECASE), "check", 72),
            ("availability", "Disponibilidade", "text", re.compile(r"((?:dispon[ií]vel|disponibilidade|imediato|estoque)\D{0,60})", re.IGNORECASE), "check", 68),
        ]
        found: Dict[str, Dict[str, Any]] = {}
        for source in PurchasesService._extraction_sources(candidate):
            text = source["text"] or ""
            for field_name, label, value_type, pattern, confidence, score in patterns:
                if field_name in found:
                    continue
                match = pattern.search(text)
                if not match:
                    continue
                raw_value = match.group(1).strip()
                normalized_value = raw_value
                if value_type == "money":
                    normalized_value = PurchasesService._money_to_decimal_text(raw_value)
                elif value_type == "integer_days":
                    normalized_value = re.search(r"\d+", raw_value).group(0)
                found[field_name] = {
                    "field_name": field_name,
                    "label": label,
                    "raw_value": raw_value,
                    "normalized_value": normalized_value,
                    "value_type": value_type,
                    "confidence_level": confidence,
                    "confidence_score": score,
                    "source_type": source["source_type"],
                    "source_label": source["source_label"],
                    "attachment_id": source["attachment_id"],
                    "snippet": PurchasesService._evidence_snippet(text, match.start(), match.end()),
                    "char_start": match.start(),
                    "char_end": match.end(),
                }
        return list(found.values())

    @staticmethod
    def _extraction_payload(extraction: PurchaseResponseExtraction) -> Dict[str, Any]:
        evidences_by_field: Dict[uuid.UUID, List[Dict[str, Any]]] = {}
        evidence_payloads = []
        for evidence in extraction.evidences:
            payload = {
                "id": evidence.id,
                "extraction_id": evidence.extraction_id,
                "field_id": evidence.field_id,
                "attachment_id": evidence.attachment_id,
                "source_type": evidence.source_type,
                "source_label": evidence.source_label,
                "snippet": evidence.snippet,
                "char_start": evidence.char_start,
                "char_end": evidence.char_end,
                "page_number": evidence.page_number,
                "row_number": evidence.row_number,
                "confidence_level": evidence.confidence_level,
                "created_at": evidence.created_at,
            }
            evidence_payloads.append(payload)
            if evidence.field_id:
                evidences_by_field.setdefault(evidence.field_id, []).append(payload)
        return {
            "id": extraction.id,
            "candidate_id": extraction.candidate_id,
            "inbound_message_id": extraction.inbound_message_id,
            "quote_id": extraction.quote_id,
            "supplier_id": extraction.supplier_id,
            "status": extraction.status,
            "extractor_version": extraction.extractor_version,
            "confidence_summary": extraction.confidence_summary,
            "fields": [{
                "id": field.id,
                "extraction_id": field.extraction_id,
                "field_name": field.field_name,
                "label": field.label,
                "raw_value": field.raw_value,
                "normalized_value": field.normalized_value,
                "value_type": field.value_type,
                "confidence_level": field.confidence_level,
                "confidence_score": float(field.confidence_score or 0),
                "review_status": field.review_status,
                "source_type": field.source_type,
                "source_label": field.source_label,
                "evidences": evidences_by_field.get(field.id, []),
                "created_at": field.created_at,
                "updated_at": field.updated_at,
            } for field in extraction.fields],
            "evidences": evidence_payloads,
            "created_at": extraction.created_at,
            "updated_at": extraction.updated_at,
            "reviewed_at": extraction.reviewed_at,
        }

    @staticmethod
    def create_response_extraction(db: Session, candidate_id: uuid.UUID, current_user: User) -> Dict[str, Any]:
        candidate = PurchasesService.get_response_candidate(db, candidate_id, current_user)
        if not candidate.quote_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vincule a resposta a uma cotacao antes de extrair dados.",
            )
        existing = db.query(PurchaseResponseExtraction).filter(
            PurchaseResponseExtraction.candidate_id == candidate.id,
            PurchaseResponseExtraction.status.in_(["needs_review", "reviewing"]),
        ).order_by(desc(PurchaseResponseExtraction.created_at)).first()
        if existing:
            db.delete(existing)
            db.flush()

        extracted_fields = PurchasesService._extract_response_fields(candidate)
        confidence_summary = "low"
        if extracted_fields:
            high_count = sum(1 for item in extracted_fields if item["confidence_level"] == "high")
            confidence_summary = "high" if high_count >= 2 else "check"
        extraction = PurchaseResponseExtraction(
            candidate_id=candidate.id,
            inbound_message_id=candidate.inbound_message_id,
            quote_id=candidate.quote_id,
            supplier_id=candidate.supplier_id,
            status="needs_review",
            extractor_version="deterministic-v1",
            confidence_summary=confidence_summary,
            created_by=current_user.id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(extraction)
        db.flush()

        for item in extracted_fields:
            field = PurchaseResponseExtractedField(
                extraction_id=extraction.id,
                field_name=item["field_name"],
                label=item["label"],
                raw_value=item["raw_value"],
                normalized_value=item["normalized_value"],
                value_type=item["value_type"],
                confidence_level=item["confidence_level"],
                confidence_score=Decimal(item["confidence_score"]),
                review_status="pending",
                source_type=item["source_type"],
                source_label=item["source_label"],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            db.add(field)
            db.flush()
            db.add(PurchaseResponseEvidence(
                extraction_id=extraction.id,
                field_id=field.id,
                attachment_id=item["attachment_id"],
                source_type=item["source_type"],
                source_label=item["source_label"],
                snippet=item["snippet"],
                char_start=item["char_start"],
                char_end=item["char_end"],
                confidence_level=item["confidence_level"],
                created_at=datetime.now(timezone.utc),
            ))

        if not extracted_fields:
            extraction.status = "needs_manual_review"
        db.commit()
        return PurchasesService._extraction_payload(PurchasesService.get_response_extraction_model(db, extraction.id, current_user))

    @staticmethod
    def get_response_extraction_model(db: Session, extraction_id: uuid.UUID, current_user: User) -> PurchaseResponseExtraction:
        extraction = db.query(PurchaseResponseExtraction).options(
            joinedload(PurchaseResponseExtraction.fields).joinedload(PurchaseResponseExtractedField.evidences),
            joinedload(PurchaseResponseExtraction.evidences),
        ).filter(PurchaseResponseExtraction.id == extraction_id).first()
        if not extraction:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Extracao da resposta nao encontrada.")
        return extraction

    @staticmethod
    def get_response_extraction_for_candidate(db: Session, candidate_id: uuid.UUID, current_user: User) -> Dict[str, Any]:
        candidate = PurchasesService.get_response_candidate(db, candidate_id, current_user)
        extraction = db.query(PurchaseResponseExtraction).options(
            joinedload(PurchaseResponseExtraction.fields).joinedload(PurchaseResponseExtractedField.evidences),
            joinedload(PurchaseResponseExtraction.evidences),
        ).filter(PurchaseResponseExtraction.candidate_id == candidate.id).order_by(desc(PurchaseResponseExtraction.created_at)).first()
        if not extraction:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhuma extracao gerada para esta resposta.")
        return PurchasesService._extraction_payload(extraction)

    @staticmethod
    def review_response_extraction(db: Session, extraction_id: uuid.UUID, payload: Any, current_user: User) -> Dict[str, Any]:
        extraction = PurchasesService.get_response_extraction_model(db, extraction_id, current_user)
        fields_by_id = {field.id: field for field in extraction.fields}
        for decision_payload in payload.decisions:
            field = fields_by_id.get(decision_payload.field_id)
            if not field:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Campo extraido nao encontrado nesta extracao.")
            previous_value = field.normalized_value
            if decision_payload.decision == "accept":
                field.review_status = "accepted"
            elif decision_payload.decision == "correct":
                field.review_status = "corrected"
                field.normalized_value = decision_payload.reviewed_value
            else:
                field.review_status = "rejected"
            field.updated_at = datetime.now(timezone.utc)
            db.add(PurchaseResponseReviewDecision(
                extraction_id=extraction.id,
                field_id=field.id,
                decision=decision_payload.decision,
                previous_value=previous_value,
                reviewed_value=decision_payload.reviewed_value,
                reviewer_user_id=current_user.id,
                note=decision_payload.note,
                created_at=datetime.now(timezone.utc),
            ))
        extraction.status = "reviewed"
        extraction.reviewed_by = current_user.id
        extraction.reviewed_at = datetime.now(timezone.utc)
        extraction.updated_at = datetime.now(timezone.utc)
        db.commit()
        refreshed = PurchasesService.get_response_extraction_model(db, extraction.id, current_user)
        return {
            "extraction": PurchasesService._extraction_payload(refreshed),
            "human_message": "Campos revisados. Nenhum preco ou comparativo foi atualizado automaticamente.",
        }

    @staticmethod
    def get_rfq_drafts(db: Session, rfq_id: uuid.UUID, current_user: User) -> List[Dict[str, Any]]:
        rfq = PurchasesService.get_rfq(db, rfq_id, current_user)
        
        # Apenas ADMIN, MANAGER ou Compras podem visualizar rascunhos
        user_level = ApprovalService.get_user_module_level(db, current_user, "purchases")
        is_admin = current_user.role and current_user.role.name == "ADMIN"
        if LEVEL_VALUES[user_level] < LEVEL_VALUES[PermissionLevel.MANAGER] and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Apenas gerentes ou administradores de compras podem visualizar rascunhos."
            )

        drafts = []
        for rfq_sup in rfq.rfq_suppliers:
            drafts.append({
                "supplier_id": rfq_sup.supplier_id,
                "supplier_name": rfq_sup.supplier.person.name,
                "contact_email": rfq_sup.contact_email,
                "subject": rfq_sup.message_subject or "",
                "body": rfq_sup.message_body or ""
            })
        return drafts

    @staticmethod
    def create_rfq(db: Session, request_id: uuid.UUID, payload: Any, current_user: User) -> PurchaseRFQ:
        request = PurchasesService.get_purchase_request(db, request_id, current_user)

        if request.status not in ["APPROVED", "QUOTING", "RFQ_PREPARING"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="RFQs so podem ser criadas a partir de requisicoes APROVADAS."
            )

        # Apenas ADMIN, MANAGER ou Compras
        user_level = ApprovalService.get_user_module_level(db, current_user, "purchases")
        is_admin = current_user.role and current_user.role.name == "ADMIN"
        if LEVEL_VALUES[user_level] < LEVEL_VALUES[PermissionLevel.MANAGER] and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Apenas gerentes ou administradores de compras podem criar RFQs."
            )

        new_rfq = PurchaseRFQ(
            purchase_request_id=request.id,
            title=payload.title,
            status="DRAFT",
            deadline=payload.deadline,
            message_template=payload.message_template,
            created_by_user_id=current_user.id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(new_rfq)
        
        # Atualiza status da requisição
        request.status = "RFQ_PREPARING"
        request.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(new_rfq)

        # Atividade
        activity = PurchaseActivity(
            purchase_request_id=request.id,
            user_id=current_user.id,
            action="rfq.created",
            details={"rfq_id": str(new_rfq.id), "title": new_rfq.title},
            created_at=datetime.now(timezone.utc)
        )
        db.add(activity)
        db.commit()

        log_action(
            db=db,
            user_id=current_user.id,
            action="purchases.rfq.created",
            module="purchases",
            details={"request_id": str(request.id), "rfq_id": str(new_rfq.id)}
        )

        try:
            emit_event(
                db=db,
                event_type="purchase.rfq.created",
                aggregate_type="purchase_rfq",
                aggregate_id=str(new_rfq.id),
                module="purchases",
                payload={
                    "id": str(new_rfq.id),
                    "request_id": str(request.id),
                    "title": new_rfq.title,
                    "status": new_rfq.status,
                    "action_url": f"/purchases?quote={new_rfq.id}&step=suppliers",
                    "summary": f"Processo de RFQ '{new_rfq.title}' iniciado por {current_user.username}."
                },
                actor_user_id=current_user.id
            )
            db.commit()
        except Exception as e:
            print(f"Failed to emit purchase.rfq.created: {e}")

        return new_rfq

    @staticmethod
    def list_rfqs(db: Session, current_user: User) -> List[PurchaseRFQ]:
        # Permissões são validadas de forma semelhante a requisições
        query = db.query(PurchaseRFQ).options(
            joinedload(PurchaseRFQ.purchase_request),
            joinedload(PurchaseRFQ.rfq_suppliers).joinedload(PurchaseRFQSupplier.supplier)
        )
        user_level = ApprovalService.get_user_module_level(db, current_user, "purchases")
        is_admin = current_user.role and current_user.role.name == "ADMIN"
        if LEVEL_VALUES[user_level] < LEVEL_VALUES[PermissionLevel.MANAGER] and not is_admin:
            query = query.join(PurchaseRequest).filter(PurchaseRequest.requester_user_id == current_user.id)
            
        return query.order_by(desc(PurchaseRFQ.created_at)).all()

    @staticmethod
    def get_rfq(db: Session, rfq_id: uuid.UUID, current_user: User) -> PurchaseRFQ:
        rfq = db.query(PurchaseRFQ).filter(PurchaseRFQ.id == rfq_id).options(
            joinedload(PurchaseRFQ.purchase_request),
            joinedload(PurchaseRFQ.rfq_suppliers).joinedload(PurchaseRFQSupplier.supplier),
            joinedload(PurchaseRFQ.comparison)
        ).first()

        if not rfq:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="RFQ nao encontrada."
            )

        # Valida visibilidade
        user_level = ApprovalService.get_user_module_level(db, current_user, "purchases")
        is_admin = current_user.role and current_user.role.name == "ADMIN"
        if LEVEL_VALUES[user_level] < LEVEL_VALUES[PermissionLevel.MANAGER] and not is_admin:
            if rfq.purchase_request.requester_user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Acesso negado a esta RFQ."
                )

        return rfq

    @staticmethod
    def add_supplier_to_rfq(db: Session, rfq_id: uuid.UUID, payload: Any, current_user: User) -> PurchaseRFQSupplier:
        rfq = PurchasesService.get_rfq(db, rfq_id, current_user)

        user_level = ApprovalService.get_user_module_level(db, current_user, "purchases")
        is_admin = current_user.role and current_user.role.name == "ADMIN"
        if LEVEL_VALUES[user_level] < LEVEL_VALUES[PermissionLevel.MANAGER] and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissao insuficiente para adicionar fornecedor."
            )

        # Verifica se o fornecedor existe e está ativo no Master Data
        supplier = db.query(Supplier).filter(Supplier.id == payload.supplier_id, Supplier.status == "ACTIVE").first()
        if not supplier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Fornecedor {payload.supplier_id} nao cadastrado ou inativo no Master Data."
            )

        # Evita duplicidade na RFQ
        existing = db.query(PurchaseRFQSupplier).filter(
            PurchaseRFQSupplier.rfq_id == rfq.id,
            PurchaseRFQSupplier.supplier_id == supplier.id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Fornecedor ja associado a esta RFQ."
            )

        contact_email = payload.contact_email or supplier.preferred_contact_email or supplier.person.email
        if not contact_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nenhum e-mail de contato configurado para este fornecedor."
            )

        new_rfq_supplier = PurchaseRFQSupplier(
            rfq_id=rfq.id,
            supplier_id=supplier.id,
            contact_email=contact_email,
            status="DRAFT",
            created_at=datetime.now(timezone.utc)
        )
        db.add(new_rfq_supplier)
        db.commit()
        db.refresh(new_rfq_supplier)

        # Atividade
        activity = PurchaseActivity(
            purchase_request_id=rfq.purchase_request_id,
            user_id=current_user.id,
            action="rfq.supplier_added",
            details={"rfq_id": str(rfq.id), "supplier": supplier.person.name},
            created_at=datetime.now(timezone.utc)
        )
        db.add(activity)
        db.commit()

        log_action(
            db=db,
            user_id=current_user.id,
            action="purchases.rfq.supplier_added",
            module="purchases",
            details={"rfq_id": str(rfq.id), "supplier_id": str(supplier.id)}
        )

        try:
            emit_event(
                db=db,
                event_type="purchase.rfq.supplier.added",
                aggregate_type="purchase_rfq",
                aggregate_id=str(rfq.id),
                module="purchases",
                payload={
                    "rfq_id": str(rfq.id),
                    "supplier_id": str(supplier.id),
                    "supplier_name": supplier.person.name,
                    "status": "DRAFT",
                    "action_url": f"/purchases?quote={rfq.id}&step=suppliers",
                    "summary": f"Fornecedor '{supplier.person.name}' adicionado ao convite da RFQ '{rfq.title}'."
                },
                actor_user_id=current_user.id
            )
            db.commit()
        except Exception as e:
            print(f"Failed to emit purchase.rfq.supplier.added: {e}")

        return new_rfq_supplier

    @staticmethod
    def generate_rfq_drafts(db: Session, rfq_id: uuid.UUID, current_user: User) -> List[PurchaseRFQSupplier]:
        rfq = PurchasesService.get_rfq(db, rfq_id, current_user)

        user_level = ApprovalService.get_user_module_level(db, current_user, "purchases")
        is_admin = current_user.role and current_user.role.name == "ADMIN"
        if LEVEL_VALUES[user_level] < LEVEL_VALUES[PermissionLevel.MANAGER] and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissao insuficiente para gerar rascunhos de RFQ."
            )

        if not rfq.rfq_suppliers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nao e possivel gerar rascunhos sem fornecedores associados na RFQ."
            )

        # Template padrão de mensagem se não definido
        msg_template = rfq.message_template or (
            "Olá {supplier_name},\n\nGostaríamos de solicitar uma cotação para a requisição '{request_title}'.\n"
            "Por favor, nos responda até {deadline} com preços e prazos para os seguintes itens:\n\n"
            "{items_list}\n\nAtenciosamente,\nPortal Vesper"
        )

        # Monta a lista de itens solicitados
        items_lines = []
        for it in rfq.purchase_request.items:
            desc_val = it.free_text_description
            if it.product_item:
                desc_val = f"{it.product_item.name} (SKU: {it.product_item.sku})"
            elif it.service:
                desc_val = f"{it.service.name} (Cód: {it.service.code})"
            
            specs = f" ({it.specifications})" if it.specifications else ""
            items_lines.append(f"- {it.quantity} {it.unit_of_measure} de '{desc_val}'{specs}")
        items_list_str = "\n".join(items_lines)

        deadline_str = rfq.deadline.strftime("%d/%m/%Y") if rfq.deadline else "breve"

        for rfq_sup in rfq.rfq_suppliers:
            sup_name = rfq_sup.supplier.person.name
            
            subject = f"Solicitação de Cotação - Portal Vesper - RFQ: {rfq.title}"
            body = msg_template.format(
                supplier_name=sup_name,
                request_title=rfq.purchase_request.title,
                deadline=deadline_str,
                items_list=items_list_str
            )

            rfq_sup.message_subject = subject
            rfq_sup.message_body = body
            rfq_sup.status = "READY"
            rfq_sup.sent_at = None # Garantindo que NÃO envia SMTP real
            
        # Atualiza status da RFQ
        rfq.status = "READY_FOR_REVIEW"
        rfq.updated_at = datetime.now(timezone.utc)
        db.commit()

        # Atividade
        activity = PurchaseActivity(
            purchase_request_id=rfq.purchase_request_id,
            user_id=current_user.id,
            action="rfq.drafts_generated",
            details={"rfq_id": str(rfq.id)},
            created_at=datetime.now(timezone.utc)
        )
        db.add(activity)
        db.commit()

        log_action(
            db=db,
            user_id=current_user.id,
            action="purchases.rfq.drafts_generated",
            module="purchases",
            details={"rfq_id": str(rfq.id)}
        )

        for rfq_sup in rfq.rfq_suppliers:
            try:
                emit_event(
                    db=db,
                    event_type="purchase.rfq.draft_generated",
                    aggregate_type="purchase_rfq",
                    aggregate_id=str(rfq.id),
                    module="purchases",
                    payload={
                        "rfq_id": str(rfq.id),
                        "supplier_id": str(rfq_sup.supplier_id),
                        "contact_email": rfq_sup.contact_email,
                        "action_url": f"/purchases?quote={rfq.id}&step=preview",
                        "summary": f"Rascunho de e-mail de cotação preparado para '{rfq_sup.supplier.person.name}'."
                    },
                    actor_user_id=current_user.id
                )
                db.commit()
            except Exception as e:
                print(f"Failed to emit purchase.rfq.draft_generated: {e}")

        # Emite evento ready_for_review
        try:
            emit_event(
                db=db,
                event_type="purchase.rfq.ready_for_review",
                aggregate_type="purchase_rfq",
                aggregate_id=str(rfq.id),
                module="purchases",
                payload={
                    "id": str(rfq.id),
                    "request_id": str(rfq.purchase_request_id),
                    "title": rfq.title,
                    "status": rfq.status,
                    "action_url": f"/purchases?quote={rfq.id}&step=preview",
                    "summary": f"RFQ '{rfq.title}' está pronta para revisão com rascunhos de e-mail disponíveis."
                },
                actor_user_id=current_user.id
            )
            db.commit()
        except Exception as e:
            print(f"Failed to emit purchase.rfq.ready_for_review: {e}")

        return rfq.rfq_suppliers

    @staticmethod
    def create_quote_response(db: Session, rfq_id: uuid.UUID, payload: Any, current_user: User) -> PurchaseQuoteResponse:
        rfq = PurchasesService.get_rfq(db, rfq_id, current_user)

        user_level = ApprovalService.get_user_module_level(db, current_user, "purchases")
        is_admin = current_user.role and current_user.role.name == "ADMIN"
        if LEVEL_VALUES[user_level] < LEVEL_VALUES[PermissionLevel.MANAGER] and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissao insuficiente para registrar resposta de cotacao."
            )

        # Se houver rfq_supplier_id informado, valida associação
        rfq_supplier = None
        if payload.rfq_supplier_id:
            rfq_supplier = db.query(PurchaseRFQSupplier).filter(
                PurchaseRFQSupplier.id == payload.rfq_supplier_id,
                PurchaseRFQSupplier.rfq_id == rfq.id
            ).first()
            if not rfq_supplier:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Fornecedor convocado {payload.rfq_supplier_id} nao pertence a esta RFQ."
                )
            if rfq_supplier.supplier_id != payload.supplier_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Inconsistência de IDs entre rfq_supplier e supplier."
                )
        else:
            # Caso contrário, tenta localizar se esse fornecedor participa da RFQ
            rfq_supplier = db.query(PurchaseRFQSupplier).filter(
                PurchaseRFQSupplier.rfq_id == rfq.id,
                PurchaseRFQSupplier.supplier_id == payload.supplier_id
            ).first()

        supplier = db.query(Supplier).filter(Supplier.id == payload.supplier_id).first()
        if not supplier:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Fornecedor nao encontrado."
            )

        new_response = PurchaseQuoteResponse(
            rfq_supplier_id=rfq_supplier.id if rfq_supplier else None,
            supplier_id=supplier.id,
            total_amount=payload.total_amount,
            currency=payload.currency or "BRL",
            delivery_days=payload.delivery_days,
            payment_terms=payload.payment_terms,
            validity_date=payload.validity_date,
            raw_text=payload.raw_text,
            attachment_file_id=payload.attachment_file_id,
            parsed_json=payload.parsed_json,
            status="RECEIVED",
            created_at=datetime.now(timezone.utc)
        )
        db.add(new_response)
        db.commit()
        db.refresh(new_response)

        calculated_total = 0.0
        for line in payload.lines:
            # Se request_item_id fornecido, valida se ele pertence à requisição
            if line.request_item_id:
                req_item = db.query(PurchaseRequestItem).filter(
                    PurchaseRequestItem.id == line.request_item_id,
                    PurchaseRequestItem.purchase_request_id == rfq.purchase_request_id
                ).first()
                if not req_item:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Item solicitado {line.request_item_id} nao faz parte desta requisicao."
                    )
            
            line_total = float(line.unit_price) * float(line.quantity)
            calculated_total += line_total

            new_line = PurchaseQuoteLine(
                quote_response_id=new_response.id,
                request_item_id=line.request_item_id,
                description=line.description,
                quantity=line.quantity,
                unit_price=line.unit_price,
                total_price=line_total,
                delivery_days=line.delivery_days,
                notes=line.notes
            )
            db.add(new_line)

        # Se o total_amount for nulo ou difere, podemos sobrescrever com calculado
        if not new_response.total_amount:
            new_response.total_amount = calculated_total
        
        # Atualiza status de participação do fornecedor
        if rfq_supplier:
            rfq_supplier.status = "RESPONDED"
            rfq_supplier.response_received_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(new_response)

        # Se todos os fornecedores responderam, atualiza a RFQ para RESPONSES_RECEIVED
        pending_suppliers = db.query(PurchaseRFQSupplier).filter(
            PurchaseRFQSupplier.rfq_id == rfq.id,
            PurchaseRFQSupplier.status.in_(["DRAFT", "READY", "SENT"])
        ).count()

        if pending_suppliers == 0:
            rfq.status = "RESPONSES_RECEIVED"
            rfq.purchase_request.status = "QUOTES_RECEIVED"
            rfq.updated_at = datetime.now(timezone.utc)
            rfq.purchase_request.updated_at = datetime.now(timezone.utc)

        # Atividade
        activity = PurchaseActivity(
            purchase_request_id=rfq.purchase_request_id,
            user_id=current_user.id,
            action="rfq.response_received",
            details={
                "rfq_id": str(rfq.id),
                "supplier": supplier.person.name,
                "total_amount": float(new_response.total_amount or 0.0)
            },
            created_at=datetime.now(timezone.utc)
        )
        db.add(activity)
        db.commit()

        log_action(
            db=db,
            user_id=current_user.id,
            action="purchases.rfq.response_received",
            module="purchases",
            details={"rfq_id": str(rfq.id), "response_id": str(new_response.id)}
        )

        try:
            emit_event(
                db=db,
                event_type="purchase.quote_response.created",
                aggregate_type="purchase_rfq",
                aggregate_id=str(rfq.id),
                module="purchases",
                payload={
                    "id": str(new_response.id),
                    "rfq_id": str(rfq.id),
                    "supplier_id": str(supplier.id),
                    "supplier_name": supplier.person.name,
                    "total_amount": float(new_response.total_amount or 0.0),
                    "status": new_response.status,
                    "action_url": f"/purchases?quote={rfq.id}&step=preview",
                    "summary": f"Resposta de cotação de '{supplier.person.name}' registrada no valor de BRL {new_response.total_amount:.2f}."
                },
                actor_user_id=current_user.id
            )
            db.commit()
        except Exception as e:
            print(f"Failed to emit purchase.quote_response.created: {e}")

        return new_response

    @staticmethod
    def get_rfq_comparison(db: Session, rfq_id: uuid.UUID, current_user: User) -> Dict[str, Any]:
        rfq = PurchasesService.get_rfq(db, rfq_id, current_user)

        user_level = ApprovalService.get_user_module_level(db, current_user, "purchases")
        is_admin = current_user.role and current_user.role.name == "ADMIN"
        if LEVEL_VALUES[user_level] < LEVEL_VALUES[PermissionLevel.MANAGER] and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissao insuficiente para gerar comparativo."
            )

        # Recupera todas as respostas associadas
        supplier_ids = [rs.supplier_id for rs in rfq.rfq_suppliers]
        responses = db.query(PurchaseQuoteResponse).filter(
            PurchaseQuoteResponse.rfq_supplier_id.in_([rs.id for rs in rfq.rfq_suppliers]),
            PurchaseQuoteResponse.status != "REJECTED"
        ).options(joinedload(PurchaseQuoteResponse.lines), joinedload(PurchaseQuoteResponse.supplier)).all()

        if not responses:
            # Retorna comparativo vazio se não há propostas
            return {
                "rfq_id": rfq.id,
                "best_supplier_id": None,
                "best_supplier_name": None,
                "recommendation_summary": "Nenhuma cotacao recebida ainda.",
                "created_at": datetime.now(timezone.utc),
                "items_comparison": [],
                "suppliers_summary": []
            }

        # Constrói comparativo por linha de item solicitado
        items_comparison = []
        for req_item in rfq.purchase_request.items:
            offers = []
            description = req_item.free_text_description
            if req_item.product_item:
                description = req_item.product_item.name
            elif req_item.service:
                description = req_item.service.name

            for resp in responses:
                # Localiza a linha correspondente para esse request_item_id
                line = next((l for l in resp.lines if l.request_item_id == req_item.id), None)
                if line:
                    offers.append({
                        "supplier_id": resp.supplier_id,
                        "supplier_name": resp.supplier.person.name,
                        "unit_price": float(line.unit_price),
                        "total_price": float(line.total_price),
                        "delivery_days": line.delivery_days or resp.delivery_days,
                        "notes": line.notes
                    })
            items_comparison.append({
                "request_item_id": req_item.id,
                "description": description or "",
                "requested_quantity": float(req_item.quantity),
                "offers": offers
            })

        # Resumo dos fornecedores e determinação dos melhores
        suppliers_summary = []
        best_price_sup_id = None
        min_price = float('inf')
        best_deliv_sup_id = None
        min_deliv = float('inf')

        for resp in responses:
            total_amt = float(resp.total_amount or 0.0)
            
            # Média de dias de entrega
            days_list = [l.delivery_days for l in resp.lines if l.delivery_days is not None]
            avg_deliv = sum(days_list) / len(days_list) if days_list else resp.delivery_days

            sup_summary = {
                "supplier_id": resp.supplier_id,
                "supplier_name": resp.supplier.person.name,
                "total_amount": total_amt,
                "quote_response_id": resp.id,
                "average_delivery_days": float(avg_deliv) if avg_deliv is not None else None,
                "payment_terms": resp.payment_terms,
                "is_active": True,
                "is_best_price": False,
                "is_best_delivery": False
            }
            
            if total_amt < min_price:
                min_price = total_amt
                best_price_sup_id = resp.supplier_id
                
            if avg_deliv is not None and avg_deliv < min_deliv:
                min_deliv = avg_deliv
                best_deliv_sup_id = resp.supplier_id

            suppliers_summary.append(sup_summary)

        # Marca flags
        for s in suppliers_summary:
            if s["supplier_id"] == best_price_sup_id:
                s["is_best_price"] = True
            if s["supplier_id"] == best_deliv_sup_id:
                s["is_best_delivery"] = True

        best_sup = db.query(Supplier).filter(Supplier.id == best_price_sup_id).first()
        best_name = best_sup.person.name if best_sup else None

        deadline_txt = f" com prazo médio de {min_deliv:.1f} dias" if min_deliv != float('inf') else ""
        recommendation = f"Fornecedor '{best_name}' recomendado por apresentar o menor valor total de BRL {min_price:.2f}{deadline_txt}."

        # Salva ou atualiza comparativo no banco
        comp = db.query(PurchaseComparison).filter(PurchaseComparison.rfq_id == rfq.id).first()
        if not comp:
            comp = PurchaseComparison(
                rfq_id=rfq.id,
                best_supplier_id=best_price_sup_id,
                recommendation_summary=recommendation,
                created_at=datetime.now(timezone.utc)
            )
            db.add(comp)
        else:
            comp.best_supplier_id = best_price_sup_id
            comp.recommendation_summary = recommendation
        
        # Altera status da requisição e RFQ
        rfq.status = "CLOSED"
        rfq.purchase_request.status = "COMPARING"
        rfq.updated_at = datetime.now(timezone.utc)
        rfq.purchase_request.updated_at = datetime.now(timezone.utc)
        
        db.commit()

        # Atividade
        activity = PurchaseActivity(
            purchase_request_id=rfq.purchase_request_id,
            user_id=current_user.id,
            action="rfq.comparison_generated",
            details={"rfq_id": str(rfq.id), "best_supplier": best_name},
            created_at=datetime.now(timezone.utc)
        )
        db.add(activity)
        db.commit()

        log_action(
            db=db,
            user_id=current_user.id,
            action="purchases.rfq.comparison_generated",
            module="purchases",
            details={"rfq_id": str(rfq.id)}
        )

        try:
            emit_event(
                db=db,
                event_type="purchase.comparison.generated",
                aggregate_type="purchase_rfq",
                aggregate_id=str(rfq.id),
                module="purchases",
                payload={
                    "rfq_id": str(rfq.id),
                    "best_supplier_id": str(best_price_sup_id) if best_price_sup_id else None,
                    "recommendation_summary": recommendation,
                    "action_url": f"/purchases?quote={rfq.id}&step=preview",
                    "summary": f"Comparativo de propostas gerado para RFQ '{rfq.title}'. Melhor preço: '{best_name}'."
                },
                actor_user_id=current_user.id
            )
            db.commit()
        except Exception as e:
            print(f"Failed to emit purchase.comparison.generated: {e}")

        return {
            "rfq_id": rfq.id,
            "best_supplier_id": best_price_sup_id,
            "best_supplier_name": best_name,
            "recommendation_summary": recommendation,
            "created_at": comp.created_at,
            "items_comparison": items_comparison,
            "suppliers_summary": suppliers_summary
        }

    @staticmethod
    def send_rfq_emails(db: Session, rfq_id: uuid.UUID, current_user: User) -> PurchaseRFQ:
        """
        Dispara as cotações por e-mail para todos os fornecedores associados à RFQ diretamente,
        sem passar por ActionIntents bloqueantes de aprovação, desde que o usuário possua
        permissão normal do módulo.
        """
        from app.models.it import ITCredential
        from app.modules.it.credentials import decrypt_secret
        from app.core.config import settings
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        rfq = PurchasesService.get_rfq(db, rfq_id, current_user)

        user_level = ApprovalService.get_user_module_level(db, current_user, "purchases")
        is_admin = current_user.role and current_user.role.name == "ADMIN"
        if LEVEL_VALUES[user_level] < LEVEL_VALUES[PermissionLevel.NORMAL] and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissão insuficiente para disparar cotações."
            )

        if not rfq.rfq_suppliers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não é possível enviar RFQ sem fornecedores associados."
            )

        is_testing = settings.ENVIRONMENT.lower() in {"testing", "test"}

        if is_testing:
            # Em ambiente de testes, simula o envio
            for rfq_sup in rfq.rfq_suppliers:
                if rfq_sup.status not in ["SENT", "RESPONDED", "DECLINED"]:
                    rfq_sup.status = "SENT"
                    rfq_sup.sent_at = datetime.now(timezone.utc)
            rfq.status = "SENT"
            rfq.purchase_request.status = "RFQ_SENT"
            rfq.updated_at = datetime.now(timezone.utc)
            rfq.purchase_request.updated_at = datetime.now(timezone.utc)
            db.commit()
            
            # Registrar atividade
            activity = PurchaseActivity(
                purchase_request_id=rfq.purchase_request_id,
                user_id=current_user.id,
                action="rfq.sent",
                details={"rfq_id": str(rfq.id), "simulated": True},
                created_at=datetime.now(timezone.utc)
            )
            db.add(activity)
            db.commit()
            return rfq

        # Busca credencial SMTP no cofre
        smtp_credential = db.query(ITCredential).filter(
            (ITCredential.system_name == "SMTP") | (ITCredential.title == "SMTP"),
            ITCredential.is_active == True
        ).first()

        if not smtp_credential:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Credenciais SMTP não encontradas no Cofre de TI (Vault). "
                       "Configure a credencial 'SMTP' ativa no cofre para permitir o disparo real."
            )

        # Determina host e porta
        host = "smtp.gmail.com"
        port = 587
        if smtp_credential.url:
            if ":" in smtp_credential.url:
                parts = smtp_credential.url.split(":")
                host = parts[0]
                try:
                    port = int(parts[1])
                except ValueError:
                    pass
            else:
                host = smtp_credential.url

        try:
            smtp_pass = decrypt_secret(smtp_credential.secret_encrypted)
            smtp_user = smtp_credential.username
            
            # Setup SMTP
            if port == 465:
                server = smtplib.SMTP_SSL(host, port, timeout=10)
            else:
                server = smtplib.SMTP(host, port, timeout=10)
                server.starttls()

            server.login(smtp_user, smtp_pass)

            for rfq_sup in rfq.rfq_suppliers:
                if rfq_sup.status not in ["SENT", "RESPONDED", "DECLINED"]:
                    subject = rfq_sup.message_subject or f"Solicitação de Cotação - {rfq.title}"
                    body = rfq_sup.message_body or f"Por favor, envie sua cotação para {rfq.title}."

                    msg = MIMEMultipart()
                    msg['From'] = smtp_user
                    msg['To'] = rfq_sup.contact_email
                    msg['Subject'] = subject
                    msg.attach(MIMEText(body, 'plain', 'utf-8'))

                    server.sendmail(smtp_user, rfq_sup.contact_email, msg.as_string())

                    rfq_sup.status = "SENT"
                    rfq_sup.sent_at = datetime.now(timezone.utc)

            server.quit()

            rfq.status = "SENT"
            rfq.purchase_request.status = "RFQ_SENT"
            rfq.updated_at = datetime.now(timezone.utc)
            rfq.purchase_request.updated_at = datetime.now(timezone.utc)
            db.commit()

            # Registrar atividade
            activity = PurchaseActivity(
                purchase_request_id=rfq.purchase_request_id,
                user_id=current_user.id,
                action="rfq.sent",
                details={"rfq_id": str(rfq.id)},
                created_at=datetime.now(timezone.utc)
            )
            db.add(activity)
            db.commit()

            log_action(
                db=db,
                user_id=current_user.id,
                action="purchases.rfq.sent",
                module="purchases",
                details={"rfq_id": str(rfq.id)}
            )

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Falha de SMTP ao disparar e-mails de cotação: {str(e)}"
            )

        return rfq

    @staticmethod
    def resend_supplier_email(db: Session, rfq_id: uuid.UUID, supplier_id: uuid.UUID, current_user: User) -> PurchaseRFQSupplier:
        """
        Reenvia o e-mail de cotação para um fornecedor específico na RFQ.
        """
        from app.models.it import ITCredential
        from app.modules.it.credentials import decrypt_secret
        from app.core.config import settings
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        rfq = PurchasesService.get_rfq(db, rfq_id, current_user)

        user_level = ApprovalService.get_user_module_level(db, current_user, "purchases")
        is_admin = current_user.role and current_user.role.name == "ADMIN"
        if LEVEL_VALUES[user_level] < LEVEL_VALUES[PermissionLevel.NORMAL] and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissão insuficiente para reenviar e-mail de cotação."
            )

        rfq_sup = db.query(PurchaseRFQSupplier).filter(
            PurchaseRFQSupplier.rfq_id == rfq_id,
            PurchaseRFQSupplier.supplier_id == supplier_id
        ).first()

        if not rfq_sup:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Fornecedor não associado a esta RFQ."
            )

        is_testing = settings.ENVIRONMENT.lower() in {"testing", "test"}

        if is_testing:
            rfq_sup.status = "SENT"
            rfq_sup.sent_at = datetime.now(timezone.utc)
            db.commit()
            return rfq_sup

        smtp_credential = db.query(ITCredential).filter(
            (ITCredential.system_name == "SMTP") | (ITCredential.title == "SMTP"),
            ITCredential.is_active == True
        ).first()

        if not smtp_credential:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Credenciais SMTP não encontradas no Cofre de TI (Vault). "
                       "Configure a credencial 'SMTP' ativa no cofre para permitir o disparo real."
            )

        host = "smtp.gmail.com"
        port = 587
        if smtp_credential.url:
            if ":" in smtp_credential.url:
                parts = smtp_credential.url.split(":")
                host = parts[0]
                try:
                    port = int(parts[1])
                except ValueError:
                    pass
            else:
                host = smtp_credential.url

        try:
            smtp_pass = decrypt_secret(smtp_credential.secret_encrypted)
            smtp_user = smtp_credential.username

            if port == 465:
                server = smtplib.SMTP_SSL(host, port, timeout=10)
            else:
                server = smtplib.SMTP(host, port, timeout=10)
                server.starttls()

            server.login(smtp_user, smtp_pass)

            subject = rfq_sup.message_subject or f"Reenvio: Solicitação de Cotação - {rfq.title}"
            body = rfq_sup.message_body or f"Por favor, envie sua cotação para {rfq.title}."

            msg = MIMEMultipart()
            msg['From'] = smtp_user
            msg['To'] = rfq_sup.contact_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain', 'utf-8'))

            server.sendmail(smtp_user, rfq_sup.contact_email, msg.as_string())
            server.quit()

            rfq_sup.status = "SENT"
            rfq_sup.sent_at = datetime.now(timezone.utc)
            db.commit()

            # Atividade
            activity = PurchaseActivity(
                purchase_request_id=rfq.purchase_request_id,
                user_id=current_user.id,
                action="rfq.supplier_resent",
                details={"rfq_id": str(rfq.id), "supplier_id": str(supplier_id)},
                created_at=datetime.now(timezone.utc)
            )
            db.add(activity)
            db.commit()

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Falha de SMTP ao reenviar e-mail: {str(e)}"
            )

        return rfq_sup

    @staticmethod
    def choose_supplier(db: Session, rfq_id: uuid.UUID, quote_response_id: uuid.UUID, current_user: User) -> PurchaseRequest:
        """
        Homologa a proposta vencedora (Quote Response) para uma RFQ, atualizando o status do processo
        e definindo diretamente os novos preços de referência homologados se o usuário for MANAGER ou superior.
        """
        rfq = PurchasesService.get_rfq(db, rfq_id, current_user)

        user_level = ApprovalService.get_user_module_level(db, current_user, "purchases")
        is_admin = current_user.role and current_user.role.name == "ADMIN"
        if LEVEL_VALUES[user_level] < LEVEL_VALUES[PermissionLevel.MANAGER] and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissão insuficiente para escolher a proposta vencedora (requer MANAGER)."
            )

        quote_resp = db.query(PurchaseQuoteResponse).filter(
            PurchaseQuoteResponse.id == quote_response_id
        ).first()

        if not quote_resp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proposta/Resposta de cotação não encontrada."
            )

        # 1. Atualiza status do fluxo
        rfq.status = "CLOSED"
        rfq.purchase_request.status = "ORDERED"
        rfq.purchase_request.selected_quotation_id = quote_resp.id
        rfq.updated_at = datetime.now(timezone.utc)
        rfq.purchase_request.updated_at = datetime.now(timezone.utc)
        db.commit()

        # 2. Homologa os preços das linhas como preços de referência ativos
        for line in quote_resp.lines:
            if line.request_item_id:
                req_item = db.query(PurchaseRequestItem).filter(
                    PurchaseRequestItem.id == line.request_item_id
                ).first()
                
                # Só homologa produtos reais, pulando textos livres ou serviços
                if req_item and req_item.item_id:
                    # Log imutável no histórico
                    new_history = PurchasePriceHistory(
                        product_item_id=req_item.item_id,
                        supplier_id=quote_resp.supplier_id,
                        evidence_id=None,
                        rfq_id=rfq.id,
                        quote_response_id=quote_resp.id,
                        unit_price=Decimal(str(line.unit_price)),
                        quantity=Decimal(str(line.quantity)),
                        total_amount=Decimal(str(line.total_price)),
                        currency=quote_resp.currency or "BRL",
                        unit_of_measure=req_item.unit_of_measure,
                        observed_at=datetime.now(timezone.utc),
                        source_type="RFQ_RESPONSE",
                        source_id=str(rfq.id),
                        created_by_user_id=current_user.id,
                        created_at=datetime.now(timezone.utc)
                    )
                    db.add(new_history)
                    db.flush()

                    # Inativa os preços de referência ativos anteriores
                    old_refs = db.query(PurchasePriceReference).filter(
                        PurchasePriceReference.product_item_id == req_item.item_id,
                        PurchasePriceReference.supplier_id == quote_resp.supplier_id,
                        PurchasePriceReference.is_active == True
                    ).all()
                    for ref in old_refs:
                        ref.is_active = False
                        ref.updated_at = datetime.now(timezone.utc)

                    # Cadastra novo preço de referência ativo
                    new_ref = PurchasePriceReference(
                        product_item_id=req_item.item_id,
                        supplier_id=quote_resp.supplier_id,
                        current_unit_price=Decimal(str(line.unit_price)),
                        currency=quote_resp.currency or "BRL",
                        unit_of_measure=req_item.unit_of_measure,
                        source_history_id=new_history.id,
                        source_evidence_id=None,
                        approved_by_user_id=current_user.id,
                        approved_at=datetime.now(timezone.utc),
                        notes=f"Homologado diretamente via escolha de proposta na RFQ {rfq.title}",
                        is_active=True,
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc)
                    )
                    db.add(new_ref)

        db.commit()

        # Atividade
        activity = PurchaseActivity(
            purchase_request_id=rfq.purchase_request_id,
            user_id=current_user.id,
            action="rfq.supplier_chosen",
            details={
                "rfq_id": str(rfq.id),
                "quote_response_id": str(quote_resp.id),
                "supplier_name": quote_resp.supplier.person.name,
                "total_amount": float(quote_resp.total_amount or 0.0)
            },
            created_at=datetime.now(timezone.utc)
        )
        db.add(activity)
        db.commit()

        # Evento
        try:
            emit_event(
                db=db,
                event_type="purchase.rfq.supplier.chosen",
                aggregate_type="purchase_rfq",
                aggregate_id=str(rfq.id),
                module="purchases",
                payload={
                    "rfq_id": str(rfq.id),
                    "quote_response_id": str(quote_resp.id),
                    "supplier_id": str(quote_resp.supplier_id),
                    "total_amount": float(quote_resp.total_amount or 0.0),
                    "summary": f"Proposta do fornecedor {quote_resp.supplier.person.name} escolhida para a RFQ {rfq.title}."
                },
                actor_user_id=current_user.id
            )
            db.commit()
        except Exception as e:
            print(f"Failed to emit purchase.rfq.supplier.chosen: {e}")

        # Retorna a requisição atualizada
        return PurchasesService.get_purchase_request(db, rfq.purchase_request_id, current_user)

    @staticmethod
    def request_send_approval(db: Session, rfq_id: uuid.UUID, current_user: User) -> dict:
        """
        Compatibility endpoint for older clients. Sending a supplier quote
        request is normal Purchases work, not a purchase order or spend.
        It is audited but does not create approval or ActionIntent rows.
        """
        rfq = PurchasesService.get_rfq(db, rfq_id, current_user)

        user_level = ApprovalService.get_user_module_level(db, current_user, "purchases")
        is_admin = current_user.role and current_user.role.name == "ADMIN"
        if LEVEL_VALUES[user_level] < LEVEL_VALUES[PermissionLevel.NORMAL] and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissao insuficiente para enviar cotacao."
            )

        if not rfq.rfq_suppliers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nao e possivel enviar cotacao sem fornecedores associados."
            )

        # No current policy approval is required for supplier quote requests.
        activity = PurchaseActivity(
            purchase_request_id=rfq.purchase_request_id,
            user_id=current_user.id,
            action="rfq.send_approval_skipped",
            details={"rfq_id": str(rfq.id), "reason": "Supplier quote requests do not require formal approval."},
            created_at=datetime.now(timezone.utc)
        )
        db.add(activity)
        db.commit()

        log_action(
            db=db,
            user_id=current_user.id,
            action="purchases.rfq.send_approval_skipped",
            module="purchases",
            details={"rfq_id": str(rfq.id)}
        )

        try:
            emit_event(
                db=db,
                event_type="purchase.rfq.send_approval.skipped",
                aggregate_type="purchase_rfq",
                aggregate_id=str(rfq.id),
                module="purchases",
                payload={
                    "rfq_id": str(rfq.id),
                    "proposed_action": "send_rfq",
                    "summary": f"A cotacao '{rfq.title}' nao precisa de aprovacao formal para envio."
                },
                actor_user_id=current_user.id
            )
            db.commit()
        except Exception as e:
            print(f"Failed to emit purchase.rfq.send_approval.skipped: {e}")

        return {
            "status": "no_approval_required",
            "rfq_id": str(rfq.id),
            "rfq_status": rfq.status,
            "message": "Cotacao nao exige aprovacao. Use o envio direto apos revisar a mensagem."
        }

    # ---------------------------------------------------------------------------
    # Métricas / Dashboard
    # ---------------------------------------------------------------------------
    @staticmethod
    def _purchase_stage(status_value: str) -> Dict[str, str]:
        status_upper = (status_value or "").upper()
        if status_upper in {"DRAFT", "REQUESTED", "APPROVED", "RFQ_PREPARING"}:
            return {"key": "preparation", "label": "Em preparacao", "next_action": "Preparar cotacao"}
        if status_upper in {"RFQ_SENT", "SENT"}:
            return {"key": "quoting", "label": "Em cotacao", "next_action": "Acompanhar respostas"}
        if status_upper in {"QUOTES_RECEIVED", "RESPONSES_RECEIVED", "COMPARING"}:
            return {"key": "analysis", "label": "Em analise", "next_action": "Comparar respostas"}
        if status_upper in {"ORDERED", "PURCHASE_ORDER_PREPARED", "PURCHASE_ORDER_SENT"}:
            return {"key": "order", "label": "Em pedido", "next_action": "Acompanhar pedido"}
        if status_upper in {"AWAITING_DELIVERY", "PARTIAL_DELIVERY", "DELIVERED"}:
            return {"key": "delivery", "label": "Em entrega", "next_action": "Registrar recebimento"}
        if status_upper in {"CANCELLED", "REJECTED", "ARCHIVED", "FINALIZED"}:
            return {"key": "done", "label": "Finalizadas", "next_action": "Abrir historico"}
        return {"key": "preparation", "label": "Em preparacao", "next_action": "Abrir"}

    @staticmethod
    def _purchase_status_label(status_value: str) -> str:
        labels = {
            "DRAFT": "Rascunho",
            "REQUESTED": "Solicitada",
            "PENDING_APPROVAL": "Aguardando aprovacao",
            "APPROVED": "Pronta para cotacao",
            "RFQ_PREPARING": "Preparando fornecedores",
            "READY_FOR_REVIEW": "Pronta para revisar",
            "RFQ_SENT": "Aguardando respostas",
            "QUOTES_RECEIVED": "Respostas recebidas",
            "COMPARING": "Pronta para comparar",
            "ORDERED": "Pedido preparado",
            "DELIVERED": "Entregue",
            "CANCELLED": "Cancelada",
            "REJECTED": "Rejeitada",
        }
        return labels.get((status_value or "").upper(), status_value or "Sem status")

    @staticmethod
    def _is_past_deadline(value: Optional[datetime]) -> bool:
        if not value:
            return False
        now = datetime.now(timezone.utc)
        candidate = value
        if candidate.tzinfo is None:
            candidate = candidate.replace(tzinfo=timezone.utc)
        return candidate < now

    @staticmethod
    def get_attention(db: Session, current_user: User, limit: int = 20) -> List[Dict[str, Any]]:
        requests = PurchasesService.list_purchase_requests(db, current_user)
        rfqs = PurchasesService.list_rfqs(db, current_user)
        request_ids = [req.id for req in requests]
        attention: List[Dict[str, Any]] = []

        response_candidates = db.query(PurchaseResponseCandidate).options(
            joinedload(PurchaseResponseCandidate.inbound_message),
            joinedload(PurchaseResponseCandidate.quote),
            joinedload(PurchaseResponseCandidate.supplier).joinedload(Supplier.person),
        ).filter(
            PurchaseResponseCandidate.candidate_status.in_(["needs_review", "suggested", "unidentified"])
        ).order_by(desc(PurchaseResponseCandidate.created_at)).limit(limit).all()
        for candidate in response_candidates:
            supplier_name = PurchasesService._supplier_name(candidate.supplier)
            if candidate.candidate_status == "unidentified":
                description = "Mensagem recebida sem cotacao identificada. Vincule manualmente antes de extrair dados."
                severity = "warning"
            else:
                description = f"Confira a resposta de {supplier_name or candidate.inbound_message.from_email} antes de comparar."
                severity = "warning" if candidate.confidence_level != "high" else "info"
            attention.append({
                "id": f"response-candidate:{candidate.id}",
                "type": "response_to_review",
                "title": "Resposta recebida para revisar",
                "description": description,
                "severity": severity,
                "status": candidate.candidate_status,
                "quote_id": candidate.quote_id,
                "supplier_id": candidate.supplier_id,
                "supplier_name": supplier_name,
                "action_label": "Revisar resposta",
                "updated_at": candidate.created_at,
            })

        for rfq in rfqs:
            if rfq.status == "READY_FOR_REVIEW":
                attention.append({
                    "id": f"rfq-ready:{rfq.id}",
                    "type": "quote_ready_for_review",
                    "title": "Cotacao pronta para revisar",
                    "description": f"Revise os rascunhos de {rfq.title} antes de enviar aos fornecedores.",
                    "severity": "info",
                    "status": rfq.status,
                    "quote_id": rfq.id,
                    "request_id": rfq.purchase_request_id,
                    "action_label": "Revisar e enviar",
                    "updated_at": rfq.updated_at,
                })

            if rfq.status in {"SENT", "RFQ_SENT"} and PurchasesService._is_past_deadline(rfq.deadline):
                pending_suppliers = [
                    rfq_supplier for rfq_supplier in rfq.rfq_suppliers
                    if rfq_supplier.status not in {"RESPONDED", "DECLINED"}
                ]
                if pending_suppliers:
                    attention.append({
                        "id": f"rfq-overdue:{rfq.id}",
                        "type": "supplier_without_response",
                        "title": "Fornecedor sem resposta",
                        "description": f"{len(pending_suppliers)} fornecedor(es) passaram do prazo em {rfq.title}.",
                        "severity": "warning",
                        "status": rfq.status,
                        "quote_id": rfq.id,
                        "request_id": rfq.purchase_request_id,
                        "action_label": "Ver pendencias",
                        "updated_at": rfq.updated_at,
                    })

            for rfq_supplier in rfq.rfq_suppliers:
                if rfq_supplier.status == "FAILED":
                    supplier_name = None
                    if rfq_supplier.supplier and rfq_supplier.supplier.person:
                        supplier_name = rfq_supplier.supplier.person.name
                    attention.append({
                        "id": f"rfq-supplier-failed:{rfq_supplier.id}",
                        "type": "send_failed",
                        "title": "Falha no envio da cotacao",
                        "description": f"Revise o envio para {supplier_name or 'fornecedor'} antes de tentar novamente.",
                        "severity": "danger",
                        "status": rfq_supplier.status,
                        "quote_id": rfq.id,
                        "request_id": rfq.purchase_request_id,
                        "supplier_id": rfq_supplier.supplier_id,
                        "supplier_name": supplier_name,
                        "action_label": "Corrigir envio",
                        "updated_at": rfq_supplier.created_at,
                    })

        if request_ids:
            responses = db.query(PurchaseQuoteResponse).options(
                joinedload(PurchaseQuoteResponse.supplier),
                joinedload(PurchaseQuoteResponse.rfq_supplier).joinedload(PurchaseRFQSupplier.rfq),
            ).filter(
                PurchaseQuoteResponse.status.in_(["RECEIVED", "PARSED", "NEEDS_REVIEW"]),
                PurchaseQuoteResponse.rfq_supplier.has(
                    PurchaseRFQSupplier.rfq.has(PurchaseRFQ.purchase_request_id.in_(request_ids))
                ),
            ).order_by(desc(PurchaseQuoteResponse.created_at)).limit(limit).all()

            for response in responses:
                supplier_name = None
                if response.supplier and response.supplier.person:
                    supplier_name = response.supplier.person.name
                rfq = response.rfq_supplier.rfq if response.rfq_supplier else None
                attention.append({
                    "id": f"quote-response:{response.id}",
                    "type": "response_to_review",
                    "title": "Resposta recebida para revisar",
                    "description": f"Confira os dados enviados por {supplier_name or 'fornecedor'} antes de comparar.",
                    "severity": "warning" if response.status == "NEEDS_REVIEW" else "info",
                    "status": response.status,
                    "quote_id": rfq.id if rfq else None,
                    "request_id": rfq.purchase_request_id if rfq else None,
                    "supplier_id": response.supplier_id,
                    "supplier_name": supplier_name,
                    "action_label": "Revisar resposta",
                    "updated_at": response.created_at,
                })

        for request in requests:
            if request.status in {"QUOTES_RECEIVED", "COMPARING"}:
                attention.append({
                    "id": f"request-compare:{request.id}",
                    "type": "ready_to_compare",
                    "title": "Cotacao pronta para comparar",
                    "description": f"{request.title} ja tem respostas registradas para analise.",
                    "severity": "info",
                    "status": request.status,
                    "request_id": request.id,
                    "action_label": "Abrir comparativo",
                    "updated_at": request.updated_at,
                })
            elif request.status == "ORDERED":
                attention.append({
                    "id": f"request-order:{request.id}",
                    "type": "order_waiting_delivery",
                    "title": "Pedido aguardando acompanhamento",
                    "description": f"Acompanhe entrega e recebimento de {request.title}.",
                    "severity": "info",
                    "status": request.status,
                    "request_id": request.id,
                    "action_label": "Acompanhar pedido",
                    "updated_at": request.updated_at,
                })

        attention.sort(key=lambda item: item.get("updated_at") or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        return attention[:limit]

    @staticmethod
    def get_overview(db: Session, current_user: User) -> Dict[str, Any]:
        requests = PurchasesService.list_purchase_requests(db, current_user)
        rfqs = PurchasesService.list_rfqs(db, current_user)
        summary = PurchasesService.get_summary(db, current_user)
        attention = PurchasesService.get_attention(db, current_user, limit=8)
        queue_counts = PurchasesService._queue_counts(requests)

        group_order = [
            ("preparation", "Em preparacao"),
            ("quoting", "Em cotacao"),
            ("analysis", "Em analise"),
            ("order", "Em pedido"),
            ("delivery", "Em entrega"),
            ("done", "Finalizadas"),
        ]
        group_counts = {key: 0 for key, _ in group_order}

        rfqs_by_request: Dict[uuid.UUID, List[PurchaseRFQ]] = {}
        for rfq in rfqs:
            rfqs_by_request.setdefault(rfq.purchase_request_id, []).append(rfq)

        ongoing_quotes: List[Dict[str, Any]] = []
        for request in requests:
            stage = PurchasesService._purchase_stage(request.status)
            group_counts[stage["key"]] = group_counts.get(stage["key"], 0) + 1
            if stage["key"] == "done":
                continue

            request_rfqs = rfqs_by_request.get(request.id, [])
            suppliers_count = sum(len(rfq.rfq_suppliers) for rfq in request_rfqs)
            responses_count = db.query(func.count(PurchaseQuoteResponse.id)).join(
                PurchaseRFQSupplier,
                PurchaseQuoteResponse.rfq_supplier_id == PurchaseRFQSupplier.id,
            ).join(
                PurchaseRFQ,
                PurchaseRFQSupplier.rfq_id == PurchaseRFQ.id,
            ).filter(PurchaseRFQ.purchase_request_id == request.id).scalar() or 0
            items_count = len(request.items)

            if items_count and suppliers_count:
                coverage_label = f"{suppliers_count} fornecedor(es) para {items_count} item(ns)"
            elif items_count:
                coverage_label = f"{items_count} item(ns), sem fornecedor selecionado"
            else:
                coverage_label = "Sem itens"

            ongoing_quotes.append({
                "request_id": request.id,
                "title": request.title,
                "status": request.status,
                "status_label": PurchasesService._purchase_status_label(request.status),
                "stage": stage["label"],
                "items_count": items_count,
                "suppliers_count": suppliers_count,
                "responses_count": responses_count,
                "coverage_label": coverage_label,
                "next_action": stage["next_action"],
                "responsible": request.requester.username if request.requester else None,
                "updated_at": request.updated_at,
            })

        return {
            "summary": summary,
            "queue_counts": queue_counts,
            "status_groups": [
                {"key": key, "label": label, "count": group_counts.get(key, 0)}
                for key, label in group_order
            ],
            "attention": attention,
            "ongoing_quotes": ongoing_quotes[:20],
        }

    @staticmethod
    def get_summary(db: Session, current_user: User) -> Dict[str, Any]:
        requests = PurchasesService.list_purchase_requests(db, current_user)
        suppliers = db.query(Supplier).all()

        drafts = 0
        pending_approval = 0
        approved = 0
        quoting = 0
        ordered = 0
        delivered = 0
        cancelled = 0
        estimated_value_open = 0.0

        for r in requests:
            status_lower = r.status.upper()
            if status_lower == "DRAFT":
                drafts += 1
            elif status_lower == "PENDING_APPROVAL":
                pending_approval += 1
                estimated_value_open += float(r.estimated_total or 0.0)
            elif status_lower in ["APPROVED", "RFQ_PREPARING", "RFQ_SENT"]:
                approved += 1
                estimated_value_open += float(r.estimated_total or 0.0)
            elif status_lower in ["QUOTING", "QUOTES_RECEIVED", "COMPARING"]:
                quoting += 1
                estimated_value_open += float(r.estimated_total or 0.0)
            elif status_lower == "ORDERED":
                ordered += 1
            elif status_lower == "DELIVERED":
                delivered += 1
            elif status_lower == "CANCELLED":
                cancelled += 1

        total_suppliers = len(suppliers)
        active_suppliers = sum(1 for s in suppliers if s.status == "ACTIVE")
        
        # Cotações pendentes (daquelas requisições APPROVED/QUOTING)
        open_req_ids = [r.id for r in requests if r.status in ["APPROVED", "QUOTING"]]
        total_quotations_pending = 0
        if open_req_ids:
            total_quotations_pending = db.query(func.count(Quotation.id)).filter(
                Quotation.purchase_request_id.in_(open_req_ids),
                Quotation.status == "PENDING"
            ).scalar() or 0

        return {
            "total_requests": len(requests),
            "drafts": drafts,
            "pending_approval": pending_approval,
            "approved": approved,
            "quoting": quoting,
            "ordered": ordered,
            "delivered": delivered,
            "cancelled": cancelled,
            "total_suppliers": total_suppliers,
            "active_suppliers": active_suppliers,
            "total_quotations_pending": total_quotations_pending,
            "estimated_value_open": estimated_value_open
        }

    # ---------------------------------------------------------------------------
    # Rastreabilidade de Preços de Compra (Price Traceability)
    # ---------------------------------------------------------------------------
    @staticmethod
    def _ensure_purchase_access(
        db: Session,
        current_user: User,
        required_level: PermissionLevel = PermissionLevel.READ_ONLY,
        message: str = "Permissao insuficiente para acessar Compras.",
    ) -> None:
        user_level = ApprovalService.get_user_module_level(db, current_user, "purchases")
        is_admin = current_user.role and current_user.role.name == "ADMIN"
        if not is_admin and LEVEL_VALUES[user_level] < LEVEL_VALUES[required_level]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=message)

    @staticmethod
    def _family_name_for_item(item: ProductItem) -> str:
        if item.family:
            return item.family.name
        if item.category:
            return item.category.strip().upper()
        return (item.name.split(" - ")[0] or item.name).strip().upper()

    @staticmethod
    def _variation_name_for_item(item: ProductItem) -> str:
        attrs = item.attributes or {}
        variation = attrs.get("variation_name") or attrs.get("variacao") or attrs.get("medida")
        if variation:
            return str(variation)
        family_name = PurchasesService._family_name_for_item(item)
        cleaned = item.name.replace(family_name, "", 1).strip(" -|")
        return cleaned or item.name

    @staticmethod
    def _serialize_product_price_variation(db: Session, item: ProductItem) -> Dict[str, Any]:
        active_ref = db.query(PurchasePriceReference).options(
            joinedload(PurchasePriceReference.supplier).joinedload(Supplier.person)
        ).filter(
            PurchasePriceReference.product_item_id == item.id,
            PurchasePriceReference.is_active == True
        ).order_by(desc(PurchasePriceReference.updated_at)).first()

        history_count = db.query(func.count(PurchasePriceHistory.id)).filter(
            PurchasePriceHistory.product_item_id == item.id
        ).scalar() or 0
        supplier_rows = db.query(PurchasePriceHistory.supplier_id).filter(
            PurchasePriceHistory.product_item_id == item.id,
            PurchasePriceHistory.supplier_id != None
        ).distinct().all()
        ref_supplier_rows = db.query(PurchasePriceReference.supplier_id).filter(
            PurchasePriceReference.product_item_id == item.id,
            PurchasePriceReference.supplier_id != None
        ).distinct().all()
        suppliers_count = len({row[0] for row in supplier_rows + ref_supplier_rows if row[0]})

        attrs = item.attributes or {}
        family_name = PurchasesService._family_name_for_item(item)
        variation_name = PurchasesService._variation_name_for_item(item)
        supplier = active_ref.supplier if active_ref else None
        supplier_name = supplier.person.name if supplier and supplier.person else None

        return {
            "id": item.id,
            "family_id": item.family_id,
            "family_name": family_name,
            "name": item.name,
            "short_name": variation_name,
            "variation_name": variation_name,
            "attributes": attrs,
            "unit_of_measure": item.unit_of_measure,
            "category": item.category,
            "current_price": active_ref.current_unit_price if active_ref else None,
            "currency": active_ref.currency if active_ref else "BRL",
            "supplier_id": active_ref.supplier_id if active_ref else None,
            "supplier_name": supplier_name,
            "last_updated_at": active_ref.updated_at if active_ref else None,
            "history_count": history_count,
            "suppliers_count": suppliers_count,
            "description": item.description,
            "technical_details": {
                "id": str(item.id),
                "sku": item.sku,
                "canonical_key": item.canonical_key,
                "item_type": item.item_type,
            },
        }

    @staticmethod
    def _build_family_rows(db: Session, items: List[ProductItem]) -> List[Dict[str, Any]]:
        grouped: Dict[str, Dict[str, Any]] = {}
        for item in items:
            family_name = PurchasesService._family_name_for_item(item)
            family_key = str(item.family_id) if item.family_id else family_name
            if family_key not in grouped:
                grouped[family_key] = {
                    "family_id": item.family_id,
                    "family_name": family_name,
                    "description": item.family.description if item.family else None,
                    "variations": [],
                }
            grouped[family_key]["variations"].append(
                PurchasesService._serialize_product_price_variation(db, item)
            )

        rows = []
        for group in grouped.values():
            variations = group["variations"]
            prices = [v["current_price"] for v in variations if v["current_price"] is not None]
            supplier_ids = {v["supplier_id"] for v in variations if v["supplier_id"]}
            dates = [v["last_updated_at"] for v in variations if v["last_updated_at"]]
            rows.append({
                "family_id": group["family_id"],
                "family_name": group["family_name"],
                "description": group["description"],
                "variations_count": len(variations),
                "suppliers_count": len(supplier_ids),
                "min_price": min(prices) if prices else None,
                "max_price": max(prices) if prices else None,
                "last_updated_at": max(dates) if dates else None,
                "variations": variations,
            })
        return sorted(rows, key=lambda row: row["family_name"])

    @staticmethod
    def get_products_prices(
        db: Session,
        current_user: User,
        search: Optional[str] = None,
        limit: int = 80,
        offset: int = 0,
    ) -> Dict[str, Any]:
        PurchasesService._ensure_purchase_access(db, current_user, PermissionLevel.READ_ONLY)
        catalog_rows = db.query(func.count(PurchaseSupplierPriceOffer.id)).scalar() or 0
        if catalog_rows:
            return PurchasesXlsxSmartCatalog.families(db, search=search, limit=limit, offset=offset)
        limit = max(1, min(limit, 120))
        offset = max(0, offset)

        query = db.query(ProductItem).options(joinedload(ProductItem.family)).filter(
            ProductItem.is_active == True
        )
        term = (search or "").strip()
        if term:
            like = f"%{term}%"
            supplier_ref_items = db.query(PurchasePriceReference.product_item_id).join(
                Supplier, PurchasePriceReference.supplier_id == Supplier.id
            ).join(Person, Supplier.person_id == Person.id).filter(Person.name.ilike(like))
            supplier_hist_items = db.query(PurchasePriceHistory.product_item_id).join(
                Supplier, PurchasePriceHistory.supplier_id == Supplier.id
            ).join(Person, Supplier.person_id == Person.id).filter(Person.name.ilike(like))
            query = query.outerjoin(ProductFamily).filter(or_(
                ProductItem.name.ilike(like),
                ProductItem.description.ilike(like),
                ProductItem.sku.ilike(like),
                ProductItem.category.ilike(like),
                ProductItem.canonical_key.ilike(like),
                ProductFamily.name.ilike(like),
                ProductItem.id.in_(supplier_ref_items),
                ProductItem.id.in_(supplier_hist_items),
            ))

        total_variations = query.count()
        items = query.order_by(ProductItem.category.asc(), ProductItem.name.asc()).offset(offset).limit(limit).all()
        products_count = db.query(func.count(ProductItem.id)).filter(ProductItem.is_active == True).scalar() or 0
        families_count = db.query(func.count(ProductFamily.id)).scalar() or 0
        current_prices_count = db.query(func.count(PurchasePriceReference.id)).filter(
            PurchasePriceReference.is_active == True
        ).scalar() or 0
        recently_updated_count = db.query(func.count(PurchasePriceReference.id)).filter(
            PurchasePriceReference.is_active == True,
            PurchasePriceReference.updated_at >= datetime.now(timezone.utc) - timedelta(days=30)
        ).scalar() or 0

        return {
            "items": PurchasesService._build_family_rows(db, items),
            "total_variations": total_variations,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_variations,
            "summary": {
                "products_count": products_count,
                "families_count": families_count,
                "current_prices_count": current_prices_count,
                "recently_updated_count": recently_updated_count,
            },
        }

    @staticmethod
    def get_product_price_family(
        db: Session,
        family_id: uuid.UUID,
        current_user: User,
        search: Optional[str] = None,
        limit: int = 80,
        offset: int = 0,
    ) -> Dict[str, Any]:
        PurchasesService._ensure_purchase_access(db, current_user, PermissionLevel.READ_ONLY)
        catalog_rows = db.query(func.count(PurchaseSupplierPriceOffer.id)).scalar() or 0
        if catalog_rows:
            return PurchasesXlsxSmartCatalog.variations(db, family_id, search=search, limit=limit, offset=offset)
        family = db.query(ProductFamily).filter(ProductFamily.id == family_id).first()
        if not family:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Familia de produto nao encontrada.")

        query = db.query(ProductItem).options(joinedload(ProductItem.family)).filter(
            ProductItem.family_id == family_id,
            ProductItem.is_active == True,
        )
        term = (search or "").strip()
        if term:
            like = f"%{term}%"
            query = query.filter(or_(
                ProductItem.name.ilike(like),
                ProductItem.description.ilike(like),
                ProductItem.sku.ilike(like),
                ProductItem.canonical_key.ilike(like),
            ))

        total = query.count()
        items = query.order_by(ProductItem.name.asc()).offset(max(0, offset)).limit(max(1, min(limit, 120))).all()
        rows = PurchasesService._build_family_rows(db, items)
        if rows:
            rows[0]["variations_count"] = total
            return rows[0]
        return {
            "family_id": family.id,
            "family_name": family.name,
            "description": family.description,
            "variations_count": total,
            "suppliers_count": 0,
            "min_price": None,
            "max_price": None,
            "last_updated_at": None,
            "variations": [],
        }

    @staticmethod
    def update_product_variation_price(
        db: Session,
        product_item_id: uuid.UUID,
        payload: Any,
        current_user: User,
    ) -> Dict[str, Any]:
        PurchasesService._ensure_purchase_access(
            db,
            current_user,
            PermissionLevel.NORMAL,
            "Permissao insuficiente para atualizar preco em Compras.",
        )
        product = db.query(ProductItem).options(joinedload(ProductItem.family)).filter(
            ProductItem.id == product_item_id,
            ProductItem.is_active == True,
        ).first()
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto ou variacao nao encontrado.")

        supplier = None
        if payload.supplier_id:
            supplier = db.query(Supplier).options(joinedload(Supplier.person)).filter(Supplier.id == payload.supplier_id).first()
            if not supplier:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Fornecedor nao encontrado.")

        new_price = _money(payload.new_price)
        active_ref = db.query(PurchasePriceReference).filter(
            PurchasePriceReference.product_item_id == product.id,
            PurchasePriceReference.supplier_id == payload.supplier_id,
            PurchasePriceReference.is_active == True,
        ).order_by(desc(PurchasePriceReference.updated_at)).first()
        old_price = _money(active_ref.current_unit_price) if active_ref else None
        now = datetime.now(timezone.utc)

        evidence = PurchasePriceEvidence(
            source_type="MANUAL_ENTRY",
            supplier_id=payload.supplier_id,
            product_item_id=product.id,
            document_number=payload.document_number,
            document_date=payload.document_date or now,
            unit_price=new_price,
            quantity=Decimal("1"),
            total_amount=new_price,
            currency="BRL",
            unit_of_measure=product.unit_of_measure,
            payment_terms=payload.payment_terms,
            file_id=payload.evidence_file_id,
            notes=payload.notes,
            created_by_user_id=current_user.id,
            created_at=now,
        )
        db.add(evidence)
        db.flush()

        history = PurchasePriceHistory(
            product_item_id=product.id,
            supplier_id=payload.supplier_id,
            evidence_id=evidence.id,
            unit_price=new_price,
            quantity=Decimal("1"),
            total_amount=new_price,
            currency="BRL",
            unit_of_measure=product.unit_of_measure,
            observed_at=payload.document_date or now,
            source_type="MANUAL_ENTRY",
            source_id=payload.document_number,
            created_by_user_id=current_user.id,
            created_at=now,
        )
        db.add(history)
        db.flush()

        old_refs = db.query(PurchasePriceReference).filter(
            PurchasePriceReference.product_item_id == product.id,
            PurchasePriceReference.supplier_id == payload.supplier_id,
            PurchasePriceReference.is_active == True,
        ).all()
        for ref in old_refs:
            ref.is_active = False
            ref.updated_at = now

        reference = PurchasePriceReference(
            product_item_id=product.id,
            supplier_id=payload.supplier_id,
            current_unit_price=new_price,
            currency="BRL",
            unit_of_measure=product.unit_of_measure,
            source_history_id=history.id,
            source_evidence_id=evidence.id,
            approved_by_user_id=current_user.id,
            approved_at=now,
            notes=payload.notes,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        db.add(reference)
        db.flush()

        difference_amount = None
        difference_percent = None
        if old_price is not None:
            difference_amount = _money(new_price - old_price)
            if old_price > 0:
                difference_percent = _percent((difference_amount / old_price) * Decimal("100"))

        try:
            emit_event(
                db=db,
                event_type="purchase.price.reference.updated",
                aggregate_type="purchase_price_reference",
                aggregate_id=str(reference.id),
                module="purchases",
                payload={
                    "product_item_id": str(product.id),
                    "supplier_id": str(payload.supplier_id) if payload.supplier_id else None,
                    "old_price": float(old_price) if old_price is not None else None,
                    "new_price": float(new_price),
                    "actor_user_id": current_user.id,
                    "summary": f"Preco atual de {product.name} atualizado por {current_user.username}.",
                },
                actor_user_id=current_user.id,
            )
        except Exception as e:
            print(f"Failed to emit purchase.price.reference.updated: {e}")

        db.commit()
        supplier_name = supplier.person.name if supplier and supplier.person else None
        return {
            "item_id": product.id,
            "family_name": PurchasesService._family_name_for_item(product),
            "variation_name": PurchasesService._variation_name_for_item(product),
            "old_price": old_price,
            "new_price": new_price,
            "difference_amount": difference_amount,
            "difference_percent": difference_percent,
            "supplier_id": payload.supplier_id,
            "supplier_name": supplier_name,
            "history_id": history.id,
            "reference_id": reference.id,
            "updated_at": now,
        }

    @staticmethod
    def get_xlsx_reconciliation(
        db: Session,
        current_user: User,
        search: Optional[str] = None,
        status_filter: str = "all",
        limit: int = 80,
        offset: int = 0,
    ) -> Dict[str, Any]:
        PurchasesService._ensure_purchase_access(db, current_user, PermissionLevel.READ_ONLY)
        PurchasesXlsxSmartCatalog.ensure_snapshot(db, current_user)
        is_admin = bool(current_user.role and current_user.role.name in {"ADMIN", "MESSIAS"})
        is_messias = current_user.username.upper() == "MESSIAS"
        if db.query(func.count(PurchaseSupplierPriceOffer.id)).scalar() or 0:
            return PurchasesXlsxSmartCatalog.reconciliation_payload(
                db,
                search=search,
                status_filter=status_filter,
                limit=limit,
                offset=offset,
                include_technical=is_admin or is_messias,
            )
        return PurchasesXlsxReconciliation.payload(db, search=search, status_filter=status_filter, limit=limit, offset=offset, include_technical=is_admin or is_messias)

    @staticmethod
    def update_price_from_xlsx_reconciliation(db: Session, payload: Any, current_user: User) -> Dict[str, Any]:
        PurchasesService._ensure_purchase_access(
            db,
            current_user,
            PermissionLevel.NORMAL,
            "Permissao insuficiente para atualizar preco usando a conferencia da planilha.",
        )
        update_payload = type("UpdatePayload", (), {
            "new_price": payload.spreadsheet_price,
            "supplier_id": payload.supplier_id,
            "document_number": payload.document_number or f"Compras Nova.xlsx:{payload.row_key}",
            "document_date": None,
            "payment_terms": None,
            "notes": payload.notes or "Atualizado a partir da Conferência da Planilha de Compras.",
            "evidence_file_id": None,
        })()
        result = PurchasesService.update_product_variation_price(db, payload.product_item_id, update_payload, current_user)
        try:
            emit_event(
                db=db,
                event_type="purchase.xlsx_reconciliation.price_updated",
                aggregate_type="product_item",
                aggregate_id=str(payload.product_item_id),
                module="purchases",
                payload={
                    "row_key": payload.row_key,
                    "product_item_id": str(payload.product_item_id),
                    "supplier_id": str(payload.supplier_id) if payload.supplier_id else None,
                    "spreadsheet_price": float(payload.spreadsheet_price),
                    "actor_user_id": current_user.id,
                    "summary": "Preco atualizado a partir da conferencia da planilha de compras.",
                },
                actor_user_id=current_user.id,
            )
            db.commit()
        except Exception as exc:
            print(f"Failed to emit purchase.xlsx_reconciliation.price_updated: {exc}")
        return result

    @staticmethod
    def update_supplier_contact_from_xlsx(db: Session, payload: Any, current_user: User) -> Supplier:
        PurchasesService._ensure_purchase_access(
            db,
            current_user,
            PermissionLevel.NORMAL,
            "Permissao insuficiente para corrigir contato de fornecedor em Compras.",
        )
        supplier = db.query(Supplier).options(joinedload(Supplier.person)).filter(Supplier.id == payload.supplier_id).first()
        if not supplier:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fornecedor nao encontrado.")
        if payload.email:
            supplier.preferred_contact_email = payload.email.strip().lower()
            if supplier.person:
                supplier.person.email = payload.email.strip().lower()
        if payload.phone and supplier.person:
            supplier.person.phone = payload.phone.strip()
        supplier.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(supplier)
        return supplier

    @staticmethod
    def export_xlsx_reconciliation(db: Session, current_user: User) -> Dict[str, Any]:
        PurchasesService._ensure_purchase_access(
            db,
            current_user,
            PermissionLevel.NORMAL,
            "Permissao insuficiente para exportar conferencia de compras.",
        )
        return PurchasesXlsxReconciliation.export_csv(db)

    @staticmethod
    def sync_catalog_from_xlsx(db: Session, current_user: User) -> Dict[str, Any]:
        PurchasesService._ensure_purchase_access(
            db,
            current_user,
            PermissionLevel.NORMAL,
            "Permissao insuficiente para atualizar o catalogo pela planilha.",
        )
        return PurchasesXlsxSmartCatalog.sync_from_xlsx(db, current_user)

    @staticmethod
    def get_catalog_summary(db: Session, current_user: User) -> Dict[str, Any]:
        PurchasesService._ensure_purchase_access(db, current_user, PermissionLevel.READ_ONLY)
        PurchasesXlsxSmartCatalog.ensure_snapshot(db, current_user)
        return PurchasesXlsxSmartCatalog.summary(db)

    @staticmethod
    def get_catalog_families(
        db: Session,
        current_user: User,
        search: Optional[str] = None,
        limit: int = 80,
        offset: int = 0,
    ) -> Dict[str, Any]:
        PurchasesService._ensure_purchase_access(db, current_user, PermissionLevel.READ_ONLY)
        PurchasesXlsxSmartCatalog.ensure_snapshot(db, current_user)
        return PurchasesXlsxSmartCatalog.families(db, search=search, limit=limit, offset=offset)

    @staticmethod
    def get_catalog_family_variations(
        db: Session,
        family_id: uuid.UUID,
        current_user: User,
        search: Optional[str] = None,
        limit: int = 80,
        offset: int = 0,
    ) -> Dict[str, Any]:
        PurchasesService._ensure_purchase_access(db, current_user, PermissionLevel.READ_ONLY)
        return PurchasesXlsxSmartCatalog.variations(db, family_id, search=search, limit=limit, offset=offset)

    @staticmethod
    def get_catalog_item(db: Session, item_id: uuid.UUID, current_user: User) -> Dict[str, Any]:
        PurchasesService._ensure_purchase_access(db, current_user, PermissionLevel.READ_ONLY)
        try:
            return PurchasesXlsxSmartCatalog.item_detail(db, item_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    @staticmethod
    def get_catalog_supplier_offers(db: Session, item_id: uuid.UUID, current_user: User) -> Dict[str, Any]:
        PurchasesService._ensure_purchase_access(db, current_user, PermissionLevel.READ_ONLY)
        return PurchasesXlsxSmartCatalog.supplier_offers(db, item_id)

    @staticmethod
    def update_catalog_supplier_offer_price(
        db: Session,
        item_id: uuid.UUID,
        offer_id: uuid.UUID,
        payload: Any,
        current_user: User,
    ) -> Dict[str, Any]:
        PurchasesService._ensure_purchase_access(
            db,
            current_user,
            PermissionLevel.NORMAL,
            "Permissao insuficiente para atualizar preco em Compras.",
        )
        try:
            return PurchasesXlsxSmartCatalog.update_supplier_offer_price(db, item_id, offer_id, payload, current_user)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    @staticmethod
    def list_price_references(
        db: Session,
        current_user: User,
        product_item_id: Optional[uuid.UUID] = None,
        supplier_id: Optional[uuid.UUID] = None
    ) -> List[PurchasePriceReference]:
        PurchasesService._ensure_purchase_access(db, current_user, PermissionLevel.READ_ONLY)
        query = db.query(PurchasePriceReference).filter(PurchasePriceReference.is_active == True)
        if product_item_id:
            query = query.filter(PurchasePriceReference.product_item_id == product_item_id)
        if supplier_id:
            query = query.filter(PurchasePriceReference.supplier_id == supplier_id)
        return query.order_by(desc(PurchasePriceReference.created_at)).all()

    @staticmethod
    def list_price_history(
        db: Session,
        current_user: User,
        product_item_id: Optional[uuid.UUID] = None,
        supplier_id: Optional[uuid.UUID] = None
    ) -> List[PurchasePriceHistory]:
        PurchasesService._ensure_purchase_access(db, current_user, PermissionLevel.READ_ONLY)
        query = db.query(PurchasePriceHistory)
        if product_item_id:
            query = query.filter(PurchasePriceHistory.product_item_id == product_item_id)
        if supplier_id:
            query = query.filter(PurchasePriceHistory.supplier_id == supplier_id)
        return query.order_by(desc(PurchasePriceHistory.observed_at)).all()

    @staticmethod
    def list_price_suggestions(db: Session, current_user: User, status: Optional[str] = None) -> List[PurchasePriceUpdateSuggestion]:
        PurchasesService._ensure_purchase_access(db, current_user, PermissionLevel.READ_ONLY)
        query = db.query(PurchasePriceUpdateSuggestion)
        if status:
            query = query.filter(PurchasePriceUpdateSuggestion.status == status)
        return query.order_by(desc(PurchasePriceUpdateSuggestion.created_at)).all()

    @staticmethod
    def get_price_suggestion(db: Session, suggestion_id: uuid.UUID, current_user: User) -> PurchasePriceUpdateSuggestion:
        PurchasesService._ensure_purchase_access(db, current_user, PermissionLevel.READ_ONLY)
        suggestion = db.query(PurchasePriceUpdateSuggestion).filter(
            PurchasePriceUpdateSuggestion.id == suggestion_id
        ).first()
        if not suggestion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sugestao de reajuste de preco nao encontrada."
            )
        return suggestion

    @staticmethod
    def get_item_price_timeline(
        db: Session,
        product_item_id: uuid.UUID,
        current_user: User,
        limit: int = 40,
        offset: int = 0,
    ) -> List[PurchasePriceHistory]:
        PurchasesService._ensure_purchase_access(db, current_user, PermissionLevel.READ_ONLY)
        return db.query(PurchasePriceHistory).filter(
            PurchasePriceHistory.product_item_id == product_item_id
        ).order_by(desc(PurchasePriceHistory.observed_at)).offset(max(0, offset)).limit(max(1, min(limit, 100))).all()

    @staticmethod
    def create_price_evidence(db: Session, payload: Any, current_user: User) -> PurchasePriceEvidence:
        user_level = ApprovalService.get_user_module_level(db, current_user, "purchases")
        is_admin = current_user.role and current_user.role.name == "ADMIN"
        if LEVEL_VALUES[user_level] < LEVEL_VALUES[PermissionLevel.NORMAL] and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissão insuficiente para registrar evidência de preço."
            )

        if payload.source_type not in PRICE_SOURCE_TYPES_ALLOWED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tipo de origem indisponivel nesta fase manual de Compras."
            )

        if not payload.product_item_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="É obrigatório informar o item de produto (product_item_id)."
            )

        # Verifica existência do item no master data
        product = db.query(ProductItem).filter(ProductItem.id == payload.product_item_id).first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Item de produto não encontrado."
            )

        if payload.service_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rastreabilidade de preco de servicos fica para uma etapa futura; selecione um item de produto."
            )

        new_unit_price = _money(payload.unit_price)
        if new_unit_price <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="E obrigatorio informar valor unitario maior que zero."
            )

        quantity = _as_decimal(payload.quantity)
        total_amount = _as_decimal(payload.total_amount)

        if payload.supplier_id:
            supplier = db.query(Supplier).filter(Supplier.id == payload.supplier_id).first()
            if not supplier:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Fornecedor não encontrado."
                )

        # 1. Cria a evidência de preço
        new_evidence = PurchasePriceEvidence(
            source_type=payload.source_type,
            supplier_id=payload.supplier_id,
            product_item_id=payload.product_item_id,
            service_id=payload.service_id,
            document_number=payload.document_number,
            document_date=payload.document_date or datetime.now(timezone.utc),
            unit_price=new_unit_price,
            quantity=quantity,
            total_amount=total_amount,
            currency=payload.currency or "BRL",
            unit_of_measure=payload.unit_of_measure,
            payment_terms=payload.payment_terms,
            due_date=payload.due_date,
            file_id=payload.file_id,
            raw_summary=payload.raw_summary,
            notes=payload.notes,
            created_by_user_id=current_user.id,
            created_at=datetime.now(timezone.utc)
        )
        db.add(new_evidence)
        db.flush() # Para gerar o id da evidência

        # 2. Cria o log histórico imutável
        new_history = PurchasePriceHistory(
            product_item_id=payload.product_item_id,
            supplier_id=payload.supplier_id,
            evidence_id=new_evidence.id,
            unit_price=new_unit_price,
            quantity=quantity,
            total_amount=total_amount,
            currency=payload.currency or "BRL",
            unit_of_measure=payload.unit_of_measure,
            observed_at=payload.document_date or datetime.now(timezone.utc),
            source_type=payload.source_type,
            source_id=payload.document_number,
            created_by_user_id=current_user.id,
            created_at=datetime.now(timezone.utc)
        )
        db.add(new_history)
        db.flush()

        # 3. Busca o preço de referência ativo
        active_ref = db.query(PurchasePriceReference).filter(
            PurchasePriceReference.product_item_id == payload.product_item_id,
            PurchasePriceReference.supplier_id == payload.supplier_id,
            PurchasePriceReference.is_active == True
        ).first()

        # Se não houver referência específica com fornecedor, busca a geral
        if not active_ref and payload.supplier_id:
            active_ref = db.query(PurchasePriceReference).filter(
                PurchasePriceReference.product_item_id == payload.product_item_id,
                PurchasePriceReference.supplier_id == None,
                PurchasePriceReference.is_active == True
            ).first()

        old_price = None
        pct_var = None
        variation_dir = "NEW_REFERENCE"

        if active_ref:
            old_price = _money(active_ref.current_unit_price)
            if old_price > 0:
                pct_var = _percent(((new_unit_price - old_price) / old_price) * Decimal("100"))
            else:
                pct_var = Decimal("0.0000")
            
            if pct_var > PRICE_VARIATION_EPSILON:
                variation_dir = "INCREASE"
            elif pct_var < -PRICE_VARIATION_EPSILON:
                variation_dir = "DECREASE"
            else:
                variation_dir = "SAME"
        
        # 4. Cria a sugestão de reajuste
        new_suggestion = PurchasePriceUpdateSuggestion(
            product_item_id=payload.product_item_id,
            supplier_id=payload.supplier_id,
            evidence_id=new_evidence.id,
            history_id=new_history.id,
            reference_id=active_ref.id if active_ref else None,
            old_unit_price=old_price,
            new_unit_price=new_unit_price,
            pct_variation=pct_var,
            variation_direction=variation_dir,
            status="PENDING",
            reason=payload.notes,
            created_by_user_id=current_user.id,
            created_at=datetime.now(timezone.utc)
        )
        db.add(new_suggestion)
        db.flush()

        # 5. Emite os eventos de domínio
        try:
            emit_event(
                db=db,
                event_type="purchase.price.evidence.created",
                aggregate_type="purchase_price_evidence",
                aggregate_id=str(new_evidence.id),
                module="purchases",
                payload={
                    "id": str(new_evidence.id),
                    "source_type": new_evidence.source_type,
                    "product_item_id": str(new_evidence.product_item_id),
                    "supplier_id": str(new_evidence.supplier_id) if new_evidence.supplier_id else None,
                    "unit_price": float(new_evidence.unit_price or 0.0),
                    "actor_user_id": current_user.id,
                    "summary": f"Evidência de preço ({new_evidence.source_type}) registrada para o item {product.name}."
                },
                actor_user_id=current_user.id
            )
            emit_event(
                db=db,
                event_type="purchase.price.history.created",
                aggregate_type="purchase_price_history",
                aggregate_id=str(new_history.id),
                module="purchases",
                payload={
                    "id": str(new_history.id),
                    "product_item_id": str(new_history.product_item_id),
                    "supplier_id": str(new_history.supplier_id) if new_history.supplier_id else None,
                    "unit_price": float(new_history.unit_price),
                    "observed_at": new_history.observed_at.isoformat(),
                    "actor_user_id": current_user.id,
                    "summary": f"Registro de preço histórico criado para o item {product.name}."
                },
                actor_user_id=current_user.id
            )
            emit_event(
                db=db,
                event_type="purchase.price.suggestion.created",
                aggregate_type="purchase_price_update_suggestion",
                aggregate_id=str(new_suggestion.id),
                module="purchases",
                payload={
                    "id": str(new_suggestion.id),
                    "product_item_id": str(new_suggestion.product_item_id),
                    "supplier_id": str(new_suggestion.supplier_id) if new_suggestion.supplier_id else None,
                    "old_unit_price": float(new_suggestion.old_unit_price) if new_suggestion.old_unit_price is not None else None,
                    "new_unit_price": float(new_suggestion.new_unit_price),
                    "pct_variation": float(new_suggestion.pct_variation) if new_suggestion.pct_variation is not None else None,
                    "variation_direction": new_suggestion.variation_direction,
                    "created_by_user_id": current_user.id,
                    "summary": f"Sugestão de reajuste de preço criada para o item {product.name}. Variação: {f'{pct_var:.2f}%' if pct_var is not None else 'Nova Referência'}."
                },
                actor_user_id=current_user.id
            )
        except Exception as e:
            print(f"Failed to emit purchase.price.* events: {e}")

        db.commit()
        db.refresh(new_evidence)
        db.refresh(new_suggestion)

        return new_evidence

    @staticmethod
    def approve_price_suggestion(db: Session, suggestion_id: uuid.UUID, notes: Optional[str], current_user: User) -> PurchasePriceUpdateSuggestion:
        user_level = ApprovalService.get_user_module_level(db, current_user, "purchases")
        is_admin = current_user.role and current_user.role.name == "ADMIN"
        if LEVEL_VALUES[user_level] < LEVEL_VALUES[PermissionLevel.MANAGER] and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissão insuficiente para aprovar sugestão de preço."
            )

        suggestion = db.query(PurchasePriceUpdateSuggestion).filter(
            PurchasePriceUpdateSuggestion.id == suggestion_id
        ).first()

        if not suggestion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sugestão de reajuste de preço não encontrada."
            )

        if suggestion.status != "PENDING":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Esta sugestão já foi revisada ou cancelada."
            )

        product = db.query(ProductItem).filter(ProductItem.id == suggestion.product_item_id).first()

        # 1. Atualiza status da sugestão
        suggestion.status = "APPROVED"
        suggestion.reviewed_by_user_id = current_user.id
        suggestion.reviewed_at = datetime.now(timezone.utc)
        suggestion.review_notes = notes

        # 2. Inativa preços de referência anteriores para item + fornecedor
        old_refs = db.query(PurchasePriceReference).filter(
            PurchasePriceReference.product_item_id == suggestion.product_item_id,
            PurchasePriceReference.supplier_id == suggestion.supplier_id,
            PurchasePriceReference.is_active == True
        ).all()
        for ref in old_refs:
            ref.is_active = False
            ref.updated_at = datetime.now(timezone.utc)

        was_new_reference = not old_refs

        # 3. Cria o novo preço de referência ativo
        new_ref = PurchasePriceReference(
            product_item_id=suggestion.product_item_id,
            supplier_id=suggestion.supplier_id,
            current_unit_price=suggestion.new_unit_price,
            currency=suggestion.evidence.currency,
            unit_of_measure=suggestion.evidence.unit_of_measure,
            source_history_id=suggestion.history_id,
            source_evidence_id=suggestion.evidence_id,
            approved_by_user_id=current_user.id,
            approved_at=datetime.now(timezone.utc),
            notes=notes,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(new_ref)
        db.flush()

        # 4. Emite eventos
        try:
            emit_event(
                db=db,
                event_type="purchase.price.suggestion.approved",
                aggregate_type="purchase_price_update_suggestion",
                aggregate_id=str(suggestion.id),
                module="purchases",
                payload={
                    "id": str(suggestion.id),
                    "product_item_id": str(suggestion.product_item_id),
                    "supplier_id": str(suggestion.supplier_id) if suggestion.supplier_id else None,
                    "new_unit_price": float(suggestion.new_unit_price),
                    "approved_by_user_id": current_user.id,
                    "created_by_user_id": suggestion.created_by_user_id,
                    "summary": f"Sugestão de preço aprovada para {product.name} por {current_user.username}."
                },
                actor_user_id=current_user.id
            )
            emit_event(
                db=db,
                event_type="purchase.price.reference.created" if was_new_reference else "purchase.price.reference.updated",
                aggregate_type="purchase_price_reference",
                aggregate_id=str(new_ref.id),
                module="purchases",
                payload={
                    "id": str(new_ref.id),
                    "product_item_id": str(new_ref.product_item_id),
                    "supplier_id": str(new_ref.supplier_id) if new_ref.supplier_id else None,
                    "current_unit_price": float(new_ref.current_unit_price),
                    "approved_by_user_id": current_user.id,
                    "summary": f"Novo preço de referência ativo definido para {product.name}."
                },
                actor_user_id=current_user.id
            )
        except Exception as e:
            print(f"Failed to emit approval events: {e}")

        db.commit()
        db.refresh(suggestion)
        db.refresh(new_ref)
        return suggestion

    @staticmethod
    def reject_price_suggestion(db: Session, suggestion_id: uuid.UUID, notes: Optional[str], current_user: User) -> PurchasePriceUpdateSuggestion:
        user_level = ApprovalService.get_user_module_level(db, current_user, "purchases")
        is_admin = current_user.role and current_user.role.name == "ADMIN"
        if LEVEL_VALUES[user_level] < LEVEL_VALUES[PermissionLevel.MANAGER] and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissão insuficiente para rejeitar sugestão de preço."
            )

        suggestion = db.query(PurchasePriceUpdateSuggestion).filter(
            PurchasePriceUpdateSuggestion.id == suggestion_id
        ).first()

        if not suggestion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sugestão de reajuste de preço não encontrada."
            )

        if suggestion.status != "PENDING":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Esta sugestão já foi revisada ou cancelada."
            )

        product = db.query(ProductItem).filter(ProductItem.id == suggestion.product_item_id).first()

        # 1. Atualiza status da sugestão
        suggestion.status = "REJECTED"
        suggestion.reviewed_by_user_id = current_user.id
        suggestion.reviewed_at = datetime.now(timezone.utc)
        suggestion.review_notes = notes
        db.flush()

        # 2. Emite evento
        try:
            emit_event(
                db=db,
                event_type="purchase.price.suggestion.rejected",
                aggregate_type="purchase_price_update_suggestion",
                aggregate_id=str(suggestion.id),
                module="purchases",
                payload={
                    "id": str(suggestion.id),
                    "product_item_id": str(suggestion.product_item_id),
                    "supplier_id": str(suggestion.supplier_id) if suggestion.supplier_id else None,
                    "new_unit_price": float(suggestion.new_unit_price),
                    "rejected_by_user_id": current_user.id,
                    "created_by_user_id": suggestion.created_by_user_id,
                    "reason": notes,
                    "summary": f"Sugestão de preço rejeitada para {product.name} por {current_user.username}."
                },
                actor_user_id=current_user.id
            )
        except Exception as e:
            print(f"Failed to emit rejection event: {e}")

        db.commit()
        db.refresh(suggestion)
        return suggestion

    @staticmethod
    def external_search(db: Session, q: str, current_user: User) -> Dict[str, Any]:
        from app.modules.purchases.search_provider import get_search_provider, CredentialsMissingException
        
        user_level = ApprovalService.get_user_module_level(db, current_user, "purchases")
        is_admin = current_user.role and current_user.role.name == "ADMIN"
        if LEVEL_VALUES[user_level] < LEVEL_VALUES[PermissionLevel.NORMAL] and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissão insuficiente para realizar busca externa."
            )

        provider = get_search_provider()
        try:
            results = provider.search_products(q)
            if not results:
                return {
                    "status": "success",
                    "results": [],
                    "classifications": {}
                }

            # Encontra os destaques para gerar classificações explicáveis
            # 1. Menor preço
            cheapest = min(results, key=lambda x: x.get("total_price", 999999.0))
            
            # 2. Entrega mais rápida
            def get_days(estimate_str):
                if not estimate_str:
                    return 999
                match = re.search(r"(\d+)\s*(?:a|\-)\s*(\d+)?\s*dia", estimate_str, re.IGNORECASE)
                if match:
                    return int(match.group(1))
                match_single = re.search(r"(\d+)\s*dia", estimate_str, re.IGNORECASE)
                if match_single:
                    return int(match_single.group(1))
                return 999

            fastest = min(results, key=lambda x: get_days(x.get("delivery_estimate", "")))
            
            # 3. Melhor avaliado
            best_rated = max(results, key=lambda x: (float(x.get("rating", 0.0)) if x.get("rating") is not None else 0.0))
            
            # 4. Melhor opção geral
            best_overall = results[0] if results else None

            classifications = {
                "cheapest_id": cheapest.get("title") + str(cheapest.get("total_price")),
                "fastest_id": fastest.get("title") + str(fastest.get("total_price")),
                "best_rated_id": best_rated.get("title") + str(best_rated.get("total_price")),
                "best_overall_id": best_overall.get("title") + str(best_overall.get("total_price")) if best_overall else None
            }

            # Atribui labels nas opções
            for item in results:
                opt_key = item.get("title") + str(item.get("total_price"))
                labels = []
                if opt_key == classifications["cheapest_id"]:
                    labels.append("Menor Preço")
                if opt_key == classifications["fastest_id"] and get_days(item.get("delivery_estimate", "")) < 999:
                    labels.append("Entrega mais Rápida")
                if opt_key == classifications["best_rated_id"] and item.get("rating") is not None and float(item.get("rating", 0)) >= 4.5:
                    labels.append("Melhor Avaliado")
                if opt_key == classifications["best_overall_id"]:
                    labels.append("Melhor Opção Geral")
                item["tags"] = labels

            return {
                "status": "success",
                "results": results,
                "classifications": classifications
            }
        except CredentialsMissingException as e:
            return {
                "status": "credentials_missing",
                "results": [],
                "classifications": {},
                "message": "Pesquisa automática de mercado ainda não está configurada. Adicione links ou opções manualmente."
            }
        except Exception as ex:
            print(f"External product search failed: {ex}")
            return {
                "status": "unavailable",
                "results": [],
                "classifications": {},
                "message": "Pesquisa automática de mercado não respondeu agora. Adicione uma opção manualmente ou tente novamente."
            }

    @staticmethod
    def create_item_research_session(db: Session, item_id: uuid.UUID, payload: Any, current_user: User) -> Dict[str, Any]:
        from app.modules.purchases.research_engine import research_engine

        item = db.query(PurchaseRequestItem).filter(PurchaseRequestItem.id == item_id).first()
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item de compra nao encontrado.")
        PurchasesService.get_purchase_request(db, item.purchase_request_id, current_user)

        user_level = ApprovalService.get_user_module_level(db, current_user, "purchases")
        is_admin = current_user.role and current_user.role.name == "ADMIN"
        if LEVEL_VALUES[user_level] < LEVEL_VALUES[PermissionLevel.NORMAL] and not is_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permissao insuficiente.")

        session = research_engine.create_session(db, item_id, current_user, payload)
        if getattr(payload, "run_immediately", True):
            if settings.PURCHASES_RESEARCH_ASYNC_ENABLED:
                PurchasesService.enqueue_purchase_research(db, session.id, current_user)
            else:
                session = research_engine.run_session(db, session.id, current_user)
        return research_engine.get_session_payload(db, session.id)

    @staticmethod
    def enqueue_purchase_research(db: Session, session_id: uuid.UUID, current_user: Optional[User] = None) -> None:
        from app.modules.purchases.research_engine import research_engine

        session = research_engine._get_session_model(db, session_id)
        job = PurchaseResearchJob(
            search_session_id=session.id,
            queue_name=settings.PURCHASES_RESEARCH_QUEUE_NAME,
            status="queued",
            attempts=0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.status = "queued"
        session.current_step = "aguardando processamento"
        session.updated_at = datetime.now(timezone.utc)
        db.add(job)
        db.commit()
        try:
            from app.modules.purchases.worker import run_purchase_research_session

            run_purchase_research_session.send(str(session.id), current_user.id if current_user else None)
        except Exception as exc:
            job.status = "retryable_error"
            job.last_error = str(exc)[:500]
            session.status = "retryable_error"
            session.current_step = "pesquisa aguardando worker"
            session.error_message = "A pesquisa foi salva, mas o worker nao esta disponivel agora."
            session.updated_at = datetime.now(timezone.utc)
            db.commit()

    @staticmethod
    def get_research_session(db: Session, session_id: uuid.UUID, current_user: User) -> Dict[str, Any]:
        from app.modules.purchases.research_engine import research_engine

        payload = research_engine.get_session_payload(db, session_id)
        PurchasesService.get_purchase_request(db, uuid.UUID(payload["purchase_request_id"]), current_user)
        return payload

    @staticmethod
    def refresh_research_session(db: Session, session_id: uuid.UUID, current_user: User) -> Dict[str, Any]:
        from app.modules.purchases.research_engine import research_engine

        session = research_engine._get_session_model(db, session_id)
        PurchasesService.get_purchase_request(db, session.purchase_request_id, current_user)
        session.status = "queued"
        session.progress_percent = 0
        session.current_step = "aguardando processamento"
        session.error_message = None
        session.completed_at = None
        session.updated_at = datetime.now(timezone.utc)
        db.commit()
        if settings.PURCHASES_RESEARCH_ASYNC_ENABLED:
            PurchasesService.enqueue_purchase_research(db, session_id, current_user)
            return research_engine.get_session_payload(db, session_id)
        refreshed = research_engine.refresh_session(db, session_id, current_user)
        return research_engine.get_session_payload(db, refreshed.id)

    @staticmethod
    def cancel_research_session(db: Session, session_id: uuid.UUID, current_user: User) -> Dict[str, Any]:
        from app.modules.purchases.research_engine import research_engine

        session = research_engine._get_session_model(db, session_id)
        PurchasesService.get_purchase_request(db, session.purchase_request_id, current_user)
        if session.status in {"completed", "completed_with_pending"}:
            return research_engine.get_session_payload(db, session_id)
        session.status = "cancelled"
        session.current_step = "pesquisa cancelada"
        session.updated_at = datetime.now(timezone.utc)
        db.query(PurchaseResearchJob).filter(
            PurchaseResearchJob.search_session_id == session_id,
            PurchaseResearchJob.status.in_(["queued", "retryable_error", "running"]),
        ).update({"status": "cancelled", "updated_at": datetime.now(timezone.utc)})
        db.commit()
        return research_engine.get_session_payload(db, session_id)

    @staticmethod
    def verify_research_offer(db: Session, session_id: uuid.UUID, option_id: uuid.UUID, current_user: User) -> Dict[str, Any]:
        from app.modules.purchases.research_engine import research_engine

        session = research_engine._get_session_model(db, session_id)
        PurchasesService.get_purchase_request(db, session.purchase_request_id, current_user)
        verified = research_engine.verify_offer(db, session_id, option_id, current_user)
        return research_engine.get_session_payload(db, verified.id)

    @staticmethod
    def revalidate_purchase_option(db: Session, option_id: uuid.UUID, current_user: User) -> PurchaseItemOption:
        from app.modules.purchases.research_engine import research_engine

        option = db.query(PurchaseItemOption).filter(PurchaseItemOption.id == option_id).first()
        if not option:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opcao de compra nao encontrada.")
        item = PurchasesService.get_request_item(db, option.purchase_item_id, current_user)
        if option.search_session_id:
            research_engine.verify_offer(db, option.search_session_id, option.id, current_user)
            db.refresh(option)
            return option
        research_engine.verifier.verify_option(db, option)
        item.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(option)
        return option

    @staticmethod
    def get_item_recommendation(db: Session, item_id: uuid.UUID, current_user: User) -> Dict[str, Any]:
        from app.modules.purchases.research_engine import research_engine

        item = db.query(PurchaseRequestItem).filter(PurchaseRequestItem.id == item_id).first()
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item de compra nao encontrado.")
        PurchasesService.get_purchase_request(db, item.purchase_request_id, current_user)
        return research_engine.build_recommendation(db, item_id)

    @staticmethod
    def request_item_approval(db: Session, item_id: uuid.UUID, payload: Any, current_user: User) -> PurchaseRequest:
        from app.modules.approvals.schemas import ApprovalCreate

        item = db.query(PurchaseRequestItem).filter(PurchaseRequestItem.id == item_id).options(
            joinedload(PurchaseRequestItem.options),
            joinedload(PurchaseRequestItem.purchase_request),
        ).first()
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item de compra nao encontrado.")
        request = PurchasesService.get_purchase_request(db, item.purchase_request_id, current_user)

        selected_option = None
        option_id = getattr(payload, "option_id", None)
        if option_id:
            selected_option = next((opt for opt in item.options if opt.id == option_id), None)
            if not selected_option:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opcao selecionada nao encontrada para este item.")
        elif item.selected_option_id:
            selected_option = next((opt for opt in item.options if opt.id == item.selected_option_id), None)

        options_payload = []
        for option in item.options:
            options_payload.append({
                "option_id": str(option.id),
                "title": option.title,
                "image_url": option.image_url,
                "store_name": option.store_name,
                "seller_name": option.seller_name,
                "unit_price": float(option.unit_price or 0),
                "shipping_price": float(option.shipping_price or 0) if option.shipping_price is not None else None,
                "total_price": float(option.total_price or 0),
                "delivery_estimate": option.delivery_estimate,
                "product_url": option.product_url,
                "compatibility_score": float(option.compatibility_score or 0) if getattr(option, "compatibility_score", None) is not None else None,
                "verification_status": getattr(option, "verification_status", None),
                "recommendation": getattr(option, "verification_summary", None),
                "selected": bool(selected_option and option.id == selected_option.id),
            })

        selected_payload = None
        if selected_option:
            selected_payload = next((opt for opt in options_payload if opt["option_id"] == str(selected_option.id)), None)
        approval_item = {
            "item_id": str(item.id),
            "purchase_item_id": str(item.id),
            "description": item.free_text_description or item.description,
            "quantity": float(getattr(payload, "quantity", None) or item.quantity or 1),
            "unit": item.unit_of_measure or "un",
            "classification": item.classification or "EXTERNAL",
            "selected_option_id": str(selected_option.id) if selected_option else None,
            "selected_option": selected_payload,
            "options": options_payload,
            "alternatives": getattr(payload, "alternatives", []) or [],
            "justification": getattr(payload, "justification", None) or "Avaliacao pontual de compra solicitada pelo comprador.",
        }

        approval_payload = ApprovalCreate(
            title=f"Aprovar item: {approval_item['description']}",
            description=f"Aprovacao opcional do item da compra {request.title}.",
            module_slug="purchases",
            risk_level="MEDIUM",
            action_type="PURCHASE_ITEM_APPROVAL",
            action_payload={
                "request_type": "purchase_options",
                "request_id": str(request.id),
                "item_approval": True,
                "items": [approval_item],
                "return_url": f"/purchases?request={request.id}&item={item.id}",
            },
            expires_at=(datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        )
        approval = ApprovalService.create_approval(db, approval_payload, current_user)
        item.requires_approval = True
        item.approval_status = "PENDING"
        request.approval_id = approval.id
        if request.status in {"DRAFT", "REQUESTED", "RFQ_PREPARING"}:
            request.status = "PENDING_APPROVAL"
        request.updated_at = datetime.now(timezone.utc)
        db.add(PurchaseActivity(
            purchase_request_id=request.id,
            user_id=current_user.id,
            action="item.approval_requested",
            details={"approval_id": approval.id, "item_id": str(item.id), "option_id": str(selected_option.id) if selected_option else None},
            created_at=datetime.now(timezone.utc),
        ))
        emit_event(
            db=db,
            event_type="purchase.item.approval_requested",
            aggregate_type="purchase_request_item",
            aggregate_id=str(item.id),
            module="purchases",
            payload={
                "purchase_request_id": str(request.id),
                "purchase_item_id": str(item.id),
                "action_url": f"/purchases?request={request.id}&item={item.id}",
                "summary": f"Aprovacao solicitada para {item.free_text_description or item.description}.",
            },
            actor_user_id=current_user.id,
        )
        db.commit()
        db.refresh(request)
        return request

    @staticmethod
    def prepare_supplier_rfq_for_item(db: Session, item_id: uuid.UUID, payload: Any, current_user: User) -> Dict[str, Any]:
        item = db.query(PurchaseRequestItem).filter(PurchaseRequestItem.id == item_id).options(
            joinedload(PurchaseRequestItem.purchase_request)
        ).first()
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item de compra nao encontrado.")
        request = PurchasesService.get_purchase_request(db, item.purchase_request_id, current_user)

        user_level = ApprovalService.get_user_module_level(db, current_user, "purchases")
        is_admin = current_user.role and current_user.role.name == "ADMIN"
        if LEVEL_VALUES[user_level] < LEVEL_VALUES[PermissionLevel.NORMAL] and not is_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permissao insuficiente.")

        rfq = PurchaseRFQ(
            purchase_request_id=request.id,
            title=f"Cotacao - {item.free_text_description or item.description}",
            status="DRAFT",
            message_template=None,
            created_by_user_id=current_user.id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(rfq)
        db.flush()
        linked_suppliers = []
        for supplier_id in getattr(payload, "supplier_ids", []) or []:
            supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
            if not supplier:
                continue
            contact_email = getattr(getattr(supplier, "person", None), "email", None) or getattr(supplier, "preferred_contact_email", None)
            rfq_supplier = PurchaseRFQSupplier(
                rfq_id=rfq.id,
                supplier_id=supplier.id,
                contact_email=contact_email,
                status="DRAFT",
                message_subject=f"Cotacao - {item.free_text_description or item.description}",
                message_body=PurchasesService._build_simple_supplier_message(request, [item]),
                created_at=datetime.now(timezone.utc),
            )
            db.add(rfq_supplier)
            db.flush()
            db.add(PurchaseRFQSupplierItem(rfq_supplier_id=rfq_supplier.id, purchase_item_id=item.id))
            linked_suppliers.append(str(supplier.id))

        request.status = "RFQ_PREPARING"
        request.updated_at = datetime.now(timezone.utc)
        db.add(PurchaseActivity(
            purchase_request_id=request.id,
            user_id=current_user.id,
            action="rfq.item_prepared",
            details={"rfq_id": str(rfq.id), "item_id": str(item.id), "suppliers": linked_suppliers},
            created_at=datetime.now(timezone.utc),
        ))
        emit_event(
            db=db,
            event_type="purchase.rfq.ready",
            aggregate_type="purchase_request_item",
            aggregate_id=str(item.id),
            module="purchases",
            payload={
                "purchase_request_id": str(request.id),
                "purchase_item_id": str(item.id),
                "action_url": f"/purchases?request={request.id}&item={item.id}&quote={rfq.id}",
                "summary": f"Cotacao preparada para {item.free_text_description or item.description}.",
            },
            actor_user_id=current_user.id,
        )
        db.commit()
        db.refresh(rfq)
        return {
            "rfq_id": str(rfq.id),
            "request_id": str(request.id),
            "item_id": str(item.id),
            "supplier_count": len(linked_suppliers),
            "homologation_mode": bool(getattr(payload, "homologation_mode", False)),
            "message": "Cotacao preparada para revisao antes do envio.",
        }

    @staticmethod
    def _build_simple_supplier_message(request: PurchaseRequest, items: List[PurchaseRequestItem]) -> str:
        lines = ["Ola,", "", "Solicitamos cotacao para os itens abaixo.", ""]
        for item in items:
            lines.extend([
                f"Item: {item.free_text_description or item.description}",
                f"Especificacao: {item.specifications or 'Conforme descricao'}",
                f"Quantidade: {float(item.quantity or 1):g} {item.unit_of_measure or 'un'}",
                "",
            ])
        lines.extend([
            "Por favor, informar:",
            "- preco;",
            "- prazo;",
            "- frete;",
            "- validade;",
            "- condicao de pagamento.",
            "",
            "Atenciosamente,",
            "Compras Vesper",
        ])
        return "\n".join(lines)

    @staticmethod
    def add_item_option(db: Session, item_id: uuid.UUID, payload: Any, current_user: User) -> PurchaseItemOption:
        from app.models.purchase import PurchaseRequestItem, PurchaseItemOption
        
        item = db.query(PurchaseRequestItem).filter(PurchaseRequestItem.id == item_id).first()
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item de requisição não encontrado.")

        # Verifica se o usuário é dono da requisição ou tem permissões
        user_level = ApprovalService.get_user_module_level(db, current_user, "purchases")
        is_admin = current_user.role and current_user.role.name == "ADMIN"
        if LEVEL_VALUES[user_level] < LEVEL_VALUES[PermissionLevel.NORMAL] and not is_admin and item.purchase_request.requester_user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permissão insuficiente.")

        option = PurchaseItemOption(
            purchase_item_id=item_id,
            source_type=payload.source_type,
            search_session_id=getattr(payload, "search_session_id", None),
            canonical_product_id=getattr(payload, "canonical_product_id", None),
            supplier_id=payload.supplier_id,
            store_name=payload.store_name,
            seller_name=payload.seller_name,
            title=payload.title,
            brand=payload.brand,
            model=payload.model,
            image_url=payload.image_url,
            product_url=payload.product_url,
            unit_price=float(payload.unit_price),
            shipping_price=float(payload.shipping_price or 0.0),
            total_price=float(payload.total_price or (payload.unit_price + (payload.shipping_price or 0.0))),
            delivery_estimate=payload.delivery_estimate,
            availability=payload.availability,
            rating=payload.rating,
            review_count=payload.review_count,
            specifications=payload.specifications,
            raw_source_metadata=payload.raw_source_metadata or {},
            source_domain=getattr(payload, "source_domain", None),
            source_rank=getattr(payload, "source_rank", None),
            compatibility_score=getattr(payload, "compatibility_score", None),
            confidence_score=getattr(payload, "confidence_score", None),
            evidence_level=getattr(payload, "evidence_level", None) or ("manual" if payload.source_type == "manual" else "discovered"),
            shipping_destination=getattr(payload, "shipping_destination", None),
            invoice_available=getattr(payload, "invoice_available", None),
            payment_summary=getattr(payload, "payment_summary", None),
            warranty_summary=getattr(payload, "warranty_summary", None),
            captured_method=getattr(payload, "captured_method", None) or ("manual_entry" if payload.source_type == "manual" else "user_submitted"),
            verification_status=getattr(payload, "verification_status", None) or "DISCOVERED",
            verification_summary=getattr(payload, "verification_summary", None) or "Opcao cadastrada para revisao antes de virar recomendacao final.",
            captured_at=datetime.now(timezone.utc),
            status="PENDING",
            selected=False
        )
        db.add(option)
        db.commit()
        db.refresh(option)
        return option

    @staticmethod
    def select_item_option(db: Session, item_id: uuid.UUID, option_id: uuid.UUID, current_user: User) -> PurchaseRequestItem:
        from app.models.purchase import PurchaseRequestItem, PurchaseItemOption
        
        item = db.query(PurchaseRequestItem).filter(PurchaseRequestItem.id == item_id).first()
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item de requisição não encontrado.")

        # Valida nível de acesso
        user_level = ApprovalService.get_user_module_level(db, current_user, "purchases")
        is_admin = current_user.role and current_user.role.name == "ADMIN"
        if LEVEL_VALUES[user_level] < LEVEL_VALUES[PermissionLevel.NORMAL] and not is_admin and item.purchase_request.requester_user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permissão insuficiente.")

        # Desmarca todas as opções para o item
        db.query(PurchaseItemOption).filter(PurchaseItemOption.purchase_item_id == item_id).update({"selected": False})
        
        # Seleciona a opção correspondente
        option = db.query(PurchaseItemOption).filter(
            PurchaseItemOption.id == option_id,
            PurchaseItemOption.purchase_item_id == item_id
        ).first()
        
        if not option:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opção de item não encontrada.")
            
        option.selected = True
        item.selected_option_id = option_id
        
        # O preço estimado do item passa a ser o preço total da opção
        item.estimated_unit_price = option.total_price
        
        db.commit()
        db.refresh(item)
        
        # Recalcula o valor total estimado da requisição
        total = sum(float(it.estimated_unit_price or 0.0) * float(it.quantity) for it in item.purchase_request.items)
        item.purchase_request.estimated_total = total
        db.commit()
        
        return item

    @staticmethod
    def list_item_options(db: Session, item_id: uuid.UUID, current_user: User) -> List[PurchaseItemOption]:
        from app.models.purchase import PurchaseRequestItem, PurchaseItemOption
        
        item = db.query(PurchaseRequestItem).filter(PurchaseRequestItem.id == item_id).first()
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item de requisição não encontrado.")

        return db.query(PurchaseItemOption).filter(PurchaseItemOption.purchase_item_id == item_id).all()

    @staticmethod
    def place_order(db: Session, request_id: uuid.UUID, payload: Any, current_user: User) -> PurchaseRequest:
        from app.models.purchase import PurchaseRequest, PurchaseActivity
        
        request = db.query(PurchaseRequest).filter(PurchaseRequest.id == request_id).first()
        if not request:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requisição de compra não encontrada.")
            
        user_level = ApprovalService.get_user_module_level(db, current_user, "purchases")
        is_admin = current_user.role and current_user.role.name == "ADMIN"
        if LEVEL_VALUES[user_level] < LEVEL_VALUES[PermissionLevel.NORMAL] and not is_admin and request.requester_user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permissão insuficiente.")

        # Avança o status geral da compra para ORDERED
        request.status = "ORDERED"
        request.approved_total = float(payload.final_value)
        request.updated_at = datetime.now(timezone.utc)
        
        # Atualiza status operacional e de entrega por item
        for item in request.items:
            item.purchasing_status = "ORDERED"
            item.delivery_status = "AWAITING_DELIVERY"
            
        # Registra detalhes adicionais no notes ou similar
        notes_str = f"[Pedido Registrado] Nro Pedido: {payload.order_number or 'N/A'}. "
        notes_str += f"Forma de Pagamento: {payload.payment_method or 'N/A'}. "
        notes_str += f"Frete: R$ {float(payload.shipping_price or 0.0):.2f}. "
        if payload.notes:
            notes_str += f"Observações: {payload.notes}"
        request.notes = (request.notes or "") + "\n" + notes_str
        
        activity = PurchaseActivity(
            purchase_request_id=request.id,
            user_id=current_user.id,
            action="order.placed",
            details={
                "order_number": payload.order_number,
                "final_value": float(payload.final_value),
                "shipping_price": float(payload.shipping_price or 0.0),
                "payment_method": payload.payment_method
            },
            created_at=datetime.now(timezone.utc)
        )
        db.add(activity)
        db.commit()
        db.refresh(request)
        return request

    @staticmethod
    def receive_delivery(db: Session, request_id: uuid.UUID, payload: Any, current_user: User) -> PurchaseRequest:
        from app.models.purchase import PurchaseRequest, PurchaseActivity
        from app.models.stock import StockCatalogItem, StockCatalogCybersulProduct, StockCatalogLink, StockCatalogPriceHistory, StockCatalogImportRun
        
        request = db.query(PurchaseRequest).filter(PurchaseRequest.id == request_id).first()
        if not request:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requisição de compra não encontrada.")
            
        user_level = ApprovalService.get_user_module_level(db, current_user, "purchases")
        is_admin = current_user.role and current_user.role.name == "ADMIN"
        if LEVEL_VALUES[user_level] < LEVEL_VALUES[PermissionLevel.NORMAL] and not is_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permissão insuficiente.")

        item_delivery_map = {str(d.item_id): d for d in payload.items}
        
        total_items_in_request = len(request.items)
        fully_delivered_count = 0
        partially_delivered_count = 0
        
        for item in request.items:
            item_id_str = str(item.id)
            if item_id_str in item_delivery_map:
                del_info = item_delivery_map[item_id_str]
                qty_rec = float(del_info.quantity_received)
                
                # Se recebeu integralmente ou mais
                if qty_rec >= float(item.quantity):
                    item.delivery_status = "DELIVERED"
                    fully_delivered_count += 1
                elif qty_rec > 0:
                    item.delivery_status = "PARTIALLY_DELIVERED"
                    partially_delivered_count += 1
                else:
                    item.delivery_status = "AWAITING_DELIVERY"
                
                # Atualiza especificações com logs de recebimento
                log_msg = f"[Recebimento: {qty_rec:.2f}/{item.quantity:.2f} recebido]"
                if del_info.is_damaged:
                    log_msg += " (AVARIADO!)"
                if del_info.deviation_notes:
                    log_msg += f" Notas: {del_info.deviation_notes}"
                item.specifications = (item.specifications or "") + "\n" + log_msg
                
                # --- PROCESSAMENTO DE ESTOQUE ---
                if qty_rec > 0:
                    catalog_item_id = item.stock_catalog_item_id
                    
                    # Se for item externo e o usuário escolheu salvar no catálogo
                    if not catalog_item_id and del_info.save_in_catalog:
                        # Criar item no catálogo de estoque!
                        import_run = db.query(StockCatalogImportRun).filter(StockCatalogImportRun.source_type == "COMPRAS_NOVA").first()
                        if not import_run:
                            import_run = StockCatalogImportRun(
                                source_type="COMPRAS_NOVA",
                                source_path="purchases_module",
                                source_filename="intelligent_purchases",
                                source_hash="system_purchases_hash",
                                status="SUCCESS",
                                started_at=datetime.now(timezone.utc),
                                finished_at=datetime.now(timezone.utc),
                            )
                            db.add(import_run)
                            db.commit()
                            db.refresh(import_run)
                        
                        import hashlib
                        cybersul_code = "COMP_" + hashlib.md5(item.free_text_description.encode('utf-8')).hexdigest()[:8].upper()
                        
                        cyber_prod = db.query(StockCatalogCybersulProduct).filter(StockCatalogCybersulProduct.cybersul_code == cybersul_code).first()
                        if not cyber_prod:
                            cyber_prod = StockCatalogCybersulProduct(
                                cybersul_code=cybersul_code,
                                description=item.free_text_description,
                                normalized_description=item.free_text_description.lower(),
                                unit=item.unit_of_measure or "un",
                                balance_vesper=qty_rec,
                                balance_ventrio=0.0,
                                balance_total=qty_rec,
                                cost_price=float(item.estimated_unit_price or 0.0),
                                active=True,
                                source_row=1,
                                import_run_id=import_run.id
                            )
                            db.add(cyber_prod)
                            db.commit()
                            db.refresh(cyber_prod)
                        else:
                            cyber_prod.balance_vesper = float(cyber_prod.balance_vesper) + qty_rec
                            cyber_prod.balance_total = float(cyber_prod.balance_vesper) + float(cyber_prod.balance_ventrio)
                        
                        # Criar item no catálogo
                        new_cat_item = StockCatalogItem(
                            import_run_id=import_run.id,
                            source_sheet="IntelligentPurchases",
                            display_name=item.free_text_description,
                            base_name=item.free_text_description,
                            normalized_name=item.free_text_description.lower(),
                            identity_hash=hashlib.md5(f"{item.free_text_description}_purchases".encode('utf-8')).hexdigest(),
                            cybersul_product_id=cyber_prod.id,
                            active=True,
                            is_operational=True
                        )
                        db.add(new_cat_item)
                        db.commit()
                        db.refresh(new_cat_item)
                        
                        # Cria link
                        link = StockCatalogLink(
                            stock_catalog_item_id=new_cat_item.id,
                            cybersul_product_id=cyber_prod.id,
                            match_type="MANUAL",
                            confidence=1.0,
                            approved_by_user_id=current_user.id,
                            approved_at=datetime.now(timezone.utc),
                            needs_review=False
                        )
                        db.add(link)
                        db.commit()
                        
                        item.stock_catalog_item_id = new_cat_item.id
                        catalog_item_id = new_cat_item.id
                    
                    if catalog_item_id:
                        cat_item = db.query(StockCatalogItem).filter(StockCatalogItem.id == catalog_item_id).first()
                        if cat_item and cat_item.cybersul_product:
                            cyber_prod = cat_item.cybersul_product
                            if not del_info.save_in_catalog:
                                cyber_prod.balance_vesper = float(cyber_prod.balance_vesper or 0.0) + qty_rec
                                cyber_prod.balance_total = float(cyber_prod.balance_vesper) + float(cyber_prod.balance_ventrio or 0.0)
                            
                            # Registra histórico
                            from app.models.stock import StockCatalogSupplier
                            from app.models.purchase import PurchaseItemOption
                            
                            supplier_name_to_use = "Mercado Externo"
                            opt = None
                            if item.selected_option_id:
                                opt = db.query(PurchaseItemOption).filter(PurchaseItemOption.id == item.selected_option_id).first()
                            
                            if opt:
                                if opt.store_name:
                                    supplier_name_to_use = opt.store_name
                                elif opt.seller_name:
                                    supplier_name_to_use = opt.seller_name
                            elif item.purchase_request.quotations:
                                q_supplier = item.purchase_request.quotations[0].supplier
                                if q_supplier and q_supplier.person:
                                    supplier_name_to_use = q_supplier.person.name
                                    
                            norm_name = supplier_name_to_use.lower().strip()
                            stock_supplier = db.query(StockCatalogSupplier).filter(StockCatalogSupplier.normalized_name == norm_name).first()
                            if not stock_supplier:
                                stock_supplier = StockCatalogSupplier(
                                    name=supplier_name_to_use,
                                    normalized_name=norm_name,
                                    active=True,
                                    source="COMPRAS"
                                )
                                db.add(stock_supplier)
                                db.flush()
                            
                            old_price = float(cyber_prod.cost_price or 0.0)
                            new_price = float(opt.unit_price) if opt else float(item.estimated_unit_price or 0.0)
                            
                            price_hist = StockCatalogPriceHistory(
                                item_id=catalog_item_id,
                                supplier_id=stock_supplier.id,
                                old_price=old_price,
                                new_price=new_price,
                                source="MANUAL",
                                source_reference=f"Compra ID {request.id}",
                                changed_by_user_id=current_user.id,
                                notes=f"Entrada de saldo via Compra ID {request.id}"
                            )
                            db.add(price_hist)
                            
        # Define o status geral da requisição de compra
        if fully_delivered_count == total_items_in_request:
            request.status = "DELIVERED"
        elif fully_delivered_count > 0 or partially_delivered_count > 0:
            request.status = "PARTIAL_DELIVERY"
            
        request.updated_at = datetime.now(timezone.utc)
        
        activity = PurchaseActivity(
            purchase_request_id=request.id,
            user_id=current_user.id,
            action="delivery.received",
            details={
                "notes": payload.notes,
                "fully_delivered_count": fully_delivered_count,
                "partially_delivered_count": partially_delivered_count
            },
            created_at=datetime.now(timezone.utc)
        )
        db.add(activity)
        db.commit()
        db.refresh(request)
        return request

    @staticmethod
    def _is_admin_or_messias(user: User) -> bool:
        role_name = user.role.name if user.role else ""
        return role_name in {"ADMIN", "MESSIAS"}

    @staticmethod
    def preview_test_data(db: Session, current_user: User) -> Dict[str, Any]:
        if not PurchasesService._is_admin_or_messias(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado. Apenas administradores (Admin/Messias) podem visualizar dados de teste."
            )
        
        from app.models.purchase import PurchaseRequest, PurchaseRFQ
        
        # Filtros de teste
        req_query = db.query(PurchaseRequest).filter(
            (PurchaseRequest.title.ilike("%[TEST]%")) |
            (PurchaseRequest.title.ilike("%[TESTE]%")) |
            (PurchaseRequest.title.ilike("%sandbox%")) |
            (PurchaseRequest.title.ilike("%teste%")) |
            (PurchaseRequest.description.ilike("%[TEST]%")) |
            (PurchaseRequest.description.ilike("%[TESTE]%")) |
            (PurchaseRequest.origin_type == "test")
        )
        
        test_requests = req_query.all()
        test_request_ids = [r.id for r in test_requests]
        
        # RFQs de teste
        test_rfqs = []
        if test_request_ids:
            test_rfqs = db.query(PurchaseRFQ).filter(
                PurchaseRFQ.purchase_request_id.in_(test_request_ids)
            ).all()
            
        # Determina quais podem ser fisicamente removidos (Safe) e quais possuem histórico operacional (Locked)
        safe_to_delete = []
        locked_from_delete = []
        
        # Status que possuem aprovação/pedido/historico real
        locked_statuses = {"APPROVED", "ORDERED", "APPROVAL_REQUIRED", "DELIVERED", "PARTIAL_DELIVERY"}
        
        for r in test_requests:
            is_locked = False
            reasons = []
            
            if r.status in locked_statuses:
                is_locked = True
                reasons.append(f"Status real '{r.status}'")
                
            # Verifica se alguma RFQ associada já foi enviada de fato (não modo teste)
            for rfq in r.rfqs:
                if rfq.status not in {"DRAFT", "READY_FOR_REVIEW"}:
                    is_locked = True
                    reasons.append(f"RFQ '{rfq.title}' com status enviado/ativo '{rfq.status}'")
            
            # Se for bloqueado, vai pro locked
            if is_locked:
                locked_from_delete.append({
                    "id": str(r.id),
                    "title": r.title,
                    "status": r.status,
                    "reason": ", ".join(reasons)
                })
            else:
                safe_to_delete.append({
                    "id": str(r.id),
                    "title": r.title,
                    "status": r.status
                })
                
        return {
            "summary": {
                "total_test_requests": len(test_requests),
                "safe_to_delete_count": len(safe_to_delete),
                "locked_count": len(locked_from_delete),
                "total_test_rfqs": len(test_rfqs)
            },
            "safe_requests": safe_to_delete,
            "locked_requests": locked_from_delete
        }

    @staticmethod
    def purge_test_data(db: Session, current_user: User) -> Dict[str, Any]:
        if not PurchasesService._is_admin_or_messias(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado. Apenas administradores (Admin/Messias) podem realizar a limpeza de dados de teste."
            )
            
        preview = PurchasesService.preview_test_data(db, current_user)
        import uuid
        safe_ids = [uuid.UUID(r["id"]) for r in preview["safe_requests"]]
        
        if not safe_ids:
            return {
                "message": "Nenhum dado de teste seguro para exclusão foi encontrado.",
                "purged_requests_count": 0,
                "locked_requests_count": preview["summary"]["locked_count"]
            }
            
        from app.models.purchase import PurchaseRequest
        
        # Deleta os registros com cascateamento do BD
        deleted_count = 0
        for req_id in safe_ids:
            r = db.query(PurchaseRequest).filter(PurchaseRequest.id == req_id).first()
            if r:
                db.delete(r)
                deleted_count += 1
                
        db.commit()
        
        return {
            "message": f"Limpeza concluída. {deleted_count} requisições de teste foram excluídas fisicamente do banco de dados.",
            "purged_requests_count": deleted_count,
            "locked_requests_count": preview["summary"]["locked_count"]
        }
