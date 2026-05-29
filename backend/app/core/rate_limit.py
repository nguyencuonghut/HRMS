from slowapi import Limiter

from app.core.config import settings


def _client_key(request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


limiter = Limiter(
    key_func=_client_key,
    storage_uri=settings.REDIS_URL,
)
