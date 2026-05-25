# Kế hoạch triển khai — 13.6. Hồ sơ pháp lý & Tuân thủ

**Phạm vi:** Checklist hồ sơ nhân viên mới · Theo dõi trạng thái giấy tờ · Nhắc báo cáo biến động lao động  
**Phụ thuộc:** `13.5 hiring_decisions` (employee_id sau convert) · `employees` ✅ · `reminder_service` ✅ · MinIO ✅  
**Căn cứ nghiệp vụ:** FEATURES.md §13.6  
**Căn cứ pháp lý:** Nghị định 145/2020/NĐ-CP (Điều 35 — khám sức khỏe); Thông tư 23/2014/TT-BLĐTBXH; Luật Việc làm 2013 Điều 16

---

## Trạng thái hiện tại

| Thành phần | Trạng thái | Ghi chú |
|---|---|---|
| `employee_attachments` | ✅ Hoàn thành | Tái dụng cho file giấy tờ |
| `reminder_service` | ✅ Hoàn thành | Tái dụng nhắc giấy tờ thiếu/hết hạn |
| MinIO | ✅ Hoàn thành | Lưu file scan giấy tờ |
| `candidate_document_checklists` | ❌ Chưa có | |
| API + Frontend | ❌ Chưa có | |

---

## Phạm vi

**Trong phạm vi:**
- Checklist loại giấy tờ cần thu thập khi nhân viên mới vào
- Gắn checklist với nhân viên (sau khi convert từ ứng viên)
- Theo dõi trạng thái từng giấy tờ: Chưa nộp / Đã nộp / Hết hạn
- Upload file scan giấy tờ → MinIO
- Cảnh báo tự động giấy tờ còn thiếu hoặc sắp hết hạn
- Nhắc nhở HR báo cáo biến động lao động định kỳ
- Xuất danh sách lao động mới theo mẫu biểu Nhà nước

**Ngoài phạm vi:**
- Xác thực tính hợp lệ của giấy tờ qua cơ quan Nhà nước
- Tích hợp hệ thống hành chính điện tử
- OCR tự động đọc thông tin từ CCCD scan

---

## Data Model

### Bảng `document_checklist_types`

```sql
-- Danh mục loại giấy tờ (cấu hình sẵn, HR có thể thêm)
CREATE TABLE document_checklist_types (
    id              SERIAL PRIMARY KEY,
    code            VARCHAR(50) UNIQUE NOT NULL,
    name            VARCHAR(200) NOT NULL,       -- "CCCD/CMND (bản sao công chứng)"
    description     TEXT,
    is_required     BOOLEAN NOT NULL DEFAULT TRUE,  -- bắt buộc hay tùy chọn
    has_expiry      BOOLEAN NOT NULL DEFAULT FALSE, -- có ngày hết hạn không
    applies_to      VARCHAR(30) DEFAULT 'all',   -- all | foreign_worker | sensitive_position
    sort_order      SMALLINT DEFAULT 0,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE
);
```

Seed dữ liệu mặc định:

| code | name | required | has_expiry | applies_to |
|---|---|---|---|---|
| cccd | CCCD/CMND (bản sao công chứng) | ✅ | ❌ | all |
| ho_khau | Sổ hộ khẩu / KT3 (bản sao) | ✅ | ❌ | all |
| giay_khai_sinh | Giấy khai sinh (bản sao) | ✅ | ❌ | all |
| bang_cap | Bằng cấp / Chứng chỉ (bản sao công chứng) | ✅ | ✅ | all |
| ly_lich_tu_phap | Lý lịch tư pháp số 1 | ❌ | ✅ | sensitive_position |
| suc_khoe | Giấy chứng nhận sức khỏe | ✅ | ✅ | all |
| mst | Mã số thuế cá nhân | ✅ | ❌ | all |
| tk_ngan_hang | Thông tin tài khoản ngân hàng | ✅ | ❌ | all |
| anh_the | Ảnh thẻ 3×4 | ✅ | ❌ | all |
| so_bhxh | Sổ BHXH | ❌ | ❌ | all |
| giay_phep_ld | Giấy phép lao động | ✅ | ✅ | foreign_worker |

### Bảng `employee_document_checklists`

```sql
CREATE TABLE employee_document_checklists (
    id                      SERIAL PRIMARY KEY,
    employee_id             INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    document_type_id        INTEGER NOT NULL REFERENCES document_checklist_types(id),

    status                  VARCHAR(20) NOT NULL DEFAULT 'not_submitted',
    -- not_submitted | submitted | expired | waived

    submitted_at            DATE,
    expires_at              DATE,        -- ngày hết hạn giấy tờ (nếu has_expiry = true)
    waived_reason           TEXT,        -- lý do miễn (ví dụ: "NV nước ngoài không có sổ BHXH")

    -- File scan giấy tờ
    file_path               VARCHAR(500),
    file_name               VARCHAR(300),
    file_size               INTEGER,
    mime_type               VARCHAR(100),

    note                    TEXT,
    created_by_id           INTEGER REFERENCES users(id),
    updated_by_id           INTEGER REFERENCES users(id),
    created_at              TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP NOT NULL DEFAULT NOW(),

    UNIQUE (employee_id, document_type_id)
);

CREATE INDEX ix_emp_doc_checklist_employee ON employee_document_checklists(employee_id);
CREATE INDEX ix_emp_doc_checklist_status ON employee_document_checklists(status);
CREATE INDEX ix_emp_doc_checklist_expiry ON employee_document_checklists(expires_at) WHERE expires_at IS NOT NULL;
```

