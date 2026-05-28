# Kế hoạch triển khai — 11.5. Báo cáo Hợp đồng

**Phạm vi:** Hợp đồng sắp hết hạn · Thống kê theo loại · Lịch sử hợp đồng · Analytics  
**Phụ thuộc:** Plan 4.x (contract management đã hoàn thành ✅)  
**Căn cứ:** FEATURES.md §11.5  
**Module chỉ đọc** — không có write operation nào

---

## Trạng thái hiện tại

| Thành phần | Trạng thái | Ghi chú |
|---|---|---|
| Model `EmployeeContract` | ✅ Đã có | `employee_contracts`, index `(effective_to, status)` |
| Model `ContractCategory` | ✅ Đã có | `contract_categories`, 5 seed records |
| Model `Employee` | ✅ Đã có | `employees` |
| Model `EmployeeJobRecord` | ✅ Đã có | `employee_job_records`, field `department_id`, `is_current` |
| Model `Department` | ✅ Đã có | `departments` |
| API `/contracts` (global list) | ✅ Đã có | Plan 4.1 |
| Service `contract_report_service.py` | ❌ Chưa có | **Cần tạo** |
| Schema `contract_report.py` | ❌ Chưa có | **Cần tạo** |
| Endpoint `contract_reports.py` | ❌ Chưa có | **Cần tạo** |
| Export `contract_export_service.py` | ❌ Chưa có | **Cần tạo** |
| Frontend `ContractReportView.vue` | ❌ Chưa có | **Cần tạo** |
| Service `contractReportService.ts` | ❌ Chưa có | **Cần tạo** |
| Route `/reports/contracts` | ❌ Chưa đăng ký | **Cần thêm vào router** |

---

## Phạm vi

### Trong phạm vi
- Dashboard KPI cards: tổng active, sắp hết hạn 0–30 ngày, 31–60 ngày, 61–90 ngày, đã hết hạn
- Danh sách hợp đồng sắp hết hạn: filter ngày còn lại, phòng ban, tìm theo tên nhân viên
- Urgency tier: CRITICAL (≤7 ngày), WARNING (≤30 ngày), NOTICE (≤90 ngày)
- Thống kê breakdown theo loại hợp đồng (probation / fixed_term_1 / fixed_term_3 / indefinite)
- Tỷ lệ gia hạn hợp đồng (số đã gia hạn / tổng hết hạn × 100%)
- Biểu đồ dự báo hết hạn theo tháng (12 tháng tới)
- Lịch sử toàn bộ hợp đồng của một nhân viên
- Export Excel toàn bộ danh sách
- Mobile responsive

### Ngoài phạm vi
- Tự động gia hạn hợp đồng
- Ký số điện tử, workflow phê duyệt
- Gửi email nhắc nhở (thuộc Plan 4.3 / 12.3)

---

## Data Model — Mapping trường thực tế

```
EmployeeContract
├── id, employee_id, contract_number
├── contract_category_id  → ContractCategory.id
├── document_kind         (labor_contract | contract_appendix)
├── effective_from, effective_to (NULL = vô thời hạn)
├── signed_date, insurance_salary
├── status                (active | expired | terminated | draft)
└── parent_contract_id    (NULL = HĐ gốc, có giá trị = phụ lục)

ContractCategory
├── id, code, name
├── document_kind         (labor_contract | contract_appendix)
├── legal_contract_type   (indefinite_term | definite_term | NULL)
└── business_group        (standard | probation | salary_change | job_change)

EmployeeJobRecord
├── employee_id, department_id
└── is_current            (partial unique index per employee)

Mapping business_group → contract_type hiển thị:
  probation       → "Thử việc"
  standard +  legal_contract_type=indefinite_term → "Không xác định thời hạn"
  standard + legal_contract_type=definite_term + effective_to - effective_from ≈ 1 năm → "XĐ 1 năm"
  standard + legal_contract_type=definite_term + effective_to - effective_from ≈ 3 năm → "XĐ 3 năm"
```

> **Lưu ý quan trọng:** Không có field `contract_type` trực tiếp trong `EmployeeContract`. Phân loại lấy từ `ContractCategory.business_group` và `ContractCategory.legal_contract_type` qua JOIN `contract_category_id`.

---

## Chỉ số chính + SQL Queries

### 1. KPI Summary

