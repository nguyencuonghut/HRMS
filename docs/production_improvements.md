# Kế hoạch nâng cấp Production — HRMS

**Người review:** System Architect  
**Ngày:** 2026-05-30  
**Phiên bản hệ thống:** v1.0.0  
**Mục tiêu:** Nâng cấp từ MVP → Production-grade, enterprise-ready

---

## Tóm tắt điều hành

Hệ thống HRMS có **nền tảng kỹ thuật tốt** (FastAPI + asyncpg + Vue 3 + PrimeVue, CI/CD skeleton, BE pagination cho phần lớn entities, structured logging, Celery). Tuy nhiên còn **15–20 vấn đề quan trọng** cần giải quyết trước khi đưa lên production thật sự với hàng trăm người dùng và dữ liệu nhân sự nhạy cảm.

Các vấn đề được chia theo **4 nhóm ưu tiên**:

| Nhóm | Số lượng | Timeframe |
|---|---|---|
| 🔴 Critical — Bắt buộc trước go-live | 5 | Sprint 1 (1–2 tuần) |
| 🟠 High — Nên có trong 30 ngày đầu | 12 | Sprint 2–3 |
| 🟡 Medium — Roadmap Q3/Q4 | 14 | Sprint 4–6 |
| 🟢 Low — Cải tiến dài hạn | 6 | Backlog |

---

## 🔴 CRITICAL — Phải có trước go-live

### C1. Secrets Management — Loại bỏ default hardcoded secrets

**Vấn đề:** `config.py` có default values không an toàn cho production:
```python
SECRET_KEY: str = "change-this-secret-key-in-production"  # ← NGUY HIỂM
MINIO_SECRET_KEY: str = "minioadmin"                        # ← NGUY HIỂM
```
Nếu `SECRET_KEY` không được override, JWT có thể bị forged.

**Fix:**
```python
# app/core/config.py
from pydantic import field_validator

class Settings(BaseSettings):
    SECRET_KEY: str
    ENCRYPTION_KEY: str

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        env = info.data.get("ENVIRONMENT", "development")
        if env == "production" and len(v) < 32:
            raise ValueError("SECRET_KEY phải ≥ 32 ký tự trong production")
        if v in ("change-this-secret-key-in-production", "dev-secret-key-change-in-prod"):
            if env == "production":
                raise ValueError("SECRET_KEY là giá trị mặc định — KHÔNG an toàn cho production")
        return v

    @field_validator("ENCRYPTION_KEY")
    @classmethod
    def validate_encryption_key(cls, v: str, info) -> str:
        env = info.data.get("ENVIRONMENT", "development")
        if env == "production" and not v:
            raise ValueError("ENCRYPTION_KEY bắt buộc trong production")
        return v
```

**Effort:** 2 giờ | **Files:** `config.py` | **Risk nếu không làm:** Data breach

---

### C2. Docker Security — Không chạy container với root user

**Vấn đề:** `backend/Dockerfile` không có `USER` directive → container chạy root → nếu bị exploit, attacker có full system access.

**Fix:**
```dockerfile
# backend/Dockerfile
FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/* && \
    # Tạo non-root user
    groupadd -r appuser && useradd -r -g appuser -u 1000 appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:appuser . .

USER appuser  # ← QUAN TRỌNG

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Effort:** 30 phút | **Files:** `backend/Dockerfile`, `frontend/Dockerfile`

---

### C3. v-html XSS — Sanitize tất cả HTML từ server

**Vấn đề:** 4 component dùng `v-html` để render HTML từ backend/database mà không sanitize:
- `NotificationSettingsView.vue:152` — email template preview
- `CommunicationTab.vue:58`, `SendEmailDialog.vue:61`, `EmailTemplateListTab.vue:138`

Attacker lưu `<script>` vào email template → XSS khi preview.

**Fix:**
```bash
npm install dompurify @types/dompurify
```

```typescript
// src/composables/useSanitize.ts
import DOMPurify from 'dompurify'

