# Kế hoạch triển khai — 15.5. Vận hành

**Phạm vi:** CI/CD · Error monitoring · Log aggregation · Environment separation · SLA  
**Phụ thuộc:** Docker Compose ✅ · Health check ✅ · PostgreSQL ✅ · Redis ✅  
**Căn cứ nghiệp vụ:** FEATURES.md §15.5  
**Mục tiêu:** DEV / STAGING / PROD separation · Daily backup 90 ngày · CI/CD · SLA 99.5%

---

## Trạng thái hiện tại

### Đã có (✅)

| Thành phần | Chi tiết |
|---|---|
| Docker Compose (dev) | 7 services: db, redis, minio, backend, celery_worker, celery_beat, frontend |
| Dockerfile multi-stage | Backend (python:3.12-slim) + Frontend (node:22 → nginx) |
| Health checks | db (pg_isready), redis (redis-cli ping), minio (http health) |
| `GET /health` endpoint | `{"status": "ok", "version": "..."}` — basic health |
| Startup verification | `ping_db()`, `ensure_bucket()`, seed RBAC |
| Alembic migrations | Versioned DB migrations, auto-run on startup |
| Basic logging | `logging.getLogger(__name__)` — stdout, không centralized |
| Environment config | `.env` file, pydantic_settings |
| Security headers | SecurityHeadersMiddleware ✅ (plan 15.1) |
| Rate limiting | slowapi ✅ (plan 15.1) |

### Chưa có (❌)

| Thành phần | Ưu tiên |
|---|---|
| **CI/CD pipeline** | 🔴 Critical |
| **Error monitoring (Sentry)** | 🔴 Critical |
| **Database backup** | 🔴 Critical → được cover tại plan 15.4 |
| **Log aggregation** | 🟠 High |
| **Environment separation (staging)** | 🟠 High |
| **Metrics / Prometheus** | 🟡 Medium |
| **Uptime monitoring** | 🟡 Medium |
| **SLA documentation** | 🟡 Medium |
| **Kubernetes manifests** | 🟡 Medium (nếu dùng K8s) |
| **Secret management** | 🟠 High |

---

## Phạm vi Plan 15.5

### Trong phạm vi

1. **CI/CD pipeline** — GitHub Actions: test → build → push image → deploy staging
2. **Error monitoring** — Sentry backend + frontend
3. **Environment separation** — dev / staging / prod configs rõ ràng
4. **Log aggregation** — structured logging, chuẩn bị ship logs
5. **Enhanced health check** — kiểm tra DB, Redis, MinIO connectivity
6. **SLA & runbook** — document targets, incident response procedure
7. **Uptime monitoring** — Healthchecks.io hoặc UptimeRobot cho `/health`

### Ngoài phạm vi

- Kubernetes (dùng Docker Compose cho production nhỏ)
- Full ELK stack (Elasticsearch + Logstash + Kibana) — dùng Loki nếu cần
- DataDog / New Relic APM (đắt tiền; dùng Sentry free tier trước)
- Multi-region deployment
- Auto-scaling

---

## Chi tiết kỹ thuật

### 1. CI/CD Pipeline — GitHub Actions (Slice 1)