```sql
-- Tổng active (chỉ HĐ gốc, không phụ lục)
SELECT COUNT(*) FROM employee_contracts ec
JOIN employees e ON e.id = ec.employee_id
WHERE ec.status = 'active'
  AND ec.document_kind = 'labor_contract'
  AND ec.parent_contract_id IS NULL
  AND e.is_active = TRUE;

-- Sắp hết hạn theo tier (ví dụ 0-30 ngày)
WHERE ec.status = 'active'
  AND ec.effective_to IS NOT NULL
  AND ec.effective_to >= CURRENT_DATE
  AND ec.effective_to <= CURRENT_DATE + INTERVAL '30 days';

-- Đã hết hạn (effective_to < today, status vẫn active do chưa cập nhật)
WHERE ec.status IN ('active', 'expired')
  AND ec.effective_to IS NOT NULL
  AND ec.effective_to < CURRENT_DATE;
```

### 2. Breakdown theo loại

```sql
SELECT
  cc.business_group,
  cc.legal_contract_type,
  cc.name AS category_name,
  COUNT(ec.id) AS total,
  COUNT(ec.id) FILTER (WHERE ec.status = 'active') AS active_count
FROM employee_contracts ec
JOIN contract_categories cc ON cc.id = ec.contract_category_id
WHERE ec.document_kind = 'labor_contract'
  AND ec.parent_contract_id IS NULL
GROUP BY cc.id, cc.business_group, cc.legal_contract_type, cc.name;
```

### 3. Tỷ lệ gia hạn

```python
# Gia hạn = HĐ đã hết hạn (status expired | effective_to < today)
# nhưng nhân viên có HĐ active khác tạo SAU đó (parent_contract_id IS NULL)
renewal_rate = (
    SELECT COUNT(DISTINCT e2.employee_id)
    FROM employee_contracts e1
    JOIN employee_contracts e2 ON e2.employee_id = e1.employee_id
    WHERE e1.effective_to < CURRENT_DATE
      AND e2.status = 'active'
      AND e2.effective_from >= e1.effective_to
) / NULLIF(expired_total, 0) * 100
```

### 4. Dự báo hết hạn 12 tháng

```sql
SELECT
  DATE_TRUNC('month', ec.effective_to) AS month,
  COUNT(*) AS expiring_count
FROM employee_contracts ec
JOIN employees e ON e.id = ec.employee_id
WHERE ec.status = 'active'
  AND ec.document_kind = 'labor_contract'
  AND ec.effective_to >= CURRENT_DATE
  AND ec.effective_to < CURRENT_DATE + INTERVAL '12 months'
  AND e.is_active = TRUE
GROUP BY DATE_TRUNC('month', ec.effective_to)
ORDER BY month;
```

---

## API Design

### Endpoints

| Method | Path | Mô tả | Response |
|---|---|---|---|
| GET | `/api/v1/reports/contracts/summary` | KPI dashboard | `ContractSummaryOut` |
| GET | `/api/v1/reports/contracts/expiring` | Danh sách sắp hết hạn (paginated) | `ContractExpiringPage` |
| GET | `/api/v1/reports/contracts/by-type` | Breakdown theo loại | `ContractByTypeOut` |
| GET | `/api/v1/reports/contracts/expiry-forecast` | Dự báo 12 tháng | `ContractForecastOut` |
| GET | `/api/v1/reports/contracts/history` | Lịch sử HĐ nhân viên | `ContractHistoryOut` |
| GET | `/api/v1/reports/contracts/export` | Xuất Excel | `StreamingResponse` |

### Query Parameters chi tiết

```
GET /summary?department_id=<int>

GET /expiring
  ?days_ahead=90          # default 90, choices: 30|60|90
  &department_id=<int>
  &keyword=<str>
  &page=1
  &page_size=50

GET /by-type
  ?department_id=<int>
  &year=<int>             # lọc theo năm ký HĐ, optional

GET /expiry-forecast
  ?months_ahead=12        # default 12, max 24

GET /history
  ?employee_id=<int>      # required

GET /export
  ?department_id=<int>
  &status=active|expired|all   # default: active
  &days_ahead=<int>            # nếu muốn chỉ export sắp hết hạn
```

**Permission:** `employees:read` cho tất cả endpoints.

**Router prefix:** `/api/v1/reports/contracts` — đăng ký trong `backend/app/api/v1/router.py`.

---

## Schemas (Pydantic v2)

