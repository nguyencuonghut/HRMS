# Kế hoạch triển khai — 11.4. Báo cáo Bảo hiểm (People Analytics)

**Phạm vi:** Tăng/giảm BHXH hàng tháng · Tổng quỹ lương BHXH · Danh sách tham gia/không tham gia · Analytics dashboard  
**Phụ thuộc:** Plan 6.x đã hoàn thành (foundation BHXH: `insurance_change_events`, `insurance_period_reports`, `employee_insurance_profiles`)  
**Căn cứ:** FEATURES.md §11.4  
**Mở rộng trên nền:** 6.4 (báo cáo biến động kỳ + approval workflow)

---

## Trạng thái hiện tại

| Thành phần | Trạng thái | Ghi chú |
|---|---|---|
| `employee_insurance_profiles` | Có — model đầy đủ | `participation_status`, `insurance_basis_amount`, `company_bhxh_joined_date`, `status_effective_from` |
| `insurance_change_events` | Có — model đầy đủ | `change_type`, `effective_date`, `basis_amount`, `employee_id` |
| `insurance_period_reports` + `insurance_report_line_items` | Có — model + service + API | Plan 6.4 hoàn chỉnh |
| `insurance_report_service.py` | Có | CRUD + workflow duyệt + auto-populate |
| Frontend `/insurance/reports` | Có | Danh sách báo cáo + chi tiết + duyệt |
| **Analytics dashboard** | **Chưa có** | Mục tiêu Plan 11.4 |
| **Endpoint `/api/v1/reports/insurance/*`** | **Chưa có** | Prefix riêng `reports/insurance`, khác `/insurance/reports` của 6.4 |
| **`insurance_analytics_service.py`** | **Chưa có** | Service mới trong 11.4 |
| **`InsuranceAnalyticsView.vue`** | **Chưa có** | View analytics mới |

---

## Phạm vi

### Đã có (Plan 6.4) — không duplicate
- Báo cáo biến động kỳ (tháng), approval workflow draft → approved
- Export D02-TS Excel (mẫu VNPT) từ báo cáo đã duyệt
- CRUD line items, điều chỉnh `declared_month`
- Frontend `/insurance/reports` và `/insurance/reports/:id`

### Mở rộng trong 11.4 — People Analytics
- **Dashboard KPI tổng quan:** số đang tham gia BHXH, tổng quỹ lương, tỷ lệ tham gia, số tăng/giảm trong tháng
- **Biểu đồ xu hướng tăng/giảm** theo 12 tháng (stacked bar chart)
- **Biểu đồ quỹ lương BHXH** theo tháng trong năm (line chart)
- **Breakdown theo phòng ban:** số tham gia, quỹ lương, tỷ lệ từng phòng
- **Danh sách không tham gia BHXH** (cảnh báo vi phạm tiềm năng)
- **Lịch sử biến động cá nhân:** tra cứu từng nhân viên qua thời gian
- **Export Excel tổng hợp analytics** (khác D02-TS: dạng báo cáo quản lý)
- **Mobile responsive** (cards 2×2 grid, charts full-width)

---

## Chỉ số chính và SQL tham chiếu

### KPI Cards

```sql
-- 1. Tổng số đang tham gia BHXH
SELECT COUNT(*)
FROM employee_insurance_profiles eip
JOIN employees e ON e.id = eip.employee_id
WHERE eip.participation_status = 'active'
  AND e.is_active = TRUE;

-- 2. Tổng quỹ lương BHXH (chỉ nhân viên active)
SELECT SUM(eip.insurance_basis_amount)
FROM employee_insurance_profiles eip
JOIN employees e ON e.id = eip.employee_id
WHERE eip.participation_status = 'active'
  AND e.is_active = TRUE
  AND eip.insurance_basis_amount IS NOT NULL;

-- 3. Số tăng trong tháng (join events)
SELECT COUNT(*)
FROM insurance_change_events ice
WHERE ice.change_type = 'increase'
  AND EXTRACT(YEAR  FROM ice.effective_date) = :year
  AND EXTRACT(MONTH FROM ice.effective_date) = :month;

-- 4. Số giảm trong tháng (leave events)
SELECT COUNT(*)
FROM insurance_change_events ice
WHERE ice.change_type = 'decrease'
  AND EXTRACT(YEAR  FROM ice.effective_date) = :year
  AND EXTRACT(MONTH FROM ice.effective_date) = :month;

-- 5. Tỷ lệ tham gia = active_insured / total_active_employees × 100
SELECT
  COUNT(*) FILTER (WHERE eip.participation_status = 'active') AS participating,
  COUNT(*) AS total_active
FROM employees e
LEFT JOIN employee_insurance_profiles eip ON eip.employee_id = e.id
WHERE e.is_active = TRUE;
```

