# Kế hoạch thực hiện — 4.3. Nhắc tái ký hợp đồng

**Phạm vi:** Cảnh báo hợp đồng sắp hết hạn · Danh sách cần tái ký · Theo dõi trạng thái  
**Phụ thuộc:** `4.1 Hợp đồng lao động` ✅

---

## Trạng thái hiện tại

| Thành phần | Trạng thái | Ghi chú |
|---|---|---|
| `reminder_service._get_contract_expiries()` | ✅ Đã có | Lọc HĐ hết hạn trong N ngày |
| `GET /api/v1/reminders?types=contract_expiry` | ✅ Đã có | Trả `ReminderItem` với `extra.contract_id` |
| `list_contracts_global(expiring_within=N)` | ✅ Đã có | Filter trong `employee_contract_service` |
| `ContractRead.days_until_expiry` | ✅ Đã có | Tính sẵn từ `effective_to - today` |
| `ContractRead.status_display` | ✅ Đã có | Hiển thị "Hết hạn (X ngày trước)" / "Còn X ngày" |
| **`ContractRead.employee_name`** (global list) | ❌ Thiếu | Join Employee đã có nhưng field bị bỏ qua |
| **Celery auto-expire task** | ❌ Chưa có | `status` vẫn = "active" dù `effective_to < today` |
| **`reminderService.ts` — type `contract_expiry`** | ❌ Thiếu | `EventType` thiếu, `RemindersResponse` thiếu field |
| **`RemindersView.vue` — card + bảng HĐ sắp HH** | ❌ Thiếu | Data có sẵn từ API nhưng không hiển thị |
| **`ContractListView.vue` — employee_name** | ❌ Chỉ hiện `#ID` | Cần tên NV trong danh sách toàn công ty |
| **`ContractListView.vue` — urgency badge** | ❌ Thiếu | Badge màu theo độ khẩn cấp |
| **Nút "Tái ký"** | ❌ Thiếu | Quick action từ danh sách sắp HH |

---

## Phân tích kỹ thuật

### 1. Vì sao `status` không tự chuyển sang "expired"?

Model `EmployeeContract.status` là trường DB — không tự cập nhật khi `effective_to` qua ngày.  
`status_display` trong schema Python **đã tính đúng** ("Hết hạn"), nhưng giá trị DB vẫn là "active".

Hệ quả: `GET /contracts?status=expired` trả kết quả rỗng dù thực tế có HĐ hết hạn.

**Giải pháp:** Celery Beat task chạy 00:05 mỗi ngày — bulk-update `status = 'expired'` cho toàn bộ HĐ quá hạn.

```
Điều kiện cập nhật:
  effective_to < today
  AND status IN ('active', 'draft')
  AND effective_to IS NOT NULL
```

### 2. `employee_name` trong global list

`list_contracts_global()` đã JOIN `Employee` nhưng kết quả bị bỏ qua:
```python
# Hiện tại:
items = [_to_read(c, cat.name) for c, cat, _ in rows]  # _ = emp bị ignore
```

Cần thêm `employee_name` và `employee_code` vào `ContractRead` (optional — không bắt buộc cho per-employee endpoints).

### 3. "Tái ký" tracking — thiết kế đơn giản

Không cần migration DB. Trạng thái tái ký được **suy ra ngầm**:
- **"Cần tái ký"**: `days_until_expiry in [0, 30]` — HĐ sắp hết / đã hết, chưa có HĐ mới
- **"Đã tái ký"**: NV đã có HĐ mới `effective_from >= effective_to` của HĐ cũ trong cùng nhóm
- Frontend hiển thị badge màu + link "Tái ký ngay" → mở employee profile tại tab Hợp đồng

Không thêm cột DB — HR tái ký bằng cách vào hồ sơ NV → Thêm HĐ mới. HĐ cũ tự chuyển "expired".

### 4. Celery infrastructure

Hiện `requirements.txt` đã có `celery[redis]>=5.4.0` và `redis>=5.0.0`, `REDIS_URL` trong settings, thư mục `app/workers/` đã tạo nhưng trống.  
Cần:
- `app/core/celery_app.py` — khởi tạo Celery + beat schedule
- `app/workers/__init__.py` + `app/workers/tasks.py` — task auto-expire
- Docker Compose: thêm service `celery_worker` và `celery_beat`

