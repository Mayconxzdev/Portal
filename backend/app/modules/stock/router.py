import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from app.core.database import get_db
from app.core.permissions import get_current_user, check_module_access, PermissionLevel
from app.models.user import User
from app.modules.stock.service import StockCatalogService
from app.modules.purchases.service import PurchasesService
from app.modules.stock.schemas import (
    StockCatalogSummary,
    StockCatalogImportRunRead,
    StockCatalogTreeNodeRead,
    StockCatalogItemRead,
    StockCatalogOfferRead,
    StockCatalogPriceHistoryRead,
    StockCatalogReviewQueueRead,
    StockCatalogAlertRead,
    PriceUpdateInput,
    PriceUpdatePreview
)

router = APIRouter()

def check_admin_or_messias(current_user: User = Depends(get_current_user)):
    """
    Dependency para restringir ações críticas a administradores ou ao usuário Messias.
    """
    if current_user.role and current_user.role.name in {"ADMIN", "MESSIAS"}:
        return current_user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Apenas administradores ou auditores autorizados podem executar esta ação."
    )

def check_compras_permission(current_user: User = Depends(get_current_user)):
    """
    Dependency para restringir a usuários com permissão no módulo de Compras.
    """
    # Se for Admin, tem todas as permissões
    if current_user.role and current_user.role.name == "ADMIN":
        return current_user
        
    # Verificar se o usuário tem permissão para compras
    for acc in current_user.module_accesses:
        if acc.module.code == "purchases" and acc.permission_level in ("NORMAL", "ADMIN"):
            return current_user
            
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Ação restrita a usuários autorizados do módulo de Compras."
    )

@router.get("/summary", response_model=StockCatalogSummary)
def get_catalog_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retorna os KPIs gerais de Estoque & Catálogo.
    """
    return StockCatalogService.get_summary(db)

@router.post("/import/compras-nova")
def import_compras_nova_xlsx(
    filepath: Optional[str] = Query(None, description="Caminho personalizado da planilha Compras Nova"),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin_or_messias)
):
    """
    Inicia a importação da planilha Compras Nova .xlsx por árvore visual.
    """
    default_path = os.getenv("PORTAL_COMPRAS_NOVA_XLSX")
    path = filepath or default_path
    if not path:
        raise HTTPException(status_code=400, detail="Informe filepath ou configure PORTAL_COMPRAS_NOVA_XLSX.")
    
    try:
        result = StockCatalogService.import_compras_nova(path, db, user_id=current_user.id)
        return {
            "message": "Sincronização da planilha Compras Nova finalizada.",
            "details": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro no processamento da planilha Compras Nova: {str(e)}"
        )

@router.post("/import/cybersul")
def import_cybersul_xlsx(
    filepath: Optional[str] = Query(None, description="Caminho personalizado da planilha Cybersul"),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin_or_messias)
):
    """
    Inicia a importação da planilha cybersul-codigo.xlsx.
    """
    default_path = os.getenv("PORTAL_CYBERSUL_XLSX")
    path = filepath or default_path
    if not path:
        raise HTTPException(status_code=400, detail="Informe filepath ou configure PORTAL_CYBERSUL_XLSX.")
    
    try:
        result = StockCatalogService.import_cybersul(path, db, user_id=current_user.id)
        return {
            "message": "Importação do Cybersul finalizada.",
            "details": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro na importação da base do Cybersul: {str(e)}"
        )

@router.post("/import/unified")
def import_unified_xlsx(
    filepath: Optional[str] = Query(None, description="Caminho personalizado da planilha mestre unificada"),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin_or_messias)
):
    """
    Inicia a importação da planilha unificada mestre.
    """
    default_path = os.getenv("PORTAL_UNIFIED_CATALOG_XLSX")
    path = filepath or default_path
    if not path:
        raise HTTPException(status_code=400, detail="Informe filepath ou configure PORTAL_UNIFIED_CATALOG_XLSX.")
    
    try:
        result = StockCatalogService.import_unified(path, db, user_id=current_user.id)
        return {
            "message": "Importação mestre unificada concluída com sucesso.",
            "details": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro na importação mestre unificada: {str(e)}"
        )

@router.get("/import-runs", response_model=List[StockCatalogImportRunRead])
def get_import_runs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retorna o histórico de execuções de sincronização.
    """
    return StockCatalogService.get_import_runs(db)

