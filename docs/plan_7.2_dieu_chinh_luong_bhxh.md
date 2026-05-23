# Kế hoạch triển khai — 7.2. Điều chỉnh lương BHXH

**Phạm vi chính:** Tạo quyết định điều chỉnh mức lương BHXH · Tự động cập nhật profile + tạo InsuranceChangeEvent · Xem lịch sử điều chỉnh theo nhân viên  
**Phụ thuộc hoàn thành:** `7.1 Mức lương BHXH` ✅ · `6.1 Thông tin bảo hiểm nhân viên` ✅ (bảng `employee_insurance_profiles`) · `6.3 Biến động BHXH` ✅ (bảng `insurance_change_events`, `change_reason='manual_correction'` đã hợp lệ)  
**Căn cứ pháp lý:**
- Thông tư 59/2015/TT-BLĐTBXH Điều 26 — thay đổi mức đóng BHXH phải thông báo cơ quan BHXH
- Quyết định 595/QĐ-BHXH (2017) — biến động tăng/giảm mức đóng qua D02-TS

---

## Nguyên tắc thiết kế

| Nguyên tắc | Mô tả |
|---|---|
| **Model mới `BhxhSalaryAdjustment`** | Lưu toàn bộ audit trail: mức cũ, mức mới, ngày hiệu lực, lý do, số quyết định, người tạo |
| **Side effects nguyên tử** | Khi tạo adjustment: (1) cập nhật `insurance_basis_amount` + `source='manual_fixed'` trong profile, (2) tạo `InsuranceChangeEvent` với `change_reason='manual_correction'`, (3) ghi AuditLog — tất cả trong 1 transaction |
| **Bất biến về lịch sử** | Adjustment đã tạo không được sửa/xóa — chỉ tạo adjustment mới đảo ngược |
| **Tích hợp 6.3 / 7.1** | InsuranceChangeEvent tạo ra sẽ xuất hiện trong danh sách biến động 6.3 và timeline lịch sử 7.1 |
| **Không scoped CSS** | Style dùng global class trong `_salary.scss` |

---

## Thiết kế dữ liệu

### Model `BhxhSalaryAdjustment` — bảng `bhxh_salary_adjustments`

```sql
CREATE TABLE bhxh_salary_adjustments (
    id                  SERIAL PRIMARY KEY,

    -- Nhân viên được điều chỉnh
    employee_id         INT NOT NULL REFERENCES employees(id) ON DELETE RESTRICT,

    -- Quyết định điều chỉnh
    decision_number     VARCHAR(100),           -- số quyết định (tùy chọn, vd: "QĐ-045/2026")
    old_basis_amount    NUMERIC(18,2) NOT NULL, -- mức lương BHXH trước khi điều chỉnh (snapshot)
    new_basis_amount    NUMERIC(18,2) NOT NULL, -- mức lương BHXH mới
    effective_date      DATE NOT NULL,          -- ngày hiệu lực của mức mới

    -- Lý do + ghi chú
    reason              TEXT NOT NULL,          -- bắt buộc (vd: "Nâng lương năm 2026")

    -- Audit trail
    created_by_id       INT REFERENCES users(id) ON DELETE SET NULL,
    created_at          TIMESTAMP NOT NULL DEFAULT now(),

    -- Liên kết với sự kiện biến động (tự động tạo khi adjustment được tạo)
    insurance_change_event_id  INT REFERENCES insurance_change_events(id) ON DELETE SET NULL,

    CONSTRAINT ck_bsa_amounts_positive  CHECK (old_basis_amount > 0 AND new_basis_amount > 0),
    CONSTRAINT ck_bsa_amounts_different CHECK (old_basis_amount != new_basis_amount)
);

CREATE INDEX ix_bsa_employee_id    ON bhxh_salary_adjustments(employee_id);
CREATE INDEX ix_bsa_effective_date ON bhxh_salary_adjustments(effective_date);
CREATE INDEX ix_bsa_created_at     ON bhxh_salary_adjustments(created_at DESC);
```

### Migration `0024_create_bhxh_salary_adjustments.py`