export function sanitizeHtml(html: string): string {
  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'ul', 'ol', 'li', 'a', 'span', 'div', 'h1', 'h2', 'h3'],
    ALLOWED_ATTR: ['href', 'target', 'rel', 'style', 'class'],
  })
}
```

```html
<!-- Thay vì: <div v-html="previewHtml" /> -->
<div v-html="sanitizeHtml(previewHtml)" />
```

**Effort:** 2 giờ | **Files:** 4 Vue components | **Risk:** Stored XSS → account takeover

---

### C4. Frontend Global Error Boundary

**Vấn đề:** Khi một component Vue throw error không được catch → toàn bộ app crash, user thấy màn hình trắng.

**Fix:**
```typescript
// src/App.vue
import { onErrorCaptured } from 'vue'

const appError = ref<Error | null>(null)

onErrorCaptured((err: Error, instance, info) => {
  console.error('[App Error]', err, info)
  appError.value = err
  // Gửi lên Sentry nếu có
  if (window.Sentry) {
    window.Sentry.captureException(err, { extra: { vueInfo: info } })
  }
  return false // Prevent propagation
})
```

```html
<template>
  <div v-if="appError" class="app-error-boundary">
    <i class="pi pi-exclamation-triangle" />
    <h2>Đã xảy ra lỗi không mong muốn</h2>
    <p>Vui lòng tải lại trang. Nếu lỗi tiếp tục, liên hệ IT.</p>
    <Button label="Tải lại trang" @click="window.location.reload()" />
  </div>
  <RouterView v-else />
</template>
```

**Effort:** 2 giờ

---

### C5. Gunicorn Graceful Timeout — Tránh mất dữ liệu khi deploy

**Vấn đề:** `docker-compose.prod.yml` dùng `gunicorn` nhưng không có timeout config → khi deploy mới, worker bị SIGKILL giữa transaction.

**Fix:**
```yaml
# docker-compose.prod.yml
backend:
  command: >
    gunicorn app.main:app
      -w 4
      -k uvicorn.workers.UvicornWorker
      --bind 0.0.0.0:8000
      --timeout 120
      --graceful-timeout 30
      --keep-alive 5
      --max-requests 1000
      --max-requests-jitter 100
      --access-logfile -
      --error-logfile -
```

**Effort:** 15 phút

---

## 🟠 HIGH — Nên có trong 30 ngày đầu

### H1. Axios — Timeout, Retry, Error Handling

**Vấn đề:** `api.ts` không có timeout → request có thể hang vô hạn. Không có retry cho lỗi mạng thoáng qua.

```typescript
// src/services/api.ts
import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30_000,  // 30s timeout
  headers: { 'Content-Type': 'application/json' },
})

// Request interceptor — thêm auth token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Response interceptor — xử lý lỗi nhất quán
api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const { response, config } = error

    // Network error — retry 1 lần sau 1 giây
    if (!response && !config._retried) {
      config._retried = true
      await new Promise((r) => setTimeout(r, 1000))
      return api(config)
    }

    // 401 → refresh token hoặc logout
    if (response?.status === 401 && !config._authRetried) {
      config._authRetried = true
      try {
        await authStore.refreshToken()
        return api(config)
      } catch {
        authStore.logout()
        router.push('/login')
      }
    }

    // 5xx → toast thông báo server error
    if (response?.status >= 500) {
      toast.add({ severity: 'error', summary: 'Lỗi hệ thống', detail: 'Máy chủ gặp sự cố, vui lòng thử lại sau.', life: 5000 })
    }

    return Promise.reject(error)
  }
)
```

**Effort:** 4 giờ

---

### H2. N+1 Query — Eager Loading

**Vấn đề:** List endpoints trả về employees/contracts kèm related data (department, job_title...) nhưng không dùng `selectinload` → N+1 queries.

**Ví dụ fix trong employee_service.py:**
```python
from sqlalchemy.orm import selectinload

async def list_employees_page(session: AsyncSession, ...) -> ...:
    stmt = (
        select(Employee)
        .options(
            selectinload(Employee.job_records).selectinload(EmployeeJobRecord.department),
            selectinload(Employee.job_records).selectinload(EmployeeJobRecord.job_title),
        )
        .where(...)
        .offset(offset)
        .limit(page_size)
    )
```

**Audit cần làm:** Chạy `DEBUG=true` → xem log SQL → tìm patterns lặp query → thêm `selectinload`.

**Effort:** 1–2 ngày (audit + fix 5–10 endpoints nặng nhất)

---

### H3. Request Tracing — Correlation ID

**Vấn đề:** Không thể trace một request cụ thể qua logs vì không có request ID.

```python
# app/middleware/request_id.py
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