### Tăng/giảm 12 tháng

```sql
SELECT
  EXTRACT(MONTH FROM ice.effective_date)::INT AS month,
  SUM(CASE WHEN ice.change_type = 'increase' THEN 1 ELSE 0 END) AS increased,
  SUM(CASE WHEN ice.change_type = 'decrease' THEN 1 ELSE 0 END) AS decreased
FROM insurance_change_events ice
WHERE EXTRACT(YEAR FROM ice.effective_date) = :year
GROUP BY EXTRACT(MONTH FROM ice.effective_date)
ORDER BY month;
```

### Quỹ lương theo tháng (từ events tăng/giảm lũy kế)

```sql
-- Snapshot cuối mỗi tháng: SUM basis_amount của tất cả nhân viên đang active tại điểm đó
-- Dùng insurance_change_events để reconstruct, hoặc query trực tiếp eip theo tháng filter
SELECT
  EXTRACT(MONTH FROM ice.effective_date)::INT AS month,
  SUM(ice.basis_amount) FILTER (WHERE ice.change_type = 'increase') AS added_amount,
  SUM(ice.basis_amount) FILTER (WHERE ice.change_type = 'decrease') AS removed_amount
FROM insurance_change_events ice
WHERE EXTRACT(YEAR FROM ice.effective_date) = :year
GROUP BY EXTRACT(MONTH FROM ice.effective_date)
ORDER BY month;
```

### Breakdown theo phòng ban

```sql
SELECT
  d.id                                          AS department_id,
  d.name                                        AS department_name,
  COUNT(*) FILTER (WHERE eip.participation_status = 'active') AS participating_count,
  COUNT(*)                                      AS total_count,
  SUM(eip.insurance_basis_amount)
    FILTER (WHERE eip.participation_status = 'active') AS total_basis_amount,
  ROUND(
    COUNT(*) FILTER (WHERE eip.participation_status = 'active')
    * 100.0 / NULLIF(COUNT(*), 0), 2
  ) AS participation_rate
FROM employees e
JOIN employee_job_records ejr
  ON ejr.employee_id = e.id AND ejr.is_current = TRUE
JOIN departments d ON d.id = ejr.department_id
LEFT JOIN employee_insurance_profiles eip ON eip.employee_id = e.id
WHERE e.is_active = TRUE
  AND (:department_id IS NULL OR d.id = :department_id)
GROUP BY d.id, d.name
ORDER BY d.name;
```

### Danh sách không tham gia BHXH

```sql
SELECT
  e.id                  AS employee_id,
  e.full_name,
  d.name                AS department_name,
  eip.participation_status,
  eip.status_effective_from,
  eip.status_note,
  eip.company_bhxh_joined_date
FROM employees e
JOIN employee_job_records ejr
  ON ejr.employee_id = e.id AND ejr.is_current = TRUE
JOIN departments d ON d.id = ejr.department_id
LEFT JOIN employee_insurance_profiles eip ON eip.employee_id = e.id
WHERE e.is_active = TRUE
  AND (eip.participation_status != 'active' OR eip.id IS NULL)
  AND (:department_id IS NULL OR d.id = :department_id)
ORDER BY d.name, e.full_name;
```

---

## API Design — Endpoints mới (prefix `/api/v1/reports/insurance`)

