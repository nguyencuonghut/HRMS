# Kế hoạch thực hiện — 4.1. Quản lý hợp đồng lao động

**Phạm vi:** Hợp đồng + Phụ lục cho từng nhân viên  
**Phụ thuộc:** `1.2 RBAC` ✅ · `2.3 Danh mục loại HĐ` ✅ · `3.1 Hồ sơ nhân sự` ✅ · `MinIO attachments` ✅

---

## Trạng thái hiện tại

| Thành phần | Trạng thái | Ghi chú |
|---|---|---|
| Model `ContractCategory` | ✅ Đã có | `contract_categories` — 5 loại seed sẵn |
| Model `ContractTemplate` + `Placeholder` | ✅ Đã có | Catalog quản lý mẫu .docx |
| API catalog hợp đồng | ✅ Đã có | CRUD categories + templates |
| DOCX inspection service | ✅ Đã có | `contract_template_docx.py` |
| RBAC resource `"contracts"` | ✅ Đã seed | Admin/HR Manager/HR Staff |
| Model `EmployeeContract` | ❌ Chưa có | **Cần tạo trong 4.1** |
| API `/employees/{id}/contracts` | ❌ Chưa có | **Cần tạo trong 4.1** |
| API `/contracts` (global list) | ❌ Chưa có | **Cần tạo trong 4.1** |
| File upload hợp đồng scan/PDF | ❌ Chưa có | Tích hợp MinIO (pattern giống attachment 3.5) |
| Frontend `ContractListView.vue` | ❌ Placeholder | Route đã đăng ký, chỉ hiện "Đang phát triển" |
| Tab Hợp đồng trong EmployeeDetailView | ❌ Chưa có | Cần thêm tab mới |
| Reminder hết hạn HĐ | ⚠️ Thiếu dữ liệu | Reminder service (3.6) chưa có `contract_expiry` do bảng chưa tồn tại |

---

## Phạm vi 4.1

| Tính năng | Chi tiết |
|---|---|
| **Hợp đồng lao động** | Tạo, sửa, xem, hủy hợp đồng per employee |
| **Phụ lục hợp đồng** | Tạo phụ lục gắn với HĐ gốc (cùng bảng, `parent_contract_id`) |
| **Upload file scan/PDF** | MinIO, xem trực tiếp hoặc tải về |
| **Lịch sử HĐ** | Toàn bộ danh sách HĐ + phụ lục của nhân viên |
| **Danh sách toàn công ty** | `/contracts` — filter theo trạng thái, loại, ngày hết hạn |
| **Nhắc nhở hết hạn** | Bổ sung `contract_expiry` vào reminder_service.py (3.6 đã thiếu do chưa có bảng) |

**Không trong 4.1:**
- Sinh hợp đồng tự động từ template .docx → 4.2
- Workflow phê duyệt / ký số → ngoài phạm vi
- Nhắc tái ký theo lịch → 4.3

---

## Seed data hiện có — `contract_categories`

| Code | Tên | document_kind | legal_contract_type | business_group |
|---|---|---|---|---|
| `labor_indefinite` | HĐLĐ không xác định thời hạn | labor_contract | indefinite_term | standard |
| `labor_definite` | HĐLĐ xác định thời hạn | labor_contract | definite_term | standard |
| `probation_agreement` | Hợp đồng thử việc | labor_contract | null | probation |
| `appendix_salary_change` | Phụ lục điều chỉnh lương | contract_appendix | null | salary_change |
| `appendix_job_change` | Phụ lục điều chỉnh chức danh | contract_appendix | null | job_change |

---

## Thiết kế Backend

### Model — `EmployeeContract`

**Bảng:** `employee_contracts`

```python
class EmployeeContract(SQLModel, table=True):
    __tablename__ = "employee_contracts"

    id:                   int | None = Field(default=None, primary_key=True)
    employee_id:          int        = Field(foreign_key="employees.id", index=True)
    parent_contract_id:   int | None = Field(default=None, foreign_key="employee_contracts.id", index=True)
    contract_category_id: int        = Field(foreign_key="contract_categories.id")
    document_kind:        str        = Field(max_length=30, index=True)   # labor_contract | contract_appendix

    contract_number:  str            = Field(max_length=100)   # Số HĐ — unique toàn công ty
    signed_date:      date                                      # Ngày ký
    effective_from:   date                                      # Ngày hiệu lực
    effective_to:     date | None = Field(default=None)         # None = vô thời hạn

    insurance_salary: Decimal | None = Field(default=None, sa_column=Column(Numeric(18, 2)))  # Lương BHXH

    status: str = Field(default="active", max_length=20, index=True)
    # active | expired | terminated | draft

    # File scan/PDF
    file_path:  str | None = Field(default=None, max_length=500)
    file_name:  str | None = Field(default=None, max_length=255)
    file_size:  int | None = Field(default=None)
    mime_type:  str | None = Field(default=None, max_length=100)

    notes:      str | None = Field(default=None)
    created_by: int | None = Field(default=None, foreign_key="users.id")
    created_at: datetime   = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = Field(default=None, sa_column_kwargs={"onupdate": datetime.utcnow})
```

