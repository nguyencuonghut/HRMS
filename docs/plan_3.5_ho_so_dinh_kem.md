# Kế hoạch thực hiện — 3.5. Hồ sơ đính kèm

**Phạm vi:** Upload & quản lý phiên bản tài liệu đính kèm hồ sơ nhân viên  
**Phụ thuộc:** `1.2 RBAC` ✅ · `3.1 Thông tin cá nhân` ✅ · MinIO đã cấu hình ✅

---

## Trạng thái hiện tại

| Thành phần | Trạng thái |
|---|---|
| MinIO object storage | ✅ Đã hoạt động — `hrms-attachments` bucket |
| `app/core/storage.py` — upload/download/delete helpers | ✅ Đã có |
| Pattern đính kèm (`job_position_attachments`) | ✅ Đã có, dùng làm reference |
| Bảng `employee_attachments` | ❌ Chưa có |
| Endpoints upload/download cho nhân viên | ❌ Chưa có |
| Tab "Tài liệu" trong EmployeeDetailView | ❌ Chưa có |

---

## Phạm vi 3.5

| Tính năng | Chi tiết |
|---|---|
| Upload tài liệu | Ảnh thẻ, CCCD, bằng cấp, chứng chỉ, hộ chiếu, hợp đồng, khác |
| Quản lý phiên bản | Mỗi lần upload = 1 phiên bản mới; lịch sử đầy đủ, phiên bản mới nhất nổi bật |
| Download | Stream qua API — không expose URL MinIO trực tiếp |
| Xóa | Xóa DB record + MinIO object, có confirm |
| Phân quyền | `employees:view` → xem/tải; `employees:edit` → upload/xóa |
| Audit log | `UPLOAD_ATTACHMENT`, `DELETE_ATTACHMENT` |

**Giới hạn file:**
- Kích thước tối đa: **20 MB** mỗi file
- Định dạng chấp nhận: `image/*`, `application/pdf`, `.doc`, `.docx`

---

## Thiết kế cơ sở dữ liệu

### Bảng `employee_attachments`

```sql
CREATE TABLE employee_attachments (
    id              SERIAL PRIMARY KEY,
    employee_id     INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,

    document_type   VARCHAR(50) NOT NULL,   -- xem bảng giá trị bên dưới
    description     VARCHAR(255),            -- mô tả tự do (VD: "CCCD mặt trước")
    file_name       VARCHAR(255) NOT NULL,   -- tên file gốc
    file_path       VARCHAR(500) NOT NULL,   -- object_name trong MinIO
    file_size       INTEGER,                 -- bytes
    mime_type       VARCHAR(100),

    uploaded_at     TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_emp_attachments_employee_id ON employee_attachments (employee_id);
CREATE INDEX ix_emp_attachments_doc_type    ON employee_attachments (employee_id, document_type);
```

### Giá trị `document_type`

| Giá trị | Hiển thị | Ghi chú |
|---|---|---|
| `avatar` | Ảnh thẻ | |
| `id_card_front` | CCCD / CMND — Mặt trước | Tách riêng vì CCCD có 2 mặt |
| `id_card_back` | CCCD / CMND — Mặt sau | |
| `passport` | Hộ chiếu | |
| `work_permit` | Giấy phép lao động | |
| `degree` | Bằng cấp / Văn bằng | |
| `certificate` | Chứng chỉ | |
| `resume` | CV / Sơ yếu lý lịch | |
| `other` | Khác | |

> **Lý do tách `id_card_front` / `id_card_back`:** CCCD/CMND bắt buộc phải có đủ 2 mặt trong hồ sơ nhân sự. Dùng 2 document_type riêng thay vì field `side` phụ — đơn giản hơn, versioning độc lập cho từng mặt, không cần thêm cột DB.

**Phiên bản:** Không có cột `version`. Phiên bản = tất cả records cùng `employee_id + document_type`, sắp xếp theo `uploaded_at` DESC — bản mới nhất là "hiện tại".

---

