# Kế hoạch triển khai — 15.2. Hiệu năng

**Phạm vi:** DB connection pool · Redis caching · N+1 query · Load testing  
**Phụ thuộc:** PostgreSQL ✅ · Redis ✅ · Celery ✅ · asyncpg ✅  
**Căn cứ nghiệp vụ:** FEATURES.md §15.2  
**Mục tiêu:** API < 800ms / 100k bản ghi · Export < 60s / 5000 dòng · 200 concurrent users

---

## Trạng thái hiện tại

### Đã có (✅)

| Thành phần | Chi tiết |
|---|---|
| 45+ DB indices | Trên tất cả bảng chính (employees, contracts, insurance, recruitment...) |
| Async driver | asyncpg + SQLAlchemy async session toàn bộ |
| Phân trang server-side | `limit/offset` pattern nhất quán, max page_size capped |
| Background export | Celery queue riêng (`"exports"`), acks_late, max_retries=2 |
| Celery beat tasks | 5 tasks định kỳ, tách queue export vs default |
| Redis | Có sẵn (dùng bởi Celery + rate limiting), chưa dùng cho cache app |

### Chưa có / Cần cải thiện (❌/⚠️)

| Thành phần | Vấn đề | Ưu tiên |
|---|---|---|
| **Connection pool** | Default pool_size=5, max_overflow=10 — quá nhỏ cho 200 users | 🔴 Critical |
| **Redis caching** | Danh mục, org structure, permission matrix load từ DB mỗi request | 🔴 Critical |
| **N+1 query** | Không dùng `selectinload`/`joinedload` — hot endpoints có thể bị N+1 | 🟠 High |
| **Slow query tracking** | Không có profiling tool trong production | 🟡 Medium |
| **Load testing** | Chưa verify 200 concurrent users | 🟡 Medium |

---

## Phạm vi Plan 15.2

### Trong phạm vi

1. **DB connection pool tuning** — cấu hình đúng cho 200 concurrent users
2. **Redis caching** — cache danh mục hành chính, phòng ban, quyền hạn
3. **N+1 query audit** — fix 5–10 hot endpoints bằng `selectinload`
4. **Query logging** — bật slow query log trong dev, Sentry performance trong prod
5. **Load testing** — k6 verify 200 concurrent users đạt SLA

### Ngoài phạm vi

- Sharding / horizontal DB scaling
- CDN cho static assets
- Read replica PostgreSQL
- Query plan optimization (EXPLAIN ANALYZE) — nếu cần làm riêng

---

## Chi tiết kỹ thuật

### 1. DB Connection Pool (Slice 1 — Critical)

**Hiện tại** (`app/core/database.py`):
```python
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args={"ssl": False},
)
# Default: pool_size=5, max_overflow=10, pool_timeout=30, pool_recycle=-1
```

**Cần sửa:**
```python
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args={"ssl": False},
    pool_size=20,           # 200 users / ~10 req concurrent per connection
    max_overflow=40,        # burst headroom
    pool_pre_ping=True,     # validate stale connections trước khi dùng
    pool_recycle=3600,      # recycle mỗi 1 giờ, tránh idle disconnect
    pool_timeout=30,        # raise TimeoutError nếu không có connection sau 30s
)
```

**Config mới trong `app/core/config.py`:**
```python
DB_POOL_SIZE:     int = 20
DB_MAX_OVERFLOW:  int = 40
DB_POOL_RECYCLE:  int = 3600
DB_POOL_PRE_PING: bool = True
```

---

### 2. Redis Application Cache (Slice 1 — Critical)

**Các đối tượng nên cache (TTL 1 giờ):**

| Key pattern | Nội dung | TTL |
|---|---|---|
| `cache:departments:all` | Toàn bộ phòng ban active | 1h |
| `cache:departments:tree` | Cây phòng ban | 1h |
| `cache:job_titles:all` | Chức danh active | 1h |
| `cache:leave_types:all` | Loại phép | 1h |
| `cache:permissions:{user_id}` | Permission set của user | 15 phút |
| `cache:admin_units:{parent_code}` | Đơn vị hành chính | 24h |