logger = structlog.get_logger()

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:8]
        
        # Bind vào structlog context — tất cả log trong request sẽ có request_id
        with structlog.contextvars.bound_contextvars(request_id=request_id):
            import time
            start = time.monotonic()
            response = await call_next(request)
            duration_ms = int((time.monotonic() - start) * 1000)

            logger.info(
                "http_request",
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                duration_ms=duration_ms,
            )

            response.headers["X-Request-ID"] = request_id
            return response
```

**Đăng ký:**
```python
# main.py
app.add_middleware(RequestIDMiddleware)
```

**Effort:** 2 giờ

---

### H4. Circuit Breaker cho MinIO và SMTP

**Vấn đề:** Nếu MinIO down → mọi upload endpoint trả 500 và không có retry. Nếu SMTP down → notification service crash silently.

```python
# app/core/circuit_breaker.py
from functools import wraps
import time
import logging

logger = logging.getLogger(__name__)

class CircuitBreaker:
    def __init__(self, name: str, failure_threshold: int = 3, recovery_timeout: int = 60):
        self.name = name
        self.failures = 0
        self.last_failure_time = 0.0
        self.threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._state = "closed"  # closed | open | half-open

    def call(self, func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if self._state == "open":
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    self._state = "half-open"
                else:
                    raise RuntimeError(f"Circuit {self.name} is OPEN — service unavailable")
            try:
                result = await func(*args, **kwargs)
                if self._state == "half-open":
                    self._state = "closed"
                    self.failures = 0
                return result
            except Exception as e:
                self.failures += 1
                self.last_failure_time = time.time()
                if self.failures >= self.threshold:
                    self._state = "open"
                    logger.error("circuit_opened", circuit=self.name, failures=self.failures)
                raise
        return wrapper

minio_circuit = CircuitBreaker("minio", failure_threshold=3, recovery_timeout=30)
smtp_circuit  = CircuitBreaker("smtp",  failure_threshold=2, recovery_timeout=60)
```

**Effort:** 4 giờ

---

### H5. Database — Soft Delete Mixin

> **✅ Phase 1 hoàn thành** — Department, JobTitle, JobPosition (migration 0051 + 0052).  
> **⏳ Phase 2 (Employee, EmployeeContract, Leave, Training)** — Xem lịch bên dưới.

#### Lịch Phase 2

**Điều kiện tiên quyết** (phải đủ trước khi bắt đầu):
- [ ] H6 (exception logging) xong — để phát hiện bugs trong quá trình migrate
- [ ] Test coverage ≥ 70% — 40+ bảng thay đổi cần safety net
- [ ] Môi trường staging có dữ liệu đầy đủ để test
- [ ] Sprint không có feature mới song song — tránh conflict

**Thời điểm:** Sprint đầu tiên **sau go-live**, khi codebase đã ổn định.

**Scope Phase 2:**
- `employees` (god table — 40+ dependent tables, cần CASCADE soft-delete ở service layer)
- `employee_contracts` (có status machine phức tạp)
- `leave_records`, `leave_entitlements`
- `training_courses`, `training_plans`, `employee_training_records`

**Effort ước tính:** 3–5 ngày (code + test + review).

---

**Vấn đề:** Hard delete mất data vĩnh viễn; không đáp ứng compliance (dữ liệu nhân sự giữ 10 năm).

```python
# app/models/mixins.py
from datetime import datetime, timezone
from typing import Optional
import sqlalchemy as sa
from sqlmodel import Field

class SoftDeleteMixin:
    deleted_at: Optional[datetime] = Field(
        default=None,
        sa_column=sa.Column(sa.DateTime, nullable=True, index=True)
    )
    deleted_by: Optional[int] = Field(default=None)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def soft_delete(self, by_user_id: int) -> None:
        self.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
        self.deleted_by = by_user_id
```

**Service pattern:**
```python
# Thay vì:
await session.delete(employee)

# Dùng:
employee.soft_delete(by_user_id=current_user.id)
await session.commit()
await audit_service.log(...)
```

**Endpoint pattern:**
```python
# List endpoint — tự động filter soft deleted:
stmt = select(Employee).where(Employee.deleted_at.is_(None))
```

**Migration:** Thêm `deleted_at`, `deleted_by` vào các bảng: employees, contracts, departments, job_titles, job_positions.

**Effort:** 1 ngày

---

### H6. Bare Exception Handling

**Vấn đề:** 30+ chỗ dùng `except Exception:` hoặc `except:` mà không log → bugs ẩn, debugging khó.

**Pattern cần áp dụng:**
```python
# ❌ Hiện tại:
try:
    result = await some_operation()
except Exception:
    pass

# ✅ Cần thay:
import structlog
logger = structlog.get_logger(__name__)

try:
    result = await some_operation()
except SomeSpecificError as e:
    logger.warning("operation_failed", reason=str(e), context=context)
    raise HTTPException(400, detail="...")
except Exception:
    logger.exception("unexpected_error", context=context)
    raise  # Không swallow exception
```

**Automation:** Dùng `ruff` rule `BLE001` (blind exception catch) để tìm toàn bộ.

**Effort:** 1 ngày

---

### H7. Redis Password Protection

**Vấn đề:** Redis expose port 6380 ra ngoài (dev compose) không có password → bất kỳ ai trong network có thể đọc cache, queue.

```yaml
# docker-compose.prod.yml
redis:
  image: redis:7-alpine
  restart: always
  command: redis-server --requirepass ${REDIS_PASSWORD} --maxmemory 512mb --maxmemory-policy allkeys-lru
  # KHÔNG expose port ra ngoài trong production
  # ports: ["6380:6379"]  ← XÓA DÒNG NÀY
```

```python
# config.py
REDIS_URL: str = "redis://:${REDIS_PASSWORD}@redis:6379/0"
```

**Effort:** 1 giờ

---

### H8. Slow Query Monitoring

**Vấn đề:** Không có visibility vào slow queries trong production.

```python
# app/core/database.py
from sqlalchemy import event
import structlog
import time

logger = structlog.get_logger(__name__)

SLOW_QUERY_THRESHOLD_MS = 500

@event.listens_for(engine.sync_engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault("query_start_time", []).append(time.monotonic())

@event.listens_for(engine.sync_engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total_ms = (time.monotonic() - conn.info["query_start_time"].pop()) * 1000
    if total_ms > SLOW_QUERY_THRESHOLD_MS:
        logger.warning(
            "slow_query",
            duration_ms=int(total_ms),
            statement=statement[:200],
        )
```

**Effort:** 2 giờ

---

### H9. Celery — Exponential Backoff + Task Isolation

**Vấn đề:** Retry delay cố định 10s; beat và worker không isolated.

```python
# workers/tasks.py
@celery_app.task(
    name="...",
    bind=True,
    max_retries=5,
    autoretry_for=(Exception,),
    retry_backoff=True,          # exponential: 1s, 2s, 4s, 8s, 16s
    retry_backoff_max=300,       # max 5 phút
    retry_jitter=True,           # tránh thundering herd
    acks_late=True,
    time_limit=3600,             # hard limit 1 giờ
    soft_time_limit=3500,        # soft limit → raise SoftTimeLimitExceeded
)
def my_task(self):
    ...
```

**Dùng `celery-redbeat`** thay beat mặc định để tránh duplicate scheduler:
```bash
pip install celery-redbeat
```
```python
# celery_app.py
celery_app.conf.redbeat_redis_url = settings.REDIS_URL
```

**Effort:** 4 giờ

---

### H10. Healthcheck — Readiness vs Liveness

**Vấn đề:** Chỉ có 1 endpoint `/health`; cần tách readiness (có thể nhận traffic?) và liveness (app còn sống?).

```python
# main.py

@app.get("/health/live", tags=["System"])  # Kubernetes liveness probe
async def liveness():
    """Chỉ kiểm tra app có đang chạy không (không check dependencies)."""
    return {"status": "alive", "version": settings.APP_VERSION}

@app.get("/health/ready", tags=["System"])  # Kubernetes readiness probe
async def readiness() -> dict:
    """Kiểm tra đầy đủ: DB + Redis + MinIO. Nếu fail → k8s không route traffic vào."""
    checks: dict[str, str] = {}
    overall = "ready"

    try:
        async with AsyncSessionLocal() as s:
            await s.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"
        overall = "not_ready"

    try:
        r = aioredis.from_url(settings.REDIS_URL, socket_timeout=2)
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"
        overall = "not_ready"

    status_code = 200 if overall == "ready" else 503
    return JSONResponse(
        {"status": overall, "checks": checks},
        status_code=status_code,
    )
```

**Effort:** 2 giờ

---

### H11. Frontend — Route Permission Guards

**Vấn đề:** `beforeEach` chỉ check `isAuthenticated` nhưng không check quyền → user có thể navigate đến trang admin.

```typescript
// router/index.ts
router.beforeEach(async (to) => {
  const auth = useAuthStore()

  // 1. Check auth
  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  // 2. Check permission
  const requiredPermission = to.meta.permission as string | undefined
  if (requiredPermission && !auth.hasPermission(requiredPermission)) {
    return { name: 'forbidden' }  // Trang 403
  }
})
```

```typescript
// Route definition
{
  path: 'admin/users',
  meta: { requiresAuth: true, permission: 'users:view' },
  component: () => import('@/views/admin/UserListView.vue'),
}
```

**Effort:** 4 giờ

---

### H12. Nginx Configuration — Reverse Proxy Production

**Vấn đề:** File nginx config không có trong repo → deployment bí ẩn.

```nginx
# nginx/conf.d/default.conf
upstream backend {
    server backend:8000;
    keepalive 32;
}

server {
    listen 80;
    server_name hrms.hongha.vn;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name hrms.hongha.vn;

    ssl_certificate     /etc/letsencrypt/live/hrms.hongha.vn/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/hrms.hongha.vn/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;

    # Gzip
    gzip on;
    gzip_types text/plain application/json application/javascript text/css;

    # Frontend
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
        expires 1h;
        add_header Cache-Control "public, must-revalidate";
    }

    # Backend API — no cache
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
        proxy_connect_timeout 10s;

        # Rate limiting
        limit_req zone=api_limit burst=20 nodelay;
    }

    # File uploads — larger body
    location /api/v1/employees/import {
        client_max_body_size 10m;
        proxy_pass http://backend;
    }

    client_max_body_size 5m;
}

# Rate limit zone
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=30r/s;
```

**Effort:** 4 giờ

---

## 🟡 MEDIUM — Roadmap Q3/Q4

### M1. CSRF Protection

Dùng `SameSite=Strict` cookie cho session indicator; double-submit cookie pattern cho state-changing ops.

**Effort:** 1 ngày

---

### M2. DOMPurify — Nâng cấp CSP

Bỏ `'unsafe-inline'` khỏi `style-src`; dùng CSS hash hoặc `nonce` cho inline styles từ PrimeVue.

**Effort:** 4 giờ

---

### M3. Test Coverage Report

```ini
# pytest.ini
[pytest]
addopts = --cov=app --cov-report=term-missing --cov-fail-under=75
```

Mục tiêu: **≥ 75% coverage** trước khi merge vào `main`.

**Effort:** 1 ngày (setup + bổ sung tests thiếu)

---

### M4. Database Index Audit

Chạy `EXPLAIN ANALYZE` trên 10 query chậm nhất, bổ sung composite indexes:
```sql
-- Ví dụ indexes thường thiếu:
CREATE INDEX CONCURRENTLY ix_leave_records_employee_year
    ON leave_records (employee_id, EXTRACT(year FROM start_date));

CREATE INDEX CONCURRENTLY ix_audit_logs_user_action_date
    ON audit_logs (user_id, action, created_at DESC);
```

**Effort:** 2–3 ngày

---

### M5. Migrate Tokens từ localStorage → Memory + HttpOnly Cookie

localStorage dễ bị XSS đánh cắp. Giải pháp tốt nhất:
- `access_token` lưu **in-memory** (biến JS, không persist)
- `refresh_token` trong **HttpOnly cookie** (không accessible bởi JS)
- Backend cần CSRF protection khi dùng cookie

**Effort:** 3–4 ngày (cần thay đổi cả FE và BE)

---

### M6. Offline Detection + UX

```typescript
// src/composables/useOnline.ts
import { ref, onMounted, onUnmounted } from 'vue'

export function useOnline() {
  const isOnline = ref(navigator.onLine)
  const onOnline  = () => { isOnline.value = true }
  const onOffline = () => { isOnline.value = false }

  onMounted(() => {
    window.addEventListener('online',  onOnline)
    window.addEventListener('offline', onOffline)
  })
  onUnmounted(() => {
    window.removeEventListener('online',  onOnline)
    window.removeEventListener('offline', onOffline)
  })
  return { isOnline }
}
```

**Effort:** 4 giờ

---

### M7. Bundle Size Monitoring

```typescript
// vite.config.ts
import { visualizer } from 'rollup-plugin-visualizer'

export default defineConfig({
  plugins: [
    vue(),
    visualizer({ open: false, filename: 'dist/stats.html' }),
  ],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['vue', 'vue-router', 'pinia'],
          primevue: ['primevue'],
          charts: ['@primevue/charts'],
        },
      },
    },
  },
})
```

Thêm vào CI: fail nếu bundle > 2MB.

**Effort:** 2 giờ

---

### M8. API Response Wrapper Nhất quán

**Vấn đề:** Một số endpoint trả `list[T]`, một số trả `{items, total}`, gây confusion cho client.

```python
# app/schemas/base.py
from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")

class PageResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int
```

Áp dụng nhất quán cho tất cả list endpoints.

**Effort:** 1 ngày (refactor)

---

### M9. Liveness & Alerting Stack

Cài đặt stack monitoring nhẹ:
```yaml
# docker-compose.monitoring.yml
services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana:latest
    ports: ["3001:3000"]

  loki:
    image: grafana/loki:latest
```

Thêm `/metrics` endpoint:
```bash
pip install prometheus-fastapi-instrumentator
```
```python
from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app, endpoint="/metrics")
```

**Effort:** 1 ngày

---

### M10. Database Backup Automation

```bash
# scripts/backup_db.sh — đã có ✅
# Cần thêm: verify backup integrity
```

```bash
# scripts/verify_backup.sh
#!/bin/bash
BACKUP_FILE="$1"
# Restore vào DB test
pg_restore -d hrms_verify "$BACKUP_FILE" 2>&1 | tail -5
# Check row counts
psql -d hrms_verify -c "SELECT count(*) FROM employees" || exit 1
echo "Backup verified OK"
```

**Effort:** 2 giờ

---

### M11. Celery Worker Monitoring — Flower

```yaml
# docker-compose.prod.yml (thêm)
flower:
  image: mher/flower:latest
  command: celery --broker=redis://redis:6379/0 flower --port=5555
  ports:
    - "5555:5555"  # KHÔNG expose ra public — chỉ internal
  environment:
    FLOWER_BASIC_AUTH: admin:${FLOWER_PASSWORD}
