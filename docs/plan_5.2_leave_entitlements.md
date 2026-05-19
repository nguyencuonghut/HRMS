# Kế hoạch thực hiện — 5.2. Quản lý số ngày phép

**Phạm vi:** Nạp phép năm, tính thâm niên, chuyển phép dư, theo dõi số ngày còn lại  
**Phụ thuộc:** 5.1 Danh mục loại nghỉ phép ✅ · Module nhân viên ✅

---

## Trạng thái hiện tại

| Thành phần | Trạng thái | Ghi chú |
|---|---|---|
| `LeaveType` với 6 trường quy tắc | ✅ Hoàn thành | `carryover_allowed`, `carryover_cutoff_month` sẵn sàng |
| Seed data 8 loại nghỉ phép | ✅ Hoàn thành | `annual_leave` đánh dấu `carryover_allowed=True` |
| `LeaveEntitlement` model | ❌ Chưa có | Bảng mới — lõi của 5.2 |
| Logic tính thâm niên (BLĐ 2019) | ❌ Chưa có | +1 ngày / 5 năm thâm niên |
| Bulk allocate phép năm | ❌ Chưa có | Nạp hàng loạt cho toàn công ty |
| Carryover khi sang năm mới | ❌ Chưa có | Tính dư năm trước → năm mới |
| Celery task reset carryover Q1 | ❌ Chưa có | Hủy dư cũ sau 31/03 |
| Frontend quản lý entitlements | ❌ Chưa có | View mới `/leave/entitlements` |
| Tests | ❌ Chưa có | |

---

## Phân tích kỹ thuật

### 1. Quy tắc tính phép năm (BLĐ 2019 Điều 113–114)

| Thâm niên (năm hoàn chỉnh) | Phép năm | Công thức |
|---|---|---|
| 0 – 4 năm | 12 ngày | base |
| 5 – 9 năm | 13 ngày | 12 + 1 |
| 10 – 14 năm | 14 ngày | 12 + 2 |
| 15 – 19 năm | 15 ngày | 12 + 3 |
| 20 – 24 năm | 16 ngày | 12 + 4 |
| cứ thêm 5 năm | +1 ngày | tiếp tục |

**Công thức:**
```python
def seniority_bonus(start_date: date, alloc_year: int) -> int:
    years_completed = alloc_year - start_date.year
    # Cần đủ năm tính đến 01/01 của năm phân bổ
    if date(alloc_year, 1, 1) < start_date.replace(year=alloc_year):
        years_completed -= 1
    return max(0, years_completed) // 5

def annual_allocation_days(employee: Employee, year: int) -> Decimal:
    return Decimal("12") + Decimal(seniority_bonus(employee.start_date, year))
```

> Điều 114 BLĐ 2019: "cứ đủ 5 năm làm việc liên tục thì được tăng thêm 1 ngày". Thâm niên tính từ `Employee.start_date`.

### 2. Quy tắc chuyển phép dư (quy định công ty)

Chỉ áp dụng cho các loại có `carryover_allowed = True` (hiện chỉ có `annual_leave`).

```
Khi nạp phép năm Y cho nhân viên A:
  1. Tìm entitlement (A, annual_leave, Y-1)
  2. Tính remaining_prev theo FIFO:
     if today > carryover_expires_{Y-1}:
       # Đã qua cutoff: carryover đã hết hạn, dùng FIFO
       used_from_regular = max(0, used_{Y-1} - carryover_{Y-1})
       remaining_prev = allocated_{Y-1} - used_from_regular
     else:
       remaining_prev = allocated_{Y-1} + carryover_{Y-1} - used_{Y-1}
  3. carryover_days_{Y} = max(0, remaining_prev)
  4. carryover_expires_{Y} = ngày cuối tháng carryover_cutoff_month của năm Y
     (ví dụ: annual_leave.carryover_cutoff_month = 3 → 31/03/Y)
```