## Storage path

```
employees/{employee_id}/{uuid8}_{original_filename}
```

Ví dụ: `employees/42/a3f8c1d2_cccd_mat_truoc.jpg`

Thêm hàm generic vào `storage.py`:

```python
async def save_employee_attachment(
    employee_id: int, upload: UploadFile
) -> tuple[str, int]:
    content = await upload.read()
    safe_name = Path(upload.filename or "file").name
    object_name = f"employees/{employee_id}/{uuid.uuid4().hex[:8]}_{safe_name}"
    _client().put_object(...)
    return object_name, len(content)
```

---

## Schema Pydantic

```python
DOCUMENT_TYPE_LABELS = {
    "avatar":       "Ảnh thẻ",
    "id_card":      "CCCD / CMND",
    "passport":     "Hộ chiếu",
    "work_permit":  "Giấy phép lao động",
    "degree":       "Bằng cấp / Văn bằng",
    "certificate":  "Chứng chỉ",
    "resume":       "CV / Sơ yếu lý lịch",
    "other":        "Khác",
}

class EmployeeAttachmentRead(BaseModel):
    id:            int
    employee_id:   int
    document_type: str
    document_type_label: str       # denormalized từ DOCUMENT_TYPE_LABELS
    description:   Optional[str]
    file_name:     str
    file_path:     str             # object_name trong MinIO (ẩn với FE)
    file_size:     Optional[int]
    mime_type:     Optional[str]
    uploaded_at:   datetime
    download_url:  str             # /api/v1/employees/{id}/attachments/{att_id}/download
```

---

## API Endpoints

```
GET    /api/v1/employees/{id}/attachments
       → list[EmployeeAttachmentRead]
       → Query param: ?document_type= (tùy chọn, lọc theo loại)
       → Quyền: employees:view

POST   /api/v1/employees/{id}/attachments
       → multipart/form-data: file (UploadFile) + document_type (str) + description (str, optional)
       → Response: EmployeeAttachmentRead (201)
       → Validate: file size ≤ 20MB, mime type hợp lệ
       → Quyền: employees:edit
       → Audit: UPLOAD_ATTACHMENT

GET    /api/v1/employees/{id}/attachments/{att_id}/download
       → StreamingResponse (Content-Disposition: attachment)
       → Quyền: employees:view

DELETE /api/v1/employees/{id}/attachments/{att_id}
       → Xóa DB record + MinIO object
       → IDOR: kiểm tra att.employee_id == id
       → Quyền: employees:edit
       → Audit: DELETE_ATTACHMENT
```

---

## Audit log actions

| Thao tác | Action |
|---|---|
| Upload tài liệu | `UPLOAD_ATTACHMENT` |
| Xóa tài liệu | `DELETE_ATTACHMENT` |

---

## Frontend

### Tab mới trong `EmployeeDetailView.vue`

```html
<Tab value="attachments" :disabled="isNew">Tài liệu</Tab>
...
<TabPanel value="attachments">
  <AttachmentsTab v-if="!isNew && employeeId" :employee-id="employeeId" />
</TabPanel>
```

### Component `AttachmentsTab.vue`

**Không dùng `<style scoped>`** — chỉ global classes từ `main.scss`.

Layout: Nhóm tài liệu theo `document_type`, mỗi nhóm là 1 section-card.

```
┌───────────────────────────────────────────────────────────┐
│ [Upload tài liệu]  ← nút mở dialog chọn loại + file      │
├───────────────────────────────────────────────────────────┤
│ Ảnh thẻ                                                    │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ avatar_2024.jpg · 245 KB · 12/01/2024  [Tải] [Xóa] │ │
│  │ avatar_2022.jpg · 198 KB · 05/03/2022  [Tải] [Xóa] │ │  ← phiên bản cũ (mờ hơn)
│  └──────────────────────────────────────────────────────┘ │
├───────────────────────────────────────────────────────────┤
│ CCCD / CMND                                               │
│  cmnd_mat_truoc.pdf · 1.2 MB · 15/06/2023  [Tải] [Xóa] │
│  cmnd_mat_sau.pdf  · 950 KB · 15/06/2023  [Tải] [Xóa]  │
├───────────────────────────────────────────────────────────┤
│ Bằng cấp / Văn bằng                                      │
│  bang_dai_hoc.pdf  · 2.1 MB · 20/09/2015  [Tải] [Xóa]  │
└───────────────────────────────────────────────────────────┘
```

