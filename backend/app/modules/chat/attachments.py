import os
import uuid
import hashlib
from pathlib import Path
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.models.kanban import File, FileModuleLink
from app.models.user import User

# Extensões bloqueadas por motivos de segurança corporativa
BLOCKED_EXTENSIONS = {
    ".exe", ".bat", ".cmd", ".ps1", ".js", ".vbs", ".sh", 
    ".scr", ".msi", ".dll", ".jar", ".cmd", ".com", ".pif", ".cpl"
}

# Extensões permitidas agrupadas por categorias de mídia
ALLOWED_IMAGES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
ALLOWED_VIDEOS = {".mp4", ".webm", ".mov"}
ALLOWED_AUDIOS = {".webm", ".mp3", ".wav", ".ogg", ".m4a"}
ALLOWED_DOCUMENTS = {".pdf", ".docx", ".xlsx", ".csv", ".txt"}

ALLOWED_EXTENSIONS = ALLOWED_IMAGES | ALLOWED_VIDEOS | ALLOWED_AUDIOS | ALLOWED_DOCUMENTS

# Limites de upload (10 MB por arquivo)
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

# Diretório padrão de upload
UPLOAD_DIR = Path(__file__).resolve().parents[4] / "storage" / "uploads"


class ChatAttachmentsManager:
    @staticmethod
    def validate_and_get_extension(upload: UploadFile, data: bytes) -> str:
        filename = upload.filename or "arquivo"
        extension = Path(filename).suffix.lower()
        
        if extension in BLOCKED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Tipo de arquivo bloqueado por motivos de seguranca."
            )
            
        if extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Extensão de arquivo nao permitida no portal."
            )
            
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Arquivo excede o limite permitido de 10 MB."
            )
            
        return extension

    @staticmethod
    def get_attachment_type(extension: str) -> str:
        if extension in ALLOWED_IMAGES:
            return "IMAGE" if extension != ".gif" else "GIF"
        elif extension in ALLOWED_VIDEOS:
            return "VIDEO"
        elif extension in ALLOWED_AUDIOS:
            return "AUDIO"
        elif extension in ALLOWED_DOCUMENTS:
            return "DOCUMENT"
        return "OTHER"

    @staticmethod
    def upload_attachment(
        db: Session,
        conversation_id: int,
        upload: UploadFile,
        user: User
    ) -> File:
        data = upload.file.read()
        extension = ChatAttachmentsManager.validate_and_get_extension(upload, data)
        
        # Garante a existência do diretório de storage
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        
        stored_filename = f"{uuid.uuid4().hex}{extension}"
        path = UPLOAD_DIR / stored_filename
        
        with path.open("wb") as buffer:
            buffer.write(data)
            
        checksum = hashlib.sha256(data).hexdigest()
        
        # Cria a entrada na tabela central de files
        file_row = File(
            original_filename=os.path.basename(upload.filename or "arquivo"),
            stored_filename=stored_filename,
            content_type=upload.content_type or "application/octet-stream",
            size_bytes=len(data),
            storage_provider="local",
            storage_bucket="backend/storage/uploads",
            storage_key=stored_filename,
            checksum_sha256=checksum,
            uploaded_by_user_id=user.id,
        )
        db.add(file_row)
        db.flush()
        
        # Associa o arquivo ao módulo de chat
        db.add(FileModuleLink(
            file_id=file_row.id,
            module_slug="chat",
            entity_type="chat_conversation",
            entity_id=conversation_id,
            created_by_user_id=user.id
        ))
        db.commit()
        
        return file_row