**Ví dụ (FIFO — phép dư tiêu trước, phép năm tiêu sau):**

| Thời điểm | Nhân viên A — dùng **0 ngày** trước 01/04 |
|---|---|
| Cuối 2025: dư 4 ngày | `allocated=12, used=8, carryover=0` |
| Nạp phép 2026 | `allocated=12, carryover=4, carryover_expires=31/03/2026` |
| Trước 01/04/2026 | `remaining = 12 + 4 - 0 = 16` |
| Sau 01/04/2026 | `remaining = 12 - max(0, 0 - 4) = 12` (4 ngày dư bị hủy) ✅ |

| Thời điểm | Nhân viên B — dùng **5 ngày** trước 01/04 |
|---|---|
| Nạp phép 2026 | `allocated=12, carryover=4, used=5` |
| Trước 01/04/2026 | `remaining = 12 + 4 - 5 = 11` |
| Sau 01/04/2026 | `remaining = 12 - max(0, 5 - 4) = 12 - 1 = 11` (5 ngày dùng = 4 từ carryover + 1 từ regular) ✅ |

> **Nguyên tắc FIFO:** phép dư (carryover) được tiêu trước phép năm (allocated). Khi cutoff qua, chỉ phần carryover **chưa dùng** bị hủy. Phép năm regular không bị ảnh hưởng.

### 3. Schema `leave_entitlements`

```
id                PK
employee_id       FK → employees (ON DELETE CASCADE)
leave_type_id     FK → leave_types
year              INTEGER (2025, 2026, ...)
allocated_days    NUMERIC(5,1) NOT NULL DEFAULT 0
carryover_days    NUMERIC(5,1) NOT NULL DEFAULT 0
carryover_expires DATE nullable  -- null nếu loại phép không cho carryover
used_days         NUMERIC(5,1) NOT NULL DEFAULT 0   -- cập nhật bởi 5.3
note              TEXT nullable
created_by_id     FK → users nullable
created_at        TIMESTAMPTZ
updated_at        TIMESTAMPTZ nullable

UNIQUE (employee_id, leave_type_id, year)
```

`remaining_days` **không lưu vào DB** — tính khi trả về API theo quy tắc FIFO:
```python
@computed_field
@property
def remaining_days(self) -> float:
    allocated = float(self.allocated_days)
    carryover = float(self.carryover_days)
    used      = float(self.used_days)

    if self.carryover_expires and date.today() > self.carryover_expires:
        # Carryover đã hết hạn (FIFO: carryover tiêu trước → phần dư unused bị hủy)
        # used_days <= carryover → tất cả ngày dùng từ pool carryover, regular còn nguyên
        # used_days > carryover → (used - carryover) ngày dùng từ regular
        used_from_regular = max(0.0, used - carryover)
        return allocated - used_from_regular
    # Carryover còn hiệu lực: cộng đủ hai pool
    return allocated + carryover - used
```

**Bảng kiểm tra công thức:**

| `allocated` | `carryover` | `used` | Trước cutoff | Sau cutoff | Ghi chú |
|---|---|---|---|---|---|
| 12 | 4 | 0 | 16 | **12** | 4 ngày dư bị hủy |
| 12 | 4 | 5 | 11 | **11** | 5 dùng = 4 carryover + 1 regular |
| 12 | 4 | 4 | 12 | **12** | dùng hết đúng carryover |
| 12 | 4 | 16 | 0 | **0** | dùng hết cả hai pool |
| 12 | 4 | 18 | -2 | **-2** | dùng vượt phép (negative allowed) |

### 4. Bulk allocate — logic xử lý

`POST /leave-entitlements/bulk-allocate` nhận `year`, `leave_type_codes` (tuỳ chọn), `employee_ids` (tuỳ chọn):

