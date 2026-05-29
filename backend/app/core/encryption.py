from __future__ import annotations

import base64
import hashlib

import sqlalchemy as sa
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.types import TypeDecorator

from app.core.config import settings

_PREFIX = "enc:"


def _derived_key() -> bytes:
    if settings.ENCRYPTION_KEY.strip():
        return settings.ENCRYPTION_KEY.strip().encode()
    digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def _fernet() -> Fernet:
    return Fernet(_derived_key())


def encrypt(value: str | None) -> str | None:
    if value is None:
        return None
    if value.startswith(_PREFIX):
        return value
    token = _fernet().encrypt(value.encode()).decode()
    return f"{_PREFIX}{token}"


def decrypt(value: str | None) -> str | None:
    if value is None:
        return None
    if not value.startswith(_PREFIX):
        return value
    token = value[len(_PREFIX):]
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        return value


def hash_sensitive(value: str | None) -> str | None:
    if value is None:
        return None
    return hashlib.sha256(value.strip().encode()).hexdigest()


class EncryptedString(TypeDecorator):
    """Store encrypted text in DB, expose plaintext in Python."""

    impl = sa.Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return encrypt(value)

    def process_result_value(self, value, dialect):
        return decrypt(value)
