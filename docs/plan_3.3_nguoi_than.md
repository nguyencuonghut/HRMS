# Kế hoạch thực hiện — 3.3. Thông tin người thân (Employee Relatives)

**Phạm vi:** Danh sách người thân (tên, quan hệ, ngày sinh, nghề nghiệp) · Đánh dấu người liên hệ khẩn cấp  
**Phụ thuộc:** `1.2 RBAC` ✅ · `3.1 Thông tin cá nhân` ✅ · `3.2 Thông tin công việc` ✅

---

## Trạng thái hiện tại

| Thành phần | Trạng thái |
|---|---|
| Bảng `employees` | ✅ Đã có (3.1) |
| Pattern CRUD 1-N (bank accounts) | ✅ Đã có — dùng làm tham chiếu |
| Model `EmployeeRelative` | ❌ Chưa có |
| Bảng `employee_relatives` | ❌ Chưa có |
| Service / Schema / Endpoint relatives | ❌ Chưa có |
| Frontend tab "Người thân" | ❌ Chưa có |

---

## Phạm vi 3.3 — Thông tin người thân

Theo `docs/FEATURES.md §3.3`:

| Yêu cầu | Thiết kế |
|---|---|
| Danh sách người thân | Bảng `employee_relatives` (1-N per employee) |
| Tên người thân | `full_name` VARCHAR NOT NULL |
| Quan hệ | `relationship_type` — enum string: vợ/chồng/cha/mẹ/con/anh/chị/em/khác |
| Ngày sinh | `date_of_birth` DATE nullable |
| Nghề nghiệp | `occupation` VARCHAR nullable |
| Người liên hệ khẩn cấp | `is_emergency_contact` BOOLEAN — bất kỳ người thân nào đều có thể là đầu mối khẩn cấp |
| Số điện thoại (LH khẩn cấp) | `phone_number` VARCHAR nullable |
| Ghi chú | `note` TEXT nullable |

> **Quyết định thiết kế**: Không tách bảng riêng cho "người liên hệ khẩn cấp" — thực tế người liên hệ khẩn cấp luôn là người thân. Dùng flag `is_emergency_contact = TRUE` trên bản ghi người thân, có thể có nhiều người liên hệ khẩn cấp.

> **Phạm vi 3.3 không bao gồm**: địa chỉ của người thân (không cần thiết cho HR cơ bản), thông tin BHXH của người thân (phạm vi payroll — module sau).

---

## Thiết kế cơ sở dữ liệu

### Bảng `employee_relatives`

```sql
CREATE TABLE employee_relatives (
    id                  SERIAL PRIMARY KEY,
    employee_id         INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,

    -- Thông tin cơ bản
    full_name           VARCHAR(200) NOT NULL,
    relationship_type   VARCHAR(20)  NOT NULL,  -- vợ | chồng | cha | mẹ | con | anh | chị | em | khác
    date_of_birth       DATE,
    occupation          VARCHAR(200),           -- nghề nghiệp
    phone_number        VARCHAR(20),

    -- Liên hệ khẩn cấp
    is_emergency_contact BOOLEAN NOT NULL DEFAULT FALSE,

    -- Ghi chú
    note                TEXT,

    -- Audit
    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP
);

CREATE INDEX ix_employee_relatives_employee_id ON employee_relatives (employee_id);
```

### Giá trị hợp lệ cho `relationship_type`

| Giá trị | Hiển thị |
|---|---|
| `vo` | Vợ |
| `chong` | Chồng |
| `cha` | Cha |
| `me` | Mẹ |
| `con` | Con |
| `anh` | Anh |
| `chi` | Chị |
| `em` | Em |
| `khac` | Khác |

> Dùng string thay vì PostgreSQL ENUM để tránh phức tạp migration khi cần mở rộng sau này.

---

## Schema thiết kế (Pydantic)

### Request schemas