> Tách biệt với `/api/v1/insurance/reports` của Plan 6.4 (approval workflow).  
> Module analytics đặt dưới prefix `reports/` để thống nhất với `reports/probation` và `leave-reports`.

```
GET /api/v1/reports/insurance/dashboard
    ?year=&month=&department_id=
    → InsuranceDashboardResponse

GET /api/v1/reports/insurance/monthly-changes
    ?year=&department_id=
    → InsuranceMonthlyChangesResponse   (12 điểm dữ liệu)

GET /api/v1/reports/insurance/payroll-fund
    ?year=&department_id=
    → InsurancePayrollFundResponse      (12 điểm dữ liệu)

GET /api/v1/reports/insurance/non-participants
    ?department_id=&page=&page_size=
    → InsuranceNonParticipantsResponse

GET /api/v1/reports/insurance/by-department
    ?year=&month=
    → InsuranceDepartmentBreakdownResponse

GET /api/v1/reports/insurance/employee-history
    ?employee_id=&year=
    → InsuranceEmployeeHistoryResponse

GET /api/v1/reports/insurance/export
    ?year=&month=&department_id=
    → StreamingResponse (.xlsx — báo cáo tổng hợp quản lý)
```

---

## Schemas (Pydantic v2)

```python
# backend/app/schemas/insurance_analytics.py

from __future__ import annotations
from datetime import date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict


class InsuranceDashboardKPI(BaseModel):
    """KPI tổng quan tháng/năm được chọn."""
    year: int
    month: int
    department_id: Optional[int]

    # Tham gia BHXH
    participating_count: int            # đang active
    total_active_employees: int         # tổng nhân viên đang làm
    participation_rate: float           # %

    # Quỹ lương
    total_basis_amount: Decimal         # VND

    # Biến động tháng
    increased_count: int
    decreased_count: int
    net_change: int                     # increased - decreased


class MonthlyChangePoint(BaseModel):
    month: int                          # 1–12
    increased: int
    decreased: int
    net: int


class InsuranceMonthlyChangesResponse(BaseModel):
    year: int
    department_id: Optional[int]
    data: list[MonthlyChangePoint]      # 12 phần tử


class PayrollFundPoint(BaseModel):
    month: int
    added_amount: Decimal               # từ tăng trong tháng
    removed_amount: Decimal             # từ giảm trong tháng
    snapshot_amount: Optional[Decimal]  # tổng quỹ hiện tại (chỉ tháng hiện tại)


class InsurancePayrollFundResponse(BaseModel):
    year: int
    department_id: Optional[int]
    data: list[PayrollFundPoint]


class NonParticipantRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    employee_id: int
    full_name: str
    department_name: str
    participation_status: Optional[str]     # 'paused' | 'stopped' | None (chưa có profile)
    status_effective_from: Optional[date]
    status_note: Optional[str]
    company_bhxh_joined_date: Optional[date]


class InsuranceNonParticipantsResponse(BaseModel):
    items: list[NonParticipantRow]
    total: int
    page: int
    page_size: int


class DepartmentBreakdownRow(BaseModel):
    department_id: int
    department_name: str
    participating_count: int
    total_count: int
    participation_rate: float           # %
    total_basis_amount: Optional[Decimal]


class InsuranceDepartmentBreakdownResponse(BaseModel):
    year: int
    month: int
    items: list[DepartmentBreakdownRow]


class EmployeeHistoryPoint(BaseModel):
    effective_date: date
    change_type: str                    # 'increase' | 'decrease'
    change_reason: str
    basis_amount: Optional[Decimal]
    participation_status_after: Optional[str]


class InsuranceEmployeeHistoryResponse(BaseModel):
    employee_id: int
    full_name: str
    current_participation_status: Optional[str]
    current_basis_amount: Optional[Decimal]
    history: list[EmployeeHistoryPoint]
```

---

## Service Logic — `insurance_analytics_service.py`

File mới: `backend/app/services/insurance_analytics_service.py`