```

**Effort:** 30 phút

---

### M12. Pagination Max Limit

**Vấn đề:** Một số endpoint cho phép `page_size=200` → 200 items × N relationships = hàng nghìn rows.

```python
# Convention: max page_size = 100 cho mọi endpoint
page_size: int = Query(20, ge=1, le=100)  # Không cho phép > 100
```

**Effort:** 2 giờ (grep + fix)

---

### M13. Migration Safety — Zero-Downtime Pattern

**Vấn đề:** Thêm NOT NULL column không có default sẽ fail trên prod với dữ liệu hiện tại.

**Pattern an toàn:**
```
Bước 1 (Deploy A): ALTER TABLE employees ADD COLUMN new_field VARCHAR NULLABLE;
Bước 2: Backfill data: UPDATE employees SET new_field = 'default' WHERE new_field IS NULL;
Bước 3 (Deploy B): ALTER TABLE employees ALTER COLUMN new_field SET NOT NULL;
```

Thêm `migration_check.sh` vào CI để verify không có breaking changes.

**Effort:** Ongoing practice

---

### M14. Encrypt thêm PII Fields

**Hiện tại:** `id_number`, `passport_number`, `personal_tax_code` đã encrypt ✅  
**Cần thêm:** `phone_number`, `personal_email` cũng là PII theo PDPA.

```python
# models/employee.py
phone_number: Optional[str] = Field(
    default=None,
    sa_column=Column(EncryptedString(), nullable=True)  # Thêm encryption
)
```

**Effort:** 4 giờ + migration

---

## 🟢 LOW — Backlog dài hạn

### L1. GraphQL hoặc tRPC cho FE-BE type safety

Hiện tại OpenAPI → codegen hoặc dùng `@hey-api/openapi-ts` để sinh TypeScript types tự động từ backend schemas.

### L2. Event Sourcing cho Audit Trail

Thay AuditLog đơn giản bằng event sourcing pattern → rebuild state từ events.

### L3. Multi-tenancy Support

Chuẩn bị schema-per-tenant hoặc row-level security (RLS) cho PostgreSQL nếu cần SaaS.

### L4. API Rate Limit per User/Endpoint

Hiện tại rate limit per IP. Cần per authenticated user + per endpoint.

### L5. WebSocket cho Real-time Notifications

Thay polling bằng WebSocket → notification bell thực sự real-time.

### L6. Internationalization (i18n)

`vue-i18n` đã chuẩn bị cấu trúc. Migrate strings khi có yêu cầu đa ngôn ngữ.

---

## Ma trận Ưu tiên vs Effort

```
          EFFORT
          Nhỏ (<4h)        Vừa (1-2 ngày)      Lớn (>3 ngày)
        ┌────────────────┬─────────────────┬────────────────────┐
