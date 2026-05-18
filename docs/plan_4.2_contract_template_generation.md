# Kế hoạch thực hiện — 4.2. Mẫu hợp đồng (Sinh hợp đồng từ mẫu)

**Phạm vi:** Upload mẫu DOCX → Sinh hợp đồng tự động điền dữ liệu nhân viên → Tải về Word  
**Phụ thuộc:** `4.1 Hợp đồng lao động` ✅ · `ContractTemplate catalog` ✅ · `DOCX inspection` ✅

---

## Trạng thái hiện tại

| Thành phần | Trạng thái | Ghi chú |
|---|---|---|
| Model `ContractTemplate` | ✅ Đã có | Catalog — CRUD, placeholder, health-summary |
| Model `ContractTemplatePlaceholder` | ✅ Đã có | Khai báo token → source_path |
| API CRUD `/contract-templates` | ✅ Đã có | List, create, update, soft-delete |
| API `inspect-docx` | ✅ Đã có | Quét file DOCX tìm placeholder |
| `SUPPORTED_TEMPLATE_FIELDS` registry | ✅ Đã có | ~20 tokens — employee, contract_draft, system |
| `storage_path` trong ContractTemplate | ⚠️ Chỉ là string | Không có endpoint upload/download file |
| **Upload file mẫu vào MinIO** | ❌ Chưa có | Cần thêm endpoint |
| **Render DOCX với dữ liệu thực** | ❌ Chưa có | Cần service render + data resolver |
| **Endpoint sinh hợp đồng** | ❌ Chưa có | `POST /employees/{id}/contracts/{cid}/generate` |
| **Frontend "Sinh hợp đồng"** | ❌ Chưa có | Button trong ContractTab |
| `python-docx` dependency | ❌ Chưa cài | Cần thêm vào requirements.txt |

---

## Phân tích kỹ thuật

### 1. Thư viện cần thêm

```
python-docx>=1.1.0   # Đọc/ghi DOCX
```

Không cần `num2words` — sẽ viết hàm chuyển số → chữ tiếng Việt nội bộ (chỉ cần cho currency, tối đa hàng tỷ đồng).

### 2. Vấn đề rendering DOCX

DOCX lưu nội dung trong XML. Placeholder `{{token}}` thường bị **tách vỡ qua nhiều `<w:r>` run** do Word tự phân đoạn khi soạn thảo.  
Ví dụ: `{{employee_full_name}}` có thể thành `{{empl`, `oyee_full`, `_name}}` trong 3 run riêng.

**Giải pháp (đã áp dụng trong inspection hiện tại):** Gộp toàn bộ text của paragraph → thay thế placeholder → ghi lại vào run đầu tiên, xóa run còn lại. Áp dụng cùng logic cho header/footer.

### 3. Token registry hiện tại (`SUPPORTED_TEMPLATE_FIELDS`)

| Token | Source | Ghi chú |
|---|---|---|
| `contract_number` | `contract.contract_number` | |
| `contract_start_date` | `contract.effective_from` | formatter: `vn_date` |
| `contract_end_date` | `contract.effective_to` | formatter: `vn_date` |
| `department_name` | `employee_job_records[is_current].department.name` | |
| `employee_full_name` | `employee.full_name` | |
| `employee_birthday` | `employee.date_of_birth` | formatter: `vn_date` |
| `employee_gender` | `employee.gender` → "Nam"/"Nữ" | |
| `employee_cccd` | `employee.id_number` | |
| `employee_cccd_issued_on` | `employee.id_issued_date` | formatter: `vn_date` |
| `employee_cccd_issued_by` | `employee.id_issued_by` | |
| `employee_address` | `employee.permanent_*` fields | Ghép địa chỉ đầy đủ |
| `employee_temp_address` | `employee.current_*` fields | |
| `employee_phone` | `employee.phone` | |
| `employee_personal_email` | `employee.personal_email` | |
| `position_title` | `employee_job_records[is_current].job_title.name` | |
| `insurance_salary` | `contract.insurance_salary` | formatter: `currency_vnd` |
| `insurance_salary_words` | `contract.insurance_salary` | Chuyển sang chữ VN |
| `Ngày` / `Tháng` / `Năm` | `contract.signed_date` | |
| `Loại_HĐLĐ__` | `contract_category.name` | |