```python
# backend/app/schemas/contract_report.py

from __future__ import annotations
from datetime import date
from typing import Optional, Literal
from pydantic import BaseModel, computed_field


# ── KPI Summary ───────────────────────────────────────────────────────────────

class ContractSummaryOut(BaseModel):
    total_active: int
    expiring_0_30: int      # 0–30 ngày
    expiring_31_60: int     # 31–60 ngày
    expiring_61_90: int     # 61–90 ngày
    already_expired: int    # effective_to < today, status active/expired
    renewal_rate: float     # phần trăm, làm tròn 1 chữ số thập phân
    as_of_date: date


# ── Danh sách sắp hết hạn ─────────────────────────────────────────────────────

UrgencyTier = Literal["CRITICAL", "WARNING", "NOTICE"]

class ContractExpiringRow(BaseModel):
    contract_id: int
    contract_number: str
    employee_id: int
    employee_code: str
    employee_name: str
    department_id: Optional[int]
    department_name: Optional[str]
    category_name: str           # tên loại HĐ từ ContractCategory.name
    business_group: str          # probation | standard | ...
    effective_from: date
    effective_to: date
    days_remaining: int
    urgency: UrgencyTier
    signed_date: date
    insurance_salary: Optional[float]

class ContractExpiringPage(BaseModel):
    items: list[ContractExpiringRow]
    total: int
    page: int
    page_size: int
    days_ahead: int


# ── Breakdown theo loại ────────────────────────────────────────────────────────

class ContractTypeBreakdown(BaseModel):
    category_id: int
    category_name: str
    business_group: str
    legal_contract_type: Optional[str]
    total: int
    active: int
    expired: int
    terminated: int
    percentage: float            # % trên tổng HĐ gốc


class ContractByTypeOut(BaseModel):
    items: list[ContractTypeBreakdown]
    total_contracts: int         # tổng HĐ gốc (không phụ lục)
    department_id: Optional[int]
    year: Optional[int]


# ── Dự báo hết hạn ────────────────────────────────────────────────────────────

class ForecastMonthItem(BaseModel):
    year_month: str              # "2025-06"
    expiring_count: int

class ContractForecastOut(BaseModel):
    months: list[ForecastMonthItem]
    months_ahead: int
    total_expiring: int


# ── Lịch sử nhân viên ─────────────────────────────────────────────────────────

class ContractHistoryItem(BaseModel):
    contract_id: int
    contract_number: str
    category_name: str
    document_kind: str           # labor_contract | contract_appendix
    is_appendix: bool            # parent_contract_id IS NOT NULL
    parent_contract_id: Optional[int]
    effective_from: date
    effective_to: Optional[date]
    signed_date: date
    status: str
    insurance_salary: Optional[float]
    file_name: Optional[str]

class ContractHistoryOut(BaseModel):
    employee_id: int
    employee_code: str
    employee_name: str
    items: list[ContractHistoryItem]
    total: int
```

---

## Service Logic — `contract_report_service.py`

### File: `backend/app/services/contract_report_service.py`

**Urgency tier logic:**
```python
def _urgency(days_remaining: int) -> str:
    if days_remaining <= 7:
        return "CRITICAL"
    elif days_remaining <= 30:
        return "WARNING"
    else:
        return "NOTICE"
```

**Hàm `get_summary`:**
```python
async def get_summary(session, *, department_id=None) -> ContractSummaryOut:
    today = date.today()
    # Base join: employee_contracts + employees + employee_job_records (is_current)
    # Filter: document_kind='labor_contract', parent_contract_id IS NULL, e.is_active=True
    # Tính từng bucket bằng func.count + filter clause (SQLAlchemy)
    # renewal_rate: subquery đếm nhân viên có HĐ mới sau khi HĐ cũ hết hạn
```

**Hàm `get_expiring`:**
```python
async def get_expiring(session, *, days_ahead=90, department_id=None,
                       keyword=None, page=1, page_size=50) -> ContractExpiringPage:
    today = date.today()
    deadline = today + timedelta(days=days_ahead)
    # WHERE status='active', effective_to >= today, effective_to <= deadline
    # JOIN Department qua EmployeeJobRecord.is_current=True
    # days_remaining = (effective_to - today).days
    # urgency = _urgency(days_remaining)
    # ORDER BY effective_to ASC (sắp hết hạn nhất lên đầu)
    # Server-side pagination
```

**Hàm `get_by_type`:**
```python
async def get_by_type(session, *, department_id=None, year=None) -> ContractByTypeOut:
    # GROUP BY contract_category_id
    # JOIN ContractCategory để lấy name, business_group, legal_contract_type
    # COUNT FILTER per status
    # percentage = count / total * 100
```

