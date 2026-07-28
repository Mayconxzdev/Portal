from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import PermissionLevel, check_module_access
from app.models.legacy_import import LegacyFileIndex

router = APIRouter(dependencies=[Depends(check_module_access("files", PermissionLevel.READ_ONLY))])


@router.get("/")
def list_files(db: Session = Depends(get_db), limit: int = Query(200, ge=1, le=1000)):
    """Retorna arquivos e templates reais indexados a partir dos legados."""
    rows = db.query(LegacyFileIndex).order_by(LegacyFileIndex.created_at.desc()).limit(limit).all()
    return {
        "status": "success",
        "module": "files",
        "files_count": len(rows),
        "files": [
            {
                "id": str(row.id),
                "title": row.file_name,
                "category": row.category,
                "type": row.file_type,
                "size_bytes": row.file_size_bytes,
                "path_masked": row.file_path_masked,
                "suggested_module": row.suggested_module,
                "tags": row.tags or [],
            }
            for row in rows
        ],
    }


@router.get("/knowledge")
def search_knowledge_base(
    q: str = "",
    db: Session = Depends(get_db),
    limit: int = Query(200, ge=1, le=1000),
):
    """Pesquisa metadados reais indexados na base de conhecimento corporativa."""
    query = db.query(LegacyFileIndex)
    if q:
        query = query.filter(LegacyFileIndex.file_name.ilike(f"%{q}%"))
    rows = query.order_by(LegacyFileIndex.created_at.desc()).limit(limit).all()
    return {
        "status": "success",
        "module": "files",
        "documents": [
            {
                "id": str(row.id),
                "title": row.file_name,
                "category": row.category or row.suggested_module,
                "type": row.file_type,
                "path_masked": row.file_path_masked,
                "size_bytes": row.file_size_bytes,
            }
            for row in rows
        ],
    }
