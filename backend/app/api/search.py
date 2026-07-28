from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import LEVEL_VALUES, PermissionLevel, get_current_user
from app.models.approval import Approval
from app.models.kanban import KanbanCard
from app.models.module import Module
from app.models.user import User
from app.modules.approvals.service import ApprovalService
from app.modules.kanban.service import KanbanService

# Novas importações
from app.models.master_data import Person, Supplier, ProductItem
from app.models.it import ITTicket, ITAsset, ITCredential
from app.models.legacy_import import LegacyOperationalRecord, LegacyFileIndex


router = APIRouter()


@router.get("/global")
def global_search(
    q: str = Query("", min_length=0, max_length=120),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = q.strip()
    lowered = query.lower()
    results = []

    # 1. Módulos
    modules = db.query(Module).filter(Module.is_active == True).order_by(Module.name).all()
    for module in modules:
        level = ApprovalService.get_user_module_level(db, current_user, module.code)
        if LEVEL_VALUES[level] >= LEVEL_VALUES[PermissionLevel.READ_ONLY] and (not lowered or lowered in module.name.lower() or lowered in module.code.lower()):
            results.append({"type": "module", "id": module.code, "title": module.name, "subtitle": "Módulo", "action": "open_module"})

    # 2. Quadros Kanban
    try:
        boards = KanbanService.list_boards(db, current_user, include_archived=False)
    except Exception:
        boards = []
    board_ids = [board.id for board in boards]
    for board in boards:
        if not lowered or lowered in board.name.lower() or lowered in board.slug.lower():
            results.append({"type": "board", "id": str(board.id), "title": board.name, "subtitle": "Board Kanban", "action": "open_board"})
            results.append({"type": "tv", "id": str(board.id), "title": f"Modo TV - {board.name}", "subtitle": "Monitor Kanban", "action": "open_tv"})

    # 3. Cards Kanban
    if board_ids and query:
        cards = (
            db.query(KanbanCard)
            .filter(
                KanbanCard.board_id.in_(board_ids),
                KanbanCard.is_archived == False,
                or_(KanbanCard.title.ilike(f"%{query}%"), KanbanCard.description.ilike(f"%{query}%")),
            )
            .limit(10)
            .all()
        )
        for card in cards:
            results.append({"type": "card", "id": str(card.id), "board_id": str(card.board_id), "title": card.title, "subtitle": "Card Kanban", "action": "open_card"})

    # 4. Aprovações
    approval_level = ApprovalService.get_user_module_level(db, current_user, "approvals")
    if LEVEL_VALUES[approval_level] >= LEVEL_VALUES[PermissionLevel.READ_ONLY] and query:
        approvals = db.query(Approval).filter(Approval.title.ilike(f"%{query}%")).limit(10).all()
        for approval in approvals:
            results.append({"type": "approval", "id": approval.id, "title": approval.title, "subtitle": "Aprovação", "action": "open_approvals"})

    # Se não houver termo de busca detalhado, retorna os resultados básicos de módulos e quadros
    if not query:
        return {"query": query, "results": results[:50]}

    # 5. Compras (Fornecedores e Produtos)
    purchases_level = ApprovalService.get_user_module_level(db, current_user, "purchases")
    if LEVEL_VALUES[purchases_level] >= LEVEL_VALUES[PermissionLevel.READ_ONLY]:
        # Fornecedores
        suppliers = (
            db.query(Supplier)
            .join(Person)
            .filter(
                or_(
                    Person.name.ilike(f"%{query}%"),
                    Person.legal_name.ilike(f"%{query}%"),
                    Supplier.supplier_code.ilike(f"%{query}%")
                )
            )
            .limit(10)
            .all()
        )
        for s in suppliers:
            results.append({
                "type": "supplier",
                "id": str(s.id),
                "title": s.person.name,
                "subtitle": f"Fornecedor ({s.supplier_code or 'S/C'})",
                "action": "open_supplier"
            })

        # Produtos / Variações
        products = (
            db.query(ProductItem)
            .filter(
                or_(
                    ProductItem.sku.ilike(f"%{query}%"),
                    ProductItem.name.ilike(f"%{query}%"),
                    ProductItem.canonical_key.ilike(f"%{query}%")
                )
            )
            .limit(10)
            .all()
        )
        for p in products:
            results.append({
                "type": "product",
                "id": str(p.id),
                "title": p.name,
                "subtitle": f"Produto (SKU: {p.sku})",
                "action": "open_product",
                "canonical_key": p.canonical_key
            })

    # 6. TI (Ativos, Chamados, Credenciais)
    it_level = ApprovalService.get_user_module_level(db, current_user, "it")
    if LEVEL_VALUES[it_level] >= LEVEL_VALUES[PermissionLevel.READ_ONLY]:
        # Ativos TI
        assets = (
            db.query(ITAsset)
            .filter(
                or_(
                    ITAsset.name.ilike(f"%{query}%"),
                    ITAsset.serial_number.ilike(f"%{query}%"),
                    ITAsset.asset_tag.ilike(f"%{query}%"),
                    ITAsset.ip_address.ilike(f"%{query}%")
                )
            )
            .limit(10)
            .all()
        )
        for asset in assets:
            results.append({
                "type": "asset",
                "id": str(asset.id),
                "title": asset.name,
                "subtitle": f"Ativo TI ({asset.asset_tag or 'Sem Tag'})",
                "action": "open_asset"
            })

        # Chamados TI
        tickets = (
            db.query(ITTicket)
            .filter(
                or_(
                    ITTicket.title.ilike(f"%{query}%"),
                    ITTicket.description.ilike(f"%{query}%")
                )
            )
            .limit(10)
            .all()
        )
        for t in tickets:
            results.append({
                "type": "ticket",
                "id": str(t.id),
                "title": t.title,
                "subtitle": f"Chamado TI (#{t.id})",
                "action": "open_ticket"
            })

        # Credenciais (Cofre)
        credentials = (
            db.query(ITCredential)
            .filter(
                or_(
                    ITCredential.title.ilike(f"%{query}%"),
                    ITCredential.system_name.ilike(f"%{query}%"),
                    ITCredential.username.ilike(f"%{query}%"),
                    ITCredential.notes.ilike(f"%{query}%")
                )
            )
            .limit(10)
            .all()
        )
        for c in credentials:
            results.append({
                "type": "credential",
                "id": str(c.id),
                "title": c.title,
                "subtitle": f"Senha / Cofre ({c.username or 'Sem Usuário'})",
                "action": "open_credential"
            })

    # 7. Propostas Comerciais
    proposals_level = ApprovalService.get_user_module_level(db, current_user, "proposals")
    if LEVEL_VALUES[proposals_level] >= LEVEL_VALUES[PermissionLevel.READ_ONLY]:
        proposals = (
            db.query(LegacyOperationalRecord)
            .filter(
                LegacyOperationalRecord.entity_target == "PROPOSAL_DOCUMENT",
                or_(
                    LegacyOperationalRecord.title.ilike(f"%{query}%"),
                    LegacyOperationalRecord.responsible.ilike(f"%{query}%")
                )
            )
            .limit(10)
            .all()
        )
        for prop in proposals:
            results.append({
                "type": "proposal",
                "id": str(prop.id),
                "title": prop.title,
                "subtitle": f"Proposta Comercial ({prop.responsible or 'Sem Resp.'})",
                "action": "open_proposal"
            })

    # 8. Arquivos NAS / Templates
    knowledge_level = ApprovalService.get_user_module_level(db, current_user, "knowledge")
    if LEVEL_VALUES[knowledge_level] >= LEVEL_VALUES[PermissionLevel.READ_ONLY]:
        files = (
            db.query(LegacyFileIndex)
            .filter(
                or_(
                    LegacyFileIndex.file_name.ilike(f"%{query}%"),
                    LegacyFileIndex.category.ilike(f"%{query}%"),
                    LegacyFileIndex.suggested_module.ilike(f"%{query}%")
                )
            )
            .limit(10)
            .all()
        )
        for f in files:
            results.append({
                "type": "file",
                "id": str(f.id),
                "title": f.file_name,
                "subtitle": f"Arquivo NAS ({f.file_type.upper()})",
                "action": "open_file",
                "file_path": f.file_path_masked
            })

    return {"query": query, "results": results[:50]}