**Constraints & Indexes:**
- `UNIQUE (contract_number)` — số HĐ là duy nhất toàn công ty
- Index: `(employee_id, status)`, `(effective_to, status)` — phục vụ reminder và filter
- FK: `employee_id → employees.id` (CASCADE)
- FK: `parent_contract_id → employee_contracts.id` (SET NULL nếu xóa HĐ gốc)
- FK: `contract_category_id → contract_categories.id`

**Quy tắc status:**
| Status | Ý nghĩa |
|---|---|
| `active` | Đang hiệu lực (effective_from ≤ today ≤ effective_to hoặc không có hạn) |
| `expired` | Đã hết hạn (effective_to < today) — có thể auto-update hoặc chỉ hiển thị |
| `terminated` | Chấm dứt sớm (HR xác nhận thủ công) |
| `draft` | Mới tạo, chưa có hiệu lực |

> **Ghi chú:** Không auto-update status bằng cron. Status chỉ là gợi ý — UI hiển thị thêm nhãn tính từ ngày tháng thực tế.

---

### Schemas

```python
# employee_contract.py

class ContractBase(BaseModel):
    contract_category_id: int
    contract_number:      str
    signed_date:          date
    effective_from:       date
    effective_to:         date | None = None
    insurance_salary:     Decimal | None = None
    notes:                str | None = None

class ContractCreate(ContractBase):
    parent_contract_id: int | None = None   # để trống nếu là HĐ gốc

class ContractUpdate(BaseModel):
    contract_category_id: int | None = None
    contract_number:      str | None = None
    signed_date:          date | None = None
    effective_from:       date | None = None
    effective_to:         date | None = None
    insurance_salary:     Decimal | None = None
    status:               str | None = None   # chỉ cho phép "terminated"
    notes:                str | None = None

class ContractRead(ContractBase):
    id:                   int
    employee_id:          int
    parent_contract_id:   int | None
    document_kind:        str
    status:               str
    status_display:       str   # computed: "Đang hiệu lực" / "Hết hạn" / ...
    days_until_expiry:    int | None   # None nếu vô thời hạn
    file_name:            str | None
    file_size:            int | None
    mime_type:            str | None
    has_file:             bool
    category_name:        str   # từ contract_categories.name
    created_at:           datetime
    updated_at:           datetime | None
    appendices:           list[ContractRead] = []   # nested — chỉ populate khi fetch HĐ gốc

class ContractListPage(BaseModel):
    items:      list[ContractRead]
    total:      int
    page:       int
    page_size:  int
```

---

### API Endpoints

#### Per-employee (dưới `/employees/{employee_id}`)

| Method | Path | Permission | Mô tả |
|---|---|---|---|
| `GET` | `/employees/{id}/contracts` | `contracts:view` | Danh sách HĐ + phụ lục của nhân viên |
| `POST` | `/employees/{id}/contracts` | `contracts:create` | Tạo HĐ mới hoặc phụ lục |
| `GET` | `/employees/{id}/contracts/{cid}` | `contracts:view` | Chi tiết 1 HĐ (kèm danh sách phụ lục) |
| `PUT` | `/employees/{id}/contracts/{cid}` | `contracts:edit` | Cập nhật thông tin HĐ |
| `DELETE` | `/employees/{id}/contracts/{cid}` | `contracts:edit` | Hủy HĐ (set status=terminated) |
| `POST` | `/employees/{id}/contracts/{cid}/upload` | `contracts:edit` | Upload file scan/PDF |
| `GET` | `/employees/{id}/contracts/{cid}/download` | `contracts:view` | Tải file (proxy MinIO) |

#### Global list

| Method | Path | Permission | Mô tả |
|---|---|---|---|
| `GET` | `/contracts` | `contracts:view` | Danh sách HĐ toàn công ty (filter, paginate) |