**File `.github/workflows/ci.yml`:**
```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_BACKEND: ${{ github.repository }}/hrms-backend
  IMAGE_FRONTEND: ${{ github.repository }}/hrms-frontend

jobs:
  # ── Backend tests ──────────────────────────────────────────────────────
  test-backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: hrms_test
          POSTGRES_PASSWORD: testpass
        ports: ["5432:5432"]
        options: --health-cmd "pg_isready -U postgres" --health-interval 5s --health-retries 5
      redis:
        image: redis:7-alpine
        ports: ["6379:6379"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with: { python-version: "3.12" }

      - name: Install dependencies
        run: pip install -r backend/requirements.txt

      - name: Run tests
        working-directory: backend
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:testpass@localhost:5432/hrms_test
          REDIS_URL: redis://localhost:6379/0
          SECRET_KEY: test-secret-key-for-ci
          ENCRYPTION_KEY: ""
        run: pytest tests/ -q --tb=short

  # ── Frontend type check ─────────────────────────────────────────────────
  check-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "22" }
      - run: npm ci
        working-directory: frontend
      - run: npx vue-tsc --noEmit
        working-directory: frontend

  # ── Build & Push images ─────────────────────────────────────────────────
  build:
    needs: [test-backend, check-frontend]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - uses: actions/checkout@v4

      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push backend
        uses: docker/build-push-action@v5
        with:
          context: backend
          push: true
          tags: ${{ env.REGISTRY }}/${{ env.IMAGE_BACKEND }}:${{ github.sha }},${{ env.REGISTRY }}/${{ env.IMAGE_BACKEND }}:latest

      - name: Build and push frontend
        uses: docker/build-push-action@v5
        with:
          context: frontend
          push: true
          tags: ${{ env.REGISTRY }}/${{ env.IMAGE_FRONTEND }}:${{ github.sha }},${{ env.REGISTRY }}/${{ env.IMAGE_FRONTEND }}:latest

  # ── Deploy to staging ────────────────────────────────────────────────────
  deploy-staging:
    needs: build
    runs-on: ubuntu-latest
    environment: staging

    steps:
      - name: Deploy to staging server
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.STAGING_HOST }}
          username: ${{ secrets.STAGING_USER }}
          key: ${{ secrets.STAGING_SSH_KEY }}
          script: |
            cd /opt/hrms-staging
            docker compose pull
            docker compose up -d --no-deps backend frontend
            docker compose exec -T backend alembic upgrade head
```

**PR workflow** (chạy tests, không deploy):
```yaml
# .github/workflows/pr.yml
on: [pull_request]
jobs:
  test: uses: ./.github/workflows/ci.yml@main
```

---

### 2. Error Monitoring — Sentry (Slice 1)

**Backend:**
```bash
# requirements.txt
sentry-sdk[fastapi]>=2.0.0
```

```python
# app/main.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
            CeleryIntegration(),
        ],
        environment=settings.ENVIRONMENT,
        release=settings.APP_VERSION,
        traces_sample_rate=0.1,      # 10% requests for performance
        profiles_sample_rate=0.05,
        send_default_pii=False,       # KHÔNG gửi PII (email, IP)
    )
```

```python
# app/core/config.py
SENTRY_DSN: str = ""     # bỏ trống = disabled
```

**Frontend:**
```bash
npm install @sentry/vue @sentry/tracing
```

```typescript
// main.ts
import * as Sentry from '@sentry/vue'

if (import.meta.env.VITE_SENTRY_DSN) {
  Sentry.init({
    app,
    dsn: import.meta.env.VITE_SENTRY_DSN,
    environment: import.meta.env.VITE_APP_ENV ?? 'development',
    tracesSampleRate: 0.1,
    tracePropagationTargets: ['localhost', /^https:\/\/hrms\.hongha\.vn/],
  })
}
```

```bash
# frontend/.env.staging
VITE_SENTRY_DSN=https://xxx@sentry.io/yyy
VITE_APP_ENV=staging
```

---

### 3. Environment Separation (Slice 1)

**Cấu trúc file env:**
```
.
├── docker-compose.yml           ← base config (shared services)
├── docker-compose.dev.yml       ← dev overrides (hot reload, debug)
├── docker-compose.staging.yml   ← staging overrides
├── docker-compose.prod.yml      ← prod overrides (no ports exposed)
├── .env.example                 ← template (commit vào git)
├── .env.dev                     ← dev values (không commit)
├── .env.staging                 ← staging values (không commit)
└── .env.prod                    ← prod values (không commit; dùng secrets manager)
```

**`docker-compose.dev.yml`:**
```yaml
services:
  backend:
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - ./backend:/app
    environment:
      DEBUG: "true"
      ENVIRONMENT: development

  frontend:
    command: npm run dev
    volumes:
      - ./frontend:/app
      - /app/node_modules
```

**`docker-compose.prod.yml`:**
```yaml
services:
  backend:
    image: ghcr.io/hongha/hrms-backend:latest
    restart: always
    environment:
      DEBUG: "false"
      ENVIRONMENT: production
    # Không expose port ra ngoài — dùng nginx reverse proxy
    expose:
      - "8000"

  frontend:
    image: ghcr.io/hongha/hrms-frontend:latest
    restart: always

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/ssl/certs:ro
```

**Deploy commands:**
```bash
# Dev
docker compose -f docker-compose.yml -f docker-compose.dev.yml up

# Staging
docker compose -f docker-compose.yml -f docker-compose.staging.yml --env-file .env.staging up -d

# Production
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.prod up -d
```