```
Với mỗi nhân viên active (status != 'resigned'):
  Với mỗi leave_type cần nạp:
    1. Tính allocated_days:
       - annual_leave: 12 + seniority_bonus
       - Loại có max_days_per_year (paternity=14, bereavement=3...): dùng max_days_per_year
       - Loại không có max_days_per_year và không phải annual_leave: bỏ qua (nạp thủ công)
    2. Tính carryover_days (nếu leave_type.carryover_allowed):
       - Lấy entitlement năm trước → tính remaining_prev
    3. INSERT ... ON CONFLICT (employee_id, leave_type_id, year)
       DO UPDATE SET allocated_days, carryover_days, carryover_expires, note
       WHERE used_days = 0   -- không ghi đè nếu đã có giao dịch
  
  Trả về: { allocated: N, skipped: M, errors: [...] }
```

> **Nạp hàng loạt không tự động cho sick_leave và maternity_leave** — hai loại này phụ thuộc BHXH/tình trạng cá nhân, HR ghi nhận thủ công khi phát sinh ở 5.3.

### 5. Celery task reset carryover

`remaining_days` computed field đã tự xử lý đúng sau cutoff date — **không cần** task zero out `carryover_days`. Tuy nhiên, task vẫn hữu ích để:
1. Ghi nhận audit log "carryover bị hủy bao nhiêu ngày" cho từng NV
2. Tránh computed field phải tính lại nhiều lần khi bulk query

```python
# Task chạy 00:05 ngày 01/04 hàng năm
@shared_task(name="leave.reset_expired_carryover")
async def reset_expired_carryover_task():
    """
    Với mỗi entitlement có carryover hết hạn:
      - Tính unused_carryover = max(0, carryover_days - used_days)
      - Nếu unused_carryover > 0: ghi log, set carryover_days = 0
      - Nếu unused_carryover = 0: carryover đã được dùng hết trước cutoff, không cần làm gì
    """
    async with async_session_factory() as session:
        result = await session.execute(
            text("""
                UPDATE leave_entitlements
                SET carryover_days = 0,
                    updated_at     = now(),
                    note           = COALESCE(note || ' | ', '')
                                     || 'Hủy ' || GREATEST(0, carryover_days - used_days)::text
                                     || ' ngày dư [' || now()::date || ']'
                WHERE carryover_expires IS NOT NULL
                  AND carryover_expires < CURRENT_DATE
                  AND carryover_days > used_days   -- chỉ khi còn carryover chưa dùng hết
            """)
        )
        await session.commit()
        return {"reset_rows": result.rowcount}
```

> Điều kiện `carryover_days > used_days` (chứ không phải `carryover_days > 0`) đảm bảo task chỉ chạy với hàng còn carryover **chưa dùng hết** — idempotent và không ghi đè hàng đã clean.

Schedule (Celery Beat): `crontab(hour=0, minute=5, day_of_month=1, month_of_year=4)`

---

## Cấu trúc file mới / thay đổi

```
backend/
  alembic/versions/0014_create_leave_entitlements.py  (NEW)
  app/models/leave_entitlement.py                      (NEW)
  app/schemas/leave_entitlement.py                     (NEW)
  app/services/leave_entitlement_service.py            (NEW)
  app/api/v1/endpoints/leave_entitlements.py           (NEW)
  app/api/v1/router.py                                 (UPDATE — đăng ký router mới)
  app/tasks/leave_tasks.py                             (NEW — Celery task reset carryover)
  app/core/celery_app.py                               (UPDATE — đăng ký task + Beat schedule)
  tests/test_leave_entitlements.py                     (NEW)

frontend/
  src/views/leave/LeaveEntitlementView.vue             (NEW)
  src/services/leaveEntitlementService.ts              (NEW)
  src/router/index.ts                                  (UPDATE — route /leave/entitlements)
  src/components/layout/AppMenu.vue (hoặc tương đương) (UPDATE — menu item)
```

---

## Thiết kế Backend