**Query params `/contracts`:**
```
keyword         — tìm số HĐ, tên nhân viên
employee_id     — lọc theo nhân viên
document_kind   — labor_contract | contract_appendix
status          — active | expired | terminated | draft
category_id     — lọc theo loại HĐ
expiring_within — số ngày (30 / 15 / 7) — HĐ sắp hết hạn
page, page_size
```

---

### Service — `employee_contract_service.py`

```
get_contracts(session, employee_id, include_appendices=True) → list[ContractRead]
get_contract_by_id(session, employee_id, contract_id)        → ContractRead
create_contract(session, employee_id, payload, created_by)   → ContractRead
update_contract(session, employee_id, contract_id, payload)  → ContractRead
terminate_contract(session, employee_id, contract_id)        → ContractRead
upload_file(session, contract_id, file_bytes, filename, mime_type) → ContractRead
get_download_url(session, contract_id)                        → str (presigned MinIO URL)
list_contracts_global(session, filters, page, page_size)     → ContractListPage
```

**Validation rules:**
- `contract_number` phải unique toàn bảng
- Nếu `parent_contract_id != null` → phải tồn tại và thuộc cùng nhân viên
- `effective_to` phải ≥ `effective_from` nếu có
- Không cho phép cập nhật HĐ đã `terminated`
- `document_kind` lấy từ `contract_category.document_kind` — không cho client set thủ công

**File upload:**
- Bucket MinIO: `hrms-attachments-{env}`
- Path: `contracts/{employee_id}/{contract_id}/{filename}`
- Accept: `.pdf`, `.docx`, `.jpg`, `.png` — tối đa 20 MB
- Không thay thế file cũ tự động — upload đè nếu đã có

---

### Bổ sung Reminder — `contract_expiry`

Thêm type `contract_expiry` vào `reminder_service.py` (bổ sung thiếu sót của 3.6):

```python
# Truy vấn HĐ sắp hết hạn trong `days` ngày tới
SELECT ec.*, e.full_name, e.id
FROM employee_contracts ec
JOIN employees e ON e.id = ec.employee_id
WHERE ec.effective_to IS NOT NULL
  AND ec.effective_to BETWEEN :today AND :today + :days
  AND ec.status IN ('active', 'draft')
  AND ec.document_kind = 'labor_contract'
  AND e.is_active = TRUE
```

Cập nhật `RemindersResponse` schema thêm `contract_expiry: list[ReminderItem]`.  
Cập nhật `GET /reminders` để trả về loại mới khi `types` include `contract_expiry`.

---

### Migration

**File:** `backend/alembic/versions/0007_create_employee_contracts.py`

```sql
CREATE TABLE employee_contracts (
    id                   SERIAL PRIMARY KEY,
    employee_id          INTEGER NOT NULL REFERENCES employees(id),
    parent_contract_id   INTEGER REFERENCES employee_contracts(id) ON DELETE SET NULL,
    contract_category_id INTEGER NOT NULL REFERENCES contract_categories(id),
    document_kind        VARCHAR(30) NOT NULL,
    contract_number      VARCHAR(100) NOT NULL UNIQUE,
    signed_date          DATE NOT NULL,
    effective_from       DATE NOT NULL,
    effective_to         DATE,
    insurance_salary     NUMERIC(18, 2),
    status               VARCHAR(20) NOT NULL DEFAULT 'active',
    file_path            VARCHAR(500),
    file_name            VARCHAR(255),
    file_size            INTEGER,
    mime_type            VARCHAR(100),
    notes                TEXT,
    created_by           INTEGER REFERENCES users(id),
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ
);

CREATE INDEX ix_employee_contracts_employee_id ON employee_contracts(employee_id);
CREATE INDEX ix_employee_contracts_parent_contract_id ON employee_contracts(parent_contract_id);
CREATE INDEX ix_employee_contracts_status ON employee_contracts(status);
CREATE INDEX ix_employee_contracts_effective_to_status ON employee_contracts(effective_to, status);
CREATE INDEX ix_employee_contracts_document_kind ON employee_contracts(document_kind);
```

---

## Thiết kế Frontend

### 1. Tab "Hợp đồng" trong `EmployeeDetailView.vue`

Thêm tab mới (sau tab "Tài liệu"):

```html
<Tab value="contracts" :disabled="isNew">Hợp đồng</Tab>
<TabPanel value="contracts">
  <ContractTab v-if="!isNew && employeeId" :employee-id="employeeId" />
</TabPanel>
```

---

### 2. Component mới — `ContractTab.vue`

Layout timeline theo employee:

```
┌─────────────────────────────────────────────────────────┐
│                                          [+ Thêm hợp đồng] │
├─────────────────────────────────────────────────────────┤
│ 🟢 HĐLĐ Không xác định thời hạn              [Xem] [Sửa] │
│    Số HĐ: HĐ2024-001 · Ngày ký: 01/01/2024              │
│    Hiệu lực: 01/01/2024 → vô thời hạn                   │
│    Lương BHXH: 10,000,000 đ · 📎 hop_dong_001.pdf        │
│    │                                                     │
│    ├── 📋 Phụ lục điều chỉnh lương        [Xem] [Sửa]   │
│    │      Số: PL2024-001 · Ngày: 01/06/2024             │
│    │      Lương BHXH mới: 12,000,000 đ                  │
│    │                                        [+ Thêm PL] │
│                                                         │
│ 🔴 HĐLĐ Xác định thời hạn (HẾT HẠN)      [Xem] [Hủy]  │
│    Số HĐ: HĐ2022-001 · 01/01/2022 → 31/12/2023          │
└─────────────────────────────────────────────────────────┘
```

**Status badge:**
- `active` → Xanh lá "Đang hiệu lực"
- `expired` → Đỏ "Hết hạn" + "(còn X ngày)" hoặc "(hết hạn X ngày trước)"
- `terminated` → Xám "Đã hủy"
- `draft` → Vàng "Chưa hiệu lực"

---

### 3. Dialog Tạo/Sửa Hợp đồng — `ContractFormDialog.vue`

```
┌──────────────────────────────────────────────────────┐
│ Thêm hợp đồng                                  [×]  │
├──────────────────────────────────────────────────────┤
│ Loại hợp đồng* [Select filter ▼]                    │
│ Số hợp đồng*   [                    ]               │
│ Ngày ký*       [  dd/mm/yyyy        ]               │
│ Ngày hiệu lực* [  dd/mm/yyyy        ]               │
│ Ngày hết hạn   [  dd/mm/yyyy        ]  □ Vô thời hạn│
│ Lương BHXH     [     0              ] đ             │
│ Ghi chú        [                    ]               │
│                                                     │
│ Upload file    [ 📂 Chọn file PDF/DOCX/ảnh ]        │
│                                                     │
│                              [Hủy]  [Lưu hợp đồng] │
└──────────────────────────────────────────────────────┘
```

- `Select` loại HĐ có `filter` prop
- Checkbox "Vô thời hạn" → disable field `effective_to`
- Upload file tùy chọn (có thể thêm sau)

---

### 4. View toàn công ty — `ContractListView.vue`

Thay thế placeholder hiện tại:

```
Toolbar: [Tìm số HĐ / tên NV] [Loại HĐ ▼] [Trạng thái ▼] [Sắp HH: 30 ngày ▼] [Reload]
DataTable: Số HĐ | Nhân viên | Loại HĐ | Hiệu lực từ | Hiệu lực đến | Lương BHXH | Trạng thái | Actions
```

- Click vào nhân viên → navigate tới `/employees/{id}?tab=contracts`
- Highlight màu đỏ / vàng cho HĐ sắp hết hạn

---

### 5. Service `contractService.ts`

```typescript
export interface ContractRead {
  id, employee_id, parent_contract_id, contract_category_id,
  document_kind, contract_number, signed_date, effective_from, effective_to,
  insurance_salary, status, status_display, days_until_expiry,
  file_name, file_size, mime_type, has_file, category_name,
  created_at, updated_at, appendices: ContractRead[]
}

export interface ContractCreate {
  contract_category_id, contract_number, signed_date, effective_from,
  effective_to?, insurance_salary?, parent_contract_id?, notes?
}

// Methods:
getContracts(employeeId): ContractRead[]
createContract(employeeId, data): ContractRead
updateContract(employeeId, contractId, data): ContractRead
terminateContract(employeeId, contractId): ContractRead
uploadFile(employeeId, contractId, file): ContractRead
downloadFile(employeeId, contractId): blob download
listContractsGlobal(params): ContractListPage
```

---

## Cấu trúc file mới

```
backend/
  app/models/employee_contract.py          (NEW)
  app/schemas/employee_contract.py         (NEW)
  app/services/employee_contract_service.py (NEW)
  app/api/v1/endpoints/contracts.py        (NEW — global list)
  app/api/v1/endpoints/employee_contracts.py (NEW — per-employee CRUD)
  alembic/versions/0007_create_employee_contracts.py (NEW)

frontend/
  src/services/contractService.ts                   (NEW)
  src/views/employees/ContractTab.vue               (NEW)
  src/views/employees/ContractFormDialog.vue        (NEW)
  src/views/contracts/ContractListView.vue          (REPLACE placeholder)
```

