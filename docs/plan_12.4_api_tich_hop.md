# Kế hoạch triển khai — 12.4. API tích hợp

**Phạm vi:** API Key auth · Quản lý client key · Rate limiting · API Documentation  
**Phụ thuộc:** 1.2 RBAC ✅ · FastAPI (OpenAPI tự sinh ✅)  
**Căn cứ nghiệp vụ:** FEATURES.md §12.4  
**Đặc điểm:** FastAPI đã có Swagger/ReDoc; plan này thêm API Key auth cho external clients và rate limiting

---

## Trạng thái hiện tại

| Thành phần | Trạng thái | Ghi chú |
|---|---|---|
| REST API (FastAPI) | ✅ Hoàn thành | Toàn bộ modules |
| Swagger UI (`/docs`) | ✅ Auto-generated | FastAPI tự sinh từ route decorators |
| ReDoc (`/redoc`) | ✅ Auto-generated | |
| JWT Bearer Token auth (user login) | ✅ Hoàn thành | `require_permission()` pattern |
| API Key auth (external clients) | ❌ Chưa có | |
| External API key management | ❌ Chưa có | |
| Rate limiting | ❌ Chưa có | |
| Webhook support | ❌ Chưa có | |
| API audit log cho external clients | ❌ Chưa có | |

---

## Phạm vi 12.4

### Trong phạm vi

1. **API Key authentication** — external systems dùng `X-API-Key: <key>` header thay vì JWT
2. **API Key management** — HR Admin tạo/thu hồi key, đặt tên, scope permissions
3. **Rate limiting** — giới hạn số request/phút per API key (slowapi + Redis)
4. **API Documentation** — tùy chỉnh OpenAPI UI với thông tin đơn vị, version, contact
5. **External API audit log** — log mọi request từ API key (endpoint, status, time)
6. **Read-only scope mặc định** — API keys chỉ có quyền đọc (GET), không có quyền ghi trừ khi được cấp thêm

### Ngoài phạm vi

- Webhook outbound (push event khi data thay đổi)
- OAuth2 Authorization Code flow (cho app bên ngoài đăng nhập thay mặt user)
- SDK client libraries
- API versioning tự động (v2, v3)
- GraphQL endpoint

---

## Database Migration

### Bảng `api_clients`

```sql
CREATE TABLE api_clients (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,           -- "Phần mềm kế toán ABC"
    description     TEXT,
    api_key         VARCHAR(64)  NOT NULL UNIQUE,    -- SHA-256 hash của raw key
    key_prefix      VARCHAR(10)  NOT NULL,           -- 8 ký tự đầu raw key (hiển thị)
    scopes          TEXT[]       NOT NULL DEFAULT '{}', -- ['employees:read', 'leaves:read']
    is_active       BOOLEAN      NOT NULL DEFAULT true,
    rate_limit_rpm  INTEGER      NOT NULL DEFAULT 60, -- requests per minute
    created_by      INTEGER      REFERENCES users(id) ON DELETE SET NULL,
    last_used_at    TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ,                     -- null = không hết hạn
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_api_clients_api_key    ON api_clients(api_key);
CREATE INDEX ix_api_clients_is_active  ON api_clients(is_active);
```

**Lưu ý bảo mật:** Chỉ lưu hash của key, không lưu raw key. Raw key chỉ hiển thị một lần khi tạo.

### Bảng `api_audit_logs`

```sql
CREATE TABLE api_audit_logs (
    id              BIGSERIAL PRIMARY KEY,
    client_id       INTEGER      REFERENCES api_clients(id) ON DELETE SET NULL,
    method          VARCHAR(10)  NOT NULL,            -- GET, POST, ...
    path            VARCHAR(500) NOT NULL,
    status_code     SMALLINT,
    response_time_ms INTEGER,
    ip_address      VARCHAR(45),
    user_agent      VARCHAR(500),
    requested_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Partition by month hoặc chỉ giữ 90 ngày gần nhất
CREATE INDEX ix_api_audit_client_id  ON api_audit_logs(client_id);
CREATE INDEX ix_api_audit_requested  ON api_audit_logs(requested_at DESC);
```