```python
class RelativeWrite(BaseModel):
    full_name: str
    relationship_type: str                  # validate trong validator
    date_of_birth: Optional[date] = None
    occupation: Optional[str] = None
    phone_number: Optional[str] = None
    is_emergency_contact: bool = False
    note: Optional[str] = None
```

> Dùng 1 schema cho cả Create và Update (tất cả field trừ `full_name` và `relationship_type` là optional khi update — xử lý bằng `Annotated` hoặc tách `RelativeCreate` / `RelativeUpdate` nếu cần validate khác nhau).

Vì Create bắt buộc `full_name` + `relationship_type` còn Update cho phép partial, tách thành 2 schema rõ ràng:

```python
class RelativeCreate(BaseModel):
    full_name: str
    relationship_type: RelationshipType     # Literal hoặc Enum
    date_of_birth: Optional[date] = None
    occupation: Optional[str] = None
    phone_number: Optional[str] = None
    is_emergency_contact: bool = False
    note: Optional[str] = None

class RelativeUpdate(BaseModel):
    full_name: Optional[str] = None
    relationship_type: Optional[RelationshipType] = None
    date_of_birth: Optional[date] = None
    occupation: Optional[str] = None
    phone_number: Optional[str] = None
    is_emergency_contact: Optional[bool] = None
    note: Optional[str] = None
```

### Response schema

```python
class EmployeeRelativeRead(BaseModel):
    id: int
    employee_id: int
    full_name: str
    relationship_type: str
    date_of_birth: Optional[date]
    occupation: Optional[str]
    phone_number: Optional[str]
    is_emergency_contact: bool
    note: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
```

### Bổ sung vào `EmployeeRead` (tuỳ chọn)

```python
class EmployeeRead(BaseModel):
    ...
    relatives: list[EmployeeRelativeRead]   # tải cùng GET /employees/{id}
```

> Load cùng lúc với `addresses` và `bank_accounts` trong `build_employee_read_data()`. Danh sách người thân thường ngắn (< 10 bản ghi) nên không cần pagination.

---

## API Endpoints

```
GET    /api/v1/employees/{id}/relatives              Danh sách người thân
POST   /api/v1/employees/{id}/relatives              Thêm người thân
PUT    /api/v1/employees/{id}/relatives/{rel_id}     Cập nhật thông tin người thân
DELETE /api/v1/employees/{id}/relatives/{rel_id}     Xóa người thân
```

### RBAC

| Hành động | Quyền |
|---|---|
| Xem danh sách người thân | `employees:view` |
| Thêm / Sửa / Xóa người thân | `employees:edit` |

Tái sử dụng cùng permission với bank accounts — không cần permission mới.

### Audit log actions

| Hành động | Action name |
|---|---|
| Thêm người thân | `CREATE_RELATIVE` |
| Cập nhật người thân | `UPDATE_RELATIVE` |
| Xóa người thân | `DELETE_RELATIVE` |

---

## Logic service

### `get_relatives(session, employee_id) → list[EmployeeRelative]`

```python
SELECT * FROM employee_relatives
WHERE employee_id = :employee_id
ORDER BY is_emergency_contact DESC, created_at ASC
```

Người liên hệ khẩn cấp hiển thị đầu danh sách.

### `create_relative(session, employee_id, payload, actor_id) → EmployeeRelative`

```python
# 1. Kiểm tra employee tồn tại
# 2. Validate relationship_type nằm trong tập hợp hợp lệ
# 3. INSERT bản ghi mới
# 4. Không có ràng buộc unique — nhân viên có thể có nhiều con, nhiều anh chị em
```

### `update_relative(session, employee_id, rel_id, payload, actor_id) → EmployeeRelative`

```python
# 1. Lấy bản ghi — kiểm tra thuộc đúng employee_id (tránh IDOR)
# 2. Cập nhật các field được gửi lên (partial update)
# 3. SET updated_at = now()
```

### `delete_relative(session, employee_id, rel_id, actor_id) → None`

```python
# 1. Lấy bản ghi — kiểm tra employee_id khớp
# 2. DELETE vật lý (không soft delete — dữ liệu người thân không cần audit trail lịch sử)
```