---

### 4. Enhanced Health Check (Slice 1)

**Cập nhật `GET /health` endpoint (`app/main.py`):**
```python
@app.get("/health", tags=["System"])
async def health_check(session: AsyncSession = Depends(get_session)) -> dict:
    checks: dict[str, str] = {}
    status = "ok"

    # Database
    try:
        await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"
        status = "degraded"

    # Redis
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"
        status = "degraded"

    # MinIO (lightweight check — chỉ ping, không list objects)
    try:
        from app.core.storage import _client, bucket_name
        _client().bucket_exists(bucket_name())
        checks["minio"] = "ok"
    except Exception as e:
        checks["minio"] = f"error: {e}"
        status = "degraded"

    return {
        "status": status,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "checks": checks,
    }
```

---

### 5. Structured Logging (Slice 2)

**Thư viện:** `structlog` (JSON output, production-ready)

```bash
# requirements.txt
structlog>=24.0.0
```

```python
# app/core/logging.py
import logging
import sys
import structlog

def setup_logging(debug: bool = False) -> None:
    level = logging.DEBUG if debug else logging.INFO

    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),    # JSON output cho log shipper
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
        cache_logger_on_first_use=True,
    )

# Gọi trong main.py startup:
setup_logging(debug=settings.DEBUG)
```

**Sử dụng:**
```python
import structlog
logger = structlog.get_logger(__name__)

logger.info("employee_created", employee_id=emp.id, email=emp.email)
logger.warning("login_failed", email=email, ip=client_ip)
logger.error("export_failed", job_id=job_id, error=str(e))
```

**Output JSON (dễ ship sang Loki/CloudWatch):**
```json
{"event": "employee_created", "employee_id": 42, "logger": "app.services.employee_service", "level": "info", "timestamp": "2026-05-29T08:00:00Z"}
```

---

### 6. Uptime Monitoring (Slice 2)

**Healthchecks.io (free tier, đơn giản):**

1. Tạo check tại healthchecks.io → lấy ping URL
2. Thêm vào Celery beat để ping định kỳ:

```python
# app/workers/tasks.py
@celery_app.task(name="app.workers.tasks.ping_healthcheck")
def ping_healthcheck() -> None:
    """Ping uptime monitoring service."""
    if not settings.HEALTHCHECK_PING_URL:
        return
    import httpx
    try:
        httpx.get(settings.HEALTHCHECK_PING_URL, timeout=10)
    except Exception:
        pass  # không fail task nếu ping lỗi
```

```python
# celery_app.py beat_schedule thêm:
"ping-healthcheck": {
    "task": "app.workers.tasks.ping_healthcheck",
    "schedule": 60.0,    # mỗi 60 giây
},
```

```python
# config.py
HEALTHCHECK_PING_URL: str = ""    # URL từ healthchecks.io
```

Nếu backend down > 5 phút (3 missed pings) → alert email/Slack tự động.

---

### 7. SLA Documentation (Slice 2)

**SLA Targets:**

| Metric | Target | Measurement |
|---|---|---|
| **Availability** | 99.5% / tháng | Uptime monitoring |
| **API response time p95** | < 800ms | Sentry performance |
| **Export time** | < 60s cho 5000 dòng | Celery task duration |
| **Recovery Time (RTO)** | ≤ 4 giờ | Manual failover |
| **Recovery Point (RPO)** | ≤ 24 giờ | Daily backup |

**Incident Response:**

| Severity | Mô tả | Response Time | Resolution Time |
|---|---|---|---|
| P1 - Critical | System down hoàn toàn | 15 phút | 4 giờ |
| P2 - High | Tính năng core không hoạt động | 30 phút | 8 giờ |
| P3 - Medium | Tính năng phụ bị ảnh hưởng | 2 giờ | 24 giờ |
| P4 - Low | Cosmetic / minor issue | 1 ngày | 1 tuần |

**Maintenance window:** Thứ Bảy 23:00–01:00 (ngoài giờ làm việc)

---

## Cấu trúc file thay đổi