Token `Thời_hạn_trả_lương` → Chưa có source trong DB, tạm để trống (không bắt buộc).

### 4. Formatters

| Formatter | Đầu vào | Đầu ra ví dụ |
|---|---|---|
| `vn_date` | `date(2024, 1, 15)` | `"15 tháng 01 năm 2024"` |
| `currency_vnd` | `Decimal("8000000")` | `"8.000.000 đồng"` |
| `gender_label` | `"male"/"female"` | `"Nam"/"Nữ"` |
| `number_to_words_vn` | `Decimal("8000000")` | `"Tám triệu đồng"` |

---

## Cấu trúc file mới / thay đổi

```
backend/
  requirements.txt                                      (UPDATE — thêm python-docx)
  app/core/storage.py                                   (UPDATE — thêm save_template_file, download_template)
  app/services/contract_generate_service.py             (NEW — data resolver + render)
  app/api/v1/endpoints/other_business_catalog.py        (UPDATE — thêm upload/download template)
  app/api/v1/endpoints/employee_contracts.py            (UPDATE — thêm generate endpoint)
  tests/test_contract_generation.py                     (NEW)

frontend/
  src/views/employees/ContractTab.vue                   (UPDATE — nút "Sinh hợp đồng")
  src/views/employees/ContractGenerateDialog.vue        (NEW — chọn template, trigger generate)
```

---

## Thiết kế Backend

### 5. `storage.py` — Thêm 2 hàm

```python
async def save_template_file(template_id: int, upload: UploadFile) -> tuple[str, int]:
    """Upload file DOCX mẫu lên MinIO. Path: templates/{template_id}/{uuid}_{filename}"""
    ...

def get_template_stream(object_name: str) -> Generator[bytes, None, None]:
    """Stream template DOCX từ MinIO (dùng lại get_object_stream đã có)."""
    return get_object_stream(object_name)
```

### 6. Endpoints upload/download template (`other_business_catalog.py`)

```
POST /contract-templates/{id}/upload
  — Permission: catalog:edit
  — Nhận UploadFile (.docx duy nhất, ≤ 5 MB)
  — Lưu MinIO → cập nhật storage_path, file_name, file_size, mime_type, file_checksum (md5)
  — Trả về ContractTemplateRead

GET /contract-templates/{id}/download
  — Permission: catalog:view
  — Stream DOCX từ MinIO
  — Header: Content-Disposition attachment; filename="{file_name}"
```

### 7. `contract_generate_service.py` (NEW)

```python
# ── Data resolver ─────────────────────────────────────────────────
async def build_contract_context(
    session: AsyncSession,
    employee_id: int,
    contract_id: int,
) -> dict[str, str]:
    """Tải Employee + EmployeeContract + EmployeeJobRecord → dict token: str_value."""
    ...

# ── Formatters ────────────────────────────────────────────────────
def fmt_vn_date(d: date | None) -> str:
    """15/01/2024  →  '15 tháng 01 năm 2024'"""

def fmt_currency_vnd(v: Decimal | None) -> str:
    """Decimal('8000000')  →  '8.000.000 đồng'"""

def number_to_words_vn(v: Decimal | None) -> str:
    """Decimal('8000000')  →  'Tám triệu đồng'"""

# ── Rendering ────────────────────────────────────────────────────
def render_contract_docx(
    template_path: Path,
    context: dict[str, str],
) -> bytes:
    """
    Đọc DOCX từ template_path, thay thế {{token}} bằng context values.
    Trả về bytes của DOCX đã render.

    Thuật toán:
    1. Mở DOCX bằng python-docx
    2. Với mỗi paragraph trong document.paragraphs + headers + footers:
       a. Gộp text toàn bộ runs thành một string
       b. Nếu string chứa {{...}}: thay thế bằng context values
       c. Ghi text đã thay thế vào run đầu tiên, xóa các run còn lại
       d. Giữ nguyên formatting của run đầu tiên
    3. Lưu ra bytes (io.BytesIO)
    """
    ...

async def generate_contract_document(
    session: AsyncSession,
    employee_id: int,
    contract_id: int,
    template_id: int,
) -> tuple[bytes, str]:
    """
    Orchestrator: load template → build context → render → return (docx_bytes, filename)
    filename = "HD_{contract_number}.docx"
    """
    ...
```