```python
# backend/alembic/versions/0024_create_bhxh_salary_adjustments.py
"""create bhxh_salary_adjustments table

Revision ID: 0024
Revises: 0023
Create Date: 2026-05-22
"""

def upgrade() -> None:
    op.create_table(
        "bhxh_salary_adjustments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("decision_number", sa.String(100), nullable=True),
        sa.Column("old_basis_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("new_basis_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("insurance_change_event_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["insurance_change_event_id"], ["insurance_change_events.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("old_basis_amount > 0 AND new_basis_amount > 0", name="ck_bsa_amounts_positive"),
        sa.CheckConstraint("old_basis_amount != new_basis_amount", name="ck_bsa_amounts_different"),
    )
    op.create_index("ix_bsa_employee_id",    "bhxh_salary_adjustments", ["employee_id"])
    op.create_index("ix_bsa_effective_date", "bhxh_salary_adjustments", ["effective_date"])
    op.create_index("ix_bsa_created_at",     "bhxh_salary_adjustments", ["created_at"])

def downgrade() -> None:
    op.drop_index("ix_bsa_created_at",     "bhxh_salary_adjustments")
    op.drop_index("ix_bsa_effective_date", "bhxh_salary_adjustments")
    op.drop_index("ix_bsa_employee_id",    "bhxh_salary_adjustments")
    op.drop_table("bhxh_salary_adjustments")
```

### SQLModel class

```python
# backend/app/models/salary_adjustment.py  (NEW)
class BhxhSalaryAdjustment(SQLModel, table=True):
    __tablename__ = "bhxh_salary_adjustments"

    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(foreign_key="employees.id")
    decision_number: Optional[str] = Field(default=None, max_length=100)
    old_basis_amount: Decimal = Field(sa_column=Column(sa.Numeric(18, 2), nullable=False))
    new_basis_amount: Decimal = Field(sa_column=Column(sa.Numeric(18, 2), nullable=False))
    effective_date: date = Field(nullable=False)
    reason: str = Field(sa_column=Column(sa.Text, nullable=False))
    created_by_id: Optional[int] = Field(default=None, foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    insurance_change_event_id: Optional[int] = Field(
        default=None, foreign_key="insurance_change_events.id"
    )
```

---

## Side Effects khi tạo Adjustment

### Flow nguyên tử (1 transaction)

```
POST /salary/adjustments
  body: { employee_id, new_basis_amount, effective_date, reason, decision_number? }

  Bước 1: Validate
    - employee tồn tại và có insurance_profile
    - new_basis_amount > 0
    - new_basis_amount != profile.insurance_basis_amount (không điều chỉnh về cùng mức)
    - effective_date <= today (không điều chỉnh tương lai quá 1 năm)

  Bước 2: Snapshot old_basis_amount
    old_basis_amount = profile.insurance_basis_amount

  Bước 3: Tạo BhxhSalaryAdjustment record (chưa có insurance_change_event_id)

  Bước 4: Tạo InsuranceChangeEvent
    change_type    = 'increase' nếu new > old, 'decrease' nếu new < old
    change_reason  = 'manual_correction'
    basis_amount   = new_basis_amount
    effective_date = adjustment.effective_date
    note           = f"Điều chỉnh lương BHXH: {old} → {new}. {reason}"
    (Snapshot các trường còn lại từ employee + insurance_profile)

  Bước 5: Cập nhật EmployeeInsuranceProfile
    profile.insurance_basis_amount = new_basis_amount
    profile.insurance_basis_source = 'manual_fixed'

  Bước 6: Cập nhật adjustment.insurance_change_event_id = event.id

  Bước 7: Ghi AuditLog
    action        = 'bhxh_salary_adjustment_created'
    resource_type = 'employee'
    resource_id   = employee_id
    detail        = { adjustment_id, old_basis_amount, new_basis_amount, effective_date }

  Bước 8: Commit transaction
```

### Mapping `change_reason='manual_correction'` vào `InsuranceChangeEvent`

