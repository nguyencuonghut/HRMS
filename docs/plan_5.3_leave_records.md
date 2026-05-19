# Kế hoạch thực hiện — 5.3. Ghi nhận nghỉ phép

**Phạm vi:** HR ghi nhận nghỉ phép cho nhân viên, tự động trừ `used_days` trong `leave_entitlements`  
**Phụ thuộc:** 5.1 Danh mục loại nghỉ phép ✅ · 5.2 Quản lý số ngày phép ✅

---

## Trạng thái hiện tại

| Thành phần | Trạng thái | Ghi chú |
|---|---|---|
| `LeaveType` 8 loại | ✅ Hoàn thành | `allow_half_day`, `max_days_per_year`, `count_public_holidays` sẵn sàng |
| `LeaveEntitlement` + bulk allocate | ✅ Hoàn thành | `used_days` chờ được cập nhật bởi 5.3 |
| `leave_records` bảng | ❌ Chưa có | Bảng mới — lõi của 5.3 |
| Tính số ngày nghỉ | ❌ Chưa có | Calendar days ± half-day offsets |
| Trừ `used_days` tự động | ❌ Chưa có | Cập nhật entitlement khi tạo/hủy |
| Frontend ghi nhận | ❌ Chưa có | View mới tại `/leaves` (route đã đăng ký) |
| Tests | ❌ Chưa có | |

---

## Phân tích kỹ thuật

### 1. Quy tắc tính số ngày nghỉ

**Nguyên tắc:** Đếm ngày dương lịch (không loại trừ weekend/lễ ở phase này — HR tự điều chỉnh thủ công nếu cần).

```
total_days = (end_date - start_date).days + 1
           - (0.5 if start_half == 'PM' else 0)
           - (0.5 if end_half == 'AM' else 0)
```

**Bảng kiểm tra:**

| Ngày bắt đầu | Nửa ngày đầu | Ngày kết thúc | Nửa ngày cuối | Tổng |
|---|---|---|---|---|
| 01/06 | — | 01/06 | — | **1.0** |
| 01/06 | PM | 01/06 | — | **0.5** |
| 01/06 | — | 01/06 | AM | **0.5** |
| 01/06 | PM | 02/06 | AM | **1.0** (2 days - 0.5 - 0.5) |
| 01/06 | — | 03/06 | — | **3.0** |
| 01/06 | PM | 05/06 | AM | **4.0** (5 days - 0.5 - 0.5) |

**Ràng buộc:**
- `start_date <= end_date`
- Nếu `start_date == end_date` và `start_half == 'PM'` và `end_half == 'AM'` → `total_days = 0` → reject
- `total_days >= 0.5`
- Nếu `leave_type.allow_half_day == False` → `start_half` và `end_half` phải là `None`

---

### 2. Cập nhật `used_days` trong `leave_entitlements`

**Logic FIFO:** `leave_entitlements.used_days` được cập nhật ngay khi tạo/hủy `leave_record`. `remaining_days` tự tính dựa trên `used_days` (không cần cập nhật gì thêm).

```
Tạo leave_record (status='active'):
  entitlement = find(employee_id, leave_type_id, year=start_date.year)
  if entitlement:
    entitlement.used_days += total_days
    # Nếu remaining_days < 0: cho phép nhưng trả về warning trong response

Hủy leave_record (status: active → cancelled):
  entitlement.used_days -= record.total_days
  entitlement.used_days = max(0, entitlement.used_days)  # tránh âm do race condition

Cập nhật leave_record (thay đổi ngày/nửa ngày):
  old_total = record.total_days  # trước khi sửa
  new_total = recalculate(...)
  entitlement.used_days += (new_total - old_total)
```

**Trường hợp không có entitlement:**
- Vẫn cho phép tạo `leave_record`
- Không cập nhật `used_days` (không có gì để cập nhật)
- Trả về `warning: "Chưa có phân bổ ngày phép cho năm này"`