**Dialog Upload:**
- Select `document_type` (Select component)
- Input `description` (InputText, optional)
- File picker (nhập file, hiển thị tên + size sau khi chọn)
- Validate client-side: size ≤ 20MB, mime type

**Hiển thị phiên bản:**
- Bản mới nhất (index 0 trong group): full opacity, không có nhãn đặc biệt
- Bản cũ hơn: class `muted-text`, label nhỏ "Phiên bản cũ"

**Global CSS cần thêm vào `main.scss`:**

```scss
.attachment-list    { display: flex; flex-direction: column; gap: 0.5rem; }
.attachment-row     { display: flex; align-items: center; gap: 0.75rem; padding: 0.5rem 0; border-bottom: 1px solid var(--p-content-border-color); }
.attachment-row:last-child { border-bottom: none; }
.attachment-icon    { font-size: 1.25rem; color: var(--p-primary-color); flex-shrink: 0; }
.attachment-info    { flex: 1; min-width: 0; }
.attachment-name    { font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.attachment-meta    { font-size: 0.8rem; color: var(--l-text-muted); }
.attachment-actions { display: flex; gap: 0.25rem; flex-shrink: 0; }
.attachment-old     { opacity: 0.55; }
```

### `employeeService.ts` bổ sung

```typescript
export const DOCUMENT_TYPE_LABELS: Record<string, string> = {
  avatar:         'Ảnh thẻ',
  id_card_front:  'CCCD / CMND — Mặt trước',
  id_card_back:   'CCCD / CMND — Mặt sau',
  passport:       'Hộ chiếu',
  work_permit:    'Giấy phép lao động',
  degree:         'Bằng cấp / Văn bằng',
  certificate:    'Chứng chỉ',
  resume:         'CV / Sơ yếu lý lịch',
  other:          'Khác',
}

// Nhóm hiển thị UI: gộp id_card_front + id_card_back thành "CCCD / CMND"
export const DOCUMENT_TYPE_GROUPS: { label: string; types: string[] }[] = [
  { label: 'Ảnh thẻ',              types: ['avatar'] },
  { label: 'CCCD / CMND',          types: ['id_card_front', 'id_card_back'] },
  { label: 'Hộ chiếu',             types: ['passport'] },
  { label: 'Giấy phép lao động',   types: ['work_permit'] },
  { label: 'Bằng cấp / Văn bằng', types: ['degree'] },
  { label: 'Chứng chỉ',            types: ['certificate'] },
  { label: 'CV / Sơ yếu lý lịch', types: ['resume'] },
  { label: 'Khác',                 types: ['other'] },
]

export interface EmployeeAttachmentRead {
  id:                  number
  employee_id:         number
  document_type:       string
  document_type_label: string
  description:         string | null
  file_name:           string
  file_path:           string
  file_size:           number | null
  mime_type:           string | null
  uploaded_at:         string
  download_url:        string
}

// Service methods
getAttachments:     (id, document_type?) => api.get(...)
uploadAttachment:   (id, formData: FormData) => api.post(...)   // multipart
downloadAttachment: (id, attId) => api.get(..., { responseType: 'blob' })
deleteAttachment:   (id, attId) => api.delete(...)
```

> **Upload dùng FormData** vì multipart/form-data — không phải JSON body.

---

## Seed dữ liệu

Không seed file thật vào MinIO (phức tạp trong môi trường dev). Seed table trống — test thủ công qua UI.

---

## Tests

File: `backend/tests/test_employee_attachments.py`