```python
"""
Plan 11.4 — Analytics service cho báo cáo BHXH tổng hợp.
Không trùng với insurance_report_service.py (Plan 6.4 — approval workflow).
"""

async def get_dashboard(
    session: AsyncSession,
    year: int,
    month: int,
    department_id: int | None,
) -> dict:
    """
    Trả về InsuranceDashboardKPI:
    - Query participation_status = 'active' từ employee_insurance_profiles
    - Filter theo department_id qua JOIN employee_job_records (is_current=TRUE)
    - Đếm increased/decreased từ insurance_change_events theo effective_date year/month
    """

async def get_monthly_changes(
    session: AsyncSession,
    year: int,
    department_id: int | None,
) -> dict:
    """
    Trả về 12 điểm tăng/giảm cho năm :year.
    GROUP BY EXTRACT(MONTH FROM effective_date).
    Tháng không có event → point với increased=0, decreased=0.
    """

async def get_payroll_fund(
    session: AsyncSession,
    year: int,
    department_id: int | None,
) -> dict:
    """
    Trả về 12 điểm added_amount/removed_amount từ insurance_change_events.
    Tháng hiện tại (year/month == today): bổ sung snapshot_amount từ SUM(insurance_basis_amount).
    """

async def get_non_participants(
    session: AsyncSession,
    department_id: int | None,
    page: int,
    page_size: int,
) -> dict:
    """
    Nhân viên is_active=TRUE mà participation_status != 'active' hoặc chưa có profile.
    JOIN employee_job_records is_current=TRUE → lấy department.
    Có phân trang.
    """

async def get_department_breakdown(
    session: AsyncSession,
    year: int,
    month: int,
) -> dict:
    """
    GROUP BY department: participating_count, total_count, participation_rate, total_basis_amount.
    """

async def get_employee_history(
    session: AsyncSession,
    employee_id: int,
    year: int | None,
) -> dict:
    """
    Lịch sử insurance_change_events của nhân viên.
    Bổ sung profile hiện tại (current_participation_status, current_basis_amount).
    Filter theo year nếu có.
    ORDER BY effective_date DESC.
    """

async def export_analytics_xlsx(
    session: AsyncSession,
    year: int,
    month: int,
    department_id: int | None,
) -> bytes:
    """
    openpyxl: workbook 3 sheets:
    - Sheet "Tổng quan": KPI cards dạng bảng
    - Sheet "Phòng ban": DepartmentBreakdownRow
    - Sheet "Không tham gia": NonParticipantRow
    Header: company name, kỳ báo cáo, ngày xuất, người xuất.
    """
```

### Kỹ thuật xử lý tháng không có event

```python
# Đảm bảo trả đủ 12 tháng dù không có event
month_map: dict[int, MonthlyChangePoint] = {
    m: MonthlyChangePoint(month=m, increased=0, decreased=0, net=0)
    for m in range(1, 13)
}
for row in db_rows:
    month_map[row.month] = MonthlyChangePoint(
        month=row.month,
        increased=row.increased,
        decreased=row.decreased,
        net=row.increased - row.decreased,
    )
return sorted(month_map.values(), key=lambda x: x.month)
```

---

## Frontend Design

### Route và cấu trúc

**Route:** `/reports/insurance` (thêm vào `/app` children trong `index.ts`)  
**View chính:** `frontend/src/views/reports/InsuranceAnalyticsView.vue`

> Đặt trong `views/reports/` (không phải `views/insurance/`) để thống nhất với module Reports (§11).