**Liên kết cross-year:** Nếu `start_date` và `end_date` khác năm (ví dụ 28/12–03/01):
- Tách thành 2 phần: phần cuối năm cũ và phần đầu năm mới
- Deduct từ 2 entitlement tương ứng
- ⚠️ Phase này chưa hỗ trợ — reject nếu cross-year, yêu cầu HR tạo 2 record riêng

---

### 3. Schema `leave_records`

```
id                PK
employee_id       FK → employees (ON DELETE CASCADE)
leave_type_id     FK → leave_types (ON DELETE RESTRICT)
entitlement_id    FK → leave_entitlements nullable  (ON DELETE SET NULL)
start_date        DATE NOT NULL
end_date          DATE NOT NULL
start_half        VARCHAR(2) nullable   -- 'AM' | 'PM' (nửa ngày đầu bỏ qua)
end_half          VARCHAR(2) nullable   -- 'AM' | 'PM' (nửa ngày cuối bỏ qua)
total_days        NUMERIC(5,1) NOT NULL -- tính tự động, không cho nhập tay
reason            TEXT nullable
status            VARCHAR(20) NOT NULL DEFAULT 'active'  -- 'active' | 'cancelled'
cancel_reason     TEXT nullable
note              TEXT nullable
created_by_id     FK → users nullable
created_at        TIMESTAMPTZ
updated_at        TIMESTAMPTZ nullable

INDEX (employee_id, start_date, end_date)
INDEX (leave_type_id, start_date)
INDEX (entitlement_id)
```

**Về `entitlement_id`:** Lưu FK để audit trail. Nếu sau này entitlement bị xóa, record vẫn còn nguyên (SET NULL).

**Về `status`:** Chỉ 2 trạng thái đơn giản — không có "pending/approved" vì HR ghi nhận trực tiếp (không cần luồng phê duyệt theo FEATURES.md 5.3).

---

### 4. Tính `total_days` — hàm Python

```python
from datetime import date
from decimal import Decimal

def compute_total_days(
    start_date: date,
    end_date: date,
    start_half: str | None,   # 'PM' → bỏ buổi sáng ngày đầu
    end_half: str | None,     # 'AM' → bỏ buổi chiều ngày cuối
) -> Decimal:
    calendar_days = (end_date - start_date).days + 1
    offset = Decimal("0")
    if start_half == "PM":
        offset += Decimal("0.5")
    if end_half == "AM":
        offset += Decimal("0.5")
    total = Decimal(str(calendar_days)) - offset
    if total <= 0:
        raise ValueError("Số ngày nghỉ phải >= 0.5")
    return total
```

---

### 5. API endpoints

```
GET    /leave-records                    list (filter: employee_id, leave_type_id, year, status, date_from, date_to)
GET    /leave-records/{id}               get single
POST   /leave-records                    tạo mới (auto tính total_days, auto trừ used_days)
PUT    /leave-records/{id}               cập nhật (adjust used_days nếu thay đổi ngày)
DELETE /leave-records/{id}               xóa hẳn nếu status='active' VÀ used_days chưa bị dựa vào
POST   /leave-records/{id}/cancel        hủy (status → 'cancelled', hoàn trả used_days)
```

**RBAC:**
| Action | Admin | HR Manager | HR Officer | Line Manager |
|---|---|---|---|---|
| list / get | ✅ | ✅ | ✅ | ✅ (phòng ban) |
| create / update | ✅ | ✅ | ✅ | ❌ |
| cancel | ✅ | ✅ | ✅ | ❌ |
| delete (hard) | ✅ | ❌ | ❌ | ❌ |

---

### 6. Schema Pydantic

**`LeaveRecordRead`:**
```python
class LeaveRecordRead(BaseModel):
    id: int
    employee_id: int
    employee_code: str
    employee_name: str
    leave_type_id: int
    leave_type_name: str
    leave_type_code: str
    entitlement_id: int | None
    start_date: date
    end_date: date
    start_half: str | None
    end_half: str | None
    total_days: float
    reason: str | None
    status: str          # 'active' | 'cancelled'
    cancel_reason: str | None
    note: str | None
    created_by_id: int | None
    created_at: datetime
    updated_at: datetime | None
    # Thông tin entitlement đính kèm (nếu có)
    remaining_days_after: float | None   # remaining sau khi trừ record này
    warning: str | None                  # cảnh báo vượt phép
```