```python
# change_reason đã tồn tại trong constraint của insurance_change_events:
# 'manual_correction' — dùng cho mọi điều chỉnh thủ công từ 7.2

# Trong InsuranceChangeEvent snapshot, điền đầy đủ:
employee_snapshot_name     = employee.full_name
employee_snapshot_code     = employee.employee_code
bhxh_code                  = insurance_profile.bhxh_code (nếu có)
basis_amount               = new_basis_amount
change_type                = 'increase' | 'decrease'
change_reason              = 'manual_correction'
effective_date             = adjustment.effective_date
suggested_declaration_year = effective_date.year
suggested_declaration_month = effective_date.month
# → event tự động xuất hiện trong 6.3 để nạp vào báo cáo 6.4 nếu cần
```

---

## Thiết kế API

### Endpoints

```
POST   /salary/adjustments
       body: BhxhSalaryAdjustmentCreate
       → BhxhSalaryAdjustmentRead (201 Created)

GET    /salary/adjustments
       ?employee_id=&page=&page_size=&from_date=&to_date=
       → BhxhSalaryAdjustmentListPage

GET    /salary/employees/{employee_id}/adjustment-history
       → list[BhxhSalaryAdjustmentRead]
       (Đây là nguồn 2 cho timeline trong 7.1 — sorted DESC by effective_date)

GET    /salary/adjustments/{adjustment_id}
       → BhxhSalaryAdjustmentRead
```

> Không có PUT / DELETE — adjustment là immutable. Nếu cần hủy: tạo adjustment mới đảo ngược.

### Schemas

```python
class BhxhSalaryAdjustmentCreate(BaseModel):
    employee_id: int
    new_basis_amount: Decimal                       # > 0
    effective_date: date                            # phải <= today + 365 ngày
    reason: str = Field(min_length=5, max_length=500)
    decision_number: str | None = Field(default=None, max_length=100)

    @field_validator("new_basis_amount")
    def must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("Mức lương BHXH phải > 0")
        return v

class BhxhSalaryAdjustmentRead(BaseModel):
    id: int
    employee_id: int
    employee_code: str                              # join
    employee_name: str                              # join
    department_name: str | None                    # join
    decision_number: str | None
    old_basis_amount: Decimal
    new_basis_amount: Decimal
    change_direction: Literal['increase', 'decrease']  # computed
    change_amount: Decimal                          # abs(new - old)
    change_pct: float                               # (new-old)/old * 100
    effective_date: date
    reason: str
    created_by_id: int | None
    created_by_name: str | None                    # join
    created_at: datetime
    insurance_change_event_id: int | None

class BhxhSalaryAdjustmentListPage(BaseModel):
    items: list[BhxhSalaryAdjustmentRead]
    total: int
    page: int
    page_size: int
```

---

## Thiết kế Backend

### Files cần tạo / sửa

```
backend/alembic/versions/0024_create_bhxh_salary_adjustments.py    (NEW)
backend/app/models/salary_adjustment.py                             (NEW)
backend/app/models/__init__.py                                      (EDIT: import BhxhSalaryAdjustment)
backend/app/schemas/salary.py                                       (EDIT: thêm adjustment schemas)
backend/app/services/salary_service.py                              (EDIT: thêm adjustment functions)
backend/app/api/v1/endpoints/salary.py                              (EDIT: thêm adjustment endpoints)
```

### `salary_service.py` — các hàm điều chỉnh

```python
async def create_bhxh_adjustment(
    session: AsyncSession,
    data: BhxhSalaryAdjustmentCreate,
    created_by_id: int,
) -> BhxhSalaryAdjustmentRead:
    """
    Tạo điều chỉnh lương BHXH nguyên tử.
    Thực thi 8 bước như mô tả trong flow phía trên.
    Raise HTTP 400 nếu new_basis_amount == current basis_amount.
    Raise HTTP 404 nếu employee không tồn tại.
    Raise HTTP 422 nếu nhân viên chưa có insurance_profile.
    """

async def list_adjustments(
    session: AsyncSession,
    *,
    employee_id: int | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    page: int = 1,
    page_size: int = 50,
) -> BhxhSalaryAdjustmentListPage:
    """
    Lấy danh sách adjustments, hỗ trợ filter theo nhân viên và khoảng ngày.
    JOIN với employees + users để trả về tên.
    Sort: effective_date DESC, created_at DESC
    """

async def get_employee_adjustment_history(
    session: AsyncSession,
    employee_id: int,
) -> list[BhxhSalaryAdjustmentRead]:
    """
    Trả về tất cả adjustments của 1 nhân viên, sorted DESC by effective_date.
    Dùng bởi 7.1 timeline (ghép với contracts).
    """
```