### Bước 1 — Migration `0014_create_leave_entitlements.py`

```python
def upgrade():
    op.create_table(
        "leave_entitlements",
        sa.Column("id",                sa.Integer(),     primary_key=True),
        sa.Column("employee_id",       sa.Integer(),     sa.ForeignKey("employees.id",   ondelete="CASCADE"), nullable=False),
        sa.Column("leave_type_id",     sa.Integer(),     sa.ForeignKey("leave_types.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("year",              sa.Integer(),     nullable=False),
        sa.Column("allocated_days",    sa.Numeric(5, 1), nullable=False, server_default="0"),
        sa.Column("carryover_days",    sa.Numeric(5, 1), nullable=False, server_default="0"),
        sa.Column("carryover_expires", sa.Date(),        nullable=True),
        sa.Column("used_days",         sa.Numeric(5, 1), nullable=False, server_default="0"),
        sa.Column("note",              sa.Text(),        nullable=True),
        sa.Column("created_by_id",     sa.Integer(),     sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at",        sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at",        sa.TIMESTAMP(timezone=True), nullable=True),
        sa.UniqueConstraint("employee_id", "leave_type_id", "year", name="uq_leave_entitlement"),
    )
    op.create_index("ix_leave_entitlements_employee_year", "leave_entitlements", ["employee_id", "year"])
    op.create_index("ix_leave_entitlements_carryover_expires", "leave_entitlements", ["carryover_expires"])
```

### Bước 2 — Model `app/models/leave_entitlement.py`

```python
class LeaveEntitlement(SQLModel, table=True):
    __tablename__ = "leave_entitlements"

    id:                Optional[int] = Field(default=None, primary_key=True)
    employee_id:       int           = Field(foreign_key="employees.id")
    leave_type_id:     int           = Field(foreign_key="leave_types.id")
    year:              int
    allocated_days:    Decimal       = Field(default=Decimal("0"), sa_column=Column(sa.Numeric(5, 1)))
    carryover_days:    Decimal       = Field(default=Decimal("0"), sa_column=Column(sa.Numeric(5, 1)))
    carryover_expires: Optional[date] = Field(default=None)
    used_days:         Decimal       = Field(default=Decimal("0"), sa_column=Column(sa.Numeric(5, 1)))
    note:              Optional[str] = Field(default=None)
    created_by_id:     Optional[int] = Field(default=None, foreign_key="users.id")
    created_at:        datetime      = Field(default_factory=_utcnow)
    updated_at:        Optional[datetime] = Field(default=None)
```

### Bước 3 — Schema `app/schemas/leave_entitlement.py`

**`LeaveEntitlementRead`** — trả về API, có `remaining_days` computed:
```python
class LeaveEntitlementRead(BaseModel):
    id:                int
    employee_id:       int
    employee_code:     str          # join từ employee
    employee_name:     str          # join từ employee
    leave_type_id:     int
    leave_type_name:   str          # join từ leave_type
    year:              int
    allocated_days:    float
    carryover_days:    float
    carryover_expires: Optional[date]
    used_days:         float
    remaining_days:    float        # computed: see below
    note:              Optional[str]
    created_at:        datetime
    updated_at:        Optional[datetime]

    @computed_field
    @property
    def remaining_days(self) -> float:
        carryover = self.carryover_days
        if self.carryover_expires and date.today() > self.carryover_expires:
            carryover = 0.0
        return self.allocated_days + carryover - self.used_days
```

**`LeaveEntitlementCreate`** — tạo thủ công:
```python
class LeaveEntitlementCreate(BaseModel):
    employee_id:       int
    leave_type_id:     int
    year:              int = Field(ge=2020, le=2100)
    allocated_days:    float = Field(ge=0, le=365)
    carryover_days:    float = Field(default=0.0, ge=0, le=365)
    carryover_expires: Optional[date] = None
    note:              Optional[str] = None
```