---

## Frontend

### Tab "Người thân" trong `EmployeeDetailView.vue`

Tab thêm vào sau tab "Công việc":

```
<Tab value="relatives" :disabled="isNew">Người thân</Tab>
```

### Component `RelativesTab.vue`

**Layout tổng quan:**

```
┌─────────────────────────────────────────────────────┐
│ Người liên hệ khẩn cấp                              │
│  Nguyễn Văn B (Cha) · 0901234567                   │
├─────────────────────────────────────────────────────┤
│ Danh sách người thân                [+ Thêm người thân] │
│                                                     │
│  Tên              Quan hệ  Ngày sinh    Nghề nghiệp │
│  Nguyễn Văn B     Cha      01/01/1960   Giáo viên   │
│  Trần Thị C       Vợ       15/06/1992   Kế toán     │
│  Nguyễn Văn D     Con      20/03/2018   —           │
└─────────────────────────────────────────────────────┘
```

**Chi tiết component:**
- Phần đầu: banner tóm tắt người liên hệ khẩn cấp (nếu có) — hiển thị tên + số điện thoại
- DataTable: danh sách tất cả người thân, cột `is_emergency_contact` hiển thị bằng Tag/icon
- Mỗi hàng: nút Sửa và Xóa (với confirm dialog)
- Dialog Thêm/Sửa: form gồm tất cả field

**Form dialog:**
```
Họ và tên *         [InputText]
Quan hệ *           [Select: vợ / chồng / cha / mẹ / con / anh / chị / em / khác]
Ngày sinh           [DatePicker]
Nghề nghiệp         [InputText]
Số điện thoại       [InputText]
Người LH khẩn cấp   [ToggleSwitch]
Ghi chú             [Textarea]
```

### Service bổ sung trong `employeeService.ts`

```typescript
export interface EmployeeRelativeRead {
  id: number
  employee_id: number
  full_name: string
  relationship_type: string
  date_of_birth: string | null
  occupation: string | null
  phone_number: string | null
  is_emergency_contact: boolean
  note: string | null
  created_at: string
  updated_at: string | null
}

export interface RelativeCreate {
  full_name: string
  relationship_type: string
  date_of_birth?: string | null
  occupation?: string | null
  phone_number?: string | null
  is_emergency_contact?: boolean
  note?: string | null
}

export interface RelativeUpdate {
  full_name?: string
  relationship_type?: string
  date_of_birth?: string | null
  occupation?: string | null
  phone_number?: string | null
  is_emergency_contact?: boolean
  note?: string | null
}

// Thêm vào EmployeeRead:
relatives: EmployeeRelativeRead[]

// Service methods:
getRelatives: (id: number) => api.get<EmployeeRelativeRead[]>(`${BASE}/${id}/relatives`)
createRelative: (id: number, data: RelativeCreate) => api.post<EmployeeRelativeRead>(`${BASE}/${id}/relatives`, data)
updateRelative: (id: number, relId: number, data: RelativeUpdate) => api.put<EmployeeRelativeRead>(`${BASE}/${id}/relatives/${relId}`, data)
deleteRelative: (id: number, relId: number) => api.delete(`${BASE}/${id}/relatives/${relId}`)
```

---

## Seed dữ liệu

Thêm người thân mẫu cho 3 nhân viên đầu (để demo UI):

| employee_seq | Người thân | Quan hệ | is_emergency_contact |
|---|---|---|---|
| 1 (Nguyễn Văn An) | Nguyễn Thị Lan | Vợ | TRUE |
| 1 (Nguyễn Văn An) | Nguyễn Văn Bình | Cha | FALSE |
| 2 (Trần Thị Bình) | Trần Văn Nam | Chồng | TRUE |
| 3 (Lê Văn Cường) | Lê Thị Mai | Mẹ | TRUE |

File seed: `backend/app/seeds/employee_relatives.py` — idempotent (check trước khi insert).

---

## Tests

File: `backend/tests/test_employee_relatives.py`