**Helper module `app/core/cache.py`:**
```python
import json
import redis.asyncio as aioredis
from app.core.config import settings

_client: aioredis.Redis | None = None

def get_redis() -> aioredis.Redis:
    global _client
    if _client is None:
        _client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _client

async def cache_get(key: str) -> dict | list | None:
    raw = await get_redis().get(key)
    return json.loads(raw) if raw else None

async def cache_set(key: str, value: dict | list, ttl: int = 3600) -> None:
    await get_redis().setex(key, ttl, json.dumps(value, ensure_ascii=False, default=str))

async def cache_delete(key: str) -> None:
    await get_redis().delete(key)

async def cache_delete_pattern(pattern: str) -> None:
    keys = await get_redis().keys(pattern)
    if keys:
        await get_redis().delete(*keys)
```

**Pattern sử dụng trong service:**
```python
# departments_service.py
async def get_all_departments(session: AsyncSession) -> list[Department]:
    key = "cache:departments:all"
    cached = await cache_get(key)
    if cached:
        return [Department.model_validate(d) for d in cached]

    depts = (await session.execute(select(Department).where(Department.is_active == True))).scalars().all()
    await cache_set(key, [d.model_dump() for d in depts])
    return depts

# Invalidate khi có thay đổi:
async def create_department(session, data) -> Department:
    dept = Department(**data.model_dump())
    session.add(dept)
    await session.commit()
    await cache_delete_pattern("cache:departments:*")  # invalidate all dept caches
    return dept
```

---

### 3. N+1 Query Audit (Slice 2)

**Hot endpoints cần kiểm tra:**

| Endpoint | Nghi ngờ N+1 | Fix |
|---|---|---|
| `GET /employees` (list) | Load job_records per employee | `.options(selectinload(Employee.job_records))` |
| `GET /employees/{id}` (detail) | Load multiple sub-resources | Batch query trong service |
| `GET /contracts` | Load employee + category | `.options(joinedload(...))` |
| `GET /leaves` (list) | Load employee + leave_type | |
| `GET /audit-logs` | Load user info per log | |

**Pattern fix N+1:**
```python
from sqlalchemy.orm import selectinload, joinedload

# Thay vì:
employees = (await session.execute(select(Employee))).scalars().all()
for emp in employees:
    job_record = await session.execute(...)  # N queries!

# Dùng:
stmt = (
    select(Employee)
    .options(selectinload(Employee.job_records))
    .options(joinedload(Employee.department))
    .where(Employee.is_active == True)
)
employees = (await session.execute(stmt)).unique().scalars().all()
```

---

### 4. Slow Query Logging (Slice 2)

**Development:**
```python
# database.py — bật khi DEBUG=True
engine = create_async_engine(
    ...,
    echo=settings.DEBUG,
    echo_pool=settings.DEBUG,
)
```

**Production — Sentry Performance:**
```python
# requirements.txt: sentry-sdk[fastapi]>=2.0.0

# main.py:
import sentry_sdk
sentry_sdk.init(
    dsn=settings.SENTRY_DSN,
    traces_sample_rate=0.1,      # sample 10% of requests
    profiles_sample_rate=0.05,   # profile 5%
)
```

**Config thêm:**
```python
# config.py
SENTRY_DSN: str = ""   # bỏ trống = disabled
```

---

### 5. Load Testing (Slice 3)

**Tool:** k6 (open source, script JavaScript)