### Bố cục màn hình

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Báo cáo Bảo hiểm                                       [Xuất Excel]        │
│ Năm: [2026 ▼]   Tháng: [05 ▼]   Phòng ban: [Tất cả ▼]    [Xem báo cáo]   │
├─────────────────────────────────────────────────────────────────────────────┤
│  KPI Cards (5 cards, responsive grid)                                       │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │
│  │ Đang tham gia│ │ Quỹ lương   │ │ Tăng tháng  │ │ Giảm tháng  │       │
│  │   142 NV    │ │ 1.23 tỷ VND │ │    3 NV     │ │    1 NV     │       │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘       │
│  ┌──────────────┐                                                           │
│  │ Tỷ lệ tham gia│                                                          │
│  │   94.7%     │                                                            │
│  └──────────────┘                                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│  [Tăng/giảm theo tháng]          [Quỹ lương theo tháng]                    │
│  Stacked bar chart (12 tháng)    Line chart (12 tháng)                      │
│  ■ Tăng  ■ Giảm                  ── Quỹ lương BHXH                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  Breakdown theo phòng ban                                                   │
│  ┌──────────────┬──────────┬──────────┬────────────┬──────────────┐        │
│  │ Phòng ban    │ Tham gia │ Tổng NV  │ Tỷ lệ %   │ Quỹ lương   │        │
│  ├──────────────┼──────────┼──────────┼────────────┼──────────────┤        │
│  │ Kế toán      │ 12       │ 13       │ 92.3%      │ 156,000,000  │        │
│  │ Nhân sự      │ 8        │ 8        │ 100%       │ 112,000,000  │        │
│  └──────────────┴──────────┴──────────┴────────────┴──────────────┘        │
├─────────────────────────────────────────────────────────────────────────────┤
│  Nhân viên không tham gia BHXH  ⚠ 8 nhân viên                              │
│  ┌─────────┬──────────────┬──────────────┬────────────────┬─────────────┐  │
│  │ Mã NV   │ Họ tên       │ Phòng ban    │ Trạng thái    │ Từ ngày     │  │
│  ├─────────┼──────────────┼──────────────┼────────────────┼─────────────┤  │
│  │ NV042   │ Nguyễn Thị B │ Kinh doanh   │ Tạm dừng      │ 01/03/2026  │  │
│  │ NV088   │ Trần Văn C   │ Kỹ thuật     │ Chưa có hồ sơ │ —          │  │
│  └─────────┴──────────────┴──────────────┴────────────────┴─────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Mobile layout
- Cards: 2×2 grid (`grid-cols-2` ≤ md, `grid-cols-4` ≥ lg) — dùng PrimeVue v4 utility classes
- Charts: full-width (`col-span-full`), height giảm xuống 220px
- Tables: horizontal scroll

### Component và service method

**Service method mới** thêm vào `frontend/src/services/insuranceService.ts`:

```typescript
// Insurance Analytics — Plan 11.4
getAnalyticsDashboard: (params: { year: number; month: number; department_id?: number }) =>
  api.get<InsuranceDashboardKPI>('/reports/insurance/dashboard', { params }),

getMonthlyChanges: (params: { year: number; department_id?: number }) =>
  api.get<InsuranceMonthlyChangesResponse>('/reports/insurance/monthly-changes', { params }),

getPayrollFund: (params: { year: number; department_id?: number }) =>
  api.get<InsurancePayrollFundResponse>('/reports/insurance/payroll-fund', { params }),

getNonParticipants: (params: { department_id?: number; page?: number; page_size?: number }) =>
  api.get<InsuranceNonParticipantsResponse>('/reports/insurance/non-participants', { params }),

getDepartmentBreakdown: (params: { year: number; month: number }) =>
  api.get<InsuranceDepartmentBreakdownResponse>('/reports/insurance/by-department', { params }),

exportAnalytics: (params: { year: number; month: number; department_id?: number }) =>
  api.get('/reports/insurance/export', { params, responseType: 'blob' }),
```

---

## Cấu trúc file

### Backend (file mới)

```
backend/app/services/insurance_analytics_service.py   (NEW)
backend/app/schemas/insurance_analytics.py            (NEW)
backend/app/api/v1/endpoints/insurance_reports.py     (NEW — router prefix /reports/insurance)
backend/tests/test_insurance_analytics.py             (NEW)
```

### Backend (file chỉnh sửa)

```
backend/app/api/v1/router.py    (EDIT — thêm include_router insurance_reports)
```

### Frontend (file mới)

```
frontend/src/views/reports/InsuranceAnalyticsView.vue (NEW)
```

### Frontend (file chỉnh sửa)

```
frontend/src/services/insuranceService.ts             (EDIT — thêm analytics methods + types)
frontend/src/router/index.ts                          (EDIT — thêm route /reports/insurance)
frontend/src/assets/styles/views/_insurance.scss      (EDIT — thêm CSS analytics)
```

