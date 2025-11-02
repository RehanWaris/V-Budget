# app/security.py
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import get_settings

settings = get_settings()

# -----------------------------------------------------------------------------
# Password hashing
# -----------------------------------------------------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def needs_rehash(hashed_password: str) -> bool:
    """Return True if the stored hash should be rehashed with current policy."""
    return pwd_context.needs_update(hashed_password)

# -----------------------------------------------------------------------------
# JWT helpers
# -----------------------------------------------------------------------------
ALGORITHM = "HS256"
SECRET_KEY = settings.secret_key  # ensure this exists in your config/.env

def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    """
    subject: usually the user's email
    """
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    to_encode = {"sub": subject, "iat": int(now.timestamp()), "exp": int(expire.timestamp())}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_access_token(token: str) -> str:
    """
    Returns the subject (email) if token is valid, else raises JWTError.
    """
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    subject = payload.get("sub")
    if not subject:
        raise JWTError("Token missing subject")
    return subject