```
test_list_relatives_empty              → GET trả [] khi chưa có ai
test_list_relatives_returns_data       → NV mẫu có người thân → trả đúng danh sách
test_list_requires_auth                → 401 khi không có token
test_create_relative_success           → 201, trả đúng dữ liệu, emergency_contact đúng
test_create_relative_emergency_contact → is_emergency_contact = True → hiển thị đầu danh sách
test_create_relative_invalid_relation  → relationship_type không hợp lệ → 422
test_create_requires_edit_perm         → viewer → 403
test_create_writes_audit_log           → audit log CREATE_RELATIVE
test_update_relative_success           → PUT → 200, field cập nhật đúng
test_update_relative_wrong_employee    → PUT với rel_id thuộc nhân viên khác → 404
test_delete_relative_success           → DELETE → 204
test_delete_relative_wrong_employee    → DELETE với rel_id thuộc nhân viên khác → 404
test_delete_writes_audit_log           → audit log DELETE_RELATIVE
test_employee_detail_includes_relatives → GET /employees/{id} có field relatives
```

---

## Thứ tự triển khai

### Bước 1 — Model & Migration
1. Tạo `backend/app/models/employee_relative.py`: `EmployeeRelative`
2. Đăng ký vào `backend/app/models/__init__.py`
3. Tạo migration `0009_create_employee_relatives.py`

### Bước 2 — Seed dữ liệu
1. Tạo `backend/app/seeds/employee_relatives.py`
2. Đăng ký vào `backend/app/seeds/sample.py`

### Bước 3 — Backend CRUD
1. Bổ sung schemas vào `backend/app/schemas/employee.py`: `RelativeCreate`, `RelativeUpdate`, `EmployeeRelativeRead`
2. Tạo `backend/app/services/employee_relative_service.py`: `get_relatives`, `create_relative`, `update_relative`, `delete_relative`
3. Cập nhật `employee_service.py`: bổ sung `relatives` vào `build_employee_read_data()` và schema `EmployeeRead`
4. Thêm endpoints vào `backend/app/api/v1/endpoints/employees.py`

### Bước 4 — Tests backend
1. Tạo `backend/tests/test_employee_relatives.py`
2. Chạy pytest → toàn bộ pass

### Bước 5 — Frontend
1. Bổ sung types + service methods vào `frontend/src/services/employeeService.ts`
2. Tạo `frontend/src/views/employees/RelativesTab.vue`
3. Thêm tab "Người thân" vào `EmployeeDetailView.vue`

### Bước 6 — Phân quyền & Audit log
1. Verify quyền `employees:view` / `employees:edit`
2. Audit log: `CREATE_RELATIVE`, `UPDATE_RELATIVE`, `DELETE_RELATIVE`

---

## Rủi ro thiết kế cần tránh

1. **IDOR khi update/delete**  
   Endpoint `PUT /relatives/{rel_id}` phải kiểm tra `relative.employee_id == employee_id` từ path param. Không tin tưởng chỉ `rel_id`.

2. **Không giới hạn số lượng người thân**  
   Không cần đặt giới hạn — nhân viên có thể có nhiều con, nhiều anh chị em. UI phân trang nếu danh sách dài.

3. **Soft delete không cần thiết ở đây**  
   Khác với job records (cần lịch sử), thông tin người thân không cần audit trail lịch sử. DELETE vật lý là đúng.

4. **relationship_type validation**  
   Validate tại Pydantic layer (Literal type hoặc validator), không tạo PostgreSQL ENUM để tránh phức tạp migration.

---

## Kết quả mong đợi sau 3.3

- Mỗi nhân viên có thể ghi nhận danh sách người thân với đầy đủ thông tin.
- Người liên hệ khẩn cấp được đánh dấu rõ ràng và hiển thị nổi bật trong hồ sơ.
- Dữ liệu người thân được tải cùng `GET /employees/{id}` — không cần call API riêng trong hồ sơ chi tiết.
- Frontend có tab "Người thân" riêng trong `EmployeeDetailView.vue`.