---

## Cấu trúc file mới / thay đổi

```
backend/
  app/core/celery_app.py                     (NEW — Celery init + beat schedule)
  app/workers/__init__.py                    (NEW — empty)
  app/workers/tasks.py                       (NEW — expire_overdue_contracts task)
  app/schemas/employee_contract.py           (UPDATE — thêm employee_name, employee_code)
  app/services/employee_contract_service.py  (UPDATE — _to_read nhận employee_name)
  tests/test_contract_renewal.py             (NEW — 8 tests)
  docker-compose.yml                         (UPDATE — thêm celery_worker + celery_beat)

frontend/
  src/services/reminderService.ts            (UPDATE — thêm contract_expiry type)
  src/views/RemindersView.vue                (UPDATE — card + filter + rows HĐ sắp HH)
  src/views/contracts/ContractListView.vue   (UPDATE — employee_name, urgency badge, tái ký action)
```

---

## Thiết kế Backend

### 5. `app/core/celery_app.py`

```python
from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "hrms",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"],
)

celery_app.conf.beat_schedule = {
    "expire-overdue-contracts": {
        "task": "app.workers.tasks.expire_overdue_contracts",
        "schedule": crontab(hour=0, minute=5),   # 00:05 hàng ngày
    },
}
celery_app.conf.timezone = "Asia/Ho_Chi_Minh"
```

### 6. `app/workers/tasks.py`

```python
import asyncio
from datetime import date

from sqlalchemy import update
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.celery_app import celery_app
from app.core.config import settings
from app.models.employee_contract import EmployeeContract


@celery_app.task(name="app.workers.tasks.expire_overdue_contracts")
def expire_overdue_contracts() -> int:
    """
    Cập nhật status = 'expired' cho tất cả HĐ quá hạn.
    Trả về số bản ghi đã cập nhật.
    """
    async def _run() -> int:
        engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
        SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
        async with SessionLocal() as session:
            result = await session.execute(
                update(EmployeeContract)
                .where(
                    EmployeeContract.effective_to < date.today(),
                    EmployeeContract.effective_to.isnot(None),
                    EmployeeContract.status.in_(["active", "draft"]),
                )
                .values(status="expired")
                .execution_options(synchronize_session=False)
            )
            await session.commit()
            return result.rowcount
        finally:
            await engine.dispose()

    return asyncio.run(_run())
```

### 7. `ContractRead` — thêm `employee_name` / `employee_code`

```python
class ContractRead(BaseModel):
    # ... existing fields ...
    employee_name: Optional[str] = None    # Chỉ populated trong global list
    employee_code: Optional[str] = None    # Mã hiển thị (dạng "HC0011")
```

`_to_read()` cập nhật:
```python
def _to_read(
    c: EmployeeContract,
    category_name: str,
    appendices: list[ContractRead] | None = None,
    employee_name: str | None = None,
    employee_code: str | None = None,
) -> ContractRead:
    ...
```

`list_contracts_global()` cập nhật:
```python
items = [
    _to_read(c, cat.name, employee_name=emp.full_name, employee_code=str(emp.employee_seq))
    for c, cat, emp in rows
]
```

---

## Thiết kế Frontend

### 8. `reminderService.ts` — thêm `contract_expiry`

```typescript
export type EventType = 'birthday' | 'anniversary' | 'probation_end' | 'contract_expiry'

export interface RemindersResponse {
  birthday:        ReminderItem[]
  anniversary:     ReminderItem[]
  probation_end:   ReminderItem[]
  contract_expiry: ReminderItem[]   // NEW
  total:           number
}

export const EVENT_TYPE_LABELS: Record<EventType, string> = {
  birthday:        'Sinh nhật',
  anniversary:     'Thâm niên',
  probation_end:   'Hết thử việc',
  contract_expiry: 'HĐ sắp hết hạn',   // NEW
}

export const EVENT_TYPE_ICONS: Record<EventType, string> = {
  birthday:        '🎂',
  anniversary:     '⭐',
  probation_end:   '📋',
  contract_expiry: '📄',   // NEW
}
```