**`LeaveRecordCreate`:**
```python
class LeaveRecordCreate(BaseModel):
    employee_id: int
    leave_type_id: int
    start_date: date
    end_date: date
    start_half: Literal['AM', 'PM'] | None = None
    end_half:   Literal['AM', 'PM'] | None = None
    reason: str | None = None
    note: str | None = None

    @model_validator(mode='after')
    def validate_dates(self):
        if self.start_date > self.end_date:
            raise ValueError("start_date phải ≤ end_date")
        if self.start_date.year != self.end_date.year:
            raise ValueError("Không hỗ trợ ghi nhận nghỉ phép vắt qua năm — vui lòng tạo 2 bản ghi")
        return self
```

**`LeaveRecordUpdate`:**
```python
class LeaveRecordUpdate(BaseModel):
    start_date: date | None = None
    end_date:   date | None = None
    start_half: Literal['AM', 'PM'] | None = None   # None = xóa nửa ngày
    end_half:   Literal['AM', 'PM'] | None = None
    reason: str | None = None
    note: str | None = None
```

**`CancelRequest`:**
```python
class CancelRequest(BaseModel):
    cancel_reason: str | None = None
```

---

### 7. Service logic chi tiết

```python
async def create_record(session, data: LeaveRecordCreate, created_by_id: int) -> LeaveRecordRead:
    lt = await get_leave_type_or_404(session, data.leave_type_id)

    # Validate half-day
    if (data.start_half or data.end_half) and not lt.allow_half_day:
        raise HTTPException(400, "Loại phép này không hỗ trợ nghỉ nửa ngày")

    total = compute_total_days(data.start_date, data.end_date, data.start_half, data.end_half)

    # Tìm entitlement cho năm start_date
    year = data.start_date.year
    ent = await find_entitlement(session, data.employee_id, data.leave_type_id, year)

    warning = None
    if ent:
        ent.used_days += total
        remaining_after = compute_remaining(ent)
        if remaining_after < 0:
            warning = f"Vượt phép {abs(remaining_after)} ngày — remaining_days = {remaining_after}"
    else:
        warning = f"Chưa có phân bổ ngày phép {lt.name} năm {year} — không cập nhật used_days"
        remaining_after = None

    record = LeaveRecord(
        employee_id=data.employee_id,
        leave_type_id=data.leave_type_id,
        entitlement_id=ent.id if ent else None,
        start_date=data.start_date,
        end_date=data.end_date,
        start_half=data.start_half,
        end_half=data.end_half,
        total_days=total,
        reason=data.reason,
        note=data.note,
        status='active',
        created_by_id=created_by_id,
    )
    session.add(record)
    if ent:
        session.add(ent)
    await session.flush()
    return await _joined_read(session, record.id, warning=warning)


async def cancel_record(session, record_id: int, cancel_reason: str | None) -> LeaveRecordRead:
    record = await get_record_or_404(session, record_id)
    if record.status == 'cancelled':
        raise HTTPException(409, "Bản ghi đã bị hủy")

    # Hoàn trả used_days
    if record.entitlement_id:
        ent = await session.get(LeaveEntitlement, record.entitlement_id)
        if ent:
            ent.used_days = max(Decimal("0"), ent.used_days - record.total_days)
            session.add(ent)

    record.status = 'cancelled'
    record.cancel_reason = cancel_reason
    record.updated_at = utcnow()
    session.add(record)
    await session.flush()
    return await _joined_read(session, record_id)
```

---

## Cấu trúc file mới / thay đổi

