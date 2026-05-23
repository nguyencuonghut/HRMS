# Kế hoạch triển khai — 7.1. Mức lương BHXH

**Phạm vi chính:** Xem mức lương BHXH hiện tại của từng nhân viên · Lịch sử thay đổi mức lương BHXH theo thời gian · Tab "Lương BHXH" trong giao diện quản lý lương  
**Phụ thuộc hoàn thành:** `6.1 Thông tin bảo hiểm nhân viên` ✅ (bảng `employee_insurance_profiles`) · `4.1 Quản lý hợp đồng` ✅ (bảng `employee_contracts` với `insurance_salary`) · `6.3 Biến động BHXH` ✅ (bảng `insurance_change_events`)  
**Phụ thuộc ngược:** `7.2 Điều chỉnh lương BHXH` — sẽ bổ sung `BhxhSalaryAdjustment` vào timeline lịch sử

---

## Nguyên tắc thiết kế

| Nguyên tắc | Mô tả |
|---|---|
| **Không tạo model mới** | Mức lương BHXH hiện tại đọc từ `employee_insurance_profiles.insurance_basis_amount` — không cần bảng riêng |
| **Lịch sử = kết hợp 2 nguồn** | Timeline lịch sử ghép từ `employee_contracts` (có `insurance_salary` + `effective_from`) và `BhxhSalaryAdjustment` (7.2, nếu có) theo thứ tự `effective_date` giảm dần |
| **Read-only trong 7.1** | Feature 7.1 chỉ hiển thị; mọi thay đổi đi qua 7.2 (Điều chỉnh lương BHXH) |
| **Nguồn dữ liệu rõ ràng** | Cột "Nguồn" phân biệt: hợp đồng (`contract`) / thủ công-cố định (`manual_fixed`) để HR biết mức nào đang áp dụng |
| **Không scoped CSS** | Style dùng global class trong `_salary.scss` hoặc PrimeVue v4 utilities |

---

## Phạm vi dữ liệu

### Mức lương BHXH hiện tại (không cần migration)

Đọc từ các bảng đã có:

```
employee_insurance_profiles
  ├── insurance_basis_amount    ← mức lương BHXH đang áp dụng
  ├── insurance_basis_source    ← 'contract' | 'computed' | 'manual_fixed'
  └── participation_status      ← 'active' | 'paused' | 'stopped'

employee_contracts (join qua employee_id)
  ├── insurance_salary          ← mức lương trong từng hợp đồng
  ├── effective_from            ← ngày hiệu lực
  ├── contract_type             ← loại hợp đồng
  └── is_active                 ← hợp đồng đang hiệu lực

departments + job_positions (join qua employees)
  ├── department_name           ← phòng ban
  └── position_title            ← vị trí công việc
```

### Timeline lịch sử (ghép 2 nguồn)

```python
# Nguồn 1: contracts
SELECT c.effective_from AS effective_date,
       c.insurance_salary AS basis_amount,
       'contract'          AS source_type,
       c.contract_type     AS note,
       NULL                AS decision_number
FROM employee_contracts c
WHERE c.employee_id = :employee_id
  AND c.insurance_salary IS NOT NULL
ORDER BY c.effective_from DESC

# Nguồn 2: BhxhSalaryAdjustment (7.2 — truy vấn conditional, skip nếu bảng chưa tồn tại)
SELECT a.effective_date,
       a.new_basis_amount  AS basis_amount,
       'manual_adjustment' AS source_type,
       a.reason            AS note,
       a.decision_number   AS decision_number
FROM bhxh_salary_adjustments a
WHERE a.employee_id = :employee_id
ORDER BY a.effective_date DESC

# Ghép + sắp xếp theo effective_date DESC ở tầng service
```

---

## Thiết kế API

### Không có migration mới trong 7.1

### Endpoints

```
GET /salary/employees
    ?department_id=&search=&participation_status=&page=&page_size=
    → SalaryEmployeeListPage

GET /salary/employees/{employee_id}/bhxh-basis
    → SalaryBhxhBasisDetail

GET /salary/employees/{employee_id}/bhxh-history
    → list[BhxhSalaryHistoryItem]
```

### Schemas

