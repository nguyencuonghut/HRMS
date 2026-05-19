# Kế hoạch thực hiện — 5.4. Báo cáo nghỉ phép

**Phạm vi:** Tổng hợp, tra cứu và xuất Excel báo cáo nghỉ phép  
**Phụ thuộc:** 5.2 Quản lý số ngày phép ✅ · 5.3 Ghi nhận nghỉ phép ✅  
**Không có bảng mới** — tất cả đọc từ `leave_entitlements` + `leave_records` đã có

---

## Trạng thái hiện tại

| Thành phần | Trạng thái | Ghi chú |
|---|---|---|
| `leave_entitlements` + `leave_records` | ✅ Hoàn thành | Nguồn dữ liệu sẵn sàng |
| Phân bổ phòng ban (`employee_job_records`) | ✅ Có sẵn | `is_current=True` xác định phòng hiện tại |
| `openpyxl` | ✅ Cài sẵn (3.1.5) | Dùng để export Excel |
| Báo cáo theo nhân viên | ❌ Chưa có | |
| Báo cáo theo phòng ban | ❌ Chưa có | |
| Báo cáo tồn phép cuối năm | ❌ Chưa có | |
| Export Excel | ❌ Chưa có | |
| Frontend báo cáo | ❌ Chưa có | |

---

## Phân tích kỹ thuật

### 1. Ba loại báo cáo

#### Báo cáo A — Chi tiết nhân viên (`employee-summary`)

**Mục đích:** Xem từng nhân viên đã dùng bao nhiêu ngày phép của từng loại, còn bao nhiêu.

**Dữ liệu trả về (1 row = 1 nhân viên × 1 loại phép):**

```
employee_code | employee_name | department_name | leave_type_name
allocated_days | carryover_days | carryover_expires | used_days | remaining_days
record_count (số lần nghỉ thực tế, status='active')
```

**Filter:** `year` (required), `employee_id?`, `department_id?`, `leave_type_id?`, `keyword?`

**JOIN logic:**
```sql
SELECT e.*, d.name AS dept, lt.*, ent.*,
       COUNT(FILTER (r.status='active')) AS record_count
FROM leave_entitlements ent
JOIN employees e ON e.id = ent.employee_id
LEFT JOIN employee_job_records ejr ON ejr.employee_id = e.id AND ejr.is_current = true
LEFT JOIN departments d ON d.id = ejr.department_id
JOIN leave_types lt ON lt.id = ent.leave_type_id
LEFT JOIN leave_records r ON r.entitlement_id = ent.id AND r.status = 'active'
WHERE ent.year = :year
GROUP BY ent.id, e.id, d.id, lt.id
```

---

#### Báo cáo B — Tổng hợp phòng ban (`department-summary`)

**Mục đích:** HR manager xem tình hình nghỉ phép tổng hợp theo phòng ban + khoảng thời gian.

**Dữ liệu trả về (1 row = 1 phòng ban × 1 loại phép):**

```
department_name | leave_type_name
employee_count | total_records | total_days_taken
avg_days_per_employee
```

**Filter:** `year` (required), `month_from?` (1–12), `month_to?` (1–12), `department_id?`, `leave_type_id?`

**JOIN logic:**
```sql
SELECT d.name, lt.name,
       COUNT(DISTINCT e.id) AS employee_count,
       COUNT(r.id)          AS total_records,
       SUM(r.total_days)    AS total_days_taken
FROM leave_records r
JOIN employees e ON e.id = r.employee_id
LEFT JOIN employee_job_records ejr ON ejr.employee_id = e.id AND ejr.is_current = true
LEFT JOIN departments d ON d.id = ejr.department_id
JOIN leave_types lt ON lt.id = r.leave_type_id
WHERE r.status = 'active'
  AND EXTRACT(year FROM r.start_date) = :year
  [AND EXTRACT(month FROM r.start_date) BETWEEN :month_from AND :month_to]
GROUP BY d.id, d.name, lt.id, lt.name
ORDER BY d.name, lt.name
```

---

#### Báo cáo C — Tồn phép cuối năm (`year-end`)

**Mục đích:** Tổng kết phép tồn đọng mỗi nhân viên để lập kế hoạch năm sau.

**Dữ liệu trả về (1 row = 1 nhân viên × 1 loại phép có carryover_allowed=True):**

```
employee_code | employee_name | department_name
leave_type_name | allocated_days | carryover_days | used_days | remaining_days
will_carry = remaining_days (nếu > 0, đây là số sẽ chuyển sang năm sau)
```

**Filter:** `year` (required), `department_id?`

**JOIN logic:** Giống Báo cáo A nhưng chỉ lấy `leave_type.carryover_allowed = True` và sort theo `remaining_days DESC`.

---

### 2. Export Excel

**Format:** `.xlsx`, 1 sheet per báo cáo.

