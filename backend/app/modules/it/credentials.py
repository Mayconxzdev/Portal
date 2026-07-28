import base64
import hashlib

from cryptography.fernet import Fernet
from fastapi import HTTPException, status

from app.core.config import settings


def _derive_dev_key() -> bytes:
    digest = hashlib.sha256(settings.JWT_SECRET.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def get_fernet() -> Fernet:
    key = settings.IT_CREDENTIAL_VAULT_KEY
    if not key:
        if settings.ENVIRONMENT.lower() not in {"development", "testing", "test"}:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Chave do cofre de credenciais nao configurada.",
            )
        return Fernet(_derive_dev_key())
    try:
        return Fernet(key.encode("utf-8"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Chave do cofre de credenciais invalida.",
        ) from exc


def encrypt_secret(secret: str) -> str:
    return get_fernet().encrypt(secret.encode("utf-8")).decode("utf-8")


def decrypt_secret(secret_encrypted: str) -> str:
    return get_fernet().decrypt(secret_encrypted.encode("utf-8")).decode("utf-8")
