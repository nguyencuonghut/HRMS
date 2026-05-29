# Kế hoạch triển khai — 15.1. Bảo mật

**Phạm vi:** Encryption at rest · Rate limiting · Security headers · Password policy · CORS hardening · JWT blacklist · Account lockout  
**Phụ thuộc:** 1.2 RBAC ✅ · Auth system ✅ · MinIO ✅  
**Căn cứ nghiệp vụ:** FEATURES.md §15.1  
**Đặc điểm:** Yêu cầu phi chức năng — không thêm nghiệp vụ, chỉ tăng cường bảo mật hạ tầng đã có

---

## Trạng thái hiện tại

### Đã có (✅)

| Thành phần | File | Chi tiết |
|---|---|---|
| JWT Bearer Token | `app/core/security.py` | HS256, access 15 phút, refresh 7 ngày |
| Bcrypt password hash | `app/core/security.py` | bcrypt 4.0+, salt rounds 12 |
| RBAC đầy đủ | `app/models/auth.py`, `app/api/v1/deps.py` | Role → Permission → User |
| `require_permission()` | `app/api/v1/deps.py` | 516+ endpoints đã bảo vệ |
| Audit log toàn bộ | `app/models/auth.py`, `app/services/auth_service.py` | Ghi old_data/new_data, IP, user-agent |
| Refresh token endpoint | `app/api/v1/endpoints/auth.py` | `/api/v1/auth/refresh` |
| Password policy cơ bản | `app/schemas/user.py` | 8 ký tự, có chữ + số |
| CORS middleware | `app/main.py` | Cấu hình theo env |
| MinIO file proxy | `app/core/storage.py` | Không expose URL trực tiếp, filename UUID |
| Pydantic input validation | Toàn bộ schemas | Parameterized SQL (SQLModel) |

### Đã triển khai (✅)

> **Hoàn thành toàn bộ — 11/11 security tests pass.**

| Thành phần | File | Chi tiết |
|---|---|---|
| Rate limiting login 5/phút/IP | `app/core/rate_limit.py`, `auth.py` | slowapi + X-Forwarded-For |
| Account lockout sau 5 lần sai | `app/services/auth_service.py` | Redis, khóa 30 phút |
| Mã hóa dữ liệu nhạy cảm | `app/core/encryption.py`, migration 0049 | Fernet + `EncryptedString` TypeDecorator |
| Security HTTP headers | `app/middleware/security_headers.py` | X-Frame-Options, CSP, HSTS, nosniff |
| JWT blacklist + logout | `app/api/v1/endpoints/auth.py` | `POST /auth/logout`, Redis TTL |
| CORS hardening | `app/main.py` | Restrict methods + headers |
| Password policy nâng cao | `app/schemas/user.py` | Ký tự đặc biệt + common check |
| MinIO env-aware bucket | `app/core/config.py` | `minio_bucket_name` property |
| `ENCRYPTION_KEY`, `ENVIRONMENT` config | `app/core/config.py` | Từ .env |

### Một phần (⚠️)

| Thành phần | Vấn đề | Cần làm |
|---|---|---|
| SECRET_KEY | Default value không an toàn trong config | Enforce non-default trong prod |
| CORS | `allow_methods=["*"]`, `allow_headers=["*"]` quá permissive | Restrict về các method/header cụ thể |
| Password policy | Không yêu cầu ký tự đặc biệt, không chặn password phổ biến | Tăng cường validator |
| MinIO bucket naming | Không phân biệt dev/staging/prod | Thêm env suffix |

---

## Phạm vi Plan 15.1

### Trong phạm vi (theo ưu tiên)

1. **Rate limiting** — bảo vệ endpoint login + API khỏi brute-force
2. **Mã hóa dữ liệu nhạy cảm** — CCCD, hộ chiếu, MST, tài khoản ngân hàng
3. **Security HTTP headers** — HSTS, X-Frame-Options, X-Content-Type-Options, CSP
4. **Account lockout** — khóa tài khoản sau N lần nhập sai
5. **JWT token blacklist** — logout thực sự invalidate token
6. **CORS hardening** — restrict method/header
7. **Password policy nâng cao** — ký tự đặc biệt, common password check
8. **MinIO env-aware** — tách bucket theo môi trường để giảm rủi ro vận hành chéo môi trường