```python
class SalaryEmployeeRow(BaseModel):
    employee_id: int
    employee_code: str
    full_name: str
    department_id: int | None
    department_name: str | None
    position_title: str | None
    insurance_basis_amount: Decimal | None       # từ employee_insurance_profiles
    insurance_basis_source: str | None           # 'contract' | 'manual_fixed' | 'computed'
    participation_status: str | None             # 'active' | 'paused' | 'stopped'
    active_contract_insurance_salary: Decimal | None  # từ hợp đồng đang hiệu lực
    has_discrepancy: bool                        # True nếu basis_amount != contract's insurance_salary

class SalaryEmployeeListPage(BaseModel):
    items: list[SalaryEmployeeRow]
    total: int
    page: int
    page_size: int

class SalaryBhxhBasisDetail(BaseModel):
    employee_id: int
    employee_code: str
    full_name: str
    department_name: str | None
    position_title: str | None
    insurance_basis_amount: Decimal | None
    insurance_basis_source: str | None           # 'contract' | 'computed' | 'manual_fixed'
    participation_status: str | None
    # Hợp đồng đang hiệu lực (nếu có)
    active_contract_id: int | None
    active_contract_type: str | None
    active_contract_insurance_salary: Decimal | None
    active_contract_effective_from: date | None
    # Cảnh báo
    has_discrepancy: bool                        # profile.basis_amount != active contract's insurance_salary

class BhxhSalaryHistoryItem(BaseModel):
    effective_date: date
    basis_amount: Decimal
    source_type: str                             # 'contract' | 'manual_adjustment'
    note: str | None                             # loại hợp đồng hoặc lý do điều chỉnh
    decision_number: str | None                  # số quyết định (chỉ với manual_adjustment)
    old_basis_amount: Decimal | None             # chỉ có với manual_adjustment
    created_by_name: str | None                  # chỉ có với manual_adjustment
```

---

## Thiết kế Backend

### Files cần tạo / sửa

```
backend/app/services/salary_service.py          (NEW — salary module service)
backend/app/schemas/salary.py                   (NEW — schemas cho salary module)
backend/app/api/v1/endpoints/salary.py          (NEW — /salary/* endpoints)
backend/app/api/v1/router.py                    (EDIT: đăng ký salary router)
```

### `salary_service.py` — các hàm chính

```python
async def list_salary_employees(
    session: AsyncSession,
    *,
    department_id: int | None = None,
    search: str | None = None,
    participation_status: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> SalaryEmployeeListPage:
    """
    Lấy danh sách nhân viên kèm mức lương BHXH.
    JOIN: employees → employee_insurance_profiles → employee_contracts (active)
    → departments → job_positions
    Tính has_discrepancy = (profile.insurance_basis_amount != active_contract.insurance_salary)
    """

async def get_employee_bhxh_basis(
    session: AsyncSession,
    employee_id: int,
) -> SalaryBhxhBasisDetail:
    """
    Lấy chi tiết mức lương BHXH của 1 nhân viên.
    Raise HTTP 404 nếu không tồn tại employee hoặc chưa có insurance profile.
    """

async def get_employee_bhxh_history(
    session: AsyncSession,
    employee_id: int,
) -> list[BhxhSalaryHistoryItem]:
    """
    Trả về timeline lịch sử mức lương BHXH.
    - Query employee_contracts: insurance_salary + effective_from
    - Query bhxh_salary_adjustments (table exists check hoặc try/except): new_basis_amount + effective_date
    - Merge + sort theo effective_date DESC
    - Mỗi dòng ghi rõ source_type để FE hiển thị icon phân biệt
    """
```

### Logic `has_discrepancy`

```python
# Trong list_salary_employees và get_employee_bhxh_basis:
has_discrepancy = (
    profile.insurance_basis_amount is not None
    and active_contract is not None
    and active_contract.insurance_salary is not None
    and profile.insurance_basis_amount != active_contract.insurance_salary
    and profile.insurance_basis_source == "manual_fixed"
    # Chỉ cảnh báo khi source = manual_fixed nhưng khác hợp đồng hiện tại
    # Nếu source = 'contract' thì basis đã đồng bộ với hợp đồng → không cảnh báo
)
```

---

## Kế hoạch triển khai theo slice

### Slice 1 — Backend Service + API (Read-only)

**Mục tiêu:** Cung cấp đủ data cho FE hiển thị danh sách + chi tiết + lịch sử.

**Files:**

```
backend/app/services/salary_service.py          (NEW)
backend/app/schemas/salary.py                   (NEW)
backend/app/api/v1/endpoints/salary.py          (NEW)
backend/app/api/v1/router.py                    (EDIT)
```

**Chi tiết triển khai:**

1. Tạo `salary_service.py`:
   - `list_salary_employees()`: JOIN employees + insurance_profiles + active_contracts + departments
   - `get_employee_bhxh_basis()`: chi tiết 1 nhân viên
   - `get_employee_bhxh_history()`: timeline từ contracts + adjustments (conditional)

2. Tạo `salary.py` schemas với 3 class: `SalaryEmployeeRow`, `SalaryBhxhBasisDetail`, `BhxhSalaryHistoryItem`

