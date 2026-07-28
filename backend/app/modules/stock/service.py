import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy import text, or_, and_, desc, func, case
from sqlalchemy.orm import Session, joinedload, selectinload, aliased
from app.models.stock import (
    StockCatalogImportRun,
    StockCatalogTreeNode,
    StockCatalogItem,
    StockCatalogItemSpec,
    StockCatalogSupplier,
    StockCatalogOffer,
    StockCatalogPriceHistory,
    StockCatalogCybersulProduct,
    StockCatalogLink,
    StockCatalogSearchIndex,
    StockCatalogReviewQueue,
    StockCatalogAlert
)
from app.models.user import User
from app.core.audit import log_action
from app.core.events import emit_event
from app.modules.stock.parser import ComprasNovaParser, _norm
from app.modules.stock.cybersul import CybersulImporter
from app.modules.stock.measure_utils import normalize_measure, strip_measurements_from_name

class StockCatalogService:
    TECHNICAL_CATEGORY_LABELS = {
        "",
        "outros",
        "outro",
        "nao usar",
        "nao-usar",
        "não usar",
        "não-usar",
        "ocultar",
        "x pecas",
        "x peças",
        "z produto final",
        "saneamento",
    }

    SEARCH_EXPANSIONS = {
        "parafuso": ["paraf", "paraf."],
        "paraf": ["parafuso"],
        "cabeca": ["cab"],
        "cab": ["cabeca"],
        "rodizio": ["rodizios"],
        "rodizios": ["rodizio"],
    }

    @staticmethod
    def _clean_text(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value
        for _ in range(2):
            if "Ã" not in cleaned and "Â" not in cleaned:
                break
            try:
                fixed = cleaned.encode("latin1").decode("utf-8")
            except (UnicodeEncodeError, UnicodeDecodeError):
                break
            if fixed == cleaned:
                break
            cleaned = fixed
        return cleaned.replace("\u00a0", " ").strip()

    @staticmethod
    def _clean_response(value: Any) -> Any:
        if isinstance(value, str):
            return StockCatalogService._clean_text(value)
        if isinstance(value, list):
            return [StockCatalogService._clean_response(item) for item in value]
        if isinstance(value, dict):
            return {key: StockCatalogService._clean_response(item) for key, item in value.items()}
        return value

    @staticmethod
    def _expanded_search_queries(normalized_q: str) -> List[str]:
        queries = {normalized_q}
        tokens = normalized_q.split()
        for idx, token in enumerate(tokens):
            for replacement in StockCatalogService.SEARCH_EXPANSIONS.get(token, []):
                expanded = list(tokens)
                expanded[idx] = _norm(replacement)
                queries.add(" ".join(expanded))
        if "parafuso" in tokens and "allen" in tokens:
            queries.add(normalized_q.replace("parafuso", "paraf"))
        if "paraf" in tokens and "allen" in tokens:
            queries.add(normalized_q.replace("paraf", "parafuso"))
        return [query for query in queries if query]

    @staticmethod
    def _is_admin_or_messias(current_user: Optional[Any]) -> bool:
        if not current_user:
            return False
        return (
            current_user.role and current_user.role.name in {"ADMIN", "MESSIAS"}
        )

    @staticmethod
    def _apply_common_catalog_filters(query, include_review: bool = False):
        query = query.filter(
            StockCatalogItem.active == True,
            or_(StockCatalogItem.is_parser_junk == False, StockCatalogItem.is_parser_junk.is_(None))
        )
        if include_review:
            return query
        return query.filter(
            or_(StockCatalogItem.visibility_scope == "COMMON", StockCatalogItem.visibility_scope.is_(None)),
            or_(StockCatalogItem.is_searchable_common == True, StockCatalogItem.is_searchable_common.is_(None)),
            or_(StockCatalogItem.quality_status.is_(None), StockCatalogItem.quality_status.notin_(["INACTIVE", "QUARANTINED", "HIDDEN"]))
        )

    @staticmethod
    def _is_meaningful_catalog_label(value: Optional[str]) -> bool:
        if not value:
            return False
        normalized = _norm(value)
        return normalized not in StockCatalogService.TECHNICAL_CATEGORY_LABELS

    @staticmethod
    def _human_catalog_label(value: Optional[str]) -> str:
        from app.modules.stock.unified_importer import normalize_category_title

        label = normalize_category_title(StockCatalogService._clean_text(value) or "").strip()
        return label if StockCatalogService._is_meaningful_catalog_label(label) else ""

    @staticmethod
    def _catalog_root_label_for_item(item: StockCatalogItem) -> str:
        candidates = [
            item.source_sheet,
            item.canonical_category_display,
            item.cybersul_product.group_name if item.cybersul_product else None,
            item.canonical_category,
        ]
        for candidate in candidates:
            label = StockCatalogService._human_catalog_label(candidate)
            if label:
                return label
        return "Outros"

    @staticmethod
    def _catalog_source_candidates_for_label(db: Session, label: str) -> Dict[str, List[str]]:
        """
        Resolve o nome humano exibido na arvore para os valores originais salvos no banco.
        Isso evita que clicar em "Rodas e Rodizios" deixe de encontrar itens cujo dado bruto
        ainda esteja como "02.9 RODAS E RODIZIOS".
        """
        target = _norm(label)
        candidates = {"source_sheet": [], "canonical_category_display": [], "canonical_category": []}
        rows = db.query(
            StockCatalogItem.source_sheet,
            StockCatalogItem.canonical_category_display,
            StockCatalogItem.canonical_category,
        ).distinct().all()

        for source_sheet, canonical_display, canonical_category in rows:
            values = {
                "source_sheet": source_sheet,
                "canonical_category_display": canonical_display,
                "canonical_category": canonical_category,
            }
            for key, value in values.items():
                if value and _norm(StockCatalogService._human_catalog_label(value) or value) == target:
                    candidates[key].append(value)

        return candidates

    @staticmethod
    def _item_to_public_dict(item: StockCatalogItem, current_offer: Optional[StockCatalogOffer] = None) -> Dict[str, Any]:
        if current_offer is None:
            current_offers = [offer for offer in item.offers if offer.is_current]
            priced_offers = [offer for offer in current_offers if offer.price and float(offer.price) > 0]
            current_offer = (priced_offers or current_offers or [None])[0]

        family_path = StockCatalogService._catalog_root_label_for_item(item)
        if item.family_node:
            family_title = StockCatalogService._human_catalog_label(item.family_node.title) or item.family_node.title
            family_path += f" > {family_title}"
        if item.product_node and (not item.family_node or item.product_node.title != item.family_node.title):
            product_title = StockCatalogService._human_catalog_label(item.product_node.title) or item.product_node.title
            family_path += f" > {product_title}"

        current_offers_count = len([offer for offer in item.offers if offer.is_current])
        primary_price = float(current_offer.price) if current_offer and current_offer.price else None
        primary_supplier = current_offer.supplier.name if current_offer else None
        normalized_measure = normalize_measure(item.variation_label, item.normalized_measure, item.specification_text)
        measure_display = normalized_measure.display or item.measure_display or item.normalized_measure
        measure_kind = normalized_measure.kind if normalized_measure.canonical_key else (item.measure_kind or ("complete" if item.normalized_measure else "none"))

        return StockCatalogService._clean_response({
            "id": str(item.id),
            "display_name": item.display_name,
            "base_name": item.base_name,
            "variation_label": item.variation_label,
            "normalized_measure": item.normalized_measure,
            "measure_display": measure_display,
            "measure_kind": measure_kind,
            "specification_text": item.specification_text,
            "internal_code": item.internal_code,
            "quality_status": item.quality_status,
            "needs_review": item.needs_review,
            "review_reason": item.review_reason,
            "family_path": family_path,
            "source_sheet": item.source_sheet,
            "cybersul_code": item.cybersul_product.cybersul_code if item.cybersul_product else item.internal_code,
            "cybersul_description": item.cybersul_product.description if item.cybersul_product else None,
            "balance_total": float(item.cybersul_product.balance_total) if item.cybersul_product else 0.0,
            "last_price": primary_price,
            "last_supplier": primary_supplier,
            "primary_price": primary_price,
            "primary_supplier": primary_supplier,
            "offer_count": current_offers_count,
            "has_price": primary_price is not None,
            "unit": current_offer.unit if current_offer else (item.cybersul_product.unit if item.cybersul_product else "un"),
            "_canonical_measure_key": normalized_measure.canonical_key,
        })

    @staticmethod
    def _deduplicate_public_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        grouped: Dict[str, Dict[str, Any]] = {}
        order: List[str] = []

        def score(item: Dict[str, Any]) -> tuple[int, int, int]:
            return (
                1 if item.get("cybersul_code") else 0,
                1 if item.get("primary_price") or item.get("last_price") else 0,
                int(item.get("offer_count") or 0),
            )

        for item in items:
            measure_key = item.get("_canonical_measure_key")
            if not measure_key or item.get("measure_kind") != "complete":
                key = f"raw:{item.get('id')}"
            else:
                base_or_display = item.get("base_name") or item.get("display_name") or ""
                stripped_base = strip_measurements_from_name(base_or_display)
                key = "|".join([
                    _norm(item.get("family_path") or item.get("source_sheet") or ""),
                    _norm(stripped_base),
                    measure_key,
                ])

            if key not in grouped:
                grouped[key] = item
                order.append(key)
                continue

            current = grouped[key]
            current_offers = int(current.get("offer_count") or 0)
            item_offers = int(item.get("offer_count") or 0)
            chosen = item if score(item) > score(current) else current
            other = current if chosen is item else item

            chosen["offer_count"] = max(1, current_offers + item_offers)
            chosen["has_price"] = bool(chosen.get("has_price") or other.get("has_price"))
            if not chosen.get("primary_supplier") and other.get("primary_supplier"):
                chosen["primary_supplier"] = other.get("primary_supplier")
                chosen["last_supplier"] = other.get("last_supplier")
            if not chosen.get("primary_price") and other.get("primary_price"):
                chosen["primary_price"] = other.get("primary_price")
                chosen["last_price"] = other.get("last_price")
            if not chosen.get("cybersul_code") and other.get("cybersul_code"):
                chosen["cybersul_code"] = other.get("cybersul_code")
                chosen["internal_code"] = other.get("internal_code")

            grouped[key] = chosen

        result = []
        for key in order:
            item = dict(grouped[key])
            item.pop("_canonical_measure_key", None)
            result.append(item)
        return result

    @staticmethod
    def _refresh_measure_fields(item: StockCatalogItem) -> None:
        normalized = normalize_measure(item.variation_label, item.normalized_measure, item.specification_text)
        if not normalized.canonical_key:
            return
        item.canonical_measure_key = normalized.canonical_key
        item.measure_display = normalized.display
        item.measure_kind = normalized.kind
        item.measure_aliases_json = normalized.aliases

    @staticmethod
    def get_summary(db: Session) -> Dict[str, Any]:
        """
        Retorna os KPIs e resumo do módulo de Estoque & Catálogo.
        """
        common_items_query = StockCatalogService._apply_common_catalog_filters(db.query(StockCatalogItem))
        total_items = common_items_query.count() or 0
        total_suppliers = db.query(func.count(StockCatalogSupplier.id)).filter(StockCatalogSupplier.active == True).scalar() or 0
        total_offers = db.query(func.count(StockCatalogOffer.id)).join(StockCatalogItem).filter(
            StockCatalogOffer.is_current == True,
            StockCatalogOffer.price.is_not(None),
            StockCatalogOffer.price > 0,
            StockCatalogItem.active == True,
            StockCatalogItem.visibility_scope == "COMMON"
        ).scalar() or 0
        
        items_without_cybersul = db.query(func.count(StockCatalogItem.id)).filter(
            StockCatalogItem.active == True,
            StockCatalogItem.cybersul_product_id.is_(None)
        ).scalar() or 0
        
        items_in_review = db.query(func.count(StockCatalogReviewQueue.id)).filter(
            StockCatalogReviewQueue.status == "PENDING"
        ).scalar() or 0
        
        # Estoque baixo baseado no saldo do Cybersul vinculado (ex: total_balance <= 5.0)
        low_stock_items = db.query(func.count(StockCatalogItem.id)).join(
            StockCatalogCybersulProduct, StockCatalogItem.cybersul_product_id == StockCatalogCybersulProduct.id
        ).filter(
            StockCatalogItem.active == True,
            StockCatalogItem.visibility_scope == "COMMON",
            StockCatalogCybersulProduct.balance_total <= 5.0
        ).scalar() or 0
        
        last_run = db.query(StockCatalogImportRun).filter(
            StockCatalogImportRun.status == "SUCCESS"
        ).order_by(desc(StockCatalogImportRun.finished_at)).first()

        # Novos KPIs positivos filtrados
        total_operational_items = total_items

        total_with_supplier = db.query(func.count(func.distinct(StockCatalogItem.id))).join(
            StockCatalogOffer, StockCatalogOffer.item_id == StockCatalogItem.id
        ).filter(
            StockCatalogItem.active == True,
            StockCatalogItem.visibility_scope == "COMMON",
            StockCatalogOffer.is_current == True,
            StockCatalogOffer.supplier_id.is_not(None)
        ).scalar() or 0

        total_with_price = db.query(func.count(func.distinct(StockCatalogItem.id))).join(
            StockCatalogOffer, StockCatalogOffer.item_id == StockCatalogItem.id
        ).filter(
            StockCatalogItem.active == True,
            StockCatalogItem.visibility_scope == "COMMON",
            StockCatalogOffer.is_current == True,
            StockCatalogOffer.price.is_not(None),
            StockCatalogOffer.price > 0
        ).scalar() or 0
        
        return {
            "total_items": total_items,
            "total_suppliers": total_suppliers,
            "total_offers": total_offers,
            "items_without_cybersul_code": items_without_cybersul,
            "items_in_review": items_in_review,
            "low_stock_items": low_stock_items,
            "last_import_at": last_run.finished_at if last_run else None,
            "total_operational_items": total_operational_items,
            "total_with_supplier": total_with_supplier,
            "total_with_price": total_with_price
        }

    @staticmethod
    def import_compras_nova(filepath: str, db: Session, user_id: Optional[int] = None) -> Dict[str, Any]:
        run = ComprasNovaParser.parse_workbook(filepath, db, user_id)
        return {
            "status": run.status,
            "run_id": str(run.id),
            "total_rows": run.total_rows,
            "total_items": run.total_items,
            "total_offers": run.total_offers,
            "total_errors": run.total_errors,
            "total_review": run.total_review,
            "error_message": run.error_message
        }

    @staticmethod
    def import_cybersul(filepath: str, db: Session, user_id: Optional[int] = None) -> Dict[str, Any]:
        run = CybersulImporter.import_products(filepath, db, user_id)
        return {
            "status": run.status,
            "run_id": str(run.id),
            "total_rows": run.total_rows,
            "total_items": run.total_items,
            "total_links_created": run.total_offers,
            "error_message": run.error_message
        }

    @staticmethod
    def import_unified(filepath: str, db: Session, user_id: Optional[int] = None) -> Dict[str, Any]:
        from app.modules.stock.unified_importer import StockCatalogUnifiedImporter
        run = StockCatalogUnifiedImporter.import_unified(filepath, db, user_id)
        return {
            "status": run.status,
            "run_id": str(run.id),
            "total_rows": run.total_rows,
            "total_items": run.total_items,
            "total_offers": run.total_offers,
            "total_errors": run.total_errors,
            "total_review": run.total_review,
            "error_message": run.error_message
        }

    @staticmethod
    def get_import_runs(db: Session) -> List[StockCatalogImportRun]:
        return db.query(StockCatalogImportRun).order_by(desc(StockCatalogImportRun.started_at)).all()

    @staticmethod
    def get_tree(db: Session, sheet_filter: Optional[str] = None, current_user: Optional[Any] = None) -> List[Dict[str, Any]]:
        """
        Retorna a estrutura hierárquica comercial simplificada e agrupada da árvore (Sheet -> Family -> Product)
        com contagens e campos adicionais exigidos pelo novo contrato de UX.
        """
        from app.modules.stock.unified_importer import normalize_category_title

        is_admin = StockCatalogService._is_admin_or_messias(current_user)

        # Sempre retorna a árvore limpa, curta, deduplicada, usando categorias canônicas
        query = db.query(StockCatalogItem).options(
            joinedload(StockCatalogItem.family_node),
            joinedload(StockCatalogItem.product_node),
            joinedload(StockCatalogItem.cybersul_product),
        )
        
        query = StockCatalogService._apply_common_catalog_filters(query, include_review=is_admin)
            
        op_items = query.all()
        
        # Busca os IDs dos itens que possuem ofertas ativas e precificadas para evitar lazy loading
        priced_rows = db.query(StockCatalogOffer.item_id).filter(
            StockCatalogOffer.price != None,
            StockCatalogOffer.price > 0
        ).all()
        priced_item_ids = {r[0] for r in priced_rows}

        # Busca os IDs dos itens com estoque baixo (balance_total <= 5.0) para evitar lazy loading do cybersul_product
        low_stock_rows = db.query(StockCatalogItem.id).join(
            StockCatalogCybersulProduct,
            StockCatalogItem.cybersul_product_id == StockCatalogCybersulProduct.id
        ).filter(
            StockCatalogCybersulProduct.balance_total <= 5.0
        ).all()
        low_stock_item_ids = {r[0] for r in low_stock_rows}
        
        tree_data = {}

        for item in op_items:
            if not is_admin and item.is_tree_visible_common is False:
                continue

            cat_display = StockCatalogService._catalog_root_label_for_item(item)
            if cat_display != "Outros" and not StockCatalogService._is_meaningful_catalog_label(cat_display):
                continue
            if not item.family_node or not item.product_node:
                continue
                
            fam_title = StockCatalogService._human_catalog_label(item.family_node.title) or normalize_category_title(item.family_node.title)
            prod_title = StockCatalogService._human_catalog_label(item.product_node.title) or normalize_category_title(item.product_node.title)

            from app.modules.stock.measure_utils import is_invalid_product_name
            if is_invalid_product_name(item.product_node.title):
                continue
            
            if not fam_title or not prod_title:
                continue
                
            if cat_display not in tree_data:
                tree_data[cat_display] = {}
            if fam_title not in tree_data[cat_display]:
                tree_data[cat_display][fam_title] = {}
            if prod_title not in tree_data[cat_display][fam_title]:
                tree_data[cat_display][fam_title][prod_title] = {
                    "family_node_id": str(item.family_node_id),
                    "product_node_id": str(item.product_node_id),
                    "sheet": cat_display,
                    "path": f"{cat_display} > {fam_title} > {prod_title}",
                    "items": []
                }
            tree_data[cat_display][fam_title][prod_title]["items"].append(item)
        
        root_nodes = []
        for cat_title, families in sorted(tree_data.items()):
            count_families = len(families)
            count_products = 0
            count_variations = 0
            count_priced = 0
            count_low_stock = 0
            
            cat_id = f"cat-{_norm(cat_title).replace(' ', '-')}"
            
            cat_children = []
            for fam_title, products in sorted(families.items()):
                fam_products_count = len(products)
                fam_variations_count = 0
                fam_priced_count = 0
                fam_low_stock_count = 0
                
                first_prod = list(products.values())[0]
                fam_id = first_prod["family_node_id"]
                
                fam_children = []
                for prod_title, prod_info in sorted(products.items()):
                    items = prod_info["items"]
                    prod_variations_count = len(items)
                    prod_priced_count = sum(1 for x in items if x.id in priced_item_ids)
                    prod_low_stock_count = sum(1 for x in items if x.id in low_stock_item_ids)
                    
                    prod_id = prod_info["product_node_id"]
                    
                    prod_node = {
                        "id": prod_id,
                        "title": prod_title,
                        "label": prod_title,
                        "display_label": prod_title,
                        "node_type": "product",
                        "kind": "product",
                        "sheet": cat_title,
                        "path": prod_info["path"],
                        "count_families": 0,
                        "count_products": 0,
                        "count_variations": prod_variations_count,
                        "count_priced": prod_priced_count,
                        "count_low_stock": prod_low_stock_count,
                        "has_children": False,
                        "parent_id": fam_id,
                        "breadcrumb": f"{cat_title} > {fam_title} > {prod_title}",
                        "hidden_for_common_user": False,
                        "admin_only_reason": None,
                        "children": []
                    }
                    fam_children.append(prod_node)
                    
                    fam_variations_count += prod_variations_count
                    fam_priced_count += prod_priced_count
                    fam_low_stock_count += prod_low_stock_count
                
                fam_node = {
                    "id": fam_id,
                    "title": fam_title,
                    "label": fam_title,
                    "display_label": fam_title,
                    "node_type": "family",
                    "kind": "family",
                    "sheet": cat_title,
                    "path": f"{cat_title} > {fam_title}",
                    "count_families": 0,
                    "count_products": fam_products_count,
                    "count_variations": fam_variations_count,
                    "count_priced": fam_priced_count,
                    "count_low_stock": fam_low_stock_count,
                    "has_children": len(fam_children) > 0,
                    "parent_id": cat_id,
                    "breadcrumb": f"{cat_title} > {fam_title}",
                    "hidden_for_common_user": False,
                    "admin_only_reason": None,
                    "children": fam_children
                }
                cat_children.append(fam_node)
                
                count_products += fam_products_count
                count_variations += fam_variations_count
                count_priced += fam_priced_count
                count_low_stock += fam_low_stock_count
            
            cat_node = {
                "id": cat_id,
                "title": cat_title,
                "label": cat_title,
                "display_label": cat_title,
                "node_type": "sheet",
                "kind": "sheet",
                "sheet": cat_title,
                "path": cat_title,
                "count_families": count_families,
                "count_products": count_products,
                "count_variations": count_variations,
                "count_priced": count_priced,
                "count_low_stock": count_low_stock,
                "has_children": len(cat_children) > 0,
                "parent_id": None,
                "breadcrumb": cat_title,
                "hidden_for_common_user": False,
                "admin_only_reason": None,
                "children": cat_children
            }
            root_nodes.append(cat_node)
            
        if sheet_filter:
            root_nodes = [node for node in root_nodes if _norm(node["sheet"]) == _norm(sheet_filter)]
            
        return StockCatalogService._clean_response(root_nodes)

    @staticmethod
    def get_navigation_categories(db: Session, current_user: Optional[Any] = None) -> List[Dict[str, Any]]:
        is_admin = StockCatalogService._is_admin_or_messias(current_user)
        priced_items = (
            db.query(StockCatalogOffer.item_id)
            .filter(StockCatalogOffer.price != None, StockCatalogOffer.price > 0)
            .distinct()
            .subquery()
        )

        query = db.query(
            StockCatalogItem.source_sheet,
            StockCatalogItem.canonical_category_display,
            StockCatalogItem.canonical_category,
            func.count(func.distinct(StockCatalogItem.family_node_id)).label("families"),
            func.count(func.distinct(StockCatalogItem.product_node_id)).label("products"),
            func.count(func.distinct(StockCatalogItem.id)).label("variations"),
            func.count(func.distinct(priced_items.c.item_id)).label("priced"),
        ).outerjoin(priced_items, priced_items.c.item_id == StockCatalogItem.id)

        query = StockCatalogService._apply_common_catalog_filters(query, include_review=is_admin)
        if not is_admin:
            query = query.filter(or_(StockCatalogItem.is_tree_visible_common == True, StockCatalogItem.is_tree_visible_common.is_(None)))
        rows = (
            query
            .filter(StockCatalogItem.family_node_id.isnot(None), StockCatalogItem.product_node_id.isnot(None))
            .group_by(
                StockCatalogItem.source_sheet,
                StockCatalogItem.canonical_category_display,
                StockCatalogItem.canonical_category,
            )
            .all()
        )

        categories: Dict[str, Dict[str, Any]] = {}
        for source_sheet, canonical_display, canonical_category, families, products, variations, priced in rows:
            label = (
                StockCatalogService._human_catalog_label(source_sheet)
                or StockCatalogService._human_catalog_label(canonical_display)
                or StockCatalogService._human_catalog_label(canonical_category)
                or "Outros"
            )
            if label != "Outros" and not StockCatalogService._is_meaningful_catalog_label(label):
                continue
            key = _norm(label)
            node = categories.setdefault(key, {
                "id": f"cat-{key.replace(' ', '-')}",
                "title": label,
                "label": label,
                "display_label": label,
                "node_type": "sheet",
                "kind": "sheet",
                "sheet": label,
                "path": label,
                "count_families": 0,
                "count_products": 0,
                "count_variations": 0,
                "count_priced": 0,
                "count_low_stock": 0,
                "has_children": True,
                "parent_id": None,
                "breadcrumb": label,
                "hidden_for_common_user": False,
                "admin_only_reason": None,
                "children": [],
            })
            node["count_families"] += int(families or 0)
            node["count_products"] += int(products or 0)
            node["count_variations"] += int(variations or 0)
            node["count_priced"] += int(priced or 0)

        return StockCatalogService._clean_response(sorted(categories.values(), key=lambda item: item["display_label"]))

    @staticmethod
    def get_navigation_families(db: Session, category: str, current_user: Optional[Any] = None) -> List[Dict[str, Any]]:
        is_admin = StockCatalogService._is_admin_or_messias(current_user)
        FamilyNode = aliased(StockCatalogTreeNode)
        ProductNode = aliased(StockCatalogTreeNode)
        priced_items = (
            db.query(StockCatalogOffer.item_id)
            .filter(StockCatalogOffer.price != None, StockCatalogOffer.price > 0)
            .distinct()
            .subquery()
        )
        low_stock_items = (
            db.query(StockCatalogItem.id)
            .join(StockCatalogCybersulProduct, StockCatalogItem.cybersul_product_id == StockCatalogCybersulProduct.id)
            .filter(StockCatalogCybersulProduct.balance_total <= 5.0)
            .distinct()
            .subquery()
        )

        query = (
            db.query(
                FamilyNode.id.label("family_id"),
                FamilyNode.title.label("family_title"),
                ProductNode.id.label("product_id"),
                ProductNode.title.label("product_title"),
                func.count(func.distinct(StockCatalogItem.id)).label("variations"),
                func.count(func.distinct(priced_items.c.item_id)).label("priced"),
                func.count(func.distinct(low_stock_items.c.id)).label("low_stock"),
            )
            .join(FamilyNode, StockCatalogItem.family_node_id == FamilyNode.id)
            .join(ProductNode, StockCatalogItem.product_node_id == ProductNode.id)
            .outerjoin(priced_items, priced_items.c.item_id == StockCatalogItem.id)
            .outerjoin(low_stock_items, low_stock_items.c.id == StockCatalogItem.id)
        )
        query = StockCatalogService._apply_common_catalog_filters(query, include_review=is_admin)
        if not is_admin:
            query = query.filter(or_(StockCatalogItem.is_tree_visible_common == True, StockCatalogItem.is_tree_visible_common.is_(None)))

        sheet_candidates = StockCatalogService._catalog_source_candidates_for_label(db, category)
        sheet_filters = [
            StockCatalogItem.canonical_category_display == category,
            StockCatalogItem.source_sheet == category,
            StockCatalogItem.canonical_category == category,
        ]
        if sheet_candidates["source_sheet"]:
            sheet_filters.append(StockCatalogItem.source_sheet.in_(sheet_candidates["source_sheet"]))
        if sheet_candidates["canonical_category_display"]:
            sheet_filters.append(StockCatalogItem.canonical_category_display.in_(sheet_candidates["canonical_category_display"]))
        if sheet_candidates["canonical_category"]:
            sheet_filters.append(StockCatalogItem.canonical_category.in_(sheet_candidates["canonical_category"]))

        rows = (
            query
            .filter(or_(*sheet_filters))
            .group_by(FamilyNode.id, FamilyNode.title, ProductNode.id, ProductNode.title)
            .order_by(FamilyNode.title, ProductNode.title)
            .all()
        )

        families: Dict[str, Dict[str, Any]] = {}
        for family_id, family_title, product_id, product_title, variations, priced, low_stock in rows:
            fam_title = StockCatalogService._human_catalog_label(family_title)
            prod_title = StockCatalogService._human_catalog_label(product_title)
            if not fam_title or not prod_title:
                continue
            from app.modules.stock.measure_utils import is_invalid_product_name
            if is_invalid_product_name(product_title):
                continue

            family = families.setdefault(str(family_id), {
                "id": str(family_id),
                "title": fam_title,
                "label": fam_title,
                "display_label": fam_title,
                "node_type": "family",
                "kind": "family",
                "sheet": category,
                "path": f"{category} > {fam_title}",
                "count_families": 0,
                "count_products": 0,
                "count_variations": 0,
                "count_priced": 0,
                "count_low_stock": 0,
                "has_children": True,
                "parent_id": f"cat-{_norm(category).replace(' ', '-')}",
                "breadcrumb": f"{category} > {fam_title}",
                "hidden_for_common_user": False,
                "admin_only_reason": None,
                "children": [],
            })
            product_node = {
                "id": str(product_id),
                "title": prod_title,
                "label": prod_title,
                "display_label": prod_title,
                "node_type": "product",
                "kind": "product",
                "sheet": category,
                "path": f"{category} > {fam_title} > {prod_title}",
                "count_families": 0,
                "count_products": 0,
                "count_variations": int(variations or 0),
                "count_priced": int(priced or 0),
                "count_low_stock": int(low_stock or 0),
                "has_children": False,
                "parent_id": str(family_id),
                "breadcrumb": f"{category} > {fam_title} > {prod_title}",
                "hidden_for_common_user": False,
                "admin_only_reason": None,
                "children": [],
            }
            family["children"].append(product_node)
            family["count_products"] += 1
            family["count_variations"] += product_node["count_variations"]
            family["count_priced"] += product_node["count_priced"]
            family["count_low_stock"] += product_node["count_low_stock"]

        return StockCatalogService._clean_response(list(families.values()))

    @staticmethod
    def get_navigation_products(db: Session, family_id: uuid.UUID, current_user: Optional[Any] = None) -> List[Dict[str, Any]]:
        for category in StockCatalogService.get_tree(db, current_user=current_user):
            for family in category.get("children", []):
                if str(family.get("id")) == str(family_id):
                    return [
                        {
                            **{key: value for key, value in product.items() if key != "children"},
                            "has_children": bool(product.get("children")),
                        }
                        for product in family.get("children", [])
                    ]
        return []

    @staticmethod
    def _legacy_search_catalog(
        db: Session,
        query_str: str,
        current_user: Optional[Any] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Busca rápida tolerante a erros no PostgreSQL usando pg_trgm ou fallback de ILIKE tokens,
        reordenada no Python com relevância por correspondência exata de termos e medidas.
        """
        import re
        normalized_q = _norm(query_str)
        if not normalized_q:
            return []

        is_admin = StockCatalogService._is_admin_or_messias(current_user)
        limit = max(1, min(limit, 100))

        # Determinar dialeto
        try:
            is_postgres = db.get_bind().dialect.name == "postgresql"
        except Exception:
            is_postgres = False

        scores_map = {}
        if is_postgres:
            # PostgreSQL: Busca avançada combinando similaridade por trigrama e ILIKE
            sql_query = text("""
                SELECT item_id, similarity(normalized_search_text, :q) as score
                FROM stock_catalog_search_index
                WHERE normalized_search_text % :q OR normalized_search_text ILIKE :ilike_q
                ORDER BY score DESC, updated_at DESC
                LIMIT :limit
            """)
            results = db.execute(sql_query, {"q": normalized_q, "ilike_q": f"%{normalized_q}%", "limit": limit}).fetchall()
            item_ids = [row[0] for row in results]
            scores_map = {str(row[0]): float(row[1]) for row in results}
        else:
            # Fallback SQLite
            full_match = db.query(StockCatalogSearchIndex).filter(
                StockCatalogSearchIndex.normalized_search_text.like(f"%{normalized_q}%")
            ).limit(limit).all()
            
            if full_match:
                item_ids = [row.item_id for row in full_match]
            else:
                tokens = [f"%{t}%" for t in normalized_q.split() if len(t) > 1]
                if not tokens:
                    return []
                
                filters = []
                for token in tokens:
                    filters.append(StockCatalogSearchIndex.normalized_search_text.like(token))
                
                search_rows = db.query(StockCatalogSearchIndex).filter(and_(*filters)).limit(limit).all()
                item_ids = [row.item_id for row in search_rows]
                
                if not item_ids:
                    or_filters = []
                    for token in tokens:
                        or_filters.append(StockCatalogSearchIndex.normalized_search_text.like(token))
                    
                    if or_filters:
                        search_rows = db.query(StockCatalogSearchIndex).filter(or_(*or_filters)).limit(limit).all()
                        item_ids = [row.item_id for row in search_rows]
            scores_map = {str(iid): 0.5 for iid in item_ids}

        if not item_ids:
            return []

        # Obter os itens com carregamento otimizado de relações
        query = db.query(StockCatalogItem).options(
            joinedload(StockCatalogItem.cybersul_product),
            joinedload(StockCatalogItem.specs),
            joinedload(StockCatalogItem.offers).joinedload(StockCatalogOffer.supplier)
        ).filter(StockCatalogItem.id.in_(item_ids))

        query = StockCatalogService._apply_common_catalog_filters(query, include_review=is_admin)

        items = query.all()

        # Ordenar e refinar relevância no Python
        items_map = {item.id: item for item in items}
        sorted_items = []
        
        query_tokens = [t for t in normalized_q.split() if len(t) > 0]
        
        for item_id in item_ids:
            if item_id in items_map:
                item = items_map[item_id]
                
                # Buscar caminho de árvore
                family_path = ""
                search_idx = db.query(StockCatalogSearchIndex).filter(StockCatalogSearchIndex.item_id == item.id).first()
                if search_idx:
                    family_path = f"{search_idx.source_sheet} > {search_idx.family_path}"

                # Encontrar a oferta atual principal
                current_offer = None
                for offer in item.offers:
                    if offer.is_current:
                        current_offer = offer
                        break

                display_norm = _norm(item.display_name)
                base_score = scores_map.get(str(item.id), 0.5)

                # 1. Correspondência exata da query no display name
                if normalized_q in display_norm:
                    base_score += 3.0
                
                # 2. Correspondência exata de tokens individuais
                match_count = 0
                for token in query_tokens:
                    if token in display_norm:
                        match_count += 1
                
                if len(query_tokens) > 0:
                    if match_count == len(query_tokens):
                        base_score += 1.5
                    else:
                        base_score += (match_count / len(query_tokens)) * 0.8

                # 3. Priorização rigorosa de medidas numéricas (ex: "1 mm" ou "304 L")
                measure_matches = re.findall(r'\b\d+(?:[.,]\d+)?\s*(?:mm|m|kg|g|"\b)', normalized_q)
                for m_match in measure_matches:
                    if m_match in display_norm:
                        base_score += 2.0
                    else:
                        # Se o usuário digitou uma medida que esse item não tem, reduz relevância drasticamente
                        base_score -= 1.5

                sorted_items.append({
                    **StockCatalogService._item_to_public_dict(item, current_offer),
                    "family_path": family_path,
                    "_score": base_score
                })

        # Reordenar com base no score final refinado
        sorted_items.sort(key=lambda x: x["_score"], reverse=True)
        
        # Remover o campo interno _score antes de retornar
        for sit in sorted_items:
            sit.pop("_score", None)
            
        return sorted_items[:limit]

    @staticmethod
    def search_catalog(
        db: Session,
        query_str: str,
        current_user: Optional[Any] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        import re

        normalized_q = _norm(query_str)
        if not normalized_q:
            return []

        is_admin = StockCatalogService._is_admin_or_messias(current_user)
        limit = max(1, min(limit, 100))
        scores_map: Dict[str, float] = {}
        item_ids = []
        seen_ids = set()
        expanded_queries = StockCatalogService._expanded_search_queries(normalized_q)
        search_limit = max(limit * 8, 80)

        def add_rows(rows, score: float):
            for row in rows:
                key = str(row.item_id)
                scores_map[key] = max(scores_map.get(key, 0.0), score)
                if key in seen_ids:
                    continue
                seen_ids.add(key)
                item_ids.append(row.item_id)

        for q_variant in expanded_queries:
            add_rows(
                db.query(StockCatalogSearchIndex)
                .filter(StockCatalogSearchIndex.normalized_search_text.like(f"%{q_variant}%"))
                .order_by(desc(StockCatalogSearchIndex.updated_at))
                .limit(search_limit)
                .all(),
                3.0 if q_variant == normalized_q else 2.4,
            )

        if len(item_ids) < limit:
            for q_variant in expanded_queries:
                token_filters = [
                    StockCatalogSearchIndex.normalized_search_text.like(f"%{token}%")
                    for token in q_variant.split()
                    if len(token) > 1
                ]
                if token_filters:
                    add_rows(
                        db.query(StockCatalogSearchIndex)
                        .filter(and_(*token_filters))
                        .order_by(desc(StockCatalogSearchIndex.updated_at))
                        .limit(search_limit)
                        .all(),
                        1.8 if q_variant == normalized_q else 1.4,
                    )

        if len(item_ids) < limit:
            token_filters = [
                StockCatalogSearchIndex.normalized_search_text.like(f"%{token}%")
                for token in normalized_q.split()
                if len(token) > 2
            ]
            if token_filters:
                add_rows(
                    db.query(StockCatalogSearchIndex)
                    .filter(or_(*token_filters))
                    .order_by(desc(StockCatalogSearchIndex.updated_at))
                    .limit(search_limit)
                    .all(),
                    0.6,
                )

        if not item_ids:
            return []

        query = db.query(StockCatalogItem).options(
            joinedload(StockCatalogItem.cybersul_product),
            joinedload(StockCatalogItem.specs),
            joinedload(StockCatalogItem.offers).joinedload(StockCatalogOffer.supplier)
        ).filter(StockCatalogItem.id.in_(item_ids))

        query = StockCatalogService._apply_common_catalog_filters(query, include_review=is_admin)
        items = query.all()
        items_map = {item.id: item for item in items}
        query_tokens = [token for token in normalized_q.split() if token]
        sorted_items = []

        for item_id in item_ids:
            if item_id not in items_map:
                continue

            item = items_map[item_id]
            search_idx = db.query(StockCatalogSearchIndex).filter(StockCatalogSearchIndex.item_id == item.id).first()
            family_path = StockCatalogService._item_to_public_dict(item).get("family_path", "")
            current_offer = next((offer for offer in item.offers if offer.is_current), None)
            display_norm = _norm(" ".join([
                item.display_name or "",
                item.base_name or "",
                item.variation_label or "",
                item.measure_display or "",
                " ".join(item.measure_aliases_json or []),
                item.specification_text or "",
                search_idx.normalized_search_text if search_idx else "",
            ]))

            base_score = scores_map.get(str(item.id), 0.5)
            if normalized_q in display_norm:
                base_score += 3.0

            if query_tokens:
                match_count = sum(1 for token in query_tokens if token in display_norm)
                base_score += 1.5 if match_count == len(query_tokens) else (match_count / len(query_tokens)) * 0.8

            measure_matches = re.findall(r'\b\d+(?:[.,]\d+)?\s*(?:mm|m|kg|g|"\b)', normalized_q)
            for measure in measure_matches:
                base_score += 2.0 if measure in display_norm else -1.5

            sorted_items.append({
                **StockCatalogService._item_to_public_dict(item, current_offer),
                "family_path": family_path,
                "_score": base_score,
            })

        sorted_items.sort(key=lambda x: x["_score"], reverse=True)
        for item in sorted_items:
            item.pop("_score", None)
        return StockCatalogService._deduplicate_public_items(sorted_items)[:limit]

    @staticmethod
    def get_item_details(db: Session, item_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """
        Retorna os detalhes completos de um item para o drawer lateral.
        """
        item = db.query(StockCatalogItem).options(
            joinedload(StockCatalogItem.cybersul_product),
            joinedload(StockCatalogItem.specs),
            joinedload(StockCatalogItem.offers).joinedload(StockCatalogOffer.supplier),
            joinedload(StockCatalogItem.family_node)
        ).filter(
            StockCatalogItem.id == item_id
        ).first()

        if not item:
            return None

        # Caminho completo na árvore
        family_path = f"{item.source_sheet}"
        if item.family_node:
            family_path += f" > {item.family_node.title}"

        # Obter o fornecedor e preço atual principal
        current_offer = None
        current_offers = [offer for offer in item.offers if offer.is_current]
        priced_offers = [offer for offer in current_offers if offer.price and float(offer.price) > 0]
        current_offer = (priced_offers or current_offers or [None])[0]
        normalized_measure = normalize_measure(item.variation_label, item.normalized_measure, item.specification_text)
        measure_display = normalized_measure.display or item.measure_display or item.normalized_measure
        measure_kind = normalized_measure.kind if normalized_measure.canonical_key else (item.measure_kind or ("complete" if item.normalized_measure else "none"))

        return StockCatalogService._clean_response({
            "id": str(item.id),
            "display_name": item.display_name,
            "base_name": item.base_name,
            "variation_label": item.variation_label,
            "normalized_measure": item.normalized_measure,
            "measure_display": measure_display,
            "measure_kind": measure_kind,
            "specification_text": item.specification_text,
            "internal_code": item.internal_code,
            "source_sheet": item.source_sheet,
            "family_path": family_path,
            "needs_review": item.needs_review,
            "review_reason": item.review_reason,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
            "identity_hash": item.identity_hash,
            "metadata_json": item.metadata_json,
            
            # Dados do Cybersul vinculado
            "cybersul_product_id": str(item.cybersul_product_id) if item.cybersul_product_id else None,
            "cybersul_code": item.cybersul_product.cybersul_code if item.cybersul_product else None,
            "cybersul_description": item.cybersul_product.description if item.cybersul_product else None,
            "balance_vesper": float(item.cybersul_product.balance_vesper) if item.cybersul_product else 0.0,
            "balance_ventrio": float(item.cybersul_product.balance_ventrio) if item.cybersul_product else 0.0,
            "balance_total": float(item.cybersul_product.balance_total) if item.cybersul_product else 0.0,
            "cost_price": float(item.cybersul_product.cost_price) if item.cybersul_product and item.cybersul_product.cost_price else None,
            "ncm": item.cybersul_product.ncm if item.cybersul_product else None,
            "group_name": item.cybersul_product.group_name if item.cybersul_product else None,
            
            # Especificações técnicas
            "specs": [{
                "key": spec.spec_key,
                "value": spec.spec_value
            } for spec in item.specs],
            
            # Fornecedor/preço atual
            "current_price": float(current_offer.price) if current_offer and current_offer.price else None,
            "current_supplier": current_offer.supplier.name if current_offer else None,
            "offer_count": len(current_offers),
            "has_price": bool(current_offer and current_offer.price and float(current_offer.price) > 0),
            "unit": current_offer.unit if current_offer else "un",
            "purchase_context": StockCatalogService.get_item_purchase_context(db, item.id),
        })

    @staticmethod
    def get_item_offers(db: Session, item_id: uuid.UUID) -> List[Dict[str, Any]]:
        offers = db.query(StockCatalogOffer).options(
            joinedload(StockCatalogOffer.supplier)
        ).filter(
            StockCatalogOffer.item_id == item_id,
            StockCatalogOffer.is_current == True
        ).all()

        return StockCatalogService._clean_response([{
            "id": o.id,
            "item_id": o.item_id,
            "supplier_id": o.supplier_id,
            "supplier_name": o.supplier.name,
            "import_run_id": o.import_run_id,
            "price": float(o.price) if o.price is not None else None,
            "price_raw": o.price_raw,
            "final_value": float(o.final_value) if o.final_value is not None else None,
            "final_value_raw": o.final_value_raw,
            "currency": o.currency,
            "unit": o.unit,
            "availability": o.availability,
            "delivery_time": o.delivery_time,
            "contact_email": o.contact_email or o.supplier.email,
            "contact_phone": o.contact_phone or o.supplier.phone,
            "email": o.contact_email or o.supplier.email,
            "phone": o.contact_phone or o.supplier.phone,
            "source_sheet": o.source_sheet,
            "source_row": o.source_row,
            "is_current": o.is_current,
            "is_consolidated_line": o.is_consolidated_line,
            "confidence": float(o.confidence) if o.confidence is not None else 1.0,
            "needs_review": o.needs_review,
            "created_at": o.created_at
        } for o in offers])

    @staticmethod
    def get_item_history(db: Session, item_id: uuid.UUID) -> List[Dict[str, Any]]:
        history = db.query(StockCatalogPriceHistory).options(
            joinedload(StockCatalogPriceHistory.supplier),
            joinedload(StockCatalogPriceHistory.changed_by)
        ).filter(
            StockCatalogPriceHistory.item_id == item_id
        ).order_by(desc(StockCatalogPriceHistory.changed_at)).all()

        return [{
            "id": str(h.id),
            "supplier_name": h.supplier.name,
            "old_price": float(h.old_price) if h.old_price else None,
            "new_price": float(h.new_price),
            "source": h.source,
            "source_reference": h.source_reference,
            "changed_by": h.changed_by.username if h.changed_by else "Sistema",
            "changed_at": h.changed_at,
            "notes": h.notes
        } for h in history]

    @staticmethod
    def get_item_purchase_context(db: Session, item_id: uuid.UUID) -> Dict[str, Any]:
        from app.models.purchase import PurchaseRequest, PurchaseRequestItem, PurchaseRFQ

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

        row = (
            db.query(PurchaseRequestItem, PurchaseRequest, PurchaseRFQ)
            .join(PurchaseRequest, PurchaseRequest.id == PurchaseRequestItem.purchase_request_id)
            .outerjoin(PurchaseRFQ, PurchaseRFQ.purchase_request_id == PurchaseRequest.id)
            .filter(
                PurchaseRequestItem.stock_catalog_item_id == item_id,
                PurchaseRequest.status.in_(open_request_statuses),
                or_(PurchaseRFQ.id.is_(None), PurchaseRFQ.status.in_(open_rfq_statuses)),
            )
            .order_by(desc(PurchaseRequest.updated_at))
            .first()
        )

        if not row:
            return {
                "has_open_purchase": False,
                "message": "Nenhuma cotacao em andamento para este item.",
                "suggested_quantity": None,
                "quantity_explanation": "Nao ha dados suficientes para sugerir quantidade. Informe a quantidade desejada.",
            }

        request_item, request, rfq = row
        quantity = float(request_item.quantity or 0)
        return {
            "has_open_purchase": True,
            "request_id": str(request.id),
            "quote_id": str(rfq.id) if rfq else None,
            "request_title": request.title,
            "request_status": request.status,
            "quote_status": rfq.status if rfq else None,
            "quantity": quantity,
            "unit": request_item.unit_of_measure,
            "created_at": request.created_at.isoformat() if request.created_at else None,
            "updated_at": request.updated_at.isoformat() if request.updated_at else None,
            "action_url": f"/purchases?quote={rfq.id}&step=products" if rfq else f"/purchases?id={request.id}",
            "message": f"Cotacao em andamento para {quantity:g} {request_item.unit_of_measure}.",
            "suggested_quantity": None,
            "quantity_explanation": "Existe uma cotacao aberta para este item. Revise antes de criar outra.",
        }

    @staticmethod
    def update_item_price(
        db: Session,
        item_id: uuid.UUID,
        supplier_id: uuid.UUID,
        new_price: float,
        notes: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Atualiza manualmente o preço de uma oferta de item/fornecedor específico.
        """
        if new_price <= 0:
            raise ValueError("Informe um preco maior que zero.")

        item = db.query(StockCatalogItem).filter(StockCatalogItem.id == item_id).first()
        if not item:
            raise ValueError("Item não encontrado no catálogo.")

        supplier = db.query(StockCatalogSupplier).filter(StockCatalogSupplier.id == supplier_id).first()
        if not supplier:
            raise ValueError("Fornecedor não cadastrado.")

        # Buscar a oferta ativa
        offer = db.query(StockCatalogOffer).filter(
            StockCatalogOffer.item_id == item_id,
            StockCatalogOffer.supplier_id == supplier_id,
            StockCatalogOffer.is_current == True
        ).first()

        if not offer:
            raise ValueError("Este fornecedor nao possui oferta ativa para esta variacao.")

        old_price = float(offer.price) if offer.price else None
        offer.is_current = False
        
        # Criar nova oferta com preço atualizado
        # Usa o import_run_id da oferta existente ou do item pai para manter integridade referencial
        fallback_run_id = offer.import_run_id if offer else item.import_run_id
        new_offer = StockCatalogOffer(
            item_id=item_id,
            supplier_id=supplier_id,
            import_run_id=fallback_run_id,
            source_sheet=offer.source_sheet if offer else "ATUALIZACAO_MANUAL",
            source_row=offer.source_row if offer else 0,
            price=new_price,
            price_raw=f"R$ {new_price:.2f}",
            final_value=new_price, # assume final_value igual
            currency="BRL",
            unit=offer.unit if offer else "un",
            is_current=True,
            is_consolidated_line=False,
            confidence=1.0,
            needs_review=False
        )
        db.add(new_offer)

        # Gravar histórico de preços
        history = StockCatalogPriceHistory(
            item_id=item_id,
            supplier_id=supplier_id,
            old_price=old_price,
            new_price=new_price,
            source="MANUAL",
            source_reference="Portal Vesper UI",
            changed_by_user_id=user_id,
            notes=notes
        )
        db.add(history)
        
        # Atualizar valor no índice de busca
        search_idx = db.query(StockCatalogSearchIndex).filter(
            StockCatalogSearchIndex.item_id == item_id
        ).first()
        if search_idx:
            search_idx.last_price = new_price
            search_idx.last_supplier = supplier.name
            search_idx.updated_at = datetime.now(timezone.utc)

        item.updated_at = datetime.now(timezone.utc)
        log_action(
            db=db,
            user_id=user_id,
            action="stock.price_updated",
            module="stock",
            details={
                "item_id": str(item_id),
                "supplier_id": str(supplier_id),
                "old_price": old_price,
                "new_price": new_price,
                "summary": f"Preco atualizado de R$ {old_price:.2f} para R$ {new_price:.2f} para o fornecedor {supplier.name}." if old_price else f"Preco atualizado para R$ {new_price:.2f} para o fornecedor {supplier.name}.",
            },
            commit=False,
        )
        emit_event(
            db=db,
            event_type="stock.price_updated",
            aggregate_type="stock_catalog_item",
            aggregate_id=str(item_id),
            module="stock",
            payload={
                "item_id": str(item_id),
                "supplier_id": str(supplier_id),
                "supplier_name": supplier.name,
                "old_price": old_price,
                "new_price": float(new_price),
                "actor_user_id": user_id,
                "summary": f"Preco de {item.display_name} atualizado para {supplier.name}.",
            },
            actor_user_id=user_id,
        )

        db.commit()

        # Calcular diferença
        diff_amount = new_price - (old_price or 0.0)
        diff_percent = (diff_amount / old_price * 100.0) if old_price else 0.0

        return {
            "item_id": str(item_id),
            "item_display_name": item.display_name,
            "supplier_id": str(supplier_id),
            "supplier_name": supplier.name,
            "old_price": old_price,
            "new_price": new_price,
            "difference_amount": diff_amount,
            "difference_percent": diff_percent,
            "notes": notes,
            "updated_at": item.updated_at.isoformat() if item.updated_at else None,
            "message": f"Preco atualizado de R$ {old_price:.2f} para R$ {new_price:.2f} para o fornecedor {supplier.name}." if old_price else f"Preco atualizado para R$ {new_price:.2f} para o fornecedor {supplier.name}.",
        }

    @staticmethod
    def create_quote_draft(db: Session, item_id: uuid.UUID) -> Dict[str, Any]:
        """
        Gera um payload/rascunho de cotação para o módulo de Compras.
        """
        item = db.query(StockCatalogItem).options(
            joinedload(StockCatalogItem.cybersul_product),
            joinedload(StockCatalogItem.offers).joinedload(StockCatalogOffer.supplier)
        ).filter(
            StockCatalogItem.id == item_id
        ).first()

        if not item:
            raise ValueError("Item não encontrado.")

        # Obter fornecedores recomendados
        suppliers = []
        for o in item.offers:
            if o.is_current:
                suppliers.append({
                    "supplier_id": str(o.supplier_id),
                    "supplier_name": o.supplier.name,
                    "last_price": float(o.price) if o.price else None,
                    "email": o.contact_email or o.supplier.email,
                    "phone": o.contact_phone or o.supplier.phone
                })

        return {
            "product_item_id": str(item.id),
            "display_name": item.display_name,
            "cybersul_code": item.cybersul_product.cybersul_code if item.cybersul_product else None,
            "variation": item.variation_label,
            "description": item.base_name,
            "suggested_suppliers": suppliers,
            "quantity": 1, # Default rascunho
            "observations": f"Rascunho gerado a partir do Catálogo. Medida: {item.normalized_measure or ''}"
        }

    @staticmethod
    def get_review_queue(db: Session) -> List[Dict[str, Any]]:
        reviews = db.query(StockCatalogReviewQueue).options(
            joinedload(StockCatalogReviewQueue.item)
        ).filter(
            StockCatalogReviewQueue.status == "PENDING"
        ).all()

        return [{
            "id": str(r.id),
            "item_id": str(r.item_id),
            "item_display_name": r.item.display_name,
            "import_run_id": str(r.import_run_id),
            "review_type": r.review_type,
            "severity": r.severity,
            "title": r.title,
            "description": r.description,
            "raw_context_json": r.raw_context_json,
            "status": r.status
        } for r in reviews]

    @staticmethod
    def get_grouped_review_queue(db: Session) -> Dict[str, Any]:
        """
        Retorna a fila de revisão agrupada por tipo de inconsistência com contadores e descrições.
        """
        # 1. Inativos do Cybersul (INACTIVE)
        inactive_count = db.query(func.count(StockCatalogItem.id)).filter(
            StockCatalogItem.quality_status == "INACTIVE"
        ).scalar() or 0
        
        # 2. Itens sem código Cybersul (NEEDS_CYBERSUL_CODE)
        missing_code_count = db.query(func.count(StockCatalogItem.id)).filter(
            StockCatalogItem.active == True,
            StockCatalogItem.quality_status == "NEEDS_REVIEW",
            StockCatalogItem.cybersul_product_id.is_(None)
        ).scalar() or 0
        
        # 3. Ofertas incompletas/sem preço
        incomplete_offers_count = db.query(func.count(StockCatalogOffer.id)).filter(
            StockCatalogOffer.is_current == False,
            or_(StockCatalogOffer.price.is_(None), StockCatalogOffer.price <= 0)
        ).scalar() or 0
        
        # 4. Fornecedores sem e-mail
        missing_email_count = db.query(func.count(StockCatalogSupplier.id)).filter(
            StockCatalogSupplier.active == True,
            or_(StockCatalogSupplier.email.is_(None), StockCatalogSupplier.email == "")
        ).scalar() or 0
        
        # 5. Possíveis duplicados
        duplicates_count = db.query(func.count(StockCatalogReviewQueue.id)).filter(
            StockCatalogReviewQueue.status == "PENDING",
            StockCatalogReviewQueue.review_type == "possible_duplicate"
        ).scalar() or 0
        
        measure_duplicates_count = len(db.query(
            StockCatalogItem.canonical_identity_key,
            func.count(StockCatalogItem.id),
        ).filter(
            StockCatalogItem.active == True,
            StockCatalogItem.canonical_identity_key.is_not(None),
        ).group_by(StockCatalogItem.canonical_identity_key).having(func.count(StockCatalogItem.id) > 1).all())
        incomplete_measure_count = db.query(func.count(StockCatalogItem.id)).filter(
            StockCatalogItem.active == True,
            StockCatalogItem.measure_kind == "partial",
        ).scalar() or 0
        suspicious_supplier_count = db.query(func.count(StockCatalogReviewQueue.id)).filter(
            StockCatalogReviewQueue.status == "PENDING",
            StockCatalogReviewQueue.review_type == "suspicious_supplier",
        ).scalar() or 0

        # 6. Linhas suspeitas/Quarentena (QUARANTINED)
        quarantine_count = db.query(func.count(StockCatalogItem.id)).filter(
            StockCatalogItem.quality_status == "QUARANTINED"
        ).scalar() or 0
        
        # 7. Vínculos de alta confiança
        high_confidence_count = db.query(func.count(StockCatalogLink.id)).filter(
            StockCatalogLink.needs_review == True,
            StockCatalogLink.confidence >= 0.90
        ).scalar() or 0
        
        # 8. Revisão humana real
        human_review_count = db.query(func.count(StockCatalogReviewQueue.id)).filter(
            StockCatalogReviewQueue.status == "PENDING",
            ~StockCatalogReviewQueue.review_type.in_(["possible_duplicate", "missing_supplier_email"])
        ).scalar() or 0
        
        return {
            "inactive": {
                "count": inactive_count,
                "label": "Inativos ocultados",
                "description": "Itens marcados como inativos no Cybersul que não aparecem no catálogo operacional."
            },
            "missing_code": {
                "count": missing_code_count,
                "label": "Sem código Cybersul",
                "description": "Itens importados de planilhas de compras que não possuem código oficial vinculado."
            },
            "incomplete_offers": {
                "count": incomplete_offers_count,
                "label": "Ofertas sem preço",
                "description": "Cotações ou linhas de importação sem valor/preço válido registrado."
            },
            "missing_email": {
                "count": missing_email_count,
                "label": "Fornecedores sem e-mail",
                "description": "Fornecedores cadastrados que necessitam de e-mail de contato para automações."
            },
            "duplicates": {
                "count": duplicates_count + measure_duplicates_count,
                "label": "Possíveis duplicados",
                "description": "Produtos com nomes ou especificações semelhantes importados de planilhas."
            },
            "incomplete_measure": {
                "count": incomplete_measure_count,
                "label": "Medidas incompletas",
                "description": "Itens com medida parcial que precisam ser revisados antes de virar medida principal."
            },
            "suspicious_supplier": {
                "count": suspicious_supplier_count,
                "label": "Fornecedor suspeito",
                "description": "Valores que parecem material, grupo ou descricao em vez de fornecedor comercial."
            },
            "quarantine": {
                "count": quarantine_count,
                "label": "Quarentena (Linhas suspeitas)",
                "description": "Linhas que parecem ruído de parser (títulos, números de linhas, cabeçalhos, etc.)."
            },
            "high_confidence": {
                "count": high_confidence_count,
                "label": "Vínculos de confiança alta",
                "description": "Pareamentos de planilhas com o Cybersul com taxa de acerto acima de 90%."
            },
            "human_review": {
                "count": human_review_count,
                "label": "Revisão humana real",
                "description": "Pendências críticas que requerem aprovação ou correção manual do administrador."
            }
        }

    @staticmethod
    def get_group_items(db: Session, group_name: str) -> List[Dict[str, Any]]:
        """
        Retorna os detalhes e itens de um grupo de saneamento específico.
        """
        if group_name == "inactive":
            items = db.query(StockCatalogItem).filter(StockCatalogItem.quality_status == "INACTIVE").all()
            return [{"id": str(i.id), "display_name": i.display_name, "code": i.internal_code, "reason": i.review_reason} for i in items]
            
        elif group_name == "missing_code":
            items = db.query(StockCatalogItem).filter(
                StockCatalogItem.active == True,
                StockCatalogItem.quality_status == "NEEDS_REVIEW",
                StockCatalogItem.cybersul_product_id.is_(None)
            ).all()
            return [{"id": str(i.id), "display_name": i.display_name, "reason": "Sem vínculo com código oficial Cybersul."} for i in items]
            
        elif group_name == "incomplete_offers":
            offers = db.query(StockCatalogOffer).options(joinedload(StockCatalogOffer.item), joinedload(StockCatalogOffer.supplier)).filter(
                StockCatalogOffer.is_current == False,
                or_(StockCatalogOffer.price.is_(None), StockCatalogOffer.price <= 0)
            ).limit(100).all()
            return [{
                "id": str(o.id),
                "display_name": o.item.display_name if o.item else "Desconhecido",
                "supplier_name": o.supplier.name if o.supplier else "Desconhecido",
                "reason": "Oferta sem preço ou zerada encontrada na linha de origem."
            } for o in offers]
            
        elif group_name == "missing_email":
            suppliers = db.query(StockCatalogSupplier).filter(
                StockCatalogSupplier.active == True,
                or_(StockCatalogSupplier.email.is_(None), StockCatalogSupplier.email == "")
            ).all()
            return [{"id": str(s.id), "display_name": s.name, "reason": "Fornecedor cadastrado sem e-mail corporativo."} for s in suppliers]
            
        elif group_name == "duplicates":
            reviews = db.query(StockCatalogReviewQueue).options(joinedload(StockCatalogReviewQueue.item)).filter(
                StockCatalogReviewQueue.status == "PENDING",
                StockCatalogReviewQueue.review_type == "possible_duplicate"
            ).all()
            rows = [{"id": str(r.id), "display_name": r.item.display_name if r.item else r.title, "reason": r.description} for r in reviews]
            duplicate_keys = db.query(
                StockCatalogItem.canonical_identity_key,
                func.count(StockCatalogItem.id),
            ).filter(
                StockCatalogItem.active == True,
                StockCatalogItem.canonical_identity_key.is_not(None),
            ).group_by(StockCatalogItem.canonical_identity_key).having(func.count(StockCatalogItem.id) > 1).limit(50).all()
            for key, count in duplicate_keys:
                sample = db.query(StockCatalogItem).filter(StockCatalogItem.canonical_identity_key == key).first()
                rows.append({
                    "id": str(sample.id) if sample else key,
                    "display_name": sample.display_name if sample else key,
                    "reason": f"{count} variacoes compartilham a mesma identidade de medida.",
                })
            return rows

        elif group_name == "incomplete_measure":
            items = db.query(StockCatalogItem).filter(
                StockCatalogItem.active == True,
                StockCatalogItem.measure_kind == "partial",
            ).limit(100).all()
            return [{"id": str(i.id), "display_name": i.display_name, "reason": i.measure_display or "Medida parcial detectada."} for i in items]

        elif group_name == "suspicious_supplier":
            reviews = db.query(StockCatalogReviewQueue).options(joinedload(StockCatalogReviewQueue.item)).filter(
                StockCatalogReviewQueue.status == "PENDING",
                StockCatalogReviewQueue.review_type == "suspicious_supplier",
            ).all()
            return [{"id": str(r.id), "display_name": r.item.display_name if r.item else r.title, "reason": r.description} for r in reviews]
            
        elif group_name == "quarantine":
            items = db.query(StockCatalogItem).filter(StockCatalogItem.quality_status == "QUARANTINED").all()
            return [{"id": str(i.id), "display_name": i.display_name, "reason": i.review_reason or "Identificado como ruído de parser ou cabeçalho."} for i in items]
            
        elif group_name == "high_confidence":
            links = db.query(StockCatalogLink).options(joinedload(StockCatalogLink.catalog_item), joinedload(StockCatalogLink.cybersul_product)).filter(
                StockCatalogLink.needs_review == True,
                StockCatalogLink.confidence >= 0.90
            ).all()
            return [{
                "id": str(link.id),
                "display_name": link.catalog_item.display_name if link.catalog_item else "Desconhecido",
                "code": link.cybersul_product.cybersul_code if link.cybersul_product else "N/A",
                "reason": f"Confiança de vinculo de {float(link.confidence)*100:.1f}%."
            } for link in links]
            
        elif group_name == "human_review":
            reviews = db.query(StockCatalogReviewQueue).options(joinedload(StockCatalogReviewQueue.item)).filter(
                StockCatalogReviewQueue.status == "PENDING",
                ~StockCatalogReviewQueue.review_type.in_(["possible_duplicate", "missing_supplier_email"])
            ).all()
            return [{"id": str(r.id), "display_name": r.item.display_name if r.item else r.title, "reason": r.description} for r in reviews]
            
        return []

    @staticmethod
    def resolve_group_bulk(db: Session, group_name: str, action: str, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Executa ações em massa de resolução para um grupo de saneamento específico.
        """
        count = 0
        if group_name == "high_confidence" and action == "APPROVE_ALL":
            links = db.query(StockCatalogLink).filter(
                StockCatalogLink.needs_review == True,
                StockCatalogLink.confidence >= 0.90
            ).all()
            for link in links:
                link.needs_review = False
                link.approved_by_user_id = user_id
                link.approved_at = datetime.now(timezone.utc)
                
                # Atualiza item
                item = db.query(StockCatalogItem).filter(StockCatalogItem.id == link.stock_catalog_item_id).first()
                if item:
                    item.cybersul_product_id = link.cybersul_product_id
                    item.quality_status = "ENRICHED"
                    item.needs_review = False
                    
                    search_idx = db.query(StockCatalogSearchIndex).filter(StockCatalogSearchIndex.item_id == item.id).first()
                    if search_idx and link.cybersul_product:
                        search_idx.cybersul_code = link.cybersul_product.cybersul_code
                count += 1
                
        elif group_name == "quarantine" and action == "EXCLUDE_ALL":
            items = db.query(StockCatalogItem).filter(StockCatalogItem.quality_status == "QUARANTINED").all()
            for i in items:
                i.visibility_scope = "HIDDEN"
                count += 1
                
        elif group_name == "missing_email" and action == "KEEP_WITHOUT_EMAIL":
            suppliers = db.query(StockCatalogSupplier).filter(
                StockCatalogSupplier.active == True,
                or_(StockCatalogSupplier.email.is_(None), StockCatalogSupplier.email == "")
            ).all()
            for s in suppliers:
                # Simplesmente marca como ativo/resolvido localmente na flag
                s.source = "RESOLVED_WITHOUT_EMAIL"
                count += 1
                
        elif group_name == "incomplete_offers" and action == "IGNORE_ALL":
            # Remove ofertas inválidas
            count = db.query(StockCatalogOffer).filter(
                StockCatalogOffer.is_current == False,
                or_(StockCatalogOffer.price.is_(None), StockCatalogOffer.price <= 0)
            ).delete()
            
        db.commit()
        return {
            "group_name": group_name,
            "action": action,
            "resolved_count": count
        }

    @staticmethod
    def resolve_review(
        db: Session,
        review_id: uuid.UUID,
        action: str, # APPROVE | REJECT | IGNORE
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        review = db.query(StockCatalogReviewQueue).filter(
            StockCatalogReviewQueue.id == review_id
        ).first()

        if not review:
            raise ValueError("Item na fila de revisão não encontrado.")

        review.status = "RESOLVED" if action in ("APPROVE", "IGNORE") else "PENDING"
        review.resolved_by_user_id = user_id
        review.resolved_at = datetime.now(timezone.utc)

        # Se for um link de Cybersul para aprovar
        if action == "APPROVE" and review.review_type == "CYBERSUL_MATCH":
            # Atualiza o item correspondente
            item = db.query(StockCatalogItem).filter(StockCatalogItem.id == review.item_id).first()
            if item and review.raw_context_json:
                cyber_prod_id = review.raw_context_json.get("cybersul_product_id")
                if cyber_prod_id:
                    item.cybersul_product_id = uuid.UUID(cyber_prod_id)
                    item.needs_review = False
                    
                    # Atualiza índice de busca
                    cyber_prod = db.query(StockCatalogCybersulProduct).filter(
                        StockCatalogCybersulProduct.id == item.cybersul_product_id
                    ).first()
                    
                    search_idx = db.query(StockCatalogSearchIndex).filter(
                        StockCatalogSearchIndex.item_id == item.id
                    ).first()
                    if search_idx and cyber_prod:
                        search_idx.cybersul_code = cyber_prod.cybersul_code

        db.commit()
        return {
            "review_id": str(review_id),
            "status": review.status,
            "resolved_at": review.resolved_at
        }

    @staticmethod
    def list_items(
        db: Session,
        q: Optional[str] = None,
        sheet: Optional[str] = None,
        family_id: Optional[uuid.UUID] = None,
        product_id: Optional[uuid.UUID] = None,
        include_review: bool = False,
        suggest: bool = False,
        current_user: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Retorna itens do catálogo filtrados por query textual (q) e/ou nós da árvore comercial.
        """
        is_admin = False
        if current_user:
            is_admin = (
                current_user.role and current_user.role.name in {"ADMIN", "MESSIAS"}
            )

        actual_include_review = include_review if is_admin else False

        if q:
            results = StockCatalogService.search_catalog(
                db,
                q,
                current_user=current_user,
                limit=6 if suggest else 50
            )
            filtered = []
            has_hidden = False
            for item in results:
                item_db = db.query(StockCatalogItem).filter(StockCatalogItem.id == uuid.UUID(item["id"])).first()
                if not item_db:
                    continue
                
                if (
                    not actual_include_review and (
                        item_db.visibility_scope != "COMMON"
                        or not item_db.is_searchable_common
                        or item_db.quality_status in ("INACTIVE", "QUARANTINED", "HIDDEN")
                    )
                ):
                    has_hidden = True
                    continue
                
                if sheet and _norm(StockCatalogService._catalog_root_label_for_item(item_db)) != _norm(sheet):
                    continue
                if family_id and item_db.family_node_id != family_id:
                    continue
                if product_id and item_db.product_node_id != product_id:
                    continue
                
                filtered.append(item)
            
            if has_hidden and not actual_include_review:
                filtered.append({
                    "id": "sentinel-hidden-reviews",
                    "display_name": "Review Sentinel",
                    "base_name": "",
                    "variation_label": None,
                    "normalized_measure": None,
                    "specification_text": None,
                    "internal_code": None,
                    "quality_status": "HIDDEN_IN_REVIEW",
                    "needs_review": False,
                    "review_reason": None,
                    "family_path": "",
                    "source_sheet": "",
                    "cybersul_code": None,
                    "cybersul_description": None,
                    "balance_total": 0.0,
                    "last_price": None,
                    "last_supplier": None,
                    "unit": "un"
                })
            filtered = StockCatalogService._deduplicate_public_items(filtered)
            result = filtered[:6] if suggest else filtered
            return StockCatalogService._clean_response(result)

        query = db.query(StockCatalogItem).options(
            joinedload(StockCatalogItem.cybersul_product),
            joinedload(StockCatalogItem.specs),
            joinedload(StockCatalogItem.offers).joinedload(StockCatalogOffer.supplier),
            joinedload(StockCatalogItem.family_node)
        )

        query = StockCatalogService._apply_common_catalog_filters(query, include_review=actual_include_review)

        if sheet:
            sheet_candidates = StockCatalogService._catalog_source_candidates_for_label(db, sheet)
            sheet_filters = [
                StockCatalogItem.canonical_category_display == sheet,
                StockCatalogItem.source_sheet == sheet,
                StockCatalogItem.canonical_category == sheet,
            ]
            if sheet_candidates["source_sheet"]:
                sheet_filters.append(StockCatalogItem.source_sheet.in_(sheet_candidates["source_sheet"]))
            if sheet_candidates["canonical_category_display"]:
                sheet_filters.append(StockCatalogItem.canonical_category_display.in_(sheet_candidates["canonical_category_display"]))
            if sheet_candidates["canonical_category"]:
                sheet_filters.append(StockCatalogItem.canonical_category.in_(sheet_candidates["canonical_category"]))
            query = query.filter(or_(*sheet_filters))
            
        if family_id:
            node = db.query(StockCatalogTreeNode).filter(StockCatalogTreeNode.id == family_id).first()
            if node:
                # Filtrar por título de família normalizado para abranger nós agrupados
                norm_title = _norm(node.title)
                all_fam_ids_query = db.query(StockCatalogTreeNode.id).filter(
                    StockCatalogTreeNode.node_type == "family",
                    StockCatalogTreeNode.normalized_title == norm_title
                )
                if sheet:
                    sheet_candidates = StockCatalogService._catalog_source_candidates_for_label(db, sheet)
                    node_sheet_filters = [StockCatalogTreeNode.source_sheet == sheet]
                    if sheet_candidates["source_sheet"]:
                        node_sheet_filters.append(StockCatalogTreeNode.source_sheet.in_(sheet_candidates["source_sheet"]))
                    all_fam_ids_query = all_fam_ids_query.filter(or_(*node_sheet_filters))
                all_fam_ids = all_fam_ids_query.all()
                fam_ids = [r[0] for r in all_fam_ids]
                query = query.filter(StockCatalogItem.family_node_id.in_(fam_ids))
            else:
                query = query.filter(StockCatalogItem.family_node_id == family_id)
                
        if product_id:
            node = db.query(StockCatalogTreeNode).filter(StockCatalogTreeNode.id == product_id).first()
            if node:
                # Filtrar por título de produto normalizado para abranger nós agrupados
                norm_title = _norm(node.title)
                all_prod_ids_query = db.query(StockCatalogTreeNode.id).filter(
                    StockCatalogTreeNode.node_type == "product",
                    StockCatalogTreeNode.normalized_title == norm_title
                )
                if sheet:
                    sheet_candidates = StockCatalogService._catalog_source_candidates_for_label(db, sheet)
                    node_sheet_filters = [StockCatalogTreeNode.source_sheet == sheet]
                    if sheet_candidates["source_sheet"]:
                        node_sheet_filters.append(StockCatalogTreeNode.source_sheet.in_(sheet_candidates["source_sheet"]))
                    all_prod_ids_query = all_prod_ids_query.filter(or_(*node_sheet_filters))
                all_prod_ids = all_prod_ids_query.all()
                prod_ids = [r[0] for r in all_prod_ids]
                query = query.filter(StockCatalogItem.product_node_id.in_(prod_ids))
            else:
                query = query.filter(StockCatalogItem.product_node_id == product_id)

        if not sheet and not family_id and not product_id:
            return []

        items = query.order_by(StockCatalogItem.display_name).limit(250).all()
        
        results = []
        for item in items:
            results.append(StockCatalogService._item_to_public_dict(item))
            
        return StockCatalogService._clean_response(StockCatalogService._deduplicate_public_items(results))

    # ─────────────────────────────────────────────────────────────────────────
    # Alertas Inteligentes
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def get_active_alerts(db: Session, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retorna alertas ativos do catálogo, enriquecidos com o display_name do item.
        """
        rows = (
            db.query(StockCatalogAlert, StockCatalogItem.display_name)
            .join(StockCatalogItem, StockCatalogItem.id == StockCatalogAlert.item_id)
            .filter(StockCatalogAlert.status == "ACTIVE")
            .order_by(
                # HIGH primeiro, depois MEDIUM, depois INFO
                desc(case(
                    (StockCatalogAlert.severity == "HIGH", 3),
                    (StockCatalogAlert.severity == "MEDIUM", 2),
                    else_=1
                )),
                desc(StockCatalogAlert.created_at)
            )
            .limit(limit)
            .all()
        )
        alerts = []
        for alert, display_name in rows:
            alerts.append(StockCatalogService._clean_response({
                "id": str(alert.id),
                "item_id": str(alert.item_id),
                "item_display_name": display_name,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "title": alert.title,
                "description": alert.description,
                "status": alert.status,
                "created_at": alert.created_at.isoformat() if alert.created_at else None,
                "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
            }))
        return alerts

    @staticmethod
    def acknowledge_alert(db: Session, alert_id: uuid.UUID) -> Dict[str, Any]:
        """
        Marca um alerta como ACKNOWLEDGED (visto pelo usuário, mas não resolvido).
        """
        alert = db.query(StockCatalogAlert).filter(StockCatalogAlert.id == alert_id).first()
        if not alert:
            raise ValueError("Alerta não encontrado.")
        alert.status = "ACKNOWLEDGED"
        db.commit()
        return {"id": str(alert.id), "status": "ACKNOWLEDGED"}

    @staticmethod
    def generate_and_refresh_alerts(db: Session) -> Dict[str, Any]:
        """
        Varredura automática para gerar alertas inteligentes com base nos dados reais do banco.

        Tipos gerados:
        - LOW_STOCK: item com saldo Cybersul <= 5 e pelo menos uma oferta ativa
        - NO_SUPPLIER: item ativo sem nenhuma oferta is_current=True
        - PRICE_STALE: item cujo preço não foi atualizado há mais de 180 dias
        - SINGLE_SUPPLIER: item com exatamente 1 fornecedor ativo

        Regra anti-duplicação: não cria novo alerta se já existe alerta ATIVO do mesmo tipo
        para o mesmo item.
        """
        now = datetime.now(timezone.utc)
        stale_threshold = now - timedelta(days=180)
        created = 0
        skipped = 0

        # ── Busca todos os alertas ATIVOS agrupados por (item_id, alert_type) para anti-duplicação ──
        existing_active = set(
            (str(r.item_id), r.alert_type)
            for r in db.query(StockCatalogAlert.item_id, StockCatalogAlert.alert_type)
            .filter(StockCatalogAlert.status == "ACTIVE")
            .all()
        )

        def _already_active(item_id: uuid.UUID, alert_type: str) -> bool:
            return (str(item_id), alert_type) in existing_active

        def _create_alert(item_id: uuid.UUID, alert_type: str, severity: str, title: str, description: str):
            nonlocal created, skipped
            if _already_active(item_id, alert_type):
                skipped += 1
                return
            alert = StockCatalogAlert(
                item_id=item_id,
                alert_type=alert_type,
                severity=severity,
                title=title,
                description=description,
                status="ACTIVE",
                created_at=now,
            )
            db.add(alert)
            existing_active.add((str(item_id), alert_type))  # evita duplicação dentro desta rodada
            created += 1

        # ── 1. LOW_STOCK: saldo Cybersul <= 5 e item tem oferta ativa ──
        low_stock_items = (
            db.query(StockCatalogItem)
            .join(StockCatalogCybersulProduct, StockCatalogItem.cybersul_product_id == StockCatalogCybersulProduct.id)
            .filter(
                StockCatalogItem.active == True,
                StockCatalogCybersulProduct.balance_total <= 5.0,
                StockCatalogCybersulProduct.balance_total >= 0,
            )
            .limit(200)
            .all()
        )
        for item in low_stock_items:
            balance = float(item.cybersul_product.balance_total) if item.cybersul_product else 0
            _create_alert(
                item_id=item.id,
                alert_type="LOW_STOCK",
                severity="HIGH" if balance <= 1 else "MEDIUM",
                title=f"Estoque baixo: {item.display_name}",
                description=f"Saldo atual: {balance:.2f} unidades. Verificar necessidade de compra.",
            )

        # ── 2. NO_SUPPLIER: item ativo sem oferta is_current ──
        items_with_offers = (
            db.query(StockCatalogOffer.item_id)
            .filter(StockCatalogOffer.is_current == True)
            .distinct()
            .subquery()
        )
        no_supplier_items = (
            db.query(StockCatalogItem)
            .filter(
                StockCatalogItem.active == True,
                StockCatalogItem.is_parser_junk == False,
                or_(StockCatalogItem.visibility_scope == "COMMON", StockCatalogItem.visibility_scope.is_(None)),
                StockCatalogItem.id.notin_(db.query(items_with_offers.c.item_id)),
            )
            .limit(200)
            .all()
        )
        for item in no_supplier_items:
            _create_alert(
                item_id=item.id,
                alert_type="NO_SUPPLIER",
                severity="MEDIUM",
                title=f"Sem fornecedor: {item.display_name}",
                description="Item sem oferta de fornecedor ativa. Necessário cotar ou vincular fornecedor.",
            )

        # ── 3. PRICE_STALE: último registro de histórico mais antigo que 180 dias ──
        # Subquery: max(changed_at) por item
        last_update_sq = (
            db.query(
                StockCatalogPriceHistory.item_id,
                func.max(StockCatalogPriceHistory.changed_at).label("last_at")
            )
            .group_by(StockCatalogPriceHistory.item_id)
            .subquery()
        )
        stale_items = (
            db.query(StockCatalogItem)
            .join(last_update_sq, last_update_sq.c.item_id == StockCatalogItem.id)
            .filter(
                StockCatalogItem.active == True,
                last_update_sq.c.last_at < stale_threshold,
                or_(StockCatalogItem.visibility_scope == "COMMON", StockCatalogItem.visibility_scope.is_(None)),
            )
            .limit(200)
            .all()
        )
        for item in stale_items:
            _create_alert(
                item_id=item.id,
                alert_type="PRICE_STALE",
                severity="INFO",
                title=f"Preço desatualizado: {item.display_name}",
                description="Preço deste item não foi atualizado nos últimos 180 dias. Recomenda-se nova cotação.",
            )

        # ── 4. SINGLE_SUPPLIER: item com exatamente 1 fornecedor ativo ──
        supplier_count_sq = (
            db.query(
                StockCatalogOffer.item_id,
                func.count(StockCatalogOffer.supplier_id.distinct()).label("supplier_count")
            )
            .filter(StockCatalogOffer.is_current == True)
            .group_by(StockCatalogOffer.item_id)
            .subquery()
        )
        single_supplier_items = (
            db.query(StockCatalogItem)
            .join(supplier_count_sq, supplier_count_sq.c.item_id == StockCatalogItem.id)
            .filter(
                StockCatalogItem.active == True,
                supplier_count_sq.c.supplier_count == 1,
                or_(StockCatalogItem.visibility_scope == "COMMON", StockCatalogItem.visibility_scope.is_(None)),
            )
            .limit(200)
            .all()
        )
        for item in single_supplier_items:
            _create_alert(
                item_id=item.id,
                alert_type="SINGLE_SUPPLIER",
                severity="INFO",
                title=f"Fornecedor único: {item.display_name}",
                description="Este item possui apenas um fornecedor ativo. Risco de desabastecimento em caso de falha.",
            )

        db.commit()

        return {
            "generated": created,
            "skipped_duplicates": skipped,
            "types_checked": ["LOW_STOCK", "NO_SUPPLIER", "PRICE_STALE", "SINGLE_SUPPLIER"],
            "generated_at": now.isoformat(),
        }