```
backend/
  alembic/versions/0015_create_leave_records.py     (NEW)
  app/models/leave_record.py                         (NEW)
  app/schemas/leave_record.py                        (NEW)
  app/services/leave_record_service.py               (NEW)
  app/api/v1/endpoints/leave_records.py              (NEW)
  app/api/v1/router.py                               (UPDATE — đăng ký /leave-records)
  tests/test_leave_records.py                        (NEW)

frontend/
  src/services/leaveRecordService.ts                 (NEW)
  src/views/leaves/LeaveListView.vue                 (REPLACE — view placeholder hiện có)
  src/router/index.ts                                (giữ nguyên — route /leaves đã có)
```

> **`LeaveListView.vue`** là file placeholder đang ở route `/leaves` — sẽ được thay bằng UI ghi nhận nghỉ phép thực tế.

---

## Thiết kế Frontend

### Layout tổng thể

```
┌──────────────────────────────────────────────────────────────────┐
│  Ghi nhận nghỉ phép             [+ Thêm bản ghi]                 │
│  Năm: [2026 ▼]  Nhân viên: [___]  Loại phép: [Tất cả ▼]        │
│  Trạng thái: [Tất cả ▼]  Ngày từ: [___] đến: [___]              │
├──────────────────────────────────────────────────────────────────┤
│ Nhân viên │ Loại phép │ Từ ngày │ Đến ngày │ Ngày │ Lý do │ TT │
│ Trần Thị B│ Phép năm  │01/06/26 │ 03/06/26 │  3.0 │ Du lịch│ ● │
│ Lê Văn C  │ Nghỉ bệnh │10/06/26 │ 10/06/26 │  0.5 │ Ốm     │ ● │
│ ...       │           │         │          │      │        │ ✕ │
└──────────────────────────────────────────────────────────────────┘
```

**Badge trạng thái:**
- `active`: xanh (`success`)
- `cancelled`: xám (`secondary`)

**Dialog Thêm/Sửa:**
```
Ghi nhận nghỉ phép
─────────────────────────────────────
Nhân viên:    [Chọn nhân viên... ▼  ]
Loại phép:    [Phép năm ▼           ]
Ngày nghỉ từ: [01/06/2026          ]
             [x] Buổi chiều (PM)    ← chỉ hiện nếu allow_half_day
Ngày nghỉ đến:[03/06/2026          ]
             [ ] Buổi sáng (AM)     ← chỉ hiện nếu allow_half_day
Số ngày:      2.5 ngày              ← tính realtime khi chọn ngày
Lý do:        [____________________]
Ghi chú:      [____________________]
─────────────────────────────────────
Còn lại hiện tại: 12.0 ngày
Còn lại sau khi trừ: 9.5 ngày  ← highlight đỏ nếu âm
─────────────────────────────────────
     [Hủy]    [Lưu]
```

**Tính `total_days` realtime ở frontend:**
```typescript
function computeTotalDays(startDate: Date, endDate: Date, startPm: boolean, endAm: boolean): number {
  const ms = endDate.getTime() - startDate.getTime()
  const calendarDays = Math.round(ms / 86400000) + 1
  return calendarDays - (startPm ? 0.5 : 0) - (endAm ? 0.5 : 0)
}
```

---

## Tests — `test_leave_records.py`

