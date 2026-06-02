from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

import bcrypt
from jose import jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(subject: str, extra_claims: Optional[dict] = None) -> str:
    return create_signed_token(
        subject,
        token_type="access",
        expires=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        extra_claims=extra_claims,
    )


def create_refresh_token(subject: str) -> str:
    return create_signed_token(
        subject,
        token_type="refresh",
        expires=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def create_signed_token(
    subject: str,
    *,
    token_type: str,
    expires: timedelta,
    extra_claims: Optional[dict] = None,
) -> str:
    expire = datetime.now(timezone.utc) + expires
    payload = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": str(uuid4()),
        "type": token_type,
        **(extra_claims or {}),
    }
    return jwt.encode(payload, settings.SECRET_KEY, settings.ALGORITHM)


def decode_token(token: str) -> dict:
    """Giải mã JWT. Raise JWTError nếu token không hợp lệ hoặc hết hạn."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
