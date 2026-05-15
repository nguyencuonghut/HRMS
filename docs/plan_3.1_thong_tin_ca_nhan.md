# Kế hoạch thực hiện — 3.1. Thông tin cá nhân (Employee Personal Info)

**Phạm vi:** Model nhân viên · Thông tin nhận dạng · Địa chỉ cư trú · Tài khoản ngân hàng · CRUD API · Frontend danh sách + hồ sơ  
**Phụ thuộc:** `2.1 Danh mục hành chính` ✅ · `2.2 Danh mục học vấn` ✅ · `2.3 Danh mục nghiệp vụ khác` ✅ · `1.1 Cơ cấu tổ chức` ✅ · `1.2 RBAC` ✅

---

## Trạng thái hiện tại

| Thành phần | Trạng thái |
|---|---|
| Danh mục quốc tịch / dân tộc / tôn giáo / ngân hàng | ✅ Đã có (2.3) |
| Danh mục hành chính hệ cũ + hệ mới | ✅ Đã có (2.1) |
| `AdministrativeAddressPairSelector` (FE component) | ✅ Đã có |
| `NationalitySelect`, `EthnicitySelect`, `ReligionSelect`, `BankSelect` | ✅ Đã có |
| `EmployeeEducationEditor` (FE component, preview only) | ✅ Có (dùng lại ở 3.4) |
| `User.employee_id` FK placeholder | ⚠️ Có cột, chưa có FK thực |
| Model `Employee` | ❌ Chưa có |
| Migration bảng `employees`, `employee_addresses`, `employee_bank_accounts` | ❌ Chưa có |
| Service / Schema / Endpoint employee | ❌ Chưa có |
| `EmployeeListView` đầy đủ | ❌ Mới là placeholder |
| `EmployeeDetailView` đầy đủ | ❌ Mới là mock preview |
| Tests cho employee | ❌ Chưa có |

---

## Phạm vi 3.1 — Thông tin cá nhân

Theo `docs/FEATURES.md §3.1`:

| Trường | Ghi chú |
|---|---|
| Họ và tên | `full_name`, `first_name`, `last_name` tách riêng để sort/lookup |
| Ngày sinh | `date_of_birth` |
| Giới tính | `gender`: male / female / other |
| Quốc tịch | FK → `nationalities` |
| Dân tộc | FK → `ethnicities` |
| Tôn giáo | FK → `religions` (nullable) |
| Số CCCD/CMND | `id_number` |
| Ngày cấp CCCD | `id_issued_on` |
| Nơi cấp CCCD | `id_issued_by` (text tự do) |
| Ngày hết hạn CCCD | `id_expires_on` (nullable, bắt buộc với người nước ngoài) |
| Số hộ chiếu | `passport_number` (nullable) |
| Ngày cấp hộ chiếu | `passport_issued_on` |
| Ngày hết hạn hộ chiếu | `passport_expires_on` |
| Giấy phép lao động | `work_permit_number`, `work_permit_issued_on`, `work_permit_expires_on` — chỉ áp dụng người nước ngoài |
| Mã số thuế cá nhân | `personal_tax_code` (nullable) |
| Số điện thoại | `phone_number` |
| Email cá nhân | `personal_email` (nullable, khác email đăng nhập) |
| Hộ khẩu thường trú | bảng `employee_addresses` (type = permanent), hỗ trợ địa chỉ hệ cũ + hệ mới |
| Địa chỉ liên lạc | bảng `employee_addresses` (type = contact), có thể trùng hộ khẩu |
| Tài khoản ngân hàng | bảng `employee_bank_accounts` (1 nhân viên có thể nhiều tài khoản, đánh dấu 1 mặc định) |
| Ảnh thẻ nhân viên | `avatar_path` (nullable, upload riêng) |
| Mã số nhân viên | `employee_seq` — số nguyên tự tăng từ 1, unique |
| Mã hiển thị | Computed: `{dept_prefix}{employee_seq:04d}` nếu có phòng ban, hoặc `{employee_seq:04d}` nếu chưa gán |
| Trạng thái | `status`: probation / official / long_leave / resigned |
| Ngày vào làm | `start_date` |