---

## API Key — Thiết kế bảo mật

### Format raw key

```
hrms_live_<32 ký tự random hex>
Ví dụ: hrms_live_a3f2b1c8d9e0f1a2b3c4d5e6f7890abc
```

- Prefix `hrms_live_` giúp dễ nhận dạng trong log
- 32 hex chars = 128 bits entropy — đủ an toàn
- `key_prefix` lưu 8 ký tự đầu (sau prefix) để hiển thị trong UI
- `api_key` column lưu `sha256(raw_key)` — không thể reverse

### Tạo key (service)

```python
import secrets, hashlib

def generate_api_key() -> tuple[str, str, str]:
    """Returns (raw_key, key_hash, key_prefix)."""
    raw = "hrms_live_" + secrets.token_hex(16)
    key_hash = hashlib.sha256(raw.encode()).hexdigest()
    key_prefix = raw[10:18]   # 8 ký tự sau prefix 'hrms_live_'
    return raw, key_hash, key_prefix
```

### Xác thực request từ external client

```python
# backend/app/api/v1/deps.py — thêm dependency mới

async def get_api_client(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> ApiClient:
    """Dependency: xác thực X-API-Key header."""
    raw_key = request.headers.get("X-API-Key", "")
    if not raw_key:
        raise HTTPException(status_code=401, detail="API key required")

    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    client = await session.execute(
        select(ApiClient)
        .where(ApiClient.api_key == key_hash, ApiClient.is_active == True)
    )
    client = client.scalar_one_or_none()

    if not client:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")
    if client.expires_at and client.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="API key expired")

    # Update last_used_at (async, không block)
    client.last_used_at = datetime.utcnow()
    await session.commit()
    return client

def require_scope(scope: str):
    """Dependency: kiểm tra API client có scope cần thiết."""
    async def _dep(client: ApiClient = Depends(get_api_client)) -> ApiClient:
        if scope not in client.scopes:
            raise HTTPException(status_code=403, detail=f"Scope '{scope}' required")
        return client
    return Depends(_dep)
```

---

## Rate Limiting

### Dùng `slowapi` (đã có pattern trong FastAPI ecosystem)

```python
# requirements.txt
slowapi>=0.1.9
```

```python
# backend/app/core/rate_limit.py
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

def get_api_key_for_rate_limit(request: Request) -> str:
    """Key function: dùng api_key hash làm identity thay vì IP."""
    raw = request.headers.get("X-API-Key", get_remote_address(request))
    return hashlib.sha256(raw.encode()).hexdigest()[:16]

api_key_limiter = Limiter(key_func=get_api_key_for_rate_limit)
```

```python
# Áp dụng trên external endpoints
@router.get("/employees")
@api_key_limiter.limit("60/minute")    # default; client.rate_limit_rpm override
async def list_employees_external(
    client: ApiClient = Depends(get_api_client),
    ...
):
    ...
```

---

## External API Endpoints

### Prefix `/api/v1/external` — chỉ dành cho API key clients

Tất cả endpoints này **không dùng JWT**, chỉ dùng `X-API-Key`:

```
GET /external/employees
    ?page=1&page_size=50&status=official&department_id=<int>
    Scope: employees:read
    → PaginatedEmployeeList (id, code, name, department, job_title, status)

GET /external/employees/{id}
    Scope: employees:read
    → EmployeeBasicInfo

GET /external/leave-records
    ?employee_id=<int>&year=2026&status=active
    Scope: leaves:read
    → PaginatedLeaveList

GET /external/departments
    Scope: employees:read
    → DepartmentList (flat, có parent_id)

GET /external/org-chart
    Scope: employees:read
    → OrgChartTree (headcount theo phòng ban)
```