**Hàm `get_expiry_forecast`:**
```python
async def get_expiry_forecast(session, *, months_ahead=12) -> ContractForecastOut:
    today = date.today()
    end_date = today + relativedelta(months=months_ahead)
    # GROUP BY func.date_trunc('month', EmployeeContract.effective_to)
    # WHERE effective_to >= today AND effective_to < end_date
    # Đảm bảo fill tháng trống với count=0 (Python-side)
    # year_month format: strftime('%Y-%m')
```

**Hàm `get_history`:**
```python
async def get_history(session, *, employee_id: int) -> ContractHistoryOut:
    # SELECT tất cả contracts của employee (kể cả phụ lục)
    # JOIN ContractCategory để lấy category_name
    # ORDER BY effective_from DESC
    # is_appendix = parent_contract_id IS NOT NULL
```

---

## Export Excel — `contract_export_service.py`

### File: `backend/app/services/contract_export_service.py`

**Sheet layout:**
```
Sheet "Hợp đồng"
Columns:
  STT | Mã NV | Họ tên | Phòng ban | Loại HĐ | Số HĐ |
  Ngày ký | Hiệu lực từ | Hiệu lực đến | Còn lại (ngày) |
  Mức lương BHXH | Trạng thái
```

**Formatting với openpyxl:**
- Header row: bold, fill màu xanh đậm `#1E3A5F`, font trắng
- Row CRITICAL (≤7 ngày): fill đỏ nhạt `#FFCCCC`
- Row WARNING (≤30 ngày): fill cam nhạt `#FFE5CC`
- Row NOTICE (≤90 ngày): fill vàng nhạt `#FFFFCC`
- `effective_to = None` → hiển thị "Vô thời hạn"
- `days_remaining` → để trống nếu `effective_to` là NULL
- `insurance_salary` → format số, căn phải
- Auto-width cột (tính `max(len(str(v)))` per column)
- Freeze row đầu tiên

```python
from io import BytesIO
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment

async def export_contracts_xlsx(session, *, department_id=None,
                                 status="active", days_ahead=None) -> BytesIO:
    # Query dữ liệu (tái dùng logic từ get_expiring nếu days_ahead,
    #                 hoặc full list nếu không)
    # Build workbook
    # Return BytesIO
```

---

## Frontend Design

### Route

```
/reports/contracts
name: "contract-reports"
component: ContractReportView.vue
meta: { title: "Báo cáo Hợp đồng" }
```

Thêm vào `/reports` section trong `frontend/src/router/index.ts` sau route `reports`.

### Cấu trúc `ContractReportView.vue`

```
ContractReportView.vue
├── Page header: "Báo cáo Hợp đồng" + subtitle
├── Toolbar: Select phòng ban + Button "Xuất Excel"
│
├── Section 1: KPI Cards (5 cards, 1 hàng desktop / 2×3 mobile)
│   ├── Card: Tổng HĐ active          → màu xanh (primary)
│   ├── Card: Hết hạn < 30 ngày       → màu đỏ
│   ├── Card: Hết hạn 31–60 ngày      → màu cam
│   ├── Card: Hết hạn 61–90 ngày      → màu vàng
│   └── Card: Đã hết hạn              → màu xám
│
├── Section 2: DataTable sắp hết hạn
│   ├── Toolbar con: days_ahead (30|60|90), keyword search
│   ├── Columns: STT, Mã NV, Họ tên, Phòng ban, Loại HĐ,
│   │            Số HĐ, Ngày hiệu lực đến, Còn lại (ngày), Urgency badge
│   ├── Sort mặc định: effective_to ASC
│   └── Server-side pagination (Paginator)
│
├── Section 3: Charts (2 cột desktop, 1 cột mobile)
│   ├── Donut chart: Breakdown theo loại HĐ (Chart.js qua PrimeVue)
│   └── Bar chart: Dự báo hết hạn 12 tháng tới
│
└── Section 4: Lịch sử hợp đồng nhân viên
    ├── Select nhân viên (autocomplete)
    └── DataTable lịch sử (HĐ + phụ lục)
```

### Color coding KPI cards

| Card | CSS class / màu |
|---|---|
| Tổng active | `bg-blue-50 border-blue-400` |
| < 30 ngày | `bg-red-50 border-red-400` |
| 31–60 ngày | `bg-orange-50 border-orange-400` |
| 61–90 ngày | `bg-yellow-50 border-yellow-400` |
| Đã hết hạn | `bg-gray-50 border-gray-400` |