### Ngoài phạm vi

- **SSO / OIDC / SAML** — bỏ qua theo quyết định dự án; có thể bổ sung sau khi có provider cụ thể
- MFA/TOTP — làm sau khi có yêu cầu rõ ràng
- Penetration testing / vulnerability scanning — giao security team riêng
- Database-level encryption (TDE) — phụ thuộc hạ tầng PostgreSQL
- VPN/network-level security — thuộc DevOps
- SIEM / centralized log monitoring — Phase sau

---

## Chi tiết kỹ thuật từng tính năng

### 1. Rate Limiting (Slice 1 — Critical)

**Thư viện:** `slowapi` (Redis backend qua `limits` library)

**Cài đặt:**
```python
# requirements.txt
slowapi>=0.1.9
limits[redis]>=3.6
```

**Config:**
```python
# app/core/rate_limit.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.REDIS_URL,
)
```

**Áp dụng:**
```python
# app/api/v1/endpoints/auth.py
@router.post("/login")
@limiter.limit("5/minute")        # Max 5 lần/phút/IP
async def login(request: Request, ...): ...

@router.post("/refresh")
@limiter.limit("20/hour")
async def refresh(request: Request, ...): ...
```

**Global handler (main.py):**
```python
from slowapi.errors import RateLimitExceeded
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
```

**Response khi vượt limit:** `429 Too Many Requests` với header `Retry-After`.

---

### 2. Mã hóa dữ liệu nhạy cảm (Slice 1 — Critical)

**Thư viện:** `cryptography` (Fernet symmetric encryption, đã có trong Python ecosystem)

**Cài đặt:**
```python
# requirements.txt
cryptography>=42.0.0
```

**Config:**
```python
# app/core/config.py — thêm
ENCRYPTION_KEY: str = ""  # Fernet key (32 bytes URL-safe base64)
```

**Helper module:**
```python
# app/core/encryption.py
from cryptography.fernet import Fernet
from app.core.config import settings

def _fernet() -> Fernet:
    if not settings.ENCRYPTION_KEY:
        raise RuntimeError("ENCRYPTION_KEY chưa được cấu hình")
    return Fernet(settings.ENCRYPTION_KEY.encode())

def encrypt(value: str | None) -> str | None:
    if value is None:
        return None
    return _fernet().encrypt(value.encode()).decode()

def decrypt(value: str | None) -> str | None:
    if value is None:
        return None
    return _fernet().decrypt(value.encode()).decode()
```

**Các trường cần mã hóa:**

| Model | Field | Bảng |
|---|---|---|
| `Employee` | `id_number` (CCCD/CMND) | `employees` |
| `Employee` | `passport_number` | `employees` |
| `Employee` | `personal_tax_code` | `employees` |
| `EmployeeBankAccount` | `account_number` | `employee_bank_accounts` |

**Migration strategy:**
1. Tạo migration `0049_encrypt_sensitive_fields.py`
2. Data migration script: đọc từng row, encrypt, ghi lại
3. Thêm prefix `enc:` để phân biệt encrypted vs plaintext trong quá trình migration
4. Sau khi verify xong: xóa prefix, set NOT NULL encrypted

**Lưu ý:** Tìm kiếm theo CCCD sau mã hóa cần hash index riêng (SHA-256 hash của value để tìm kiếm exact match, không decrypt toàn bộ):

```python
# app/models/employee.py
id_number_hash: str = Field(...)  # SHA256(id_number) — dùng để lookup
id_number_enc: str = Field(...)   # Fernet(id_number) — dùng để display
```

---

### 3. Security HTTP Headers (Slice 2)

**Middleware tự viết (không cần thư viện):**

```python
# app/middleware/security_headers.py
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        # HSTS chỉ bật khi production HTTPS
        if settings.ENVIRONMENT == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response
```

**Đăng ký trong main.py:**
```python
from app.middleware.security_headers import SecurityHeadersMiddleware
app.add_middleware(SecurityHeadersMiddleware)
```

---

### 4. Account Lockout (Slice 2)

Dùng Redis để track failed attempts:

```python
# app/services/auth_service.py — thêm

MAX_FAILED = 5
LOCKOUT_SECONDS = 30 * 60  # 30 phút

async def check_login_allowed(email: str) -> None:
    key = f"login_failed:{email}"
    count = await redis.get(key)
    if count and int(count) >= MAX_FAILED:
        raise HTTPException(423, "Tài khoản tạm khóa 30 phút do quá nhiều lần đăng nhập sai")

async def record_failed_login(email: str) -> None:
    key = f"login_failed:{email}"
    await redis.incr(key)
    await redis.expire(key, LOCKOUT_SECONDS)

async def clear_failed_login(email: str) -> None:
    await redis.delete(f"login_failed:{email}")
```

Gọi trong login endpoint:
1. `await check_login_allowed(email)` → trước khi verify password
2. Nếu sai password: `await record_failed_login(email)`
3. Nếu đúng: `await clear_failed_login(email)`

---

### 5. JWT Token Blacklist (Slice 2)

Khi logout, lưu JTI (JWT ID) vào Redis với TTL = thời gian còn lại của token:

```python
# app/core/security.py — thêm jti vào payload
import uuid

def create_access_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "jti": str(uuid.uuid4()),   # ← thêm
        "exp": ...,
        "iat": ...,
    }
    ...

async def blacklist_token(jti: str, expires_at: datetime) -> None:
    ttl = int((expires_at - datetime.utcnow()).total_seconds())
    if ttl > 0:
        await redis.setex(f"token:blacklist:{jti}", ttl, "1")

async def is_token_blacklisted(jti: str) -> bool:
    return await redis.exists(f"token:blacklist:{jti}") > 0
```

Kiểm tra trong `get_current_user()` dep.

---

### 6. CORS Hardening (Slice 2)

```python
# app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    expose_headers=["Content-Disposition"],
    max_age=600,
)
```

---

### 7. Password Policy nâng cao (Slice 2)

```python
# app/schemas/user.py — cập nhật _validate_password()

COMMON_PASSWORDS = {"123456", "password", "qwerty", "abc123", "111111", ...}

@field_validator("password")
def _validate_password(cls, v: str) -> str:
    if len(v) < 8:
        raise ValueError("Mật khẩu phải có ít nhất 8 ký tự")
    if not any(c.isalpha() for c in v):
        raise ValueError("Mật khẩu phải có ít nhất 1 chữ cái")
    if not any(c.isdigit() for c in v):
        raise ValueError("Mật khẩu phải có ít nhất 1 chữ số")
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
        raise ValueError("Mật khẩu phải có ít nhất 1 ký tự đặc biệt")
    if v.lower() in COMMON_PASSWORDS:
        raise ValueError("Mật khẩu quá phổ biến, vui lòng chọn mật khẩu khác")
    return v
```

---

### 8. MinIO Bucket env-aware (Slice 3)

```python
# app/core/config.py
ENVIRONMENT: str = "development"  # development | staging | production
MINIO_BUCKET: str = ""  # Để trống, tính động

@property
def minio_bucket_name(self) -> str:
    env_suffix = {"development": "dev", "staging": "stg", "production": "prod"}
    suffix = env_suffix.get(self.ENVIRONMENT, "dev")
    return f"hrms-attachments-{suffix}"
```

---

## API Endpoints mới

```
POST /api/v1/auth/logout          → blacklist current token (yêu cầu auth)
```

---

## Cấu trúc file

```
backend/app/
├── core/
│   ├── encryption.py           ← NEW — Fernet encrypt/decrypt helpers
│   ├── rate_limit.py           ← NEW — slowapi Limiter instance
│   └── config.py               ← UPDATE — ENCRYPTION_KEY, ENVIRONMENT
├── middleware/
│   └── security_headers.py     ← NEW — HTTP security headers middleware
├── services/
│   └── auth_service.py         ← UPDATE — account lockout, token blacklist
├── schemas/
│   └── user.py                 ← UPDATE — password policy nâng cao
├── api/v1/endpoints/
│   └── auth.py                 ← UPDATE — rate limit decorators, logout
├── main.py                     ← UPDATE — middleware registration, CORS hardening
└── alembic/versions/
    └── 0049_encrypt_sensitive_fields.py  ← NEW — migration + data encryption
```

---

## Kế hoạch theo Slice

### Slice 1 — Critical: Rate limiting + Encryption + Account lockout