HIGH    │ C5 Gunicorn    │ H1 Axios        │ H2 N+1 Queries     │
IMPACT  │ C4 Error bound │ H5 Soft delete  │ H11 Route guards   │
        │ H7 Redis pass  │ H6 Exceptions   │ M5 Token migration │
        │ H8 Slow query  │ H9 Celery retry │                    │
        ├────────────────┼─────────────────┼────────────────────┤
MED     │ M6 Offline     │ M3 Coverage     │ M9 Monitoring      │
IMPACT  │ M7 Bundle size │ M4 Index audit  │                    │
        │ H12 Nginx      │ M10 Backup verify                    │
        ├────────────────┼─────────────────┼────────────────────┤
LOW     │ M11 Flower     │ M14 Encrypt PII │ L1 GraphQL         │
IMPACT  │ M12 Max limit  │                 │ L3 Multi-tenant    │
        └────────────────┴─────────────────┴────────────────────┘
```

---

## Checklist Go-Live Production

### 🔐 Security
- [ ] C1: Default secrets removed + validation added
- [x] C2: Docker non-root user (appuser uid=1000)
- [x] C3: DOMPurify for v-html (4 components)
- [x] C5: Gunicorn timeout configured (--timeout 120 --graceful-timeout 30)
- [ ] H7: Redis password protected
- [ ] H12: Nginx config in repo + SSL

### 🚀 Performance & Reliability
- [ ] C4: Global error boundary in App.vue
- [ ] H1: Axios timeout + retry
- [ ] H2: Top 5 N+1 queries fixed
- [ ] H3: Request correlation ID
- [ ] H4: Circuit breaker MinIO/SMTP
- [ ] H9: Celery exponential backoff + soft time limit
- [ ] H10: `/health/live` + `/health/ready` separated

### 📊 Observability
- [ ] H8: Slow query monitoring (>500ms)
- [ ] H3: Request ID in all logs
- [ ] Sentry DSN configured in production
- [ ] HEALTHCHECK_PING_URL configured

### 🗄️ Data
- [x] H5 Phase 1: Soft delete — Department, JobTitle, JobPosition (migration 0051+0052)
- [ ] H5 Phase 2: Soft delete — Employee, Contract, Leave, Training (sau go-live)
- [ ] Database backup running + verified
- [ ] H6: No bare except without logging

### 🔧 Infrastructure  
- [ ] Load test: 200 concurrent users, p95 < 800ms
- [ ] Smoke test after each deploy
- [ ] Rollback plan documented
- [ ] On-call runbook written

---

## Liên kết tài liệu liên quan

- [plan_15.1_bao_mat.md](plan_15.1_bao_mat.md) — Chi tiết bảo mật
- [plan_15.2_hieu_nang.md](plan_15.2_hieu_nang.md) — Chi tiết hiệu năng
- [plan_15.5_van_hanh.md](plan_15.5_van_hanh.md) — Chi tiết vận hành
- [sla.md](sla.md) — SLA targets
- [scripts/restore_procedure.md](../scripts/restore_procedure.md) — Disaster recovery
