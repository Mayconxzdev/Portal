import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Union
from jose import jwt
from pwdlib import PasswordHash
from app.core.config import settings

from pwdlib.hashers.bcrypt import BcryptHasher

# Instância do PasswordHash moderno da biblioteca pwdlib configurado para bcrypt
password_hash = PasswordHash(hashers=[BcryptHasher()])

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica se uma senha em texto puro corresponde ao hash criptografado.
    """
    try:
        return password_hash.verify(plain_password, hashed_password)
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    """
    Gera um hash bcrypt seguro para a senha informada.
    """
    return password_hash.hash(password)

def create_access_token(
    subject: Union[str, Any],
    expires_delta: timedelta = None,
    session_id: str | None = None,
    token_id: str | None = None,
) -> str:
    """
    Gera um token de acesso JWT local assinado pelo backend.
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode = {"exp": expire, "sub": str(subject)}
    if session_id:
        to_encode["sid"] = session_id
    if token_id:
        to_encode["jti"] = token_id
    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def generate_token_identifier() -> str:
    return secrets.token_urlsafe(32)


def hash_token_identifier(token_identifier: str) -> str:
    return hashlib.sha256(token_identifier.encode("utf-8")).hexdigest()
