import hashlib
import os
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.models.kanban import File, FileModuleLink
from app.models.user import User


UPLOAD_DIR = Path(__file__).resolve().parents[4] / "storage" / "uploads"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {
    ".pdf", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".txt", ".csv",
    ".xls", ".xlsx", ".doc", ".docx", ".ppt", ".pptx", ".zip"
}
BLOCKED_EXTENSIONS = {".exe", ".bat", ".cmd", ".ps1", ".sh", ".js", ".msi", ".dll", ".scr", ".vbs"}


def validate_upload(upload: UploadFile, data: bytes) -> str:
    filename = upload.filename or "arquivo"
    extension = Path(filename).suffix.lower()
    if extension in BLOCKED_EXTENSIONS or extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tipo de arquivo nao permitido.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo acima do limite de 10 MB.")
    return extension


def save_upload_file(db: Session, upload: UploadFile, user: User, *, entity_type: str, entity_id: int) -> File:
    data = upload.file.read()
    extension = validate_upload(upload, data)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    stored_filename = f"{uuid.uuid4().hex}{extension}"
    path = UPLOAD_DIR / stored_filename
    with path.open("wb") as buffer:
        buffer.write(data)

    file_row = File(
        original_filename=os.path.basename(upload.filename or "arquivo"),
        stored_filename=stored_filename,
        content_type=upload.content_type or "application/octet-stream",
        size_bytes=len(data),
        storage_provider="local",
        storage_bucket="backend/storage/uploads",
        storage_key=stored_filename,
        checksum_sha256=hashlib.sha256(data).hexdigest(),
        uploaded_by_user_id=user.id,
    )
    db.add(file_row)
    db.flush()
    db.add(
        FileModuleLink(
            file_id=file_row.id,
            module_slug="it",
            entity_type=entity_type,
            entity_id=entity_id,
            created_by_user_id=user.id,
        )
    )
    return file_row