@router.get("/tree")
def get_catalog_tree(
    sheet: Optional[str] = Query(None, description="Filtrar por aba"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retorna a árvore comercial comercial organizada (Aba -> Família -> Produto).
    """
    return StockCatalogService.get_tree(db, sheet_filter=sheet, current_user=current_user)


@router.get("/navigation/categories")
def get_navigation_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retorna somente as abas/categorias do catálogo para navegação inicial leve.
    """
    return StockCatalogService.get_navigation_categories(db, current_user=current_user)


@router.get("/navigation/families")
def get_navigation_families(
    category: str = Query(..., description="Nome da aba/categoria do catálogo"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retorna as famílias de uma aba/categoria sem carregar os itens da navegação inteira.
    """
    return StockCatalogService.get_navigation_families(db, category=category, current_user=current_user)


@router.get("/navigation/products")
def get_navigation_products(
    family_id: uuid.UUID = Query(..., description="ID da família selecionada"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retorna os produtos/grupos de uma família selecionada.
    """
    return StockCatalogService.get_navigation_products(db, family_id=family_id, current_user=current_user)

@router.get("/search")
def search_catalog(
    q: Optional[str] = Query(None, description="Termo de pesquisa"),
    sheet: Optional[str] = Query(None, description="Filtrar por aba"),
    family_id: Optional[uuid.UUID] = Query(None, description="Filtrar por ID da família"),
    product_id: Optional[uuid.UUID] = Query(None, description="Filtrar por ID do produto"),
    suggest: bool = Query(False, description="Retornar apenas sugestoes leves para autocomplete"),
    include_review: bool = Query(False, description="Incluir itens em revisão para administradores"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Busca rápida e tolerante a erros no catálogo de produtos ou navegação na árvore.
    """
    return StockCatalogService.list_items(
        db, q=q, sheet=sheet, family_id=family_id, product_id=product_id, include_review=include_review, suggest=suggest, current_user=current_user
    )

@router.get("/items/{id}")
def get_item_details(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retorna detalhes completos de um item específico do catálogo (para o Drawer).
    """
    details = StockCatalogService.get_item_details(db, id)
    if not details:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item não encontrado no catálogo."
        )
        
    # Filtrar detalhes técnicos se o usuário não for Admin ou Messias
    is_admin = current_user.role and current_user.role.name == "ADMIN"
    is_messias = current_user.username == "Messias"
    if not (is_admin or is_messias):
        # Ocultar campos de identificação interna crua e metadados técnicos complexos
        details.pop("identity_hash", None)
        details.pop("source_row", None)
        
    return details

@router.get("/items/{id}/offers", response_model=List[StockCatalogOfferRead])
def get_item_offers(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retorna as ofertas de fornecedores ativas e preços só do item solicitado.
    """
    return StockCatalogService.get_item_offers(db, id)

@router.get("/items/{id}/history", response_model=List[StockCatalogPriceHistoryRead])
def get_item_price_history(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retorna a linha do tempo e log de preços apenas do item solicitado.
    """
    return StockCatalogService.get_item_history(db, id)

@router.post("/items/{id}/price-update", response_model=PriceUpdatePreview)
def update_item_price(
    id: uuid.UUID,
    input_data: PriceUpdateInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_compras_permission)
):
    """
    Atualiza manualmente o preço de oferta do item para um fornecedor.
    Registra histórico e logs de auditoria.
    """
    try:
        return StockCatalogService.update_item_price(
            db=db,
            item_id=id,
            supplier_id=input_data.supplier_id,
            new_price=input_data.new_price,
            notes=input_data.notes,
            user_id=current_user.id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/items/{id}/quote-draft")
def create_quote_draft(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_compras_permission)
):
    """
    Gera rascunho de cotação para o módulo de Compras com as ofertas ativas.
    """
    try:
        return PurchasesService.create_quote_from_stock_item(db, id, current_user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/review-queue", response_model=List[StockCatalogReviewQueueRead])
def get_review_queue(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lista itens com inconsistências pendentes na fila de revisão.
    """
    return StockCatalogService.get_review_queue(db)

@router.get("/review-queue/grouped")
def get_grouped_review_queue(
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin_or_messias)
):
    """
    Retorna a fila de revisão agrupada com contadores e descrições para o dashboard do administrador.
    """
    return StockCatalogService.get_grouped_review_queue(db)

@router.get("/review-queue/group/{group_name}")
def get_group_items(
    group_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin_or_messias)
):
    """
    Retorna a lista de itens pertencentes a um grupo específico de saneamento.
    """
    return StockCatalogService.get_group_items(db, group_name)

@router.post("/review-queue/group/{group_name}/resolve")
def resolve_group_bulk(
    group_name: str,
    action: str = Query(..., description="Ação em massa (APPROVE_ALL | EXCLUDE_ALL | KEEP_WITHOUT_EMAIL | IGNORE_ALL)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin_or_messias)
):
    """
    Executa resoluções em lote/massa para um grupo de saneamento específico.
    """
    try:
        return StockCatalogService.resolve_group_bulk(db, group_name, action, user_id=current_user.id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/review-queue/{id}/resolve")
def resolve_review_item(
    id: uuid.UUID,
    action: str = Query(..., description="Ação para resolução (APPROVE | IGNORE)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin_or_messias)
):
    """
    Resolve item na fila de revisão de catalogação.
    """
    try:
        return StockCatalogService.resolve_review(db, id, action, user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

# ─────────────────────────────────────────────────────────────────────────────
# Alertas Inteligentes
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/alerts", response_model=List[StockCatalogAlertRead])
def get_active_alerts(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retorna alertas inteligentes ativos do catálogo de estoque.
    Ordenados por severidade (HIGH → MEDIUM → INFO) e data de criação.
    """
    return StockCatalogService.get_active_alerts(db, limit=limit)


@router.post("/alerts/refresh")
def refresh_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin_or_messias),
):
    """
    Dispara varredura para gerar/atualizar alertas inteligentes.
    Analisa: estoque baixo, sem fornecedor, preço desatualizado, fornecedor único.
    Somente Admin ou Messias podem executar.
    """
    try:
        return StockCatalogService.generate_and_refresh_alerts(db)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao gerar alertas: {str(e)}"
        )


@router.post("/alerts/{alert_id}/acknowledge")
def acknowledge_alert(
    alert_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Marca um alerta como ACKNOWLEDGED (visto pelo usuário).
    Não resolve o alerta — apenas registra que foi visualizado.
    """
    try:
        return StockCatalogService.acknowledge_alert(db, alert_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
