from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.legacy_import import LegacyFileIndex

router = APIRouter()


@router.get("/")
def list_proposals(db: Session = Depends(get_db)):
    """Retorna propostas/templates reais indexados dos legados."""
    rows = (
        db.query(LegacyFileIndex)
        .filter(LegacyFileIndex.suggested_module == "proposals")
        .order_by(LegacyFileIndex.created_at.desc())
        .limit(300)
        .all()
    )
    return {
        "status": "success",
        "module": "proposals",
        "count": len(rows),
        "proposals": [
            {
                "id": str(row.id),
                "file_name": row.file_name,
                "category": row.category,
                "file_type": row.file_type,
                "file_size_bytes": row.file_size_bytes,
                "path_masked": row.file_path_masked,
                "tags": row.tags or [],
                "status": "Indexada",
            }
            for row in rows
        ],
    }