**`LeaveEntitlementUpdate`**:
```python
class LeaveEntitlementUpdate(BaseModel):
    allocated_days:    Optional[float] = Field(default=None, ge=0, le=365)
    carryover_days:    Optional[float] = Field(default=None, ge=0, le=365)
    carryover_expires: Optional[date]  = None
    note:              Optional[str]   = None
```

**`BulkAllocateRequest`**:
```python
class BulkAllocateRequest(BaseModel):
    year:             int            = Field(ge=2020, le=2100)
    leave_type_codes: Optional[list[str]] = None  # None = chỉ annual_leave
    employee_ids:     Optional[list[int]] = None  # None = tất cả nhân viên active
    overwrite:        bool           = False  # True = ghi đè dù đã có giao dịch

class BulkAllocateResult(BaseModel):
    year:             int
    allocated:        int   # số bản ghi được tạo/cập nhật
    skipped:          int   # bỏ qua (đã có used_days > 0 và overwrite=False)
    errors:           list[str]
```

### Bước 4 — Service `leave_entitlement_service.py`

Các hàm chính:

```python
async def list_entitlements(
    session, *, employee_id=None, year=None, leave_type_id=None,
    department_id=None, page=1, page_size=20
) -> Page[LeaveEntitlementRead]: ...

async def get_entitlement(session, entitlement_id: int) -> LeaveEntitlementRead: ...

async def create_entitlement(
    session, data: LeaveEntitlementCreate, created_by_id: int
) -> LeaveEntitlementRead: ...

async def update_entitlement(
    session, entitlement_id: int, data: LeaveEntitlementUpdate
) -> LeaveEntitlementRead: ...

async def delete_entitlement(session, entitlement_id: int) -> None:
    # Chỉ xóa được nếu used_days == 0

async def bulk_allocate(
    session, req: BulkAllocateRequest, created_by_id: int
) -> BulkAllocateResult:
    # Nạp phép hàng loạt — logic tính seniority + carryover
    ...

def _compute_carryover(
    prev_entitlement: LeaveEntitlement | None,
    leave_type: LeaveType,
    alloc_year: int
) -> tuple[Decimal, date | None]:
    # Tính carryover_days và carryover_expires cho năm alloc_year
    ...

def _seniority_bonus(start_date: date, alloc_year: int) -> int: ...
```

### Bước 5 — API endpoints `leave_entitlements.py`

```
GET    /leave-entitlements                    list (filter: employee_id, year, leave_type_id, department_id)
GET    /leave-entitlements/{id}               get single
POST   /leave-entitlements                    create (Admin, HR Manager)
PUT    /leave-entitlements/{id}               update allocated_days, note (Admin, HR Manager)
DELETE /leave-entitlements/{id}               delete nếu used_days = 0 (Admin)
POST   /leave-entitlements/bulk-allocate      nạp phép hàng loạt (Admin, HR Manager)
GET    /leave-entitlements/summary            tổng hợp theo năm/phòng ban
```

**RBAC:**
| Action | Admin | HR Manager | HR Officer | Line Manager |
|---|---|---|---|---|
| list / get | ✅ | ✅ | ✅ (xem) | ✅ (phòng ban mình) |
| create / update | ✅ | ✅ | ❌ | ❌ |
| bulk-allocate | ✅ | ✅ | ❌ | ❌ |
| delete | ✅ | ❌ | ❌ | ❌ |

### Bước 6 — Celery task `leave_tasks.py`

```python
from celery import shared_task
from sqlalchemy import text

@shared_task(name="leave.reset_expired_carryover")
async def reset_expired_carryover_task():
    """Chạy 00:05 ngày 01/04 hàng năm — hủy carryover đã hết hạn."""
    async with async_session_factory() as session:
        result = await session.execute(
            text("""
                UPDATE leave_entitlements
                SET carryover_days = 0,
                    updated_at     = now(),
                    note           = COALESCE(note, '') || ' [Carryover reset ' || now()::date || ']'
                WHERE carryover_expires IS NOT NULL
                  AND carryover_expires < CURRENT_DATE
                  AND carryover_days > 0
            """)
        )
        await session.commit()
        return {"reset_count": result.rowcount}
```

