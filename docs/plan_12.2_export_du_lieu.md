# Kế hoạch triển khai — 12.2. Export dữ liệu

**Phạm vi:** Biểu mẫu BHXH chuẩn Nhà nước · PDF export · Template chuẩn doanh nghiệp  
**Phụ thuộc:** 11.6 Unified Export Center ✅ · 6.x Bảo hiểm ✅ · 7.x Lương BHXH ✅  
**Căn cứ nghiệp vụ:** FEATURES.md §12.2  
**Đặc điểm:** Export infrastructure (11.6) đã hoàn thành; plan này bổ sung biểu mẫu BHXH Nhà nước và PDF

---

## Trạng thái hiện tại

| Thành phần | Trạng thái | Ghi chú |
|---|---|---|
| Unified Export Center | ✅ Hoàn thành | Plan 11.6 — ExportService, Celery jobs |
| Export Excel inline (các module) | ✅ Hoàn thành | StreamingResponse trực tiếp |
| Export hồ sơ nhân viên (5 sheet) | ✅ Hoàn thành | `employee_export_service.py` |
| Excel style chuẩn (header, border) | ✅ Hoàn thành | Tích hợp trong export_service |
| Biểu mẫu BHXH chuẩn Nhà nước | ❌ Chưa có | D02-LT, D03-TS, C12-TS |
| PDF export | ❌ Chưa có | WeasyPrint chưa cài |
| Template chuẩn doanh nghiệp (letterhead) | ❌ Chưa có | |
| Export danh sách BHXH theo cơ quan | ❌ Chưa có | |

---

## Phạm vi 12.2

### Trong phạm vi

1. **Biểu mẫu BHXH theo chuẩn cơ quan Nhà nước:**
   - **D02-LT** — Danh sách lao động tham gia BHXH, BHYT, BHTN
   - **D03-TS** — Bảng tổng hợp mức đóng BHXH, BHYT, BHTN
   - **C12-TS** — Danh sách thanh toán trợ cấp ốm đau, thai sản (stub — chờ module nghiệp vụ)
2. **PDF export** — xuất bất kỳ báo cáo Excel thành PDF qua LibreOffice headless (đã có trong Docker)
3. **Template chuẩn doanh nghiệp** — Excel có header logo + tên công ty + ngày xuất (áp dụng cho tất cả export từ unified center)
4. **Export danh sách BHXH có đầy đủ thông tin** — employee code, name, CCCD, bhxh_code, wage, period

### Ngoài phạm vi

- Ký số PDF (digital signing)
- Gửi file tự động cho cơ quan BHXH
- Định dạng XML/eClaims BHXH online
- Lưu file dài hạn (>7 ngày) — đã covered bởi 11.6 (7 ngày)
- Custom formula / pivot trong Excel

---

## Biểu mẫu BHXH — Thiết kế chi tiết

### D02-LT — Danh sách lao động tham gia BHXH/BHYT/BHTN

**Căn cứ:** Quyết định 595/QĐ-BHXH (biểu mẫu BHXH Việt Nam)

**Cấu trúc file:** 1 sheet với format cố định theo mẫu cơ quan

| Cột | Header | Nguồn dữ liệu |
|---|---|---|
| STT | Số thứ tự | auto |
| Họ và tên | | `employees.full_name` |
| Ngày sinh | | `employees.date_of_birth` |
| Giới tính | | `employees.gender` |
| Số CCCD/CMND | | `employees.id_number` |
| Số sổ BHXH | | `employee_insurance_profiles.bhxh_code` |
| Số thẻ BHYT | | `employee_insurance_profiles.bhyt_code` |
| Chức danh | | `job_titles.name` (via `employee_job_records`) |
| Mức lương đóng BHXH | | `employee_insurance_profiles.insurance_salary` |
| Ngày tham gia | | `employee_insurance_profiles.participation_date` |
| Ghi chú | | Trạng thái: active/suspended |

**Header cố định:**
```
DANH SÁCH LAO ĐỘNG THAM GIA BHXH, BHYT, BHTN
Đơn vị: [COMPANY_NAME]              Mã đơn vị: [COMPANY_BHXH_CODE]
Tháng/Kỳ: [month]/[year]            Tỉnh/TP: [PROVINCE]
```