> **Phạm vi 3.1 không bao gồm**: thông tin công việc (phòng ban, chức danh — phần 3.2), người thân (3.3), học vấn (3.4), hồ sơ đính kèm (3.5). Các phần đó sẽ có plan riêng.

---

## Thiết kế cơ sở dữ liệu

### Bảng `employees`

```sql
CREATE TABLE employees (
    id                      SERIAL PRIMARY KEY,

    -- Mã số nhân viên: số nguyên tự tăng từ 1, KHÔNG dùng SERIAL
    -- (cần tính MAX + 1 trong service để đảm bảo tương thích khi import)
    employee_seq            INTEGER UNIQUE NOT NULL,

    -- Họ tên
    full_name               VARCHAR(200) NOT NULL,
    normalized_name         VARCHAR(200) NOT NULL,  -- unaccented, lowercase, dùng để search
    last_name               VARCHAR(100) NOT NULL,
    first_name              VARCHAR(100) NOT NULL,

    -- Thông tin cá nhân cơ bản
    date_of_birth           DATE NOT NULL,
    gender                  VARCHAR(10) NOT NULL CHECK (gender IN ('male', 'female', 'other')),
    nationality_id          INTEGER REFERENCES nationalities(id) NOT NULL,
    ethnicity_id            INTEGER REFERENCES ethnicities(id),
    religion_id             INTEGER REFERENCES religions(id),

    -- Giấy tờ nhận dạng (CCCD/CMND)
    id_number               VARCHAR(20) NOT NULL,
    id_issued_on            DATE NOT NULL,
    id_issued_by            VARCHAR(200) NOT NULL,
    id_expires_on           DATE,                  -- nullable: CCCD VN không hết hạn nếu trước 2021

    -- Hộ chiếu (nullable — chủ yếu cho người nước ngoài)
    passport_number         VARCHAR(50),
    passport_issued_on      DATE,
    passport_expires_on     DATE,

    -- Giấy phép lao động (nullable — chỉ người nước ngoài)
    work_permit_number      VARCHAR(50),
    work_permit_issued_on   DATE,
    work_permit_expires_on  DATE,

    -- Liên lạc cá nhân
    phone_number            VARCHAR(20),
    personal_email          VARCHAR(200),
    personal_tax_code       VARCHAR(20),           -- MST cá nhân

    -- Ảnh thẻ
    avatar_path             VARCHAR(500),

    -- Trạng thái nhân sự
    status                  VARCHAR(20) NOT NULL DEFAULT 'probation'
                                CHECK (status IN ('probation', 'official', 'long_leave', 'resigned')),
    start_date              DATE NOT NULL,
    resigned_date           DATE,

    -- Liên kết tài khoản hệ thống (1-1, nullable)
    user_id                 INTEGER REFERENCES users(id) UNIQUE,

    -- Thông tin bảo hiểm (dùng ở module 6, đặt ở đây cho đủ nền)
    bhxh_code               VARCHAR(20),           -- Mã số BHXH

    -- Audit
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    created_at              TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP
);

CREATE INDEX ix_employees_employee_seq ON employees (employee_seq);
CREATE INDEX ix_employees_normalized_name ON employees (normalized_name);
CREATE INDEX ix_employees_status ON employees (status);
```

> **Ghi chú thiết kế**:
> - `employee_seq` là số nguyên thuần — KHÔNG phụ thuộc năm, KHÔNG có prefix. Service tự tính `MAX(employee_seq) + 1` trong transaction để đảm bảo tương thích khi import với mã số cũ.
> - Mã hiển thị (ví dụ `HC0011`) là **computed field**, không lưu vào DB — tính khi trả response từ `employee_seq` + `departments.display_prefix` của phòng ban hiện tại.
> - `normalized_name` lưu text đã bỏ dấu + lowercase — dùng cho full-text search.
> - `user_id` nullable UNIQUE: một User có tối đa 1 Employee, nhưng không phải mọi User đều là nhân viên (ví dụ admin kỹ thuật).  
> - Không dùng FK ngược (`User.employee_id`) để tránh circular dependency trong migration.

---

### Cột bổ sung `departments.display_prefix`

Để tính mã hiển thị nhân viên, bảng `departments` cần thêm một cột ngắn dùng làm prefix:

```sql
ALTER TABLE departments ADD COLUMN display_prefix VARCHAR(5);
-- Nullable: phòng ban chưa đặt prefix thì mã hiển thị chỉ là số (0011)
-- Ví dụ: HC = Hành chính, KH = Kho hàng, KD = Kinh doanh, KT = Kế toán
```

> Cột này được thêm trong migration `0007` cùng với bảng `employees`, không cần migration riêng.  
> Khi seed phòng ban (hoặc qua UI quản lý phòng ban), HR Admin đặt `display_prefix` cho từng phòng.  
> `display_prefix` là **nullable** — phòng ban không có prefix thì nhân viên hiển thị mã số thuần.

**Quy tắc hiển thị mã nhân viên**:

| Tình huống | Hiển thị | Ví dụ |
|---|---|---|
| Chưa gán phòng ban | `{employee_seq:04d}` | `0011` |
| Có phòng ban, phòng ban có `display_prefix` | `{display_prefix}{employee_seq:04d}` | `HC0011` |
| Có phòng ban, phòng ban chưa đặt `display_prefix` | `{employee_seq:04d}` | `0011` |

Nhân viên chuyển phòng ban → mã số (`employee_seq`) không đổi, **prefix đổi theo phòng mới**.

---

### Bảng `employee_addresses`

```sql
CREATE TABLE employee_addresses (
    id                  SERIAL PRIMARY KEY,
    employee_id         INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,

    -- Loại địa chỉ
    address_type        VARCHAR(20) NOT NULL CHECK (address_type IN ('permanent', 'contact')),
    -- permanent = hộ khẩu thường trú, contact = địa chỉ liên lạc

    -- Địa chỉ hệ mới (hệ thống đơn vị hành chính mới theo QĐ 19/2025)
    new_province_unit_id    INTEGER REFERENCES administrative_units(id),
    new_district_unit_id    INTEGER REFERENCES administrative_units(id),
    new_ward_unit_id        INTEGER REFERENCES administrative_units(id),
    new_address_line        VARCHAR(500),          -- Số nhà, tên đường

    -- Địa chỉ hệ cũ (legacy 3 cấp trước 2025)
    old_province_unit_id    INTEGER REFERENCES administrative_units(id),
    old_district_unit_id    INTEGER REFERENCES administrative_units(id),
    old_ward_unit_id        INTEGER REFERENCES administrative_units(id),
    old_address_line        VARCHAR(500),

    -- Địa chỉ đầy đủ dạng text (denormalized, dùng để hiển thị nhanh)
    full_address_text        VARCHAR(1000),

    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP,

    UNIQUE (employee_id, address_type)  -- mỗi nhân viên chỉ có 1 hộ khẩu + 1 địa chỉ liên lạc
);
```

> **Thiết kế song song hệ cũ + hệ mới**: cùng lưu cả hai hệ địa chỉ trong 1 hàng — thống nhất với `AdministrativeAddressPairSelector` đã có ở frontend.

---

### Bảng `employee_bank_accounts`

```sql
CREATE TABLE employee_bank_accounts (
    id              SERIAL PRIMARY KEY,
    employee_id     INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    bank_id         INTEGER NOT NULL REFERENCES banks(id),
    account_number  VARCHAR(50) NOT NULL,
    account_name    VARCHAR(200) NOT NULL,         -- Tên chủ tài khoản (thường = full_name)
    branch_name     VARCHAR(200),                  -- Chi nhánh
    is_primary      BOOLEAN NOT NULL DEFAULT FALSE, -- Tài khoản nhận lương mặc định
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    note            TEXT,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP
);
```

---

## RBAC

Tái sử dụng module `employees` đã có trong seed RBAC.

| Role | Quyền |
|---|---|
| `admin` | `employees:*` |
| `hr_manager` | `employees:view, create, edit, delete, export` |
| `hr_officer` | `employees:view, create, edit, export` (không delete) |
| `line_manager` | `employees:view` (chỉ xem) |
| `finance` | `employees:view` (cần tên + mã để khớp BHXH) |

---

## Schema thiết kế (Pydantic)

### Request schemas