**Lý do tách prefix `/external`:**
- Dễ áp dụng rate limiting riêng
- Dễ monitor traffic external
- Audit log riêng
- Scopes phân biệt rõ với internal endpoints

---

## API Key Management — Endpoints

### Prefix `/api/v1/api-keys` — chỉ Admin và HR Manager

```
GET  /api-keys                  → Danh sách keys (không show raw key)
POST /api-keys                  → Tạo key mới → trả raw_key MỘT LẦN DUY NHẤT
     Body: { name, description, scopes[], rate_limit_rpm, expires_at }
     Response: { id, name, raw_key (lần này thôi), key_prefix, scopes, ... }

GET  /api-keys/{id}             → Chi tiết key (không show raw)
PUT  /api-keys/{id}             → Cập nhật (name, description, scopes, rate_limit_rpm)
DELETE /api-keys/{id}           → Thu hồi (soft delete: is_active=False)

GET  /api-keys/{id}/audit-logs  → Lịch sử request của key này
     ?from=...&to=...&status=...
     → PaginatedAuditLog
```

### Permission: `api_keys:manage` (chỉ HR Manager, Admin)

---

## OpenAPI / Swagger Customization

### Cấu hình trong `app/main.py`

```python
from fastapi import FastAPI

app = FastAPI(
    title="Hồng Hà HRMS API",
    version="2.0.0",
    description="""
## Hệ thống Quản lý Nhân sự Hồng Hà

**Base URL:** `https://hrms.hongha.vn/api/v1`

### Xác thực

Hỗ trợ 2 phương thức:
- **Bearer Token:** Cho người dùng nội bộ (đăng nhập qua `/auth/login`)
- **API Key:** Cho hệ thống tích hợp (`X-API-Key: hrms_live_...`)

### Rate Limiting
- Internal users: không giới hạn
- API Keys: mặc định 60 req/phút (có thể cấu hình riêng)