### Alembic migration

File: `0038_add_document_checklists.py`

---

## Logic tự động khởi tạo Checklist

Khi `hiring_decision_service.convert_to_employee()` tạo `Employee` mới, tự động tạo checklist:

```python
async def _init_document_checklist(session, employee_id, is_foreign_worker: bool):
    types = await session.execute(
        select(DocumentChecklistType)
        .where(DocumentChecklistType.is_active == True)
        .where(or_(
            DocumentChecklistType.applies_to == 'all',
            and_(is_foreign_worker, DocumentChecklistType.applies_to == 'foreign_worker')
        ))
        .order_by(DocumentChecklistType.sort_order)
    )
    for dtype in types.scalars():
        session.add(EmployeeDocumentChecklist(
            employee_id=employee_id,
            document_type_id=dtype.id,
            status='not_submitted',
        ))
```

---

## API Design

### Danh mục loại giấy tờ

```
GET    /recruitment/document-types               -- danh sách (public trong module)
POST   /recruitment/document-types              -- admin thêm loại mới
PUT    /recruitment/document-types/{id}
DELETE /recruitment/document-types/{id}         -- chỉ khi không có checklist item đang dùng
```

### Checklist nhân viên

```
GET    /employees/{employee_id}/document-checklist             -- danh sách giấy tờ + trạng thái
PUT    /employees/{employee_id}/document-checklist/{item_id}  -- cập nhật trạng thái, ngày, ghi chú
POST   /employees/{employee_id}/document-checklist/{item_id}/upload   -- upload file scan
GET    /employees/{employee_id}/document-checklist/{item_id}/download
DELETE /employees/{employee_id}/document-checklist/{item_id}/file     -- xóa file (giữ record)
POST   /employees/{employee_id}/document-checklist/{item_id}/waive    -- miễn giấy tờ
```

### Báo cáo & xuất

```
GET    /recruitment/document-checklist/summary?status=not_submitted&department_id=
       → danh sách nhân viên còn thiếu giấy tờ

GET    /recruitment/labor-report/export?month=&year=
       → Excel danh sách lao động mới theo mẫu TT23/2014
```

### Permissions

| Action | Permission |
|---|---|
| Xem checklist | `recruitment:view` hoặc `employees:view` |
| Cập nhật / upload | `recruitment:manage` |
| Quản lý danh mục | `recruitment:manage` |

---

## Schemas

```python
class DocumentChecklistTypeRead(BaseModel):
    id: int
    code: str
    name: str
    description: Optional[str]
    is_required: bool
    has_expiry: bool
    applies_to: str
    sort_order: int

class ChecklistItemRead(BaseModel):
    id: int
    document_type_id: int
    document_type_name: str
    document_type_code: str
    is_required: bool
    has_expiry: bool
    status: str            -- not_submitted | submitted | expired | waived
    submitted_at: Optional[date]
    expires_at: Optional[date]
    days_until_expiry: Optional[int]   -- tính tự động
    is_expiring_soon: bool             -- expires_at < today + 30 ngày
    waived_reason: Optional[str]
    has_file: bool
    file_name: Optional[str]
    note: Optional[str]
    updated_at: datetime

class EmployeeChecklistSummary(BaseModel):
    employee_id: int
    employee_code: str
    employee_name: str
    department_name: Optional[str]
    total_required: int
    submitted_count: int
    missing_count: int
    expiring_count: int    -- sắp hết hạn trong 30 ngày
    completion_rate: float  # submitted / total_required * 100

class ChecklistItemUpdate(BaseModel):
    status: Optional[str] = None
    submitted_at: Optional[date] = None
    expires_at: Optional[date] = None
    note: Optional[str] = None
```

---

## Service Logic

### `document_checklist_service.py`

**`get_employee_checklist(session, employee_id) → List[ChecklistItemRead]`**
- Lấy tất cả items của nhân viên
- Tính `days_until_expiry = (expires_at - today).days` nếu expires_at not null
- Tính `is_expiring_soon = days_until_expiry <= 30`
- Tự động mark `status = expired` nếu `expires_at < today`

**`update_checklist_item(session, employee_id, item_id, data, user_id)`**
- Validate: `expires_at` bắt buộc nếu `document_type.has_expiry = True` và status = submitted
- Nếu `expires_at < today`: force `status = expired`

