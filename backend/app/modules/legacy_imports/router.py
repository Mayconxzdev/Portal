import uuid
from typing import List
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import get_current_user
from app.models.user import User
from app.modules.legacy_imports.service import LegacyImportService
from app.modules.legacy_imports.schemas import (
    LegacyImportBatchCreate,
    LegacyImportBatchRead,
    LegacyImportRowBulkCreate,
    LegacyImportRowRead,
    LegacyDuplicateCandidateRead,
    LegacyImportDecisionCreate,
    LegacyImportDecisionRead,
    LegacyImportSummary
)

router = APIRouter()

# Dependência para restringir acesso a administradores ou gerentes
def require_admin_or_manager(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.role or current_user.role.name not in ("ADMIN", "MANAGER"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Recurso restrito a administradores ou gerentes."
        )
    return current_user


@router.get("/batches", response_model=List[LegacyImportBatchRead])
def list_batches(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """Retorna a lista de lotes de importação legada cadastrados."""
    return LegacyImportService.get_batches(db, skip=skip, limit=limit)


@router.post("/batches", response_model=LegacyImportBatchRead, status_code=status.HTTP_201_CREATED)
def create_batch(
    payload: LegacyImportBatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """Cria um novo lote de importação legada."""
    return LegacyImportService.create_batch(db, payload, current_user.id)


@router.get("/batches/{id}", response_model=LegacyImportBatchRead)
def get_batch(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """Busca os detalhes de um lote de importação pelo ID."""
    batch = LegacyImportService.get_batch_by_id(db, id)
    if not batch:
        raise HTTPException(status_code=404, detail="Lote de importacao nao encontrado.")
    return batch


@router.post("/batches/{id}/rows", response_model=List[LegacyImportRowRead], status_code=status.HTTP_201_CREATED)
def add_rows_to_batch(
    id: uuid.UUID,
    payload: LegacyImportRowBulkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """Adiciona e processa linhas de importação dentro de um lote."""
    try:
        return LegacyImportService.add_rows_to_batch(db, id, payload.rows)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/batches/{id}/rows", response_model=List[LegacyImportRowRead])
def list_rows_for_batch(
    id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """Retorna a lista de linhas de staging vinculadas a um lote."""
    return LegacyImportService.get_rows_by_batch(db, id, skip=skip, limit=limit)


@router.get("/rows/{id}", response_model=LegacyImportRowRead)
def get_row(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """Busca detalhes de uma linha de importação específica pelo ID."""
    row = LegacyImportService.get_row_by_id(db, id)
    if not row:
        raise HTTPException(status_code=404, detail="Linha de importacao nao encontrada.")
    return row


@router.post("/rows/{id}/decision", response_model=LegacyImportDecisionRead, status_code=status.HTTP_201_CREATED)
def record_row_decision(
    id: uuid.UUID,
    payload: LegacyImportDecisionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """Registra uma decisão administrativa sobre uma linha de staging."""
    try:
        return LegacyImportService.record_row_decision(db, id, payload, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/summary", response_model=LegacyImportSummary)
def get_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """Retorna estatísticas sumarizadas das importações legadas."""
    return LegacyImportService.get_summary(db)


@router.get("/duplicates", response_model=List[LegacyDuplicateCandidateRead])
def get_duplicates(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    """Retorna a lista de candidatos a duplicados pendentes de revisão."""
    return LegacyImportService.get_duplicates(db, skip=skip, limit=limit)