**Endpoint:** `GET /leave-reports/export?report_type={A|B|C}&...filters`

Response: `StreamingResponse` với `Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, `Content-Disposition: attachment; filename="...xlsx"`.

**Cấu trúc file Excel:**
- Row 1: Tiêu đề báo cáo (merge cells, bold, font 14)
- Row 2: "Năm: 2026 · Xuất ngày: 19/05/2026" (merge, italic)
- Row 3: Header columns (bold, background #1F3864 white text)
- Row 4+: Data (alternating row tint)
- Row cuối: Dòng tổng (SUM columns số)

**Hàm helper `build_xlsx(title, headers, rows) → BytesIO`** — dùng chung cho 3 loại.

---

### 3. Schemas Pydantic

```python
# Báo cáo A
class EmployeeSummaryRow(BaseModel):
    employee_id:     int
    employee_code:   str
    employee_name:   str
    department_name: str | None
    leave_type_id:   int
    leave_type_name: str
    leave_type_code: str
    allocated_days:  float
    carryover_days:  float
    carryover_expires: date | None
    used_days:       float
    remaining_days:  float
    record_count:    int   # số lần nghỉ thực tế (status=active)

class EmployeeSummaryReport(BaseModel):
    year:   int
    items:  list[EmployeeSummaryRow]
    total:  int   # total rows (cho phân trang)
    page:   int
    page_size: int

# Báo cáo B
class DepartmentSummaryRow(BaseModel):
    department_id:        int | None
    department_name:      str | None
    leave_type_id:        int
    leave_type_name:      str
    employee_count:       int
    total_records:        int
    total_days_taken:     float
    avg_days_per_employee: float

class DepartmentSummaryReport(BaseModel):
    year:       int
    month_from: int | None
    month_to:   int | None
    items:      list[DepartmentSummaryRow]

# Báo cáo C
class YearEndRow(BaseModel):
    employee_id:     int
    employee_code:   str
    employee_name:   str
    department_name: str | None
    leave_type_name: str
    allocated_days:  float
    carryover_days:  float
    used_days:       float
    remaining_days:  float
    will_carry:      float  # = max(0, remaining_days)

class YearEndReport(BaseModel):
    year:  int
    items: list[YearEndRow]
    total: int
    page:  int
    page_size: int
```

---

### 4. API Endpoints

```
GET /leave-reports/employee-summary    Báo cáo A — theo nhân viên
GET /leave-reports/department-summary  Báo cáo B — theo phòng ban
GET /leave-reports/year-end            Báo cáo C — tồn phép cuối năm
GET /leave-reports/export              Export Excel (report_type=A|B|C + filters)
```

**Query params chung:**
| Param | Type | Bắt buộc | Dùng ở |
|---|---|---|---|
| `year` | int | ✅ | A, B, C |
| `employee_id` | int? | | A |
| `department_id` | int? | | A, B, C |
| `leave_type_id` | int? | | A, B |
| `keyword` | str? | | A |
| `month_from` | int 1–12? | | B |
| `month_to` | int 1–12? | | B |
| `page` | int default 1 | | A, C |
| `page_size` | int default 50 | | A, C |
| `report_type` | A\|B\|C | ✅ | export |

**RBAC:** Tất cả đều cần `leaves:read`. Không có thao tác ghi.

---

### 5. Frontend — `LeaveReportView.vue`

**Route:** `/leave-reports` (thêm vào router.ts + AppMenu.vue dưới nhóm Nghỉ phép)

**Layout:**

```
┌──────────────────────────────────────────────────────────────────┐
│  Báo cáo nghỉ phép                                               │
│  [Tab: Chi tiết NV] [Tab: Theo phòng ban] [Tab: Tồn phép]        │
├──────────────────────────────────────────────────────────────────┤
│  Năm: [2026 ▼]  Phòng ban: [Tất cả ▼]  Loại phép: [Tất cả ▼]   │
│  [Xuất Excel]                                                     │
├──────────────────────────────────────────────────────────────────┤
│  ... DataTable tương ứng từng tab ...                            │
└──────────────────────────────────────────────────────────────────┘
```

**Tab A (Chi tiết NV):**
| Nhân viên | Phòng ban | Loại phép | Cấp | Chuyển dư | Đã dùng | Còn lại | Số lần |
|---|---|---|---|---|---|---|---|

**Tab B (Theo phòng ban):**
| Phòng ban | Loại phép | Số NV | Số lần | Tổng ngày | TB/NV |
|---|---|---|---|---|---|

Thêm filter `Tháng từ` / `Tháng đến` (Select 1–12).

**Tab C (Tồn phép):**
| Nhân viên | Phòng ban | Loại phép | Cấp | Chuyển dư | Đã dùng | Còn lại | Sẽ chuyển |
|---|---|---|---|---|---|---|---|

**Xuất Excel:** Button gọi endpoint `/leave-reports/export` → tải file.

**Màu sắc `remaining_days`:** Dùng lại `.days-badge .ok/.warning/.expired` đã có trong `main.scss`.

---

## Cấu trúc file mới / thay đổi

```
backend/
  app/schemas/leave_report.py           (NEW)
  app/services/leave_report_service.py  (NEW)
  app/api/v1/endpoints/leave_reports.py (NEW)
  app/api/v1/router.py                  (UPDATE — đăng ký /leave-reports)
  tests/test_leave_reports.py           (NEW)