---

## Kế hoạch triển khai theo slice

### Slice 1 — Migration + Model

**Files:**

```
backend/alembic/versions/0024_create_bhxh_salary_adjustments.py    (NEW)
backend/app/models/salary_adjustment.py                             (NEW)
backend/app/models/__init__.py                                      (EDIT)
```

**Chi tiết:**
1. Viết migration `0024` theo schema SQL ở trên
2. Tạo SQLModel class `BhxhSalaryAdjustment`
3. Import vào `models/__init__.py`

**Exit criteria:**
- `alembic upgrade head` không lỗi
- `alembic downgrade -1` không lỗi
- Bảng `bhxh_salary_adjustments` tồn tại với đủ constraint và index

---

### Slice 2 — Backend Service + API

**Files:**

```
backend/app/schemas/salary.py                   (EDIT: thêm BhxhSalaryAdjustmentCreate/Read)
backend/app/services/salary_service.py          (EDIT: thêm create/list/history functions)
backend/app/api/v1/endpoints/salary.py          (EDIT: thêm POST/GET endpoints)
```

**Logic kiểm tra khi tạo adjustment:**

```python
# Validate trước khi tạo
employee = await session.get(Employee, data.employee_id)
if not employee:
    raise HTTPException(404, "Nhân viên không tồn tại")

profile = await get_insurance_profile(session, data.employee_id)
if not profile:
    raise HTTPException(422, "Nhân viên chưa có hồ sơ bảo hiểm")

if profile.insurance_basis_amount == data.new_basis_amount:
    raise HTTPException(400, "Mức lương BHXH mới phải khác mức hiện tại")

# Snapshot old
old_basis = profile.insurance_basis_amount or Decimal("0")
```

**Tạo InsuranceChangeEvent — các trường bắt buộc phải snapshot:**

```python
event = InsuranceChangeEvent(
    employee_id             = data.employee_id,
    change_type             = "increase" if data.new_basis_amount > old_basis else "decrease",
    change_reason           = "manual_correction",
    effective_date          = data.effective_date,
    basis_amount            = data.new_basis_amount,
    # Snapshot các trường nhân viên tại thời điểm tạo
    employee_snapshot_name  = employee.full_name,
    employee_snapshot_code  = employee.employee_code,
    bhxh_code               = profile.bhxh_code,
    id_number               = employee.id_number,
    date_of_birth           = employee.date_of_birth,
    # Tháng kê khai gợi ý = tháng của effective_date
    suggested_declaration_year  = data.effective_date.year,
    suggested_declaration_month = data.effective_date.month,
    note = (
        f"Điều chỉnh lương BHXH: {old_basis:,.0f} → {data.new_basis_amount:,.0f} đ. "
        f"Lý do: {data.reason}"
    ),
    created_by_id = created_by_id,
)
```

**Exit criteria Slice 2:**
- `POST /salary/adjustments` tạo đủ 3 records: adjustment + event + profile update
- `profile.insurance_basis_amount` = `new_basis_amount` sau khi tạo
- `profile.insurance_basis_source` = `'manual_fixed'` sau khi tạo
- `InsuranceChangeEvent` với `change_reason='manual_correction'` được tạo
- `GET /salary/adjustments?employee_id=X` trả đúng danh sách
- Cùng mức lương → HTTP 400

---

### Slice 3 — Frontend

**Files:**

```
frontend/src/services/salaryService.ts                              (EDIT: thêm adjustment API calls)
frontend/src/views/salary/components/BhxhAdjustmentDialog.vue      (NEW: form tạo điều chỉnh)
frontend/src/views/salary/components/BhxhBasisTable.vue             (EDIT: thêm nút "Điều chỉnh")
frontend/src/assets/styles/views/_salary.scss                       (EDIT: thêm CSS adjustment)
```