**Xử lý token không tìm thấy trong context:** Thay bằng chuỗi rỗng `""` (không raise error) — HR có thể điền tay sau.

**Xử lý placeholder tách vỡ qua nhiều run (core algorithm):**

```python
def _merge_and_replace_paragraph(paragraph, context: dict[str, str]) -> None:
    """Gộp runs, thay placeholder, ghi lại vào run đầu."""
    if not paragraph.runs:
        return
    full_text = "".join(r.text for r in paragraph.runs)
    if "{{" not in full_text:
        return
    replaced = _DOUBLE_PATTERN.sub(
        lambda m: context.get(m.group(1).strip(), ""),
        full_text,
    )
    paragraph.runs[0].text = replaced
    for run in paragraph.runs[1:]:
        run.text = ""
```

### 8. Generation endpoint (`employee_contracts.py`)

```
POST /employees/{employee_id}/contracts/{contract_id}/generate
  Body: { "template_id": int }
  Permission: contracts:edit
  
  Flow:
  1. Lấy contract → kiểm tra thuộc employee, không terminated
  2. Lấy template → kiểm tra is_active, có storage_path, document_kind khớp với contract
  3. Build context (load employee + job + contract data)
  4. Render DOCX → bytes
  5. Audit log: GENERATE_CONTRACT_DOCUMENT
  6. Return StreamingResponse(
       content=io.BytesIO(docx_bytes),
       media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
       headers={"Content-Disposition": f'attachment; filename="{filename}"'}
     )
```

---

## Thiết kế Frontend

### 9. `ContractGenerateDialog.vue` (NEW)

```
┌─────────────────────────────────────────────────────┐
│ Sinh hợp đồng từ mẫu                          [×]  │
├─────────────────────────────────────────────────────┤
│ Hợp đồng: HĐ-2024-001                              │
│                                                     │
│ Chọn mẫu hợp đồng *                                │
│ [Select filter ▼] ← lọc theo document_kind HĐ      │
│                                                     │
│ ℹ️  File Word (.docx) sẽ được tải về máy bạn       │
│                                                     │
│                          [Hủy]  [Tải về Word ↓]    │
└─────────────────────────────────────────────────────┘
```

- Chỉ hiện template `is_active = true` và `document_kind` khớp với contract
- Click "Tải về Word" → gọi `POST .../generate` với `responseType: 'blob'` → `downloadBlob()`
- Loading state khi đang render
- Error toast nếu template không có file hoặc render thất bại

### 10. Cập nhật `ContractTab.vue`

Thêm button "Sinh hợp đồng" trong `contract-actions` (chỉ hiện khi `status !== 'terminated'` và `canEdit`):

```html
<Button
  icon="pi pi-file-word"
  text rounded size="small"
  v-tooltip.top="'Sinh hợp đồng từ mẫu'"
  @click="openGenerate(c)"
/>
```

---

## Tests — `test_contract_generation.py`