### 9. `RemindersView.vue` — card + filter + column

**Summary cards:**
```
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐
│ 🎂  3    │  │ ⭐  1    │  │ 📋  2    │  │ 📄  5            │
│ Sinh nhật│  │ Thâm niên│  │Hết thử VL│  │ HĐ sắp hết hạn   │
└──────────┘  └──────────┘  └──────────┘  └──────────────────┘
```

**typeOptions** thêm:
```javascript
{ label: 'HĐ sắp hết hạn', value: 'contract_expiry' }
```

**allItems computed** thêm `...data.contract_expiry`

**DataTable column "Loại"** — khi `contract_expiry`:
```html
<span>📄 HĐ sắp hết hạn</span>
<span class="muted-text">#{{ row.extra.contract_number }}</span>
```

Click row → `router.push('/employees/' + row.employee_id + '?tab=contracts')`

### 10. `ContractListView.vue` — nâng cấp

**Cột "Nhân viên"** (thay vì `#employee_id`):
```html
<Column header="Nhân viên">
  <template #body="{ data }">
    <router-link :to="`/employees/${data.employee_id}`">
      <div style="font-weight:500;">{{ data.employee_name ?? '—' }}</div>
      <div class="muted-text">{{ data.employee_code ? `#${data.employee_code}` : `#${data.employee_id}` }}</div>
    </router-link>
  </template>
</Column>
```

**Cột "Còn lại"** — badge màu theo urgency:
```html
<Column header="Còn lại" style="width:110px;">
  <template #body="{ data }">
    <span v-if="data.days_until_expiry !== null"
          :class="['days-badge', urgencyClass(data.days_until_expiry)]">
      {{ data.days_until_expiry <= 0 ? 'Hết hạn' : `${data.days_until_expiry} ngày` }}
    </span>
    <span v-else class="muted-text">—</span>
  </template>
</Column>
```

```typescript
function urgencyClass(days: number | null): string {
  if (days === null) return ''
  if (days <= 0)  return 'expired'
  if (days <= 7)  return 'critical'  // đỏ
  if (days <= 15) return 'warning'   // vàng
  if (days <= 30) return 'soon'      // cam
  return 'ok'
}
```

**Nút "Tái ký"** trong cột Actions (chỉ hiện khi `days_until_expiry` trong [-30, 30]):
```html
<Button
  icon="pi pi-replay"
  text rounded size="small"
  v-tooltip.top="'Tái ký — mở hồ sơ nhân viên'"
  @click="router.push(`/employees/${data.employee_id}?tab=contracts`)"
/>
```

**Preset filter URL** — từ RemindersView có thể navigate đến:
```
/contracts?expiring_within=30
```
ContractListView đọc query param khi mount để pre-fill bộ lọc.

---

## Tests — `test_contract_renewal.py`

```
test_expire_overdue_task_marks_status         — Celery task: HĐ quá hạn → status=expired
test_expire_overdue_task_skips_terminated     — HĐ terminated không bị thay đổi
test_expire_overdue_task_skips_indefinite     — HĐ vô thời hạn (effective_to=NULL) không bị thay đổi
test_expire_overdue_task_returns_count        — Task trả số bản ghi đã cập nhật

test_global_list_includes_employee_name       — GET /contracts trả employee_name trong items
test_global_list_expiring_filter_sorts_asc    — expiring_within → sort theo effective_to asc

test_reminder_contract_expiry_in_30d          — GET /reminders?types=contract_expiry&days=30 → đúng
test_reminder_contract_expiry_extra_fields    — extra.contract_number + extra.contract_id có mặt
```

---

## Docker Compose — thêm Celery services

```yaml
  celery_worker:
    build: ./backend
    command: celery -A app.core.celery_app.celery_app worker --loglevel=info
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=redis://redis:6379/0
    depends_on: [db, redis]
    volumes:
      - ./backend:/app

  celery_beat:
    build: ./backend
    command: celery -A app.core.celery_app.celery_app beat --loglevel=info
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=redis://redis:6379/0
    depends_on: [db, redis, celery_worker]
    volumes:
      - ./backend:/app