---

## Kế hoạch theo Slice

### Slice 1 — Backend Service + Schemas

**Mục tiêu:** Toàn bộ business logic analytics sẵn sàng, không cần migration (dùng bảng đã có).

**Files:**
```
backend/app/schemas/insurance_analytics.py            (NEW)
backend/app/services/insurance_analytics_service.py   (NEW)
```

**Checklist:**
- [ ] Schema: `InsuranceDashboardKPI`, `InsuranceMonthlyChangesResponse`, `InsurancePayrollFundResponse`, `InsuranceNonParticipantsResponse`, `InsuranceDepartmentBreakdownResponse`, `InsuranceEmployeeHistoryResponse`
- [ ] Service: `get_dashboard()` — 5 KPI queries với filter `department_id` qua `employee_job_records`
- [ ] Service: `get_monthly_changes()` — GROUP BY month, đủ 12 tháng dù không có event
- [ ] Service: `get_payroll_fund()` — added/removed theo tháng từ `insurance_change_events`
- [ ] Service: `get_non_participants()` — `participation_status != 'active'` hoặc chưa có profile, phân trang
- [ ] Service: `get_department_breakdown()` — JOIN `employee_job_records` is_current=TRUE
- [ ] Service: `get_employee_history()` — events theo `employee_id`, optional filter year
- [ ] Service: `export_analytics_xlsx()` — openpyxl 3 sheets

**Exit criteria:**
- Import service không lỗi
- Gọi thủ công trong Python shell với session thật → dict hợp lệ
- `get_monthly_changes()` với năm không có event → 12 điểm zeros

---

### Slice 2 — API Endpoints + Router

**Mục tiêu:** Endpoint RESTful hoạt động, Swagger docs rõ ràng.

**Files:**
```
backend/app/api/v1/endpoints/insurance_reports.py     (NEW)
backend/app/api/v1/router.py                          (EDIT)
```

**Nội dung `insurance_reports.py`:**

```python
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.api.v1.deps import require_permission
from app.core.database import get_session
from app.models.auth import User
from app.schemas.insurance_analytics import (
    InsuranceDashboardKPI,
    InsuranceDepartmentBreakdownResponse,
    InsuranceMonthlyChangesResponse,
    InsuranceNonParticipantsResponse,
    InsurancePayrollFundResponse,
)
from app.services import insurance_analytics_service

router = APIRouter()

@router.get("/dashboard", response_model=InsuranceDashboardKPI, ...)
async def get_dashboard(
    year: int = Query(..., ge=2020, le=2100),
    month: int = Query(..., ge=1, le=12),
    department_id: Optional[int] = Query(None),
    current_user: User = require_permission("insurance:read"),
    session: AsyncSession = Depends(get_session),
): ...

@router.get("/monthly-changes", response_model=InsuranceMonthlyChangesResponse, ...)
@router.get("/payroll-fund", response_model=InsurancePayrollFundResponse, ...)
@router.get("/non-participants", response_model=InsuranceNonParticipantsResponse, ...)
@router.get("/by-department", response_model=InsuranceDepartmentBreakdownResponse, ...)
@router.get("/export")  # → StreamingResponse xlsx
```

**Thêm vào `router.py`:**
```python
from app.api.v1.endpoints import insurance_reports
router.include_router(
    insurance_reports.router,
    prefix="/reports/insurance",
    tags=["Báo cáo Bảo hiểm Analytics"],
)
```

**Checklist:**
- [ ] 7 endpoints đăng ký đúng prefix `/reports/insurance`
- [ ] Permission guard `insurance:read` trên tất cả endpoints
- [ ] Export endpoint trả `StreamingResponse` với `Content-Disposition: attachment; filename="bao_cao_bhxh_{year}_{month}.xlsx"`
- [ ] Swagger UI (`/docs`) hiển thị đầy đủ, response schemas đúng