3. Tạo `salary.py` router:
   - `GET /salary/employees` — phân trang, filter phòng ban + search + participation_status
   - `GET /salary/employees/{id}/bhxh-basis` — chi tiết
   - `GET /salary/employees/{id}/bhxh-history` — timeline

4. Đăng ký `salary_router` trong `router.py`

**Exit criteria:**
- `GET /salary/employees` trả đúng danh sách với mức lương BHXH từ profile
- `GET /salary/employees/{id}/bhxh-history` trả timeline contracts sắp xếp DESC
- Khi 7.2 đã hoàn thành, endpoint tự động bổ sung adjustments vào timeline
- `has_discrepancy = True` khi `source=manual_fixed` nhưng khác mức trong hợp đồng đang hiệu lực

---

### Slice 2 — Frontend: Tab "Lương BHXH" trong SalaryView

**Mục tiêu:** Hiển thị DataTable danh sách nhân viên + popup lịch sử.

**Files:**

```
frontend/src/services/salaryService.ts                              (NEW hoặc EDIT nếu đã có)
frontend/src/views/salary/SalaryView.vue                            (EDIT: thêm tab Lương BHXH)
frontend/src/views/salary/components/BhxhBasisTable.vue             (NEW)
frontend/src/views/salary/components/BhxhHistoryDialog.vue          (NEW)
frontend/src/assets/styles/views/_salary.scss                       (NEW hoặc EDIT)
```

#### Giao diện Tab "Lương BHXH" (`BhxhBasisTable.vue`)

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Mức lương BHXH                                                             │
├────────────────────────────────────────────────────────────────────────────┤
│ Phòng ban: [Tất cả ▼]  Trạng thái BH: [Tất cả ▼]  🔍 [Tìm tên/mã NV   ] │
├───────┬──────────────────┬───────────────┬────────────────┬────────┬───────┤
│ Mã NV │ Họ và tên        │ Phòng ban      │ Mức lương BHXH │ Nguồn  │ TT BH │
├───────┼──────────────────┼───────────────┼────────────────┼────────┼───────┤
│ NV001 │ Nguyễn Văn A     │ Kỹ thuật      │ 10,000,000 đ   │ HĐ     │ ● Đang│
│ NV002 │ Trần Thị B       │ Kế toán       │  8,500,000 đ ⚠ │ Thủ công│ ● Đang│
│ NV003 │ Lê Văn C         │ Nhân sự       │  7,000,000 đ   │ HĐ     │ ○ Tạm│
│ NV004 │ Phạm Thị D       │ Kinh doanh    │      —         │ —      │ ✗ Dừng│
├───────┴──────────────────┴───────────────┴────────────────┴────────┴───────┤
│ Tổng: 4 nhân viên (3 đang đóng, 1 tạm dừng)              [Xuất Excel 7.3] │
└────────────────────────────────────────────────────────────────────────────┘

Chú thích: ⚠ = Mức thủ công khác mức trong hợp đồng hiện tại
           HĐ = Từ hợp đồng lao động
           Thủ công = Đã điều chỉnh thủ công (7.2)
```

**Cột chi tiết:**

| Cột | Nguồn dữ liệu | Ghi chú |
|---|---|---|
| Mã NV | `employee_code` | Sortable |
| Họ và tên | `full_name` | Sortable |
| Phòng ban | `department_name` | Filter dropdown |
| Mức lương BHXH | `insurance_basis_amount` | Format tiền VND, hiển thị `—` nếu null |
| Nguồn | `insurance_basis_source` | `contract` → "HĐ", `manual_fixed` → "Thủ công", `computed` → "Tính tự động" |
| TT BH | `participation_status` | `active` → ● xanh, `paused` → ○ cam, `stopped` → ✗ xám |

**Icon cảnh báo ⚠:** Hiện cạnh mức lương khi `has_discrepancy = true`, tooltip: "Mức thủ công khác mức trong hợp đồng đang hiệu lực. Nhấn để xem lịch sử."

**Click vào hàng nhân viên:** Mở `BhxhHistoryDialog`.

#### Giao diện Dialog Lịch sử (`BhxhHistoryDialog.vue`)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Lịch sử mức lương BHXH — NV001 Nguyễn Văn A              [✕]          │
├─────────────────────────────────────────────────────────────────────────┤
│ Mức hiện tại: 10,000,000 đ  |  Nguồn: Hợp đồng  |  TT: ● Đang đóng   │
├──────────────┬───────────────┬──────────────┬────────────────┬──────────┤
│ Ngày h/l     │ Mức lương BHXH │ Loại thay đổi │ Ghi chú       │ Số QĐ   │
├──────────────┼───────────────┼──────────────┼────────────────┼──────────┤
│ 01/01/2025   │ 10,000,000 đ  │ 📄 Hợp đồng   │ HĐLĐ vô thời hạn│ —      │
│ 01/07/2024   │  8,500,000 đ  │ ✏ Điều chỉnh  │ Nâng lương    │ QĐ-045  │
│ 01/01/2024   │  8,000,000 đ  │ 📄 Hợp đồng   │ HĐLĐ 12 tháng │ —       │
│ 01/10/2023   │  7,500,000 đ  │ 📄 Hợp đồng   │ Hợp đồng thử việc│ —    │
├──────────────┴───────────────┴──────────────┴────────────────┴──────────┤
│ 📄 = Từ hợp đồng lao động    ✏ = Điều chỉnh thủ công (7.2)             │
└─────────────────────────────────────────────────────────────────────────┘
```