**Tham số query:**
```
GET /exports/bhxh/d02-lt?year=2026&month=5&department_id=<id>
```

### D03-TS — Bảng tổng hợp mức đóng BHXH/BHYT/BHTN

| Cột | Nội dung | Công thức |
|---|---|---|
| STT | | auto |
| Họ tên | | |
| Lương đóng BHXH | | `insurance_salary` |
| BHXH NLĐ đóng (8%) | | `insurance_salary × 8%` |
| BHYT NLĐ đóng (1.5%) | | `insurance_salary × 1.5%` |
| BHTN NLĐ đóng (1%) | | `insurance_salary × 1%` |
| BHXH NSDLĐ đóng (17%) | | `insurance_salary × 17%` |
| BHYT NSDLĐ đóng (3%) | | `insurance_salary × 3%` |
| BHTN NSDLĐ đóng (1%) | | `insurance_salary × 1%` |
| Tổng NLĐ đóng | | BHXH + BHYT + BHTN NLĐ |
| Tổng NSDLĐ đóng | | BHXH + BHYT + BHTN NSDLĐ |

**Hàng tổng cộng** (bold, border dày) ở cuối bảng.

**Tham số:**
```
GET /exports/bhxh/d03-ts?year=2026&month=5
```

---

## PDF Export — LibreOffice Headless

LibreOffice đã có trong Docker image (xác nhận trong Dockerfile).

### Workflow

```
Người dùng request PDF export
        ↓
Backend: export Excel (BytesIO) → save /tmp/report_{job_id}.xlsx
        ↓
subprocess: libreoffice --headless --convert-to pdf /tmp/report_{job_id}.xlsx
        ↓
Đọc /tmp/report_{job_id}.pdf → StreamingResponse
        ↓
Cleanup /tmp files sau khi response
```

### Service helper

```python
# backend/app/services/pdf_export_service.py

import subprocess
import tempfile
import os
from io import BytesIO

def xlsx_to_pdf(xlsx_bytes: bytes) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        f.write(xlsx_bytes)
        xlsx_path = f.name

    out_dir = tempfile.mkdtemp()
    try:
        subprocess.run(
            ["libreoffice", "--headless", "--convert-to", "pdf",
             "--outdir", out_dir, xlsx_path],
            timeout=30,
            capture_output=True,
            check=True,
        )
        pdf_path = os.path.join(out_dir, os.path.basename(xlsx_path).replace(".xlsx", ".pdf"))
        with open(pdf_path, "rb") as pf:
            return pf.read()
    finally:
        os.unlink(xlsx_path)
        for f in os.listdir(out_dir):
            os.unlink(os.path.join(out_dir, f))
        os.rmdir(out_dir)
```

**Timeout:** 30 giây — đủ cho file < 5000 dòng.

---

## Template chuẩn doanh nghiệp

### Header block (áp dụng cho tất cả export)

```
Hàng 1: [Logo space]    TÊN CÔNG TY / ĐƠN VỊ
Hàng 2:                 [Tên báo cáo — bold, font 14]
Hàng 3:                 Ngày xuất: dd/mm/yyyy hh:mm
Hàng 4: (trống)
Hàng 5: → Header bảng bắt đầu
```

**Style constants** (áp dụng toàn bộ hệ thống):

```python
# backend/app/services/export_styles.py

HEADER_FILL    = PatternFill("solid", fgColor="1F4E79")   # xanh đậm
HEADER_FONT    = Font(bold=True, color="FFFFFF", size=10)
SUBHEADER_FILL = PatternFill("solid", fgColor="D6E4F0")   # xanh nhạt
ALT_ROW_FILL   = PatternFill("solid", fgColor="F5F5F5")   # xám nhạt alternate
TOTAL_FONT     = Font(bold=True)
BORDER_THIN    = Border(...)
COMPANY_FONT   = Font(bold=True, size=12)
```

---

## API Endpoints mới

### Endpoints BHXH — prefix `/api/v1/exports/bhxh`