```
# ── Tạo bản ghi ───────────────────────────────────────────────────
test_create_full_day
  → POST 1 ngày → 201, total_days=1.0, used_days cập nhật

test_create_half_day_start
  → start_half='PM', 1 ngày → total_days=0.5

test_create_multi_day_with_halfs
  → 5 ngày, start_half='PM', end_half='AM' → total_days=4.0

test_create_updates_used_days
  → Tạo record → entitlement.used_days tăng đúng total_days

test_create_warns_if_no_entitlement
  → Không có entitlement → 201 nhưng response.warning != null

test_create_warns_if_overspend
  → used + total > allocated + carryover → 201 nhưng warning về vượt phép

test_create_cross_year_rejected
  → start=2025-12-28, end=2026-01-03 → 422

test_create_half_day_on_no_half_day_type
  → leave_type.allow_half_day=False + start_half='PM' → 400

# ── Hủy bản ghi ───────────────────────────────────────────────────
test_cancel_restores_used_days
  → Cancel record → entitlement.used_days giảm đúng total_days

test_cancel_already_cancelled
  → Cancel lần 2 → 409

# ── Cập nhật ──────────────────────────────────────────────────────
test_update_dates_adjusts_used_days
  → PUT thay đổi end_date (tăng 1 ngày) → used_days tăng thêm 1

test_update_cancelled_record_rejected
  → PUT record đã hủy → 409

# ── Xóa ───────────────────────────────────────────────────────────
test_delete_active_record
  → DELETE → 204, used_days giảm

# ── List & Filter ─────────────────────────────────────────────────
test_list_by_employee
test_list_by_year
test_list_by_status_cancelled

# ── RBAC ──────────────────────────────────────────────────────────
test_officer_can_create
test_unauthenticated_rejected
```

---

## Thứ tự triển khai

### Bước 1 — Migration `0015_create_leave_records.py`
Tạo bảng `leave_records`, indexes, FKs.

### Bước 2 — Model `app/models/leave_record.py`
SQLModel class. Đăng ký trong `app/models/__init__.py`.

### Bước 3 — Schema `app/schemas/leave_record.py`
`LeaveRecordRead`, `LeaveRecordCreate`, `LeaveRecordUpdate`, `CancelRequest`.  
Hàm `compute_total_days` đặt trong schema hoặc service (dùng chung).

### Bước 4 — Service `app/services/leave_record_service.py`
CRUD + `create_record` (tính total, tìm entitlement, cập nhật used_days) + `cancel_record` (hoàn trả used_days) + `update_record` (tính lại delta).

### Bước 5 — API + Router
6 endpoints. Đăng ký prefix `/leave-records` trong `router.py`.

### Bước 6 — Tests
`tests/test_leave_records.py` — 16 test cases. Chạy pytest pass.

### Bước 7 — Frontend
`src/services/leaveRecordService.ts` → service.  
`src/views/leaves/LeaveListView.vue` → thay thế placeholder bằng view thực tế.

### Bước 8 — Verify
1. Migration chạy → bảng `leave_records` đầy đủ cột và constraint
2. Tạo record 3 ngày → `total_days=3.0`, `used_days` của entitlement tăng đúng
3. Hủy record → `used_days` hoàn trả
4. Ghi nhận nửa ngày (loại `annual_leave`) → `total_days=0.5`
5. Frontend `/leaves` hiển thị danh sách, dialog tính ngày realtime

---

## Rủi ro & Cách xử lý

| Rủi ro | Cách xử lý |
|---|---|
| Race condition khi 2 request đồng thời trừ used_days | `SELECT ... FOR UPDATE` trên entitlement row khi UPDATE |
| `used_days` âm sau khi hoàn trả | `max(0, used_days - total)` trong cancel logic |
| Nghỉ phép vắt qua năm (28/12 – 03/01) | Reject, yêu cầu tạo 2 record — note để hỗ trợ cross-year ở 5.4 |
| Xóa entitlement sau khi đã có record | `entitlement_id SET NULL` — record vẫn còn, used_days không hoàn trả tự động |
| Loại phép không có `allow_half_day` nhưng gửi `start_half` | Validate ở service level → 400 |
| Cập nhật record đã hủy | Reject với 409 |

---

## Liên kết với 5.2 và 5.4

**5.2 → 5.3:** `leave_entitlements.used_days` được cập nhật bởi 5.3 (hiện đang = 0 cho tất cả).

**5.3 → 5.4 (Báo cáo):** `leave_records` là nguồn dữ liệu cho báo cáo:
- Báo cáo số ngày đã dùng / còn lại: JOIN `leave_records` + `leave_entitlements`
- Báo cáo theo phòng ban: JOIN thêm `employees` + `org_history`
- Tồn phép cuối năm: `allocated - used` tại thời điểm 31/12