**Hành vi:**
- Sắp xếp mặc định: `effective_date` giảm dần (mới nhất trên cùng)
- Dòng đầu tiên được highlight (mức đang áp dụng)
- Mỗi dòng: badge màu phân biệt `source_type` — xanh dương (hợp đồng) / cam (điều chỉnh)
- Không có nút sửa trong dialog này (7.1 read-only); link "Tạo điều chỉnh mới" → 7.2

**Exit criteria Slice 2:**
- Bảng hiển thị đúng danh sách, phân trang, filter phòng ban hoạt động
- Icon ⚠ hiển thị đúng khi `has_discrepancy = true`
- Click hàng → dialog lịch sử mở, hiển thị đúng timeline
- Khi 7.2 tồn tại: dòng `manual_adjustment` hiển thị đúng với icon ✏ và số QĐ
- `vue-tsc --noEmit` không lỗi
- Không có `<style scoped>` hoặc `style=""` inline trong component

---

### Slice 3 — Tests

**Files:**

```
backend/tests/test_salary_bhxh_basis.py     (NEW)
```

**Test cases:**

```python
class TestListSalaryEmployees:
    async def test_returns_employees_with_insurance_profile()
    async def test_filter_by_department_id()
    async def test_filter_by_participation_status_active()
    async def test_search_by_employee_code()
    async def test_search_by_full_name()
    async def test_has_discrepancy_false_when_source_contract()
    async def test_has_discrepancy_true_when_manual_fixed_differs_from_contract()
    async def test_has_discrepancy_false_when_manual_fixed_matches_contract()
    async def test_employee_without_insurance_profile_shows_null_basis()
    async def test_pagination_works_correctly()

class TestGetBhxhBasis:
    async def test_returns_detail_for_valid_employee()
    async def test_raises_404_for_nonexistent_employee()
    async def test_shows_active_contract_salary_alongside_basis()

class TestGetBhxhHistory:
    async def test_returns_contracts_sorted_desc_by_effective_date()
    async def test_excludes_contracts_with_null_insurance_salary()
    async def test_merges_adjustments_when_table_exists()
    async def test_returns_empty_list_for_employee_with_no_contracts()
```

**Exit criteria:**
- Tất cả test cases mới pass
- Không làm vỡ các test hiện có ở `test_insurance*.py`, `test_contracts.py`

---

## Thứ tự thực hiện

```
Slice 1 (Backend Service + API)
  ↓
Slice 2 (Frontend)
  ↓
Slice 3 (Tests)
  ↓
7.2 sẽ tự động bổ sung adjustments vào timeline (không cần sửa 7.1 nữa)
```

---

## Không nằm trong 7.1

| Phần | Thuộc về |
|---|---|
| Tạo / sửa mức lương BHXH | 7.2 (Điều chỉnh lương BHXH) |
| Tính số tiền đóng BHXH theo tháng | 7.3 (Bảng tổng hợp) |
| Xuất Excel danh sách lương BHXH | 7.3 (Bảng tổng hợp) |
| Liên kết mức lương mặc định theo vị trí | 7.1 mở rộng — tạm thời bỏ qua, đọc từ hợp đồng là đủ |
| Đồng bộ tự động khi ký hợp đồng mới | Thuộc 4.1 — khi tạo hợp đồng mới, `insurance_basis_source` set lại `'contract'` |

---

## Rủi ro và cách né

| Rủi ro | Cách né |
|---|---|
| Timeline lịch sử trống khi 7.2 chưa tồn tại | Query `bhxh_salary_adjustments` trong try/except; nếu bảng chưa có thì chỉ trả contracts |
| `has_discrepancy` gây nhầm lẫn khi `source='contract'` | Chỉ tính `has_discrepancy=True` khi `source='manual_fixed'` và khác contract — ghi rõ trong code |
| Nhân viên chưa có insurance profile | Trả `null` cho các cột basis; không raise 500 |
| Dialog lịch sử chậm khi nhiều contracts | Limit 50 dòng mới nhất; thêm index trên `employee_contracts(employee_id, effective_from)` nếu cần |
