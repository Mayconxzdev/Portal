import hashlib
import re
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.events import emit_event
from app.models.it import ITAsset
from app.models.purchase import (
    PurchaseActivity,
    PurchaseCanonicalProduct,
    PurchaseItemOption,
    PurchaseOfferFieldEvidence,
    PurchaseOfferPriceCondition,
    PurchaseRequestItem,
    PurchaseResearchTask,
    PurchaseSearchSession,
    PurchaseSearchSource,
)
from app.models.stock import StockCatalogItem, StockCatalogOffer
from app.models.user import User
from app.modules.purchases.search_provider import (
    CredentialsMissingException,
    get_search_provider,
    is_safe_url,
    safe_fetch_html,
)


DEFAULT_CEP = "21043-030"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _money(value: Any) -> Decimal:
    if value is None or value == "":
        return Decimal("0.00")
    return Decimal(str(value)).quantize(Decimal("0.01"))


def _human_domain(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    host = urlparse(url).netloc.lower().replace("www.", "")
    return host or None


def _normalize_key(value: str) -> str:
    value = (value or "").lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())[:300] or "produto"


def _hash_snapshot(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()


class PurchaseResearchPlanner:
    """Interpreta a necessidade e cria subtarefas por categoria."""

    GPU_WORDS = {"placa de video", "placa de vídeo", "gpu", "rtx", "radeon", "geforce"}
    RAM_WORDS = {"memoria ram", "memória ram", "ddr3", "ddr4", "ddr5", "sodimm"}
    INDUSTRIAL_WORDS = {"arame", "tubo", "chapa", "aco", "aço", "inox", "flange", "parafuso", "rolamento"}

    def detect_category(self, text: str) -> str:
        clean = text.lower()
        if any(word in clean for word in self.GPU_WORDS):
            return "informatica_gpu"
        if any(word in clean for word in self.RAM_WORDS):
            return "informatica_memoria"
        if any(word in clean for word in self.INDUSTRIAL_WORDS):
            return "material_industrial"
        return "general_external"

    def extract_budget(self, text: str, fallback: Optional[float]) -> Optional[float]:
        if fallback is not None:
            return float(fallback)
        match = re.search(r"(?:ate|até|r\$)\s*([\d\.\,]+)", text.lower())
        if not match:
            return None
        raw = match.group(1).replace(".", "").replace(",", ".")
        try:
            return float(raw)
        except ValueError:
            return None

    def extract_destination(self, text: str, fallback: Optional[str]) -> Optional[str]:
        if fallback:
            return fallback
        match = re.search(r"\bpara\s+(?:o\s+|a\s+)?([^,.;]+)", text, re.IGNORECASE)
        if not match:
            return None
        destination = match.group(1).strip()
        return destination[:255] if destination else None

    def plan(self, item: PurchaseRequestItem) -> Dict[str, Any]:
        text = item.free_text_description or item.description or item.normalized_name or "item"
        category = self.detect_category(text)
        budget = self.extract_budget(text, float(item.budget_limit) if item.budget_limit is not None else None)
        destination = self.extract_destination(text, item.destination)

        task_map = {
            "informatica_gpu": [
                ("interpret_need", "Entender uso, orçamento e destino"),
                ("asset_compatibility", "Verificar compatibilidade do computador"),
                ("model_discovery", "Identificar modelos dentro do orçamento"),
                ("market_search", "Buscar lojas brasileiras"),
                ("offer_verification", "Confirmar preço total, frete e garantia"),
                ("equivalents", "Encontrar alternativas equivalentes"),
            ],
            "informatica_memoria": [
                ("interpret_need", "Entender capacidade, DDR e formato"),
                ("asset_compatibility", "Verificar compatibilidade com o computador"),
                ("market_search", "Buscar lojas brasileiras"),
                ("offer_verification", "Confirmar preço total e frete"),
            ],
            "material_industrial": [
                ("interpret_need", "Confirmar material, medida e norma"),
                ("stock_lookup", "Consultar Estoque e Catálogo"),
                ("supplier_lookup", "Consultar fornecedores vinculados"),
                ("quote_preparation", "Preparar cotação direta quando necessário"),
            ],
            "general_external": [
                ("interpret_need", "Entender produto, quantidade e orçamento"),
                ("market_search", "Buscar opções de mercado"),
                ("offer_verification", "Confirmar preço total e frete"),
            ],
        }

        criteria = {
            "category": category,
            "budget_limit": budget,
            "destination": destination,
            "quantity": float(item.quantity or 1),
            "shipping_postal_code": DEFAULT_CEP,
        }
        return {
            "category": category,
            "query": text,
            "budget_limit": budget,
            "destination": destination,
            "tasks": [
                {"task_type": task_type, "title": title, "criteria": criteria}
                for task_type, title in task_map[category]
            ],
            "summary": {
                "human_category": {
                    "informatica_gpu": "Placa de video",
                    "informatica_memoria": "Memoria RAM",
                    "material_industrial": "Material industrial",
                    "general_external": "Compra externa",
                }[category],
                "criteria": criteria,
            },
        }


class CompatibilityResolver:
    """Resolve compatibilidade usando destino, TI/Ativos e regras por categoria."""

    def resolve(self, db: Session, session: PurchaseSearchSession, item: PurchaseRequestItem) -> Dict[str, Any]:
        category = session.category
        destination = session.destination or item.destination
        missing_questions: List[Dict[str, Any]] = []
        asset_payload = None

        if destination:
            cleaned_destination = destination.lower()
            possible_name = cleaned_destination.replace("pc do", "").replace("pc da", "").strip()
            asset = (
                db.query(ITAsset)
                .join(User, ITAsset.assigned_to_user_id == User.id, isouter=True)
                .filter(
                    or_(
                        ITAsset.name.ilike(f"%{destination}%"),
                        ITAsset.hostname.ilike(f"%{destination}%"),
                        User.username.ilike(f"%{possible_name}%"),
                        User.email.ilike(f"%{possible_name}%"),
                    )
                )
                .first()
            )
            if asset:
                asset_payload = {
                    "asset_id": asset.id,
                    "name": asset.name,
                    "hostname": asset.hostname,
                    "processor": asset.processor,
                    "motherboard": asset.motherboard,
                    "gpu": asset.gpu,
                    "power_supply": asset.power_supply,
                    "cabinet": asset.cabinet,
                    "ram": asset.ram,
                }

        if category == "informatica_gpu":
            if not asset_payload:
                missing_questions.append({
                    "field": "destination_asset",
                    "question": "Qual computador recebera a placa de video?",
                    "reason": "A compatibilidade depende da fonte, gabinete e placa-mae.",
                })
            elif not asset_payload.get("power_supply"):
                missing_questions.append({
                    "field": "power_supply",
                    "question": "Qual e a fonte instalada nesse computador?",
                    "reason": "A placa de video pode exigir potencia e conectores especificos.",
                })
            elif not asset_payload.get("cabinet"):
                missing_questions.append({
                    "field": "cabinet",
                    "question": "O gabinete tem limite de comprimento para a placa?",
                    "reason": "Alguns modelos podem nao caber fisicamente.",
                })
        elif category == "material_industrial":
            text = f"{item.free_text_description or ''} {item.specifications or ''}".lower()
            for field, label in [
                ("material", "material"),
                ("medida", "medida"),
                ("quantidade", "quantidade"),
            ]:
                if field not in text and field == "material":
                    missing_questions.append({
                        "field": field,
                        "question": f"Qual e o {label} correto?",
                        "reason": "Esse dado muda fornecedores, preco e equivalentes.",
                    })

        base_score = 0.95 if not missing_questions else 0.65
        return {
            "compatibility_score": base_score,
            "asset": asset_payload,
            "missing_questions": missing_questions,
            "summary": "Compatibilidade validada com os dados disponiveis." if not missing_questions else "Faltam dados que podem alterar a compra.",
        }


class OfferVerificationEngine:
    """Confirma campos de uma oferta e grava evidencias por campo."""

    CONFIRMABLE_FIELDS = {
        "title": "produto",
        "store_name": "loja",
        "seller_name": "vendedor",
        "unit_price": "preco",
        "shipping_price": "frete",
        "total_price": "total",
        "delivery_estimate": "prazo",
        "availability": "disponibilidade",
        "product_url": "link",
        "invoice_available": "nota_fiscal",
        "payment_summary": "pagamento",
        "warranty_summary": "garantia",
    }

    def record_field_evidence(
        self,
        db: Session,
        option: PurchaseItemOption,
        field_name: str,
        field_status: str,
        source_type: str,
        method: str,
        value: Any,
        confidence: float,
        source_url: Optional[str] = None,
    ) -> None:
        evidence = PurchaseOfferFieldEvidence(
            option_id=option.id,
            search_session_id=getattr(option, "search_session_id", None),
            field_name=field_name,
            field_status=field_status,
            source_type=source_type,
            method=method,
            confidence=confidence,
            source_url=source_url,
            captured_value=str(value) if value is not None else None,
            snapshot_hash=_hash_snapshot(f"{field_name}|{value}|{source_url or ''}"),
            captured_at=_now(),
            last_verified_at=_now() if field_status == "confirmed" else None,
        )
        db.add(evidence)

    def record_discovery_evidence(self, db: Session, option: PurchaseItemOption, source_type: str, method: str) -> None:
        for field_name in self.CONFIRMABLE_FIELDS:
            value = getattr(option, field_name, None)
            if value is None or value == "":
                status_value = "unavailable"
                confidence = 0.0
            elif source_type in {"direct_store", "manual_link", "stock", "internal_supplier"}:
                status_value = "confirmed"
                confidence = 0.9
            else:
                status_value = "estimated"
                confidence = 0.55
            self.record_field_evidence(
                db,
                option,
                field_name,
                status_value,
                source_type,
                method,
                value,
                confidence,
                option.product_url,
            )

    def verify_option(self, db: Session, option: PurchaseItemOption) -> PurchaseItemOption:
        if not option.product_url:
            option.verification_status = "PARTIALLY_CONFIRMED"
            option.verification_summary = "Oferta sem link final; alguns campos permanecem estimados."
            self.record_discovery_evidence(db, option, "manual", "user_or_provider_data")
            return option

        safe, reason = is_safe_url(option.product_url)
        if not safe:
            option.verification_status = "BLOCKED"
            option.verification_summary = reason
            return option

        try:
            html = safe_fetch_html(option.product_url, timeout_seconds=8, max_bytes=2 * 1024 * 1024)
        except Exception as exc:
            option.verification_status = "PARTIALLY_CONFIRMED"
            option.verification_summary = "Nao foi possivel confirmar a pagina da loja agora."
            self.record_discovery_evidence(db, option, "direct_store", "fetch_failed")
            self.record_field_evidence(db, option, "product_url", "confirmed", "direct_store", "url_validation", option.product_url, 0.9, option.product_url)
            option.raw_source_metadata = {**(option.raw_source_metadata or {}), "verification_error": str(exc)[:240]}
            return option

        page_hash = _hash_snapshot(html[:200000])
        option.raw_source_metadata = {
            **(option.raw_source_metadata or {}),
            "verified_snapshot_hash": page_hash,
            "verified_at": _now().isoformat(),
        }
        try:
            from app.modules.purchases.offer_extractor import extract_offer_from_html

            extracted = extract_offer_from_html(html, url=option.product_url, fallback_title=option.title)
            if extracted.title:
                option.title = extracted.title[:255]
            db.query(PurchaseOfferPriceCondition).filter(
                PurchaseOfferPriceCondition.option_id == option.id
            ).delete(synchronize_session=False)
            recommended_amount = None
            for condition in extracted.price_conditions:
                is_recommended = condition.condition_type == extracted.recommended_condition
                if is_recommended:
                    recommended_amount = condition.amount
                db.add(PurchaseOfferPriceCondition(
                    option_id=option.id,
                    condition_type=condition.condition_type,
                    amount=float(condition.amount),
                    installments=condition.installments,
                    installment_amount=float(condition.installment_amount) if condition.installment_amount is not None else None,
                    discount_percent=float(condition.discount_percent) if condition.discount_percent is not None else None,
                    is_recommended=is_recommended,
                    source_label=condition.source_label,
                    evidence_status=condition.evidence_status,
                    captured_at=_now(),
                ))
            if recommended_amount is not None and recommended_amount > 0:
                option.unit_price = float(recommended_amount)
                shipping = Decimal(str(option.shipping_price or 0))
                option.total_price = float(recommended_amount + shipping)
                labels = {"pix": "Pix", "boleto": "Boleto", "card": "Cartao", "current": "Preco atual"}
                option.payment_summary = labels.get(extracted.recommended_condition or "", "Condicao confirmada")
        except Exception as exc:
            option.raw_source_metadata = {
                **(option.raw_source_metadata or {}),
                "price_extraction_error": str(exc)[:240],
            }
        option.verification_status = "PARTIALLY_CONFIRMED"
        option.verification_summary = "A pagina foi acessada e os campos principais foram registrados com evidencia."
        for field_name in self.CONFIRMABLE_FIELDS:
            value = getattr(option, field_name, None)
            status_value = "confirmed" if value not in {None, ""} else "unavailable"
            self.record_field_evidence(db, option, field_name, status_value, "direct_store", "httpx_structured_or_html", value, 0.85 if status_value == "confirmed" else 0.0, option.product_url)
        return option


class PurchaseRecommendationAgent:
    """Gera recomendacao humana com base somente em dados persistidos."""

    def build(self, session: PurchaseSearchSession) -> Dict[str, Any]:
        options = list(session.options or [])
        confirmed_options = [
            opt for opt in options
            if (opt.verification_status or "").upper() in {"PARTIALLY_CONFIRMED", "CONFIRMED"}
        ]
        ranked = sorted(
            options,
            key=lambda opt: (
                float(opt.total_price or 999999999),
                -float(opt.compatibility_score or 0),
                -float(opt.confidence_score or 0),
            ),
        )
        cheapest = min(confirmed_options or options, key=lambda opt: float(opt.total_price or 999999999), default=None)

        def delivery_days(opt: PurchaseItemOption) -> int:
            text = opt.delivery_estimate or ""
            match = re.search(r"(\d+)", text)
            return int(match.group(1)) if match else 999

        fastest = min(confirmed_options or options, key=delivery_days, default=None)
        best = ranked[0] if ranked else None
        stores = {opt.store_name for opt in options if opt.store_name}
        compatible_count = sum(1 for opt in options if float(opt.compatibility_score or 0) >= 0.75)
        budget = float(session.budget_limit or 0)
        within_budget = [
            opt for opt in options
            if budget <= 0 or float(opt.total_price or 0) <= budget
        ]

        if not options:
            summary = "Ainda nao ha ofertas confirmadas para comparar. Adicione um link, aguarde a pesquisa ou cadastre uma opcao manual."
        else:
            pending = []
            if any((opt.shipping_price is None) for opt in options):
                pending.append("frete")
            if any((opt.verification_status or "").upper() in {"DISCOVERED", "PARTIAL", "PARTIALLY_CONFIRMED"} for opt in options):
                pending.append("confirmacao de oferta")
            pending_text = f" Falta confirmar: {', '.join(sorted(set(pending)))}." if pending else " Os dados principais ja possuem evidencia."
            summary = (
                f"Encontramos {len(options)} ofertas em {len(stores)} lojas. "
                f"{len(within_budget)} ofertas atendem ao orçamento e {compatible_count} parecem compativeis."
                f"{pending_text}"
            )

        return {
            "summary": summary,
            "cheapest_option_id": str(cheapest.id) if cheapest else None,
            "best_overall_option_id": str(best.id) if best else None,
            "fastest_option_id": str(fastest.id) if fastest else None,
            "highlights": {
                "cheapest": self._option_payload(cheapest),
                "best_overall": self._option_payload(best),
                "fastest": self._option_payload(fastest),
            },
            "why": self._why(best, cheapest, fastest),
            "pending": session.missing_questions or [],
            "generated_at": _now().isoformat(),
        }

    def _option_payload(self, option: Optional[PurchaseItemOption]) -> Optional[Dict[str, Any]]:
        if not option:
            return None
        return {
            "option_id": str(option.id),
            "title": option.title,
            "store_name": option.store_name,
            "seller_name": option.seller_name,
            "total_price": float(option.total_price or 0),
            "delivery_estimate": option.delivery_estimate,
            "compatibility_score": float(option.compatibility_score or 0),
            "confidence_score": float(option.confidence_score or 0),
            "verification_status": option.verification_status,
        }

    def _why(
        self,
        best: Optional[PurchaseItemOption],
        cheapest: Optional[PurchaseItemOption],
        fastest: Optional[PurchaseItemOption],
    ) -> List[str]:
        notes: List[str] = []
        if best:
            notes.append(f"Melhor opcao geral: {best.title}, combinando total, compatibilidade e confianca dos dados.")
        if cheapest:
            notes.append(f"Menor custo total encontrado: {cheapest.title}.")
        if fastest and fastest.id != getattr(cheapest, "id", None):
            notes.append(f"Entrega mais rapida: {fastest.title}.")
        return notes


class PurchaseResearchEngine:
    def __init__(self) -> None:
        self.planner = PurchaseResearchPlanner()
        self.compatibility = CompatibilityResolver()
        self.verifier = OfferVerificationEngine()
        self.recommender = PurchaseRecommendationAgent()

    def create_session(
        self,
        db: Session,
        item_id: uuid.UUID,
        current_user: User,
        payload: Any,
    ) -> PurchaseSearchSession:
        item = (
            db.query(PurchaseRequestItem)
            .options(joinedload(PurchaseRequestItem.purchase_request), joinedload(PurchaseRequestItem.options))
            .filter(PurchaseRequestItem.id == item_id)
            .first()
        )
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item de compra nao encontrado.")

        query = getattr(payload, "query", None) or item.free_text_description or item.description or item.normalized_name or "item"
        destination = getattr(payload, "destination", None) or item.destination
        shipping_postal_code = getattr(payload, "shipping_postal_code", None) or DEFAULT_CEP
        budget_limit = getattr(payload, "budget_limit", None)
        if budget_limit is None and item.budget_limit is not None:
            budget_limit = float(item.budget_limit)

        planned = self.planner.plan(item)
        session = PurchaseSearchSession(
            purchase_request_id=item.purchase_request_id,
            purchase_item_id=item.id,
            query=query,
            category=planned["category"],
            status="queued",
            progress_percent=0,
            current_step="interpretando necessidade",
            destination=destination or planned.get("destination"),
            shipping_postal_code=shipping_postal_code,
            budget_limit=budget_limit if budget_limit is not None else planned.get("budget_limit"),
            planner_summary=planned["summary"],
            missing_questions=[],
            created_by_user_id=current_user.id,
            created_at=_now(),
            updated_at=_now(),
        )
        db.add(session)
        db.flush()
        for task in planned["tasks"]:
            db.add(PurchaseResearchTask(search_session_id=session.id, **task))
        db.add(PurchaseActivity(
            purchase_request_id=item.purchase_request_id,
            user_id=current_user.id,
            action="research.started",
            details={"item_id": str(item.id), "session_id": str(session.id), "query": query},
            created_at=_now(),
        ))
        db.commit()
        db.refresh(session)
        self._emit_event(db, "purchase.research.started", session, current_user)
        return session

    def run_session(self, db: Session, session_id: uuid.UUID, current_user: Optional[User] = None) -> PurchaseSearchSession:
        session = self._get_session_model(db, session_id)
        item = session.purchase_item
        session.status = "running"
        session.started_at = session.started_at or _now()
        self._update_progress(db, session, 10, "interpretando necessidade")

        compat = self.compatibility.resolve(db, session, item)
        session.missing_questions = compat["missing_questions"]
        session.planner_summary = {**(session.planner_summary or {}), "compatibility": compat}
        self._update_progress(db, session, 25, "consultando Estoque")
        self._collect_stock_options(db, session, item, compat)

        self._update_progress(db, session, 40, "consultando fornecedores conhecidos")
        self._collect_history_context(db, session)

        if (item.classification or "").upper() != "INTERNAL":
            self._update_progress(db, session, 55, "procurando lojas")
            self._collect_searxng(db, session)
            self._collect_external_provider(db, session)
            self._collect_gemini_sources(db, session)

        self._update_progress(db, session, 75, "validando produtos")
        for option in list(session.options or []):
            self.verifier.verify_option(db, option)

        self._update_progress(db, session, 88, "agrupando produtos")
        self._group_canonical_products(db, session)

        self._update_progress(db, session, 95, "atualizando recomendacao")
        db.flush()
        db.refresh(session)
        session.recommendation_summary = self.recommender.build(session)
        session.status = "completed_with_pending" if session.missing_questions else "completed"
        session.progress_percent = 100
        session.current_step = "concluida com pendencias" if session.missing_questions else "concluida"
        session.completed_at = _now()
        session.updated_at = _now()
        db.commit()
        db.refresh(session)
        self._emit_event(db, "purchase.research.updated", session, current_user)
        return session

    def refresh_session(self, db: Session, session_id: uuid.UUID, current_user: User) -> PurchaseSearchSession:
        session = self._get_session_model(db, session_id)
        session.status = "queued"
        session.progress_percent = 0
        session.current_step = "interpretando necessidade"
        session.error_message = None
        session.completed_at = None
        session.updated_at = _now()
        db.commit()
        return self.run_session(db, session.id, current_user)

    def verify_offer(self, db: Session, session_id: uuid.UUID, option_id: uuid.UUID, current_user: User) -> PurchaseSearchSession:
        session = self._get_session_model(db, session_id)
        option = (
            db.query(PurchaseItemOption)
            .filter(PurchaseItemOption.id == option_id, PurchaseItemOption.search_session_id == session_id)
            .first()
        )
        if not option:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Oferta nao encontrada nesta pesquisa.")
        self.verifier.verify_option(db, option)
        db.flush()
        session.recommendation_summary = self.recommender.build(session)
        session.updated_at = _now()
        db.commit()
        db.refresh(session)
        self._emit_event(db, "purchase.offer.verified", session, current_user)
        return session

    def get_session_payload(self, db: Session, session_id: uuid.UUID) -> Dict[str, Any]:
        session = self._get_session_model(db, session_id)
        return self._session_payload(session)

    def build_recommendation(self, db: Session, item_id: uuid.UUID) -> Dict[str, Any]:
        session = (
            db.query(PurchaseSearchSession)
            .options(
                joinedload(PurchaseSearchSession.options),
                joinedload(PurchaseSearchSession.options).joinedload(PurchaseItemOption.price_conditions),
                joinedload(PurchaseSearchSession.canonical_products).joinedload(PurchaseCanonicalProduct.options),
            )
            .filter(PurchaseSearchSession.purchase_item_id == item_id)
            .order_by(PurchaseSearchSession.created_at.desc())
            .first()
        )
        if not session:
            return {
                "summary": "Ainda nao ha pesquisa persistida para este item.",
                "highlights": {},
                "why": [],
                "pending": [],
            }
        return session.recommendation_summary or self.recommender.build(session)

    def _collect_stock_options(self, db: Session, session: PurchaseSearchSession, item: PurchaseRequestItem, compat: Dict[str, Any]) -> None:
        source = PurchaseSearchSource(
            search_session_id=session.id,
            source_type="stock",
            source_label="Estoque e Catalogo",
            status="completed",
            result_count=0,
            evidence_summary={"human_label": "Estoque consultado"},
            created_at=_now(),
            updated_at=_now(),
        )
        db.add(source)
        result_count = 0
        if item.stock_catalog_item_id:
            offers = (
                db.query(StockCatalogOffer)
                .options(joinedload(StockCatalogOffer.supplier))
                .filter(
                    StockCatalogOffer.item_id == item.stock_catalog_item_id,
                    StockCatalogOffer.is_current == True,
                )
                .limit(5)
                .all()
            )
            catalog_item = db.query(StockCatalogItem).filter(StockCatalogItem.id == item.stock_catalog_item_id).first()
            for idx, offer in enumerate(offers, start=1):
                price = float(offer.final_value or offer.price or 0)
                if price <= 0:
                    continue
                supplier_name = offer.supplier.name if offer.supplier else "Fornecedor vinculado"
                option = self._create_option(
                    session=session,
                    item=item,
                    source_type="INTERNAL_SUPPLIER",
                    title=catalog_item.display_name if catalog_item else (item.free_text_description or "Item interno"),
                    store_name=supplier_name,
                    seller_name=supplier_name,
                    unit_price=price,
                    shipping_price=None,
                    delivery_estimate=offer.delivery_time,
                    product_url=None,
                    image_url=None,
                    rank=idx,
                    compatibility_score=compat["compatibility_score"],
                    confidence_score=float(offer.confidence or 1.0),
                    evidence_level="confirmed",
                    captured_method="stock_catalog",
                    verification_status="PARTIALLY_CONFIRMED",
                    verification_summary="Preco e fornecedor vieram do Estoque/Catalogo; frete pode depender de cotacao.",
                )
                db.add(option)
                result_count += 1
        source.result_count = result_count

    def _collect_history_context(self, db: Session, session: PurchaseSearchSession) -> None:
        source = PurchaseSearchSource(
            search_session_id=session.id,
            source_type="purchase_history",
            source_label="Historico de compras",
            status="completed",
            result_count=0,
            evidence_summary={"human_label": "Historico consultado"},
            created_at=_now(),
            updated_at=_now(),
        )
        db.add(source)

    def _collect_searxng(self, db: Session, session: PurchaseSearchSession) -> None:
        start = time.perf_counter()
        source = PurchaseSearchSource(
            search_session_id=session.id,
            source_type="searxng",
            source_label="Pesquisa de mercado",
            status="running",
            result_count=0,
            created_at=_now(),
            updated_at=_now(),
        )
        db.add(source)
        db.flush()
        if not settings.PURCHASES_SEARXNG_URL:
            source.status = "skipped"
            source.error_message = "Servico de pesquisa nao configurado."
            return
        try:
            params = {"q": session.query, "format": "json", "language": "pt-BR", "categories": "general"}
            with httpx.Client(timeout=8.0, follow_redirects=True) as client:
                response = client.get(f"{settings.PURCHASES_SEARXNG_URL.rstrip('/')}/search", params=params)
                response.raise_for_status()
                data = response.json()
            count = 0
            for result in (data.get("results") or [])[:5]:
                url = result.get("url")
                title = result.get("title") or session.query
                if not url:
                    continue
                option = self._option_from_discovery(session, title, url, count + 1, "EXTERNAL_MARKET", "searxng_discovery")
                db.add(option)
                count += 1
            source.status = "completed"
            source.result_count = count
        except Exception as exc:
            source.status = "unavailable"
            source.error_message = "Pesquisa de mercado indisponivel agora; outras fontes continuam."
            source.evidence_summary = {"admin_error": str(exc)[:240]}
        finally:
            source.duration_ms = int((time.perf_counter() - start) * 1000)
            source.updated_at = _now()

    def _collect_external_provider(self, db: Session, session: PurchaseSearchSession) -> None:
        start = time.perf_counter()
        source = PurchaseSearchSource(
            search_session_id=session.id,
            source_type="external_provider",
            source_label="Fontes externas configuradas",
            status="running",
            result_count=0,
            created_at=_now(),
            updated_at=_now(),
        )
        db.add(source)
        db.flush()
        try:
            provider = get_search_provider()
            results = provider.search_products(session.query)
            count = 0
            for idx, result in enumerate(results[: min(8, settings.PURCHASES_SEARCH_MAX_PROVIDER_CALLS)], start=1):
                price = float(result.get("unit_price") or 0)
                total = float(result.get("total_price") or (price + float(result.get("shipping_price") or 0)))
                if price <= 0 and total <= 0:
                    continue
                option = self._create_option(
                    session=session,
                    item=session.purchase_item,
                    source_type=result.get("source_type") or "EXTERNAL_MARKET",
                    title=result.get("title") or session.query,
                    store_name=result.get("store_name"),
                    seller_name=result.get("seller_name"),
                    unit_price=price,
                    shipping_price=result.get("shipping_price"),
                    delivery_estimate=result.get("delivery_estimate"),
                    product_url=result.get("product_url"),
                    image_url=result.get("image_url"),
                    rank=idx,
                    compatibility_score=0.85,
                    confidence_score=0.55,
                    evidence_level="estimated",
                    captured_method="provider_discovery",
                    verification_status="DISCOVERED",
                    verification_summary="Resultado descoberto por fonte externa; sera confirmado pela loja quando possivel.",
                    raw_metadata=result.get("raw_source_metadata") or {},
                    rating=result.get("rating"),
                    review_count=result.get("review_count"),
                    brand=result.get("brand"),
                    model=result.get("model"),
                    specifications=result.get("specifications"),
                )
                db.add(option)
                count += 1
            source.status = "completed"
            source.result_count = count
        except CredentialsMissingException:
            source.status = "skipped"
            source.error_message = "Fonte opcional sem credencial configurada."
        except Exception as exc:
            source.status = "unavailable"
            source.error_message = "Fonte externa nao respondeu agora."
            source.evidence_summary = {"admin_error": str(exc)[:240]}
        finally:
            source.duration_ms = int((time.perf_counter() - start) * 1000)
            source.updated_at = _now()

    def _collect_gemini_sources(self, db: Session, session: PurchaseSearchSession) -> None:
        start = time.perf_counter()
        source = PurchaseSearchSource(
            search_session_id=session.id,
            source_type="gemini_grounding",
            source_label="Expansao inteligente de pesquisa",
            status="skipped",
            result_count=0,
            created_at=_now(),
            updated_at=_now(),
        )
        db.add(source)
        if not settings.GEMINI_API_KEY:
            source.error_message = "Provedor opcional nao configurado."
            return
        try:
            prompt = (
                "Você ajuda a planejar pesquisas de compra no Brasil. "
                "Não invente preço, frete, vendedor, avaliação, estoque ou link. "
                "Apenas sugira consultas relacionadas, critérios de compatibilidade e fontes a verificar. "
                f"Necessidade: {session.query}. "
                f"Categoria: {session.category}. "
                f"Destino: {session.destination or 'não informado'}. "
                f"Orçamento: {session.budget_limit or 'não informado'}."
            )
            endpoint = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{settings.PURCHASES_GEMINI_MODEL}:generateContent"
            )
            request_body = {
                "contents": [{"parts": [{"text": prompt}]}],
                "tools": [{"google_search": {}}],
                "generationConfig": {"temperature": 0.2, "maxOutputTokens": 900},
            }
            with httpx.Client(timeout=12.0) as client:
                response = client.post(
                    endpoint,
                    headers={
                        "Content-Type": "application/json",
                        "x-goog-api-key": settings.GEMINI_API_KEY,
                    },
                    json=request_body,
                )
                response.raise_for_status()
                data = response.json()

            candidate = (data.get("candidates") or [{}])[0]
            parts = (((candidate.get("content") or {}).get("parts")) or [])
            text = "\n".join(str(part.get("text", "")) for part in parts if part.get("text")).strip()
            grounding = candidate.get("groundingMetadata") or {}
            chunks = grounding.get("groundingChunks") or []
            cited_sources = []
            for chunk in chunks[:10]:
                web_chunk = chunk.get("web") or {}
                url = web_chunk.get("uri")
                title = web_chunk.get("title")
                if not url:
                    continue
                cited_sources.append({
                    "title": title,
                    "url_hash": _hash_snapshot(url),
                    "domain": _human_domain(url),
                })
            source.status = "completed"
            source.result_count = len(cited_sources)
            source.evidence_summary = {
                "human_label": "Expansao consultada sem gerar oferta final.",
                "policy": "IA nao confirma preco, frete ou disponibilidade.",
                "suggested_queries": grounding.get("webSearchQueries") or [],
                "summary": text[:1200],
                "sources": cited_sources,
            }
        except Exception as exc:
            source.status = "unavailable"
            source.error_message = "Expansao inteligente indisponivel; pesquisa continua pelas outras fontes."
            source.evidence_summary = {"admin_error": str(exc)[:240]}
        finally:
            source.duration_ms = int((time.perf_counter() - start) * 1000)
            source.updated_at = _now()

    def _option_from_discovery(self, session: PurchaseSearchSession, title: str, url: str, rank: int, source_type: str, method: str) -> PurchaseItemOption:
        domain = _human_domain(url)
        return self._create_option(
            session=session,
            item=session.purchase_item,
            source_type=source_type,
            title=title,
            store_name=domain,
            seller_name=domain,
            unit_price=0,
            shipping_price=None,
            delivery_estimate=None,
            product_url=url,
            image_url=None,
            rank=rank,
            compatibility_score=0.5,
            confidence_score=0.35,
            evidence_level="discovered",
            captured_method=method,
            verification_status="DISCOVERED",
            verification_summary="Produto descoberto; preco e frete ainda precisam ser confirmados na fonte real.",
        )

    def _create_option(
        self,
        session: PurchaseSearchSession,
        item: PurchaseRequestItem,
        source_type: str,
        title: str,
        store_name: Optional[str],
        seller_name: Optional[str],
        unit_price: Any,
        shipping_price: Any,
        delivery_estimate: Optional[str],
        product_url: Optional[str],
        image_url: Optional[str],
        rank: int,
        compatibility_score: float,
        confidence_score: float,
        evidence_level: str,
        captured_method: str,
        verification_status: str,
        verification_summary: str,
        raw_metadata: Optional[Dict[str, Any]] = None,
        rating: Any = None,
        review_count: Any = None,
        brand: Optional[str] = None,
        model: Optional[str] = None,
        specifications: Optional[str] = None,
    ) -> PurchaseItemOption:
        unit = _money(unit_price)
        shipping = _money(shipping_price) if shipping_price is not None else None
        total = unit + (shipping or Decimal("0.00"))
        return PurchaseItemOption(
            purchase_item_id=item.id,
            source_type=source_type,
            store_name=store_name,
            seller_name=seller_name,
            title=title[:255],
            brand=brand,
            model=model,
            image_url=image_url,
            product_url=product_url,
            unit_price=float(unit),
            shipping_price=float(shipping) if shipping is not None else None,
            total_price=float(total),
            delivery_estimate=delivery_estimate,
            availability=True,
            rating=rating,
            review_count=review_count,
            specifications=specifications,
            captured_at=_now(),
            raw_source_metadata=raw_metadata or {},
            status="PENDING",
            selected=False,
            search_session_id=session.id,
            source_domain=_human_domain(product_url),
            source_rank=rank,
            compatibility_score=compatibility_score,
            confidence_score=confidence_score,
            evidence_level=evidence_level,
            shipping_destination=session.shipping_postal_code,
            captured_method=captured_method,
            verification_status=verification_status,
            verification_summary=verification_summary,
        )

    def _group_canonical_products(self, db: Session, session: PurchaseSearchSession) -> None:
        existing = {prod.normalized_key: prod for prod in session.canonical_products or []}
        for option in session.options or []:
            key = _normalize_key(option.title)
            canonical = existing.get(key)
            if not canonical:
                canonical = PurchaseCanonicalProduct(
                    search_session_id=session.id,
                    title=option.title,
                    brand=option.brand,
                    model=option.model,
                    normalized_key=key,
                    image_url=option.image_url,
                    compatibility_score=option.compatibility_score,
                    created_at=_now(),
                    updated_at=_now(),
                )
                db.add(canonical)
                db.flush()
                existing[key] = canonical
            option.canonical_product_id = canonical.id

    def _update_progress(self, db: Session, session: PurchaseSearchSession, progress: int, step: str) -> None:
        session.progress_percent = progress
        session.current_step = step
        session.updated_at = _now()
        db.commit()
        db.refresh(session)

    def _get_session_model(self, db: Session, session_id: uuid.UUID) -> PurchaseSearchSession:
        session = (
            db.query(PurchaseSearchSession)
            .options(
                joinedload(PurchaseSearchSession.purchase_item).joinedload(PurchaseRequestItem.purchase_request),
                joinedload(PurchaseSearchSession.tasks),
                joinedload(PurchaseSearchSession.sources),
                joinedload(PurchaseSearchSession.options),
                joinedload(PurchaseSearchSession.canonical_products).joinedload(PurchaseCanonicalProduct.options),
            )
            .filter(PurchaseSearchSession.id == session_id)
            .first()
        )
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pesquisa de compra nao encontrada.")
        return session

    def _session_payload(self, session: PurchaseSearchSession) -> Dict[str, Any]:
        return {
            "id": str(session.id),
            "purchase_request_id": str(session.purchase_request_id),
            "purchase_item_id": str(session.purchase_item_id),
            "query": session.query,
            "category": session.category,
            "status": session.status,
            "progress_percent": session.progress_percent,
            "current_step": session.current_step,
            "destination": session.destination,
            "shipping_postal_code": session.shipping_postal_code,
            "budget_limit": float(session.budget_limit) if session.budget_limit is not None else None,
            "planner_summary": session.planner_summary or {},
            "recommendation_summary": session.recommendation_summary or {},
            "missing_questions": session.missing_questions or [],
            "sources": [
                {
                    "id": str(src.id),
                    "source_label": src.source_label,
                    "status": src.status,
                    "result_count": src.result_count,
                    "error_message": src.error_message,
                    "duration_ms": src.duration_ms,
                }
                for src in sorted(session.sources or [], key=lambda s: s.created_at or _now())
            ],
            "tasks": [
                {
                    "id": str(task.id),
                    "title": task.title,
                    "status": task.status,
                    "criteria": task.criteria or {},
                    "result_summary": task.result_summary or {},
                }
                for task in session.tasks or []
            ],
            "canonical_products": [
                {
                    "id": str(prod.id),
                    "title": prod.title,
                    "name": prod.title,
                    "brand": prod.brand,
                    "model": prod.model,
                    "image_url": prod.image_url,
                    "compatibility_score": float(prod.compatibility_score or 0),
                    "offers": [self._option_payload(opt) for opt in prod.options or []],
                }
                for prod in session.canonical_products or []
            ],
            "options": [self._option_payload(opt) for opt in session.options or []],
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "updated_at": session.updated_at.isoformat() if session.updated_at else None,
        }

    def _option_payload(self, option: PurchaseItemOption) -> Dict[str, Any]:
        return {
            "id": str(option.id),
            "purchase_item_id": str(option.purchase_item_id),
            "source_type": option.source_type,
            "store_name": option.store_name,
            "seller_name": option.seller_name,
            "title": option.title,
            "brand": option.brand,
            "model": option.model,
            "image_url": option.image_url,
            "product_url": option.product_url,
            "unit_price": float(option.unit_price or 0),
            "shipping_price": float(option.shipping_price) if option.shipping_price is not None else None,
            "total_price": float(option.total_price or 0),
            "delivery_estimate": option.delivery_estimate,
            "availability": bool(option.availability),
            "rating": float(option.rating) if option.rating is not None else None,
            "review_count": option.review_count,
            "selected": option.selected,
            "source_domain": option.source_domain,
            "compatibility_score": float(option.compatibility_score or 0),
            "confidence_score": float(option.confidence_score or 0),
            "evidence_level": option.evidence_level,
            "verification_status": option.verification_status,
            "verification_summary": option.verification_summary,
            "invoice_available": option.invoice_available,
            "payment_summary": option.payment_summary,
            "warranty_summary": option.warranty_summary,
            "price_conditions": [
                {
                    "id": str(condition.id),
                    "condition_type": condition.condition_type,
                    "amount": float(condition.amount or 0),
                    "currency": condition.currency,
                    "installments": condition.installments,
                    "installment_amount": float(condition.installment_amount) if condition.installment_amount is not None else None,
                    "discount_percent": float(condition.discount_percent) if condition.discount_percent is not None else None,
                    "is_recommended": condition.is_recommended,
                    "source_label": condition.source_label,
                    "evidence_status": condition.evidence_status,
                    "captured_at": condition.captured_at.isoformat() if condition.captured_at else None,
                }
                for condition in getattr(option, "price_conditions", []) or []
            ],
        }

    def _emit_event(self, db: Session, event_type: str, session: PurchaseSearchSession, current_user: Optional[User]) -> None:
        try:
            emit_event(
                db=db,
                event_type=event_type,
                aggregate_type="purchase_search_session",
                aggregate_id=str(session.id),
                module="purchases",
                payload={
                    "session_id": str(session.id),
                    "purchase_request_id": str(session.purchase_request_id),
                    "purchase_item_id": str(session.purchase_item_id),
                    "status": session.status,
                    "progress_percent": session.progress_percent,
                    "action_url": f"/purchases?request={session.purchase_request_id}&item={session.purchase_item_id}",
                    "summary": f"Pesquisa de compra atualizada: {session.current_step}.",
                },
                actor_user_id=current_user.id if current_user else session.created_by_user_id,
            )
            db.commit()
        except Exception:
            db.rollback()


research_engine = PurchaseResearchEngine()