### Liên hệ
- Email: it@hongha.vn
- Hỗ trợ: Phòng IT Hồng Hà
""",
    contact={"name": "Phòng IT Hồng Hà", "email": "it@hongha.vn"},
    license_info={"name": "Nội bộ — Không phân phối"},
)
```

### Security Scheme cho Swagger

```python
from fastapi.security import HTTPBearer, APIKeyHeader

http_bearer = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
```

---

## Middleware — API Audit Log

```python
# backend/app/middleware/api_audit.py

class ApiAuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Chỉ log external requests
        if not request.url.path.startswith("/api/v1/external"):
            return await call_next(request)

        raw_key = request.headers.get("X-API-Key", "")
        start = time.monotonic()
        response = await call_next(request)
        elapsed_ms = int((time.monotonic() - start) * 1000)

        # Async log (fire-and-forget, không block response)
        asyncio.create_task(_log_request(
            key_hash=hashlib.sha256(raw_key.encode()).hexdigest() if raw_key else None,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            response_time_ms=elapsed_ms,
            ip=request.client.host if request.client else None,
        ))
        return response
```

---

## Frontend Design — Quản lý API Keys

### Route

```
/settings/api-keys   →   ApiKeyManagementView.vue
```

### Layout

```
┌─ API Keys ───────────────────────────────────────────────────────────┐
│ Quản lý API Keys cho hệ thống tích hợp    [+ Tạo API Key mới]       │
├──────────────────────────────────────────────────────────────────────┤
│ DataTable:                                                           │
│ Tên | Prefix | Scopes | Rate limit | Lần dùng cuối | Hết hạn | ⋮    │
│ ─────────────────────────────────────────────────────────────────── │
│ Phần mềm Kế toán ABC │ a3f2b1c8│ employees:read │ 60/min│ hôm nay │[⋮]│
│   → menu: [Xem log] [Sửa] [Thu hồi]                                │
└──────────────────────────────────────────────────────────────────────┘

┌─ Dialog: Tạo API Key mới ────────────────────────────────────────────┐
│ Tên hệ thống: [_________________________]                           │
│ Mô tả: [_________________________]                                   │
│ Quyền truy cập (scopes):                                            │
│   [✓] employees:read  [  ] leaves:read  [  ] contracts:read         │
│   [  ] insurance:read                                                │
│ Rate limit: [60] req/phút                                           │
│ Hết hạn: [Không hết hạn ▼]                                         │
│                                           [Hủy] [Tạo API Key]       │
└──────────────────────────────────────────────────────────────────────┘

┌─ Dialog: Raw Key (chỉ hiển thị 1 lần) ──────────────────────────────┐
│ ⚠️ Lưu lại key này ngay — sẽ không hiển thị lại!                   │
│                                                                      │
│ hrms_live_a3f2b1c8d9e0f1a2b3c4d5e6f7890abc  [📋 Copy]              │
│                                                                      │
│                                              [Đã lưu, đóng]         │
└──────────────────────────────────────────────────────────────────────┘
```

**PrimeVue components:** `DataTable`, `Dialog`, `MultiSelect` (scopes), `InputNumber`, `Tag`, `Message`

---

## Service `apiKeyService.ts` (file mới)

```typescript
const BASE = '/api-keys'

export default {
  listKeys: () => api.get<ApiKeyRead[]>(BASE),
  createKey: (data: CreateApiKeyDto) => api.post<CreateApiKeyResponse>(BASE, data),
  updateKey: (id: number, data: UpdateApiKeyDto) => api.put<ApiKeyRead>(`${BASE}/${id}`, data),
  revokeKey: (id: number) => api.delete(`${BASE}/${id}`),
  getAuditLogs: (id: number, params: AuditLogParams) =>
    api.get<PaginatedAuditLog>(`${BASE}/${id}/audit-logs`, { params }),
}
```

---

## Cấu trúc file

```
backend/app/
├── models/
│   └── api_client.py                       ← NEW (ApiClient, ApiAuditLog)
├── schemas/
│   └── api_client.py                       ← NEW (ApiKeyRead, CreateApiKeyDto, ...)
├── services/
│   └── api_key_service.py                  ← NEW (generate, validate, audit)
├── api/v1/endpoints/
│   ├── api_keys.py                         ← NEW (management CRUD)
│   └── external_api.py                     ← NEW (external read-only endpoints)
├── api/v1/deps.py                          ← UPDATE (get_api_client, require_scope)
├── api/v1/router.py                        ← UPDATE (đăng ký /api-keys, /external)
├── middleware/
│   └── api_audit.py                        ← NEW (ApiAuditMiddleware)
├── core/
│   └── rate_limit.py                       ← NEW (slowapi config)
└── alembic/versions/
    └── xxxx_add_api_clients.py             ← NEW

frontend/src/
├── services/
│   └── apiKeyService.ts                    ← NEW
├── views/settings/
│   └── ApiKeyManagementView.vue            ← NEW
└── router/index.ts                         ← UPDATE
```

---

## Kế hoạch theo Slice

### Slice 1 — Backend: Models + API Key Auth + External Endpoints

**Việc cần làm:**
1. Migration `xxxx_add_api_clients.py` — 2 bảng
2. Tạo `api_client.py` model
3. Tạo `api_key_service.py`:
   - `generate_api_key()` → (raw_key, hash, prefix)
   - `validate_api_key(raw_key, session)` → ApiClient | None
4. Cập nhật `deps.py` — `get_api_client()`, `require_scope()`
5. Tạo `external_api.py` — 5 read-only endpoints dùng `require_scope`
6. Cài `slowapi` — rate limiting 60/min per key
7. Tests:
   - `test_valid_api_key_accepted`
   - `test_invalid_api_key_rejected_401`
   - `test_revoked_key_rejected_401`
   - `test_expired_key_rejected_401`
   - `test_wrong_scope_rejected_403`
   - `test_rate_limit_exceeded_429` (mock Redis/limiter)
   - `test_external_employees_returns_data`

**Verify:** `pytest tests/test_api_keys.py -v` pass.

---

### Slice 2 — Backend: Key Management CRUD + Audit Log

**Việc cần làm:**
1. Tạo schemas `api_client.py` — `ApiKeyRead`, `CreateApiKeyDto`, `CreateApiKeyResponse`, etc.
2. Tạo `api_keys.py` endpoint — CRUD + audit logs
3. Thêm `ApiAuditMiddleware` vào `app/main.py`
4. Thêm vào `router.py`
5. Tests:
   - `test_create_key_returns_raw_key_once`
   - `test_list_keys_no_raw_key_in_response`
   - `test_revoke_key_deactivates`
   - `test_audit_log_records_external_request`
   - `test_non_admin_cannot_manage_keys_403`

**Verify:** `pytest tests/test_api_key_management.py -v` pass.

---

### Slice 3 — OpenAPI Customization + Frontend

**Việc cần làm:**
1. Cập nhật `app/main.py` — title, description, version, contact
2. Thêm `APIKeyHeader` security scheme vào Swagger
3. Kiểm tra `/docs` và `/redoc` render đúng
4. Tạo `apiKeyService.ts`
5. Tạo `ApiKeyManagementView.vue`:
   - DataTable keys + action menu
   - Dialog tạo key (tên, scopes checkbox, rate limit)
   - Dialog hiển thị raw key (copy-to-clipboard, 1 lần)
   - Dialog xem audit log
6. Cập nhật router + AppMenu (Settings)
7. `vue-tsc --noEmit` clean

**Verify:**
- Tạo key → dialog hiển thị raw key → đóng → key hiển thị trong list với prefix
- Dùng raw key với curl → `/api/v1/external/employees` → 200
- Thu hồi key → cùng raw key → 401

---

## Rủi ro & Cách xử lý

| Rủi ro | Cách xử lý |
|---|---|
| Raw key bị lộ trong log | Log chỉ ghi `key_prefix`, không bao giờ ghi raw key; middleware filter header `X-API-Key` trước khi log |
| `slowapi` cần Redis — dev không có | Fallback: in-memory limiter khi `REDIS_URL` không có |
| Audit log table tăng nhanh | Celery beat task cleanup logs > 90 ngày (thêm vào schedule) |
| Hash collision (SHA-256) | Probability negligible — 2^-128; không cần xử lý thêm |
| External client dùng JWT nhầm endpoint | Middleware kiểm tra: nếu path `/external/` và có `Authorization: Bearer` → gợi ý dùng API Key |
| Scope `employees:read` quá rộng cho một số client | Có thể thêm scope chi tiết hơn sau: `employees:list_only`, `employees:profile` — dễ mở rộng |

---

## Checklist

### Backend
- [ ] Migration 2 bảng chạy không lỗi
- [ ] `pytest tests/test_api_keys.py tests/test_api_key_management.py` pass
- [ ] Rate limiting trả 429 đúng khi vượt limit
- [ ] Audit log ghi mỗi request external
- [ ] Raw key KHÔNG xuất hiện ở bất kỳ endpoint GET nào sau khi tạo

### Frontend
- [ ] `vue-tsc --noEmit` clean
- [ ] Dialog raw key chỉ hiển thị 1 lần (state clear sau khi đóng)
- [ ] Scopes hiển thị đúng label tiếng Việt
- [ ] Audit log DataTable phân trang đúng
- [ ] Responsive mobile (table scroll ngang)

### Documentation
- [ ] `/docs` (Swagger UI) hiển thị title + description đúng
- [ ] `X-API-Key` security scheme có trong Swagger
- [ ] Có thể thử external endpoints trực tiếp từ Swagger