```
test_list_attachments_empty
test_upload_attachment_success               → 201, record trong DB, object trong MinIO
test_upload_attachment_file_too_large_413   → file > 20MB → 413
test_download_attachment_success            → StreamingResponse 200
test_download_wrong_employee_404            → IDOR: att của nhân viên khác → 404
test_delete_attachment_success              → xóa DB + MinIO
test_delete_wrong_employee_404             → IDOR protection
test_upload_audit_log                       → UPLOAD_ATTACHMENT trong audit log
test_viewer_cannot_upload_403              → employees:view → upload → 403
test_viewer_cannot_delete_403              → employees:view → delete → 403
test_filter_by_document_type               → ?document_type=degree → chỉ trả degree
test_multiple_versions_same_type           → 2 uploads cùng loại → 2 records
```

**Cleanup fixture:** `DELETE FROM employee_attachments WHERE employee_id IN (...test employees...)`  
MinIO cleanup: gọi `delete_attachment(att.file_path)` trong cleanup.

---

## Thứ tự triển khai

### Bước 1 — Model & Migration
1. Tạo `EmployeeAttachment` model trong `backend/app/models/employee_attachment.py`
2. Đăng ký vào `backend/app/models/__init__.py`
3. Tạo migration `0011_create_employee_attachments.py`
4. Chạy migration trong container

### Bước 2 — Backend Storage & Service
1. Thêm `save_employee_attachment()` vào `backend/app/core/storage.py`
2. Tạo `backend/app/schemas/employee_attachment.py` (hoặc bổ sung vào `employee.py`)
3. Thêm service logic vào `backend/app/services/employee_service.py` hoặc file riêng
   - `get_attachments(session, employee_id, document_type?)` 
   - `get_attachment_or_404(session, employee_id, att_id)`
4. Thêm 4 endpoints vào `backend/app/api/v1/endpoints/employees.py`

### Bước 3 — Tests backend
1. Tạo `backend/tests/test_employee_attachments.py`
2. Chạy pytest → tất cả pass

### Bước 4 — Frontend
1. Bổ sung `DOCUMENT_TYPE_LABELS`, `EmployeeAttachmentRead`, 4 service methods vào `employeeService.ts`
2. Thêm CSS attachment classes vào `main.scss`
3. Tạo `frontend/src/views/employees/AttachmentsTab.vue`
4. Thêm tab "Tài liệu" vào `EmployeeDetailView.vue`

### Bước 5 — Phân quyền & Audit log (Verify)
1. Xác nhận `employees:view` / `employees:edit` đúng trên 4 endpoints
2. Xác nhận `UPLOAD_ATTACHMENT` và `DELETE_ATTACHMENT` có trong audit log

---

## Rủi ro thiết kế cần tránh

| Rủi ro | Cách xử lý |
|---|---|
| Expose URL MinIO trực tiếp | Stream qua `/download` endpoint — không dùng presigned URL |
| Upload không giới hạn size | Validate trong endpoint: `if file.size > 20_971_520: raise 413` |
| Xóa DB nhưng không xóa MinIO | Xóa MinIO **trước** commit DB, hoặc xóa MinIO sau commit (file orphan vẫn chấp nhận được) |
| IDOR khi download/delete | `_get_att_or_404()` luôn kiểm tra `att.employee_id == employee_id` |
| File name với ký tự đặc biệt trong Content-Disposition | Encode UTF-8 → latin-1 (pattern đã dùng trong job_positions) |
| MinIO không có bucket khi test | `ensure_bucket()` gọi khi startup — đảm bảo bucket tồn tại |

---

## Kết quả mong đợi sau 3.5

- HR có thể upload ảnh thẻ, CCCD, bằng cấp, chứng chỉ vào hồ sơ nhân viên
- Lịch sử phiên bản: mỗi upload mới không ghi đè — giữ lại bản cũ
- Download file an toàn qua API proxy, không lộ storage URL
- Audit log đầy đủ: ai upload/xóa file nào, lúc nào