```python
class EmployeeCreate(BaseModel):
    # employee_seq không cần truyền vào — service tự tính MAX+1
    # Khi import hàng loạt, có thể truyền employee_seq cụ thể (override)
    employee_seq: Optional[int] = None  # None = tự tính

    # Họ tên
    full_name: str          # max 200
    last_name: str          # max 100
    first_name: str         # max 100

    # Cá nhân
    date_of_birth: date
    gender: Literal["male", "female", "other"]
    nationality_id: int
    ethnicity_id: Optional[int] = None
    religion_id: Optional[int] = None

    # Giấy tờ
    id_number: str
    id_issued_on: date
    id_issued_by: str
    id_expires_on: Optional[date] = None
    passport_number: Optional[str] = None
    passport_issued_on: Optional[date] = None
    passport_expires_on: Optional[date] = None
    work_permit_number: Optional[str] = None
    work_permit_issued_on: Optional[date] = None
    work_permit_expires_on: Optional[date] = None

    # Liên lạc & thuế
    phone_number: Optional[str] = None
    personal_email: Optional[str] = None
    personal_tax_code: Optional[str] = None
    bhxh_code: Optional[str] = None

    # Nhân sự
    start_date: date
    status: Literal["probation", "official", "long_leave", "resigned"] = "probation"

    # Địa chỉ (optional tại bước tạo, có thể update sau)
    permanent_address: Optional[EmployeeAddressWrite] = None
    contact_address: Optional[EmployeeAddressWrite] = None

class EmployeeAddressWrite(BaseModel):
    new_province_unit_id: Optional[int] = None
    new_district_unit_id: Optional[int] = None
    new_ward_unit_id: Optional[int] = None
    new_address_line: Optional[str] = None
    old_province_unit_id: Optional[int] = None
    old_district_unit_id: Optional[int] = None
    old_ward_unit_id: Optional[int] = None
    old_address_line: Optional[str] = None

class EmployeeBankAccountWrite(BaseModel):
    bank_id: int
    account_number: str
    account_name: str
    branch_name: Optional[str] = None
    is_primary: bool = False
    note: Optional[str] = None
```

### Response schemas

```python
class EmployeeListItem(BaseModel):
    id: int
    employee_seq: int
    display_code: str           # computed: "HC0011" hoặc "0011"
    full_name: str
    status: str
    start_date: date
    phone_number: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

class EmployeeRead(BaseModel):
    id: int
    employee_seq: int
    display_code: str           # computed
    full_name: str
    last_name: str
    first_name: str
    date_of_birth: date
    gender: str
    nationality_id: int
    nationality_name: str           # denormalized để UI không cần lookup
    ethnicity_id: Optional[int]
    ethnicity_name: Optional[str]
    religion_id: Optional[int]
    religion_name: Optional[str]
    id_number: str
    id_issued_on: date
    id_issued_by: str
    id_expires_on: Optional[date]
    passport_number: Optional[str]
    passport_issued_on: Optional[date]
    passport_expires_on: Optional[date]
    work_permit_number: Optional[str]
    work_permit_issued_on: Optional[date]
    work_permit_expires_on: Optional[date]
    phone_number: Optional[str]
    personal_email: Optional[str]
    personal_tax_code: Optional[str]
    bhxh_code: Optional[str]
    avatar_path: Optional[str]
    status: str
    start_date: date
    resigned_date: Optional[date]
    user_id: Optional[int]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    # Nested
    permanent_address: Optional[EmployeeAddressRead]
    contact_address: Optional[EmployeeAddressRead]
    bank_accounts: list[EmployeeBankAccountRead]
```

---

## API Endpoints

```
GET    /api/v1/employees                   Danh sách, phân trang, filter: keyword/status/is_active
POST   /api/v1/employees                   Tạo mới
GET    /api/v1/employees/{id}              Chi tiết
PUT    /api/v1/employees/{id}              Cập nhật thông tin cá nhân
DELETE /api/v1/employees/{id}              Soft deactivate (is_active=false)

GET    /api/v1/employees/{id}/addresses                  Lấy địa chỉ
PUT    /api/v1/employees/{id}/addresses/{type}           Upsert địa chỉ (type: permanent | contact)

GET    /api/v1/employees/{id}/bank-accounts              Danh sách tài khoản ngân hàng
POST   /api/v1/employees/{id}/bank-accounts              Thêm tài khoản
PUT    /api/v1/employees/{id}/bank-accounts/{acct_id}    Cập nhật tài khoản
DELETE /api/v1/employees/{id}/bank-accounts/{acct_id}    Xóa tài khoản
PUT    /api/v1/employees/{id}/bank-accounts/{acct_id}/set-primary  Đặt làm tài khoản mặc định

GET    /api/v1/employees/{id}/avatar                     Lấy URL ảnh thẻ
POST   /api/v1/employees/{id}/avatar                     Upload ảnh thẻ (multipart)

GET    /api/v1/lookups/employees           Search nhân viên (autocomplete), trả id + name + code
```