**Exit criteria:**
- `curl -H "Authorization: Bearer ..." http://localhost:8000/api/v1/reports/insurance/dashboard?year=2026&month=5` → JSON hợp lệ
- `curl .../export?year=2026&month=5` → file `.xlsx` download được mở bằng LibreOffice Calc

---

### Slice 3 — Frontend Analytics View

**Mục tiêu:** Dashboard đầy đủ, mobile responsive, kết nối API thật.

**Files:**
```
frontend/src/services/insuranceService.ts             (EDIT)
frontend/src/router/index.ts                          (EDIT)
frontend/src/views/reports/InsuranceAnalyticsView.vue (NEW)
frontend/src/assets/styles/views/_insurance.scss      (EDIT)
```

**Cấu trúc `InsuranceAnalyticsView.vue`:**

```
<script setup lang="ts">
// State: selectedYear, selectedMonth, selectedDepartment
// Composables: useInsuranceDashboard, useMonthlyChanges, usePayrollFund, etc.
// Dùng Promise.all() để fetch song song 5 API calls khi filter thay đổi
// Chart library: PrimeVue Chart component (wrapper Chart.js)
</script>

<template>
  <!-- Section 1: Filter bar -->
  <div class="ins-analytics-filters">
    <Select v-model="selectedYear" .../>
    <Select v-model="selectedMonth" .../>
    <Select v-model="selectedDepartment" .../>
    <Button @click="fetchAll">Xem báo cáo</Button>
    <Button @click="exportXlsx" severity="secondary">Xuất Excel</Button>
  </div>

  <!-- Section 2: KPI Cards -->
  <div class="ins-kpi-grid">
    <div class="ins-kpi-card" v-for="kpi in kpiCards" :key="kpi.label">
      <div class="ins-kpi-value">{{ kpi.value }}</div>
      <div class="ins-kpi-label">{{ kpi.label }}</div>
    </div>
  </div>

  <!-- Section 3: Charts (2 columns desktop, 1 column mobile) -->
  <div class="ins-charts-grid">
    <Chart type="bar" :data="monthlyChangesChartData" .../>   <!-- stacked bar -->
    <Chart type="line" :data="payrollFundChartData" .../>
  </div>

  <!-- Section 4: Department breakdown DataTable -->
  <DataTable :value="departmentRows" ...>...</DataTable>

  <!-- Section 5: Non-participants DataTable với cảnh báo -->
  <Message severity="warn" v-if="nonParticipants.total > 0">
    ⚠ {{ nonParticipants.total }} nhân viên không tham gia BHXH
  </Message>
  <DataTable :value="nonParticipants.items" paginator ...>...</DataTable>
</template>
```

**CSS global** thêm vào `_insurance.scss`:

```scss
// Plan 11.4 — Insurance Analytics
.ins-analytics-filters { display: flex; flex-wrap: wrap; gap: 0.75rem; align-items: flex-end; }
.ins-kpi-grid {
  display: grid;
  gap: 1rem;
  grid-template-columns: repeat(2, 1fr);       // mobile 2 cột
  @media (min-width: 1024px) { grid-template-columns: repeat(5, 1fr); }  // desktop 5 cột
}
.ins-kpi-card {
  padding: 1.25rem;
  border-radius: var(--p-border-radius-md);
  background: var(--p-surface-card);
  border: 1px solid var(--p-surface-border);
}
.ins-kpi-value { font-size: 1.75rem; font-weight: 700; color: var(--p-primary-color); }
.ins-kpi-label { font-size: 0.85rem; color: var(--p-text-muted-color); margin-top: 0.25rem; }
.ins-charts-grid {
  display: grid;
  gap: 1rem;
  grid-template-columns: 1fr;
  @media (min-width: 768px) { grid-template-columns: repeat(2, 1fr); }
}
.ins-non-participant-warning { color: var(--p-orange-600); font-weight: 600; }
html.dark-mode {
  .ins-kpi-card { background: var(--p-surface-800); border-color: var(--p-surface-700); }
}
```

**Thêm route** vào `router/index.ts` trong block `/app` children:

```typescript
{
  path: 'reports/insurance',
  name: 'reports-insurance-analytics',
  component: () => import('@/views/reports/InsuranceAnalyticsView.vue'),
  meta: { title: 'Báo cáo Bảo hiểm', permission: 'insurance:read' },
},
```

**Checklist:**
- [ ] 5 KPI cards hiển thị đúng giá trị từ API
- [ ] Stacked bar chart: trục X là tháng 1–12, hai series "Tăng" (xanh) / "Giảm" (đỏ)
- [ ] Line chart: trục X là tháng 1–12, series "Quỹ lương BHXH"
- [ ] Filter thay đổi → refetch tất cả API, loading skeleton hiển thị trong khi chờ
- [ ] DataTable phòng ban: `participation_rate` hiển thị màu đỏ nếu < 80%
- [ ] DataTable không tham gia: badge màu cam "Tạm dừng" / màu đỏ "Đã dừng" / màu xám "Chưa có hồ sơ"
- [ ] Nút "Xuất Excel" → download file `bao_cao_bhxh_2026_05.xlsx`
- [ ] Mobile: test trên viewport 375px — cards 2×2, charts full-width
- [ ] `vue-tsc --noEmit` không lỗi

**Exit criteria:**
- Mở trình duyệt tại `/reports/insurance` → trang load, filter, charts, tables hoạt động với dữ liệu thật
- Xuất Excel → file mở được, 3 sheet, dữ liệu đúng

---

## Thứ tự thực hiện

```
Slice 1 (Service + Schemas — không cần migration)
  ↓
Slice 2 (API Endpoints + Router registration)
  ↓
Slice 3 (Frontend View + Routes + Service methods)
```

---

## Không nằm trong 11.4

| Phần | Thuộc về |
|---|---|
| Approval workflow báo cáo tháng, export D02-TS | Plan 6.4 (đã hoàn thành) |
| Import dữ liệu bảo hiểm hàng loạt | Plan 12.1 |
| Gửi file XML lên cổng dichvucong.gov.vn | Ngoài phạm vi (cần API bên ngoài) |
| Lịch sử nộp hồ sơ đến cơ quan BHXH | Ngoài phạm vi |
| Điều chỉnh lương BHXH tạo biến động | Plan 7.2 |
| Báo cáo C12-TS (Bảng thanh toán chi tiết) | Plan 6.4 mở rộng hoặc 6.5 |
| So sánh nhiều năm (multi-year trend) | 11.4 mở rộng sau |

---

## Rủi ro và cách né

| Rủi ro | Cách né |
|---|---|
| `insurance_basis_amount` NULL cho nhiều NV → quỹ lương sai | Service dùng `COALESCE(insurance_basis_amount, 0)` và ghi chú "X nhân viên chưa có mức đóng" trong response |
| NV active nhưng chưa có `employee_insurance_profiles` → bị bỏ qua | Query dùng `LEFT JOIN` và tính `total_active_employees` từ `employees` table, không từ profiles |
| Tháng không có event → chart trống → trông như bug | Service đảm bảo trả đủ 12 điểm, `increased=0` / `decreased=0` cho tháng không có event |
| `employee_job_records` NV không có bản ghi `is_current=TRUE` (data inconsistency) | Query thêm `OR ejr.id IS NULL` để không bỏ sót NV; ghi log warning nếu count mismatch |
| 5 API calls song song → chậm nếu DB load cao | Frontend dùng `Promise.all()` (không tuần tự); mỗi query chạy trong 1 DB request; cân nhắc thêm `LIMIT` cho non-participants |
| Export xlsx với nhiều NV → timeout | Endpoint export chạy async, dùng streaming; nếu > 5000 dòng thì paginate hoặc background job |
| CSS mới xung đột với class cũ trong `_insurance.scss` | Prefix tất cả class mới bằng `ins-analytics-*` hoặc `ins-kpi-*` để không trùng |
| Route `/reports/insurance` trùng với menu item nào đó trong Plan 11 | Kiểm tra `router/index.ts` trước khi thêm; đặt trong `children` của `/app` cùng level với `reports` hiện có |
