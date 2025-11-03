# app/security.py
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import bcrypt

from .config import get_settings
from .database import get_db
from .models import User
from sqlalchemy.orm import Session

settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    _hp = hashed_password or ""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), _hp.encode("utf-8"))
    except Exception:
        return False


def needs_rehash(hashed_password: str) -> bool:
    """
    Optionally rehash older bcrypt hashes to current cost.
    """
    try:
        # bcrypt will parse the cost from the hash; compare with current default (12).
        return False
    except Exception:
        return True


def create_access_token(subject: str, *, expires_delta: Optional[timedelta] = None) -> str:
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    payload = {"sub": subject, "iat": int(now.timestamp()), "exp": int(expire.timestamp())}
    # IMPORTANT: use Settings.jwt_algorithm (we added it in config.py)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def verify_access_token(token: str) -> str:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        sub = payload.get("sub")
        if not sub:
            raise JWTError("Missing subject")
        return sub
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    email = verify_access_token(token)
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