---

## Sinh và hiển thị mã nhân viên

### Lưu trữ: `employee_seq` (số nguyên)

```python
async def next_employee_seq(session: AsyncSession) -> int:
    # SELECT FOR UPDATE để tránh race condition khi tạo đồng thời
    result = await session.execute(
        select(func.max(Employee.employee_seq)).with_for_update()
    )
    current_max = result.scalar() or 0
    return current_max + 1
```

Gọi trong `create_employee()` service, trong cùng transaction commit.

**Import nhân viên từ file Excel**: nếu file có cột mã số sẵn (ví dụ dữ liệu cũ), dùng trực tiếp số đó; sau khi import xong cần đặt lại sequence = `MAX(employee_seq)` hiện tại để tránh conflict.

### Hiển thị: `display_code` (computed field, không lưu DB)

```python
def compute_display_code(employee_seq: int, dept_display_prefix: str | None) -> str:
    seq_str = f"{employee_seq:04d}"
    if dept_display_prefix:
        return f"{dept_display_prefix}{seq_str}"
    return seq_str

# Ví dụ:
compute_display_code(11, "HC")    # → "HC0011"
compute_display_code(2278, "KH")  # → "KH2278"
compute_display_code(11, None)    # → "0011"
compute_display_code(2278, None)  # → "2278"
```

Trường `display_code` được trả về trong `EmployeeListItem` và `EmployeeRead` — service tự join với phòng ban hiện tại (sau khi 3.2 có `employee_job_records`) để lấy `display_prefix`.

**Trong 3.1** (chưa có bảng job records): `display_code = f"{employee_seq:04d}"`.  
**Từ 3.2 trở đi**: join lấy phòng ban hiện tại → lấy `display_prefix` → tính đủ.

---

## Cảnh báo sắp hết hạn

Các trường cần cảnh báo (hiển thị trên UI và dùng cho notification về sau):

| Trường | Ngưỡng cảnh báo |
|---|---|
| `id_expires_on` | < 30 ngày |
| `passport_expires_on` | < 60 ngày |
| `work_permit_expires_on` | < 60 ngày |

API trả thêm trường `expiry_alerts: list[str]` trong `EmployeeRead`.

---

## Frontend

### EmployeeListView (thay thế placeholder hiện tại)

**Tính năng:**
- DataTable phân trang với lazy loading
- Filter: keyword (tìm tên/mã), status (probation/official/resigned), is_active
- Cột: Mã NV · Họ tên · Trạng thái · Ngày vào làm · Số điện thoại · Thao tác
- Nút tạo mới → mở Dialog hoặc navigate tới trang tạo
- Tag màu theo `status`: cam (probation), xanh lá (official), xám (resigned)

### EmployeeDetailView / EmployeeCreateView

Form nhập liệu phân thành các section (accordion hoặc tab):

**Section 1: Thông tin cơ bản**
- `full_name` (text), `last_name` / `first_name` (2 cột)
- `date_of_birth` (DatePicker), `gender` (Select)
- `nationality_id` → `NationalitySelect` (đã có)
- `ethnicity_id` → `EthnicitySelect` (đã có)
- `religion_id` → `ReligionSelect` (đã có)

**Section 2: Giấy tờ nhận dạng**
- `id_number`, `id_issued_on`, `id_issued_by`, `id_expires_on`
- Toggle "Có hộ chiếu" → hiện `passport_number`, `passport_issued_on`, `passport_expires_on`
- Toggle "Người nước ngoài" → hiện `work_permit_number`, `work_permit_issued_on`, `work_permit_expires_on`

**Section 3: Liên lạc & Thuế**
- `phone_number`, `personal_email`, `personal_tax_code`, `bhxh_code`

