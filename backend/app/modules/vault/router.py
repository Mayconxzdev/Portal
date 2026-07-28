from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import get_current_user
from app.models.it import ITActivity, ITCredential
from app.models.user import User
from app.modules.it.service import ITService

router = APIRouter()


class VaultSecretCreate(BaseModel):
    name: str = Field(..., max_length=255)
    system_name: str
    username: str | None = None
    secret: str
    notes: str | None = None


class VaultSecretUpdate(BaseModel):
    name: str | None = None
    system_name: str | None = None
    username: str | None = None
    secret: str | None = None
    notes: str | None = None
    is_active: bool | None = None


def _secret_to_public(row: ITCredential) -> dict:
    return {
        "id": row.id,
        "name": row.title,
        "system_name": row.system_name,
        "secret_type": "PASSWORD",
        "username": row.username,
        "account_identifier": row.username,
        "status": "ACTIVE" if row.is_active else "DISABLED",
        "source": "IMPORTED_STAGING" if row.notes and "Importado" in row.notes else "PORTAL",
        "notes": row.notes,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "last_revealed_at": row.last_revealed_at,
        "has_secret": True,
    }


@router.get("/secrets")
def list_secrets(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = ITService.list_credentials(db, current_user)
    return {"status": "success", "secrets": [_secret_to_public(row) for row in rows]}


@router.get("/secrets/{secret_id}")
def get_secret(secret_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    row = db.query(ITCredential).filter(ITCredential.id == secret_id, ITCredential.is_active == True).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Segredo nao encontrado.")
    ITService.list_credentials(db, current_user)
    return _secret_to_public(row)


@router.post("/secrets", status_code=status.HTTP_201_CREATED)
def create_secret(payload: VaultSecretCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.modules.it.schemas import CredentialCreate

    row = ITService.create_credential(
        db,
        CredentialCreate(
            title=payload.name,
            system_name=payload.system_name,
            username=payload.username,
            secret=payload.secret,
            notes=payload.notes,
            visibility_level="IT_MANAGER",
        ),
        current_user,
    )
    return _secret_to_public(row)


@router.patch("/secrets/{secret_id}")
def update_secret(secret_id: int, payload: VaultSecretUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.modules.it.schemas import CredentialUpdate

    row = ITService.update_credential(
        db,
        secret_id,
        CredentialUpdate(
            title=payload.name,
            system_name=payload.system_name,
            username=payload.username,
            secret=payload.secret,
            notes=payload.notes,
            is_active=payload.is_active,
        ),
        current_user,
    )
    return _secret_to_public(row)


@router.post("/secrets/{secret_id}/reveal")
def reveal_secret(secret_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    revealed = ITService.reveal_credential(db, secret_id, current_user, copied=False)
    return {"id": revealed["id"], "secret": revealed["secret"]}


@router.post("/secrets/{secret_id}/disable")
def disable_secret(secret_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ITService.disable_credential(db, secret_id, current_user)


@router.get("/secrets/{secret_id}/audit")
def get_secret_audit(secret_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ITService.list_credentials(db, current_user)
    rows = (
        db.query(ITActivity)
        .filter(ITActivity.credential_id == secret_id)
        .order_by(ITActivity.created_at.desc())
        .limit(200)
        .all()
    )
    return {
        "status": "success",
        "audit": [
            {
                "id": row.id,
                "action": row.action,
                "actor_user_id": row.actor_user_id,
                "created_at": row.created_at,
                "metadata": row.metadata_json,
            }
            for row in rows
        ],
    }