**Đăng ký Beat schedule (trong `celery_app.py`):**
```python
beat_schedule={
    # ... tasks hiện có ...
    "reset-expired-carryover": {
        "task": "leave.reset_expired_carryover",
        "schedule": crontab(hour=0, minute=5, day_of_month=1, month_of_year=4),
    },
}
```

---

## Thiết kế Frontend

### Bước 7 — `LeaveEntitlementView.vue`

**Layout tổng thể:**
```
┌──────────────────────────────────────────────────────────────────┐
│  Quản lý số ngày phép          [Nạp phép hàng loạt] [Thêm thủ công]
│  Năm: [2026 ▼]  Phòng ban: [Tất cả ▼]  Loại phép: [Tất cả ▼]   │
│  Tìm kiếm: [___________________________]                          │
├──────────────────────────────────────────────────────────────────┤
│ Nhân viên │ Loại phép │ Cấp phép │ Chuyển dư │ Đã dùng │ Còn lại │ Hết hạn dư │ Sửa │
│ Nguyễn A  │ Phép năm  │   12.0   │    4.0    │   3.0   │  13.0   │ 31/03/2026 │  ✏️  │
│ Nguyễn A  │ Nghỉ tang │    3.0   │    0.0    │   0.0   │   3.0   │     —      │  ✏️  │
└──────────────────────────────────────────────────────────────────┘
```

**Màu sắc cột "Còn lại":**
- `remaining <= 0`: đỏ (`expired`)
- `remaining <= 2`: cam (`warning`)
- `remaining > 2`: bình thường

**Dialog Nạp phép hàng loạt:**
```
Nạp phép hàng loạt
─────────────────────────────────────
Năm phân bổ:     [2026        ]
Loại phép:       [Phép năm ▼  ]  (mặc định: annual_leave)
Nhân viên:       [Tất cả ▼    ]  (hoặc chọn phòng ban)
Ghi đè nếu đã có: [ ] (chỉ ghi đè nếu chưa có giao dịch)
─────────────────────────────────────
     [Hủy]    [Xem trước]  [Xác nhận nạp phép]
```

**Dialog Thêm/Sửa thủ công:**
```
Thêm ngày phép
─────────────────────────────────────
Nhân viên:   [Tìm nhân viên... ▼   ]
Loại phép:   [Phép năm          ▼   ]
Năm:         [2026               ]
Cấp phép:    [12.0               ] ngày
Chuyển dư:   [4.0                ] ngày
Hết hạn dư:  [31/03/2026         ]
Ghi chú:     [___________________  ]
─────────────────────────────────────
     [Hủy]    [Lưu]
```

### Route và menu

```typescript
// router/index.ts
{ path: '/leave/entitlements', component: LeaveEntitlementView, meta: { requiresAuth: true } }
```

Menu: thêm dưới mục "Nghỉ phép" (module 5):
```
📋 Nghỉ phép
  ├── Số ngày phép        /leave/entitlements
  └── Ghi nhận nghỉ phép  /leave/records       (5.3 — sẽ làm sau)
```

### Service `leaveEntitlementService.ts`