frontend/
  src/services/leaveReportService.ts    (NEW)
  src/views/leaves/LeaveReportView.vue  (NEW)
  src/router/index.ts                   (UPDATE — thêm /leave-reports)
  src/components/layout/AppMenu.vue     (UPDATE — thêm vào nhóm Nghỉ phép)
```

---

## Tests — `test_leave_reports.py`

```
# ── Báo cáo A ──────────────────────────────────────────────────────
test_employee_summary_returns_data
  → Tạo entitlement + record → GET employee-summary?year=X
  → Trả về 1 row với used_days, remaining_days, record_count đúng

test_employee_summary_filter_by_employee
  → GET ?year=X&employee_id=Y → chỉ trả về row của employee Y

test_employee_summary_filter_by_leave_type
  → GET ?year=X&leave_type_id=Z → chỉ trả về row có leave_type đó

# ── Báo cáo B ──────────────────────────────────────────────────────
test_department_summary_aggregates_correctly
  → Tạo 2 record cùng phòng → total_days = sum đúng

test_department_summary_filter_by_month
  → Record tháng 6, filter month_from=7 → không xuất hiện
  → Filter month_from=6 → xuất hiện

# ── Báo cáo C ──────────────────────────────────────────────────────
test_year_end_only_carryover_types
  → Chỉ xuất loại phép có carryover_allowed=True

test_year_end_will_carry_is_max_zero
  → remaining_days < 0 → will_carry = 0

# ── Export ──────────────────────────────────────────────────────────
test_export_returns_xlsx_content_type
  → GET /export?report_type=A&year=X
  → status 200, Content-Type = application/vnd.openxmlformats...

test_export_type_b
  → GET /export?report_type=B&year=X → 200, file xlsx hợp lệ

# ── RBAC ───────────────────────────────────────────────────────────
test_unauthenticated_rejected
```

---

## Thứ tự triển khai

### Bước 1 — Schema `app/schemas/leave_report.py`
3 response schemas: `EmployeeSummaryReport`, `DepartmentSummaryReport`, `YearEndReport`.

### Bước 2 — Service `app/services/leave_report_service.py`
- `get_employee_summary(session, year, ...)` → query + build rows
- `get_department_summary(session, year, ...)` → GROUP BY dept + leave_type
- `get_year_end(session, year, ...)` → filter carryover_allowed=True
- `build_xlsx(title, headers, rows)` → `BytesIO`
- `export_excel(session, report_type, year, ...)` → gọi service + wrap vào StreamingResponse

### Bước 3 — API `app/api/v1/endpoints/leave_reports.py`
4 endpoints. Tất cả GET, không có commit. Đăng ký trong `router.py`.

### Bước 4 — Tests `tests/test_leave_reports.py`
10 test cases. Chạy pytest pass.

### Bước 5 — Frontend
`src/services/leaveReportService.ts` → wrapper gọi API + download Excel.  
`src/views/leaves/LeaveReportView.vue` → 3 tabs + toolbar + DataTable.  
`router.ts` + `AppMenu.vue` → thêm route `/leave-reports`.

### Bước 6 — Verify
1. API trả đúng số liệu (cross-check với dữ liệu thủ công)
2. Export Excel mở được, số liệu khớp
3. Frontend hiển thị đúng 3 tab, filter hoạt động
4. pytest pass toàn bộ

---

## Rủi ro & Cách xử lý

| Rủi ro | Cách xử lý |
|---|---|
| Nhân viên không có `employee_job_records.is_current` | LEFT JOIN → `department_name = null` → hiển thị "—" |
| `leave_records` có `entitlement_id = null` (không có phân bổ) | Vẫn tính vào báo cáo B; không xuất hiện trong báo cáo A và C (join entitlements) |
| `remaining_days` âm (vượt phép) | Hiển thị với màu đỏ (`.days-badge.expired`), `will_carry = 0` |
| Export file lớn (>1000 nhân viên) | Streaming response — openpyxl write trực tiếp vào BytesIO, không buffering toàn DB |
| `month_from > month_to` | Validate ở API level → 422 |

---

## Liên kết

**5.3 → 5.4:** `leave_records.total_days` và `leave_entitlements.used_days` là nguồn số liệu.  
**5.4 → Báo cáo tổng hợp (module 10):** Báo cáo tổng hợp toàn công ty sẽ tái dùng service này.