#### Giao diện Dialog tạo điều chỉnh (`BhxhAdjustmentDialog.vue`)

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Điều chỉnh mức lương BHXH                                        [✕]    │
├──────────────────────────────────────────────────────────────────────────┤
│ Nhân viên: NV001 — Nguyễn Văn A  |  Phòng ban: Kỹ thuật                │
│ Mức hiện tại: 10,000,000 đ  (Nguồn: Hợp đồng)                          │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Mức lương BHXH mới *           Ngày hiệu lực *                         │
│  ┌──────────────────────┐        ┌──────────────┐                       │
│  │ 11,000,000           │        │ 01/06/2026   │                       │
│  └──────────────────────┘        └──────────────┘                       │
│  → Thay đổi: +1,000,000 đ (+10%)                                        │
│                                                                          │
│  Số quyết định (tùy chọn)                                               │
│  ┌─────────────────────────────────────┐                                 │
│  │ QĐ-045/2026                         │                                 │
│  └─────────────────────────────────────┘                                 │
│                                                                          │
│  Lý do điều chỉnh *                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ Nâng lương theo kết quả đánh giá năm 2026                       │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ⚠ Hành động này sẽ:                                                    │
│    • Cập nhật mức lương BHXH hiện tại của nhân viên                     │
│    • Tạo biến động BHXH (tăng/giảm) trong module Bảo hiểm              │
│    • Không thể hoàn tác — chỉ tạo điều chỉnh mới để đảo ngược          │
│                                                                          │
│                              [Hủy]  [Xác nhận điều chỉnh]              │
└──────────────────────────────────────────────────────────────────────────┘
```

**Behavior:**
- Tính real-time `change_amount` và `change_pct` khi nhập `new_basis_amount`
- Hiển thị badge màu: xanh = tăng (+), đỏ = giảm (−)
- `reason` bắt buộc, minimum 5 ký tự
- Sau khi submit thành công: đóng dialog, refresh BhxhBasisTable, toast "Điều chỉnh lương BHXH thành công"

**Tích hợp vào `BhxhBasisTable.vue`:**
- Thêm cột "Hành động" với nút "Điều chỉnh" (icon bút + tooltip)
- Nút chỉ hiển thị khi `participation_status = 'active'`
- Click nút → mở `BhxhAdjustmentDialog` với employee pre-filled

**Exit criteria Slice 3:**
- Dialog hiển thị đúng mức hiện tại + tính toán delta realtime
- Submit thành công → bảng refresh với mức mới, badge "Thủ công"
- Error handling: hiển thị message lỗi từ API (400/422) trong dialog
- `vue-tsc --noEmit` không lỗi
- Không có `<style scoped>` hay inline style

---

### Slice 4 — Trang danh sách điều chỉnh (quản lý)

**Files:**

```
frontend/src/views/salary/BhxhAdjustmentsView.vue       (NEW: trang /salary/bhxh-adjustments)
frontend/src/router/index.ts                            (EDIT: thêm route)
```

#### Giao diện trang danh sách (`BhxhAdjustmentsView.vue`)

```
┌───────────────────────────────────────────────────────────────────────────┐
│ Lịch sử điều chỉnh lương BHXH                                            │
├───────────────────────────────────────────────────────────────────────────┤
│ Phòng ban: [Tất cả ▼]  Từ ngày: [____] Đến ngày: [____]  🔍 [Tìm NV  ] │
├────────────┬─────────────────┬────────────┬──────────────┬────────────────┤
│ Ngày h/l   │ Nhân viên       │ Mức cũ     │ Mức mới      │ Thay đổi      │
├────────────┼─────────────────┼────────────┼──────────────┼────────────────┤
│ 01/06/2026 │ NV001 - A       │ 10,000,000 │ 11,000,000  │ +1,000,000 ↑  │
│ 15/05/2026 │ NV042 - B       │  9,000,000 │  8,000,000  │ -1,000,000 ↓  │
│ 01/04/2026 │ NV015 - C       │  7,500,000 │  8,500,000  │ +1,000,000 ↑  │
├────────────┴─────────────────┴────────────┴──────────────┴────────────────┤
│ Tổng: 3 điều chỉnh                                                        │
└───────────────────────────────────────────────────────────────────────────┘
```

- Click vào dòng → hiển thị panel chi tiết (số QĐ, lý do, người tạo, liên kết event biến động)
- Không có nút xóa/sửa (immutable)

**Exit criteria Slice 4:**
- Route `/salary/bhxh-adjustments` hoạt động
- Filter theo phòng ban, khoảng ngày hoạt động đúng
- Click dòng → chi tiết hiện đủ thông tin
- `vue-tsc --noEmit` không lỗi

---

### Slice 5 — Tests

**Files:**

```
backend/tests/test_bhxh_salary_adjustments.py    (NEW)
```

**Test cases:**

```python
class TestCreateAdjustment:
    async def test_create_adjustment_updates_profile_basis_amount()
    async def test_create_adjustment_sets_source_to_manual_fixed()
    async def test_create_adjustment_creates_insurance_change_event()
    async def test_create_adjustment_links_event_id_to_adjustment()
    async def test_increase_creates_increase_event()
    async def test_decrease_creates_decrease_event()
    async def test_event_change_reason_is_manual_correction()
    async def test_audit_log_created()
    async def test_all_side_effects_in_single_transaction()