**Script `scripts/load_test.js`:**
```javascript
import http from 'k6/http'
import { check, sleep } from 'k6'

export const options = {
  stages: [
    { duration: '30s', target: 50 },    // ramp up
    { duration: '2m',  target: 200 },   // stay at 200
    { duration: '30s', target: 0 },     // ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<800'],   // 95% < 800ms
    http_req_failed:   ['rate<0.01'],   // <1% error
  },
}

const BASE = 'http://localhost:8000/api/v1'
let token = ''

export function setup() {
  const res = http.post(`${BASE}/auth/login`, JSON.stringify({
    email: 'admin@hrms.local', password: 'Hrms@2026'
  }), { headers: { 'Content-Type': 'application/json' } })
  return { token: res.json('access_token') }
}

export default function(data) {
  const headers = { Authorization: `Bearer ${data.token}` }
  
  // Test các endpoint thường dùng nhất
  const r1 = http.get(`${BASE}/employees?page=1&page_size=20`, { headers })
  check(r1, { 'employees list 200': r => r.status === 200 })
  
  const r2 = http.get(`${BASE}/departments`, { headers })
  check(r2, { 'departments 200': r => r.status === 200 })
  
  sleep(1)
}
```

**Chạy:**
```bash
k6 run scripts/load_test.js
```

---

## Cấu trúc file thay đổi

```
backend/app/
├── core/
│   ├── cache.py          ← NEW — Redis cache helpers
│   ├── database.py       ← UPDATE — pool_size, max_overflow, pool_pre_ping
│   └── config.py         ← UPDATE — DB_POOL_SIZE, DB_MAX_OVERFLOW, SENTRY_DSN
├── services/
│   ├── department_service.py   ← UPDATE — cache layer
│   ├── org_service.py          ← UPDATE — cache layer
│   └── auth_service.py         ← UPDATE — permission cache 15 phút
scripts/
└── load_test.js          ← NEW — k6 load test script
```

---

## Kế hoạch theo Slice

### Slice 1 — Connection Pool + Redis Cache (Critical)

**Việc cần làm:**
1. Cập nhật `database.py` — pool_size=20, max_overflow=40, pool_pre_ping=True, pool_recycle=3600
2. Thêm config vào `config.py` — DB_POOL_SIZE, DB_MAX_OVERFLOW
3. Tạo `app/core/cache.py` — cache_get/set/delete helpers
4. Áp dụng cache cho: departments (list + tree), job_titles, leave_types
5. Cache invalidation khi có write operation trên các entity này

**Verify:**
- Lần 1 gọi GET /departments → query DB (log thấy SQL)
- Lần 2 gọi → không thấy SQL (hit cache)
- Sau CREATE/UPDATE department → cache bị invalidate → lần sau query DB lại

---

### Slice 2 — N+1 Audit + Slow Query Log (High)

**Việc cần làm:**
1. Audit 5 hot endpoints với `DEBUG=True` → đếm số SQL queries per request
2. Thêm `selectinload`/`joinedload` tại các điểm N+1 tìm thấy
3. Thêm `SENTRY_DSN` config + Sentry init trong main.py (optional)
4. Verify: số SQL queries giảm, response time tốt hơn

---

### Slice 3 — Load Testing (Medium)

**Việc cần làm:**
1. Cài k6: `docker run --network host grafana/k6 run -`
2. Viết script `scripts/load_test.js`
3. Chạy với 200 concurrent, đo p95 response time
4. Fix bottleneck nếu p95 > 800ms
5. Document kết quả: "200 concurrent users — p95 = Xms"

---

## Rủi ro & Cách xử lý

| Rủi ro | Cách xử lý |
|---|---|
| Redis cache stale → hiển thị data cũ | TTL ngắn (1h), invalidate on write; cache chỉ áp dụng read-heavy data |
| Pool size quá lớn → vượt PostgreSQL max_connections | Default PG max_connections=100; với pool_size=20, max_overflow=40 → tối đa 60 connections (safe) |
| N+1 fix sai → trả dư data | Review SQL generated trong DEBUG, không thêm selectinload nếu không cần |
| Load test làm "tốn" auth tokens | Dùng user test riêng cho load test; không chạy trên prod DB |

---

## Checklist

- [ ] `pool_size=20, max_overflow=40, pool_pre_ping=True` đã cập nhật trong database.py
- [ ] `cache.py` viết xong và áp dụng cho departments, job_titles
- [ ] Invalidation hoạt động: update department → cache cleared
- [ ] Audit ít nhất 3 hot endpoints bằng SQL log → không còn N+1
- [ ] k6 load test: 200 users concurrent, p95 < 800ms