```
GET /exports/bhxh/d02-lt
    ?year=2026&month=5&department_id=<int>&format=xlsx|pdf
    → StreamingResponse (xlsx hoặc pdf)
    Permission: insurance:view

GET /exports/bhxh/d03-ts
    ?year=2026&month=5&format=xlsx|pdf
    → StreamingResponse
    Permission: insurance:view
```

### Tích hợp vào Unified Export Center (bổ sung handlers)

Đăng ký thêm `report_type` vào `ExportService._HANDLERS`:

```python
_HANDLERS = {
    # ... existing handlers ...
    "bhxh-d02-lt": _export_bhxh_d02_lt,
    "bhxh-d03-ts": _export_bhxh_d03_ts,
    "employee-list-full": _export_employee_list_full,   # với letterhead
}
```

Frontend gọi qua `POST /reports/export` với `report_type="bhxh-d02-lt"` như các loại báo cáo khác.

---

## Service Logic

### File mới cần tạo

```
backend/app/services/
├── bhxh_export_service.py          ← NEW — D02-LT, D03-TS
├── pdf_export_service.py           ← NEW — LibreOffice wrapper
└── export_styles.py                ← NEW (hoặc UPDATE) — shared style constants

backend/app/api/v1/endpoints/
└── bhxh_exports.py                 ← NEW — direct endpoints D02-LT, D03-TS
```

### `bhxh_export_service.py`

```python
async def build_d02_lt(
    session: AsyncSession, *, year: int, month: int,
    department_id: int | None = None,
) -> io.BytesIO:
    # Query: employees JOIN insurance_profiles JOIN job_records JOIN departments
    # WHERE insurance_profile.status = 'active'
    # Filter by department if given
    # Build xlsx với format cố định D02-LT
    ...

async def build_d03_ts(
    session: AsyncSession, *, year: int, month: int,
) -> io.BytesIO:
    # Query: employees JOIN insurance_profiles
    # Tính các mức đóng theo % cố định (8%, 1.5%, 1%, 17%, 3%, 1%)
    # Build xlsx với tổng cộng
    ...
```

---

## Frontend Design

### Bổ sung vào Export Center (11.6 UI)

Tab mới "**Biểu mẫu BHXH**" trong `ExportCenterView.vue`:

```
┌─ Export Center ──────────────────────────────────────────┐
│ [Báo cáo nhân sự] [Báo cáo nghỉ phép] [Biểu mẫu BHXH] │
├──────────────────────────────────────────────────────────┤
│ Biểu mẫu BHXH                                           │
│                                                          │
│ Kỳ: Tháng [5 ▼] Năm [2026 ▼]  Phòng ban: [Tất cả ▼]   │
│                                                          │
│ ┌─────────────────────────────────────────┐             │
│ │ D02-LT Danh sách lao động tham gia BHXH │             │
│ │ [Xuất Excel] [Xuất PDF]                 │             │
│ └─────────────────────────────────────────┘             │
│                                                          │
│ ┌─────────────────────────────────────────┐             │
│ │ D03-TS Bảng tổng hợp mức đóng          │             │
│ │ [Xuất Excel] [Xuất PDF]                 │             │
│ └─────────────────────────────────────────┘             │
└──────────────────────────────────────────────────────────┘
```

### Service `bhxhExportService.ts` (file mới)

```typescript
const BASE = '/exports/bhxh'

export default {
  exportD02Lt: async (params: { year: number; month: number; department_id?: number; format: 'xlsx' | 'pdf' }) => {
    const res = await api.get(`${BASE}/d02-lt`, { params, responseType: 'blob' })
    downloadBlob(res.data, res.headers['content-disposition'])
  },
  exportD03Ts: async (params: { year: number; month: number; format: 'xlsx' | 'pdf' }) => {
    const res = await api.get(`${BASE}/d03-ts`, { params, responseType: 'blob' })
    downloadBlob(res.data, res.headers['content-disposition'])
  },
}
```

---

## Cấu trúc file