class TestValidation:
    async def test_raises_404_for_nonexistent_employee()
    async def test_raises_422_for_employee_without_insurance_profile()
    async def test_raises_400_when_new_amount_equals_current()
    async def test_raises_422_when_new_amount_is_zero()
    async def test_raises_422_when_reason_too_short()

class TestListAdjustments:
    async def test_list_all_adjustments_sorted_desc()
    async def test_filter_by_employee_id()
    async def test_filter_by_date_range()
    async def test_pagination_works()

class TestAdjustmentHistory:
    async def test_returns_all_adjustments_for_employee()
    async def test_sorted_desc_by_effective_date()
    async def test_empty_list_for_employee_with_no_adjustments()

class TestIntegrationWith71:
    async def test_adjustment_appears_in_71_timeline()
    async def test_71_timeline_shows_correct_source_type()
```

**Exit criteria:**
- Tất cả tests mới pass
- Chạy `pytest tests/test_insurance*.py` không fail regression
- `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` không lỗi

---

## Thứ tự thực hiện

```
Slice 1 (Migration + Model)
  ↓
Slice 2 (Backend Service + API)
  ↓
Slice 3 (Frontend: Dialog điều chỉnh)
  ↓
Slice 4 (Frontend: Trang danh sách)
  ↓
Slice 5 (Tests)
```

---

## Không nằm trong 7.2

| Phần | Thuộc về |
|---|---|
| Hiển thị mức lương BHXH hiện tại + danh sách nhân viên | 7.1 |
| Tính số tiền đóng BHXH theo tháng | 7.3 |
| Approval workflow cho adjustment (phê duyệt 2 bước) | Ngoài phạm vi — thêm sau nếu khách hàng yêu cầu |
| Điều chỉnh hàng loạt (bulk adjustment) | Ngoài phạm vi |
| Import adjustment từ Excel | Ngoài phạm vi |

---

## Rủi ro và cách né

| Rủi ro | Cách né |
|---|---|
| Transaction partial failure: adjustment tạo nhưng profile không update | Tất cả trong 1 `async with session.begin()` — rollback toàn bộ nếu bất kỳ bước nào lỗi |
| Tạo InsuranceChangeEvent không đủ trường snapshot | Copy logic snapshot từ service 6.3 — sử dụng chung helper function |
| HR điều chỉnh nhầm rồi muốn hoàn tác | UI hiển thị rõ warning "không thể hoàn tác"; hướng dẫn tạo adjustment đảo ngược; timeline 7.1 hiện rõ dấu vết |
| `old_basis_amount` NULL khi nhân viên chưa có mức | Validate trước: nếu `profile.insurance_basis_amount is None` → yêu cầu nhập `old_basis_amount` thủ công hoặc báo lỗi 422 |
| Adjustment với `effective_date` quá xa trong quá khứ | Cảnh báo nếu `effective_date < today - 90 ngày` nhưng không chặn; HR tự chịu trách nhiệm |
| Trùng lặp event biến động trong 6.3 | Event chỉ được tạo 1 lần per adjustment; `insurance_change_event_id` trong adjustment là unique reference |