**Section 4: Địa chỉ**
- Component `AdministrativeAddressPairSelector` (đã có) cho hộ khẩu thường trú
- Checkbox "Địa chỉ liên lạc giống hộ khẩu" → nếu không tích thì hiện thêm `AdministrativeAddressPairSelector` thứ hai

**Section 5: Tài khoản ngân hàng**
- Danh sách tài khoản (table nhỏ)
- Thêm/sửa/xóa inline dialog
- `BankSelect` (đã có) + `account_number`, `account_name`, `branch_name`, `is_primary`

### Service (employeeService.ts)

```typescript
getEmployees(params?)          → Page<EmployeeListItem>
getEmployeeById(id)            → EmployeeRead
createEmployee(data)           → EmployeeRead
updateEmployee(id, data)       → EmployeeRead
deleteEmployee(id)             → { message }
lookupEmployees(params?)       → EmployeeRead[]   // autocomplete

getEmployeeAddresses(id)       → EmployeeAddressRead[]
upsertEmployeeAddress(id, type, data)  → EmployeeAddressRead

getEmployeeBankAccounts(id)    → EmployeeBankAccountRead[]
createBankAccount(id, data)    → EmployeeBankAccountRead
updateBankAccount(id, acctId, data)    → EmployeeBankAccountRead
deleteBankAccount(id, acctId)  → { message }
setPrimaryBankAccount(id, acctId)      → EmployeeBankAccountRead

uploadAvatar(id, file)         → { avatar_url }
```

---

## Seed dữ liệu

10 nhân viên mẫu (đa dạng trạng thái, giới tính, quốc tịch):

| employee_seq | display_code (3.1) | full_name | status | start_date |
|---|---|---|---|---|
| 1 | 0001 | Nguyễn Văn An | official | 2024-01-15 |
| 2 | 0002 | Trần Thị Bình | official | 2024-03-01 |
| 3 | 0003 | Lê Văn Cường | official | 2024-06-15 |
| 4 | 0004 | Phạm Thị Dung | official | 2024-09-01 |
| 5 | 0005 | Hoàng Văn Em | official | 2025-01-01 |
| 6 | 0006 | Ngô Thị Phương | official | 2025-04-01 |
| 7 | 0007 | Đỗ Văn Giang | probation | 2025-11-01 |
| 8 | 0008 | Vũ Thị Hoa | probation | 2026-03-01 |
| 9 | 0009 | Bùi Văn Ích | probation | 2026-04-15 |
| 10 | 0010 | Trịnh Thị Kim | resigned | 2023-06-01 |

> Sau khi 3.2 gán phòng ban, `display_code` sẽ tự động thay đổi theo prefix phòng (ví dụ: nhân viên 0001 vào phòng HC → `HC0001`).

Mỗi seed employee cần:
- Địa chỉ thường trú (hệ mới) tại một tỉnh/thành ngẫu nhiên
- Ít nhất 1 tài khoản ngân hàng

---

## Tests

### `test_employees.py`

```
test_list_employees_returns_200
test_list_employees_supports_pagination
test_list_employees_filter_by_status
test_list_employees_filter_by_keyword
test_create_employee_success                → 201, employee_seq sinh tự động (MAX+1), display_code = f"{seq:04d}"
test_create_employee_seq_increments         → tạo 2 nhân viên liên tiếp, seq cách nhau đúng 1
test_create_employee_with_explicit_seq      → import với employee_seq cụ thể, không conflict
test_create_employee_duplicate_id_409      → id_number trùng
test_get_employee_by_id
test_get_employee_404
test_update_employee_success
test_update_employee_requires_edit_perm
test_delete_employee_soft_deactivate
test_upsert_permanent_address
test_upsert_contact_address
test_add_bank_account
test_set_primary_bank_account
test_delete_bank_account
test_create_employee_writes_audit_log
test_update_employee_writes_audit_log
test_employee_requires_token_401
test_officer_cannot_delete_employee_403
test_expiry_alert_in_response             → work_permit_expires_on < 30 ngày → có cảnh báo
```

---

## Thứ tự triển khai (theo bước)

