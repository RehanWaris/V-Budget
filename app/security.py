from datetime import datetime, timedelta
from typing import Optional

import base64
import hashlib
import secrets

import bcrypt
from jose import JWTError, jwt

from .config import get_settings

from jose import jwt, JWTError
from passlib.context import CryptContext

from .config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
settings = get_settings()


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = {"sub": subject}
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def verify_access_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload.get("sub")
    except JWTError:
        return None


def get_password_hash(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return base64.b64encode(salt + derived).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password that may be stored as PBKDF2 (new) or bcrypt (legacy)."""
    if hashed_password.startswith("$2"):
        try:
            return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
        except ValueError:
            return False

    try:
        decoded = base64.b64decode(hashed_password.encode("utf-8"), validate=True)
        salt, stored_hash = decoded[:16], decoded[16:]
        candidate = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, 100_000)
        return secrets.compare_digest(candidate, stored_hash)
    except (ValueError, TypeError):
        return False


def needs_rehash(hashed_password: str) -> bool:
    """Detect legacy bcrypt hashes that should be replaced with PBKDF2."""
    return hashed_password.startswith("$2")
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