**Đăng ký router:**
```python
# router.py — thêm sau employee_io
from app.api.v1.endpoints import contracts, employee_contracts
router.include_router(contracts.router, prefix="/contracts", tags=["Hợp đồng"])
router.include_router(employee_contracts.router, prefix="/employees", tags=["Hợp đồng nhân viên"])
```

---

## Tests

**File:** `backend/tests/test_employee_contracts.py`

```
# CRUD
test_create_contract_success
test_create_contract_duplicate_number_409
test_create_appendix_linked_to_parent
test_create_appendix_wrong_employee_400
test_update_contract_success
test_update_terminated_contract_400
test_terminate_contract_success

# File upload
test_upload_file_success
test_upload_file_invalid_type_400
test_upload_file_too_large_400
test_download_file_success
test_download_file_not_found_404

# History & list
test_list_contracts_with_appendices
test_list_global_filter_status
test_list_global_filter_expiring_within
test_global_list_404_employee_not_found

# Permissions
test_viewer_cannot_create_403
test_viewer_can_read_200

# Reminder integration
test_reminder_contract_expiry_included
```

---

## Thứ tự triển khai

### Bước 1 — Backend Model & Migration
1. Tạo `app/models/employee_contract.py`
2. Tạo migration `0007_create_employee_contracts.py`
3. Chạy `alembic upgrade head`

### Bước 2 — Backend Schema & Service
1. Tạo `app/schemas/employee_contract.py`
2. Tạo `app/services/employee_contract_service.py`
   - CRUD + file upload + global list
3. Cập nhật `app/services/reminder_service.py` — thêm `contract_expiry`
4. Cập nhật `app/schemas/reminder.py` — thêm field vào `RemindersResponse`

### Bước 3 — Backend Endpoints & Router
1. Tạo `app/api/v1/endpoints/employee_contracts.py` — 7 endpoints per-employee
2. Tạo `app/api/v1/endpoints/contracts.py` — global list
3. Đăng ký vào `router.py`

### Bước 4 — Backend Tests
1. Tạo `tests/test_employee_contracts.py`
2. Chạy pytest → tất cả pass

### Bước 5 — Frontend
1. Tạo `contractService.ts`
2. Tạo `ContractFormDialog.vue` (không scoped style, Select có filter)
3. Tạo `ContractTab.vue` (không scoped style)
4. Thêm tab "Hợp đồng" vào `EmployeeDetailView.vue`
5. Thay thế placeholder `ContractListView.vue`

### Bước 6 — Verify
1. Tạo HĐ mới cho nhân viên → kiểm tra hiển thị tab
2. Tạo phụ lục → kiểm tra hiển thị lồng vào HĐ gốc
3. Upload file PDF → tải về, xem được
4. Hủy HĐ → status chuyển "Đã hủy"
5. Global list filter "sắp hết hạn 30 ngày"
6. Kiểm tra reminder `/reminders` trả về `contract_expiry`

---

## Rủi ro & Cách xử lý

| Rủi ro | Cách xử lý |
|---|---|
| Số HĐ trùng lặp | `UNIQUE constraint` trên DB + validate trước khi INSERT, 409 nếu trùng |
| File upload lớn (>20 MB) | Validate size trước khi đẩy lên MinIO, trả 400 |
| Xóa HĐ gốc khi còn phụ lục | Không cho xóa cứng — chỉ "terminate"; FK `SET NULL` cho parent_contract_id |
| HĐ không có ngày hết hạn nhưng cần reminder | `effective_to IS NULL` → bỏ qua trong query reminder `contract_expiry` |
| Status drift (effective_to đã qua nhưng status vẫn "active") | Tính toán `status_display` runtime từ ngày thực tế — không auto-update DB để tránh cron phức tạp |
| Phân quyền: HR Staff chỉ tạo, không sửa/xóa | Dùng `contracts:create` vs `contracts:edit` riêng biệt (đã seed trong RBAC) |

---

## Kết quả mong đợi sau 4.1

- HR tạo hợp đồng lao động cho nhân viên, upload file scan
- Xem toàn bộ lịch sử hợp đồng + phụ lục trong tab nhân viên
- Trang tổng hợp hợp đồng toàn công ty — lọc nhanh theo trạng thái, sắp hết hạn
- Nhắc nhở hợp đồng sắp hết hạn xuất hiện trong module 3.6 Nhắc nhở