### Bước 1 — Model & Migration
1. Tạo `backend/app/models/employee.py`: `Employee`, `EmployeeAddress`, `EmployeeBankAccount`
2. Tạo migration `0007_create_employee_tables.py`
3. Thêm FK ngược: cập nhật `User.employee_id` → thêm `ForeignKey("employees.id")` (migration riêng hoặc trong 0007)

### Bước 2 — Seed dữ liệu
1. Tạo `backend/app/seeds/employees.py`
2. Đăng ký vào `seed_required` / `seed_sample` tương tự pattern `other_business_catalog.py`

### Bước 3 — Backend CRUD
1. Tạo `backend/app/schemas/employee.py`: tất cả schemas (Create/Update/Read)
2. Tạo `backend/app/services/employee_service.py`: list/get/create/update/delete + address upsert + bank account CRUD
3. Tạo `backend/app/api/v1/endpoints/employees.py`: tất cả endpoints
4. Đăng ký router vào `backend/app/api/v1/router.py`

### Bước 4 — Tests backend
1. Tạo `backend/tests/test_employees.py`
2. Chạy `docker exec hrms-backend-1 python -m pytest tests/ -v` → toàn bộ pass

### Bước 5 — Frontend
1. Tạo `frontend/src/services/employeeService.ts`
2. Xây dựng `EmployeeListView.vue` thay thế placeholder
3. Xây dựng `EmployeeDetailView.vue` / `EmployeeFormDialog.vue` với 5 sections
4. Cập nhật router để navigate đúng route `/employees/:id`

### Bước 6 — Phân quyền, audit log, cảnh báo hết hạn
1. Verify quyền `employees:*` đã đúng theo RBAC
2. Audit log: CREATE / UPDATE / DELETE
3. Panel cảnh báo hết hạn giấy tờ trong EmployeeListView (badge/icon)

---

## Rủi ro thiết kế cần tránh

1. **Gộp thông tin công việc vào Employee model**  
   Thông tin công việc (phòng ban, chức danh, ngày chính thức) sẽ có ở `3.2`. Tách bảng `employee_job_records` riêng. `employees` chỉ giữ `status` và `start_date` là thông tin nhân sự cơ bản.

2. **Để `user_id` là FK bắt buộc**  
   Không phải mọi nhân viên đều có tài khoản đăng nhập. `user_id` phải nullable.

3. **Lưu tên tỉnh/quận/xã dạng text thuần**  
   Phải lưu FK → `administrative_units` để sau này tra cứu, validate và chuyển đổi hệ địa chỉ được.

4. **Dùng một tài khoản ngân hàng duy nhất trong `employees`**  
   Thực tế nhân viên có thể có nhiều tài khoản (lương + tiết kiệm). Phải dùng bảng `employee_bank_accounts` với flag `is_primary`.

5. **Dùng `SERIAL` hoặc `IDENTITY` cho `employee_seq`**  
   SERIAL của PostgreSQL không thể reset hoặc điều chỉnh dễ dàng khi import. Phải dùng `INTEGER` thường + `SELECT MAX(employee_seq) FOR UPDATE` trong service để kiểm soát hoàn toàn giá trị khi import dữ liệu cũ.

6. **Lưu `display_code` vào DB**  
   `display_code` phụ thuộc phòng ban hiện tại — nếu lưu cứng vào DB thì mỗi lần nhân viên chuyển phòng phải cập nhật cột này ở nhiều nơi. Phải để là computed field trong service/schema.

---

## Kết quả mong đợi sau 3.1

- HR có thể tạo, xem, sửa hồ sơ nhân viên với đầy đủ thông tin cá nhân.
- Mã số nhân viên (`employee_seq`) là số nguyên tự tăng, đơn giản, ổn định khi import hàng loạt.
- Mã hiển thị (`display_code`) tự động phản ánh phòng ban hiện tại — không cần cập nhật thủ công khi chuyển phòng.
- Địa chỉ hộ khẩu lưu đồng thời hệ cũ và hệ mới — đảm bảo tương thích.
- Tài khoản ngân hàng quản lý linh hoạt, đánh dấu tài khoản nhận lương.
- Cảnh báo hết hạn giấy tờ hiển thị trên danh sách và hồ sơ.
- Nền dữ liệu đủ để `3.2 Thông tin công việc`, `4. Hợp đồng lao động` và `6. BHXH` tham chiếu trực tiếp.