### Urgency Badge

```html
<!-- Dùng PrimeVue Tag component -->
<Tag
  :value="row.urgency"
  :severity="urgencyToSeverity(row.urgency)"
/>
<!-- CRITICAL → danger, WARNING → warn, NOTICE → info -->
```

### `contractReportService.ts`

```typescript
// frontend/src/services/contractReportService.ts

export interface ContractSummaryOut {
  total_active: number
  expiring_0_30: number
  expiring_31_60: number
  expiring_61_90: number
  already_expired: number
  renewal_rate: number
  as_of_date: string
}

export interface ContractExpiringRow {
  contract_id: number
  contract_number: string
  employee_id: number
  employee_code: string
  employee_name: string
  department_id: number | null
  department_name: string | null
  category_name: string
  business_group: string
  effective_from: string
  effective_to: string
  days_remaining: number
  urgency: 'CRITICAL' | 'WARNING' | 'NOTICE'
  signed_date: string
  insurance_salary: number | null
}

export interface ContractExpiringPage {
  items: ContractExpiringRow[]
  total: number
  page: number
  page_size: number
  days_ahead: number
}

export interface ContractTypeBreakdown {
  category_id: number
  category_name: string
  business_group: string
  legal_contract_type: string | null
  total: number
  active: number
  expired: number
  terminated: number
  percentage: number
}

export interface ContractByTypeOut {
  items: ContractTypeBreakdown[]
  total_contracts: number
  department_id: number | null
  year: number | null
}

export interface ForecastMonthItem {
  year_month: string
  expiring_count: number
}

export interface ContractForecastOut {
  months: ForecastMonthItem[]
  months_ahead: number
  total_expiring: number
}

export interface ContractHistoryItem {
  contract_id: number
  contract_number: string
  category_name: string
  document_kind: string
  is_appendix: boolean
  parent_contract_id: number | null
  effective_from: string
  effective_to: string | null
  signed_date: string
  status: string
  insurance_salary: number | null
  file_name: string | null
}

export interface ContractHistoryOut {
  employee_id: number
  employee_code: string
  employee_name: string
  items: ContractHistoryItem[]
  total: number
}

const BASE = '/api/v1/reports/contracts'

export const contractReportService = {
  getSummary: (params: { department_id?: number }) =>
    api.get<ContractSummaryOut>(`${BASE}/summary`, { params }),

  getExpiring: (params: {
    days_ahead?: number
    department_id?: number
    keyword?: string
    page?: number
    page_size?: number
  }) => api.get<ContractExpiringPage>(`${BASE}/expiring`, { params }),

  getByType: (params: { department_id?: number; year?: number }) =>
    api.get<ContractByTypeOut>(`${BASE}/by-type`, { params }),

  getForecast: (params: { months_ahead?: number }) =>
    api.get<ContractForecastOut>(`${BASE}/expiry-forecast`, { params }),

  getHistory: (employee_id: number) =>
    api.get<ContractHistoryOut>(`${BASE}/history`, { params: { employee_id } }),

  exportXlsx: (params: { department_id?: number; status?: string; days_ahead?: number }) =>
    api.get(`${BASE}/export`, { params, responseType: 'blob' }),
}
```

### Mobile responsive

- KPI cards: grid 2 cột trên mobile (`grid-cols-2`), 5 cột trên desktop
- DataTable: `overflow-x-auto` + horizontal scroll
- Charts: stacked (1 cột) trên màn hình < 768px
- Lịch sử: ẩn bớt cột ít quan trọng trên mobile (`hidden md:table-cell`)

---

## Cấu trúc file

```
backend/app/
├── schemas/
│   └── contract_report.py              # Pydantic schemas (mới)
├── services/
│   ├── contract_report_service.py      # Business logic (mới)
│   └── contract_export_service.py      # openpyxl export (mới)
└── api/v1/endpoints/
    └── contract_reports.py             # FastAPI router (mới)

frontend/src/
├── services/
│   └── contractReportService.ts        # API client + types (mới)
└── views/contracts/
    └── ContractReportView.vue          # Main view (mới)

Đăng ký:
  backend/app/api/v1/router.py          # include_router contract_reports
  frontend/src/router/index.ts          # thêm route /reports/contracts
```

---

## Kế hoạch theo Slice

### Slice 1 — Backend Core (KPI + Expiring list)