**`upload_document_file(session, employee_id, item_id, file, user_id)`**
- MinIO path: `recruitment/employee-documents/{employee_id}/{document_type_code}/{filename}`
- Tái dụng cùng pattern với `employee_attachment_service`

**`get_missing_documents_report(session, status, department_id?) → List[EmployeeChecklistSummary]`**
- JOIN employees + checklist items
- Lọc theo `is_required = True`
- Tính tỷ lệ hoàn thành

**`export_labor_report_excel(session, year, month) → bytes`**

Xuất danh sách lao động mới theo mẫu Thông tư 23/2014/TT-BLĐTBXH:
- Lọc `Employee` có `EmployeeJobRecord.probation_start_date` trong tháng/năm chỉ định
- Columns theo biểu mẫu: STT, Họ tên, Ngày sinh, Giới tính, CCCD, Vị trí, Phòng ban, Ngày vào làm, Loại HĐ
- Header: tên công ty, tháng báo cáo, người lập biểu

### Nhắc nhở tự động (tích hợp `reminder_service`)

**Scheduled tasks:**
- Hàng ngày: tìm checklist `expires_at ∈ [today+1, today+30]` → tạo reminder cho HR
- Hàng tuần: tìm nhân viên có `missing_count > 0` và `join_date > 30 ngày trước` → nhắc HR hoàn thiện hồ sơ
- Hàng quý (ngày đầu quý): nhắc HR chuẩn bị báo cáo biến động lao động (TT23/2014)

---

## Thiết kế Frontend

### Tab "Hồ sơ pháp lý" trong `EmployeeDetailView.vue`

Thêm tab mới vào hồ sơ nhân viên (bên cạnh các tab hiện có):

**DataTable checklist:**

| Cột | Nội dung |
|---|---|
| Loại giấy tờ | Tên + "Bắt buộc" badge nếu required |
| Trạng thái | Tag: Chưa nộp 🔴 / Đã nộp ✅ / Hết hạn 🔴 / Miễn ⚪ |
| Ngày nộp | |
| Ngày hết hạn | Đỏ nếu < 30 ngày hoặc đã qua |
| File | Icon download nếu có |
| Thao tác | Cập nhật / Upload / Miễn |

**Progress bar** tổng hoàn thành: `submitted / total_required * 100%`

**Button "Upload"** → file picker → upload ngay

### `DocumentChecklistView.vue` (trang HR tổng hợp)

Trong module Recruitment, tab "Hồ sơ pháp lý":
- DataTable: danh sách nhân viên còn thiếu giấy tờ
- Filter: phòng ban, trạng thái (thiếu / sắp hết hạn)
- Button "Xuất báo cáo lao động" → download Excel TT23/2014

---

## Cấu trúc file

```
backend/
  alembic/versions/0038_add_document_checklists.py     (NEW)
  app/models/recruitment.py                             (EDIT: DocumentChecklistType, EmployeeDocumentChecklist)
  app/schemas/recruitment.py                            (EDIT)
  app/services/document_checklist_service.py           (NEW)
  app/api/v1/endpoints/recruitment.py                  (EDIT: document checklist endpoints)
  app/api/v1/endpoints/employees.py                    (EDIT: thêm /employees/{id}/document-checklist)
  tests/test_recruitment_document_checklist.py         (NEW)

frontend/
  src/services/recruitmentService.ts                   (EDIT)
  src/views/employees/DocumentChecklistTab.vue         (NEW — tab trong EmployeeDetailView)
  src/views/employees/EmployeeDetailView.vue           (EDIT: thêm tab)
  src/views/recruitment/components/DocumentChecklistSummaryTab.vue (NEW)
```

---

## Kế hoạch theo Slice

### Slice 1 — Backend: Models + Migration + Seed

### Slice 2 — Backend: Checklist CRUD + Upload + Init auto

### Slice 3 — Backend: Report + Reminder integration + TT23 Excel export

### Slice 4 — Backend: Tests

### Slice 5 — Frontend: Tab trong EmployeeDetailView

### Slice 6 — Frontend: DocumentChecklistSummaryTab (HR tổng hợp)

---

## Rủi ro và cách xử lý

| Rủi ro | Mức độ | Cách xử lý |
|---|---|---|
| Nhân viên cũ (trước khi có module này) không có checklist | Trung bình | Cung cấp API batch-init để HR khởi tạo checklist hàng loạt theo phòng ban |
| Giấy tờ miễn vs thiếu bị nhầm trong báo cáo | Thấp | Status `waived` tách biệt với `not_submitted`; báo cáo chỉ cảnh báo `not_submitted` |
| Ngày hết hạn sức khỏe nhắc sai | Thấp | `has_expiry = true` cho sức khỏe; `expires_at` do HR nhập khi upload; check ≤ 30 ngày |
| Xuất Excel TT23 sai mẫu theo năm | Trung bình | Hard-code theo mẫu năm hiện hành; ghi rõ "Theo TT23/2014" trong header sheet |