**Mục tiêu:** Vá 3 lỗ hổng critical trước khi lên production.

**Việc cần làm:**
1. Thêm `slowapi` + `cryptography` vào `requirements.txt`
2. Tạo `app/core/encryption.py` với `encrypt()`/`decrypt()`
3. Tạo `app/core/rate_limit.py`
4. Áp dụng `@limiter.limit("5/minute")` cho login + refresh
5. Tạo migration `0049_encrypt_sensitive_fields.py`:
   - Thêm cột `id_number_enc`, `id_number_hash` vào `employees`
   - Script data migration (đọc → encrypt → ghi)
   - Cập nhật service: đọc/ghi qua encrypt/decrypt
6. Implement account lockout trong `auth_service.py`
7. Cấu hình `ENVIRONMENT` và `ENCRYPTION_KEY` trong `.env`

**Tests:**
- `test_login_rate_limit` — quá 5 lần → 429
- `test_account_lockout_after_5_fails` — verify 423
- `test_encryption_roundtrip` — encrypt → decrypt = original
- `test_encrypted_field_not_plaintext_in_db` — kiểm tra DB value khác plaintext

**Verify:** `pytest tests/test_security.py -v` pass.

---

### Slice 2 — High: Security headers + JWT blacklist + CORS + Password policy

**Mục tiêu:** Tăng cường bảo mật response và session management.

**Việc cần làm:**
1. Tạo `app/middleware/security_headers.py`
2. Đăng ký middleware trong `main.py`
3. Thêm `jti` claim vào JWT creation
4. Implement token blacklist qua Redis
5. Thêm endpoint `POST /auth/logout`
6. CORS: restrict methods + headers
7. Password validator: ký tự đặc biệt + common check

**Tests:**
- `test_security_headers_present` — kiểm tra X-Frame-Options, HSTS, v.v.
- `test_logout_blacklists_token` — dùng token đã logout → 401
- `test_password_requires_special_char` — "Abc12345" → lỗi
- `test_cors_restricts_methods` — verify OPTIONS response

**Verify:** `pytest tests/test_security.py -v` pass toàn bộ.

---

### Slice 3 — Medium: MinIO env-aware

**Việc cần làm:**
1. Cập nhật `MINIO_BUCKET` → dùng `minio_bucket_name` property
2. Cập nhật Docker Compose các env để set `ENVIRONMENT=development`

**Verify:** App khởi động bình thường, bucket MinIO được tách đúng theo môi trường.

---

## Rủi ro & Cách xử lý

| Rủi ro | Cách xử lý |
|---|---|
| Data migration encrypt làm chậm DB (100k rows) | Chạy migration batch (1000 rows/batch), ngoài giờ cao điểm |
| ENCRYPTION_KEY bị mất → không decrypt được | Backup key riêng biệt ngoài DB; dùng secret manager (Vault/AWS SSM) |
| Rate limit chặn người dùng thật (shared IP corporate) | Tăng limit cho /api/v1 general, chỉ strict trên /auth/login |
| Fernet key rotation (đổi key định kỳ) | Decrypt với old key → encrypt với new key → cần rotation script |

---

## Checklist trước khi lên production

### Critical (phải có trước go-live)
- [x] `ENCRYPTION_KEY` được set trong `.env` production (không phải default)
- [x] `SECRET_KEY` được set ngẫu nhiên (không phải default `"change-this-secret-key..."`)
- [x] Rate limiting hoạt động: login giới hạn 5/phút/IP
- [x] Account lockout hoạt động sau 5 lần sai
- [x] CCCD, MST, tài khoản ngân hàng đã được mã hóa trong DB (migration 0049)
- [x] Security headers trả về đúng

### High (nên có trước go-live)
- [x] Logout thực sự invalidate token (JWT blacklist + `/auth/logout`)
- [x] CORS chỉ cho phép đúng origin production
- [x] MinIO bucket dùng env-aware naming
- [x] Password policy yêu cầu ký tự đặc biệt

### Không áp dụng (đã loại khỏi phạm vi)
- SSO / OIDC — bỏ qua theo quyết định dự án

### Medium (làm sau go-live nếu cần)
- [ ] Audit log alert khi nhiều lần failed login
- [ ] JWT algorithm cân nhắc chuyển sang RS256 nếu multi-service
