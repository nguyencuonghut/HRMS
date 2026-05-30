"""Security Headers Middleware (M2 — CSP Hardening).

CSP theo OWASP recommendations + thực tế PrimeVue 4.x constraints.

style-src cần 'unsafe-inline' vì PrimeVue v4 inject CSS variables + theme tokens
qua JavaScript — không thể dùng nonce-based approach mà không chuyển sang
PrimeVue Unstyled mode (thay đổi lớn, ngoài scope). XSS qua CSS injection ít
nguy hiểm hơn JS injection và đã được giảm thiểu bằng DOMPurify (C3).

script-src KHÔNG có 'unsafe-inline' → mọi script injection đều bị chặn.
"""
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

# ── CSP directives ────────────────────────────────────────────────────────────
# Mỗi directive tách riêng để dễ review và maintain

_CSP_DIRECTIVES = [
    # Fallback: chỉ cho phép cùng origin
    "default-src 'self'",

    # Scripts: KHÔNG có unsafe-inline → JS injection bị chặn hoàn toàn
    "script-src 'self'",

    # Styles: 'unsafe-inline' cần cho PrimeVue dynamic theming
    # NOTE: Không thể loại bỏ mà không migrate sang PrimeVue Unstyled mode
    "style-src 'self' 'unsafe-inline'",

    # Fonts: data: cho Base64 embedded fonts (PrimeIcons)
    "font-src 'self' data:",

    # Images: data: cho SVG/Base64, blob: cho object URLs (file preview)
    "img-src 'self' data: blob:",

    # Media: không cho phép audio/video
    "media-src 'none'",

    # Objects/plugins: Flash và plugins cũ đều bị chặn
    "object-src 'none'",

    # Embeds: không cho phép embed ngoài
    "frame-src 'none'",

    # Frames (cho bảo vệ clickjacking — bổ sung X-Frame-Options)
    "frame-ancestors 'none'",

    # Forms: chỉ submit về cùng origin
    "form-action 'self'",

    # Base tag: ngăn base tag injection (redirect tất cả links)
    "base-uri 'self'",

    # Web Workers
    "worker-src 'self'",

    # XHR / Fetch / WebSocket: chỉ đến cùng origin
    "connect-src 'self'",

    # Manifest (PWA)
    "manifest-src 'self'",
]

_CSP_HEADER = "; ".join(_CSP_DIRECTIVES)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)

        # ── Clickjacking & MIME sniffing ──────────────────────────────────────
        response.headers["X-Frame-Options"]        = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"

        # ── XSS heuristics (legacy browsers) ─────────────────────────────────
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # ── Referrer ──────────────────────────────────────────────────────────
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # ── Permissions ───────────────────────────────────────────────────────
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), "
            "payment=(), usb=(), magnetometer=(), gyroscope=()"
        )

        # ── Content Security Policy ───────────────────────────────────────────
        response.headers["Content-Security-Policy"] = _CSP_HEADER

        # ── Cross-Origin policies (isolation) ────────────────────────────────
        response.headers["Cross-Origin-Opener-Policy"]   = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"

        # ── HSTS: chỉ production (đã có HTTPS) ───────────────────────────────
        if settings.ENVIRONMENT == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        return response