```
test_upload_template_docx_success          — Upload file .docx → storage_path được set
test_upload_template_invalid_type_400      — Upload .pdf → 400
test_upload_template_too_large_400         — File >5MB → 400
test_download_template_success             — GET download → 200 + DOCX content-type
test_download_template_no_file_404         — Template chưa có file → 404

test_generate_contract_success             — Tạo DOCX thực, kiểm tra bytes > 0
test_generate_contract_wrong_employee_404  — contract_id không thuộc employee → 404
test_generate_contract_terminated_400      — Contract đã terminated → 400
test_generate_contract_no_template_file_422 — Template chưa có storage_path → 422
test_generate_contract_kind_mismatch_400   — Template labor_contract cho appendix → 400
test_generate_contract_unauth_401          — Không token → 401
test_generate_contract_no_perm_403         — Line manager → 403

test_render_docx_replaces_tokens           — Unit test render_contract_docx()
test_render_docx_split_run_placeholder     — Placeholder vỡ qua nhiều run → thay đúng
test_number_to_words_vn                    — "8000000" → "Tám triệu đồng"
test_fmt_vn_date                           — date(2024,1,15) → "15 tháng 01 năm 2024"
```

---

## Thứ tự triển khai

### Bước 1 — Dependency + Storage
1. Thêm `python-docx>=1.1.0` vào `requirements.txt`
2. Cài trong Docker: `docker compose build backend`
3. Thêm `save_template_file()` vào `storage.py`

### Bước 2 — Upload/Download template API
1. Thêm endpoint `POST /contract-templates/{id}/upload` vào `other_business_catalog.py`
2. Thêm endpoint `GET /contract-templates/{id}/download`

### Bước 3 — Rendering service
1. Tạo `app/services/contract_generate_service.py`
   - Hàm `build_contract_context()` — data resolver từ DB
   - Hàm `render_contract_docx()` — DOCX rendering với python-docx
   - Formatters: `fmt_vn_date`, `fmt_currency_vnd`, `number_to_words_vn`

### Bước 4 — Generation endpoint
1. Thêm `POST /employees/{id}/contracts/{cid}/generate` vào `employee_contracts.py`

### Bước 5 — Tests
1. Tạo `tests/test_contract_generation.py`
2. Cần fixture: tạo DOCX mẫu tối thiểu (có `{{employee_full_name}}`, `{{contract_number}}`)
3. Chạy pytest → tất cả pass

### Bước 6 — Frontend
1. Tạo `ContractGenerateDialog.vue`
2. Cập nhật `ContractTab.vue` — thêm button + dialog

### Bước 7 — Verify
1. Upload file DOCX mẫu thực vào template catalog
2. Từ tab Hợp đồng của nhân viên → Sinh hợp đồng → tải về
3. Kiểm tra file Word có dữ liệu điền đúng

---

## Rủi ro & Cách xử lý

| Rủi ro | Cách xử lý |
|---|---|
| Placeholder vỡ qua nhiều XML run | Dùng paragraph-merge algorithm: gộp text toàn run → thay → ghi vào run[0] |
| Token không có dữ liệu (trường None) | Thay bằng `""` — không raise error, HR điền tay sau |
| Template DOCX dùng MERGEFIELD thay vì `{{}}` | Cảnh báo trong health-summary; inspection đề xuất token thay thế |
| `document_kind` không khớp (mẫu phụ lục cho HĐ gốc) | Kiểm tra và trả 400 trong endpoint generate |
| File DOCX template không tồn tại trong MinIO | Trả 422 — storage_path trống hoặc file bị xóa |
| Ký tự đặc biệt trong XML (< > & ' ") | python-docx tự xử lý XML escaping khi ghi text qua `.text` property |
| Render chậm với template lớn (nhiều trang) | Không cần optimize — DOCX rendering rất nhanh (<1s thông thường) |

---

## Kết quả mong đợi sau 4.2

- HR upload file DOCX mẫu vào danh mục template (qua trang Catalog)
- Từ tab Hợp đồng của nhân viên bấm "Sinh hợp đồng" → chọn mẫu → tải về DOCX
- File Word được điền sẵn: tên nhân viên, CCCD, địa chỉ, số hợp đồng, ngày ký, lương BHXH bằng số & bằng chữ
- Token không có dữ liệu để trống — HR chỉnh sửa thủ công trước khi in
