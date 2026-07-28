import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import get_current_user
from app.models.user import User
from app.modules.legacy_promotion.service import LegacyPromotionService
from app.modules.legacy_promotion.schemas import (
    LegacyPromotionRequest,
    LegacyPromotionRowRequest,
    LegacyPromotionPreview,
    SyncPortalAccessResponse,
    RealDataDashboard,
    ITAccessRecordRead,
    LegacyOperationalRecordRead,
    LegacyFileIndexRead,
    PromoteBatchRequest,
    PromoteBatchResponse
)

router = APIRouter()

def require_admin_or_manager(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.role or current_user.role.name not in ("ADMIN", "MANAGER"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Recurso restrito a administradores ou gerentes."
        )
    return current_user

@router.get("/real-data-dashboard", response_model=RealDataDashboard)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """Retorna estatísticas gerais de dados reais ativados."""
    return LegacyPromotionService.get_dashboard_stats(db)

@router.get("/preview/{batch_id}", response_model=LegacyPromotionPreview)
def preview_batch_promotion(
    batch_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """Gera uma prévia da promoção do lote."""
    try:
        return LegacyPromotionService.preview_batch_promotion(db, batch_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/rows/{row_id}/promote", status_code=status.HTTP_200_OK)
def promote_row(
    row_id: uuid.UUID,
    payload: LegacyPromotionRowRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """Promove uma única linha de staging para o cadastro oficial."""
    try:
        return LegacyPromotionService.promote_row(db, row_id, current_user.id, payload.reason)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/batches/{batch_id}/promote-accepted", status_code=status.HTTP_200_OK)
def promote_batch_accepted(
    batch_id: uuid.UUID,
    payload: LegacyPromotionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """Promove em lote as linhas de staging aceitas ou sem duplicidade de um batch."""
    try:
        return LegacyPromotionService.promote_batch_accepted(db, batch_id, current_user.id, payload.reason)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/promote-batch", response_model=PromoteBatchResponse)
def promote_batch_by_module(
    payload: PromoteBatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """Promove todos os registros READY de staging para as tabelas oficiais do módulo especificado."""
    try:
        result = LegacyPromotionService.promote_all_ready_by_module(db, payload.module, current_user.id, payload.reason)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/sync-portal-access", response_model=SyncPortalAccessResponse)
def sync_portal_access(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """Sincroniza os acessos reais internos do Portal Vesper na Matriz de Acessos de TI."""
    return LegacyPromotionService.sync_portal_access(db, current_user.id)

@router.get("/export-access-matrix")
def export_access_matrix(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """Exporta a Matriz de Acessos de TI sanitizada para download em formato CSV."""
    csv_data = LegacyPromotionService.export_access_matrix_csv(db, actor_user_id=current_user.id)
    
    # Retorna o CSV como stream/download com o header correto para decodificacao de acentos (utf-8-sig)
    # Usando o prefixo UTF-8 BOM para garantir compatibilidade total com o Microsoft Excel em português
    bom = b"\xef\xbb\xbf"
    response_content = bom + csv_data.encode("utf-8")
    
    return Response(
        content=response_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=matriz_de_acessos_ti.csv"
        }
    )

@router.post("/export-to-network", status_code=status.HTTP_200_OK)
def export_to_network(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """Exporta a Matriz de Acessos de TI sanitizada diretamente para o Drive K: na rede."""
    try:
        return LegacyPromotionService.export_access_matrix_to_network(db, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/access-matrix", response_model=List[ITAccessRecordRead])
def get_access_matrix(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """Retorna os registros da Matriz de Acessos de TI em formato JSON."""
    return LegacyPromotionService.get_access_matrix(db)

@router.get("/operational-records", response_model=List[LegacyOperationalRecordRead])
def get_operational_records(
    entity_target: Optional[str] = Query(None, description="Filtro pelo target da entidade"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retorna registros operacionais legados (Produção, Projetos, Propostas)."""
    return LegacyPromotionService.get_operational_records(db, entity_target)

@router.get("/file-index", response_model=List[LegacyFileIndexRead])
def get_file_index(
    suggested_module: Optional[str] = Query(None, description="Filtro pelo módulo sugerido"),
    category: Optional[str] = Query(None, description="Filtro pela categoria do arquivo"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retorna metadados de arquivos/templates indexados legados."""
    return LegacyPromotionService.get_file_index(db, suggested_module, category)