```typescript
export interface LeaveEntitlementRead {
  id: number
  employee_id: number
  employee_code: string
  employee_name: string
  leave_type_id: number
  leave_type_name: string
  year: number
  allocated_days: number
  carryover_days: number
  carryover_expires: string | null
  used_days: number
  remaining_days: number
  note: string | null
  created_at: string
  updated_at: string | null
}

export interface LeaveEntitlementCreate {
  employee_id: number
  leave_type_id: number
  year: number
  allocated_days: number
  carryover_days?: number
  carryover_expires?: string | null
  note?: string | null
}

export interface LeaveEntitlementUpdate {
  allocated_days?: number
  carryover_days?: number
  carryover_expires?: string | null
  note?: string | null
}

export interface BulkAllocateRequest {
  year: number
  leave_type_codes?: string[]
  employee_ids?: number[]
  overwrite?: boolean
}

export interface BulkAllocateResult {
  year: number
  allocated: number
  skipped: number
  errors: string[]
}

export default {
  list:          (params?) => api.get<Page<LeaveEntitlementRead>>('/leave-entitlements', { params }),
  get:           (id)      => api.get<LeaveEntitlementRead>(`/leave-entitlements/${id}`),
  create:        (data)    => api.post<LeaveEntitlementRead>('/leave-entitlements', data),
  update:        (id, data)=> api.put<LeaveEntitlementRead>(`/leave-entitlements/${id}`, data),
  delete:        (id)      => api.delete<{ message: string }>(`/leave-entitlements/${id}`),
  bulkAllocate:  (data)    => api.post<BulkAllocateResult>('/leave-entitlements/bulk-allocate', data),
  getSummary:    (params?) => api.get('/leave-entitlements/summary', { params }),
}
```

---

## Tests — `test_leave_entitlements.py`

```
# ── Tạo thủ công ──────────────────────────────────────────────────────
test_create_entitlement_manual
  → POST với đủ trường → 201, remaining_days = allocated - used

test_create_entitlement_duplicate_rejected
  → POST cùng (employee, leave_type, year) lần 2 → 409 Conflict

test_create_entitlement_invalid_allocated_days
  → allocated_days = -1 → 422

# ── remaining_days computation ─────────────────────────────────────────
test_remaining_days_no_carryover
  → allocated=12, carryover=0, used=3 → remaining=9

test_remaining_days_with_active_carryover
  → allocated=12, carryover=4, carryover_expires=future → remaining=16-used

test_remaining_days_with_expired_carryover
  → carryover_expires=past → remaining = allocated - used (carryover bị bỏ)

# ── Bulk allocate ──────────────────────────────────────────────────────
test_bulk_allocate_annual_leave_basic
  → Tạo employee, POST bulk-allocate year=2026
  → 201, result.allocated >= 1, entitlement.allocated_days = 12

test_bulk_allocate_seniority_bonus
  → Employee có start_date cách đây 6 năm
  → bulk-allocate → allocated_days = 13

test_bulk_allocate_with_carryover
  → Tạo entitlement 2025 (allocated=12, used=8)
  → bulk-allocate 2026 → carryover_days=4, carryover_expires=31/03/2026

test_bulk_allocate_skip_if_has_transactions
  → Tạo entitlement 2026 có used_days=2
  → bulk-allocate 2026 với overwrite=False → result.skipped=1

test_bulk_allocate_overwrite_flag
  → Tạo entitlement 2026 có used_days=2
  → bulk-allocate 2026 với overwrite=True → result.allocated=1

# ── Update & Delete ────────────────────────────────────────────────────
test_update_entitlement_allocated_days
  → PUT allocated_days=15 → 200, remaining thay đổi đúng

test_delete_entitlement_no_transactions
  → used_days=0 → DELETE → 204

test_delete_entitlement_with_transactions
  → used_days=3 → DELETE → 400 hoặc 409

# ── RBAC ──────────────────────────────────────────────────────────────
test_officer_cannot_create_entitlement
  → POST với token officer → 403

test_officer_can_list_entitlements
  → GET với token officer → 200

test_unauthenticated_rejected
  → GET không có token → 401
```

---

## Thứ tự triển khai

### Bước 1 — Migration
`0014_create_leave_entitlements.py` — tạo bảng `leave_entitlements` với unique constraint và index.