```
.
├── .github/workflows/
│   ├── ci.yml               ← NEW — CI/CD pipeline
│   └── pr.yml               ← NEW — PR checks
├── docker-compose.dev.yml   ← NEW — dev overrides
├── docker-compose.prod.yml  ← NEW — prod overrides
├── .env.example             ← NEW — template (commit)
backend/
├── requirements.txt         ← UPDATE — sentry-sdk, structlog
├── app/
│   ├── core/
│   │   ├── config.py       ← UPDATE — SENTRY_DSN, HEALTHCHECK_PING_URL
│   │   └── logging.py      ← NEW — structured logging setup
│   ├── main.py             ← UPDATE — Sentry init, enhanced /health
│   └── workers/tasks.py    ← UPDATE — ping_healthcheck task
frontend/
├── package.json            ← UPDATE — @sentry/vue
├── src/main.ts             ← UPDATE — Sentry init
└── .env.staging            ← NEW — staging env vars
scripts/
└── deploy.sh               ← NEW — deployment helper script
```

---

## Kế hoạch theo Slice

### Slice 1 — CI/CD + Sentry + Environment Separation (Critical)

**Việc cần làm:**
1. Tạo `.github/workflows/ci.yml` với test → build → push → deploy staging
2. Cấu hình GitHub repository secrets: `STAGING_HOST`, `STAGING_USER`, `STAGING_SSH_KEY`
3. Thêm `sentry-sdk[fastapi]` vào requirements.txt
4. Thêm `SENTRY_DSN` vào config + init trong main.py
5. Thêm `@sentry/vue` vào frontend + init trong main.ts
6. Tạo `docker-compose.dev.yml` + `docker-compose.prod.yml`
7. Cập nhật `/health` endpoint — kiểm tra DB + Redis + MinIO
8. Tạo `.env.example` template

**Verify:**
- Push code lên GitHub → CI chạy → tests pass → image build
- Sentry nhận 1 test error từ backend + frontend
- `GET /health` → trả `checks.database: "ok"`, `checks.redis: "ok"`

---

### Slice 2 — Logging + Uptime + SLA (High)

**Việc cần làm:**
1. Thêm `structlog` vào requirements.txt
2. Tạo `app/core/logging.py` + gọi `setup_logging()` trong main.py
3. Replace `logging.getLogger()` với `structlog.get_logger()` tại 5–10 service files
4. Thêm `ping_healthcheck` Celery task + config `HEALTHCHECK_PING_URL`
5. Setup Healthchecks.io (hoặc UptimeRobot) cho `GET /health`
6. Viết `docs/sla.md` với SLA targets + incident response matrix

**Verify:** Logs output JSON format, Healthchecks.io nhận ping.

---

## Rủi ro & Cách xử lý

| Rủi ro | Cách xử lý |
|---|---|
| CI/CD deploy staging fail → rollback | `docker compose up --rollback` hoặc pull previous image tag |
| Sentry gửi PII (CCCD, email) | Set `send_default_pii=False`, filter `before_send` nếu cần |
| Log volume quá lớn → disk full | Rotate logs `logrotate`, ship to external store nhanh |
| GitHub Actions costs | Tận dụng 2000 phút/tháng free; self-hosted runner nếu cần |
| Healthcheck ping bị block (firewall) | Dùng outbound HTTPS port 443 — thường không bị block |

---

## Checklist

### Critical (phải có trước go-live)
- [ ] `.github/workflows/ci.yml` — tests pass trên PR, deploy staging trên merge main
- [ ] Sentry backend setup — errors xuất hiện trong Sentry dashboard
- [ ] Sentry frontend setup — JS errors được track
- [ ] `docker-compose.prod.yml` — production config tách biệt, no debug
- [ ] `.env.example` — document tất cả env variables cần thiết
- [ ] `/health` endpoint trả về chi tiết DB/Redis/MinIO status

### High (nên có trước go-live)
- [ ] Structured logging (structlog JSON format)
- [ ] Uptime monitoring active — alert khi down > 5 phút
- [ ] `HEALTHCHECK_PING_URL` config + Celery ping task
- [ ] `docs/sla.md` — SLA targets ký duyệt

### Medium (làm sau go-live)
- [ ] Loki / CloudWatch log aggregation
- [ ] Prometheus `/metrics` endpoint
- [ ] Nginx reverse proxy config (SSL termination, rate limit)
- [ ] Kubernetes manifests (nếu scale lên)
- [ ] Monthly restore drill — test backup thực sự restore được