```
backend/app/
├── services/
│   ├── bhxh_export_service.py          ← NEW
│   ├── pdf_export_service.py           ← NEW
│   └── export_styles.py                ← NEW
├── api/v1/endpoints/
│   └── bhxh_exports.py                 ← NEW
└── api/v1/router.py                    ← UPDATE

frontend/src/
├── services/
│   └── bhxhExportService.ts            ← NEW
└── views/reports/
    └── ExportCenterView.vue            ← UPDATE (thêm tab Biểu mẫu BHXH)
```

---

## Kế hoạch theo Slice

### Slice 1 — BHXH D02-LT + D03-TS (Excel)

**Việc cần làm:**
1. Tạo `bhxh_export_service.py`:
   - `build_d02_lt(session, year, month, department_id)` → BytesIO
   - `build_d03_ts(session, year, month)` → BytesIO với row tổng cộng
2. Tạo `bhxh_exports.py` endpoints (2 GET)
3. Đăng ký router prefix `/exports/bhxh`
4. Tests:
   - `test_d02_lt_returns_xlsx` — verify content-type + data rows
   - `test_d02_lt_columns_correct` — verify column headers đúng mẫu
   - `test_d03_ts_calculation` — verify mức đóng 8%, 17% đúng
   - `test_bhxh_export_requires_permission` — 403 nếu không có `insurance:view`

**Verify:** `pytest tests/test_bhxh_export.py -v` pass.

---

### Slice 2 — PDF Export

**Việc cần làm:**
1. Kiểm tra LibreOffice có trong Docker: `docker exec hrms-backend-1 which libreoffice`
2. Tạo `pdf_export_service.py` với `xlsx_to_pdf(bytes) -> bytes`
3. Thêm `format=xlsx|pdf` parameter vào cả 2 endpoints BHXH
4. Thêm `format` support vào Unified Export Center (job có thêm format='pdf')
5. Tests:
   - `test_pdf_conversion_success` — upload xlsx → trả pdf bytes
   - `test_d02_lt_pdf_format` — endpoint với format=pdf → content-type application/pdf
   - `test_pdf_timeout_handling` — LibreOffice timeout → 500 với error message

**Verify:** Download PDF từ API mở được, có đúng nội dung.

---

### Slice 3 — Template chuẩn DN + Frontend

**Việc cần làm:**
1. Tạo `export_styles.py` — shared constants style (HEADER_FILL, FONTS, etc.)
2. Áp dụng letterhead cho D02-LT, D03-TS (company name, date, period)
3. Cập nhật `ExportCenterView.vue` — thêm tab "Biểu mẫu BHXH"
4. Tạo `bhxhExportService.ts` — 2 functions download
5. `vue-tsc --noEmit` clean

**Verify:** Xuất D02-LT từ UI, file mở được, có header đơn vị và ngày xuất đúng.

---

## Rủi ro & Cách xử lý

| Rủi ro | Cách xử lý |
|---|---|
| LibreOffice không có trong Docker image | Kiểm tra Dockerfile; nếu thiếu thêm `RUN apt-get install libreoffice` |
| PDF conversion chậm (>10s) | Chuyển sang Celery async task; frontend polling như export lớn |
| Format D02-LT thay đổi theo nghị định | Viết helper riêng `_build_d02_lt_header()` dễ sửa; comment rõ căn cứ pháp lý |
| `insurance_salary` null (NV chưa có profile) | Bỏ qua dòng có null, ghi chú trong file; hoặc dùng 0 với cờ |
| Column width không fit trong PDF | Hardcode column width cho BHXH templates thay vì auto-fit |

---

## Checklist

### Backend
- [ ] `pytest tests/test_bhxh_export.py` pass
- [ ] D02-LT format đúng header cố định theo mẫu Nhà nước
- [ ] D03-TS tính đúng % mức đóng
- [ ] PDF export hoạt động (libreoffice --headless)
- [ ] Permission `insurance:view` kiểm tra đúng

### Frontend
- [ ] Tab "Biểu mẫu BHXH" hiển thị đúng trong Export Center
- [ ] Xuất Excel → tải file thành công
- [ ] Xuất PDF → tải file PDF mở được
- [ ] `vue-tsc --noEmit` clean