### Bước 2 — Model
`app/models/leave_entitlement.py` — SQLModel class.

### Bước 3 — Schema
`app/schemas/leave_entitlement.py` — Read (có `remaining_days` computed), Create, Update, BulkAllocateRequest/Result.

### Bước 4 — Service
`app/services/leave_entitlement_service.py`:
- CRUD cơ bản
- Hàm `_seniority_bonus` và `_compute_carryover`
- Hàm `bulk_allocate` (core logic của 5.2)

### Bước 5 — API + Router
`app/api/v1/endpoints/leave_entitlements.py` — 6 endpoints.  
`app/api/v1/router.py` — đăng ký prefix `/leave-entitlements`.

### Bước 6 — Celery task
`app/tasks/leave_tasks.py` — task `reset_expired_carryover_task`.  
`app/core/celery_app.py` — đăng ký Beat schedule.

### Bước 7 — Tests
`tests/test_leave_entitlements.py` — 15 test cases, chạy pytest pass.

### Bước 8 — Frontend
`src/services/leaveEntitlementService.ts` → service.  
`src/views/leave/LeaveEntitlementView.vue` → view chính.  
Route + menu item.

### Bước 9 — Verify
1. Migration chạy → bảng `leave_entitlements` có đầy đủ cột và constraint
2. `POST /leave-entitlements/bulk-allocate { year: 2026 }` → tất cả nhân viên active có entitlement
3. Employee thâm niên 6 năm → `allocated_days = 13`
4. `annual_leave` 2026 có `carryover_expires = 2026-03-31`
5. Frontend `/leave/entitlements` hiển thị bảng đúng màu còn lại

---

## Rủi ro & Cách xử lý

| Rủi ro | Cách xử lý |
|---|---|
| Duplicate khi bulk-allocate chạy 2 lần | `ON CONFLICT (employee_id, leave_type_id, year) DO UPDATE` — idempotent |
| Xóa entitlement có giao dịch (5.3) | Check `used_days > 0` trước khi xóa, trả 400 với message rõ ràng |
| `remaining_days < 0` (dùng vượt phép) | Cho phép âm — HR được phép ghi nhận vượt phép (5.3 xử lý cảnh báo) |
| Celery task không chạy đúng giờ | Task idempotent → có thể trigger thủ công qua API admin, hoặc tự recover lần sau |
| Tính thâm niên không chính xác | Test riêng cho `_seniority_bonus` với các mốc biên (năm thứ 5 đúng ngày) |
| `carryover_expires` tính sai tháng | Dùng `calendar.monthrange(year, month)[1]` để lấy ngày cuối tháng chính xác |

---

## Kết quả mong đợi sau 5.2

- HR có thể **nạp phép năm hàng loạt** bằng 1 thao tác: toàn bộ nhân viên active có entitlement cho năm mới, với thâm niên và carryover đã tính đúng
- **Phép dư năm trước** tự động mang sang, hiển thị ngày hết hạn 31/03
- Celery task **tự động hủy carryover** vào 01/04 — HR không cần thao tác thủ công
- Frontend hiển thị **trực quan số ngày còn lại** theo màu cảnh báo
- Sẵn sàng cho **5.3 ghi nhận nghỉ phép**: service 5.3 chỉ cần `UPDATE leave_entitlements SET used_days = used_days + days WHERE (employee_id, leave_type_id, year)`

---

## Liên kết với 5.3 (Ghi nhận nghỉ phép)

5.3 sẽ tạo bảng `leave_records` và:
- Khi ghi nhận 1 đợt nghỉ: tính số ngày → update `used_days` trong `leave_entitlements`
- Khi xóa/hủy ghi nhận: trừ ngược lại `used_days`
- Cảnh báo nếu `remaining_days` sau khi trừ < 0 (vượt phép)
- Hỗ trợ nửa ngày: `used_days` dạng `Numeric(5,1)` → cộng 0.5 được