**Mục tiêu:** API sẵn sàng, test pass, có thể gọi từ curl/Postman.

**Tasks:**
1. Tạo `backend/app/schemas/contract_report.py` — `ContractSummaryOut`, `ContractExpiringRow`, `ContractExpiringPage`
2. Tạo `backend/app/services/contract_report_service.py` — `get_summary`, `get_expiring`
3. Tạo `backend/app/api/v1/endpoints/contract_reports.py` — `GET /summary`, `GET /expiring`
4. Đăng ký router trong `backend/app/api/v1/router.py`
5. Viết pytest: `tests/api/v1/test_contract_reports.py`
   - Test `GET /summary` trả đúng bucket count
   - Test `GET /expiring?days_ahead=30` trả đúng danh sách, urgency tier
   - Test filter `department_id`
   - Test pagination

**Verify:** `pytest tests/api/v1/test_contract_reports.py -v` — all green.

---

### Slice 2 — Backend Analytics + Export

**Mục tiêu:** Đầy đủ analytics API + file xlsx tải được.

**Tasks:**
1. Bổ sung schemas: `ContractByTypeOut`, `ContractForecastOut`, `ContractHistoryOut`
2. Bổ sung service functions: `get_by_type`, `get_expiry_forecast`, `get_history`
3. Tạo `backend/app/services/contract_export_service.py` — openpyxl, color coding urgency
4. Bổ sung endpoints: `GET /by-type`, `GET /expiry-forecast`, `GET /history`, `GET /export`
5. Bổ sung pytest:
   - Test `GET /by-type` — đủ 5 category seed, sum = total
   - Test `GET /expiry-forecast` — 12 tháng tới, tháng trống có count=0
   - Test `GET /history?employee_id=X` — đúng thứ tự, có phụ lục
   - Test `GET /export` — response Content-Type xlsx, không raise exception

**Verify:** `pytest tests/api/v1/test_contract_reports.py -v` — all green.

---

### Slice 3 — Frontend

**Mục tiêu:** Giao diện hoàn chỉnh, mobile responsive, export hoạt động.

**Tasks:**
1. Tạo `frontend/src/services/contractReportService.ts` — interfaces + API calls
2. Tạo `frontend/src/views/contracts/ContractReportView.vue`:
   - Section 1: 5 KPI cards với color coding
   - Section 2: DataTable sắp hết hạn + filter + pagination + urgency badge
   - Section 3: Donut chart (by-type) + Bar chart (forecast) dùng PrimeVue Chart
   - Section 4: Select nhân viên + DataTable lịch sử
3. Đăng ký route trong `frontend/src/router/index.ts`
4. Thêm link vào navigation sidebar (nếu có mục Hợp đồng/Báo cáo)
5. Verify: `vue-tsc --noEmit` — no TypeScript errors

**Checklist trước khi báo xong:**
- [ ] `vue-tsc --noEmit` pass
- [ ] Mobile layout test (Chrome DevTools 375px)
- [ ] Export xlsx tải về mở được trong Excel
- [ ] Urgency badge đúng màu
- [ ] Pagination server-side hoạt động

---

## Rủi ro

| Rủi ro | Xác suất | Ảnh hưởng | Xử lý |
|---|---|---|---|
| `effective_to = NULL` (vô thời hạn) bị tính nhầm vào expiring list | Cao | Cao | WHERE `effective_to IS NOT NULL` ở tất cả expiring queries |
| Nhân viên không active vẫn có HĐ active trong DB | Trung bình | Trung bình | JOIN `employees.is_active = TRUE` trong summary |
| Phụ lục HĐ bị đếm nhầm vào thống kê chính | Cao | Cao | WHERE `parent_contract_id IS NULL` ở tất cả KPI queries |
| `contract_type` không có field trực tiếp → cần JOIN `ContractCategory` | Cao | Thấp | Đã xác nhận, luôn JOIN `contract_categories` qua `contract_category_id` |
| Tháng forecast bị bỏ sót khi không có HĐ nào hết hạn | Trung bình | Thấp | Fill Python-side: tạo dict 12 tháng → merge kết quả DB |
| Dữ liệu lớn → export Excel chậm | Thấp | Trung bình | Thêm `LIMIT` warning nếu > 5000 rows; dùng streaming response |
| `days_remaining` âm nếu `effective_to` < today lọt vào | Thấp | Thấp | WHERE `effective_to >= today` trong expiring query |