```

---

## Thứ tự triển khai

### Bước 1 — Backend: Celery auto-expire + employee_name trong ContractRead
1. Tạo `app/core/celery_app.py` — Celery app + beat schedule
2. Tạo `app/workers/__init__.py` (trống) + `app/workers/tasks.py` — task expire
3. Cập nhật `app/schemas/employee_contract.py` — thêm `employee_name`, `employee_code`
4. Cập nhật `_to_read()` và `list_contracts_global()` trong service
5. Cập nhật `docker-compose.yml` — thêm `celery_worker`, `celery_beat`

### Bước 2 — Frontend: Fix `reminderService.ts`
1. Thêm `'contract_expiry'` vào `EventType`
2. Thêm `contract_expiry: ReminderItem[]` vào `RemindersResponse`
3. Thêm label + icon cho `contract_expiry`

### Bước 3 — Frontend: Update `RemindersView.vue`
1. Thêm card summary "HĐ sắp hết hạn"
2. Thêm `contract_expiry` vào `typeOptions` và `allItems`
3. Hiển thị `extra.contract_number` trong DataTable row
4. Click row → navigate `/employees/{id}?tab=contracts`

### Bước 4 — Frontend: Nâng cấp `ContractListView.vue`
1. Cột "Nhân viên": hiển thị `employee_name` + `employee_code`
2. Thêm cột "Còn lại" với badge màu theo urgency
3. Thêm nút "Tái ký" navigate to employee profile
4. Đọc query param `expiring_within` từ URL khi mount (deep-link từ RemindersView)

### Bước 5 — Tests
1. Tạo `tests/test_contract_renewal.py` — 8 test cases
2. Chạy pytest toàn bộ — tất cả pass

### Bước 6 — Verify
1. Chạy task thủ công: `celery -A ... call app.workers.tasks.expire_overdue_contracts`
2. Kiểm tra `/contracts?status=expired` trả data thực
3. Mở `/reminders` → thấy card "HĐ sắp hết hạn" + rows trong bảng
4. Mở `/contracts?expiring_within=30` → thấy employee_name, urgency badge
5. Click nút "Tái ký" → mở đúng hồ sơ NV tại tab Hợp đồng

---

## Rủi ro & Cách xử lý

| Rủi ro | Cách xử lý |
|---|---|
| Celery task chạy lại nhiều lần / duplicate update | `update().where(status IN ['active','draft'])` — idempotent, chạy N lần vẫn an toàn |
| Docker Compose chưa có Redis exposed | Redis đã có trong compose (`hrms-redis-1`), chỉ cần thêm worker/beat service |
| `employee_name = None` ở per-employee endpoints | Field `Optional[str] = None` — backward compatible, không break existing tests |
| NV có nhiều HĐ sắp hết hạn cùng lúc | `_get_contract_expiries()` trả từng HĐ riêng → mỗi row là 1 HĐ |
| Task không chạy khi Celery chưa start | Status vẫn được hiển thị đúng qua `status_display` (tính on-read) — chỉ filter `status=expired` bị ảnh hưởng |

---

## Kết quả mong đợi sau 4.3

- Trang **Nhắc nhở** hiển thị đầy đủ 4 loại: sinh nhật, thâm niên, hết thử việc, **HĐ sắp hết hạn**
- Badge sidebar hiển thị **tổng số sự kiện** bao gồm HĐ sắp hết hạn
- Trang **Hợp đồng** hiển thị tên nhân viên, badge urgency màu đỏ/vàng/cam cho HĐ gần hết hạn
- Filter `Sắp hết hạn: 7/30/60/90 ngày tới` hoạt động đúng với status thực tế trong DB
- HR click "Tái ký" → mở thẳng tab Hợp đồng của nhân viên để tạo HĐ mới
- Hàng đêm Celery tự động đánh dấu HĐ quá hạn → filter `status=expired` cho kết quả chính xác
